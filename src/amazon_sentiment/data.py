"""Dataset loading and text preparation."""

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = {"Review", "Sentiment"}


def clean_text(review: object) -> str:
    """Return a whitespace-normalised review suitable for a text vectorizer."""
    return " ".join(str(review).split())


def load_reviews(path: str | Path) -> pd.DataFrame:
    """Load reviews and map ratings 1–3 to negative and 4–5 to positive.

    Rows with missing text or ratings outside the expected 1–5 range are removed.
    """
    reviews = pd.read_csv(path)
    missing = REQUIRED_COLUMNS.difference(reviews.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing)}")

    reviews = reviews.loc[:, ["Review", "Sentiment"]].dropna().copy()
    reviews["Sentiment"] = pd.to_numeric(reviews["Sentiment"], errors="coerce")
    reviews = reviews[reviews["Sentiment"].between(1, 5)].copy()
    reviews["Review"] = reviews["Review"].map(clean_text)
    reviews = reviews[reviews["Review"].ne("")]
    reviews["Sentiment"] = (reviews["Sentiment"] >= 4).astype(int)
    return reviews.reset_index(drop=True)
