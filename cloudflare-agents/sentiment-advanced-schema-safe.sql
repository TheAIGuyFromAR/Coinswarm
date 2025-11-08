-- Advanced Sentiment Schema with Time-Series Analysis (SAFE VERSION)
-- Adds keywords, headlines, and sentiment derivatives (velocity, acceleration, jerk)
-- IMPROVED: Uses INT timestamps, adds CHECK constraints, migration tracking

-- Migration tracking (ensure schema_migrations table exists)
CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_id TEXT PRIMARY KEY,
    applied_at INTEGER DEFAULT (cast(strftime('%s', 'now') as integer)),
    description TEXT,
    status TEXT DEFAULT 'success'
);

-- Update chaos_trades table with advanced sentiment fields
-- Note: These ALTER statements will fail if columns exist (expected behavior)

ALTER TABLE chaos_trades ADD COLUMN sentiment_keywords TEXT; -- JSON array of trending keywords at trade time
ALTER TABLE chaos_trades ADD COLUMN sentiment_headlines_1hr TEXT; -- JSON array of headlines from last 1 hour
ALTER TABLE chaos_trades ADD COLUMN sentiment_headlines_24hr TEXT; -- JSON array of headlines from last 24 hours
ALTER TABLE chaos_trades ADD COLUMN sentiment_direction TEXT CHECK (sentiment_direction IN ('improving', 'declining', 'stable')); -- 'improving', 'declining', 'stable'

-- Sentiment derivatives (time-series analysis)
ALTER TABLE chaos_trades ADD COLUMN sentiment_velocity REAL; -- 1st derivative: change per hour (ΔS/Δt)
ALTER TABLE chaos_trades ADD COLUMN sentiment_acceleration REAL; -- 2nd derivative: change in velocity (Δ²S/Δt²)
ALTER TABLE chaos_trades ADD COLUMN sentiment_jerk REAL; -- 3rd derivative: change in acceleration (Δ³S/Δt³)

-- Historical sentiment for derivative calculations
ALTER TABLE chaos_trades ADD COLUMN sentiment_1hr_ago REAL CHECK (sentiment_1hr_ago >= -1 AND sentiment_1hr_ago <= 1); -- Sentiment 1 hour before trade
ALTER TABLE chaos_trades ADD COLUMN sentiment_4hr_ago REAL CHECK (sentiment_4hr_ago >= -1 AND sentiment_4hr_ago <= 1); -- Sentiment 4 hours before trade
ALTER TABLE chaos_trades ADD COLUMN sentiment_24hr_ago REAL CHECK (sentiment_24hr_ago >= -1 AND sentiment_24hr_ago <= 1); -- Sentiment 24 hours before trade

-- News volume and quality metrics
ALTER TABLE chaos_trades ADD COLUMN news_volume_1hr INTEGER CHECK (news_volume_1hr >= 0); -- Number of articles in last hour
ALTER TABLE chaos_trades ADD COLUMN news_volume_24hr INTEGER CHECK (news_volume_24hr >= 0); -- Number of articles in last 24 hours
ALTER TABLE chaos_trades ADD COLUMN news_sentiment_1hr REAL CHECK (news_sentiment_1hr >= -1 AND news_sentiment_1hr <= 1); -- Average sentiment of last hour's news
ALTER TABLE chaos_trades ADD COLUMN news_sentiment_24hr REAL CHECK (news_sentiment_24hr >= -1 AND news_sentiment_24hr <= 1); -- Average sentiment of last 24hr news
ALTER TABLE chaos_trades ADD COLUMN news_sentiment_spread REAL CHECK (news_sentiment_spread >= 0); -- Std dev of sentiment (disagreement)

-- Record migration
INSERT OR IGNORE INTO schema_migrations (migration_id, description)
VALUES ('sentiment-advanced-columns-2025-11-08', 'Add advanced sentiment columns to chaos_trades');

-- Keyword trending analysis (with INTEGER timestamps)
CREATE TABLE IF NOT EXISTS sentiment_keywords (
    keyword_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL, -- Unix timestamp
    keyword TEXT NOT NULL,
    frequency INTEGER DEFAULT 1 CHECK (frequency > 0), -- How many articles mentioned it
    sentiment_score REAL CHECK (sentiment_score >= -1 AND sentiment_score <= 1), -- Average sentiment of articles with this keyword
    trending_score REAL, -- Frequency compared to baseline
    sources TEXT, -- JSON array of sources mentioning it
    created_at INTEGER DEFAULT (cast(strftime('%s', 'now') as integer)),

    -- Prevent exact duplicates
    UNIQUE(timestamp, keyword)
);

