-- Historical Price Data Table
-- Stores OHLCV (Open, High, Low, Close, Volume) candle data from various sources
-- Used for backtesting, analysis, and real-time strategy execution

CREATE TABLE IF NOT EXISTS historical_prices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Symbol and timeframe
    symbol VARCHAR(20) NOT NULL,  -- BTC, ETH, SOL, etc.
    base_currency VARCHAR(10) NOT NULL DEFAULT 'USD',  -- USD, USDT, etc.
    interval VARCHAR(10) NOT NULL,  -- 1m, 5m, 15m, 1h, 1d

    -- Timestamp (unique per symbol/interval combination)
    timestamp TIMESTAMPTZ NOT NULL,
    unix_timestamp BIGINT NOT NULL,

    -- OHLCV data
    open DECIMAL(20, 8) NOT NULL,
    high DECIMAL(20, 8) NOT NULL,
    low DECIMAL(20, 8) NOT NULL,
    close DECIMAL(20, 8) NOT NULL,
    volume DECIMAL(30, 8),

    -- Data source tracking
    source VARCHAR(50) NOT NULL,  -- coingecko, cryptocompare, binance, kraken

    -- Metadata
    data_quality VARCHAR(20) DEFAULT 'good',  -- good, interpolated, suspicious

    -- Unique constraint: one candle per symbol/interval/timestamp
    CONSTRAINT unique_candle UNIQUE (symbol, base_currency, interval, timestamp)
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_prices_symbol_time ON historical_prices (symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_prices_symbol_interval_time ON historical_prices (symbol, interval, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_prices_timestamp ON historical_prices (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_prices_source ON historical_prices (source);

-- Composite index for common backtesting queries
CREATE INDEX IF NOT EXISTS idx_prices_backtest ON historical_prices (symbol, interval, timestamp DESC) WHERE data_quality = 'good';

-- Add comments for documentation
COMMENT ON TABLE historical_prices IS 'Historical OHLCV price data from multiple sources for crypto assets';
COMMENT ON COLUMN historical_prices.interval IS 'Candle interval: 1m, 5m, 15m, 30m, 1h, 4h, 1d';
COMMENT ON COLUMN historical_prices.data_quality IS 'Quality indicator: good (real data), interpolated (filled gaps), suspicious (anomalies detected)';

-- View for latest prices per symbol
CREATE OR REPLACE VIEW latest_prices AS
SELECT DISTINCT ON (symbol, interval)
    symbol,
    interval,
    timestamp,
    close as price,
    volume,
    source
FROM historical_prices
WHERE data_quality = 'good'
ORDER BY symbol, interval, timestamp DESC;

-- View for daily summaries
CREATE OR REPLACE VIEW daily_price_summary AS
SELECT
    symbol,
    DATE(timestamp) as date,
    MIN(low) as day_low,
    MAX(high) as day_high,
    (array_agg(open ORDER BY timestamp ASC))[1] as day_open,
    (array_agg(close ORDER BY timestamp DESC))[1] as day_close,
    SUM(volume) as total_volume,
    COUNT(*) as candle_count
FROM historical_prices
WHERE interval IN ('1h', '4h', '1d')
GROUP BY symbol, DATE(timestamp)
ORDER BY symbol, date DESC;

COMMENT ON VIEW latest_prices IS 'Latest price for each symbol and interval';
COMMENT ON VIEW daily_price_summary IS 'Daily OHLC summary aggregated from hourly/4h/daily candles';
