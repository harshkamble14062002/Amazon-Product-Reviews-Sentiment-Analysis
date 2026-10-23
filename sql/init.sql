CREATE TABLE IF NOT EXISTS reviews (
    id BIGSERIAL PRIMARY KEY,
    review_id VARCHAR(100) UNIQUE NOT NULL,
    product_id VARCHAR(100) NOT NULL,
    review_text TEXT NOT NULL,
    sentiment VARCHAR(20),
    positive_probability DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reviews_product_id
ON reviews(product_id);

CREATE INDEX IF NOT EXISTS idx_reviews_sentiment
ON reviews(sentiment);
