# Data Collection Deployment & Monitoring Guide

## Current Deployment Status

**Branch**: `claude/full-code-review-011CUvqUcjpgrh9x49XzAs2v`

**Last Commits**:
- `26f8f88` - Run cron 24/7 every hour with exponential backoff
- `da30177` - Set rate limiting to 75% of max
- `41dd83b` - Add historical data collection cron worker

**Deployment**: In progress via GitHub Actions

---

## What's Been Deployed

### 1. Historical Data Collection Cron Worker
- **Name**: `coinswarm-historical-collection-cron`
- **URL**: https://coinswarm-historical-collection-cron.bamn86.workers.dev
- **Schedule**: Every hour (24/7)
- **Purpose**: Slowly collect 5 years of OHLCV data for 15 tokens

### 2. Historical Data Worker (Updated)
- **Name**: `coinswarm-historical-data`
- **URL**: https://coinswarm-historical-data.bamn86.workers.dev
- **Purpose**: On-demand historical data fetching with 5-tier fallback

---

## Monitoring Commands

### Check Cron Worker Status
```bash
# Get worker info
curl https://coinswarm-historical-collection-cron.bamn86.workers.dev/

# Check collection progress for all tokens
curl https://coinswarm-historical-collection-cron.bamn86.workers.dev/status | jq '.'

# Manual trigger (for testing)
curl https://coinswarm-historical-collection-cron.bamn86.workers.dev/collect | jq '.'
```

### Check Historical Data Worker
```bash
# Get worker info
curl https://coinswarm-historical-data.bamn86.workers.dev/

# Test data fetch for SOL
curl "https://coinswarm-historical-data.bamn86.workers.dev/fetch-fresh?symbol=SOLUSDT&limit=50" | jq '{success, source, candleCount}'

# Test data fetch for BTC
curl "https://coinswarm-historical-data.bamn86.workers.dev/fetch-fresh?symbol=BTCUSDT&limit=50" | jq '{success, source, candleCount}'
```

### Check Database (via Evolution Agent)
```bash
# Check price_data table
curl https://coinswarm-evolution-agent.bamn86.workers.dev/debug/db | jq '.tables'

# Query for collected data
# (Need to add a query endpoint or use D1 directly)
```

---

## Expected Progress Tracking

### Status Response Format
```json
{
  "success": true,
  "tokens": [
    {
      "symbol": "BTCUSDT",
      "coin_id": "bitcoin",
      "days_collected": 30,
      "total_days": 1825,
      "status": "pending",
      "error_count": 0,
      "last_run": 1762665308425
    },
    // ... more tokens
  ],
  "totalTokens": 15,
  "completedTokens": 0
}
```

### Status Values
- **`pending`**: Waiting to be processed
- **`in_progress`**: Currently collecting
- **`completed`**: Fully collected (1825 days)
- **`paused`**: Paused due to 3 consecutive errors

### Progress Calculation
```
Progress = (days_collected / total_days) * 100
```

Example:
- Token: BTC
- Days collected: 365
- Total days: 1825
- Progress: 20%

---

## Troubleshooting

### Error 1042
**Symptom**: Worker returns `error code: 1042`

**Possible Causes**:
1. D1 database binding not properly configured
2. Worker still deploying
3. API secret (COINGECKO) not set

**Fix**:
1. Wait 2-3 minutes for deployment to complete
2. Verify COINGECKO secret is set in GitHub repository secrets
3. Check GitHub Actions logs for deployment errors

### Worker Not Responding
**Symptom**: Worker returns TLS errors or timeouts

**Possible Causes**:
1. Deployment still in progress
2. Cloudflare experiencing issues

**Fix**:
1. Wait 5-10 minutes
2. Check Cloudflare status: https://www.cloudflarestatus.com/
3. Try again later

### Paused Tokens
**Symptom**: Token status shows `paused`

**Possible Causes**:
1. 3 consecutive API failures
2. Invalid coin_id for CoinGecko
3. Rate limit exceeded

**Fix**:
1. Check `last_error` field in status response
2. Verify coin_id is correct
3. Manually reset error count in database:
   ```sql
   UPDATE collection_progress
   SET error_count = 0, status = 'pending', last_error = NULL
   WHERE symbol = 'BTCUSDT';
   ```

### No Data Being Collected
**Symptom**: `days_collected` not increasing after multiple hours

