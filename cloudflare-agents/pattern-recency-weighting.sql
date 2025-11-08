-- Pattern scoring with logarithmic recency decay
-- Patterns are NEVER retired, just weighted by recent performance

-- Add recency tracking columns to discovered_patterns
ALTER TABLE discovered_patterns ADD COLUMN last_success_date TEXT;
ALTER TABLE discovered_patterns ADD COLUMN last_failure_date TEXT;
ALTER TABLE discovered_patterns ADD COLUMN recency_bonus REAL DEFAULT 0;
ALTER TABLE discovered_patterns ADD COLUMN selection_score REAL DEFAULT 0;

-- Historical performance tracking (time-series)
CREATE TABLE IF NOT EXISTS pattern_performance_history (
    history_id TEXT PRIMARY KEY,
    pattern_id TEXT NOT NULL,
    test_date TEXT NOT NULL,
    win_rate REAL,
    roi REAL,
    sample_size INTEGER,
    market_regime TEXT, -- 'bull', 'bear', 'sideways', 'volatile'

    FOREIGN KEY (pattern_id) REFERENCES discovered_patterns(pattern_id)
);

CREATE INDEX IF NOT EXISTS idx_pattern_performance_date ON pattern_performance_history(test_date DESC);
CREATE INDEX IF NOT EXISTS idx_pattern_performance_pattern ON pattern_performance_history(pattern_id);

-- View for pattern selection with recency weighting
CREATE VIEW IF NOT EXISTS pattern_selection_view AS
SELECT
    pattern_id,
    name,
    win_rate,
    sample_size,
    last_success_date,
    -- Logarithmic recency bonus (decays slowly over time)
    CASE
        WHEN last_success_date IS NOT NULL THEN
            -1 * LOG(1 + CAST((JULIANDAY('now') - JULIANDAY(last_success_date)) AS REAL))
        ELSE -10  -- Never succeeded = very negative bonus
    END as recency_bonus,
    -- Selection score = fitness + recency
    (win_rate * sample_size / 100.0) +
    CASE
        WHEN last_success_date IS NOT NULL THEN
            -1 * LOG(1 + CAST((JULIANDAY('now') - JULIANDAY(last_success_date)) AS REAL))
        ELSE -10
    END as selection_score,
    -- Mark stale patterns but DON'T retire them
    CASE
        WHEN last_success_date IS NULL OR
             JULIANDAY('now') - JULIANDAY(last_success_date) > 180
        THEN 'stale'
        WHEN JULIANDAY('now') - JULIANDAY(last_success_date) > 90
        THEN 'aging'
        WHEN JULIANDAY('now') - JULIANDAY(last_success_date) > 30
        THEN 'recent'
        ELSE 'hot'
    END as freshness_status
FROM discovered_patterns
WHERE active = 1
ORDER BY selection_score DESC;

-- Market regime detection table
CREATE TABLE IF NOT EXISTS market_regimes (
    regime_id TEXT PRIMARY KEY,
    start_date TEXT NOT NULL,
    end_date TEXT,
    regime_type TEXT NOT NULL, -- 'bull', 'bear', 'sideways', 'volatile'
    characteristics TEXT, -- JSON of metrics that defined this regime
    avg_volatility REAL,
    avg_volume REAL,
    dominant_patterns TEXT -- JSON array of pattern IDs that worked best
);

CREATE INDEX IF NOT EXISTS idx_market_regimes_dates ON market_regimes(start_date, end_date);

-- Pattern-regime affinity (which patterns work in which regimes)
CREATE TABLE IF NOT EXISTS pattern_regime_affinity (
    affinity_id TEXT PRIMARY KEY,
    pattern_id TEXT NOT NULL,
    regime_type TEXT NOT NULL,
    win_rate_in_regime REAL,
    sample_size_in_regime INTEGER,
    last_tested_in_regime TEXT,

    FOREIGN KEY (pattern_id) REFERENCES discovered_patterns(pattern_id)
);

CREATE INDEX IF NOT EXISTS idx_pattern_regime ON pattern_regime_affinity(pattern_id, regime_type);

-- Comments
COMMENT ON COLUMN discovered_patterns.last_success_date IS 'Last time this pattern won a competition or had profitable trade';
COMMENT ON COLUMN discovered_patterns.recency_bonus IS 'Logarithmic bonus based on time since last success (cached)';
COMMENT ON COLUMN discovered_patterns.selection_score IS 'Combined fitness + recency bonus for selection probability (cached)';
COMMENT ON TABLE pattern_performance_history IS 'Time-series of pattern performance - enables detecting when old patterns come back to life';
COMMENT ON TABLE market_regimes IS 'Historical market regimes - patterns that worked in 2021 bull might work again in future bull';
COMMENT ON TABLE pattern_regime_affinity IS 'Which patterns work best in which market regimes - enables smart re-activation';
