# Database Schema Initialization Required

## The Issue

The worker is deployed and running, but the D1 database doesn't have the required tables yet:
- `chaos_trades` - stores trading data
- `discovered_patterns` - stores AI-discovered patterns
- `system_stats` - stores system statistics

## Quick Fix (Run This Command)

```bash
wrangler d1 execute coinswarm-evolution --file=cloudflare-d1-evolution-schema.sql
```

Or use the script:
```bash
./init-evolution-db.sh
```

## What This Does

Creates 3 tables in your D1 database:

### 1. chaos_trades
Stores every random trade with:
- Entry/exit prices and times
- P&L and profitability
- Buy/sell justifications
- Market state (momentum, SMA, volume, volatility)

### 2. discovered_patterns
Stores patterns found by AI and statistical analysis:
- Pattern name and conditions
- Win rate and sample size
- AI reasoning and confidence
- Votes (upvotes/downvotes from testing)

### 3. system_stats
Tracks overall system statistics

## After Initialization

Once the tables are created, trigger another cycle:
```bash
curl -X POST https://coinswarm-evolution-agent.bamn86.workers.dev/trigger
```

The worker will:
1. ✅ Generate 50 chaos trades
2. ✅ Store them in D1
3. ✅ After 5 cycles: Run AI pattern analysis
4. ✅ After 10 cycles: Test strategies
5. ✅ Continue running every 60 seconds automatically

## Alternative: One-Command Fix

If you don't have wrangler locally, I can add a GitHub Action to do this automatically on push.

---

**The worker is healthy and ready - it just needs the database schema!**
