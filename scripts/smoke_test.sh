#!/usr/bin/env bash

set -euo pipefail

PRODUCT_ID="smoke-$(date +%s)"

echo "1. Checking API..."

curl -fsS \
  http://localhost:8000/health

echo
echo "API OK"

echo
echo "2. Sending review..."

curl -fsS \
  -X POST \
  http://localhost:8000/reviews \
  -H "Content-Type: application/json" \
  -d "{
    \"product_id\": \"$PRODUCT_ID\",
    \"review_text\": \"This product is excellent and works perfectly.\"
  }"

echo
echo "Review sent: $PRODUCT_ID"

echo
echo "3. Waiting for Spark result..."

FOUND=0

for attempt in {1..60}; do
    RESULT=$(
        docker exec amazon-reviews-postgres \
        psql \
        -U review_app \
        -d reviews \
        -tAc "
            SELECT sentiment
            FROM reviews
            WHERE product_id = '$PRODUCT_ID'
            LIMIT 1;
        "
    )

    if [[ -n "$RESULT" ]]; then
        FOUND=1
        break
    fi

    sleep 3
done

if [[ "$FOUND" -ne 1 ]]; then
    echo "ERROR: Spark did not write result to PostgreSQL."
    exit 1
fi

echo "PostgreSQL result: $RESULT"

echo
echo "4. Checking Redis..."

REDIS_RESULT=$(
    docker exec amazon-reviews-redis \
    redis-cli \
    HGET \
    "product:$PRODUCT_ID:latest" \
    sentiment
)

if [[ -z "$REDIS_RESULT" ]]; then
    echo "ERROR: Redis result missing."
    exit 1
fi

echo "Redis result: $REDIS_RESULT"

echo
echo "===================================="
echo "END-TO-END PIPELINE TEST PASSED"
echo "===================================="
echo
echo "FastAPI -> Kafka -> Spark -> ML"
echo "                   -> PostgreSQL"
echo "                   -> Redis"