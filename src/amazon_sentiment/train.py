"""Command-line training entry point."""

import argparse
import json
from pathlib import Path

import joblib
from sklearn.model_selection import train_test_split

from .data import load_reviews
from .model import build_pipeline, evaluate


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the Amazon review sentiment baseline.")
    parser.add_argument("--data", default="AmazonReview.csv", help="Path to a CSV with Review and Sentiment columns.")
    parser.add_argument("--output-dir", default="artifacts", help="Directory for the trained model and metrics.")
    args = parser.parse_args()

    data = load_reviews(args.data)
    x_train, x_test, y_train, y_test = train_test_split(
        data["Review"], data["Sentiment"], test_size=0.2, random_state=42, stratify=data["Sentiment"]
    )
    model = build_pipeline()
    model.fit(x_train, y_train)
    metrics = evaluate(model, x_test, y_test)
    metrics.update({"train_rows": len(x_train), "test_rows": len(x_test)})

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_dir / "sentiment_pipeline.joblib")
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
