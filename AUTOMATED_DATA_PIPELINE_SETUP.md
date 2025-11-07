# 🚀 Automated Data Pipeline Setup

Complete guide to set up aggressive historical data backfilling into Cloudflare D1.

---

## 🎯 What This Does

**Automatically fetches and stores historical crypto data:**
- Runs every minute until data sources are exhausted
- Fetches from CryptoCompare API (2000+ days available)
- Stores in Cloudflare D1 (5GB free, globally distributed)
- Handles rate limits intelligently (auto-retry with backoff)
- Tracks progress and deduplicates data
- Supports BTC, ETH, SOL at 5m, 1h, 1d intervals

**End Result:**
- Local database with maximum historical data
- No API calls needed for backtesting
- Sub-10ms query times (edge database)
- Free forever (within Cloudflare free tier)

---

## 📋 Prerequisites

1. **Cloudflare account** (free tier OK)
2. **Wrangler CLI** installed
3. **CryptoCompare API key** (you have: `da672b9999120841fbd4427fa4550b83b5f23e017c5c03ff33bafe09064abe83`)

---

## 🔧 Step-by-Step Setup

### Step 1: Create D1 Database

```bash
# Create the database
wrangler d1 create coinswarm-historical-data

# IMPORTANT: Copy the database_id from output
# It will look like: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

**Save the database_id!** You'll need it in Step 3.

### Step 2: Apply Database Schema

```bash
# Apply the schema to create tables
wrangler d1 execute coinswarm-historical-data --file=cloudflare-d1-schema.sql

# Verify tables were created
wrangler d1 execute coinswarm-historical-data --command="SELECT name FROM sqlite_master WHERE type='table'"
```

**Expected output:**
```
price_data
data_coverage
price_stats
```

### Step 3: Update Wrangler Config

Edit `wrangler-data-ingestion.toml` and replace `REPLACE_WITH_YOUR_D1_DATABASE_ID` with your actual database_id from Step 1:

```toml
[[d1_databases]]
binding = "DB"
database_name = "coinswarm-historical-data"
database_id = "YOUR_DATABASE_ID_HERE"  # ← PUT YOUR ID HERE
```

### Step 4: Set API Key Secret

```bash
# Set your CryptoCompare API key as a secret
wrangler secret put CRYPTOCOMPARE_API_KEY --config wrangler-data-ingestion.toml

# When prompted, paste: da672b9999120841fbd4427fa4550b83b5f23e017c5c03ff33bafe09064abe83
```

### Step 5: Deploy the Worker

```bash
# Deploy the backfill worker
wrangler deploy --config wrangler-data-ingestion.toml

# Output will show your worker URL, e.g.:
# https://coinswarm-data-backfill.YOUR_SUBDOMAIN.workers.dev
```

---

## ✅ Verify It's Working

### Check Status

```bash
curl https://coinswarm-data-backfill.YOUR_SUBDOMAIN.workers.dev/progress
```

**Expected response:**
```json
{
  "totalCandles": 0,
  "coverage": [],
  "isComplete": false,
  "nextAction": "CONTINUE - More data to fetch",
  "lastUpdated": "2025-11-06T..."
}
```

### Trigger Manual Backfill (Test)

```bash
curl https://coinswarm-data-backfill.YOUR_SUBDOMAIN.workers.dev/backfill
```

**Expected response:**
```json
{
  "timestamp": "2025-11-06T...",
  "symbols": {
    "BTC": {
      "5m": { "inserted": 400, "skipped": 0, "apiCalls": 1 },
      "1h": { "inserted": 400, "skipped": 0, "apiCalls": 1 },
      "1d": { "inserted": 400, "skipped": 0, "apiCalls": 1 }
    },
    "ETH": { ... },
    "SOL": { ... }
  },
  "totalInserted": 3600,
  "totalSkipped": 0,
  "apiCalls": 9,
  "errors": [],
  "isComplete": false,
  "duration": "12.3s"
}
```

---

## 📊 Monitor Progress

### Option 1: Progress Endpoint

```bash
# Check progress every few minutes
watch -n 60 'curl -s https://coinswarm-data-backfill.YOUR_SUBDOMAIN.workers.dev/progress | jq'
```

### Option 2: Cloudflare Dashboard

1. Go to **Cloudflare Dashboard** → **Workers & Pages**
2. Click on `coinswarm-data-backfill`
3. Go to **Logs** tab
4. Watch real-time backfill progress

### Option 3: Query D1 Directly

```bash
# Check total candles
wrangler d1 execute coinswarm-historical-data --command="SELECT COUNT(*) as total FROM price_data"

# Check coverage by symbol
wrangler d1 execute coinswarm-historical-data --command="
SELECT
  symbol,
  timeframe,
  COUNT(*) as candles,
  datetime(MIN(timestamp), 'unixepoch') as oldest,
  datetime(MAX(timestamp), 'unixepoch') as newest,
  ROUND((julianday('now') - julianday(MIN(timestamp), 'unixepoch')) / 365.25, 1) as years
