import os

import psycopg


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://review_app:review_dev_password@localhost:5433/reviews",
)


def get_connection():
    return psycopg.connect(DATABASE_URL)




def save_review(
    connection,
    review: dict,
    sentiment: str,
    positive_probability: float,
):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO reviews (
                review_id,
                product_id,
                review_text,
                sentiment,
                positive_probability,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (review_id) DO NOTHING;
            """,
            (
                review["review_id"],
                review["product_id"],
                review["review_text"],
                sentiment,
                positive_probability,
                review["created_at"],
            ),
        )

    connection.commit()


def get_reviews(connection, limit: int = 20):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                review_id,
                product_id,
                review_text,
                sentiment,
                positive_probability,
                created_at
            FROM reviews
            ORDER BY created_at DESC
            LIMIT %s;
            """,
            (limit,),
        )

        rows = cursor.fetchall()

    return [
        {
            "review_id": row[0],
            "product_id": row[1],
            "review_text": row[2],
            "sentiment": row[3],
            "positive_probability": row[4],
            "created_at": row[5],
        }
        for row in rows
    ]

