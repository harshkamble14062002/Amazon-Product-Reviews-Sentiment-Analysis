"""A minimal public-facing Streamlit demo."""

from pathlib import Path

import joblib
import streamlit as st

MODEL_PATH = Path("artifacts/sentiment_pipeline.joblib")

st.set_page_config(page_title="Amazon Review Sentiment Studio", page_icon="💬")
st.title("Amazon Review Sentiment Studio")
st.caption("An explainable TF-IDF + Logistic Regression baseline for product-review sentiment.")

if not MODEL_PATH.exists():
    st.warning("Train the model first: `python -m amazon_sentiment.train`")
    st.stop()

@st.cache_resource
def load_model():
    return joblib.load(MODEL_PATH)


review = st.text_area("Paste a product review", placeholder="The delivery was fast and the product exceeded my expectations.")
if st.button("Analyse sentiment", type="primary", disabled=not review.strip()):
    probability = load_model().predict_proba([review])[0][1]
    label = "Positive" if probability >= 0.5 else "Negative"
    st.metric("Prediction", label, f"{probability:.0%} positive probability")
    st.caption("This is a baseline classifier; use it as an analytical aid, not a decision-making system.")
