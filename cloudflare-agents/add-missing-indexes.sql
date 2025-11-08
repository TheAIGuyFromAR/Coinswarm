-- Add Missing Performance Indexes
-- Improves query performance on foreign keys and common queries
-- Safe to run multiple times (IF NOT EXISTS)

-- Migration tracking
CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_id TEXT PRIMARY KEY,
    applied_at INTEGER DEFAULT (cast(strftime('%s', 'now') as integer)),
    description TEXT,
    status TEXT DEFAULT 'success'
);

-- ===================================================================
-- FOREIGN KEY INDEXES
-- ===================================================================
-- Foreign keys without indexes cause slow JOIN operations
-- These should have been added when foreign keys were created

-- Agent knowledge sharing - foreign key indexes
CREATE INDEX IF NOT EXISTS idx_knowledge_sharing_teacher_fk
  ON agent_knowledge_sharing(teacher_agent_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_sharing_student_fk
  ON agent_knowledge_sharing(student_agent_id);

-- Agent lineage - foreign key indexes
CREATE INDEX IF NOT EXISTS idx_lineage_ancestor_fk
  ON agent_lineage(ancestor_id);

CREATE INDEX IF NOT EXISTS idx_lineage_descendant_fk
  ON agent_lineage(descendant_id);

-- Agent competitions - foreign key to agents
CREATE INDEX IF NOT EXISTS idx_competitions_winner_fk
  ON agent_competitions(winner_id);

-- ===================================================================
-- PERFORMANCE INDEXES FOR COMMON QUERIES
-- ===================================================================

-- Chaos trades - pattern discovery queries
-- "Find all profitable trades with pattern X"
CREATE INDEX IF NOT EXISTS idx_chaos_trades_pattern_profitable
  ON chaos_trades(pattern_id, profitable);

-- "Find trades in specific date range"
CREATE INDEX IF NOT EXISTS idx_chaos_trades_entry_time
  ON chaos_trades(entry_time DESC);

-- "Find trades with specific technical indicators"
CREATE INDEX IF NOT EXISTS idx_chaos_trades_rsi_oversold
  ON chaos_trades(entry_rsi_14) WHERE entry_rsi_14 < 30;

CREATE INDEX IF NOT EXISTS idx_chaos_trades_rsi_overbought
  ON chaos_trades(entry_rsi_14) WHERE entry_rsi_14 > 70;

-- "Find trades during specific volatility"
CREATE INDEX IF NOT EXISTS idx_chaos_trades_volatility
  ON chaos_trades(entry_volatility);

-- Discovered patterns - performance indexes
-- "Find patterns by confidence score"
CREATE INDEX IF NOT EXISTS idx_patterns_confidence
  ON discovered_patterns(confidence_score DESC);

-- "Find patterns by last success"
CREATE INDEX IF NOT EXISTS idx_patterns_last_success
  ON discovered_patterns(last_success_date DESC);

-- "Find patterns by sample size"
CREATE INDEX IF NOT EXISTS idx_patterns_sample_size
  ON discovered_patterns(sample_size DESC);

-- "Find winning patterns"
CREATE INDEX IF NOT EXISTS idx_patterns_win_rate
  ON discovered_patterns(win_rate DESC) WHERE sample_size >= 10;

-- Trading agents - leaderboard queries
-- "Get top agents by fitness"
CREATE INDEX IF NOT EXISTS idx_agents_fitness_score
  ON trading_agents(fitness_score DESC) WHERE status = 'active';

-- "Get agents by generation"
CREATE INDEX IF NOT EXISTS idx_agents_generation
  ON trading_agents(generation DESC);

-- "Find active agents"
CREATE INDEX IF NOT EXISTS idx_agents_status
  ON trading_agents(status) WHERE status = 'active';

-- "Get agents by total ROI"
CREATE INDEX IF NOT EXISTS idx_agents_total_roi
  ON trading_agents(total_roi DESC);

-- Agent memories - decision retrieval
-- "Find recent memories for an agent"
CREATE INDEX IF NOT EXISTS idx_memories_agent_cycle
  ON agent_memories(agent_id, cycle_number DESC);

-- "Find memories with high confidence"
CREATE INDEX IF NOT EXISTS idx_memories_confidence
  ON agent_memories(confidence_level DESC) WHERE confidence_level >= 0.7;

-- Agent decisions - pattern usage tracking
-- "Find decisions using specific pattern"
CREATE INDEX IF NOT EXISTS idx_decisions_pattern
  ON agent_decisions(pattern_id);

-- "Find decisions by cycle"
CREATE INDEX IF NOT EXISTS idx_decisions_cycle
  ON agent_decisions(cycle_number DESC);

-- Historical prices - time-series queries
CREATE INDEX IF NOT EXISTS idx_price_data_symbol_time
  ON price_data(symbol, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_price_data_interval
  ON price_data(interval);

-- Sentiment snapshots - time-based queries
CREATE INDEX IF NOT EXISTS idx_sentiment_fear_greed
  ON sentiment_snapshots(fear_greed_index);

CREATE INDEX IF NOT EXISTS idx_sentiment_timestamp_regime
  ON sentiment_snapshots(timestamp DESC, market_regime);

-- News articles - search and filter
CREATE INDEX IF NOT EXISTS idx_news_sentiment_published
  ON news_articles(sentiment_score, published_on DESC);

CREATE INDEX IF NOT EXISTS idx_news_symbols
  ON news_articles(symbols) WHERE symbols IS NOT NULL;

-- ===================================================================
-- COMPOSITE INDEXES FOR COMPLEX QUERIES
-- ===================================================================

-- Pattern discovery: "Find profitable trades with sentiment"
CREATE INDEX IF NOT EXISTS idx_chaos_sentiment_profitable_compound
  ON chaos_trades(profitable, sentiment_fear_greed, sentiment_regime)
  WHERE sentiment_fear_greed IS NOT NULL;

-- Pattern analysis: "Win rate by pattern and market regime"
CREATE INDEX IF NOT EXISTS idx_chaos_pattern_regime_profitable
  ON chaos_trades(pattern_id, sentiment_regime, profitable);

-- Agent performance: "Active agents by fitness and generation"
CREATE INDEX IF NOT EXISTS idx_agents_active_fitness_gen
  ON trading_agents(status, fitness_score DESC, generation DESC);

-- Competition history: "Recent competitions with results"
CREATE INDEX IF NOT EXISTS idx_competitions_time_winner
  ON agent_competitions(competition_date DESC, winner_id);

-- Learning patterns: "Knowledge shared between agents"
CREATE INDEX IF NOT EXISTS idx_knowledge_teacher_type_confidence
  ON agent_knowledge_sharing(teacher_agent_id, knowledge_type, confidence DESC);

-- ===================================================================
-- INDEXES FOR AGGREGATION QUERIES
-- ===================================================================

-- "Count trades per pattern"
CREATE INDEX IF NOT EXISTS idx_chaos_trades_pattern_count
  ON chaos_trades(pattern_id, profitable);

-- "Average ROI per agent"
CREATE INDEX IF NOT EXISTS idx_agents_roi_trades
  ON trading_agents(agent_id, total_roi, total_trades) WHERE status = 'active';

-- "Pattern success rate over time"
CREATE INDEX IF NOT EXISTS idx_patterns_time_success
  ON discovered_patterns(discovered_at DESC, win_rate DESC, sample_size);

-- ===================================================================
-- INDEXES FOR DASHBOARD/API QUERIES
-- ===================================================================

-- Dashboard: Recent activity
CREATE INDEX IF NOT EXISTS idx_chaos_recent_activity
  ON chaos_trades(entry_time DESC, profitable);

-- Dashboard: Top patterns today
CREATE INDEX IF NOT EXISTS idx_patterns_recent_performance
  ON discovered_patterns(last_success_date DESC, win_rate DESC);

-- API: Agent leaderboard
CREATE INDEX IF NOT EXISTS idx_agents_leaderboard
  ON trading_agents(status, fitness_score DESC, total_trades DESC)
  WHERE status = 'active';

-- API: Pattern leaderboard
CREATE INDEX IF NOT EXISTS idx_patterns_leaderboard
  ON discovered_patterns(win_rate DESC, sample_size DESC, confidence_score DESC)
  WHERE sample_size >= 10;

-- ===================================================================
-- COVERING INDEXES (Include frequently accessed columns)
-- ===================================================================

-- Trades with key metrics (avoid table lookups)
CREATE INDEX IF NOT EXISTS idx_chaos_trades_metrics
  ON chaos_trades(pattern_id, profitable, pnl_pct, entry_time DESC);

-- Patterns with performance metrics
CREATE INDEX IF NOT EXISTS idx_patterns_performance
  ON discovered_patterns(pattern_id, win_rate, sample_size, confidence_score);

-- Agents with stats
CREATE INDEX IF NOT EXISTS idx_agents_stats
  ON trading_agents(agent_id, fitness_score, total_trades, win_rate)
  WHERE status = 'active';

-- ===================================================================
-- RECORD MIGRATION
-- ===================================================================

INSERT OR IGNORE INTO schema_migrations (migration_id, description)
VALUES ('add-missing-indexes-2025-11-08', 'Add comprehensive performance indexes for foreign keys, queries, and dashboards');

-- ===================================================================
-- VERIFICATION QUERIES
-- ===================================================================

-- To verify indexes were created, run:
-- SELECT name, tbl_name, sql FROM sqlite_master WHERE type = 'index' ORDER BY tbl_name, name;

-- To check index usage:
-- EXPLAIN QUERY PLAN SELECT * FROM chaos_trades WHERE profitable = 1 AND sentiment_fear_greed < 25;

-- To see table sizes:
-- SELECT
--   name,
--   (SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND tbl_name=m.name) as index_count
-- FROM sqlite_master m
-- WHERE m.type='table'
-- ORDER BY name;
