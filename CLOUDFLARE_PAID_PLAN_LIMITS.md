# Cloudflare Workers Paid Plan ($5/month) - Complete Limits & Included Usage

**Last Updated**: January 2025
**Base Cost**: $5 USD per month minimum

This document outlines ALL included usage limits for Cloudflare's Workers Paid plan to help you avoid incurring additional usage charges.

---

## Table of Contents
1. [Workers](#workers)
2. [D1 Database](#d1-database)
3. [KV Storage](#kv-storage)
4. [R2 Object Storage](#r2-object-storage)
5. [Durable Objects](#durable-objects)
6. [Queues](#queues)
7. [Workers AI](#workers-ai)
8. [Vectorize](#vectorize)
9. [Hyperdrive](#hyperdrive)
10. [Containers](#containers)

---

## Workers

### Included Monthly Limits
- **Requests**: 10 million requests/month
- **CPU Time**: Standard usage model (pay per ms)
- **Duration**: No wall clock time charges (only CPU time)

### Overage Pricing
- **$0.50** per million requests (after 10M included)
- **$0.02** per million CPU milliseconds

### Key Features
- Scale to zero pricing
- No charges while waiting on I/O
- All limits reset monthly based on subscription date

---

## D1 Database

### Included Monthly Limits
- **Rows Read**: 25 billion rows
- **Rows Written**: 50 million rows
- **Storage**: 5 GB

### Overage Pricing
- **Rows Read**: $0.001 per million rows
- **Rows Written**: $1.00 per million rows
- **Storage**: $0.75 per GB/month

### Database Limits
- **Max Database Size**: 10 GB (cannot be increased)
- **Max Databases per Account**: 50,000 databases
- **Total Storage per Account**: 1 TB maximum

### Key Features
- **NO egress charges** - Free data transfer out
- **Time Travel**: Restore to any minute within last 30 days (FREE)
- **Read Replicas**: No additional charges

---

## KV Storage

### Included Monthly Limits
- **Storage**: 1 GB
- **Read Operations**: 10 million
- **Write Operations**: 1 million
- **Delete Operations**: 1 million
- **List Operations**: 1 million

### Overage Pricing
- **Storage**: $0.50 per GB/month
- **Read Operations**: $0.50 per million
- **Write/Delete/List Operations**: $5.00 per million

### Technical Limits
- **Max Value Size**: 25 MB
- **Operations per Worker Invocation**: 1,000 operations

### Key Features
- No egress/bandwidth charges
- Eventual consistency model
- Operations billed per-key

---

## R2 Object Storage

### Free Tier (Applies to ALL Plans)
- **Storage**: 10 GB
- **Class A Operations**: 1 million/month (write, delete)
- **Class B Operations**: 10 million/month (read, list)
- **Egress**: UNLIMITED (always free)

### Overage Pricing (Standard Storage)
- **Storage**: $0.015 per GB/month
- **Class A Operations**: $4.50 per million
- **Class B Operations**: $0.36 per million
- **Egress**: $0.00 (FREE)

### Key Features
- Zero egress fees
- S3-compatible API
- Billed in GB-months
- Free tier applies to Standard storage only

---

## Durable Objects

### Included Monthly Limits
- **Requests**: 1 million requests

### Overage Pricing
- **Requests**: $0.15 per million (after 1M included)
- **Compute Duration**: Charged based on GB-seconds
- **Storage**: No billing enabled for SQLite-backed DO (currently)

### Storage Limits
- **Per Object Storage**: 10 GB (SQLite-backed)
- **Total Account Storage**: No limit (Paid plan)

### Key Features
- Available with SQLite or key-value storage
- Strongly consistent
- Global uniqueness

---

## Queues

### Included Monthly Limits
- **Operations**: 1 million operations

### Overage Pricing
- **$0.40** per million operations
- Operation = each 64 KB chunk written, read, or deleted

### Cost Estimates
- **Message Delivery**: ~3 operations (write, read, ack) = **$1.20/million messages**

### Technical Limits
- **Max Throughput**: 5,000 messages/second per queue
- **Max Concurrent Consumers**: 250
- **Max Queues per Account**: 10,000 queues
- **Message Retention**: 60 seconds to 14 days (default: 4 days)
- **Pull Consumer Rate**: 5,000 messages/second per queue

### Key Features
- No egress fees
- Globally distributed
- HTTP pull consumers supported

---

## Workers AI

### Included Daily Limits
- **Neurons**: 10,000 Neurons/day (FREE)
- Limits reset daily at 00:00 UTC

### Pricing Beyond Free Tier
- **$0.011** per 1,000 Neurons

### What are Neurons?
Neurons measure GPU compute across different AI models. Each model has different Neuron costs.

### Example Pricing (Llama 3.2-1b-instruct)
- **Input**: $0.027 per million tokens
- **Output**: $0.201 per million tokens

### Key Features
- Free daily allocation available on both Free and Paid plans
- Need Paid plan to use more than 10,000 Neurons/day
- Per-model Neuron mappings available

---

## Vectorize

### Included Monthly Limits
- **Queried Vector Dimensions**: 30 million/month
- **Stored Vector Dimensions**: 5 million/account

### Overage Pricing
- **Queried Dimensions**: $0.01 per million vector dimensions
- **Stored Dimensions**: $0.05 per 100 million vector dimensions

### Technical Limits
- **Max Indexes per Account**: 50,000 indexes
- **Max Namespaces per Index**: 50,000 namespaces
- **Max Dimensions per Index**: 5 million vector dimensions

### Key Features
- No CPU/memory charges
- No "active index hours" charges
- Only pay when querying
- Free tier available

---

## Hyperdrive

### Included in Plan
- **FREE** - No additional charges beyond Workers Paid plan
- Connection pooling included
- Query caching included

### How Billing Works
- Hyperdrive itself has NO charges
- Workers making queries are billed per Workers pricing
- All queries (cached or uncached) count toward limits

### Key Features
- Database connection pooling
- Query caching
- Works with PostgreSQL-compatible databases
- Limits reset daily at 00:00 UTC

---

## Containers

### Pricing Model
- Billed in **10ms slices** while container is running
- Scale to zero (no charges when idle)
- Charges apply for both Workers and Durable Objects usage

### Instance Types (Beta)
- **dev**: 256 MiB
- **basic**: 1 GiB
- **standard**: 4 GiB

### Network Egress - Included Monthly Limits
- **North America & Europe**: 1 TB included, then $0.025/GB
- **Australia, NZ, Taiwan, Korea**: 500 GB included, then $0.050/GB
- **Everywhere else**: 500 GB included, then $0.040/GB

### Current Limits
- **Total Memory**: 40 GiB concurrent
- **Total vCPU**: 40 vCPU concurrent
- **Autoscaling**: Triggers at 75% CPU usage

### Key Features
- Scale to zero
- Global deployment
- Docker container support

---

## Summary Table - What's Included in $5/month

| Service | Included Usage | Overage Price |
|---------|---------------|---------------|
| **Workers** | 10M requests | $0.50/M requests |
| **D1** | 25B rows read, 50M rows written, 5GB storage | $0.001/M reads, $1/M writes |
| **KV** | 1GB storage, 10M reads, 1M writes | $0.50/GB, $0.50/M reads |
| **R2** | 10GB storage, 1M Class A ops, 10M Class B ops | $0.015/GB, varies by op |
| **Durable Objects** | 1M requests | $0.15/M requests |
| **Queues** | 1M operations | $0.40/M operations |
| **Workers AI** | 10K Neurons/day | $0.011/1K Neurons |
| **Vectorize** | 30M queried dims, 5M stored dims | $0.01/M, $0.05/100M |
| **Hyperdrive** | FREE (no limits) | Workers pricing applies |
| **Containers** | Varies by region (1TB-500GB egress) | Varies by region |

---

## Important Notes

### Billing Periods
- Most limits reset **monthly** on your subscription renewal date
- **Workers AI** limits reset **daily** at 00:00 UTC
- **Hyperdrive** limits reset **daily** at 00:00 UTC

### No Hidden Fees
- **D1**: No egress charges, no Time Travel charges
- **R2**: No egress fees (always free)
- **KV**: No egress/bandwidth charges
- **Queues**: No egress fees
- **Vectorize**: No CPU/memory/index hour charges
- **Hyperdrive**: No additional charges

### Overage Strategy
To avoid unexpected charges:
1. Monitor usage in Cloudflare Dashboard
2. Set up billing alerts
3. Implement rate limiting in your applications
4. Use caching strategically (Hyperdrive, KV)
5. Optimize D1 queries (use indexes, limit reads)
6. Batch operations where possible

### Best Practices for Staying Under Limits

#### Workers (10M requests)
- Use caching (KV, Hyperdrive)
- Implement CDN for static assets
- Rate limit abusive traffic

#### D1 (25B reads, 50M writes)
- Create indexes on frequently queried columns
- Use `LIMIT` clauses
- Batch writes when possible
- Consider read replicas for read-heavy workloads

#### KV (10M reads, 1M writes)
- Cache frequently accessed data
- Use bulk operations
- Set appropriate TTLs

#### Queues (1M operations)
- Batch messages (each 64KB = 1 op)
- Optimize message size
- Process efficiently to minimize retries

#### Workers AI (10K Neurons/day)
- Cache AI responses
- Batch requests
- Use smaller models when appropriate

---

## Monitoring & Alerts

### Dashboard Metrics
Access real-time usage at: `https://dash.cloudflare.com/[account]/workers/analytics`

### Key Metrics to Monitor
- Workers requests (daily/monthly)
- D1 rows read/written
- KV operations
- Durable Objects requests
- Queue operations
- AI Neurons consumed

### Setting Up Alerts
1. Go to Cloudflare Dashboard
2. Navigate to Workers & Pages
3. Set up usage notifications
4. Configure email alerts at 50%, 75%, 90% of included limits

---

## Additional Resources

- [Cloudflare Workers Pricing](https://developers.cloudflare.com/workers/platform/pricing/)
- [D1 Pricing & Limits](https://developers.cloudflare.com/d1/platform/pricing/)
- [KV Pricing](https://developers.cloudflare.com/kv/platform/pricing/)
- [R2 Pricing](https://developers.cloudflare.com/r2/pricing/)
- [Durable Objects Pricing](https://developers.cloudflare.com/durable-objects/platform/pricing/)
- [Queues Pricing](https://developers.cloudflare.com/queues/platform/pricing/)
- [Workers AI Pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/)
- [Vectorize Pricing](https://developers.cloudflare.com/vectorize/platform/pricing/)
- [Containers Pricing](https://developers.cloudflare.com/containers/pricing/)

---

## Quick Reference Card

```
CLOUDFLARE WORKERS PAID PLAN - $5/MONTH INCLUDED LIMITS

COMPUTE
├─ Workers:         10M requests/month
├─ Workers AI:      10K Neurons/day
└─ Hyperdrive:      FREE (unlimited)

STORAGE
├─ D1:              5 GB + 25B reads + 50M writes
├─ KV:              1 GB + 10M reads + 1M writes
├─ R2:              10 GB + 1M writes + 10M reads
└─ Durable Objects: 1M requests

MESSAGING
└─ Queues:          1M operations

VECTOR/AI
└─ Vectorize:       30M queried + 5M stored dimensions

CONTAINERS
└─ Egress:          1 TB (NA/EU) or 500 GB (other regions)

ZERO EGRESS FEES: D1, R2, KV, Queues
TIME TRAVEL: D1 (30 days, FREE)
SCALE TO ZERO: Workers, Containers
```

---

**Note**: This document reflects pricing and limits as of January 2025. Always verify current limits at [Cloudflare's official documentation](https://developers.cloudflare.com/workers/platform/pricing/) as they may change.
