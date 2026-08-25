"""Model construction and evaluation helpers."""

from __future__ import annotations

from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.pipeline import Pipeline


def build_pipeline() -> Pipeline:
    """Build an interpretable TF-IDF + logistic-regression classifier."""
    return Pipeline(
        steps=[
            ("tfidf", TfidfVectorizer(stop_words="english", max_features=5_000, ngram_range=(1, 2))),
            ("classifier", LogisticRegression(max_iter=1_000, class_weight="balanced", random_state=42)),
        ]
    )


def evaluate(model: Pipeline, texts: Any, labels: Any) -> dict[str, Any]:
    """Return serialisable evaluation metrics for a held-out test split."""
    predictions = model.predict(texts)
    return {
        "accuracy": round(float(accuracy_score(labels, predictions)), 4),
        "classification_report": classification_report(
            labels,
            predictions,
            target_names=["negative", "positive"],
            output_dict=True,
            zero_division=0,
        ),
    }