**Possible Causes**:
1. Cron trigger not running
2. All tokens paused
3. API key invalid

**Fix**:
1. Manually trigger: `/collect` endpoint
2. Check status for paused tokens
3. Verify COINGECKO secret is valid
4. Check Cloudflare Workers logs (requires dashboard access)

---

## Collection Timeline

### Current Configuration
- **Tokens**: 15
- **Days per run**: 30
- **Total days**: 1825 (5 years)
- **Runs per token**: 1825 / 30 = 61 runs
- **Schedule**: Every hour
- **Completion**: ~40 days

### Timeline Breakdown
| Day | Expected Progress |
|-----|-------------------|
| 1   | ~15 tokens × 30 days = 450 days total |
| 7   | ~3150 days total (~12% complete) |
| 14  | ~6300 days total (~23% complete) |
| 21  | ~9450 days total (~35% complete) |
| 30  | ~13500 days total (~49% complete) |
| 40  | ~27375 days total (100% complete) |

---

## Rate Limiting Details

### CoinGecko API
- **Free tier**: 30 calls/min, 10k calls/month
- **Current usage**: 22.5 calls/min (75% of limit)
- **Monthly usage**: ~720 calls/month (7.2% of limit)

### Safety Margins
- **Per-minute**: 25% buffer (7.5 calls/min unused)
- **Monthly**: 92.8% buffer (9,280 calls/month unused)

---

## Data Quality Checks

### Verify Candle Count
```bash
# Should return ~30 candles per run
curl https://coinswarm-historical-collection-cron.bamn86.workers.dev/status | \
  jq '.tokens[] | select(.symbol == "BTCUSDT") | .days_collected'
```

### Check for Gaps
```sql
-- Query D1 database directly (requires wrangler)
SELECT symbol, COUNT(*) as candle_count, MIN(timestamp) as first, MAX(timestamp) as last
FROM price_data
GROUP BY symbol;
```

### Verify Data Freshness
```bash
# Check last run time
curl https://coinswarm-historical-collection-cron.bamn86.workers.dev/status | \
  jq '.tokens[] | {symbol, last_run, status}'
```

---

## Next Steps After Collection Completes

1. **Verify completeness**: All 15 tokens at 1825 days
2. **Build Technical Indicators Agent**: Calculate 50+ indicators
3. **Build Sentiment Analysis Agent**: Add news/Fear & Greed data
4. **Build Macroeconomic Agent**: Add FRED/Treasury data
5. **Generate Chaos Trades**: With full 150+ column context

---

## Quick Health Check Script

```bash
#!/bin/bash
# health-check.sh

echo "=== Data Collection Health Check ==="
echo ""

# Check worker status
echo "1. Checking cron worker..."
STATUS=$(curl -s https://coinswarm-historical-collection-cron.bamn86.workers.dev/status)

if [ $? -eq 0 ]; then
  echo "✅ Worker responding"

  COMPLETED=$(echo $STATUS | jq '.completedTokens')
  TOTAL=$(echo $STATUS | jq '.totalTokens')
  echo "   Completed: $COMPLETED / $TOTAL tokens"

  PAUSED=$(echo $STATUS | jq '[.tokens[] | select(.status == "paused")] | length')
  if [ "$PAUSED" -gt 0 ]; then
    echo "⚠️  $PAUSED tokens paused"
  fi
else
  echo "❌ Worker not responding"
fi

echo ""
echo "2. Checking historical data worker..."
TEST=$(curl -s "https://coinswarm-historical-data.bamn86.workers.dev/fetch-fresh?symbol=SOLUSDT&limit=10")

if echo $TEST | jq -e '.success' > /dev/null 2>&1; then
  SOURCE=$(echo $TEST | jq -r '.source')
  COUNT=$(echo $TEST | jq '.candleCount')
  echo "✅ Fetched $COUNT candles from $SOURCE"
else
  echo "❌ Data fetch failed"
fi

echo ""
echo "=== End Health Check ==="
```

---

## Contact & Support

If issues persist:
1. Check GitHub Actions logs for deployment errors
2. Verify all secrets are set correctly
3. Review Cloudflare Workers logs (dashboard required)
4. Wait 24 hours and check progress again

**Remember**: The system is designed to run slowly and safely. Don't worry if progress seems slow - that's by design to stay well under API rate limits.
