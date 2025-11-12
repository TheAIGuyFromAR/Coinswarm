# What Happens When Queue Fills Faster Than D1 Can Write

## TL;DR

**Good news:** Cloudflare Queues are designed for this! They'll buffer messages and process them as fast as D1 can handle, with built-in backpressure management.

**What actually happens:**
1. Messages accumulate in the queue (this is normal and expected)
2. Consumers process batches as fast as D1 allows
3. Queue depth grows temporarily during spikes
4. Consumers catch up during quieter periods
5. System self-regulates and stays stable

---

## How Cloudflare Queues Handle Backpressure

### 1. Queue Depth Accumulation ✅

**When producer is faster than consumer:**

```
Producer: 100 messages/min → Queue
Consumer: 60 messages/min ← Queue

Hour 1:
  In: 6,000 messages
  Out: 3,600 messages
  Queue depth: 2,400 messages (backlog building)

Hour 2:
  In: 6,000 messages
  Out: 3,600 messages
  Queue depth: 4,800 messages (still building)

Hour 3:
  In: 6,000 messages
  Out: 3,600 messages
  Queue depth: 7,200 messages (continues...)
```

**This is normal and expected!** Queues are designed to buffer during high load.

---

### 2. Consumer Parallelization

Your consumer configuration controls throughput:

**File:** `cloudflare-agents/wrangler-historical-queue.toml`

```toml
[[queues.consumers]]
queue = "historical-data-queue"
max_batch_size = 100        # Process 100 messages at once
max_batch_timeout = 5       # Wait max 5 sec to fill batch
max_concurrency = 5         # Run 5 consumers in parallel
max_retries = 3             # Retry failed messages 3 times
dead_letter_queue = "historical-data-dlq"  # Send failures here
```

**What this means:**

- **max_concurrency = 5**: Up to 5 consumer instances run simultaneously
- **max_batch_size = 100**: Each instance processes 100 messages at once
- **Theoretical throughput**: 5 instances × 100 messages = 500 messages per batch
- **With 5 sec timeout**: Up to ~6,000 messages/minute (if D1 keeps up)

---

### 3. D1 Batch Write Limits

**D1's actual write capacity:**

```typescript
// Your consumer does this:
await env.DB.batch(statements);  // Up to 100 statements per batch
```

**D1 Limits:**
- ✅ **Max 100 statements per batch** (db.batch())
- ✅ **Max ~1000 parameters per statement**
- ✅ **Max 50M writes/month included** (on $5 plan)
- ⚠️ **Rate limiting**: ~100-500 writes/sec per database

**Real-world throughput:**
- Single INSERT: ~10-50 per second
- Batched INSERTs: ~100-500 per second
- With 5 concurrent consumers: ~500-2500 writes/second

**Example batch operation:**

```typescript
// Process 100 messages in parallel
const statements = batch.messages.map(msg =>
  env.DB.prepare(`INSERT OR IGNORE INTO price_data (...) VALUES (?, ?, ...)`)
    .bind(...msg.body)
);

// Execute all 100 at once (100x faster than sequential)
await env.DB.batch(statements);
```

---

### 4. Queue Backpressure Mechanisms

#### Mechanism 1: Consumer Scaling

When queue depth grows, Cloudflare automatically:

1. **Scales up consumer instances** (up to `max_concurrency`)
2. **Increases batch sizes** (up to `max_batch_size`)
3. **Reduces batch timeout** (processes faster)

```
Queue depth: 0-100      → 1 consumer, small batches
Queue depth: 100-1000   → 3 consumers, medium batches
Queue depth: 1000+      → 5 consumers, full batches
```

#### Mechanism 2: Retry Backoff

If D1 writes fail (e.g., "database is locked"):

```typescript
// Consumer automatically retries with exponential backoff
try {
  await env.DB.batch(statements);
  message.ack();  // Success, remove from queue
} catch (error) {
  if (error.message.includes('database is locked')) {
    message.retry();  // Retry after delay (1s, 2s, 4s, 8s...)
  } else {
    throw error;  // Dead letter queue
  }
}
```

**Retry schedule:**
- Attempt 1: Immediate
- Attempt 2: +1 second delay
- Attempt 3: +2 second delay
- Attempt 4: +4 second delay
- After max_retries (3): → Dead letter queue

#### Mechanism 3: Dead Letter Queue (DLQ)

Messages that fail after all retries go to DLQ:

```toml
[[queues.consumers]]
dead_letter_queue = "historical-data-dlq"
```

**What gets sent to DLQ:**
- Messages that cause consistent errors (bad data format)
- Messages that exceed retry limit
- Messages that crash the consumer

**You can then:**
- Inspect failed messages
- Fix the issue (code or data)
- Re-queue them manually

---

## Real-World Scenarios

### Scenario 1: Historical Backfill (Your 200MB Situation)

**What you did:**
- Fetched 200MB of historical data
- Producer queued it all rapidly

**What happened (or should happen):**

