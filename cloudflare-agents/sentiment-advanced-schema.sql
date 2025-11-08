-- Advanced Sentiment Schema with Time-Series Analysis
-- Adds keywords, headlines, and sentiment derivatives (velocity, acceleration, jerk)

-- Update chaos_trades table with advanced sentiment fields
ALTER TABLE chaos_trades ADD COLUMN sentiment_keywords TEXT; -- JSON array of trending keywords at trade time
ALTER TABLE chaos_trades ADD COLUMN sentiment_headlines_1hr TEXT; -- JSON array of headlines from last 1 hour
ALTER TABLE chaos_trades ADD COLUMN sentiment_headlines_24hr TEXT; -- JSON array of headlines from last 24 hours
ALTER TABLE chaos_trades ADD COLUMN sentiment_direction TEXT; -- 'improving', 'declining', 'stable'

-- Sentiment derivatives (time-series analysis)
ALTER TABLE chaos_trades ADD COLUMN sentiment_velocity REAL; -- 1st derivative: change per hour (ΔS/Δt)
ALTER TABLE chaos_trades ADD COLUMN sentiment_acceleration REAL; -- 2nd derivative: change in velocity (Δ²S/Δt²)
ALTER TABLE chaos_trades ADD COLUMN sentiment_jerk REAL; -- 3rd derivative: change in acceleration (Δ³S/Δt³)

-- Historical sentiment for derivative calculations
ALTER TABLE chaos_trades ADD COLUMN sentiment_1hr_ago REAL; -- Sentiment 1 hour before trade
ALTER TABLE chaos_trades ADD COLUMN sentiment_4hr_ago REAL; -- Sentiment 4 hours before trade
ALTER TABLE chaos_trades ADD COLUMN sentiment_24hr_ago REAL; -- Sentiment 24 hours before trade

-- News volume and quality metrics
ALTER TABLE chaos_trades ADD COLUMN news_volume_1hr INTEGER; -- Number of articles in last hour
ALTER TABLE chaos_trades ADD COLUMN news_volume_24hr INTEGER; -- Number of articles in last 24 hours
ALTER TABLE chaos_trades ADD COLUMN news_sentiment_1hr REAL; -- Average sentiment of last hour's news
ALTER TABLE chaos_trades ADD COLUMN news_sentiment_24hr REAL; -- Average sentiment of last 24hr news
ALTER TABLE chaos_trades ADD COLUMN news_sentiment_spread REAL; -- Std dev of sentiment (disagreement)

