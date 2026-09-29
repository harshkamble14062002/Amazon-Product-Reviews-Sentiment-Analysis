import json
import os
import uuid
from datetime import datetime, timezone

from kafka import KafkaProducer


TOPIC = "review-events"


def create_producer():
    bootstrap_servers = os.getenv(
        "KAFKA_BOOTSTRAP_SERVERS",
        "localhost:9092",
    )

    return KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        key_serializer=lambda key: key.encode("utf-8"),
    )


def send_review(
    producer,
    product_id: str,
    review_text: str,
):
    event = {
        "review_id": str(uuid.uuid4()),
        "product_id": product_id,
        "review_text": review_text,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    future = producer.send(
        TOPIC,
        key=product_id,
        value=event,
    )

    metadata = future.get(timeout=10)

    event["partition"] = metadata.partition
    event["offset"] = metadata.offset

    return event


if __name__ == "__main__":
    producer = create_producer()

    try:
        event = send_review(
            producer,
            "amazon-product-001",
            "The product quality is excellent and delivery was fast.",
        )

        print(event)

    finally:
        producer.flush()
        producer.close()