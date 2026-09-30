import uuid

from amazon_sentiment.pipeline.cache import (
    get_redis_client,
    update_sentiment_cache,
)


def test_duplicate_review_updates_redis_only_once():
    client = get_redis_client()

    review_id = str(uuid.uuid4())
    product_id = f"test-product-{uuid.uuid4()}"

    total_before = int(
        client.get("reviews:total") or 0
    )

    # First delivery
    first_result = update_sentiment_cache(
        client,
        review_id,
        product_id,
        "Positive",
        0.95,
    )

    # Simulate Kafka delivering same event again
    second_result = update_sentiment_cache(
        client,
        review_id,
        product_id,
        "Positive",
        0.95,
    )

    total_after = int(
        client.get("reviews:total") or 0
    )

    assert first_result is True
    assert second_result is False

    # Counter should increase only once
    assert total_after == total_before + 1

    # Product counter should also be exactly 1
    assert int(
        client.get(
            f"product:{product_id}:reviews"
        )
    ) == 1

    # Dedup marker must exist
    assert client.exists(
        f"processed:{review_id}"
    ) == 1

    client.close()