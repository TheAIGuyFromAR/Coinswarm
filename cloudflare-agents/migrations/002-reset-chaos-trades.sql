-- Migration: Reset chaos trades for fresh start with REAL historical data
--
-- IMPORTANT: Only run this AFTER historical data collection has started
-- and the system is generating trades based on REAL data (not synthetic)
--
-- Check first:
-- SELECT COUNT(*) FROM price_data;  -- Should be 1000+ before running
--
-- This will delete all existing chaos trades (196,749 synthetic trades)
-- and reset the evolution system for a fresh start with real data.

-- 1. Delete all existing chaos trades
DELETE FROM chaos_trades;

-- 2. Reset agent performance tracking (optional - preserves agent evolution)
-- Uncomment if you want agents to start fresh too:
-- DELETE FROM agent_performance;

-- 3. Reset any pattern discovery data tied to old trades (if exists)
-- Uncomment if you have pattern tables:
-- DELETE FROM discovered_patterns;
-- DELETE FROM pattern_performance;

-- 4. Vacuum to reclaim space
VACUUM;

-- 5. Record the reset
INSERT INTO schema_migrations (migration_id, description, applied_at)
VALUES (
  'chaos-trades-reset-real-data-2025-11-10',
  'Reset chaos trades to start fresh with real historical data',
  unixepoch()
);

-- Verification queries to run after migration:
-- SELECT COUNT(*) FROM chaos_trades;  -- Should be 0
-- SELECT COUNT(*) FROM price_data;    -- Should be 1000+
-- SELECT MIN(timestamp), MAX(timestamp) FROM price_data;  -- Check data range
