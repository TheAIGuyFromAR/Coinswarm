-- Historical Prices Table (Optimized for Queue-based Ingestion)
-- This schema is designed for high-throughput batch inserts via Cloudflare Queues

CREATE TABLE IF NOT EXISTS historical_prices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol TEXT NOT NULL,
  timestamp INTEGER NOT NULL,
  open REAL NOT NULL,
  high REAL NOT NULL,
  low REAL NOT NULL,
  close REAL NOT NULL,
  volume REAL NOT NULL,
  source TEXT NOT NULL CHECK(source IN ('binance', 'coingecko', 'cryptocompare')),
  created_at INTEGER NOT NULL,

  -- Unique constraint prevents duplicates
  UNIQUE(symbol, timestamp, source)
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_historical_symbol_timestamp
  ON historical_prices(symbol, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_historical_timestamp
  ON historical_prices(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_historical_symbol_source
  ON historical_prices(symbol, source);

-- Query performance stats table
CREATE TABLE IF NOT EXISTS ingestion_stats (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  batch_size INTEGER NOT NULL,
  duration_ms INTEGER NOT NULL,
  throughput_per_sec REAL NOT NULL,
  source TEXT NOT NULL,
  timestamp INTEGER NOT NULL
);

-- Dead letter queue tracking (for failed messages)
CREATE TABLE IF NOT EXISTS failed_ingestions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol TEXT NOT NULL,
  timestamp INTEGER NOT NULL,
  error_message TEXT NOT NULL,
  retry_count INTEGER NOT NULL,
  failed_at INTEGER NOT NULL,
  raw_data TEXT  -- JSON of the failed data point
);

-- Index for failed message queries
CREATE INDEX IF NOT EXISTS idx_failed_symbol_timestamp
  ON failed_ingestions(symbol, timestamp DESC);

-- View: Latest prices per symbol
CREATE VIEW IF NOT EXISTS latest_prices AS
SELECT
  symbol,
  MAX(timestamp) as latest_timestamp,
  close as latest_price,
  source
FROM historical_prices
GROUP BY symbol;

-- View: Data coverage stats
CREATE VIEW IF NOT EXISTS data_coverage AS
SELECT
  symbol,
  source,
  COUNT(*) as data_points,
  MIN(timestamp) as earliest_timestamp,
  MAX(timestamp) as latest_timestamp,
  (MAX(timestamp) - MIN(timestamp)) / 1000 / 60 / 60 / 24 as days_coverage
FROM historical_prices
GROUP BY symbol, source;

-- View: Ingestion performance
CREATE VIEW IF NOT EXISTS ingestion_performance AS
SELECT
  source,
  AVG(throughput_per_sec) as avg_throughput,
  MAX(throughput_per_sec) as max_throughput,
  AVG(batch_size) as avg_batch_size,
  COUNT(*) as total_batches
FROM ingestion_stats
GROUP BY source;
