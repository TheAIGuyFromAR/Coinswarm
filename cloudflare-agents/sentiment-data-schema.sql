-- Sentiment Data Schema
-- Stores sentiment snapshots and adds sentiment context to chaos trades

-- Sentiment snapshots table (historical sentiment tracking)
CREATE TABLE IF NOT EXISTS sentiment_snapshots (
    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,

    -- Fear & Greed Index (always available)
    fear_greed_index INTEGER NOT NULL, -- 0-100
    fear_greed_classification TEXT NOT NULL, -- 'Extreme Fear', 'Fear', 'Neutral', 'Greed', 'Extreme Greed'

    -- News sentiment (if available)
    news_sentiment REAL, -- -1 to +1
    news_articles_analyzed INTEGER DEFAULT 0,

    -- Overall sentiment
    overall_sentiment REAL NOT NULL, -- -1 to +1 (normalized)

    -- Market regime
    market_regime TEXT NOT NULL, -- 'bull', 'bear', 'sideways', 'volatile'

    -- Macro indicators (JSON)
    macro_indicators_json TEXT, -- JSON array of macro indicators

    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sentiment_timestamp ON sentiment_snapshots(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_sentiment_regime ON sentiment_snapshots(market_regime);

-- Add sentiment columns to chaos_trades
-- These columns allow pattern discovery like "RSI oversold + extreme fear = 78% win rate"
ALTER TABLE chaos_trades ADD COLUMN sentiment_fear_greed INTEGER; -- 0-100
ALTER TABLE chaos_trades ADD COLUMN sentiment_overall REAL; -- -1 to +1
ALTER TABLE chaos_trades ADD COLUMN sentiment_regime TEXT; -- 'bull', 'bear', 'sideways', 'volatile'
ALTER TABLE chaos_trades ADD COLUMN sentiment_classification TEXT; -- 'Extreme Fear', etc.
ALTER TABLE chaos_trades ADD COLUMN sentiment_news_score REAL; -- -1 to +1 (news only)

-- Add macro indicators to chaos trades (for pattern discovery)
ALTER TABLE chaos_trades ADD COLUMN macro_fed_rate REAL; -- Federal Funds Rate
ALTER TABLE chaos_trades ADD COLUMN macro_cpi REAL; -- Inflation
ALTER TABLE chaos_trades ADD COLUMN macro_unemployment REAL; -- Unemployment
ALTER TABLE chaos_trades ADD COLUMN macro_10y_yield REAL; -- 10-Year Treasury Yield

-- Indexes for pattern queries
CREATE INDEX IF NOT EXISTS idx_chaos_trades_sentiment ON chaos_trades(sentiment_fear_greed);
CREATE INDEX IF NOT EXISTS idx_chaos_trades_regime ON chaos_trades(sentiment_regime);
CREATE INDEX IF NOT EXISTS idx_chaos_trades_profitable_sentiment ON chaos_trades(profitable, sentiment_fear_greed);
CREATE INDEX IF NOT EXISTS idx_chaos_trades_profitable_regime ON chaos_trades(profitable, sentiment_regime);

-- Pattern discovery queries will look like:
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

-- News articles table (optional, for detailed analysis)
CREATE TABLE IF NOT EXISTS news_articles (
    article_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    body TEXT,
    url TEXT,
    source TEXT NOT NULL,
    published_on INTEGER NOT NULL, -- Unix timestamp
    sentiment_score REAL, -- -1 to +1
    tags TEXT, -- JSON array
    symbols TEXT, -- JSON array ['BTC', 'ETH', 'SOL']
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_news_published ON news_articles(published_on DESC);
CREATE INDEX IF NOT EXISTS idx_news_source ON news_articles(source);
CREATE INDEX IF NOT EXISTS idx_news_sentiment ON news_articles(sentiment_score);

-- Macro indicators table (optional, for historical tracking)
CREATE TABLE IF NOT EXISTS macro_indicators (
    indicator_id INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator_code TEXT NOT NULL, -- 'FEDFUNDS', 'CPIAUCSL', etc.
    indicator_name TEXT NOT NULL,
    value REAL NOT NULL,
    date TEXT NOT NULL, -- YYYY-MM-DD
    unit TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_macro_code_date ON macro_indicators(indicator_code, date DESC);

-- Committee weighting log (tracks how sentiment influenced agent decisions)
CREATE TABLE IF NOT EXISTS committee_weighting_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    cycle_number INTEGER NOT NULL,

    -- Sentiment context
    sentiment_score REAL NOT NULL,
    regime TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    recommended_bias TEXT NOT NULL,
    fear_greed INTEGER NOT NULL,

    -- Committee decision
    decision TEXT, -- 'BUY', 'SELL', 'HOLD'
    confidence REAL, -- 0-1

    -- Pattern combination used
    patterns_selected TEXT, -- JSON array of pattern IDs

    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_committee_log_timestamp ON committee_weighting_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_committee_log_regime ON committee_weighting_log(regime);

-- View: Pattern performance by sentiment regime
CREATE VIEW IF NOT EXISTS pattern_performance_by_regime AS
SELECT
    dp.pattern_id,
    dp.name,
    ct.sentiment_regime,
    COUNT(*) as total_tests,
    SUM(ct.profitable) as wins,
    CAST(SUM(ct.profitable) AS REAL) / COUNT(*) as win_rate,
    AVG(ct.pnl_pct) as avg_return
FROM discovered_patterns dp
JOIN chaos_trades ct ON 1=1  -- Simplified join for pattern testing
WHERE ct.sentiment_regime IS NOT NULL
GROUP BY dp.pattern_id, dp.name, ct.sentiment_regime
HAVING COUNT(*) >= 10  -- Minimum sample size
ORDER BY win_rate DESC;

-- View: Sentiment influence on chaos trades
CREATE VIEW IF NOT EXISTS sentiment_trading_stats AS
SELECT
    sentiment_regime,
    sentiment_classification,
    CASE
        WHEN sentiment_fear_greed < 25 THEN 'Extreme Fear'
        WHEN sentiment_fear_greed < 45 THEN 'Fear'
        WHEN sentiment_fear_greed < 55 THEN 'Neutral'
        WHEN sentiment_fear_greed < 75 THEN 'Greed'
        ELSE 'Extreme Greed'
    END as fear_greed_bucket,
    COUNT(*) as total_trades,
    SUM(profitable) as winning_trades,
    CAST(SUM(profitable) AS REAL) / COUNT(*) as win_rate,
    AVG(pnl_pct) as avg_return,
    MIN(pnl_pct) as worst_return,
    MAX(pnl_pct) as best_return
FROM chaos_trades
WHERE sentiment_regime IS NOT NULL
GROUP BY sentiment_regime, sentiment_classification, fear_greed_bucket
ORDER BY win_rate DESC;

-- Comments
COMMENT ON TABLE sentiment_snapshots IS 'Historical sentiment and market regime snapshots for pattern discovery';
COMMENT ON TABLE news_articles IS 'News articles with sentiment analysis for detailed correlation studies';
COMMENT ON TABLE macro_indicators IS 'Macro economic indicators (Fed rate, CPI, unemployment) for pattern context';
COMMENT ON TABLE committee_weighting_log IS 'Log of how sentiment influenced multi-agent committee decisions';
COMMENT ON COLUMN chaos_trades.sentiment_fear_greed IS 'Fear & Greed Index (0-100) at time of trade entry';
COMMENT ON COLUMN chaos_trades.sentiment_overall IS 'Overall sentiment score (-1 to +1) combining news + fear/greed';
COMMENT ON COLUMN chaos_trades.sentiment_regime IS 'Market regime (bull/bear/sideways/volatile) at trade entry';
