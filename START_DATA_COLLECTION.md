# START DATA COLLECTION - Quick Guide

**Status:** GitHub Actions deployment in progress (started ~10 minutes ago)

---

## Current Situation

✅ **Code ready:** `/init` endpoint added to historical-data-collection-cron.ts
✅ **Committed:** All changes pushed to branch `claude/audit-historical-data-system-011CUx7r66ZDX5rTp6bRDQYE`
⏳ **Deploying:** GitHub Actions workflow running (typical time: 5-15 minutes)
❌ **Not initialized:** Database still empty (0 tokens)

**Current time:** 19:18 UTC
**Next cron run:** 20:00 UTC (42 minutes from now)

---

## Step-by-Step: Start Data Collection

### Option 1: Wait for Deployment + Initialize (Recommended)

**1. Wait for deployment to complete** (check every few minutes)
```bash
# Test if new endpoint is deployed
curl -X POST https://coinswarm-historical-collection-cron.bamn86.workers.dev/init
```

**Expected response when deployed:**
```json
{
  "success": true,
  "message": "Database initialized successfully",
  "tokensInserted": 15,
  "totalInDatabase": 15,
  "expectedTotal": 15
}
```

**Current response (old version):**
```json
{
  "status": "ok",
  "name": "Multi-Timeframe Historical Data Collection Worker",
  ...
}
```

**2. Once deployed, initialize the database:**
```bash
curl -X POST https://coinswarm-historical-collection-cron.bamn86.workers.dev/init
```

**3. Verify initialization:**
```bash
curl https://coinswarm-historical-collection-cron.bamn86.workers.dev/status | jq '.tokens | length'
# Should return: 15
```

**4. Wait for next cron trigger:**
- Cron runs every hour at :00
- Next run: **20:00 UTC** (top of next hour)
- Data collection starts automatically

**5. Verify collection started:**
```bash
# Check after 20:00
curl https://coinswarm-historical-collection-cron.bamn86.workers.dev/status | jq '.tokens[0].minutes_collected'
# Should be > 0 if collection started
```

---

### Option 2: Manual Deployment (If GitHub Actions is slow)

**Run the deployment script:**
```bash
bash /home/user/Coinswarm/deploy-and-init.sh
```

This will:
1. Install wrangler CLI if needed
2. Deploy the updated worker
3. Call /init endpoint
4. Verify initialization
5. Show next steps

---

## What Happens After Initialization

Once `/init` is called successfully:

### Immediate (< 1 minute)
- ✅ 15 tokens inserted into `collection_progress` table
- ✅ All statuses set to 'pending'
- ✅ System ready for data collection

### First Cron Run (next :00)
**Three parallel collectors start:**

1. **Minute Collector** (CryptoCompare)
   - Fetches 2,000 minutes per run
   - Rate: 16.875 calls/min
   - Runs continuously

2. **Hourly Collector** (Binance.US)
   - Fetches 1,000 hours per run
   - Rate: 675 calls/min
   - Until 5 years complete

3. **Daily Collector** (CoinGecko)
   - Fetches 365 days per run
   - Rate: 16.875 calls/min
   - Until 5 years complete

### After Each Collection Run
- Technical indicators calculated automatically
- SMA, EMA, Bollinger Bands, MACD, RSI, Fear/Greed Index
- Data stored in `price_data` and `technical_indicators` tables

---

## Timeline for Full Dataset

| Timeframe | Data Points per Token | Total Data Points | Estimated Time |
|-----------|----------------------|-------------------|----------------|
| **Daily** | 1,825 | 27,375 | 24-48 hours |
| **Hourly** | 43,800 | 657,000 | 24-48 hours |
| **Minute** | 2,628,000 | 39,420,000 | ~97 days |

**Total historical dataset:** ~40 million data points across 15 tokens

---

## Monitoring Progress

### Check Overall Status
```bash
curl https://coinswarm-historical-collection-cron.bamn86.workers.dev/status | jq
```

### Check Specific Token Progress
```bash
curl https://coinswarm-historical-collection-cron.bamn86.workers.dev/status | \
  jq '.tokens[] | select(.symbol == "BTCUSDT")'
```

### View Collection Alerts
```bash
curl https://coinswarm-collection-alerts.bamn86.workers.dev/alerts | jq
```

### Access Dashboard (once fixed)
```
https://coinswarm-data-monitor.bamn86.workers.dev/
```

---

## Troubleshooting

### "/init returns old response"
**Issue:** Deployment hasn't completed yet
**Solution:** Wait a few more minutes, deployment can take 10-15 minutes

### "success: false" from /init
**Issue:** Database error or connectivity issue
**Solution:** Check error message in response, may need to check D1 database status

### "Tokens in DB: 0/15 after init"
**Issue:** Initialization didn't commit to database
**Solution:** Try calling /init again, check worker logs in Cloudflare dashboard

### "No data collecting after hours"
**Issue:** Cron may not be triggering or API keys missing
**Solution:**
- Verify cron schedule in Cloudflare Workers dashboard
- Check COINGECKO and CRYPTOCOMPARE_API_KEY secrets are set
- Check worker logs for errors

---

## Current Status Check

Run this to see current state:
```bash
echo "=== COLLECTION STATUS ===" && \
curl -s https://coinswarm-historical-collection-cron.bamn86.workers.dev/status | \
  python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f\"Tokens in DB: {len(d['tokens'])}/15\")
print(f\"Daily complete: {d['dailyCompleted']}\")
print(f\"Hourly complete: {d['hourlyCompleted']}\")
print(f\"Minute complete: {d['minuteCompleted']}\")
if len(d['tokens']) > 0:
    t = d['tokens'][0]
    print(f\"\\nSample (BTCUSDT):\")
    print(f\"  Minutes: {t.get('minutes_collected', 0)}/{t.get('total_minutes', 0)}\")
    print(f\"  Hours: {t.get('hours_collected', 0)}/{t.get('total_hours', 0)}\")
    print(f\"  Days: {t.get('days_collected', 0)}/{t.get('total_days', 0)}\")
else:
    print(\"\\n❌ Database not initialized yet\")
"
```

---

## Next Manual Check

**Check deployment status at:** 19:30 UTC (12 minutes from now)

**Expected:** `/init` endpoint should be live by then

**Command to run:**
```bash
curl -X POST https://coinswarm-historical-collection-cron.bamn86.workers.dev/init
```

---

## Summary

**To start data collection, you need to:**
1. ⏳ Wait for GitHub Actions deployment (~5 more minutes)
2. 🔧 Call `/init` endpoint (1 command)
3. ⏰ Wait for next cron run at 20:00 UTC
4. ✅ Verify collection started

**Total time to first data:** ~45 minutes from now (19:18 → 20:00 + collection time)

**Files to monitor:**
- Deployment status: Check GitHub Actions tab in repository
- Collection progress: `/status` endpoint
- Worker logs: Cloudflare Workers dashboard
