# How to Stay Within Free Limits on $5/Month Paid Plan

This guide shows you how to maximize Cloudflare's included usage without incurring any overage charges.

---

## Current Usage Analysis

### Queue Operations (1M included)

**Incremental Data Collection** (once historical backfill is done):

| Scenario | Data Points/Day | Queue Ops/Day | Monthly Ops | Over Limit? |
|----------|-----------------|---------------|-------------|-------------|
| **13 tokens, 15min cron** | 18,720 | 56,160 | 1,684,800 | ⚠️ +684K ($0.27) |
| **13 tokens, 30min cron** | 9,360 | 28,080 | 842,400 | ✅ Under limit |
| **13 tokens, 1hr cron** | 4,680 | 14,040 | 421,200 | ✅ Under limit |
| **25 tokens, 1hr cron** | 9,000 | 27,000 | 810,000 | ✅ Under limit |
| **50 tokens, 2hr cron** | 9,000 | 27,000 | 810,000 | ✅ Under limit |

**Calculation:**
- Each data point = 3 queue operations (write, read, ack)
- 15min cron = 96 runs/day
- 30min cron = 48 runs/day
- 1hr cron = 24 runs/day
- 2hr cron = 12 runs/day

### D1 Database (50M writes included)

| Scenario | Writes/Day | Monthly Writes | Over Limit? |
|----------|------------|----------------|-------------|
| **13 tokens, 15min** | 18,720 | 561,600 | ✅ 1.1% of limit |
| **100 tokens, 15min** | 144,000 | 4,320,000 | ✅ 8.6% of limit |
| **500 tokens, 15min** | 720,000 | 21,600,000 | ✅ 43% of limit |

**You're nowhere near D1 limits!** You could track 500+ tokens before hitting D1 write limits.

### Workers Requests (10M included)

| Component | Requests/Day | Monthly Requests | Over Limit? |
|-----------|--------------|------------------|-------------|
| **Cron triggers** (96/day) | 96 | 2,880 | ✅ 0.03% |
| **Queue consumers** (56K/day) | 56,160 | 1,684,800 | ✅ 16.8% |
| **Total** | 56,256 | 1,687,680 | ✅ 16.9% |

**Plenty of headroom!** You're using <17% of included requests.

---

## ✅ Recommended Configuration (Zero Overage)

### Option 1: Stay Under 1M Queue Ops (Recommended)

**Change cron from 15min → 30min:**

```toml
# wrangler-historical-queue.toml
[triggers]
crons = ["*/30 * * * *"]  # Every 30 minutes instead of 15
```

**Result:**
- Queue operations: 842,400/month (✅ Under 1M)
- D1 writes: 561,600/month (✅ Under 50M)
- Workers requests: 843,840/month (✅ Under 10M)
- **Total overage cost: $0.00** 💰

**Trade-off:** Data freshness reduced from 15min to 30min (still excellent for trading)

---

### Option 2: Selective Token Tracking

Track high-priority tokens more frequently:

```typescript
// historical-data-queue-producer.ts
const HIGH_PRIORITY_TOKENS = [
  { symbol: 'BTCUSDT', coinId: 'bitcoin', interval: '15min' },
  { symbol: 'ETHUSDT', coinId: 'ethereum', interval: '15min' },
  { symbol: 'SOLUSDT', coinId: 'solana', interval: '15min' },
];

const MEDIUM_PRIORITY_TOKENS = [
  { symbol: 'BNBUSDT', coinId: 'binancecoin', interval: '1hr' },
  { symbol: 'MATICUSDT', coinId: 'matic-network', interval: '1hr' },
  // ... rest
];

export default {
  async scheduled(event: ScheduledEvent, env: Env) {
    const currentMinute = new Date().getMinutes();

    // High priority: every 15 min
    if (currentMinute % 15 === 0) {
      await fetchTokens(HIGH_PRIORITY_TOKENS, env);
    }

    // Medium priority: every hour
    if (currentMinute === 0) {
      await fetchTokens(MEDIUM_PRIORITY_TOKENS, env);
    }
  }
}
```

**Result:**
- 3 tokens @ 15min = 8,640 ops/day
- 10 tokens @ 1hr = 7,200 ops/day
- **Total: 15,840 ops/day = 475,200/month** ✅ Under limit

---

### Option 3: Smart Deduplication (Advanced)

Only fetch data if it's actually new:

```typescript
// Cache last timestamp in KV (10M reads included!)
async function shouldFetch(symbol: string, env: Env): Promise<boolean> {
  const lastFetch = await env.KV.get(`last_fetch:${symbol}`);
  const now = Date.now();

  if (!lastFetch) return true;

  const elapsed = now - parseInt(lastFetch);
  const minInterval = 15 * 60 * 1000; // 15 minutes

  if (elapsed < minInterval) {
    console.log(`Skipping ${symbol}, last fetch was ${elapsed}ms ago`);
    return false;
  }

  return true;
}

export default {
  async scheduled(event: ScheduledEvent, env: Env) {
    for (const token of TOKENS) {
      // Skip if recently fetched
      if (!await shouldFetch(token.symbol, env)) {
        continue;
      }

      const data = await fetchData(token);

      // Only queue if we got new data
      if (data.length > 0) {
        await env.QUEUE.sendBatch(data);
        await env.KV.put(`last_fetch:${token.symbol}`, Date.now().toString());
      }
    }
  }
}
```

