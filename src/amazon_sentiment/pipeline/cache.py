import os

import redis


REDIS_HOST = os.getenv(
    "REDIS_HOST",
    "localhost",
)

REDIS_PORT = int(
    os.getenv(
        "REDIS_PORT",
        "6379",
    )
)


def get_redis_client():
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True,
    )


CACHE_SCRIPT = """
local processed_key = KEYS[1]

if redis.call("EXISTS", processed_key) == 1 then
    return 0
end

local product_id = ARGV[1]
local sentiment = ARGV[2]
local probability = ARGV[3]

redis.call("INCR", "reviews:total")

redis.call(
    "INCR",
    "reviews:sentiment:" .. string.lower(sentiment)
)

redis.call(
    "INCR",
    "product:" .. product_id .. ":reviews"
)

redis.call(
    "INCR",
    "product:" ..
        product_id ..
        ":sentiment:" ..
        string.lower(sentiment)
)

redis.call(
    "HSET",
    "product:" .. product_id .. ":latest",
    "sentiment",
    sentiment,
    "positive_probability",
    probability
)

redis.call(
    "SET",
    processed_key,
    "1"
)

return 1
"""


def update_sentiment_cache(
    client,
    review_id: str,
    product_id: str,
    sentiment: str,
    probability: float,
) -> bool:
    processed_key = f"processed:{review_id}"

    result = client.eval(
        CACHE_SCRIPT,
        1,
        processed_key,
        product_id,
        sentiment,
        probability,
    )

    return result == 1


def get_global_stats(client):
    return {
        "total_reviews": int(
            client.get("reviews:total") or 0
        ),
        "positive_reviews": int(
            client.get("reviews:sentiment:positive") or 0
        ),
        "negative_reviews": int(
            client.get("reviews:sentiment:negative") or 0
        ),
    }


def get_product_sentiment(
    client,
    product_id: str,
):
    latest = client.hgetall(
        f"product:{product_id}:latest"
    )

    if not latest:
        return None

    return {
        "product_id": product_id,
        "total_reviews": int(
            client.get(
                f"product:{product_id}:reviews"
            )
            or 0
        ),
        "latest_sentiment": latest.get(
            "sentiment"
        ),
        "positive_probability": float(
            latest.get(
                "positive_probability",
                0,
            )
        ),
        "positive_reviews": int(
            client.get(
                f"product:{product_id}:sentiment:positive"
            )
            or 0
        ),
        "negative_reviews": int(
            client.get(
                f"product:{product_id}:sentiment:negative"
            )
            or 0
        ),
    }



