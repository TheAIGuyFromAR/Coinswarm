# How to View Cloudflare Workers Logs

## Method 1: Cloudflare Dashboard (Web UI)

### Step 1: Navigate to Workers
```
1. Go to: https://dash.cloudflare.com
2. Select your account
3. Click: Workers & Pages (left sidebar)
4. You should see a list of deployed workers
```

### Step 2: View Worker Logs
```
For Queue Consumer:
1. Click: historical-data-queue-consumer
2. Click: "Logs" tab (top navigation)
3. You should see real-time logs here

For Queue Producer:
1. Click: historical-data-queue-producer
2. Click: "Logs" tab
3. Logs appear here when cron runs (every 30 min)

For Python Worker:
1. Click: coinswarm-historical-import
2. Click: "Logs" tab
3. Logs appear when you trigger it
```

### Important Notes:
- **Logs only appear when workers run**
- Queue consumer: Logs appear when processing messages
- Queue producer: Logs appear every 30 minutes (cron)
- Python worker: Logs appear when you POST /trigger
- Logs are retained for **24 hours** in free tier
- Logs are retained for **30 days** in paid tier ($5/month plan)

---

## Method 2: Logpush (Advanced - Streams to External Service)

If you want logs streamed to an external service, you need Logpush.

**Current config has:**
```toml
[observability]
enabled = true
```

But this alone doesn't do anything. You need to configure a destination:

```toml
[observability]
enabled = true
head_sampling_rate = 1  # Sample 100% of requests

# Example: Send to an HTTP endpoint
[[observability.logs]]
enabled = true
# Add destination config here (requires additional setup)
```

**However**, for basic log viewing, you don't need this. The dashboard "Logs" tab should work automatically.

---

## Method 3: Wrangler Tail (Real-Time CLI)

From your local machine:

```bash
# Install wrangler globally
npm install -g wrangler

# Login to Cloudflare
wrangler login

# Tail consumer logs (real-time)
wrangler tail historical-data-queue-consumer --format pretty

# Tail producer logs (real-time)
wrangler tail historical-data-queue-producer --format pretty

# Tail Python worker logs (real-time)
wrangler tail coinswarm-historical-import --format pretty
```

**This shows logs in real-time as workers execute.**

---

## Troubleshooting: No Logs Showing?

### Issue 1: Workers Haven't Run Yet

**Queue Consumer:**
- Only runs when there are messages in the queue
- Check queue depth: `wrangler queues consumer historical-data-queue`
- If 0 messages, consumer has nothing to process (no logs)

**Queue Producer:**
- Only runs every 30 minutes (cron)
- Next run time shown in dashboard
- Manually trigger to test: Deploy trigger endpoint

**Python Worker:**
- Only runs on manual POST request
- Trigger it: `curl -X POST https://coinswarm-historical-import.<subdomain>.workers.dev/trigger`

---

### Issue 2: Workers Not Deployed

Check if workers exist in dashboard:
```
https://dash.cloudflare.com → Workers & Pages

You should see:
✅ historical-data-queue-consumer
✅ historical-data-queue-producer
✅ coinswarm-historical-import

If missing, deployment failed. Check GitHub Actions.
```

---

### Issue 3: Wrong Account/Zone

Make sure you're viewing the correct Cloudflare account:
- Top-right dropdown in dashboard
- Select the account that has your workers

---

## Quick Test: Trigger Python Worker to Generate Logs

```bash
# Replace <subdomain> with your Workers subdomain
curl -X POST https://coinswarm-historical-import.<your-account>.workers.dev/trigger

# This should:
# 1. Trigger the Python worker
# 2. Generate logs
# 3. Queue messages
# 4. Trigger consumer (generates more logs)
```

Then check:
1. Dashboard → Workers & Pages → coinswarm-historical-import → Logs tab
2. Should see log entries appear immediately
3. Then check consumer logs (will process the queued messages)

---

## What Logs Look Like in Dashboard

**Consumer logs (when processing):**
```
2025-11-13 00:45:12  INFO  📥 Processing batch of 100 data points
2025-11-13 00:45:12  INFO     Deduplicated: 1000 → 995 unique points
2025-11-13 00:45:13  INFO  ✅ Inserted 995 rows in 248ms
2025-11-13 00:45:13  INFO     Throughput: 4008 rows/sec
```

**Producer logs (when cron runs):**
```
2025-11-13 00:30:00  INFO  Starting historical data collection
2025-11-13 00:30:01  INFO  Fetching from CryptoCompare...
2025-11-13 00:30:02  INFO  Fetching from Binance...
2025-11-13 00:30:03  INFO  Queued 195 data points in 20 batches
```

**Python worker logs (when triggered):**
```
2025-11-13 00:50:00  INFO  Fetched 2000 candles for BTC-USDC
2025-11-13 00:50:01  INFO  Queued 2000 candles in 200 batches
```

---

## If Still No Logs

The `[observability] enabled = true` setting we added is for advanced features like Logpush.

**Basic logs should work automatically** without any config.

If you're not seeing logs in the dashboard:

1. **Verify workers are deployed:**
   - Check: https://dash.cloudflare.com → Workers & Pages
   - Do the workers exist?

2. **Verify workers are running:**
   - Queue producer: Wait for next 30-min cron
   - Or manually trigger Python worker

3. **Check the "Logs" tab:**
   - Click worker name
   - Click "Logs" tab (not "Settings" or "Triggers")
   - Logs appear here in real-time

4. **Use wrangler tail instead:**
   - More reliable than dashboard
   - Shows logs immediately
   - Works from local terminal

---

## Summary

**Where to find logs:**
1. ✅ **Dashboard:** Workers & Pages → [Worker] → Logs tab
2. ✅ **Wrangler tail:** `wrangler tail <worker-name> --format pretty`
3. ✅ **GitHub Actions:** Shows deployment logs only

**Why no logs?**
- Workers haven't run yet (no triggers)
- Wrong account selected in dashboard
- Workers not deployed (check GitHub Actions)

**Quick test:**
```bash
# Trigger Python worker (generates logs immediately)
curl -X POST https://coinswarm-historical-import.<subdomain>.workers.dev/trigger

# Then check dashboard logs tab
```

Let me know what you see!
