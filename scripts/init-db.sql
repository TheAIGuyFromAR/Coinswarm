-- Coinswarm PostgreSQL Initialization Script
-- Creates initial database schema for trades, patterns, and metadata

-- ============================================================================
-- Extensions
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text similarity search

-- ============================================================================
-- Trades Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Order information
    order_id VARCHAR(255) NOT NULL,
    client_order_id VARCHAR(255),
    product_id VARCHAR(50) NOT NULL,
    side VARCHAR(10) NOT NULL,  -- BUY, SELL
    order_type VARCHAR(20) NOT NULL,  -- MARKET, LIMIT, STOP_LIMIT

    -- Execution details
    status VARCHAR(50) NOT NULL,  -- OPEN, FILLED, CANCELLED, EXPIRED
    filled_size DECIMAL(20, 8),
    filled_value DECIMAL(20, 8),
    average_price DECIMAL(20, 8),
    fees DECIMAL(20, 8),

    -- Trade outcome
    pnl DECIMAL(20, 8),
    slippage_bps DECIMAL(10, 4),

    -- Context
    agent_id VARCHAR(100),
    pattern_ids TEXT[],
    regime VARCHAR(50),

    -- Timestamps
    order_placed_at TIMESTAMPTZ,
    order_filled_at TIMESTAMPTZ,

    -- Indexes
    INDEX idx_trades_product (product_id),
    INDEX idx_trades_status (status),
    INDEX idx_trades_agent (agent_id),
    INDEX idx_trades_created (created_at DESC),
    INDEX idx_trades_regime (regime)
);

-- ============================================================================
-- Patterns Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Pattern identification
    pattern_name VARCHAR(255) NOT NULL UNIQUE,
    pattern_type VARCHAR(50) NOT NULL,  -- trend, mean_reversion, arbitrage, etc.

    -- Pattern conditions
    conditions JSONB NOT NULL,
    regime_tags TEXT[],

    -- Performance metrics
    total_trades INTEGER NOT NULL DEFAULT 0,
    winning_trades INTEGER NOT NULL DEFAULT 0,
    losing_trades INTEGER NOT NULL DEFAULT 0,
    total_pnl DECIMAL(20, 8) NOT NULL DEFAULT 0,
    sharpe_ratio DECIMAL(10, 4),
    max_drawdown DECIMAL(10, 4),
    win_rate DECIMAL(5, 4),

    -- Quality gates
    promoted BOOLEAN NOT NULL DEFAULT FALSE,
    deprecated BOOLEAN NOT NULL DEFAULT FALSE,
    deprecated_reason TEXT,

    -- Metadata
    discovered_by VARCHAR(100),
    last_used_at TIMESTAMPTZ,

    -- Indexes
    INDEX idx_patterns_type (pattern_type),
    INDEX idx_patterns_promoted (promoted),
    INDEX idx_patterns_sharpe (sharpe_ratio DESC NULLS LAST),
    INDEX idx_patterns_updated (updated_at DESC)
);

-- ============================================================================
-- Regimes Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS regimes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Regime identification
    regime_name VARCHAR(100) NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,

    -- Market conditions
    volatility_regime VARCHAR(50),  -- low, medium, high
    trend_regime VARCHAR(50),  -- bullish, bearish, ranging
    liquidity_regime VARCHAR(50),  -- high, medium, low

    -- Characteristics
    avg_volatility DECIMAL(10, 4),
    avg_spread_bps DECIMAL(10, 4),
    avg_volume DECIMAL(20, 8),

    -- Products affected
    products TEXT[],

    -- Indexes
    INDEX idx_regimes_name (regime_name),
    INDEX idx_regimes_time (start_time DESC, end_time DESC NULLS LAST)
);

-- ============================================================================
-- Memory Episodes Table (for episodic memory backup)
-- ============================================================================
CREATE TABLE IF NOT EXISTS memory_episodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Episode identification
    bot_id VARCHAR(100) NOT NULL,
    episode_id VARCHAR(255) NOT NULL,

    -- State information
    state_vector BYTEA,  -- Binary embedding
    product_id VARCHAR(50) NOT NULL,
    regime VARCHAR(50),

    -- Action and outcome
    action VARCHAR(50) NOT NULL,
    pnl DECIMAL(20, 8),

    -- Pattern associations
    pattern_ids TEXT[],

    -- Metadata
    metadata JSONB,

    -- TTL for cleanup
    expires_at TIMESTAMPTZ NOT NULL,

    -- Indexes
    INDEX idx_episodes_bot (bot_id),
    INDEX idx_episodes_product (product_id),
    INDEX idx_episodes_regime (regime),
    INDEX idx_episodes_created (created_at DESC),
    INDEX idx_episodes_expires (expires_at)
);

-- ============================================================================
-- Agent States Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS agent_states (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Agent identification
    agent_id VARCHAR(100) NOT NULL UNIQUE,
    agent_type VARCHAR(50) NOT NULL,

    -- State
    status VARCHAR(50) NOT NULL,  -- active, paused, stopped, error
    last_heartbeat TIMESTAMPTZ,

    -- Configuration
    config JSONB,
    weights JSONB,

    -- Performance
    total_trades INTEGER NOT NULL DEFAULT 0,
    total_pnl DECIMAL(20, 8) NOT NULL DEFAULT 0,

    -- Indexes
    INDEX idx_agent_states_type (agent_type),
    INDEX idx_agent_states_status (status),
    INDEX idx_agent_states_heartbeat (last_heartbeat DESC)
);

-- ============================================================================
-- Quorum Votes Table (for audit trail)
-- ============================================================================
CREATE TABLE IF NOT EXISTS quorum_votes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Proposal information
    proposal_id VARCHAR(255) NOT NULL,
    coordinator_id VARCHAR(100) NOT NULL,

    -- Vote details
    manager_id VARCHAR(100) NOT NULL,
    decision VARCHAR(20) NOT NULL,  -- ACCEPT, REJECT
    vote_hash VARCHAR(64) NOT NULL,

    -- Outcome
    committed BOOLEAN NOT NULL DEFAULT FALSE,

    -- Indexes
    INDEX idx_votes_proposal (proposal_id),
    INDEX idx_votes_manager (manager_id),
    INDEX idx_votes_created (created_at DESC)
);

-- ============================================================================
-- Triggers for updated_at
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_trades_updated_at BEFORE UPDATE ON trades
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_patterns_updated_at BEFORE UPDATE ON patterns
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agent_states_updated_at BEFORE UPDATE ON agent_states
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Initial Data
-- ============================================================================
-- Insert default agent states placeholder (will be populated by agents on startup)
-- None for now - agents will self-register

-- ============================================================================
-- Cleanup Job for Expired Episodes
-- ============================================================================
-- Note: This should be run periodically via cron or application logic
-- DELETE FROM memory_episodes WHERE expires_at < NOW();
