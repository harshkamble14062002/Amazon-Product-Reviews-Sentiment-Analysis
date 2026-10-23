import os

import pandas as pd
import requests
import streamlit as st


API_URL = os.getenv(
    "API_URL",
    "http://localhost:8000",
)


st.set_page_config(
    page_title="Sentiment Pipeline Dashboard",
    page_icon="📊",
    layout="wide",
)


def get_health():
    response = requests.get(
        f"{API_URL}/health",
        timeout=5,
    )

    response.raise_for_status()

    return response.json()


def get_stats():
    response = requests.get(
        f"{API_URL}/stats",
        timeout=5,
    )

    response.raise_for_status()

    return response.json()


def get_reviews():
    response = requests.get(
        f"{API_URL}/reviews",
        params={
            "limit": 100,
        },
        timeout=5,
    )

    response.raise_for_status()

    return response.json()


st.title(
    "Real-Time ML Pipeline Dashboard"
)

st.caption(
    "Monitor the Amazon Review "
    "Sentiment Processing System"
)


# -------------------------------------------------
# Sidebar
# -------------------------------------------------

with st.sidebar:
    st.header(
        "Architecture"
    )

    st.code(
        """
User
 ↓
Streamlit
 ↓
FastAPI
 ↓
Kafka
 ↓
Spark
 ↓
ML Model
 ↓
PostgreSQL
 +
Redis
"""
    )

    st.divider()

    if st.button(
        "Refresh Dashboard",
        use_container_width=True,
    ):
        st.rerun()


# -------------------------------------------------
# Backend health
# -------------------------------------------------

st.subheader(
    "System Status"
)

try:
    health = get_health()

    st.success(
        "FastAPI backend is online"
    )

except requests.RequestException:
    st.error(
        "FastAPI backend is offline"
    )

    st.stop()


# -------------------------------------------------
# Statistics
# -------------------------------------------------

try:
    stats = get_stats()

except requests.RequestException:
    stats = {
        "total_reviews": 0,
        "positive_reviews": 0,
        "negative_reviews": 0,
    }


total = stats.get(
    "total_reviews",
    0,
)

positive = stats.get(
    "positive_reviews",
    0,
)

negative = stats.get(
    "negative_reviews",
    0,
)


col1, col2, col3 = st.columns(3)

col1.metric(
    "Total Reviews",
    total,
)

col2.metric(
    "Positive Reviews",
    positive,
)

col3.metric(
    "Negative Reviews",
    negative,
)


# -------------------------------------------------
# Sentiment distribution
# -------------------------------------------------

st.divider()

st.subheader(
    "Sentiment Distribution"
)

chart_data = pd.DataFrame(
    {
        "Sentiment": [
            "Positive",
            "Negative",
        ],
        "Reviews": [
            positive,
            negative,
        ],
    }
)

st.bar_chart(
    chart_data,
    x="Sentiment",
    y="Reviews",
)


# -------------------------------------------------
# Ratios
# -------------------------------------------------

if total > 0:
    positive_percentage = (
        positive / total
    ) * 100

    negative_percentage = (
        negative / total
    ) * 100

    col1, col2 = st.columns(2)

    col1.metric(
        "Positive Rate",
        f"{positive_percentage:.2f}%",
    )

    col2.metric(
        "Negative Rate",
        f"{negative_percentage:.2f}%",
    )


# -------------------------------------------------
# Recent predictions
# -------------------------------------------------

st.divider()

st.subheader(
    "Recent Processed Reviews"
)

try:
    reviews = get_reviews()

except requests.RequestException:
    reviews = []


if not reviews:
    st.info(
        "No processed reviews available."
    )

else:
    dataframe = pd.DataFrame(
        reviews
    )

    if (
        "positive_probability"
        in dataframe.columns
    ):
        dataframe[
            "positive_probability"
        ] = (
            dataframe[
                "positive_probability"
            ]
            * 100
        ).round(2)

        dataframe = dataframe.rename(
            columns={
                "positive_probability":
                    "Positive Probability (%)"
            }
        )

    st.dataframe(
        dataframe,
        use_container_width=True,
        hide_index=True,
    )


# -------------------------------------------------
# Technology explanation
# -------------------------------------------------

st.divider()

st.subheader(
    "How the Backend Works"
)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        """
### Ingestion

**FastAPI**

Receives reviews from users.

**Kafka**

Buffers and distributes review events.
"""
    )


with col2:
    st.markdown(
        """
### Processing

**Spark Structured Streaming**

Consumes Kafka events.

**ML Model**

TF-IDF + Logistic Regression performs
sentiment inference.
"""
    )


with col3:
    st.markdown(
        """
### Storage

**PostgreSQL**

Stores permanent prediction history.

**Redis**

Stores counters, latest results,
and duplicate-event markers.
"""
    )