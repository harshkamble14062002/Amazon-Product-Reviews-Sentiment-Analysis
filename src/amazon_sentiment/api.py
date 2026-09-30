from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from amazon_sentiment.pipeline.cache import (
    get_global_stats,
    get_redis_client,
)
from amazon_sentiment.pipeline.database import (
    get_connection,
    get_review_by_id,
    get_reviews,
)
from amazon_sentiment.pipeline.producer import (
    create_producer,
    send_review,
)


class ReviewRequest(BaseModel):
    product_id: str = Field(
        min_length=1,
        max_length=100,
    )

    review_text: str = Field(
        min_length=1,
        max_length=5000,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    producer = create_producer()

    app.state.kafka_producer = producer

    yield

    producer.flush()
    producer.close()


app = FastAPI(
    title="Amazon Review Sentiment API",
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "amazon-review-sentiment-api",
    }


@app.post(
    "/reviews",
    status_code=202,
)
def create_review(
    review: ReviewRequest,
):
    event = send_review(
        app.state.kafka_producer,
        review.product_id,
        review.review_text,
    )

    return {
        "status": "accepted",
        "review_id": event["review_id"],
        "product_id": event["product_id"],
        "partition": event["partition"],
        "offset": event["offset"],
    }


@app.get("/reviews")
def list_reviews(
    limit: int = 50,
):
    limit = max(
        1,
        min(limit, 200),
    )

    database = get_connection()

    try:
        return get_reviews(
            database,
            limit,
        )

    finally:
        database.close()


@app.get("/reviews/{review_id}")
def review_result(
    review_id: str,
):
    database = get_connection()

    try:
        result = get_review_by_id(
            database,
            review_id,
        )

    finally:
        database.close()

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Review is still being processed.",
        )

    return result


@app.get("/stats")
def statistics():
    redis_client = get_redis_client()

    try:
        return get_global_stats(
            redis_client
        )

    finally:
        redis_client.close()