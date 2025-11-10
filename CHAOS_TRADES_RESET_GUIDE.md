# Chaos Trades Reset Guide

## Why Reset?

The current 196,749 chaos trades were generated **without real historical data**. Once we have:
- ✅ 1,000+ records of REAL price data
- ✅ Chaos trading validation passing (using real data)

We need to **wipe the synthetic trades** and start fresh with trades based on REAL historical patterns.

---

## When to Reset

### Prerequisites (ALL must be true):

1. **Historical data collection is active**
   ```sql
   SELECT COUNT(*) FROM price_data;
   -- Should return 1,000+ records
   ```

2. **Data has good timeframe coverage**
   ```sql
   SELECT
     MIN(timestamp) as earliest,
     MAX(timestamp) as latest,
     COUNT(DISTINCT symbol) as num_symbols,
     COUNT(DISTINCT timeframe) as num_timeframes
   FROM price_data;
   -- Should show multiple symbols, multiple timeframes
   ```

3. **Chaos trading is generating trades with REAL data**
   ```sql
   SELECT COUNT(*) FROM chaos_trades
   WHERE created_at > unixepoch() - 3600;  -- Last hour
   -- Should show NEW trades being created
   ```

4. **Validation is passing**
   - Check evolution agent logs for: "✅ Historical data validation passed"
   - Should NOT see: "🚫 CHAOS TRADING BLOCKED"

---

## How to Reset

### Method 1: Via Wrangler (Recommended)

```bash
cd cloudflare-agents

# 1. First, verify you have enough real data
export CLOUDFLARE_API_TOKEN="your-token"
export CLOUDFLARE_ACCOUNT_ID="8a330fc6c339f031a73905d4ca2f3e5d"

npx wrangler d1 execute coinswarm-evolution --remote \
  --command "SELECT COUNT(*) as count FROM price_data"

# If count >= 1000, proceed:

# 2. Run the reset migration
npx wrangler d1 execute coinswarm-evolution --remote \
  --file=migrations/002-reset-chaos-trades.sql

# 3. Verify reset
npx wrangler d1 execute coinswarm-evolution --remote \
  --command "SELECT COUNT(*) as chaos_count FROM chaos_trades"
# Should return 0

# 4. Monitor new trades
npx wrangler d1 execute coinswarm-evolution --remote \
  --command "SELECT COUNT(*) as new_trades FROM chaos_trades WHERE created_at > unixepoch() - 600"
# Wait 10 minutes, should show new trades being created
```

### Method 2: Via Cloudflare Dashboard

1. Go to: https://dash.cloudflare.com/8a330fc6c339f031a73905d4ca2f3e5d/workers/d1
2. Click on `coinswarm-evolution` database
3. Click "Console" tab
4. Run verification query: `SELECT COUNT(*) FROM price_data;`
5. If >= 1000, copy/paste the migration SQL from `migrations/002-reset-chaos-trades.sql`
6. Click "Execute"

---

## What Gets Deleted

### ❌ DELETED:
- **chaos_trades table**: All 196,749 synthetic trades
- Optional: agent_performance (if you want agents to start fresh)
- Optional: discovered_patterns (if linked to synthetic trades)

### ✅ PRESERVED:
- **price_data**: All real historical data (untouched)
- **collection_progress**: Data collection tracking (untouched)
- **news_articles**: News and sentiment data (untouched)
- **sentiment_snapshots**: Sentiment history (untouched)
- **technical_indicators**: Calculated indicators (untouched)
- **All agent code**: Evolution logic intact (untouched)

---

## After Reset - What to Expect

### Timeline:

**First 10 minutes:**
- Evolution agent generates first chaos trades using REAL data
- Trades will have accurate historical context
- `validateHistoricalDataExists()` continues passing

**First hour:**
- ~100-500 new chaos trades generated
- Trades exploring different entry points, timeframes, strategies
- Pattern discovery begins with real data

