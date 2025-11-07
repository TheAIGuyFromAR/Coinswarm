# 🚀 Fill 'Er Up! - Quick Deployment

## One Command to Rule Them All

```bash
./deploy-data-pipeline.sh
```

That's it! This will:
1. ✅ Create D1 database
2. ✅ Apply schema
3. ✅ Configure API keys
4. ✅ Deploy worker with cron trigger
5. ✅ Start backfilling immediately

---

## What Happens Next

The worker will run **every minute** and fetch historical data:

- **BTC, ETH, SOL**
- **5-minute, 1-hour, daily intervals**
- **2+ years of history**
- **~24,000 candles total**

**Completes in:** ~10-15 minutes

---

## Monitor Progress

### Quick Check
```bash
# Replace YOUR_URL with actual worker URL from deployment output
curl https://coinswarm-data-backfill.YOUR_SUBDOMAIN.workers.dev/progress
```

### Watch in Real-Time
```bash
watch -n 10 'curl -s https://coinswarm-data-backfill.YOUR_SUBDOMAIN.workers.dev/progress | jq'
```

### View Logs
```bash
wrangler tail --config wrangler-data-ingestion.toml
```

---

## Stop When Full

When progress stops increasing (data sources exhausted):

### Option 1: Disable Cron (Recommended)
```bash
# Edit wrangler-data-ingestion.toml
# Comment out the cron line:
# crons = ["* * * * *"]

# Redeploy
wrangler deploy --config wrangler-data-ingestion.toml
```

### Option 2: Delete Worker
```bash
wrangler delete --config wrangler-data-ingestion.toml
```

---

## Troubleshooting

### "wrangler: command not found"
```bash
npm install -g wrangler
```

### "Not logged in"
```bash
wrangler login
```

### Check what's in the database
```bash
wrangler d1 execute coinswarm-historical-data --command="
SELECT
  symbol,
  timeframe,
  COUNT(*) as candles,
  datetime(MIN(timestamp), 'unixepoch') as oldest,
  datetime(MAX(timestamp), 'unixepoch') as newest
FROM price_data
GROUP BY symbol, timeframe
"
```

---

## Manual Deployment (If Script Fails)

If the script fails, follow `AUTOMATED_DATA_PIPELINE_SETUP.md` for step-by-step manual instructions.

---

## Expected Output

```json
{
  "totalCandles": 3600,
  "coverage": [
    {
      "symbol": "BTC",
      "timeframe": "5m",
      "candle_count": 400,
      "oldest_date": "2025-11-05 12:00:00",
      "newest_date": "2025-11-06 12:00:00",
      "years_of_data": 0.0
    },
    ...
  ],
  "isComplete": false,
  "nextAction": "CONTINUE - More data to fetch"
}
```

After 10-15 minutes:
- `totalCandles`: ~24,000
- `years_of_data`: ~2.0 for each symbol/timeframe
- All symbols have data

---

## That's It!

Run `./deploy-data-pipeline.sh` and let it fill up! 🚀

Check progress every few minutes with:
```bash
curl https://YOUR_WORKER_URL/progress | jq
```

When `totalCandles` stops increasing, disable the cron and enjoy your fully-loaded database!
