from __future__ import annotations

import os

import joblib
import pandas as pd

from pyspark import SparkFiles
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    from_json,
    pandas_udf,
)
from pyspark.sql.types import (
    DoubleType,
    StringType,
    StructField,
    StructType,
)

from amazon_sentiment.pipeline.cache import (
    get_redis_client,
    update_sentiment_cache,
)
from amazon_sentiment.pipeline.database import (
    get_connection,
    save_review,
)


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

KAFKA_SERVER = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:9092",
)

TOPIC = os.getenv(
    "KAFKA_TOPIC",
    "review-events",
)

MODEL_FILENAME = "sentiment_pipeline.joblib"

CHECKPOINT_LOCATION = os.getenv(
    "SPARK_CHECKPOINT_LOCATION",
    ".spark-checkpoints/ml-persistence-v1",
)


# ---------------------------------------------------------
# Kafka event schema
# ---------------------------------------------------------

EVENT_SCHEMA = StructType(
    [
        StructField(
            "review_id",
            StringType(),
            True,
        ),
        StructField(
            "product_id",
            StringType(),
            True,
        ),
        StructField(
            "review_text",
            StringType(),
            True,
        ),
        StructField(
            "created_at",
            StringType(),
            True,
        ),
    ]
)


# ---------------------------------------------------------
# Pandas UDF output schema
#
# nullable=True is required because Arrow/Pandas
# returns nullable fields.
# ---------------------------------------------------------

PREDICTION_SCHEMA = StructType(
    [
        StructField(
            "sentiment",
            StringType(),
            True,
        ),
        StructField(
            "positive_probability",
            DoubleType(),
            True,
        ),
    ]
)


# ---------------------------------------------------------
# ML model
# ---------------------------------------------------------

_model = None


def get_model():
    """
    Load the ML model once per Python worker.

    The model is distributed to Spark using:

    --files /opt/app/artifacts/sentiment_pipeline.joblib
    """

    global _model

    if _model is None:
        model_path = SparkFiles.get(
            MODEL_FILENAME
        )

        _model = joblib.load(
            model_path
        )

    return _model


# ---------------------------------------------------------
# Spark ML inference
# ---------------------------------------------------------

@pandas_udf(PREDICTION_SCHEMA)
def predict_sentiment(
    reviews: pd.Series,
) -> pd.DataFrame:
    """
    Perform vectorized sentiment inference.

    Spark sends review text batches to Pandas.
    The existing TF-IDF + Logistic Regression
    pipeline performs prediction.
    """

    model = get_model()

    cleaned_reviews = (
        reviews
        .fillna("")
        .astype(str)
        .map(
            lambda value:
            " ".join(value.split())
        )
    )

    texts = cleaned_reviews.tolist()

    predictions = model.predict(
        texts
    )

    probabilities = model.predict_proba(
        texts
    )[:, 1]

    sentiments = [
        (
            "Positive"
            if int(prediction) == 1
            else "Negative"
        )
        for prediction in predictions
    ]

    return pd.DataFrame(
        {
            "sentiment": sentiments,
            "positive_probability":
                probabilities.astype(float),
        }
    )


# ---------------------------------------------------------
# External storage
# ---------------------------------------------------------

def write_partition(rows):
    """
    Persist one Spark partition.

    Each Spark partition gets its own:
    - PostgreSQL connection
    - Redis connection
    """

    database = get_connection()
    redis_client = get_redis_client()

    try:
        for row in rows:

            review_id = row["review_id"]
            product_id = row["product_id"]
            review_text = row["review_text"]
            created_at = row["created_at"]
            sentiment = row["sentiment"]

            probability = float(
                row["positive_probability"]
            )

            review = {
                "review_id": review_id,
                "product_id": product_id,
                "review_text": review_text,
                "created_at": created_at,
            }

            # PostgreSQL uses review_id idempotency.
            save_review(
                database,
                review,
                sentiment,
                probability,
            )

            # Redis uses processed:<review_id>
            # to prevent duplicate counter updates.
            cache_updated = (
                update_sentiment_cache(
                    redis_client,
                    review_id,
                    product_id,
                    sentiment,
                    probability,
                )
            )

            print(
                f"Processed review "
                f"{review_id} | "
                f"{sentiment} | "
                f"Probability="
                f"{probability:.4f} | "
                f"Redis updated="
                f"{cache_updated}"
            )

    finally:
        database.close()
        redis_client.close()


