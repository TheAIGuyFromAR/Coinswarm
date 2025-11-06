-- D1 Schema for Evolution System

-- Chaos trades table
CREATE TABLE IF NOT EXISTS chaos_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_time TEXT NOT NULL,
    exit_time TEXT NOT NULL,
    entry_price REAL NOT NULL,
    exit_price REAL NOT NULL,
    pnl_pct REAL NOT NULL,
    profitable INTEGER NOT NULL,  -- 0 or 1
    buy_reason TEXT,
    buy_state TEXT,  -- JSON
    sell_reason TEXT,
    sell_state TEXT,  -- JSON
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Index for performance
CREATE INDEX IF NOT EXISTS idx_chaos_trades_profitable ON chaos_trades(profitable);
CREATE INDEX IF NOT EXISTS idx_chaos_trades_created ON chaos_trades(created_at);

-- Discovered patterns table
CREATE TABLE IF NOT EXISTS discovered_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    conditions TEXT NOT NULL,  -- JSON with pattern details
    win_rate REAL,
    sample_size INTEGER,
    discovered_at TEXT NOT NULL,
    tested INTEGER DEFAULT 0,  -- 0 = not tested, 1 = tested
    accuracy REAL,
    votes INTEGER DEFAULT 0,  -- Upvotes - downvotes
    tested_at TEXT,
    -- Performance tracking columns
    number_of_runs INTEGER DEFAULT 0,  -- How many times tested
    max_ending_value REAL,  -- Best performance achieved
    average_ending_value REAL,  -- Average performance across runs
    average_roi_pct REAL,  -- Average ROI percentage across all runs
    annualized_roi_pct REAL,  -- Annualized ROI percentage (primary sort metric)
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_patterns_votes ON discovered_patterns(votes DESC);
CREATE INDEX IF NOT EXISTS idx_patterns_tested ON discovered_patterns(tested);
CREATE INDEX IF NOT EXISTS idx_patterns_best ON discovered_patterns(annualized_roi_pct DESC, number_of_runs DESC, max_ending_value DESC);

-- System stats table
CREATE TABLE IF NOT EXISTS system_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stat_name TEXT UNIQUE NOT NULL,
    stat_value TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Insert initial stats
INSERT OR IGNORE INTO system_stats (stat_name, stat_value) VALUES ('total_cycles', '0');
INSERT OR IGNORE INTO system_stats (stat_name, stat_value) VALUES ('last_run', 'never');
INSERT OR IGNORE INTO system_stats (stat_name, stat_value) VALUES ('winning_strategies', '0');
