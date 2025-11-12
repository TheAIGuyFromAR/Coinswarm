# Where Each Historical Worker's Data Goes

## Summary of ALL Historical Workers

You have **4 different historical data workers** doing different things:

---

## 1. ✅ **historical-data-collection-cron.ts** (WORKING)

**Status:** 24 triggers/day, 7000 requests

**Where data goes:**
```
Fetch from APIs → D1 Database `price_data` table
```

**Database:**
- Name: `coinswarm-evolution`
- ID: `ac4629b2-8240-4378-b3e3-e5262cd9b285`

**Table:** `price_data`
```sql
INSERT OR IGNORE INTO price_data (
  symbol, timestamp, timeframe, open, high, low, close,
  volume_from, volume_to, source
) VALUES (...)
```

**Data sources:**
- CryptoCompare (minute data)
- CoinGecko (daily data)
- Binance (hourly data)

**This is probably where your 200MB is!** ✅

---

## 2. ❌ **historical-data-queue-producer.ts** (FAILING SILENTLY)

**Status:** 96 runs/day (working), but consumer failing

**Where data SHOULD go:**
```
Fetch from APIs → Queue → Consumer → D1 Database
```

**What's ACTUALLY happening:**
```
Fetch from APIs → Queue → Consumer → ❌ FAILS
                                      (tries to write to non-existent table)
```

**Database config:**
- Name: `coinswarm-db`
- ID: `YOUR_D1_DATABASE_ID` ❌ PLACEHOLDER!

**Consumer tries to write to:** `historical_prices` (doesn't exist)
**Should write to:** `price_data` (exists, has your 200MB)

**Result:** Data queued, consumer receives it, tries to write, fails, acks anyway, data lost

---

## 3. ❓ **historical-data-worker.ts** (KV-BASED)

**Status:** 7000 requests (same as cron?)

**Where data goes:**
```
Fetch from Binance → KV Storage (NOT D1!)
```

**Storage:** `HISTORICAL_PRICES` KV namespace

**Purpose:** Different use case
- Stores raw JSON datasets in KV
- 30-day expiration
- For quick retrieval/caching
- NOT for long-term D1 storage

**This is NOT your 200MB** - KV is temporary cache

---

## 4. ❌ **pyswarm/Data_Import/historical_worker.py** (FAILING)

**Status:** Gets data reliably, doesn't write to D1

**Where data SHOULD go:**
```
Fetch from CryptoCompare → D1 Database `price_data` table
```

**Database:**
- ID: `ac4629b2-8240-4378-b3e3-e5262cd9b285` (same as cron)

**Problem:** Bulk INSERT with 2000 rows × 10 params = 20,000 parameters
- D1 limit: ~1000 parameters
- **Result:** Silent failure, no data written

**Also:** No queue configured (writes direct to D1)

---

## Your 200MB Data

**Most likely location:**
```
Database: ac4629b2-8240-4378-b3e3-e5262cd9b285 (coinswarm-evolution)
Table: price_data
Source: Manual fetch + historical-data-collection-cron.ts
```

**Verify with:**
```bash
wrangler d1 execute ac4629b2-8240-4378-b3e3-e5262cd9b285 \
  --command "SELECT COUNT(*) as total, source, timeframe FROM price_data GROUP BY source, timeframe" \
  --remote
```

---

## What Should Be Using Queues?

**Currently using direct D1 writes:**
- ❌ historical-data-collection-cron.ts (24/day) → slow, no retry
- ❌ pyswarm historical_worker.py → broken

**Should be using queues:**
- ✅ historical-data-queue-producer.ts (already is!)
- ❌ But consumer is writing to wrong table

---

## The Fix

### Option 1: Fix Queue Consumer (Recommended)

Point the queue consumer to your existing `price_data` table:

**File:** `cloudflare-agents/historical-data-queue-consumer.ts`

**Change line 113 from:**
```typescript
INSERT OR IGNORE INTO historical_prices (
  symbol, timestamp, open, high, low, close, volume, source, created_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
```

**To:**
```typescript
INSERT OR IGNORE INTO price_data (
  symbol, timestamp, timeframe, open, high, low, close,
  volume_from, volume_to, source
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
```

**Also update the binding:**
```typescript
.bind(
  point.symbol,
  point.timestamp,
  '1h',              // Add timeframe
  point.open,
  point.high,
  point.low,
  point.close,
  point.volume,      // volume_from
  point.volume,      // volume_to (or 0 if separate)
  point.source
);
```

**And fix wrangler config:**
```toml
# wrangler-historical-queue.toml
database_id = "ac4629b2-8240-4378-b3e3-e5262cd9b285"  # Use real ID!
```

### Option 2: Migrate Everything to Queue System

1. Fix queue consumer (above)
2. Disable old cron worker
3. Only use queue-based architecture going forward

---

## Data Flow After Fix

```
┌─────────────────────────────────────────────────────────────┐
│ historical-data-queue-producer.ts (96 runs/day)             │
│ Fetches from Binance/CoinGecko/CryptoCompare               │
└─────────────────────────────────────────────────────────────┘
                        ↓
                  [Queue: 1M ops/month free]
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ historical-data-queue-consumer.ts (batched writes)         │
│ INSERT OR IGNORE INTO price_data                           │
│ - Skips duplicates (your 200MB safe)                       │
│ - Adds new data                                             │
│ - Fills gaps                                                │
└─────────────────────────────────────────────────────────────┘
                        ↓
        Database: ac4629b2-8240-4378-b3e3-e5262cd9b285
        Table: price_data (has your 200MB + new data)
```

---

## Summary

| Worker | Where Data Goes | Status | Fix Needed |
|--------|-----------------|--------|------------|
| **historical-data-collection-cron.ts** | D1 `price_data` | ✅ Working | None |
| **historical-data-queue-producer** | Queue | ✅ Working | None |
| **historical-data-queue-consumer** | D1 `historical_prices` ❌ | ❌ Failing | Point to `price_data` |
| **historical-data-worker.ts** | KV Storage | ✅ Working | None (different purpose) |
| **pyswarm historical_worker.py** | D1 `price_data` | ❌ Failing | Batch writes or use queue |

**Main issue:** Queue consumer writes to wrong table (`historical_prices` instead of `price_data`)

**Your 200MB is safe** in `price_data` table in database `ac4629b2-8240-4378-b3e3-e5262cd9b285`

**Next step:** Fix the queue consumer to write to `price_data`, then it will add to your existing data without conflicts.