-- Keyword trending analysis
CREATE TABLE IF NOT EXISTS sentiment_keywords (
    keyword_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    keyword TEXT NOT NULL,
    frequency INTEGER DEFAULT 1, -- How many articles mentioned it
    sentiment_score REAL, -- Average sentiment of articles with this keyword
    trending_score REAL, -- Frequency compared to baseline
    sources TEXT, -- JSON array of sources mentioning it
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sentiment_keywords_timestamp ON sentiment_keywords(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_sentiment_keywords_keyword ON sentiment_keywords(keyword);
CREATE INDEX IF NOT EXISTS idx_sentiment_keywords_trending ON sentiment_keywords(trending_score DESC);

-- Enhanced news articles table with more metadata
ALTER TABLE news_articles ADD COLUMN keywords TEXT; -- JSON array extracted from title/body
ALTER TABLE news_articles ADD COLUMN importance_score REAL; -- 0-1 based on source quality + engagement
ALTER TABLE news_articles ADD COLUMN category TEXT; -- 'regulation', 'adoption', 'technical', 'market', 'hack', etc.

-- Sentiment time-series snapshots (for derivative calculations)
CREATE TABLE IF NOT EXISTS sentiment_timeseries (
    timeseries_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    symbol TEXT NOT NULL, -- 'BTC', 'ETH', 'SOL', 'MARKET' (overall)

    -- Current values
    sentiment_value REAL NOT NULL,
    fear_greed_value INTEGER,

    -- Derivatives
    velocity REAL, -- Change per hour
    acceleration REAL, -- Change in velocity
    jerk REAL, -- Change in acceleration

    -- Classification
    direction TEXT, -- 'improving', 'declining', 'stable'
    regime TEXT, -- 'bull', 'bear', 'sideways', 'volatile'

    -- Supporting data
    news_volume INTEGER,
    news_sentiment REAL,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(timestamp, symbol)
);

CREATE INDEX IF NOT EXISTS idx_sentiment_timeseries_timestamp ON sentiment_timeseries(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_sentiment_timeseries_symbol ON sentiment_timeseries(symbol);

-- View: Pattern discovery with sentiment derivatives
CREATE VIEW IF NOT EXISTS chaos_trades_with_sentiment_derivatives AS
SELECT
    ct.*,
    -- Derivative classifications
    CASE
        WHEN ct.sentiment_velocity > 0.1 THEN 'rapidly_improving'
        WHEN ct.sentiment_velocity > 0.03 THEN 'improving'
        WHEN ct.sentiment_velocity < -0.1 THEN 'rapidly_declining'
        WHEN ct.sentiment_velocity < -0.03 THEN 'declining'
        ELSE 'stable'
    END as velocity_classification,

    CASE
        WHEN ct.sentiment_acceleration > 0.05 THEN 'accelerating_improvement'
        WHEN ct.sentiment_acceleration > 0 THEN 'slight_acceleration'
        WHEN ct.sentiment_acceleration < -0.05 THEN 'accelerating_decline'
        WHEN ct.sentiment_acceleration < 0 THEN 'slight_deceleration'
        ELSE 'constant_velocity'
    END as acceleration_classification,

    CASE
        WHEN ct.sentiment_jerk > 0 THEN 'jerk_positive'
        WHEN ct.sentiment_jerk < 0 THEN 'jerk_negative'
        ELSE 'jerk_neutral'
    END as jerk_classification
FROM chaos_trades ct
WHERE ct.sentiment_velocity IS NOT NULL;

-- View: High-value patterns with sentiment context
CREATE VIEW IF NOT EXISTS high_value_sentiment_patterns AS
SELECT
    -- Technical indicators
    entry_rsi_14,
    entry_macd_bullish_cross,
    entry_bb_at_lower,

    -- Sentiment context
    sentiment_fear_greed,
    sentiment_regime,
    sentiment_direction,
    sentiment_velocity,
    sentiment_acceleration,
    sentiment_jerk,

    -- News context
    news_volume_1hr,
    news_sentiment_1hr,

    -- Performance
    COUNT(*) as sample_size,
    SUM(profitable) as wins,
    CAST(SUM(profitable) AS REAL) / COUNT(*) as win_rate,
    AVG(pnl_pct) as avg_return,
    MAX(pnl_pct) as best_return,
    MIN(pnl_pct) as worst_return
FROM chaos_trades
WHERE sentiment_velocity IS NOT NULL
GROUP BY
    ROUND(entry_rsi_14 / 10) * 10,
    entry_macd_bullish_cross,
    entry_bb_at_lower,
    ROUND(sentiment_fear_greed / 10) * 10,
    sentiment_regime,
    sentiment_direction,
    ROUND(sentiment_velocity / 0.05) * 0.05,
    CASE
        WHEN sentiment_acceleration > 0.02 THEN 'strong_positive'
        WHEN sentiment_acceleration > 0 THEN 'weak_positive'
        WHEN sentiment_acceleration < -0.02 THEN 'strong_negative'
        WHEN sentiment_acceleration < 0 THEN 'weak_negative'
        ELSE 'neutral'
    END,
    CASE WHEN sentiment_jerk > 0 THEN 'positive' WHEN sentiment_jerk < 0 THEN 'negative' ELSE 'neutral' END,
    CASE WHEN news_volume_1hr > 5 THEN 'high' WHEN news_volume_1hr > 0 THEN 'low' ELSE 'none' END,
    ROUND(COALESCE(news_sentiment_1hr, 0) / 0.2) * 0.2
HAVING COUNT(*) >= 20
ORDER BY win_rate DESC, avg_return DESC;

-- Comments
COMMENT ON COLUMN chaos_trades.sentiment_velocity IS '1st derivative: rate of sentiment change per hour (positive = improving)';
COMMENT ON COLUMN chaos_trades.sentiment_acceleration IS '2nd derivative: rate of change of velocity (positive = improvement accelerating)';
COMMENT ON COLUMN chaos_trades.sentiment_jerk IS '3rd derivative: rate of change of acceleration (positive = acceleration increasing)';
COMMENT ON COLUMN chaos_trades.sentiment_keywords IS 'JSON array of trending keywords at time of trade (e.g., ["regulation", "ETF", "hack"])';
COMMENT ON COLUMN chaos_trades.sentiment_headlines_1hr IS 'JSON array of headlines from 1 hour before trade';
COMMENT ON COLUMN chaos_trades.sentiment_headlines_24hr IS 'JSON array of headlines from 24 hours before trade';

-- Example queries for pattern discovery:

-- Find patterns where sentiment is improving but price is falling (contrarian opportunity)
-- SELECT * FROM chaos_trades
-- WHERE sentiment_velocity > 0.05
--   AND entry_momentum_1 < -0.01
--   AND profitable = 1;

-- Find patterns where sentiment acceleration is positive (early stage rally)
-- SELECT * FROM chaos_trades
-- WHERE sentiment_acceleration > 0.02
--   AND entry_rsi_14 < 40
--   AND profitable = 1;

-- Find patterns where jerk is negative (momentum fading)
-- SELECT * FROM chaos_trades
-- WHERE sentiment_jerk < -0.01
--   AND sentiment_velocity > 0
--   AND profitable = 0;  -- These failed trades

-- Find patterns with high news volume and positive sentiment
-- SELECT * FROM chaos_trades
-- WHERE news_volume_1hr >= 5
--   AND news_sentiment_1hr > 0.5
--   AND profitable = 1;
