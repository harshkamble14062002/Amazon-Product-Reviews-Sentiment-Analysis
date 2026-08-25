"""A minimal public-facing Streamlit demo."""

from pathlib import Path
import sys

import joblib
import streamlit as st

# Streamlit runs this file from the repository root; expose the src-layout package.
sys.path.insert(0, str(Path(__file__).parent / "src"))

from amazon_sentiment.data import load_reviews
from amazon_sentiment.model import build_pipeline

MODEL_PATH = Path("artifacts/sentiment_pipeline.joblib")
DATA_PATH = Path("AmazonReview.csv")

st.set_page_config(page_title="Amazon Review Sentiment Studio", page_icon="💬")
st.title("Amazon Review Sentiment Studio")
st.caption("An explainable TF-IDF + Logistic Regression baseline for product-review sentiment.")

@st.cache_resource
def load_model():
    """Load the saved pipeline or train it once for a fresh cloud deployment."""
    if MODEL_PATH.exists():
        return joblib.load(MODEL_PATH)

    with st.spinner("Preparing the sentiment model for its first run…"):
        data = load_reviews(DATA_PATH)
        model = build_pipeline()
        model.fit(data["Review"], data["Sentiment"])
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, MODEL_PATH)
    return model


review = st.text_area("Paste a product review", placeholder="The delivery was fast and the product exceeded my expectations.")
if st.button("Analyse sentiment", type="primary", disabled=not review.strip()):
    probability = load_model().predict_proba([review])[0][1]
    label = "Positive" if probability >= 0.5 else "Negative"
    st.metric("Prediction", label, f"{probability:.0%} positive probability")
