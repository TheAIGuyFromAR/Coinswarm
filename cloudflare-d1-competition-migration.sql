-- Migration: Add multi-agent competition support
-- Adds origin tracking, head-to-head competition, and timeframe testing

-- Add new columns to discovered_patterns
ALTER TABLE discovered_patterns ADD COLUMN origin TEXT DEFAULT 'chaos';
ALTER TABLE discovered_patterns ADD COLUMN source_detail TEXT;
ALTER TABLE discovered_patterns ADD COLUMN last_tested_at TEXT;
ALTER TABLE discovered_patterns ADD COLUMN head_to_head_wins INTEGER DEFAULT 0;
ALTER TABLE discovered_patterns ADD COLUMN head_to_head_losses INTEGER DEFAULT 0;
ALTER TABLE discovered_patterns ADD COLUMN timeframe_tested TEXT; -- JSON array of tested timeframes
ALTER TABLE discovered_patterns ADD COLUMN timeframe_performance TEXT; -- JSON map of timeframe -> ROI

-- Index for weighted selection (fewer runs + more votes)
CREATE INDEX IF NOT EXISTS idx_patterns_selection ON discovered_patterns(number_of_runs ASC, votes DESC);

-- Index for head-to-head tracking
CREATE INDEX IF NOT EXISTS idx_patterns_h2h ON discovered_patterns(head_to_head_wins DESC, head_to_head_losses ASC);

-- Index for origin-based queries
CREATE INDEX IF NOT EXISTS idx_patterns_origin ON discovered_patterns(origin);

-- Head-to-head matchups table
CREATE TABLE IF NOT EXISTS h2h_matchups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_a_id TEXT NOT NULL,
    pattern_b_id TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    pattern_a_roi REAL NOT NULL,
    pattern_b_roi REAL NOT NULL,
    timeframe_bonus REAL NOT NULL,
    winner_id TEXT NOT NULL,
    tested_at TEXT DEFAULT CURRENT_TIMESTAMP,
    data_slice_start TEXT,
    data_slice_end TEXT
);

CREATE INDEX IF NOT EXISTS idx_h2h_tested ON h2h_matchups(tested_at DESC);
CREATE INDEX IF NOT EXISTS idx_h2h_patterns ON h2h_matchups(pattern_a_id, pattern_b_id);

-- Research agent tracking
CREATE TABLE IF NOT EXISTS research_agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_type TEXT NOT NULL, -- 'academic', 'technical', 'chaos'
    agent_name TEXT NOT NULL,
    last_run_at TEXT,
    patterns_generated INTEGER DEFAULT 0,
    sources_processed INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Insert research agents
INSERT OR IGNORE INTO research_agents (agent_type, agent_name, status) VALUES
    ('academic', 'Academic Papers Agent', 'active'),
    ('technical', 'Technical Patterns Agent', 'active'),
    ('chaos', 'Chaos Discovery Agent', 'active');

-- Historical data sources table
CREATE TABLE IF NOT EXISTS data_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exchange TEXT NOT NULL,
    pair TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    last_fetched_at TEXT,
    candles_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Index for data source queries
CREATE INDEX IF NOT EXISTS idx_data_sources_status ON data_sources(status, last_fetched_at);

-- Insert initial Solana ecosystem data sources
INSERT OR IGNORE INTO data_sources (exchange, pair, timeframe, status) VALUES
    ('binance', 'SOLUSDT', '1m', 'pending'),
    ('binance', 'SOLUSDT', '5m', 'pending'),
    ('binance', 'SOLUSDT', '1h', 'pending'),
    ('binance', 'SOLUSDT', '1d', 'pending');
