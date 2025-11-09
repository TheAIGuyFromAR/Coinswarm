-- Price data collection schema
-- Stores multi-timeframe OHLCV data from multiple sources

CREATE TABLE IF NOT EXISTS price_data (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol TEXT NOT NULL,
  timestamp INTEGER NOT NULL,
  timeframe TEXT NOT NULL, -- '1m', '1h', '1d'
  open REAL NOT NULL,
  high REAL NOT NULL,
  low REAL NOT NULL,
  close REAL NOT NULL,
  volume REAL,
  source TEXT NOT NULL, -- 'cryptocompare', 'coingecko', 'binance', 'dexscreener'
  created_at INTEGER DEFAULT (unixepoch()),
  UNIQUE(symbol, timestamp, timeframe, source)
);

CREATE INDEX IF NOT EXISTS idx_price_data_symbol_timeframe ON price_data(symbol, timeframe, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_price_data_timestamp ON price_data(timestamp DESC);

-- Collection progress tracking
CREATE TABLE IF NOT EXISTS collection_progress (
  symbol TEXT PRIMARY KEY,
  coin_id TEXT NOT NULL,
  minutes_collected INTEGER DEFAULT 0,
  days_collected INTEGER DEFAULT 0,
  hours_collected INTEGER DEFAULT 0,
  total_minutes INTEGER NOT NULL,
  total_days INTEGER NOT NULL,
  total_hours INTEGER NOT NULL,
  daily_status TEXT DEFAULT 'pending', -- 'pending', 'in_progress', 'completed', 'paused'
  minute_status TEXT DEFAULT 'pending',
  hourly_status TEXT DEFAULT 'pending',
  error_count INTEGER DEFAULT 0,
  last_error TEXT,
  last_minute_timestamp INTEGER,
  updated_at INTEGER DEFAULT (unixepoch())
);

-- Collection alerts
CREATE TABLE IF NOT EXISTS collection_alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  alert_type TEXT NOT NULL, -- 'daily_complete', 'hourly_complete', 'minute_25', etc.
  message TEXT NOT NULL,
  severity TEXT NOT NULL, -- 'info', 'warning', 'success', 'error'
  metadata TEXT, -- JSON string with additional data
  acknowledged BOOLEAN DEFAULT 0,
  created_at INTEGER DEFAULT (unixepoch())
);

CREATE INDEX IF NOT EXISTS idx_alerts_created ON collection_alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_ack ON collection_alerts(acknowledged, created_at DESC);

-- Technical indicators
CREATE TABLE IF NOT EXISTS technical_indicators (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp INTEGER NOT NULL,
  symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL, -- '1h', '1d'
  
  -- Moving Averages
  sma_20 REAL,
  sma_50 REAL,
  sma_200 REAL,
  ema_12 REAL,
  ema_26 REAL,
  ema_50 REAL,
  
  -- Bollinger Bands
  bb_upper REAL,
  bb_middle REAL,
  bb_lower REAL,
  bb_width REAL,
  
  -- MACD
  macd REAL,
  macd_signal REAL,
  macd_histogram REAL,
  
  -- RSI
  rsi_14 REAL,
  
  -- Custom indicators
  fear_greed_index REAL, -- 0-100 composite score
  
  -- Volume
  volume_sma_20 REAL,
  volume_ratio REAL, -- current / sma
  
  created_at INTEGER DEFAULT (unixepoch()),
  UNIQUE(symbol, timestamp, timeframe)
);

CREATE INDEX IF NOT EXISTS idx_indicators_symbol_timeframe ON technical_indicators(symbol, timeframe, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_indicators_timestamp ON technical_indicators(timestamp DESC);

-- Rate limiting buckets for real-time collection
CREATE TABLE IF NOT EXISTS rate_limit_buckets (
  source TEXT PRIMARY KEY, -- 'coingecko', 'cryptocompare', 'binance', 'dexscreener'
  tokens REAL NOT NULL, -- current bucket capacity
  max_tokens REAL NOT NULL, -- max bucket size
  refill_rate REAL NOT NULL, -- tokens per second
  last_refill INTEGER NOT NULL, -- unix timestamp
  updated_at INTEGER DEFAULT (unixepoch())
);
