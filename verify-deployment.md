# Deployment Verification Checklist

## Step 1: Check if GitHub Actions Ran

```bash
gh run list --branch claude/full-code-review-011CUvqUcjpgrh9x49XzAs2v --limit 5
```

**Expected:** Recent workflow runs for commits:
- `731c694` - Add collection alerts agent
- `e7a464c` - Add monitoring dashboard and technical indicators
- `7b2cb71` - Add real-time price collection

## Step 2: Check Latest Workflow Run Status

```bash
gh run view
```

**Expected:** Status should be "completed" and "success"

If failed, check logs:
```bash
gh run view --log-failed
```

## Step 3: Verify Workers Are Live on Cloudflare

Go to: https://dash.cloudflare.com
- Navigate to: Workers & Pages
- Check for these workers:

### Expected Workers (NEW - created in this session):
1. ✅ `coinswarm-data-monitor` - Monitoring dashboard
2. ✅ `coinswarm-realtime-price-cron` - Real-time prices (every minute)
3. ✅ `coinswarm-technical-indicators` - Technical indicators (hourly)
4. ✅ `coinswarm-collection-alerts` - Collection alerts (every 15 min)

### Expected Workers (UPDATED):
5. ✅ `coinswarm-historical-collection-cron` - Multi-timeframe collection (hourly)

## Step 4: Test Worker Endpoints

Run the test script:
```bash
./test-workers.sh
```

Or manually test each worker:

```bash
# Historical collection cron
curl https://coinswarm-historical-collection-cron.theaiguyfrom.workers.dev/

# Expected response:
{
  "status": "ok",
  "name": "Multi-Timeframe Historical Data Collection Worker",
  "strategy": {
    "minute": "CryptoCompare - runs forever (16.875 calls/min)",
    "daily": "CoinGecko - until 5 years complete (16.875 calls/min)",
    "hourly": "Binance.US - until 5 years complete (675 calls/min)"
  },
  "parallel": "All three collectors run simultaneously",
  "tokens": 15,
  "timeframes": ["1m", "1h", "1d"]
}

# Real-time price collector
curl https://coinswarm-realtime-price-cron.theaiguyfrom.workers.dev/

# Expected response:
{
  "status": "ok",
  "name": "Real-Time Price Collection Worker",
  "schedule": "Every minute",
  "algorithm": "Leaky bucket with intelligent round-robin",
  "rateLimits": "25% of each API max capacity",
  "tokens": 15,
  "endpoints": ["/status", "/latest"]
}

# Technical indicators
curl https://coinswarm-technical-indicators.theaiguyfrom.workers.dev/

# Expected response:
{
  "status": "ok",
  "name": "Technical Indicators Agent",
  "endpoints": [...],
  "indicators": [...]
}

# Collection alerts
curl https://coinswarm-collection-alerts.theaiguyfrom.workers.dev/

# Expected response:
{
  "status": "ok",
  "name": "Collection Alerts Agent",
  "endpoints": [...],
  "alertTypes": [...]
}

# Monitoring dashboard
curl https://coinswarm-data-monitor.theaiguyfrom.workers.dev/
# Expected: HTML page with "Coinswarm Data Collection Monitor"

curl https://coinswarm-data-monitor.theaiguyfrom.workers.dev/api/stats
# Expected: JSON with collection stats
```

## Step 5: If Workers Are Missing

### Option A: Trigger GitHub Actions Manually

```bash
gh workflow run "Deploy Evolution System (All Workers)" --ref claude/full-code-review-011CUvqUcjpgrh9x49XzAs2v
```

### Option B: Deploy Manually with Wrangler

```bash
cd cloudflare-agents

# Deploy each new worker
wrangler deploy --config wrangler-data-monitor.toml
wrangler deploy --config wrangler-realtime-price-cron.toml
wrangler deploy --config wrangler-technical-indicators.toml
wrangler deploy --config wrangler-collection-alerts.toml

# Redeploy updated worker
wrangler deploy --config wrangler-historical-collection-cron.toml
```

## Step 6: Check Cron Schedules

After deployment, verify cron triggers are set:

```bash
wrangler deployments list --name coinswarm-historical-collection-cron
wrangler deployments list --name coinswarm-realtime-price-cron
wrangler deployments list --name coinswarm-technical-indicators
wrangler deployments list --name coinswarm-collection-alerts
```

## Common Issues

### Issue: "Worker not found"
**Cause:** Deployment didn't run or failed
**Fix:** Check GitHub Actions logs or deploy manually

### Issue: "Secrets not set"
**Cause:** `COINGECKO` or `CRYPTOCOMPARE_API_KEY` missing
**Fix:** Set in Cloudflare dashboard or via wrangler:
```bash
wrangler secret put COINGECKO --name coinswarm-realtime-price-cron
wrangler secret put CRYPTOCOMPARE_API_KEY --name coinswarm-realtime-price-cron
```

### Issue: "Database binding error"
**Cause:** D1 database not accessible
**Fix:** Verify D1 database exists and ID matches in wrangler.toml files
