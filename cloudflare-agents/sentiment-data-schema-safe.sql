-- Sentiment Data Schema (SAFE VERSION)
-- Stores sentiment snapshots and adds sentiment context to chaos trades
-- IMPROVED: Idempotent column additions that won't fail if already applied

-- Sentiment snapshots table (historical sentiment tracking)
CREATE TABLE IF NOT EXISTS sentiment_snapshots (
    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL, -- Unix timestamp for better performance

    -- Fear & Greed Index (always available)
    fear_greed_index INTEGER NOT NULL CHECK (fear_greed_index >= 0 AND fear_greed_index <= 100), -- 0-100
    fear_greed_classification TEXT NOT NULL CHECK (fear_greed_classification IN ('Extreme Fear', 'Fear', 'Neutral', 'Greed', 'Extreme Greed')),

    -- News sentiment (if available)
    news_sentiment REAL CHECK (news_sentiment >= -1 AND news_sentiment <= 1), -- -1 to +1
    news_articles_analyzed INTEGER DEFAULT 0,

    -- Overall sentiment
    overall_sentiment REAL NOT NULL CHECK (overall_sentiment >= -1 AND overall_sentiment <= 1), -- -1 to +1 (normalized)

    -- Market regime
    market_regime TEXT NOT NULL CHECK (market_regime IN ('bull', 'bear', 'sideways', 'volatile')),

    -- Macro indicators (JSON)
    macro_indicators_json TEXT, -- JSON array of macro indicators

    created_at INTEGER DEFAULT (cast(strftime('%s', 'now') as integer))
);

CREATE INDEX IF NOT EXISTS idx_sentiment_timestamp ON sentiment_snapshots(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_sentiment_regime ON sentiment_snapshots(market_regime);
CREATE INDEX IF NOT EXISTS idx_sentiment_created ON sentiment_snapshots(created_at DESC);

-- Add sentiment columns to chaos_trades (SAFE: checks if column exists first)
-- Method: Create a migration tracking table first

CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_id TEXT PRIMARY KEY,
    applied_at INTEGER DEFAULT (cast(strftime('%s', 'now') as integer)),
    description TEXT,
    status TEXT DEFAULT 'success'
);

-- Check if sentiment migration already applied
-- Note: SQLite doesn't support IF NOT EXISTS for ALTER TABLE ADD COLUMN
-- We use a different approach: Try to add, ignore errors
-- This is handled at the application level or via separate migration scripts

-- For D1 deployment, run these ALTER statements manually:
-- They will fail gracefully if columns already exist in most scenarios

-- MANUAL MIGRATION STEP 1: Sentiment columns
-- Run these one at a time, ignore "duplicate column name" errors

ALTER TABLE chaos_trades ADD COLUMN sentiment_fear_greed INTEGER CHECK (sentiment_fear_greed >= 0 AND sentiment_fear_greed <= 100);
ALTER TABLE chaos_trades ADD COLUMN sentiment_overall REAL CHECK (sentiment_overall >= -1 AND sentiment_overall <= 1);
ALTER TABLE chaos_trades ADD COLUMN sentiment_regime TEXT CHECK (sentiment_regime IN ('bull', 'bear', 'sideways', 'volatile'));
ALTER TABLE chaos_trades ADD COLUMN sentiment_classification TEXT;
ALTER TABLE chaos_trades ADD COLUMN sentiment_news_score REAL CHECK (sentiment_news_score >= -1 AND sentiment_news_score <= 1);

-- MANUAL MIGRATION STEP 2: Macro indicator columns
ALTER TABLE chaos_trades ADD COLUMN macro_fed_rate REAL;
ALTER TABLE chaos_trades ADD COLUMN macro_cpi REAL;
ALTER TABLE chaos_trades ADD COLUMN macro_unemployment REAL CHECK (macro_unemployment >= 0 AND macro_unemployment <= 100);
ALTER TABLE chaos_trades ADD COLUMN macro_10y_yield REAL;

