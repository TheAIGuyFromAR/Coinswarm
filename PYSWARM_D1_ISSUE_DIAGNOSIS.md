# Pyswarm Historical Worker - D1 Write Issue Diagnosis

## Current Architecture

```
Python Worker (coinswarm-historical-import)
  ↓
  Fetches from CryptoCompare ✅ (working reliably)
  ↓
  Attempts Direct D1 Write ❌ (NOT working)

NO QUEUE IN BETWEEN
```

## Problems Found

### 1. **No Queue Configuration** ⚠️

**What You Expected:**
```
Fetch Data → Queue → Consumer → D1 Write
```

**What's Actually Configured:**
```
Fetch Data → Direct D1 Write (failing)
```

**Evidence:**
- `pyswarm/wrangler_historical_import.toml` has NO queue bindings
- `pyswarm/Data_Import/historical_worker.py` has NO queue code
- Only has D1 binding: `[[d1_databases]]`
- Missing: `[[queues.producers]]` configuration

### 2. **Direct D1 Write Issues**

**File:** `pyswarm/Data_Import/historical_worker.py`
**Line 84:** `await env.DB.prepare(sql).bind(*params).run()`

**Problems:**
1. **Bulk INSERT limits**: Lines 65-68 build a massive INSERT statement:
   ```python
   sql = (
       "INSERT OR IGNORE INTO price_data "
       "(symbol, timestamp, ...) VALUES "
       + ", ".join(["(?, ?, ?, ...)"] * len(candles))  # Could be 2000 rows!
   )
   ```
   - D1 has parameter limits (~1000 bindings per statement)
   - If `len(candles) = 2000`, you get 2000 × 10 params = 20,000 parameters
   - This exceeds D1's limits and causes silent failures

2. **No error handling**: The D1 write has no try/catch
   ```python
   await insert_candles_to_d1(env, symbol, candles, "1d", source)
   # ^ If this fails, error is swallowed
   ```

3. **Python Workers D1 support**: Python Workers are relatively new, D1 bindings may be buggy

### 3. **Database Mismatch**

**Wrangler Config:** `pyswarm/wrangler_historical_import.toml`
```toml
[[d1_databases]]
binding = "DB"
name = "history"
database_id = "ac4629b2-8240-4378-b3e3-e5262cd9b285"
```

**Code writes to:** `price_data` table
**This table should exist in:** database ID `ac4629b2-8240-4378-b3e3-e5262cd9b285` (coinswarm-evolution)

**Questions:**
- Is this table actually created in this database?
- Check schema with: `wrangler d1 execute ac4629b2-8240-4378-b3e3-e5262cd9b285 --command "SELECT name FROM sqlite_master WHERE type='table'"`

### 4. **Trigger Mechanism**

**The worker is HTTP-triggered, not cron:**
```python
if method == "POST" and (path == "trigger" or path == "/trigger"):
    # Fetch and insert data
```

**How is it being triggered?**
- Manual POST requests?
- Another worker calling it?
- Cron job somewhere?

If no one is calling this endpoint, the worker never runs!

## Root Cause Analysis

### Why Data Isn't Reaching D1:

**Most Likely Issues (in order):**

1. ⚠️ **Parameter Limit Exceeded**
   - Bulk INSERT with 2000 candles = 20,000 parameters
   - D1 limit: ~1000 parameters
   - Solution: Batch in groups of 100

2. ⚠️ **No Queue System**
   - You expected queue-based architecture
   - Current code has no queue bindings or code
   - Direct writes to D1 are failing silently

3. ⚠️ **Python Workers + D1 Compatibility**
   - Python Workers for D1 are beta/experimental
   - May have bugs or limitations
   - TypeScript workers are more mature

4. ⚠️ **Table Doesn't Exist**
   - The `price_data` table might not exist in database `ac4629b2-8240-4378-b3e3-e5262cd9b285`
   - Check with: `wrangler d1 execute <db-id> --command "PRAGMA table_info(price_data)"`

## How to Fix

### Option 1: Add Queue Support (Recommended)