# ---------------------------------------------------------
# Spark foreachBatch
# ---------------------------------------------------------

def process_batch(
    batch_df,
    batch_id: int,
):
    """
    Process one Spark Structured Streaming
    micro-batch.
    """

    print(
        f"Processing Spark batch: "
        f"{batch_id}"
    )

    valid_batch = batch_df.dropna(
        subset=[
            "review_id",
            "product_id",
            "review_text",
            "created_at",
            "sentiment",
            "positive_probability",
        ]
    )

    valid_batch.foreachPartition(
        write_partition
    )

    print(
        f"Completed Spark batch: "
        f"{batch_id}"
    )


# ---------------------------------------------------------
# Main Spark application
# ---------------------------------------------------------

def main():

    print(
        f"Kafka server: "
        f"{KAFKA_SERVER}"
    )

    print(
        f"Kafka topic: "
        f"{TOPIC}"
    )

    print(
        f"Checkpoint location: "
        f"{CHECKPOINT_LOCATION}"
    )

    spark = (
        SparkSession
        .builder
        .appName(
            "AmazonReviewSentimentPipeline"
        )
        .master("local[*]")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel(
        "WARN"
    )

    print(
        "Starting Amazon Review "
        "Spark pipeline..."
    )

    # -----------------------------------------------------
    # Kafka source
    # -----------------------------------------------------

    raw_stream = (
        spark
        .readStream
        .format("kafka")
        .option(
            "kafka.bootstrap.servers",
            KAFKA_SERVER,
        )
        .option(
            "subscribe",
            TOPIC,
        )
        .option(
            "startingOffsets",
            "latest",
        )
        .load()
    )

    # -----------------------------------------------------
    # Parse Kafka JSON
    # -----------------------------------------------------

    parsed_stream = (
        raw_stream
        .select(
            col("value")
            .cast("string")
            .alias("json_value"),

            col("partition"),

            col("offset"),

            col("timestamp"),
        )
        .withColumn(
            "review",
            from_json(
                col("json_value"),
                EVENT_SCHEMA,
            ),
        )
        .select(
            col(
                "review.review_id"
            ).alias(
                "review_id"
            ),

            col(
                "review.product_id"
            ).alias(
                "product_id"
            ),

            col(
                "review.review_text"
            ).alias(
                "review_text"
            ),

            col(
                "review.created_at"
            ).alias(
                "created_at"
            ),

            col("partition"),

            col("offset"),

            col("timestamp"),
        )
    )

    # -----------------------------------------------------
    # ML inference
    # -----------------------------------------------------

    predicted_stream = (
        parsed_stream
        .filter(
            col("review_text").isNotNull()
        )
        .withColumn(
            "prediction",
            predict_sentiment(
                col("review_text")
            ),
        )
        .select(
            "review_id",

            "product_id",

            "review_text",

            "created_at",

            col(
                "prediction.sentiment"
            ).alias(
                "sentiment"
            ),

            col(
                "prediction."
                "positive_probability"
            ).alias(
                "positive_probability"
            ),

            "partition",

            "offset",

            "timestamp",
        )
    )

    # -----------------------------------------------------
    # Streaming sink
    # -----------------------------------------------------

    query = (
        predicted_stream
        .writeStream
        .foreachBatch(
            process_batch
        )
        .option(
            "checkpointLocation",
            CHECKPOINT_LOCATION,
        )
        .start()
    )

    print(
        "Spark pipeline waiting "
        "for review events..."
    )

    query.awaitTermination()


if __name__ == "__main__":
    main()