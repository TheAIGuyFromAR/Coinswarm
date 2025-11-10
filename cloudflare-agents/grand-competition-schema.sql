-- Grand Competition Schema
-- Elite agents compete in full historical runs with sophisticated scoring

-- Competition runs (full dataset backtests)
CREATE TABLE IF NOT EXISTS competition_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL,
    agent_name TEXT NOT NULL,

    -- Run parameters
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    dataset_size INTEGER NOT NULL, -- Number of candles

    -- Performance metrics
    starting_capital REAL NOT NULL DEFAULT 10000.0,
    ending_capital REAL NOT NULL,
    total_roi_pct REAL NOT NULL,
    total_trades INTEGER NOT NULL,
    profitable_trades INTEGER NOT NULL,
    win_rate REAL NOT NULL, -- Percentage of profitable trades

    -- Activity requirements (shot clock)
    avg_candles_between_trades REAL NOT NULL,
    max_idle_candles INTEGER NOT NULL,
    activity_penalty REAL DEFAULT 0, -- Penalty for sitting idle

    -- Market condition performance
    bull_market_roi REAL, -- ROI during rising markets
    bear_market_roi REAL, -- ROI during declining markets
    sideways_market_roi REAL, -- ROI during flat markets

    -- Benchmark comparison (buy & hold)
    market_roi REAL NOT NULL, -- Simple buy & hold return
    alpha REAL NOT NULL, -- Excess return vs market

    -- Risk metrics
    sharpe_ratio REAL,
    max_drawdown_pct REAL,
    avg_trade_duration_minutes REAL,

    -- Asymmetric profit metrics
    avg_win_size REAL,
    avg_loss_size REAL,
    profit_factor REAL, -- Gross profit / Gross loss

    -- Grand Competition Score (multi-factor)
    base_score REAL NOT NULL,
    market_condition_multiplier REAL NOT NULL,
    activity_multiplier REAL NOT NULL,
    consistency_multiplier REAL NOT NULL,
    asymmetry_multiplier REAL NOT NULL,
    final_score REAL NOT NULL,

    -- Rankings
    rank_by_score INTEGER,
    rank_by_roi INTEGER,
    rank_by_win_rate INTEGER,
    rank_by_alpha INTEGER,

    -- Metadata
    completed BOOLEAN DEFAULT 0,
    error_message TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,

    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

CREATE INDEX IF NOT EXISTS idx_competition_score ON competition_runs(final_score DESC);
CREATE INDEX IF NOT EXISTS idx_competition_agent ON competition_runs(agent_id);
CREATE INDEX IF NOT EXISTS idx_competition_completed ON competition_runs(completed, final_score DESC);

-- Market regime periods (for scoring bear market performance)
CREATE TABLE IF NOT EXISTS market_regimes (
    regime_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pair TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    regime TEXT NOT NULL, -- 'bull', 'bear', 'sideways', 'volatile'

    -- Regime characteristics
    price_change_pct REAL NOT NULL,
    duration_hours REAL NOT NULL,
    avg_volatility REAL,

    -- For detecting trend
    start_price REAL NOT NULL,
    end_price REAL NOT NULL,
    high_price REAL,
    low_price REAL,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(pair, start_time, end_time)
);

