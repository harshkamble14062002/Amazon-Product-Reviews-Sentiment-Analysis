import uuid
from datetime import datetime, timezone

from amazon_sentiment.pipeline.database import (
    get_connection,
    save_review,
)


def test_duplicate_review_is_inserted_once():
    database = get_connection()

    review_id = str(uuid.uuid4())

    review = {
        "review_id": review_id,
        "product_id": "test-product-db",
        "review_text": "Excellent product.",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        save_review(
            database,
            review,
            "Positive",
            0.95,
        )

        save_review(
            database,
            review,
            "Positive",
            0.95,
        )

        with database.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM reviews
                WHERE review_id = %s;
                """,
                (review_id,),
            )

            count = cursor.fetchone()[0]

        assert count == 1

    finally:
        database.close()