CREATE INDEX IF NOT EXISTS idx_sentiment_keywords_timestamp ON sentiment_keywords(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_sentiment_keywords_keyword ON sentiment_keywords(keyword);
CREATE INDEX IF NOT EXISTS idx_sentiment_keywords_trending ON sentiment_keywords(trending_score DESC);
CREATE INDEX IF NOT EXISTS idx_sentiment_keywords_created ON sentiment_keywords(created_at DESC);

-- Enhanced news articles table with more metadata
-- Note: These ALTER statements add to the existing news_articles table

ALTER TABLE news_articles ADD COLUMN keywords TEXT; -- JSON array extracted from title/body
ALTER TABLE news_articles ADD COLUMN importance_score REAL CHECK (importance_score >= 0 AND importance_score <= 1); -- 0-1 based on source quality + engagement
ALTER TABLE news_articles ADD COLUMN category TEXT CHECK (category IN ('regulation', 'adoption', 'technical', 'market', 'hack', 'security', 'defi', 'nft', 'other')); -- Article category

-- Record migration
INSERT OR IGNORE INTO schema_migrations (migration_id, description)
VALUES ('news-articles-enhancements-2025-11-08', 'Add keywords, importance, category to news_articles');

-- Sentiment time-series snapshots (for derivative calculations)
CREATE TABLE IF NOT EXISTS sentiment_timeseries (
    timeseries_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL, -- Unix timestamp
    symbol TEXT NOT NULL CHECK (symbol IN ('BTC', 'ETH', 'SOL', 'MARKET')), -- 'BTC', 'ETH', 'SOL', 'MARKET' (overall)

    -- Current values
    sentiment_value REAL NOT NULL CHECK (sentiment_value >= -1 AND sentiment_value <= 1),
    fear_greed_value INTEGER CHECK (fear_greed_value >= 0 AND fear_greed_value <= 100),

    -- Derivatives
    velocity REAL, -- Change per hour
    acceleration REAL, -- Change in velocity
    jerk REAL, -- Change in acceleration

    -- Classification
    direction TEXT CHECK (direction IN ('improving', 'declining', 'stable')), -- 'improving', 'declining', 'stable'
    regime TEXT CHECK (regime IN ('bull', 'bear', 'sideways', 'volatile')), -- 'bull', 'bear', 'sideways', 'volatile'

    -- Supporting data
    news_volume INTEGER CHECK (news_volume >= 0),
    news_sentiment REAL CHECK (news_sentiment >= -1 AND news_sentiment <= 1),

    created_at INTEGER DEFAULT (cast(strftime('%s', 'now') as integer)),

    -- Prevent duplicates
    UNIQUE(timestamp, symbol)
);

CREATE INDEX IF NOT EXISTS idx_sentiment_timeseries_timestamp ON sentiment_timeseries(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_sentiment_timeseries_symbol ON sentiment_timeseries(symbol);
CREATE INDEX IF NOT EXISTS idx_sentiment_timeseries_symbol_time ON sentiment_timeseries(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_sentiment_timeseries_created ON sentiment_timeseries(created_at DESC);

-- Sentiment derivative calculation helpers
CREATE TABLE IF NOT EXISTS sentiment_derivative_calculations (
    calc_id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    calculation_timestamp INTEGER NOT NULL,
    lookback_window_hours INTEGER NOT NULL, -- How far back we looked (1, 4, 24)
    data_points_used INTEGER NOT NULL, -- How many snapshots we used
    velocity REAL,
    acceleration REAL,
    jerk REAL,
    confidence REAL CHECK (confidence >= 0 AND confidence <= 1), -- Based on data quality
    created_at INTEGER DEFAULT (cast(strftime('%s', 'now') as integer))
);

CREATE INDEX IF NOT EXISTS idx_derivative_calc_symbol ON sentiment_derivative_calculations(symbol);
CREATE INDEX IF NOT EXISTS idx_derivative_calc_time ON sentiment_derivative_calculations(calculation_timestamp DESC);

-- View: Pattern discovery with sentiment derivatives
CREATE VIEW IF NOT EXISTS chaos_trades_with_sentiment_derivatives AS
SELECT
    t.*,
    -- Calculate velocity if not stored (fallback)
    COALESCE(t.sentiment_velocity,
        CASE
            WHEN t.sentiment_1hr_ago IS NOT NULL
            THEN (t.sentiment_overall - t.sentiment_1hr_ago) / 1.0
            ELSE NULL
        END
    ) as calculated_velocity,

    -- Calculate acceleration if not stored (fallback)
    COALESCE(t.sentiment_acceleration,
        CASE
            WHEN t.sentiment_1hr_ago IS NOT NULL AND t.sentiment_4hr_ago IS NOT NULL
            THEN ((t.sentiment_overall - t.sentiment_1hr_ago) - (t.sentiment_1hr_ago - t.sentiment_4hr_ago)) / 3.0
            ELSE NULL
        END
    ) as calculated_acceleration,

    -- Classify sentiment momentum
    CASE
        WHEN t.sentiment_velocity > 0.1 THEN 'strongly_improving'
        WHEN t.sentiment_velocity > 0.02 THEN 'improving'
        WHEN t.sentiment_velocity > -0.02 THEN 'stable'
        WHEN t.sentiment_velocity > -0.1 THEN 'declining'
        ELSE 'strongly_declining'
    END as sentiment_momentum_class,

    -- News volume classification
    CASE
        WHEN t.news_volume_1hr >= 10 THEN 'high'
        WHEN t.news_volume_1hr >= 5 THEN 'medium'
        WHEN t.news_volume_1hr >= 1 THEN 'low'
        ELSE 'none'
    END as news_volume_class

FROM chaos_trades t
WHERE t.sentiment_overall IS NOT NULL;

-- View: Best performing sentiment derivative patterns
CREATE VIEW IF NOT EXISTS sentiment_derivative_performance AS
SELECT
    -- Derivative buckets
    CASE
        WHEN sentiment_velocity > 0.1 THEN 'strong_positive_velocity'
        WHEN sentiment_velocity > 0.02 THEN 'positive_velocity'
        WHEN sentiment_velocity > -0.02 THEN 'stable_velocity'
        WHEN sentiment_velocity > -0.1 THEN 'negative_velocity'
        ELSE 'strong_negative_velocity'
    END as velocity_bucket,

    CASE
        WHEN sentiment_acceleration > 0.05 THEN 'accelerating'
        WHEN sentiment_acceleration > -0.05 THEN 'stable'
        ELSE 'decelerating'
    END as acceleration_bucket,

    sentiment_regime,
    sentiment_direction,

    -- Performance metrics
    COUNT(*) as total_trades,
    SUM(CASE WHEN profitable = 1 THEN 1 ELSE 0 END) as winning_trades,
    CAST(SUM(CASE WHEN profitable = 1 THEN 1 ELSE 0 END) AS REAL) / COUNT(*) as win_rate,
    AVG(pnl_pct) as avg_return,
    MAX(pnl_pct) as best_return,
    MIN(pnl_pct) as worst_return,
    AVG(CASE WHEN profitable = 1 THEN pnl_pct ELSE NULL END) as avg_winning_return,
    AVG(CASE WHEN profitable = 0 THEN pnl_pct ELSE NULL END) as avg_losing_return

FROM chaos_trades
WHERE sentiment_velocity IS NOT NULL
  AND sentiment_overall IS NOT NULL
GROUP BY velocity_bucket, acceleration_bucket, sentiment_regime, sentiment_direction
HAVING COUNT(*) >= 10 -- At least 10 samples
ORDER BY win_rate DESC;

-- View: News sentiment impact analysis
CREATE VIEW IF NOT EXISTS news_sentiment_impact AS
SELECT
    CASE
        WHEN news_volume_1hr >= 10 THEN 'high_volume'
        WHEN news_volume_1hr >= 5 THEN 'medium_volume'
        WHEN news_volume_1hr >= 1 THEN 'low_volume'
        ELSE 'no_news'
    END as news_volume_class,

    CASE
        WHEN news_sentiment_1hr > 0.2 THEN 'very_positive'
        WHEN news_sentiment_1hr > 0.05 THEN 'positive'
        WHEN news_sentiment_1hr > -0.05 THEN 'neutral'
        WHEN news_sentiment_1hr > -0.2 THEN 'negative'
        ELSE 'very_negative'
    END as news_sentiment_class,

    CASE
        WHEN news_sentiment_spread > 0.5 THEN 'high_disagreement'
        WHEN news_sentiment_spread > 0.2 THEN 'moderate_disagreement'
        ELSE 'low_disagreement'
    END as news_disagreement,

    -- Performance
    COUNT(*) as total_trades,
    SUM(CASE WHEN profitable = 1 THEN 1 ELSE 0 END) as wins,
    CAST(SUM(CASE WHEN profitable = 1 THEN 1 ELSE 0 END) AS REAL) / COUNT(*) as win_rate,
    AVG(pnl_pct) as avg_return

FROM chaos_trades
WHERE news_volume_1hr IS NOT NULL
  AND news_sentiment_1hr IS NOT NULL
GROUP BY news_volume_class, news_sentiment_class, news_disagreement
HAVING COUNT(*) >= 5
ORDER BY win_rate DESC;

-- View: Trending keywords performance
CREATE VIEW IF NOT EXISTS trending_keywords_performance AS
SELECT
    k.keyword,
    k.trending_score,
    COUNT(DISTINCT t.trade_id) as trades_with_keyword,
    SUM(CASE WHEN t.profitable = 1 THEN 1 ELSE 0 END) as winning_trades,
    CAST(SUM(CASE WHEN t.profitable = 1 THEN 1 ELSE 0 END) AS REAL) / COUNT(*) as win_rate,
    AVG(t.pnl_pct) as avg_return
FROM sentiment_keywords k
LEFT JOIN chaos_trades t ON t.sentiment_keywords LIKE '%' || k.keyword || '%'
WHERE k.trending_score > 1.5 -- Only significantly trending keywords
  AND t.trade_id IS NOT NULL
GROUP BY k.keyword, k.trending_score
HAVING trades_with_keyword >= 3
ORDER BY win_rate DESC;

-- Record schema version
INSERT OR IGNORE INTO schema_migrations (migration_id, description)
VALUES ('sentiment-advanced-schema-safe-2025-11-08', 'Advanced sentiment schema with derivatives, INTEGER timestamps, and constraints');

-- Migration completion log
INSERT OR IGNORE INTO schema_migrations (migration_id, description, status)
VALUES (
    'sentiment-advanced-complete-2025-11-08',
    'Advanced sentiment schema fully applied with time-series analysis, derivatives, and performance views',
    'success'
);
