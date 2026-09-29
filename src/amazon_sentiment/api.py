from contextlib import asynccontextmanager
from pydantic import BaseModel, Field

from amazon_sentiment.pipeline.producer import (
    create_producer,
    send_review,
)
from fastapi import FastAPI, HTTPException

from amazon_sentiment.pipeline.cache import (
    get_global_stats,
    get_product_sentiment,
    get_redis_client,
)
from amazon_sentiment.pipeline.database import (
    get_connection,
    get_reviews,
)


class ReviewRequest(BaseModel):
    product_id: str = Field(min_length=1, max_length=100)
    review_text: str = Field(min_length=1, max_length=5000)


@asynccontextmanager
async def lifespan(app: FastAPI):
    producer = create_producer()
    app.state.kafka_producer = producer

    yield

    producer.flush()
    producer.close()


app = FastAPI(
    title="Amazon Review Sentiment API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reviews", status_code=202)
def create_review(review: ReviewRequest):
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
def list_reviews(limit: int = 20):
    database = get_connection()

    try:
        return {
            "reviews": get_reviews(
                database,
                limit=min(limit, 100),
            )
        }
    finally:
        database.close()


@app.get("/stats")
def stats():
    redis_client = get_redis_client()

    try:
        return get_global_stats(redis_client)
    finally:
        redis_client.close()


@app.get("/products/{product_id}/sentiment")
def product_sentiment(product_id: str):
    redis_client = get_redis_client()

    try:
        result = get_product_sentiment(
            redis_client,
            product_id,
        )
    finally:
        redis_client.close()

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    return result