**Update `pyswarm/wrangler_historical_import.toml`:**
```toml
name = "coinswarm-historical-import"
main = "Data_Import/historical_worker.py"
compatibility_date = "2025-11-10"
compatibility_flags = ["python_workers"]

[[d1_databases]]
binding = "DB"
name = "history"
database_id = "ac4629b2-8240-4378-b3e3-e5262cd9b285"

# ADD THIS:
[[queues.producers]]
queue = "pyswarm-historical-queue"
binding = "HISTORICAL_QUEUE"
```

**Update `pyswarm/Data_Import/historical_worker.py`:**
```python
async def insert_candles_to_d1(env, symbol, candles, timeframe, source):
    if not candles:
        return

    # Instead of direct D1 write, queue the data
    await env.HISTORICAL_QUEUE.send({
        "symbol": symbol,
        "candles": candles,
        "timeframe": timeframe,
        "source": source
    })
    print(f"Queued {len(candles)} candles for {symbol}")
```

**Create Queue Consumer (TypeScript - Python doesn't support queue consumers yet):**
```typescript
// pyswarm-historical-queue-consumer.ts
export default {
  async queue(batch: MessageBatch, env: Env) {
    for (const msg of batch.messages) {
      const { symbol, candles, timeframe, source } = msg.body;

      // Batch insert in groups of 100 (avoid parameter limit)
      const batches = chunkArray(candles, 100);
      for (const batch of batches) {
        const stmts = batch.map(candle =>
          env.DB.prepare(`
            INSERT OR IGNORE INTO price_data
            (symbol, timestamp, timeframe, open, high, low, close, volume_from, volume_to, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
          `).bind(
            symbol,
            candle.time,
            timeframe,
            candle.open,
            candle.high,
            candle.low,
            candle.close,
            candle.volumefrom || 0,
            candle.volumeto || 0,
            source
          )
        );
        await env.DB.batch(stmts);
      }
      msg.ack();
    }
  }
}
```

### Option 2: Fix Direct D1 Writes (Simpler but Less Reliable)

**Update `pyswarm/Data_Import/historical_worker.py` line 61:**
```python
async def insert_candles_to_d1(env, symbol, candles, timeframe, source):
    if not candles:
        return

    # Batch in groups of 100 to avoid parameter limits
    batch_size = 100
    for i in range(0, len(candles), batch_size):
        batch = candles[i:i+batch_size]

        sql = (
            "INSERT OR IGNORE INTO price_data "
            "(symbol, timestamp, timeframe, open, high, low, close, volume_from, volume_to, source) VALUES "
            + ", ".join(["(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"] * len(batch))
        )
        params = []
        for candle in batch:
            params.extend([
                symbol,
                candle["time"],
                timeframe,
                candle["open"],
                candle["high"],
                candle["low"],
                candle["close"],
                candle.get("volumefrom", 0),
                candle.get("volumeto", 0),
                source
            ])

        try:
            await env.DB.prepare(sql).bind(*params).run()
            print(f"Inserted batch of {len(batch)} candles")
        except Exception as e:
            print(f"Failed to insert batch: {e}")
            raise
```

## Verification Steps

### 1. Check if table exists:
```bash
wrangler d1 execute ac4629b2-8240-4378-b3e3-e5262cd9b285 \
  --command "SELECT name FROM sqlite_master WHERE type='table' AND name='price_data'" \
  --remote
```

### 2. Check if worker is deployed:
```bash
wrangler deployments list --name coinswarm-historical-import
```

### 3. Test the worker:
```bash
curl -X POST https://coinswarm-historical-import.YOUR-SUBDOMAIN.workers.dev/trigger
```

### 4. Check worker logs:
```bash
wrangler tail coinswarm-historical-import
```

### 5. Verify data in D1:
```bash
wrangler d1 execute ac4629b2-8240-4378-b3e3-e5262cd9b285 \
  --command "SELECT COUNT(*) FROM price_data" \
  --remote
```

## Summary

**The Problem:**
- Python worker fetches data successfully ✅
- No queue system configured ❌
- Direct D1 writes failing silently ❌
- Likely cause: Parameter limit exceeded (20,000 params vs 1000 limit)

**The Solution:**
- Option 1: Add queue system (more reliable, scales better)
- Option 2: Batch D1 writes in groups of 100 (simpler, less reliable)

**Next Steps:**
1. Run verification steps above to confirm diagnosis
2. Choose Option 1 or Option 2
3. I can implement the fix once you confirm which approach