FROM price_data
GROUP BY symbol, timeframe
"
```

---

## ⚙️ How It Works

### Cron Schedule

Worker runs **every minute** (`* * * * *`) automatically via Cloudflare Cron Triggers.

Each run:
1. Checks what data is already in D1
2. Fetches the oldest missing data for each symbol/interval
3. Inserts new candles (ignores duplicates)
4. Updates coverage metadata
5. Sleeps 1 second between API calls to avoid 429s
6. Retries 3 times with backoff on errors

### Rate Limit Handling

- **1 second delay** between API requests
- **5 second backoff** on 429 errors
- **3 retries** with exponential backoff
- **Batch inserts** to D1 (500 candles per batch)

### Data Flow

```
CryptoCompare API
      ↓
Backfill Worker (every minute)
      ↓
Cloudflare D1 Database
      ↓
Your Backtesting / Trading System
```

---

## 📈 Expected Timeline

**Fetch Speed:**
- ~400 candles per API call
- ~9 API calls per minute (3 symbols × 3 intervals)
- ~3,600 candles per minute

**Total Data:**
- BTC: ~8,000 candles (5m, 1h, 1d combined)
- ETH: ~8,000 candles
- SOL: ~8,000 candles
- **Total: ~24,000 candles**

**Estimated Time:**
- Full backfill: **~7-10 minutes**
- Limited by: API rate limits and 1-second delays

**Free Tier Usage:**
- API calls: ~90 per minute × 10 minutes = ~900 calls (well within 100k/month)
- D1 writes: ~3,600 per minute × 10 minutes = ~36,000 writes (well within 100k/day)

---

## 🛑 Stopping the Backfill

### When to Stop

The worker will keep running until you manually stop it. Stop when:

1. **Progress endpoint shows no new inserts:**
   ```bash
   curl https://coinswarm-data-backfill.YOUR_SUBDOMAIN.workers.dev/progress
   ```
   If `totalCandles` stops increasing, backfill is done.

2. **Coverage looks good:**
   Check that you have 2+ years of data for all symbols.

### How to Stop

**Option 1: Disable Cron Trigger (Recommended)**

Edit `wrangler-data-ingestion.toml`:
```toml
# Comment out the cron trigger
# [triggers]
# crons = ["* * * * *"]
```

Redeploy:
```bash
wrangler deploy --config wrangler-data-ingestion.toml
```

**Option 2: Delete the Worker**

```bash
wrangler delete --config wrangler-data-ingestion.toml
```

---

## 🔍 Troubleshooting

### No Data Being Inserted

**Check logs:**
```bash
wrangler tail --config wrangler-data-ingestion.toml
```

**Common issues:**
- API key not set: Run Step 4 again
- Database not bound: Check `database_id` in wrangler.toml
- Rate limits: Worker will auto-retry, just wait

### 429 Rate Limit Errors

**This is normal!** The worker will:
- Wait 5 seconds
- Retry up to 3 times
- Continue with next symbol/interval if persistent

Just let it run - it will work through the rate limits.

### Progress Stopped

If progress stops but you're not at maximum history:

**Trigger manual backfill:**
```bash
curl https://coinswarm-data-backfill.YOUR_SUBDOMAIN.workers.dev/backfill
```

**Check if cron is still running:**
```bash
wrangler deployments list --config wrangler-data-ingestion.toml
```

---

## 🎯 Next Steps

**After Backfill Completes:**

1. **Stop the cron trigger** (save resources)

2. **Query your data:**
   ```bash
   wrangler d1 execute coinswarm-historical-data --command="
   SELECT * FROM price_data WHERE symbol='BTC' AND timeframe='1h' ORDER BY timestamp DESC LIMIT 10
   "
   ```

3. **Use in your trading system:**
   - Update your worker to query D1 instead of external APIs
   - Sub-10ms query times globally
   - No rate limits
   - Free forever

4. **Set up daily updates:**
   - Change cron to `0 0 * * *` (daily at midnight)
   - Redeploy
   - Keeps data fresh with minimal API calls

---

## 📝 Summary

**What You Built:**
- ✅ Automated data pipeline (Cloudflare Worker + D1)
- ✅ Aggressive backfilling (every minute until exhausted)
- ✅ Rate limit handling (auto-retry with backoff)
- ✅ Progress tracking (/progress endpoint)
- ✅ Free tier optimized (batch inserts, smart delays)

**Deployment Commands:**
```bash
# 1. Create database
wrangler d1 create coinswarm-historical-data

# 2. Apply schema
wrangler d1 execute coinswarm-historical-data --file=cloudflare-d1-schema.sql

# 3. Update wrangler-data-ingestion.toml with database_id

# 4. Set API key
wrangler secret put CRYPTOCOMPARE_API_KEY --config wrangler-data-ingestion.toml

# 5. Deploy
wrangler deploy --config wrangler-data-ingestion.toml

# 6. Monitor
curl https://coinswarm-data-backfill.YOUR_SUBDOMAIN.workers.dev/progress
```

**Result:**
- Backfill completes in ~10 minutes
- ~24,000 candles stored in D1
- 2+ years of historical data
- Ready for backtesting and live trading

---

🚀 **Ready to start? Run the commands above!**
