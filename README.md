# Amazon Review Sentiment Studio

An end-to-end, reproducible NLP baseline that classifies Amazon product reviews as **negative** (ratings 1–3) or **positive** (ratings 4–5). It turns the original exploratory notebook into a small, reviewable machine-learning project with a training command, test suite, and interactive demo.

> **Portfolio framing:** this project demonstrates practical text preprocessing, feature engineering with TF-IDF, model evaluation, and lightweight deployment—not a production-quality sentiment service.

## Why this project exists

Product reviews are high-volume and unstructured. This project shows how a transparent baseline can turn review text into an immediately useful signal, while keeping the implementation simple enough to inspect and improve.

## What is included

```
.
├── AmazonReview.csv                         # Original 25,000-review dataset
├── Amazon_Product_Reviews_Sentiment_Analysis.ipynb  # Original exploratory work
├── src/amazon_sentiment/                    # Reusable loading, modelling, and training code
├── tests/                                   # Data-preparation tests
├── app.py                                   # Streamlit demo
└── .github/workflows/tests.yml              # CI on pushes and pull requests
```

## Approach

1. Validate and clean the `Review` and `Sentiment` columns.
2. Map 1–3 star ratings to negative and 4–5 to positive.
3. Split data using a stratified 80/20 train/test split with a fixed seed.
4. Convert text to TF-IDF features (unigrams and bigrams).
5. Train a class-balanced Logistic Regression classifier and save its held-out metrics.

TF-IDF + Logistic Regression is deliberate: it is fast, reproducible, and easier to reason about than a black-box model. The generated metrics are never hard-coded in this README; run training to report the actual result for your environment and data.

## Quick start

Requires Python 3.10+.

```bash
git clone https://github.com/harshkamble14062002/Amazon-Product-Reviews-Sentiment-Analysis.git
cd Amazon-Product-Reviews-Sentiment-Analysis
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
PYTHONPATH=src python -m amazon_sentiment.train
PYTHONPATH=src streamlit run app.py
```

Training writes a serialised model and `metrics.json` to `artifacts/`; that directory is intentionally excluded from version control. Open the Streamlit URL printed in your terminal and paste a review to test the classifier.

## Responsible use and limitations

- Ratings are treated as sentiment labels, which is a useful proxy but not a perfect measure of a writer's attitude.
- The dataset may not represent all products, languages, dialects, or current Amazon reviews.
- The model does not understand sarcasm, context outside the review, or nuanced mixed sentiment.
- Do not use this baseline for high-impact or automated decisions about people.

## Next improvements

- Add data provenance and licence information before redistributing the dataset.
- Compare against a linear SVM and a transformer baseline using the same split.
- Add error analysis for short, mixed, and product-specific reviews.
- Deploy the Streamlit app and add a screenshot/link here.

## License

Code is released under the [MIT License](LICENSE). Confirm that you have the right to publish and redistribute the included dataset before using it outside this repository.
