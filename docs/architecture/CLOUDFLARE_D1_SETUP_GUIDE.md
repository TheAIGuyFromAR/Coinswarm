# 🗄️ Cloudflare D1 Setup Guide

Store 2+ years of historical crypto data in Cloudflare D1 for instant, rate-limit-free backtesting!

---

## Why Cloudflare D1?

✅ **Fast**: Global edge database, <10ms queries
✅ **Free Tier**: 5GB storage, 5M reads/day, 100K writes/day
✅ **No Rate Limits**: Data cached in your database
✅ **Serverless**: No infrastructure to manage
✅ **Perfect for Backtesting**: Store years of data, query instantly

---

## Step 1: Create D1 Database

```bash
# Install Wrangler (if not already installed)
npm install -g wrangler

# Login to Cloudflare
wrangler login

# Create D1 database
wrangler d1 create coinswarm-historical-data

# Note the database_id from the output!
# You'll see something like:
# [[d1_databases]]
# binding = "DB"
# database_name = "coinswarm-historical-data"
# database_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

---

## Step 2: Apply Database Schema

```bash
# Apply the schema
wrangler d1 execute coinswarm-historical-data --file=cloudflare-d1-schema.sql

# Verify tables were created
wrangler d1 execute coinswarm-historical-data --command="SELECT name FROM sqlite_master WHERE type='table'"
```

Expected output:
```
price_data
data_coverage
price_stats
```

---

## Step 3: Update Worker with D1 Binding

Add this to your `wrangler.toml` (or create it):

```toml
name = "coinswarm-data-fetcher"
main = "DEPLOY_TO_CLOUDFLARE_D1.js"
compatibility_date = "2024-01-01"

[[d1_databases]]
binding = "DB"  # This is how you'll access it in code
database_name = "coinswarm-historical-data"
database_id = "YOUR-DATABASE-ID-HERE"  # From step 1
```

---

## Step 4: Deploy Updated Worker

The new Worker will have endpoints to:
- `POST /store` - Store historical data in D1
- `GET /query` - Query data from D1
- `GET /stats` - Get summary statistics
- `GET /coverage` - See what data periods we have

```bash
# Deploy Worker with D1 binding
wrangler deploy
```

---

## Step 5: Populate Database with Historical Data

### Option A: Use Python Script (Recommended)

```bash
# Set Worker URL and Account ID
export WORKER_URL=https://coinswarm.bamn86.workers.dev
export CF_ACCOUNT_ID=8a330fc6c339f031a73905d4ca2f3e5d
export CF_API_TOKEN=cOTsKCt2SiDLz_suEOky--HkUQ4qwYd4hCPwAeZU

# Fetch and store 3 months of BTC data
python populate_d1_database.py --symbol BTC --months 3

# Fetch and store 6 months of BTC, ETH, SOL
python populate_d1_database.py --symbols BTC ETH SOL --months 6

# Build up to 2 years over time
python populate_d1_database.py --symbols BTC ETH SOL --months 24
```

### Option B: Use Worker Cron Job

Set up a cron job to automatically fetch and store new data:

```toml
# Add to wrangler.toml
[triggers]
crons = ["0 0 * * *"]  # Run daily at midnight
```

The Worker will automatically:
- Fetch yesterday's data
- Store in D1
- Update coverage metadata
- Calculate rolling statistics

---

## Step 6: Query Data for Backtesting

### Python Client

```python
from coinswarm.data_ingest.d1_client import D1Client

# Initialize client
client = D1Client("https://coinswarm.bamn86.workers.dev")

# Fetch 90 days of BTC data (instant, from D1!)
btc_data = await client.fetch_data("BTC", days=90)

# Query multiple symbols
data = await client.fetch_multiple(["BTC", "ETH", "SOL"], days=90)