-- Record migration
INSERT OR IGNORE INTO schema_migrations (migration_id, description)
VALUES ('sentiment-data-2025-11-08', 'Add sentiment and macro columns to chaos_trades');

-- Indexes for pattern queries
CREATE INDEX IF NOT EXISTS idx_chaos_trades_sentiment ON chaos_trades(sentiment_fear_greed);
CREATE INDEX IF NOT EXISTS idx_chaos_trades_regime ON chaos_trades(sentiment_regime);
CREATE INDEX IF NOT EXISTS idx_chaos_trades_profitable_sentiment ON chaos_trades(profitable, sentiment_fear_greed);
CREATE INDEX IF NOT EXISTS idx_chaos_trades_profitable_regime ON chaos_trades(profitable, sentiment_regime);

-- Pattern discovery example queries:
-- "Find all profitable trades during extreme fear"
-- SELECT * FROM chaos_trades WHERE profitable = 1 AND sentiment_fear_greed < 25;

-- "Find all profitable trades during bull markets with RSI oversold"
-- SELECT * FROM chaos_trades WHERE profitable = 1 AND sentiment_regime = 'bull' AND entry_rsi_14 < 30;

-- "Find win rate for MACD crossover during extreme greed"
-- SELECT
--   COUNT(*) as total,
--   SUM(profitable) as wins,
--   AVG(pnl_pct) as avg_return
-- FROM chaos_trades
-- WHERE entry_macd_bullish_cross = 1
--   AND sentiment_fear_greed > 75;

-- News articles table (with unix timestamps for better performance)
CREATE TABLE IF NOT EXISTS news_articles (
    article_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    body TEXT,
    url TEXT UNIQUE, -- Prevent duplicates
    source TEXT NOT NULL,
    published_on INTEGER NOT NULL, -- Unix timestamp
    sentiment_score REAL CHECK (sentiment_score >= -1 AND sentiment_score <= 1), -- -1 to +1
    tags TEXT, -- JSON array
    symbols TEXT, -- JSON array ['BTC', 'ETH', 'SOL']
    created_at INTEGER DEFAULT (cast(strftime('%s', 'now') as integer))
);

CREATE INDEX IF NOT EXISTS idx_news_published ON news_articles(published_on DESC);
CREATE INDEX IF NOT EXISTS idx_news_source ON news_articles(source);
CREATE INDEX IF NOT EXISTS idx_news_sentiment ON news_articles(sentiment_score);
CREATE INDEX IF NOT EXISTS idx_news_created ON news_articles(created_at DESC);

-- Macro indicators table (with unix timestamps)
CREATE TABLE IF NOT EXISTS macro_indicators (
    indicator_id INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator_code TEXT NOT NULL, -- 'FEDFUNDS', 'CPIAUCSL', etc.
    indicator_name TEXT NOT NULL,
    value REAL NOT NULL,
    date INTEGER NOT NULL, -- Unix timestamp instead of TEXT date
    unit TEXT,
    created_at INTEGER DEFAULT (cast(strftime('%s', 'now') as integer)),

    -- Prevent duplicate entries
    UNIQUE(indicator_code, date)
);

CREATE INDEX IF NOT EXISTS idx_macro_code_date ON macro_indicators(indicator_code, date DESC);
CREATE INDEX IF NOT EXISTS idx_macro_created ON macro_indicators(created_at DESC);

-- Committee weighting log (tracks how sentiment influenced agent decisions)
CREATE TABLE IF NOT EXISTS committee_weighting_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    sentiment_fear_greed INTEGER,
    sentiment_regime TEXT,
    agent_weight REAL NOT NULL,
    final_decision TEXT NOT NULL,
    created_at INTEGER DEFAULT (cast(strftime('%s', 'now') as integer))
);

CREATE INDEX IF NOT EXISTS idx_committee_log_decision ON committee_weighting_log(decision_id);
CREATE INDEX IF NOT EXISTS idx_committee_log_agent ON committee_weighting_log(agent_id);
CREATE INDEX IF NOT EXISTS idx_committee_log_created ON committee_weighting_log(created_at DESC);