**Benefit:** Reduces queue operations by 30-50% (skips when no new data)

---

## 🎯 Optimization Strategies

### 1. Batch Messages Larger

Instead of 1 data point per message, batch them:

```typescript
// Before: 1 message = 1 data point = 3 ops
await env.QUEUE.send({ body: dataPoint });

// After: 1 message = 10 data points = 3 ops total
const batches = chunkArray(dataPoints, 10);
for (const batch of batches) {
  await env.QUEUE.send({ body: batch }); // Send array
}
```

**Savings:** 10x reduction in queue operations! 🎉

**Updated consumer:**
```typescript
export default {
  async queue(batch: MessageBatch, env: Env) {
    for (const msg of batch.messages) {
      const dataPoints = msg.body; // Now an array of 10 points

      // Process all 10 at once
      await batchInsertToD1(dataPoints, env.DB);
      msg.ack();
    }
  }
}
```

### 2. Use R2 for Historical Backfill

For the initial massive historical data load (millions of points):

```typescript
// During backfill: Store in R2 instead of queueing
const historicalData = await fetchLast5Years(token);

// Upload to R2 (10GB free, unlimited egress)
await env.R2.put(`historical/${token.symbol}.json`,
  JSON.stringify(historicalData)
);

// Then batch import from R2 to D1 later
```

**Benefit:** Zero queue operations for backfill, process at your own pace

### 3. Reduce Data Sources

You're fetching from 3 sources per token. Consider:

```typescript
// Option A: Reduce to 1 primary source
const TOKENS = [
  { symbol: 'BTCUSDT', source: 'binance' }, // Only Binance
];

// Option B: Rotate sources (different source each day)
const todaySource = ['binance', 'coingecko', 'cryptocompare'][new Date().getDay() % 3];
```

**Savings:** 66% reduction in data points = 66% fewer queue ops

---

## 📊 Real-World Optimized Configuration

Here's my recommended setup that stays well under limits:

```typescript
// historical-data-queue-producer.ts (OPTIMIZED)

// Group 1: Critical tokens (every 30min)
const CRITICAL_TOKENS = [
  'BTCUSDT', 'ETHUSDT', 'SOLUSDT'
];

// Group 2: Important tokens (every 1hr)
const IMPORTANT_TOKENS = [
  'BNBUSDT', 'MATICUSDT', 'ARBUSDT', 'OPUSDT'
];

// Group 3: Watchlist (every 4hr)
const WATCHLIST_TOKENS = [
  'CAKEUSDT', 'RAYUSDT', 'ORCAUSDT', 'JUPUSDT', 'GMXUSDT', 'VELOUSDT'
];

export default {
  async scheduled(event: ScheduledEvent, env: Env) {
    const minute = new Date().getMinutes();
    const hour = new Date().getHours();

    let tokensToFetch: string[] = [];

    // Every 30 min: Critical tokens
    if (minute % 30 === 0) {
      tokensToFetch.push(...CRITICAL_TOKENS);
    }

    // Every hour: Important tokens
    if (minute === 0) {
      tokensToFetch.push(...IMPORTANT_TOKENS);
    }

    // Every 4 hours: Watchlist
    if (minute === 0 && hour % 4 === 0) {
      tokensToFetch.push(...WATCHLIST_TOKENS);
    }

    // Fetch from Binance only (fastest, most reliable)
    const dataPoints = await Promise.all(
      tokensToFetch.map(symbol => fetchFromBinance(symbol, env))
    );

    // Batch 10 points per message (10x reduction!)
    const batched = chunkArrays(dataPoints.flat(), 10);

    await env.QUEUE.sendBatch(
      batched.map(batch => ({ body: batch }))
    );
  }
}
```

**Monthly Usage:**
- Critical (3 tokens × 48 runs/day): 4,320 data points/day
- Important (4 tokens × 24 runs/day): 2,880 data points/day
- Watchlist (6 tokens × 6 runs/day): 1,080 data points/day
- **Total**: 8,280 data points/day = 248,400/month

**Queue Operations** (with 10x batching):
- 248,400 / 10 = 24,840 messages
- 24,840 × 3 ops = **74,520 operations/month** ✅ Only 7.5% of limit!

**Cost**: $0.00 overage 💰

---

## 🚨 Monitoring & Alerts

Set up alerts BEFORE hitting limits:

### 1. Cloudflare Dashboard Alerts