**First 24 hours:**
- ~2,000-10,000 trades generated
- Early patterns emerging: "RSI oversold + volume spike = X% win rate"
- Agent evolution optimizing based on REAL outcomes

**First week:**
- ~50,000-100,000 trades
- Robust pattern discovery
- Top-performing agents identified
- Committee weights optimized

---

## Monitoring After Reset

### Check Data Collection Progress:
```sql
SELECT
  symbol,
  minutes_collected,
  hours_collected,
  days_collected,
  minute_status,
  hourly_status,
  daily_status
FROM collection_progress
ORDER BY minutes_collected DESC;
```

### Check New Chaos Trades:
```sql
SELECT
  COUNT(*) as total_trades,
  MIN(created_at) as first_trade,
  MAX(created_at) as last_trade,
  COUNT(DISTINCT agent_id) as num_agents,
  AVG(outcome) as avg_outcome
FROM chaos_trades
WHERE created_at > unixepoch() - 86400;  -- Last 24 hours
```

### Check Pattern Quality:
```sql
SELECT
  pattern,
  COUNT(*) as occurrences,
  AVG(outcome) as avg_outcome,
  COUNT(CASE WHEN outcome > 0 THEN 1 END) * 100.0 / COUNT(*) as win_rate
FROM chaos_trades
WHERE created_at > unixepoch() - 86400
GROUP BY pattern
HAVING COUNT(*) >= 10
ORDER BY win_rate DESC
LIMIT 20;
```

---

## Rollback (Emergency Only)

**There is NO rollback.** Once deleted, synthetic trades are gone forever.

If you reset by mistake:
1. Stop all workers to prevent new trades
2. The evolution system will regenerate trades automatically
3. New trades will be based on real data (which is actually better)

**Don't panic** - regenerating trades is the whole point of the chaos system!

---

## Automation Option

Want to auto-reset when data is ready? Add this to evolution agent:

```typescript
// In evolution-agent-simple.ts
private async checkAndResetIfReady(): Promise<void> {
  const priceDataCount = await this.env.DB.prepare(
    'SELECT COUNT(*) as count FROM price_data'
  ).first<{ count: number }>();

  const chaosTradeCount = await this.env.DB.prepare(
    'SELECT COUNT(*) as count FROM chaos_trades'
  ).first<{ count: number }>();

  // If we have real data (1000+) and old synthetic trades (>100k)
  if (priceDataCount?.count >= 1000 && chaosTradeCount?.count > 100000) {
    this.log('🔄 READY TO RESET: Real data available, wiping synthetic trades...');

    // Only reset once - check if already done
    const resetDone = await this.env.DB.prepare(
      "SELECT 1 FROM schema_migrations WHERE migration_id = 'chaos-trades-reset-real-data-2025-11-10'"
    ).first();

    if (!resetDone) {
      await this.env.DB.prepare('DELETE FROM chaos_trades').run();
      await this.env.DB.prepare(`
        INSERT INTO schema_migrations (migration_id, description, applied_at)
        VALUES ('chaos-trades-reset-real-data-2025-11-10', 'Auto-reset with real data', unixepoch())
      `).run();

      this.log('✅ RESET COMPLETE: Starting fresh with real historical data!');
    }
  }
}
```

---

## FAQ

**Q: Will this break the evolution system?**
A: No. The system is designed to generate trades continuously. It will immediately start generating new trades.

**Q: Will I lose agent evolution progress?**
A: No (unless you uncomment the agent_performance deletion). Agents retain their learned strategies.

**Q: How long until pattern discovery works again?**
A: 24-48 hours to rebuild a solid pattern base with real data.

**Q: Should I reset now or wait?**
A: **Wait** until you have at least 1,000 price_data records. Check with: `SELECT COUNT(*) FROM price_data;`

**Q: Can I do a partial reset (keep some trades)?**
A: Yes, modify the migration:
```sql
-- Keep trades from last hour (presumably real)
DELETE FROM chaos_trades WHERE created_at < unixepoch() - 3600;
```

---

**Status:** Ready to execute once historical data collection reaches 1,000+ records.