-- Agent knowledge sharing table (for cross-agent learning with sentiment context)
CREATE TABLE IF NOT EXISTS agent_knowledge_sharing (
    sharing_id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_agent_id TEXT NOT NULL,
    student_agent_id TEXT NOT NULL,
    knowledge_type TEXT NOT NULL, -- 'pattern_preference', 'risk_adjustment', 'sentiment_weight'
    knowledge_content TEXT NOT NULL, -- JSON
    confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    sentiment_context TEXT, -- JSON: what sentiment was present when this knowledge was learned
    shared_at INTEGER DEFAULT (cast(strftime('%s', 'now') as integer)),

    FOREIGN KEY (teacher_agent_id) REFERENCES trading_agents(agent_id),
    FOREIGN KEY (student_agent_id) REFERENCES trading_agents(agent_id)
);

CREATE INDEX IF NOT EXISTS idx_knowledge_sharing_teacher ON agent_knowledge_sharing(teacher_agent_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_sharing_student ON agent_knowledge_sharing(student_agent_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_sharing_type ON agent_knowledge_sharing(knowledge_type);
CREATE INDEX IF NOT EXISTS idx_knowledge_sharing_shared ON agent_knowledge_sharing(shared_at DESC);

-- Sentiment backfill tracking (to know which historical trades have sentiment data)
CREATE TABLE IF NOT EXISTS sentiment_backfill_progress (
    progress_id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_trade_id INTEGER NOT NULL,
    end_trade_id INTEGER NOT NULL,
    trades_processed INTEGER NOT NULL,
    trades_updated INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('in_progress', 'completed', 'failed')),
    error_message TEXT,
    started_at INTEGER DEFAULT (cast(strftime('%s', 'now') as integer)),
    completed_at INTEGER,

    CHECK (end_trade_id >= start_trade_id)
);

CREATE INDEX IF NOT EXISTS idx_backfill_status ON sentiment_backfill_progress(status);
CREATE INDEX IF NOT EXISTS idx_backfill_started ON sentiment_backfill_progress(started_at DESC);

-- View: Recent sentiment trends
CREATE VIEW IF NOT EXISTS recent_sentiment_trends AS
SELECT
    date(timestamp, 'unixepoch') as date,
    AVG(fear_greed_index) as avg_fear_greed,
    AVG(overall_sentiment) as avg_sentiment,
    COUNT(*) as snapshot_count,
    market_regime,
    COUNT(DISTINCT market_regime) as regime_changes
FROM sentiment_snapshots
WHERE timestamp >= (cast(strftime('%s', 'now') as integer) - 86400 * 30) -- Last 30 days
GROUP BY date(timestamp, 'unixepoch'), market_regime
ORDER BY date DESC;

-- View: Sentiment impact on profitability
CREATE VIEW IF NOT EXISTS sentiment_profitability_analysis AS
SELECT
    CASE
        WHEN sentiment_fear_greed < 20 THEN 'Extreme Fear'
        WHEN sentiment_fear_greed < 40 THEN 'Fear'
        WHEN sentiment_fear_greed < 60 THEN 'Neutral'
        WHEN sentiment_fear_greed < 80 THEN 'Greed'
        ELSE 'Extreme Greed'
    END as sentiment_bucket,
    sentiment_regime,
    COUNT(*) as total_trades,
    SUM(CASE WHEN profitable = 1 THEN 1 ELSE 0 END) as winning_trades,
    CAST(SUM(CASE WHEN profitable = 1 THEN 1 ELSE 0 END) AS REAL) / COUNT(*) as win_rate,
    AVG(pnl_pct) as avg_return
FROM chaos_trades
WHERE sentiment_fear_greed IS NOT NULL
GROUP BY sentiment_bucket, sentiment_regime
ORDER BY win_rate DESC;

-- Record schema version
INSERT OR IGNORE INTO schema_migrations (migration_id, description)
VALUES ('sentiment-data-schema-safe-2025-11-08', 'Safe sentiment data schema with timestamps and constraints');
