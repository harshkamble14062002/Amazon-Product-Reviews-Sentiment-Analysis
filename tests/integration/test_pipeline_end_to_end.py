import json
import os
import time
import uuid
from datetime import datetime, timezone

from kafka import KafkaAdminClient, KafkaProducer
from kafka.errors import NoBrokersAvailable

from amazon_sentiment.pipeline.cache import (
    get_redis_client,
)
from amazon_sentiment.pipeline.database import (
    get_connection,
)


TOPIC = "review-events"

KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:9092",
)


def wait_for_kafka(
    timeout: int = 30,
) -> None:
    """
    Wait until Kafka is ready before
    starting the integration test.
    """

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        try:
            admin = KafkaAdminClient(
                bootstrap_servers=(
                    KAFKA_BOOTSTRAP_SERVERS
                ),
                request_timeout_ms=3000,
            )

            admin.list_topics()
            admin.close()

            return

        except NoBrokersAvailable:
            time.sleep(1)

    raise RuntimeError(
        "Kafka did not become available at "
        f"{KAFKA_BOOTSTRAP_SERVERS}"
    )


def wait_for_postgres_result(
    database,
    review_id: str,
    timeout: int = 30,
):
    """
    Wait for Spark to process the Kafka event
    and write the result to PostgreSQL.
    """

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        with database.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    product_id,
                    sentiment,
                    positive_probability
                FROM reviews
                WHERE review_id = %s;
                """,
                (review_id,),
            )

            row = cursor.fetchone()

        if row is not None:
            return row

        time.sleep(1)

    raise AssertionError(
        "Spark did not write the review "
        "to PostgreSQL within the timeout."
    )


def wait_for_redis_result(
    redis_client,
    review_id: str,
    product_id: str,
    timeout: int = 30,
):
    """
    Wait for Spark to update Redis.
    """

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        processed = redis_client.exists(
            f"processed:{review_id}"
        )

        latest = redis_client.hgetall(
            f"product:{product_id}:latest"
        )

        if processed == 1 and latest:
            return latest

        time.sleep(1)

    raise AssertionError(
        "Spark did not update Redis "
        "within the timeout."
    )


def test_kafka_to_postgres_and_redis():
    # ----------------------------------------
    # Make sure Kafka is available
    # ----------------------------------------

    wait_for_kafka()

    # ----------------------------------------
    # Generate unique test event
    # ----------------------------------------

    review_id = str(uuid.uuid4())

    product_id = (
        f"e2e-product-{uuid.uuid4()}"
    )

    event = {
        "review_id": review_id,
        "product_id": product_id,
        "review_text": (
            "This product is excellent "
            "and works perfectly."
        ),
        "created_at": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
    }

    # ----------------------------------------
    # Produce event to Kafka
    # ----------------------------------------

    producer = KafkaProducer(
        bootstrap_servers=(
            KAFKA_BOOTSTRAP_SERVERS
        ),
        value_serializer=lambda value: (
            json.dumps(value).encode("utf-8")
        ),
        key_serializer=lambda key: (
            key.encode("utf-8")
        ),
    )

    try:
        metadata = producer.send(
            TOPIC,
            key=product_id,
            value=event,
        ).get(timeout=10)

        assert metadata.topic == TOPIC

    finally:
        producer.flush()
        producer.close()

    # ----------------------------------------
    # Connect to external stores
    # ----------------------------------------

    database = get_connection()
    redis_client = get_redis_client()

    try:
        # ------------------------------------
        # Wait for:
        #
        # Kafka
        #   ↓
        # Spark
        #   ↓
        # ML prediction
        #   ↓
        # PostgreSQL
        # ------------------------------------

        row = wait_for_postgres_result(
            database,
            review_id,
        )

        assert row is not None

        assert row[0] == product_id

        assert row[1] in (
            "Positive",
            "Negative",
        )

        assert row[2] is not None

        probability = float(
            row[2]
        )

        assert 0.0 <= probability <= 1.0

        # ------------------------------------
        # Redis verification
        # ------------------------------------

        latest = wait_for_redis_result(
            redis_client,
            review_id,
            product_id,
        )

        assert redis_client.exists(
            f"processed:{review_id}"
        ) == 1

        product_reviews = int(
            redis_client.get(
                f"product:{product_id}:reviews"
            )
            or 0
        )

        assert product_reviews == 1

        assert latest[
            "sentiment"
        ] in (
            "Positive",
            "Negative",
        )

        redis_probability = float(
            latest[
                "positive_probability"
            ]
        )

        assert (
            0.0
            <= redis_probability
            <= 1.0
        )

        # PostgreSQL and Redis should
        # contain the same prediction.

        assert (
            latest["sentiment"]
            == row[1]
        )

    finally:
        database.close()
        redis_client.close()