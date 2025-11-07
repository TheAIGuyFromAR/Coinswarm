-- Reasoning Agents Schema
-- Self-reflective trading agents that combine patterns and evolve through competition

-- Main agent table
CREATE TABLE IF NOT EXISTS trading_agents (
    agent_id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL,
    generation INTEGER DEFAULT 1,
    parent_id TEXT,
    personality TEXT NOT NULL, -- 'conservative', 'aggressive', 'balanced', 'contrarian', 'momentum_hunter', 'mean_reverter'

    -- Performance metrics
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    total_roi REAL DEFAULT 0,
    avg_roi_per_trade REAL DEFAULT 0,
    sharpe_ratio REAL DEFAULT 0,
    max_drawdown REAL DEFAULT 0,

    -- Competition stats
    competitions_entered INTEGER DEFAULT 0,
    competitions_won INTEGER DEFAULT 0,
    rank INTEGER DEFAULT 999,
    fitness_score REAL DEFAULT 0,

    -- Learning metrics
    decisions_made INTEGER DEFAULT 0,
    reflections_completed INTEGER DEFAULT 0,
    strategy_pivots INTEGER DEFAULT 0, -- how many times agent changed approach

    -- Status
    status TEXT DEFAULT 'active', -- 'active', 'retired', 'evolved', 'eliminated'
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_active_at TEXT DEFAULT CURRENT_TIMESTAMP,
    eliminated_at TEXT,

    FOREIGN KEY (parent_id) REFERENCES trading_agents(agent_id)
);

-- Agent memory - stores every decision and reflection
CREATE TABLE IF NOT EXISTS agent_memories (
    memory_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,

    -- Decision context
    decision_timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    cycle_number INTEGER NOT NULL,

    -- Market analysis
    market_volatility TEXT, -- 'low', 'medium', 'high'
    market_trend TEXT, -- 'strong_up', 'weak_up', 'sideways', 'weak_down', 'strong_down'
    market_volume TEXT, -- 'low', 'medium', 'high'
    price_momentum REAL,

    -- Agent reasoning
    patterns_considered TEXT, -- JSON array of pattern IDs considered
    patterns_selected TEXT, -- JSON array of pattern IDs actually used
    combination_reasoning TEXT, -- AI-generated explanation
    confidence_level REAL, -- 0-1 how confident in this decision

    -- Execution
    trades_executed INTEGER,
    entry_price REAL,
    exit_price REAL,
    hold_duration_minutes INTEGER,

    -- Outcome
    outcome TEXT, -- 'win', 'loss', 'neutral'
    roi REAL,
    roi_annualized REAL,

    -- Self-reflection (generated after outcome known)
    reflection_text TEXT, -- AI-generated reflection
    lessons_learned TEXT, -- Key takeaways
    strategy_adjustment TEXT, -- What to change next time
    reflected_at TEXT,

    FOREIGN KEY (agent_id) REFERENCES trading_agents(agent_id)
);

-- Agent knowledge base - accumulated wisdom
CREATE TABLE IF NOT EXISTS agent_knowledge (
    knowledge_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,

    knowledge_type TEXT NOT NULL, -- 'pattern_preference', 'market_condition', 'combination_rule', 'avoid_condition'

    -- Pattern preferences
    pattern_id TEXT,
    preference_strength REAL, -- -1 to 1 (negative = avoid, positive = prefer)

    -- Learned rules
    condition TEXT, -- e.g., "high_volatility AND uptrend"
    recommended_action TEXT, -- e.g., "Use momentum patterns"
    confidence REAL, -- 0-1 based on experience

    -- Evidence
    times_validated INTEGER DEFAULT 0,
    times_contradicted INTEGER DEFAULT 0,
    last_updated TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (agent_id) REFERENCES trading_agents(agent_id),
    FOREIGN KEY (pattern_id) REFERENCES discovered_patterns(pattern_id)
);

-- Agent competitions - head-to-head battles
CREATE TABLE IF NOT EXISTS agent_competitions (
    competition_id TEXT PRIMARY KEY,
    competition_timestamp TEXT DEFAULT CURRENT_TIMESTAMP,

    -- Competition setup
    timeframe TEXT NOT NULL, -- how long agents had to trade
    market_conditions TEXT, -- JSON of conditions during competition

    -- Participants (can be 2+ agents)
    participants TEXT NOT NULL, -- JSON array of agent IDs

    -- Results
    winner_id TEXT NOT NULL,
    rankings TEXT NOT NULL, -- JSON array of agent IDs in rank order
    performance_data TEXT, -- JSON of each agent's ROI, trades, etc.

    -- Evolution outcomes
    agents_eliminated TEXT, -- JSON array of eliminated agent IDs
    agents_cloned TEXT, -- JSON array of newly created agent IDs

    FOREIGN KEY (winner_id) REFERENCES trading_agents(agent_id)
);

-- Agent evolution lineage
CREATE TABLE IF NOT EXISTS agent_lineage (
    lineage_id TEXT PRIMARY KEY,
    ancestor_id TEXT NOT NULL,
    descendant_id TEXT NOT NULL,
    generation_gap INTEGER NOT NULL,
    mutation_type TEXT, -- 'personality_shift', 'pattern_preference', 'risk_tolerance', 'combination_strategy'
    mutation_details TEXT, -- JSON describing what changed
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ancestor_id) REFERENCES trading_agents(agent_id),
    FOREIGN KEY (descendant_id) REFERENCES trading_agents(agent_id)
);

-- Performance tracking over time
CREATE TABLE IF NOT EXISTS agent_performance_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    snapshot_timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    cycle_number INTEGER NOT NULL,

    -- Performance at this point in time
    total_trades INTEGER,
    win_rate REAL,
    total_roi REAL,
    avg_roi REAL,
    sharpe_ratio REAL,

    -- Learning progress
    memories_stored INTEGER,
    knowledge_items INTEGER,
    strategy_maturity REAL, -- 0-1 how refined strategy is

    FOREIGN KEY (agent_id) REFERENCES trading_agents(agent_id)
);

-- Model testing and research tables
CREATE TABLE IF NOT EXISTS model_test_results (
    test_id TEXT PRIMARY KEY,
    model_id TEXT NOT NULL,
    test_type TEXT NOT NULL,
    prompt TEXT,
    response TEXT,
    reasoning_quality REAL,
    response_time_ms INTEGER,
    coherence_score REAL,
    accuracy_score REAL,
    tested_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS research_log (
    log_id TEXT PRIMARY KEY,
    log_type TEXT NOT NULL,
    content TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_agent_memories_agent ON agent_memories(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_memories_timestamp ON agent_memories(decision_timestamp);
CREATE INDEX IF NOT EXISTS idx_agent_knowledge_agent ON agent_knowledge(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_knowledge_pattern ON agent_knowledge(pattern_id);
CREATE INDEX IF NOT EXISTS idx_agent_competitions_timestamp ON agent_competitions(competition_timestamp);
CREATE INDEX IF NOT EXISTS idx_agent_lineage_ancestor ON agent_lineage(ancestor_id);
CREATE INDEX IF NOT EXISTS idx_agent_lineage_descendant ON agent_lineage(descendant_id);
CREATE INDEX IF NOT EXISTS idx_model_test_results_model ON model_test_results(model_id);
CREATE INDEX IF NOT EXISTS idx_research_log_type ON research_log(log_type);
