import pandas as pd

from amazon_sentiment.data import clean_text, load_reviews


def test_clean_text_normalises_whitespace():
    assert clean_text("  great\n product  ") == "great product"


def test_load_reviews_binarises_ratings(tmp_path):
    dataset = tmp_path / "reviews.csv"
    pd.DataFrame({"Review": ["Poor", "Excellent", None], "Sentiment": [2, 5, 4]}).to_csv(dataset, index=False)
    loaded = load_reviews(dataset)
    assert loaded.to_dict("records") == [
        {"Review": "Poor", "Sentiment": 0},
        {"Review": "Excellent", "Sentiment": 1},
    ]
