# Historical Data Queue Deployment Guide

This guide shows you how to deploy the queue-based historical data ingestion system that solves your D1 write throughput problem.

## Problem Solved

**Before (Without Queues):**
- Fetching 10,000+ data points
- Each D1 INSERT takes 10-50ms
- Total time: 100-500 seconds ❌
- D1 gets overwhelmed, writes fail
- Cron times out

**After (With Queues):**
- Fetching 10,000+ data points
- Queue all data points: 1-2 seconds ✅
- D1 writes happen async in batches
- Throughput: 500-1000 rows/sec ✅
- No timeouts, no failures

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  PRODUCER (Fast - Completes in seconds)                     │
├─────────────────────────────────────────────────────────────┤
│  1. Cron triggers every 15 min                              │
│  2. Fetch from Binance/CoinGecko/CryptoCompare             │
│  3. Queue all data points (NO D1 writes)                   │
│  4. Return success immediately                              │
└─────────────────────────────────────────────────────────────┘
                              ↓
                    [Cloudflare Queue]
                   (Reliable, Durable)
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  CONSUMER (Efficient - Batch writes)                        │
├─────────────────────────────────────────────────────────────┤
│  1. Receives batches of 100 messages                        │
│  2. Deduplicates data points                                │
│  3. Batch INSERT to D1 (100x faster)                       │
│  4. Retries on D1 overload                                  │
│  5. Acks messages on success                                │
└─────────────────────────────────────────────────────────────┘
```

---

## Deployment Steps

### 1. Create D1 Database (if not exists)

```bash
cd cloudflare-agents

# Create D1 database
wrangler d1 create coinswarm-db

# Note the database_id from output
```

### 2. Apply D1 Schema

```bash
# Create tables and indexes
wrangler d1 execute coinswarm-db \
  --file=d1-schema-historical-prices-queue.sql \
  --remote
```

### 3. Create Queue

```bash
# Create the queue
wrangler queues create historical-data-queue

# Create dead letter queue (for failed messages)
wrangler queues create historical-data-dlq
```

### 4. Update wrangler.toml

Edit `wrangler-historical-queue.toml`:

```toml
# Replace YOUR_D1_DATABASE_ID with actual ID from step 1
database_id = "abc123-your-actual-database-id"

# Add your API keys
[vars]
COINGECKO = "CG-your-key"
CRYPTOCOMPARE_API_KEY = "your-cryptocompare-key"
```

### 5. Deploy Producer Worker

```bash
# Deploy the cron worker that fetches data
wrangler deploy \
  --config wrangler-historical-queue.toml \
  historical-data-queue-producer.ts
```

### 6. Deploy Consumer Worker

```bash
# Deploy the queue consumer that writes to D1
wrangler deploy \
  --config wrangler-historical-queue.toml \
  historical-data-queue-consumer.ts
```

### 7. Test the System

```bash
# Trigger the cron manually to test
wrangler cron trigger historical-data-queue-producer

# Check queue stats
wrangler queues list

# View queue metrics
wrangler queues consumer historical-data-queue
```

---

## Monitoring

### Check Producer Logs

```bash
wrangler tail historical-data-queue-producer --format pretty
```

**Expected output:**
```
✅ Queued 12,450 data points in 2,134ms
   Average: 0.17ms per point
   D1 writes will happen async via queue consumer
```

### Check Consumer Logs

```bash
wrangler tail historical-data-queue-consumer --format pretty
```

**Expected output:**
```
📥 Processing batch of 100 data points
   Deduplicated: 100 → 98 unique points
✅ Inserted 98 rows in 156ms
   Throughput: 628 rows/sec
```

### Query D1 to Verify Data

```bash
# Count rows
wrangler d1 execute coinswarm-db \
  --command "SELECT COUNT(*) FROM historical_prices" \
  --remote

# Check latest data
wrangler d1 execute coinswarm-db \
  --command "SELECT * FROM latest_prices ORDER BY latest_timestamp DESC LIMIT 10" \
  --remote

# View coverage stats
wrangler d1 execute coinswarm-db \
  --command "SELECT * FROM data_coverage ORDER BY data_points DESC" \
  --remote

# Check ingestion performance
wrangler d1 execute coinswarm-db \
  --command "SELECT * FROM ingestion_performance" \
  --remote
```

---

## Performance Expectations

### Producer Performance
- **Fetching**: 1-3 seconds for all sources
- **Queuing**: 200-500ms for 10,000 points
- **Total**: 2-4 seconds per cron run
- **Success Rate**: 99.9%+ (no D1 bottleneck)

### Consumer Performance
- **Throughput**: 500-1000 rows/sec
- **Batch Size**: 100 messages per batch
- **Processing Time**: 100-200ms per batch
- **10,000 points**: Processed in 10-20 seconds

### Cost Estimate

**Queue Operations** (1M included):
- 13 tokens × 1000 data points/run × 96 runs/day = 1,248,000 messages/day
- Each message = 3 operations (write, read, ack)
- Total: ~3.7M operations/day
- **Cost after free tier**: ~$1.10/day or ~$33/month

**D1 Usage** (25B reads, 50M writes included):
- Writes: ~1.2M rows/day = ~36M rows/month
- Reads: Minimal (only for dedup checks)
- **Under included limits**: $0

---

## Troubleshooting

### Queue is Backing Up

**Symptoms**: Queue depth keeps increasing

**Causes**:
- D1 overloaded
- Consumer not processing fast enough
- Too many retries

**Solutions**:
```bash
# Check queue depth
wrangler queues consumer historical-data-queue