```
Navigate to: Dashboard → Notifications → Create Notification

Alert 1: Queue Operations
- Metric: Queue operations
- Threshold: > 750,000/month (75% of limit)
- Action: Email notification

Alert 2: D1 Writes
- Metric: D1 rows written
- Threshold: > 37,500,000/month (75% of limit)
- Action: Email notification

Alert 3: Workers Requests
- Metric: Worker requests
- Threshold: > 7,500,000/month (75% of limit)
- Action: Email notification
```

### 2. Daily Usage Check Script

```bash
#!/bin/bash
# check-usage.sh - Run daily via cron

# Check queue depth
wrangler queues consumer historical-data-queue

# Check D1 usage
wrangler d1 execute coinswarm-db \
  --command "SELECT COUNT(*) as total_rows FROM historical_prices WHERE created_at > $(date -d '30 days ago' +%s)000" \
  --remote

echo "Check your Cloudflare dashboard for detailed usage metrics"
```

### 3. In-App Monitoring

Add usage tracking to your consumer:

```typescript
// Track daily operations
export default {
  async queue(batch: MessageBatch, env: Env) {
    const today = new Date().toISOString().split('T')[0];
    const key = `usage:${today}`;

    // Increment counter in KV
    const current = parseInt(await env.KV.get(key) || '0');
    await env.KV.put(key, (current + batch.messages.length * 3).toString(), {
      expirationTtl: 86400 * 31 // Keep for 31 days
    });

    // Alert if approaching limit
    if (current > 25000) { // ~750K/month pace
      console.warn(`⚠️ High queue usage: ${current} ops today`);
    }

    // Process messages...
  }
}
```

---

## 💡 Pro Tips

### 1. Use KV for Caching
KV reads are 10M/month included - use them!

```typescript
// Cache exchange data for 15 min
const cached = await env.KV.get(`price:${symbol}`);
if (cached) {
  return JSON.parse(cached);
}

const fresh = await fetchFromExchange(symbol);
await env.KV.put(`price:${symbol}`, JSON.stringify(fresh), {
  expirationTtl: 900 // 15 minutes
});
```

### 2. Consolidate Cron Jobs

Instead of multiple crons:
```toml
# ❌ Multiple workers, multiple crons
crons = ["*/15 * * * *"]  # Prices
crons = ["0 * * * *"]     # Indicators
crons = ["0 0 * * *"]     # Daily stats
```

Use one cron, route internally:
```toml
# ✅ One worker, smart routing
crons = ["*/15 * * * *"]
```

```typescript
async scheduled(event: ScheduledEvent, env: Env) {
  const minute = new Date().getMinutes();
  const hour = new Date().getHours();

  // Every 15 min: Prices
  await collectPrices();

  // Every hour
  if (minute === 0) {
    await calculateIndicators();
  }

  // Daily
  if (minute === 0 && hour === 0) {
    await generateDailyStats();
  }
}
```

### 3. Offload to R2 + D1 Combination

```typescript
// Hot data (recent): D1 for fast queries
// Cold data (historical): R2 for cheap storage

// Store last 7 days in D1
await env.DB.prepare(`
  DELETE FROM historical_prices
  WHERE timestamp < ?
`).bind(Date.now() - 7 * 24 * 60 * 60 * 1000).run();

// Archive to R2
const archived = await env.DB.prepare(`
  SELECT * FROM historical_prices
  WHERE timestamp < ?
`).bind(Date.now() - 7 * 24 * 60 * 60 * 1000).all();

await env.R2.put('archive/2025-01.json', JSON.stringify(archived));
```

---

## 📈 Scaling Roadmap

As you grow, here's when you'll need to upgrade:

| Milestone | Monthly Cost | Notes |
|-----------|--------------|-------|
| **0-25 tokens, 30min updates** | $5.00 (base) | All within included limits |
| **26-50 tokens, 30min updates** | $5.50 | ~$0.50 queue overage |
| **51-100 tokens, 30min updates** | $6.50 | ~$1.50 queue overage |
| **100+ tokens, 15min updates** | $8-15 | Consider Workers for Platforms |

**Recommendation**: Stay at 13-25 tokens with 30min updates = $5.00/month flat

---

## Summary: Zero-Overage Configuration

```toml
# wrangler-historical-queue.toml
[triggers]
crons = ["*/30 * * * *"]  # 30 min intervals

[[queues.consumers]]
max_batch_size = 100       # Process 100 at once
max_batch_timeout = 5      # 5 sec timeout
max_concurrency = 3        # 3 parallel consumers
```

```typescript
// 13 tokens, 1 source (Binance), 30min intervals
// Batch 10 data points per message

Monthly Usage:
✅ Queue: 75K ops (7.5% of 1M limit)
✅ D1 Writes: 562K rows (1.1% of 50M limit)
✅ Workers: 844K requests (8.4% of 10M limit)
✅ Cost: $5.00 (no overage)
```

Ready to optimize your configuration?
