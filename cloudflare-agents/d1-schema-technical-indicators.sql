/**
 * D1 Database Schema for Chaos Trades with ALL Technical Indicators
 *
 * This schema stores every possible indicator so AI can find correlations
 * between indicator combinations and successful outcomes
 */

CREATE TABLE IF NOT EXISTS chaos_trades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pair TEXT NOT NULL,
  entry_time TEXT NOT NULL,
  exit_time TEXT NOT NULL,
  entry_price REAL NOT NULL,
  exit_price REAL NOT NULL,
  pnl_pct REAL NOT NULL,
  profitable INTEGER NOT NULL,
  hold_duration_minutes INTEGER NOT NULL,

  -- RSI
  entry_rsi_14 REAL,
  entry_rsi_oversold INTEGER, -- Boolean
  entry_rsi_overbought INTEGER,

  -- MACD
  entry_macd_line REAL,
  entry_macd_signal REAL,
  entry_macd_histogram REAL,
  entry_macd_bullish_cross INTEGER,
  entry_macd_bearish_cross INTEGER,

  -- Bollinger Bands
  entry_bb_upper REAL,
  entry_bb_middle REAL,
  entry_bb_lower REAL,
  entry_bb_position REAL, -- 0-1
  entry_bb_squeeze INTEGER,
  entry_bb_at_lower INTEGER,
  entry_bb_at_upper INTEGER,

  -- Moving Averages
  entry_sma_10 REAL,
  entry_sma_50 REAL,
  entry_sma_200 REAL,
  entry_ema_10 REAL,
  entry_ema_50 REAL,
  entry_price_vs_sma10 REAL,
  entry_price_vs_sma50 REAL,
  entry_price_vs_sma200 REAL,
  entry_above_sma10 INTEGER,
  entry_above_sma50 INTEGER,
  entry_above_sma200 INTEGER,
  entry_golden_cross INTEGER,
  entry_death_cross INTEGER,

  -- Stochastic
  entry_stoch_k REAL,
  entry_stoch_d REAL,
  entry_stoch_oversold INTEGER,
  entry_stoch_overbought INTEGER,
  entry_stoch_bullish_cross INTEGER,
  entry_stoch_bearish_cross INTEGER,

  -- ATR / Volatility
  entry_atr_14 REAL,
  entry_volatility_regime TEXT, -- 'low', 'medium', 'high'

  -- Volume
  entry_volume REAL,
  entry_volume_sma_20 REAL,
  entry_volume_vs_avg REAL,
  entry_volume_spike INTEGER,
  entry_volume_dry INTEGER,

  -- Momentum
  entry_momentum_1 REAL,
  entry_momentum_5 REAL,
  entry_momentum_10 REAL,
  entry_momentum_positive INTEGER,
  entry_momentum_strong INTEGER,

  -- Trend
  entry_trend_regime TEXT, -- 'uptrend', 'downtrend', 'sideways'
  entry_higher_highs INTEGER,
  entry_lower_lows INTEGER,

  -- Temporal Features (CRITICAL for discovering time-based patterns)
  entry_day_of_week INTEGER, -- 0=Monday, 6=Sunday
  entry_hour_of_day INTEGER, -- 0-23
  entry_month INTEGER, -- 1-12
  entry_week_of_month INTEGER, -- 1-4
  entry_is_weekend INTEGER,
  entry_is_monday INTEGER,
  entry_is_tuesday INTEGER,
  entry_is_wednesday INTEGER,
  entry_is_thursday INTEGER,
  entry_is_friday INTEGER,
  entry_is_market_hours INTEGER,

  -- Support/Resistance
  entry_near_recent_high INTEGER,
  entry_near_recent_low INTEGER,
  entry_at_resistance INTEGER,
  entry_at_support INTEGER,

  -- Trade Rationalization (what indicators suggested this trade)
  buy_rationalization TEXT, -- JSON array of reasons
  sell_rationalization TEXT, -- JSON array of reasons

  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast querying by pattern discovery
CREATE INDEX IF NOT EXISTS idx_chaos_trades_profitable ON chaos_trades(profitable);
CREATE INDEX IF NOT EXISTS idx_chaos_trades_pair ON chaos_trades(pair);
CREATE INDEX IF NOT EXISTS idx_chaos_trades_day_of_week ON chaos_trades(entry_day_of_week);
CREATE INDEX IF NOT EXISTS idx_chaos_trades_hour ON chaos_trades(entry_hour_of_day);
CREATE INDEX IF NOT EXISTS idx_chaos_trades_month ON chaos_trades(entry_month);
CREATE INDEX IF NOT EXISTS idx_chaos_trades_rsi ON chaos_trades(entry_rsi_14);
CREATE INDEX IF NOT EXISTS idx_chaos_trades_macd_cross ON chaos_trades(entry_macd_bullish_cross, entry_macd_bearish_cross);
CREATE INDEX IF NOT EXISTS idx_chaos_trades_trend ON chaos_trades(entry_trend_regime);
CREATE INDEX IF NOT EXISTS idx_chaos_trades_volatility ON chaos_trades(entry_volatility_regime);

-- Patterns table (discovered patterns)
CREATE TABLE IF NOT EXISTS patterns (
  pattern_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  source TEXT NOT NULL, -- 'chaos', 'academic', 'technical', 'agent'
  conditions TEXT NOT NULL, -- JSON
  win_rate REAL NOT NULL,
  sample_size INTEGER NOT NULL,
  avg_pnl_pct REAL,
  sharpe_ratio REAL,
  max_drawdown REAL,
  fitness_score REAL,
  discovered_at TEXT DEFAULT CURRENT_TIMESTAMP,
  tested INTEGER DEFAULT 0,
  active INTEGER DEFAULT 1
);

-- Agents table (Layer 2 - Reasoning Agents)
CREATE TABLE IF NOT EXISTS agents (
  agent_id TEXT PRIMARY KEY,
  strategy TEXT NOT NULL, -- JSON: combined patterns
  win_rate REAL,
  sample_size INTEGER,
  avg_pnl_pct REAL,
  sharpe_ratio REAL,
  max_drawdown REAL,
  fitness_score REAL,
  generation INTEGER,
  parent_id TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  active INTEGER DEFAULT 1
);

-- System state
CREATE TABLE IF NOT EXISTS system_state (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
