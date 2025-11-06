# 🚀 One-Time Setup, Then Auto-Deploy Forever

## The Flow

1. **One-time manual setup** (5 minutes) - Create D1 database
2. **Commit wrangler config** - GitHub Actions auto-deploys
3. **Done!** - Every future update auto-deploys

---

## Step 1: One-Time D1 Database Setup

You only need to do this **once**. After this, everything auto-deploys via GitHub Actions.

### 1a. Create D1 Database

```bash
wrangler d1 create coinswarm-historical-data
```

**Save the `database_id` from the output!** It looks like:
```
database_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

### 1b. Apply Schema

```bash
wrangler d1 execute coinswarm-historical-data --file=cloudflare-d1-schema.sql
```

Verify it worked:
```bash
wrangler d1 execute coinswarm-historical-data --command="SELECT name FROM sqlite_master WHERE type='table'"
```

Should show: `price_data`, `data_coverage`, `price_stats`

### 1c. Add GitHub Secrets (if not already done)

Go to: https://github.com/TheAIGuyFromAR/Coinswarm/settings/secrets/actions

Add these secrets:

1. **`CLOUDFLARE_API_TOKEN`** (if not already added)
   - Value: `rvXIkCIXf778QSR1tVlHHjjPqh3x3xRLJ73zmikf`

2. **`CRYPTOCOMPARE_API_KEY`**
   - Value: `da672b9999120841fbd4427fa4550b83b5f23e017c5c03ff33bafe09064abe83`

---

## Step 2: Update Database ID in Config

Edit `wrangler-data-ingestion.toml`:

```toml
[[d1_databases]]
binding = "DB"
database_name = "coinswarm-historical-data"
database_id = "PUT_YOUR_DATABASE_ID_HERE"  # ← Replace with ID from Step 1a
```

---

## Step 3: Commit and Push = Auto-Deploy! 🎉

```bash
git add wrangler-data-ingestion.toml
git commit -m "Configure D1 database for backfill worker"
git push origin claude/debug-cloudflare-historical-data-011CUqugUynEoovcsiVnoaPB
```

**That's it!** GitHub Actions will automatically:
- ✅ Deploy the backfill worker
- ✅ Configure the D1 database binding
- ✅ Set the API key secret
- ✅ Enable the cron trigger (runs every minute)

---

## Step 4: Monitor Deployment

### Watch GitHub Actions

Go to: https://github.com/TheAIGuyFromAR/Coinswarm/actions

You'll see "Deploy Data Backfill Worker" running. Wait for the green checkmark ✅.

### Get Worker URL

After deployment succeeds, your worker will be at:
```
https://coinswarm-data-backfill.YOUR_SUBDOMAIN.workers.dev
```

Find the exact URL in the GitHub Actions logs.

### Check Progress

```bash
curl https://coinswarm-data-backfill.YOUR_SUBDOMAIN.workers.dev/progress
```

---

## From Now On: Auto-Deploy on Every Commit

Now that setup is done, **any changes to these files auto-deploy:**

- `cloudflare-workers/data-backfill-worker.js`
- `wrangler-data-ingestion.toml`
- `.github/workflows/deploy-backfill-worker.yml`

Just commit and push. GitHub Actions does the rest!

---

## How the Backfill Works

Once deployed:

- **Runs every minute** (cron: `* * * * *`)
- **Fetches historical data** from CryptoCompare
- **Stores in D1** with deduplication
- **Handles rate limits** with exponential backoff
- **Targets:** BTC, ETH, SOL at 5m, 1h, 1d intervals
- **Fills ~3,600 candles/minute**
- **Completes in ~10-15 minutes**

---

## Monitor Progress

### Quick Check
```bash
curl https://YOUR_WORKER_URL/progress | jq
```

### Watch Live
```bash
watch -n 10 'curl -s https://YOUR_WORKER_URL/progress | jq .totalCandles'
```

### View Logs
```bash
wrangler tail coinswarm-data-backfill
```

### Query D1 Directly
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

## Stop Backfilling

When `totalCandles` stops increasing (data sources exhausted):

### Option 1: Disable Cron
Edit `wrangler-data-ingestion.toml`:
```toml
# Comment out the cron trigger
# [triggers]
# crons = ["* * * * *"]
```

Commit and push - GitHub Actions will redeploy with cron disabled.

### Option 2: Delete Worker
```bash
wrangler delete coinswarm-data-backfill
```

---

## Troubleshooting

### GitHub Actions workflow not running

Check that:
- ✅ `CLOUDFLARE_API_TOKEN` secret is set
- ✅ `CRYPTOCOMPARE_API_KEY` secret is set
- ✅ You pushed to the right branch
- ✅ File paths match workflow triggers

### Worker deployed but not fetching data

Check logs:
```bash
wrangler tail coinswarm-data-backfill
```

Common issues:
- Database ID wrong in `wrangler-data-ingestion.toml`
- API key secret not set in GitHub
- D1 database not created

### Rate limiting (429 errors)

This is normal! The worker will:
- Auto-retry with exponential backoff (5s, 10s, 20s)
- Continue with next symbol if persistent
- Eventually succeed

---

## Summary

**One-time setup:**
```bash
# 1. Create D1 database
wrangler d1 create coinswarm-historical-data

# 2. Apply schema
wrangler d1 execute coinswarm-historical-data --file=cloudflare-d1-schema.sql

# 3. Update wrangler-data-ingestion.toml with database_id

# 4. Add GitHub secrets (CLOUDFLARE_API_TOKEN, CRYPTOCOMPARE_API_KEY)
```

**Deploy:**
```bash
git add wrangler-data-ingestion.toml
git commit -m "Deploy backfill worker"
git push
```

**Monitor:**
```bash
curl https://YOUR_WORKER_URL/progress
```

**That's it! Fill 'er up!** 🚀
