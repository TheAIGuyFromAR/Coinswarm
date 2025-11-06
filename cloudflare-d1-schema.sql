-- Cloudflare D1 Schema for Coinswarm Historical Data
--
-- Run this to create the D1 database structure
--
-- Create D1 database:
--   wrangler d1 create coinswarm-historical-data
--
-- Apply schema:
--   wrangler d1 execute coinswarm-historical-data --file=cloudflare-d1-schema.sql

-- Price data table (OHLCV candles)
CREATE TABLE IF NOT EXISTS price_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,                -- BTC, ETH, SOL
    timestamp INTEGER NOT NULL,          -- Unix timestamp (seconds)
    timeframe TEXT NOT NULL,             -- 1h, 4h, 1d
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,
    providers TEXT,                      -- JSON array of data sources
    data_points INTEGER DEFAULT 1,       -- Number of exchanges aggregated
    variance REAL DEFAULT 0,             -- Price variance across sources
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    UNIQUE(symbol, timestamp, timeframe)
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_symbol_timestamp ON price_data(symbol, timestamp);
CREATE INDEX IF NOT EXISTS idx_symbol_timeframe_timestamp ON price_data(symbol, timeframe, timestamp);
CREATE INDEX IF NOT EXISTS idx_timestamp ON price_data(timestamp);

-- Metadata table (track what data we have)
CREATE TABLE IF NOT EXISTS data_coverage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    start_timestamp INTEGER NOT NULL,
    end_timestamp INTEGER NOT NULL,
    candle_count INTEGER NOT NULL,
    last_updated INTEGER DEFAULT (strftime('%s', 'now')),
    UNIQUE(symbol, timeframe, start_timestamp)
);

-- Index for coverage queries
CREATE INDEX IF NOT EXISTS idx_coverage_symbol ON data_coverage(symbol, timeframe);

-- Stats table (quick access to summary statistics)
CREATE TABLE IF NOT EXISTS price_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    period TEXT NOT NULL,               -- '1d', '7d', '30d', '90d', '1y', '2y'
    start_timestamp INTEGER NOT NULL,
    end_timestamp INTEGER NOT NULL,
    open_price REAL NOT NULL,
    close_price REAL NOT NULL,
    high_price REAL NOT NULL,
    low_price REAL NOT NULL,
    price_change_pct REAL NOT NULL,
    total_volume REAL NOT NULL,
    avg_volume REAL NOT NULL,
    volatility REAL,                    -- Standard deviation of returns
    updated_at INTEGER DEFAULT (strftime('%s', 'now')),
    UNIQUE(symbol, period, start_timestamp)
);

-- Index for stats queries
CREATE INDEX IF NOT EXISTS idx_stats_symbol_period ON price_stats(symbol, period);

-- View: Latest prices
CREATE VIEW IF NOT EXISTS latest_prices AS
SELECT
    symbol,
    timeframe,
    MAX(timestamp) as timestamp,
    close as price,
    volume
FROM price_data
GROUP BY symbol, timeframe;

-- View: Daily returns
CREATE VIEW IF NOT EXISTS daily_returns AS
SELECT
    symbol,
    DATE(timestamp, 'unixepoch') as date,
    (close - open) / open * 100 as return_pct,
    volume
FROM price_data
WHERE timeframe = '1d'
ORDER BY symbol, timestamp DESC;