```
T+0 min:  Producer queues 50,000 messages (200MB ÷ 4KB avg)
          Queue depth: 50,000

T+1 min:  Consumer starts processing
          - 5 concurrent instances
          - 100 messages per batch
          - ~500 messages/min processed
          Queue depth: 49,500 (declining slowly)

T+10 min: Queue depth: 45,000 (still huge backlog)

T+60 min: Queue depth: 20,000 (making progress)

T+100 min: Queue depth: 0 (caught up!)
```

**Timeline:** ~100 minutes (1.5 hours) to process 50,000 messages at 500/min

**This is NORMAL!** Queues are designed to handle bursts like this.

---

### Scenario 2: Continuous Real-Time Data

**Your current setup:**
- Producer: 96 runs/day (every 15 min)
- Each run: ~195 data points (13 tokens × 3 sources × 5 data points)

**Math:**
- Per run: 195 messages queued
- Per day: 96 × 195 = 18,720 messages
- Per minute average: ~13 messages/min

**Consumer capacity:**
- Theoretical: 6,000 messages/min (if queue is full)
- Actual: ~500 messages/min (sustainable rate)

**Result:** Consumer has **38x** more capacity than needed! ✅

**Queue depth stays near zero** (messages processed immediately)

---

### Scenario 3: Queue Fills Up Completely

**What if queue reaches maximum capacity?**

Cloudflare Queues have limits:
- ✅ **Max messages in queue**: ~100,000 messages (estimated, varies by account)
- ✅ **Max message size**: 128KB per message
- ✅ **Max retention**: 24 hours (messages older than this are dropped)

**If queue fills completely:**

```typescript
// Producer receives an error when sending
try {
  await env.QUEUE.send({ body: dataPoint });
} catch (error) {
  if (error.message.includes('queue is full')) {
    // Queue is at capacity!
    // Options:
    // 1. Wait and retry
    // 2. Log error (data is lost)
    // 3. Store in R2 as backup
    // 4. Alert monitoring system
  }
}
```

**Recommended approach:**

```typescript
async function sendWithBackup(data: any, env: Env) {
  try {
    await env.QUEUE.send({ body: data });
  } catch (error) {
    if (error.message.includes('queue is full')) {
      // Fallback: Store in R2
      const timestamp = Date.now();
      await env.R2.put(
        `queue-overflow/${timestamp}.json`,
        JSON.stringify(data)
      );
      console.error('Queue full, backed up to R2');
    }
  }
}
```

---

## Monitoring Queue Health

### 1. Check Queue Depth

```bash
# View current queue depth
wrangler queues consumer historical-data-queue

# Output shows:
# - Messages in queue (backlog)
# - Messages delivered (throughput)
# - Messages acked (success rate)
# - Consumer errors
```

**Healthy indicators:**
- ✅ Queue depth < 1,000 (processing fast)
- ✅ Ack rate > 95% (few errors)
- ✅ Consumer errors < 1% (stable)