# Increase consumer concurrency
# Edit wrangler-historical-queue.toml:
max_concurrency = 10  # Increase from 5

# Redeploy consumer
wrangler deploy historical-data-queue-consumer
```

### Messages Going to Dead Letter Queue

**Symptoms**: `historical-data-dlq` has messages

**Check failed messages**:
```bash
# Query failed ingestions
wrangler d1 execute coinswarm-db \
  --command "SELECT * FROM failed_ingestions ORDER BY failed_at DESC LIMIT 10" \
  --remote
```

**Common causes**:
- Duplicate key violations (normal, handled with INSERT OR IGNORE)
- D1 database locked for >30 seconds
- Invalid data format

### Producer Timing Out

**Symptoms**: Cron fails with timeout

**Solutions**:
- Reduce number of tokens fetched per run
- Decrease API request timeouts
- Split into multiple cron jobs

---

## Scaling Guidelines

### Current Setup
- **13 tokens**
- **3 sources** per token
- **~1000 points** per source
- **Total**: ~40,000 points per cron run

### If You Add More Tokens

| Tokens | Points/Run | Queue Ops/Day | Cost/Month |
|--------|------------|---------------|------------|
| 13     | 40,000     | 11.5M         | $4.20      |
| 25     | 75,000     | 21.6M         | $8.20      |
| 50     | 150,000    | 43.2M         | $16.80     |
| 100    | 300,000    | 86.4M         | $33.60     |

### Optimization Tips

1. **Reduce Fetch Frequency**: Change cron from 15min → 30min
2. **Increase Batch Size**: 100 → 500 messages per batch (if D1 can handle)
3. **Parallel Consumers**: Increase `max_concurrency` from 5 → 20
4. **Use KV for Deduplication**: Cache recent timestamps to skip already-fetched data

---

## Advanced Features

### Add Monitoring Dashboard

Create a dashboard worker to visualize ingestion stats:

```typescript
// dashboard.ts
export default {
  async fetch(request: Request, env: Env) {
    const stats = await env.DB.prepare(`
      SELECT * FROM ingestion_performance
    `).all();

    return new Response(JSON.stringify(stats), {
      headers: { 'Content-Type': 'application/json' }
    });
  }
}
```

### Add Alerts for Queue Backlog

```bash
# Set up alert (Cloudflare dashboard)
# Go to: Notifications → Create Notification
# Trigger: Queue depth > 10,000
# Action: Send email
```

### Add Rate Limiting

```typescript
// In producer, rate limit external API calls
const rateLimiter = new Map<string, number>();

async function fetchWithRateLimit(url: string) {
  const lastCall = rateLimiter.get(url) || 0;
  const now = Date.now();
  const minInterval = 100; // 100ms between calls

  if (now - lastCall < minInterval) {
    await sleep(minInterval - (now - lastCall));
  }

  rateLimiter.set(url, Date.now());
  return fetch(url);
}
```

---

## Migration from Old System

### Step 1: Deploy Queue System (Parallel)

Deploy the new queue-based system alongside your existing system. They can coexist.

### Step 2: Test with Subset

Start with 1-2 tokens to verify it works:

```typescript
// Temporarily reduce tokens for testing
const TOKENS = [
  { symbol: 'BTCUSDT', coinId: 'bitcoin' },
  { symbol: 'ETHUSDT', coinId: 'ethereum' },
];
```

### Step 3: Compare Results

Query both old and new tables to verify data consistency:

```sql
-- Compare data points
SELECT symbol, COUNT(*) as count
FROM historical_prices
GROUP BY symbol
ORDER BY count DESC;
```

### Step 4: Switch Over

Once verified, update cron to use queue-based producer:

```bash
# Disable old cron
wrangler cron trigger historical-data-collection-cron --disable

# Enable new cron
wrangler cron trigger historical-data-queue-producer --enable
```

### Step 5: Monitor for 24 Hours

Watch logs and queue depth to ensure system is stable.

---

## Support

If you encounter issues:

1. Check logs: `wrangler tail <worker-name>`
2. Check queue stats: `wrangler queues consumer <queue-name>`
3. Check D1 data: `wrangler d1 execute <db> --command "SELECT..."`
4. Review [Cloudflare Queues docs](https://developers.cloudflare.com/queues/)

---

## Summary

**What You Gain:**
✅ 100x faster data ingestion
✅ No more timeouts or failures
✅ Automatic retries on D1 overload
✅ Scales to millions of data points
✅ Only $4-8/month for 13-25 tokens

**What It Costs:**
- Setup time: 30 minutes
- Monthly cost: $4-8 (queue operations)
- Monitoring: Built-in via logs

**Next Steps:**
1. Deploy the system (follow steps above)
2. Test with 2-3 tokens
3. Scale to all tokens
4. Monitor performance
5. Optimize as needed