# Get data coverage
coverage = await client.get_coverage("BTC")
print(f"BTC data: {coverage['start_date']} to {coverage['end_date']}")
```

### Direct HTTP Queries

```bash
# Get 30 days of BTC data
curl "https://coinswarm.bamn86.workers.dev/query?symbol=BTC&days=30"

# Get data coverage
curl "https://coinswarm.bamn86.workers.dev/coverage"

# Get statistics
curl "https://coinswarm.bamn86.workers.dev/stats?symbol=BTC&period=30d"
```

---

## Data Storage Estimates

### Free Tier Limits
- **Storage**: 5 GB
- **Reads**: 5M per day
- **Writes**: 100K per day

### Size Calculations

**Per candle** (1 row): ~200 bytes

**Storage needed:**
- 1 month (720 hours): 720 × 200 bytes = 144 KB
- 1 year (8,760 hours): 8,760 × 200 bytes = 1.7 MB
- 2 years: 3.4 MB
- **3 symbols × 2 years**: ~10 MB

**You can store 100+ years of 3 symbols in the free tier!**

### Read/Write Usage

**Daily backtest (typical)**:
- Query 90 days: ~2,200 candles = 1 read operation
- Run 100 backtests/day: 100 reads
- **Total**: 100 reads << 5M limit ✅

**Daily updates**:
- Store 24 new hourly candles × 3 symbols = 72 writes
- **Total**: 72 writes << 100K limit ✅

---

## Benefits for Backtesting

### Before D1 (External APIs):
- ❌ Rate limited
- ❌ Slow (network latency)
- ❌ Can't test offline
- ❌ Costs money for API calls
- ❌ Data might change/disappear

### After D1:
- ✅ **Instant queries** (<10ms)
- ✅ **No rate limits**
- ✅ **Consistent data**
- ✅ **Works offline** (Worker is always up)
- ✅ **Free** (within generous limits)
- ✅ **Global CDN** (fast worldwide)

---

## Maintenance

### Daily: Auto-Update
Cron job fetches latest data automatically.

### Weekly: Verify Coverage
```bash
python check_d1_coverage.py
```

### Monthly: Calculate Stats
```bash
python calculate_d1_stats.py
```

### Yearly: Archive Old Data (Optional)
```bash
python archive_d1_data.py --older-than 2y
```

---

## Next Steps

1. ✅ **Create D1 database** (`wrangler d1 create`)
2. ✅ **Apply schema** (`wrangler d1 execute`)
3. ✅ **Deploy Worker** with D1 binding
4. ✅ **Populate data** (start with 3 months, build to 2 years)
5. ✅ **Run backtests** with D1 data

---

## Troubleshooting

### Issue: "Database not found"
- Check `wrangler.toml` has correct `database_id`
- Verify database exists: `wrangler d1 list`

### Issue: "Quota exceeded"
- Check usage: `wrangler d1 info coinswarm-historical-data`
- Free tier: 5GB storage, 5M reads/day, 100K writes/day

### Issue: "Slow queries"
- Add indexes (already in schema)
- Use `EXPLAIN QUERY PLAN` to optimize

### Issue: "Missing data periods"
- Check coverage: `curl .../coverage`
- Backfill: `python populate_d1_database.py --backfill`

---

## Cost Estimate

**Free Tier**: $0/month (sufficient for development)

**Paid Tier** (if you exceed free tier):
- $0.75 per GB storage/month
- $0.001 per 1K reads
- $1.00 per 1M writes

**Example (10 symbols, 2 years, 1000 backtests/day)**:
- Storage: 30 MB = $0.02/month
- Reads: 30K/day = $0.90/month
- Writes: 240/day = $0.01/month
- **Total**: ~$1/month

---

## Summary

**Setup time**: 10 minutes
**Cost**: Free (or $1/month at scale)
**Result**: 2+ years of historical data, instant queries, no rate limits

**Perfect for**:
- Strategy development
- Robust backtesting
- Random window validation
- Multi-year analysis
- Production trading systems

Ready to set it up? Follow Step 1! 🚀