**Warning signs:**
- ⚠️ Queue depth > 10,000 (backlog building)
- ⚠️ Queue depth growing over time (not catching up)
- ⚠️ Consumer errors > 5% (something's wrong)

### 2. Monitor Consumer Performance

```bash
# Tail consumer logs in real-time
wrangler tail historical-data-queue-consumer --format pretty

# Look for:
# - Batch processing time
# - D1 write latency
# - Error messages
# - Retry attempts
```

**Example healthy log:**

```
[INFO] Processing batch of 100 messages
[INFO] D1 batch write completed in 245ms
[INFO] Acknowledged 100 messages
[INFO] Queue depth: 127
```

**Example unhealthy log:**

```
[ERROR] D1 batch write failed: database is locked
[WARN] Retrying batch (attempt 2/3)
[ERROR] Unknown error, acknowledging messages  ❌ BAD!
[INFO] Queue depth: 15,342 (growing)
```

### 3. Set Up Alerts

**Cloudflare Dashboard Alerts:**

1. Navigate to: **Queues → historical-data-queue → Metrics**
2. Create alert:
   - **Metric:** Queue depth
   - **Condition:** > 5,000 for 10 minutes
   - **Action:** Email notification

**Monitoring worker:**

```typescript
// queue-monitor.ts - Runs every 5 minutes
export default {
  async scheduled(event: ScheduledEvent, env: Env) {
    const stats = await env.QUEUE.getStats();

    if (stats.depth > 5000) {
      // Send alert via email/webhook
      await fetch('https://hooks.slack.com/...', {
        method: 'POST',
        body: JSON.stringify({
          text: `⚠️ Queue depth is ${stats.depth} messages!`
        })
      });
    }
  }
}
```

---

## Scaling Consumer Capacity

### Option 1: Increase Concurrency (Easiest)

```toml
# wrangler-historical-queue.toml
[[queues.consumers]]
max_concurrency = 10  # Increase from 5 to 10 (2x throughput)
max_batch_size = 100
max_batch_timeout = 5
```

**Result:** 2x more consumer instances = 2x throughput

**Trade-off:** More concurrent D1 writes (might hit rate limits)

---

### Option 2: Optimize Batch Writes

**Use D1 batch API more efficiently:**

```typescript
// BEFORE: Sequential writes (slow)
for (const msg of batch.messages) {
  await env.DB.prepare('INSERT...').bind(...).run();
  msg.ack();
}

// AFTER: Batched writes (100x faster)
const statements = batch.messages.map(msg =>
  env.DB.prepare('INSERT...').bind(...)
);
await env.DB.batch(statements);  // Execute all at once
batch.ackAll();  // Ack all at once
```

**Performance gain:** 100-1000x faster for large batches

---

### Option 3: Use Multiple Consumers

**Split by timeframe:**

```toml
# Consumer 1: Minute data
[[queues.consumers]]
queue = "historical-data-queue-minute"
max_concurrency = 5

# Consumer 2: Hourly data
[[queues.consumers]]
queue = "historical-data-queue-hourly"
max_concurrency = 5

# Consumer 3: Daily data
[[queues.consumers]]
queue = "historical-data-queue-daily"
max_concurrency = 5
```

**Result:** 3x total capacity (15 concurrent consumers)

---

### Option 4: Add Dead Letter Queue Processing

```typescript
// dlq-reprocessor.ts - Runs daily
export default {
  async scheduled(event: ScheduledEvent, env: Env) {
    // Check DLQ for failed messages
    const failedMessages = await env.DLQ.receiveMessages(100);

    if (failedMessages.length > 0) {
      console.log(`Reprocessing ${failedMessages.length} failed messages`);

      for (const msg of failedMessages) {
        try {
          // Retry with fixed code/data
          await processMessage(msg, env);
          msg.ack();
        } catch (error) {
          console.error('Still failing:', error);
          // Keep in DLQ for manual review
        }
      }
    }
  }
}
```

---

## Your Current Configuration Analysis

**From `wrangler-historical-queue.toml`:**

```toml
[[queues.consumers]]
queue = "historical-data-queue"
max_batch_size = 100
max_batch_timeout = 5
max_concurrency = 5
```

**Current capacity:**
- 5 concurrent consumers
- 100 messages per batch
- ~500-2500 messages/minute (depending on D1 speed)

**Current load:**
- Producer: ~13 messages/minute (continuous)
- Bursts: ~195 messages per 15-minute interval

**Verdict:** ✅ **You have 38x excess capacity!**

**Queue depth should be:**
- Normal operation: 0-50 messages (near-instant processing)
- During burst: 50-200 messages (clears in <30 seconds)
- Historical backfill: 10,000-50,000 messages (clears in 30-120 minutes)

---

## What You Should Do

### Immediate Actions:

1. **Fix the consumer to write to correct table** (top priority!)
   - Change `historical_prices` → `price_data`
   - Fix column mappings
   - Deploy updated consumer

2. **Monitor queue depth after fix:**
   ```bash
   wrangler queues consumer historical-data-queue
   ```
   - Should see depth decrease as messages process
   - Should reach 0 within an hour

3. **Check for messages in DLQ:**
   ```bash
   # If DLQ exists
   wrangler queues consumer historical-data-dlq
   ```
   - These are messages that failed all retries
   - Might be from your 200MB historical load

### Long-Term Monitoring:

1. **Set up daily queue health check:**
   ```bash
   # Add to cron
   0 12 * * * wrangler queues consumer historical-data-queue >> /var/log/queue-health.log
   ```

2. **Alert if queue depth > 5,000 for 10+ minutes**
   - This indicates consumer can't keep up
   - May need to increase concurrency

3. **Review DLQ weekly:**
   - Failed messages need manual review
   - May indicate data quality issues

---

## Summary: What Happens When Queue Fills Faster Than D1?

**Short answer:** Nothing bad! This is exactly what queues are designed for.

**The system will:**
1. ✅ Buffer messages in the queue (up to ~100K messages)
2. ✅ Scale consumer instances automatically (up to your max_concurrency)
3. ✅ Process as fast as D1 allows (~500-2500 messages/min)
4. ✅ Retry failed writes with exponential backoff
5. ✅ Send permanently failed messages to dead letter queue
6. ✅ Self-regulate and catch up during quieter periods

**You're safe because:**
- Current load: ~13 messages/min
- Consumer capacity: ~500 messages/min
- **Headroom: 38x excess capacity**

**Even during historical backfill:**
- 50,000 messages queued
- Processes in ~100 minutes
- System stable throughout

**Only concern:**
- Messages older than 24 hours are dropped (Cloudflare policy)
- So backlog must clear within 24 hours
- Your 50K messages @ 500/min = 100 minutes ✅ (well under 24 hours)

---

## Next Steps

Want me to:
1. ✅ Fix the consumer to write to `price_data` table?
2. ✅ Add queue monitoring dashboard?
3. ✅ Set up DLQ reprocessor?
4. ✅ Create alert system for queue health?

Let me know and I'll implement it!