CREATE INDEX IF NOT EXISTS idx_regime_pair ON market_regimes(pair);
CREATE INDEX IF NOT EXISTS idx_regime_time ON market_regimes(pair, start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_regime_type ON market_regimes(regime);

-- Agent trades during competition runs
CREATE TABLE IF NOT EXISTS competition_trades (
    trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    agent_id INTEGER NOT NULL,

    -- Trade details
    pair TEXT NOT NULL,
    entry_time TEXT NOT NULL,
    exit_time TEXT NOT NULL,
    entry_price REAL NOT NULL,
    exit_price REAL NOT NULL,

    -- Position
    position_size REAL NOT NULL,
    capital_at_entry REAL NOT NULL,
    capital_at_exit REAL NOT NULL,

    -- Performance
    pnl REAL NOT NULL,
    pnl_pct REAL NOT NULL,
    profitable BOOLEAN NOT NULL,

    -- Market context
    market_regime TEXT, -- 'bull', 'bear', 'sideways'
    market_roi_during_trade REAL, -- What buy & hold would have made

    -- Shot clock compliance
    candles_since_last_trade INTEGER,
    shot_clock_violation BOOLEAN DEFAULT 0,

    -- Decision rationale
    entry_reason TEXT,
    exit_reason TEXT,
    confidence REAL,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (run_id) REFERENCES competition_runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_comp_trades_run ON competition_trades(run_id);
CREATE INDEX IF NOT EXISTS idx_comp_trades_agent ON competition_trades(agent_id);
CREATE INDEX IF NOT EXISTS idx_comp_trades_profitable ON competition_trades(profitable, market_regime);

-- Competition leaderboard (view)
CREATE VIEW IF NOT EXISTS competition_leaderboard AS
SELECT
    cr.agent_id,
    cr.agent_name,
    COUNT(*) as total_runs,
    MAX(cr.final_score) as best_score,
    AVG(cr.final_score) as avg_score,
    MAX(cr.total_roi_pct) as best_roi,
    AVG(cr.win_rate) as avg_win_rate,
    MAX(cr.alpha) as best_alpha,
    AVG(cr.bear_market_roi) as avg_bear_market_roi,
    MIN(cr.max_drawdown_pct) as best_drawdown,

    -- Consistency metrics
    COUNT(CASE WHEN cr.total_roi_pct > 0 THEN 1 END) as profitable_runs,
    COUNT(CASE WHEN cr.bear_market_roi > 0 THEN 1 END) as profitable_in_bear,

    -- Latest run
    MAX(cr.completed_at) as last_run_at
FROM competition_runs cr
WHERE cr.completed = 1
GROUP BY cr.agent_id, cr.agent_name
ORDER BY best_score DESC;

-- Scoring formula documentation
--
-- FINAL_SCORE = base_roi * market_condition_multiplier * activity_multiplier * consistency_multiplier * asymmetry_multiplier
--
-- 1. BASE_SCORE = total_roi_pct
--
-- 2. MARKET_CONDITION_MULTIPLIER:
--    - Bear market profits (market down, agent up): (agent_roi / market_roi)^3  (CUBIC reward)
--    - Bull market outperformance (both up, agent better): (agent_roi / market_roi)^2  (EXPONENTIAL reward)
--    - Bull market underperformance: agent_roi / market_roi  (LINEAR penalty)
--
-- 3. ACTIVITY_MULTIPLIER:
--    - Must maintain minimum trade frequency (shot clock)
--    - Penalty for sitting idle: max(0, 1 - (avg_idle_candles / shot_clock_limit))
--
-- 4. CONSISTENCY_MULTIPLIER:
--    - Win rate bonus: (win_rate / 50)^0.5  (Square root to avoid over-weighting)
--    - Sharpe ratio bonus: max(1, sharpe_ratio)
--    - Drawdown penalty: 1 / (1 + max_drawdown_pct)
--
-- 5. ASYMMETRY_MULTIPLIER:
--    - Profit factor (big wins, small losses): log(profit_factor + 1)
--    - Risk/Reward ratio: avg_win_size / avg_loss_size
--
-- Example Scenarios:
--
-- Scenario A: Agent makes 50% in bear market (-20%)
--   market_condition_multiplier = (50 / -20)^3 = -15.625 → abs() = 15.625x
--   (Massively rewarded for making money when market is down)
--
-- Scenario B: Agent makes 100% in bull market (+80%)
--   market_condition_multiplier = (100 / 80)^2 = 1.56x
--   (Modest reward for outperforming bull market)
--
-- Scenario C: Agent makes 60% in bull market (+80%)
--   market_condition_multiplier = 60 / 80 = 0.75x
--   (Penalized for underperforming bull market)
