import os
import time
import uuid

import requests
import streamlit as st


API_URL = os.getenv(
    "API_URL",
    "http://localhost:8000",
)


st.set_page_config(
    page_title="Amazon Review Sentiment",
    page_icon="⭐",
    layout="centered",
)


st.title("Amazon Review Sentiment")

st.caption(
    "Enter your product review and "
    "get the sentiment result in real time."
)


def submit_review(
    product_id: str,
    review_text: str,
):
    response = requests.post(
        f"{API_URL}/reviews",
        json={
            "product_id": product_id,
            "review_text": review_text,
        },
        timeout=15,
    )

    response.raise_for_status()

    return response.json()


def wait_for_prediction(
    review_id: str,
    timeout: int = 40,
):
    """
    Poll FastAPI until Spark finishes processing
    and PostgreSQL contains the prediction.
    """

    deadline = (
        time.monotonic()
        + timeout
    )

    while (
        time.monotonic()
        < deadline
    ):
        response = requests.get(
            f"{API_URL}/reviews/{review_id}",
            timeout=5,
        )

        if response.status_code == 200:
            return response.json()

        if response.status_code != 404:
            response.raise_for_status()

        time.sleep(1)

    return None


def generate_product_id() -> str:
    """
    Automatically generate an internal product ID.

    The user does not need to enter this.
    """

    return (
        f"product-"
        f"{uuid.uuid4().hex[:12]}"
    )


with st.form("review_form"):
    review_text = st.text_area(
        "Your Review",
        placeholder=(
            "Example: "
            "The product quality is excellent "
            "and delivery was very fast."
        ),
        height=180,
    )

    submit = st.form_submit_button(
        "Check Sentiment",
        type="primary",
        use_container_width=True,
    )


if submit:
    if not review_text.strip():
        st.warning(
            "Please enter a review."
        )

    else:
        product_id = generate_product_id()

        try:
            with st.spinner(
                "Submitting review..."
            ):
                accepted = submit_review(
                    product_id,
                    review_text.strip(),
                )

            review_id = accepted[
                "review_id"
            ]

            st.info(
                "Review accepted. "
                "Analyzing sentiment..."
            )

            with st.spinner(
                "Running sentiment analysis..."
            ):
                result = wait_for_prediction(
                    review_id
                )

            if result is None:
                st.warning(
                    "The review is taking longer "
                    "than expected to process."
                )

                st.caption(
                    f"Review ID: {review_id}"
                )

            else:
                sentiment = result[
                    "sentiment"
                ]

                positive_probability = float(
                    result[
                        "positive_probability"
                    ]
                )

                if sentiment == "Positive":
                    confidence = (
                        positive_probability
                        * 100
                    )

                    st.success(
                        "Positive Review 😊"
                    )

                else:
                    confidence = (
                        1
                        - positive_probability
                    ) * 100

                    st.error(
                        "Negative Review 😞"
                    )

                col1, col2 = st.columns(2)

                col1.metric(
                    "Sentiment",
                    sentiment,
                )

                col2.metric(
                    "Confidence",
                    f"{confidence:.2f}%",
                )

                st.progress(
                    min(
                        confidence / 100,
                        1.0,
                    )
                )

                st.divider()

                st.subheader(
                    "Review"
                )

                st.write(
                    result[
                        "review_text"
                    ]
                )

                st.caption(
                    "Processed successfully "
                    "through Kafka and Spark."
                )

        except requests.ConnectionError:
            st.error(
                "Cannot connect to the backend. "
                "Make sure Docker Compose "
                "and FastAPI are running."
            )

        except requests.Timeout:
            st.error(
                "The backend request timed out."
            )

        except requests.RequestException as exc:
            st.error(
                f"Backend error: {exc}"
            )


st.divider()

st.caption(
    "Powered by FastAPI • Kafka • "
    "Spark Structured Streaming • "
    "PostgreSQL • Redis"
)