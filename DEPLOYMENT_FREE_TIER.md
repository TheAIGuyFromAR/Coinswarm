# Deploy Evolution System on Free Tier 🎉

Two options to run continuously for FREE:

## Option 1: Cloudflare Worker (Recommended)

**Pros:**
- 100% free forever (100,000 requests/day)
- Automatic cron triggers
- D1 database included (5GB free)
- Global edge network
- No timeout worries

**Limits:**
- Runs in micro-batches (50 trades per minute)
- Max 30 second execution time per request

### Deploy Steps:

1. **Create D1 Database:**
```bash
wrangler d1 create coinswarm-evolution
```

Copy the database ID and update `wrangler-evolution.toml`

2. **Initialize Database Schema:**
```bash
wrangler d1 execute coinswarm-evolution --file=cloudflare-d1-evolution-schema.sql
```

3. **Deploy Worker:**
```bash
wrangler deploy --config wrangler-evolution.toml
```

4. **That's it!** Your worker will now:
   - Generate 50 chaos trades every minute (72,000 trades/day)
   - Analyze patterns every 5 minutes
   - Test strategies every 10 minutes
   - Build a winning strategy database automatically

5. **Monitor Progress:**
```bash
# Check status via HTTP
curl https://coinswarm-evolution.YOURNAME.workers.dev/status

# Or view logs
wrangler tail --config wrangler-evolution.toml
```

### What You Get:
- **72,000 trades per day** (50 trades/min × 1440 minutes)
- **288 pattern analyses per day** (every 5 min)
- **144 strategy tests per day** (every 10 min)
- **All stored in D1** for pattern discovery

---

## Option 2: Docker Container (Alternative)

**Pros:**
- Runs full Python code continuously
- No batching needed
- Can run faster (1000+ trades per cycle)

**Cons:**
- Limited free tier hours
- May sleep on inactivity

### Free Tier Options:

#### Railway (Best)
- **500 hours/month free** (~16 hours/day)
- $5 credit/month
- Automatic deploys from GitHub

**Deploy:**
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Deploy
railway up
```

Or use GitHub integration:
1. Push to GitHub
2. Connect Railway to repo
3. Railway auto-detects Dockerfile.evolution
4. Deploy!

#### Render
- **750 hours/month free** (25 hours/day)
- Sleeps after 15 min inactivity (but that's OK for batch jobs)

**Deploy:**
1. Create account at render.com
2. New Background Worker
3. Connect GitHub repo
4. Docker: Use `Dockerfile.evolution`
5. Deploy

#### Fly.io
- **3 shared VMs free**
- 160GB transfer/month

**Deploy:**
```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Launch
flyctl launch --dockerfile Dockerfile.evolution

# Deploy
flyctl deploy
```

---

## Monitoring & Management

### Check Status (Cloudflare Worker):
```bash
curl https://your-worker.workers.dev/status
```

### Check Status (Docker Container):
```bash
# Railway
railway logs

# Render
# View logs in dashboard

# Fly.io
flyctl logs
```

### View Results:

**Cloudflare:**
```bash
# Query D1 directly
wrangler d1 execute coinswarm-evolution --command="SELECT COUNT(*) FROM chaos_trades"
wrangler d1 execute coinswarm-evolution --command="SELECT * FROM discovered_patterns WHERE votes > 0"
```

**Docker:**
```bash
# Data saved in container
# Set up volume mounts or export to S3/Cloudflare R2
```

---

## Cost Analysis

### Cloudflare Worker (FREE FOREVER):
- Requests: 100,000/day (we use ~1,440/day) ✅
- D1 Storage: 5GB (we use <100MB) ✅
- D1 Reads: 5M/day (we use ~10K/day) ✅
- D1 Writes: 100K/day (we use ~2K/day) ✅

**Total: $0/month**

### Railway (FREE for 16 hours/day):
- 500 hours/month = ~16 hours/day
- Run during peak hours only
- Pause at night

**Total: $0/month** (if under 500 hours)

### Render (FREE but with sleep):
- 750 hours/month
- Sleeps after 15 min inactivity
- Good for batch processing

**Total: $0/month**

---

## Recommended Setup

**Best Strategy: Cloudflare Worker**

Runs 24/7 forever for free with these results:

- **Day 1**: 72,000 trades generated
- **Day 7**: 504,000 trades, ~50 patterns discovered
- **Day 30**: 2.16M trades, ~200 patterns discovered
- **Month 3**: 6.48M trades, winning strategies identified! 🎉

No babysitting, no costs, no timeouts. Just continuous evolution discovering what actually works.

---

## Quick Start (Copy-Paste)

```bash
# 1. Install Wrangler
npm install -g wrangler

# 2. Login to Cloudflare
wrangler login

# 3. Create database
wrangler d1 create coinswarm-evolution

# 4. Copy the database_id from output and update wrangler-evolution.toml

# 5. Initialize schema
wrangler d1 execute coinswarm-evolution --file=cloudflare-d1-evolution-schema.sql

# 6. Deploy
wrangler deploy --config wrangler-evolution.toml

# 7. Check status
curl https://coinswarm-evolution.YOURNAME.workers.dev/status

# Done! System runs automatically forever.
```

---

## Troubleshooting

**Worker timing out?**
- Reduce batch size in code (50 → 25 trades)
- Split analysis into smaller chunks

**D1 storage full?**
- Free tier = 5GB (enough for millions of trades)
- Add cleanup job: Delete trades older than 30 days

**Need faster results?**
- Run multiple workers in parallel
- Or use Docker on Railway for 1000 trades/minute

**Want to scale up?**
- Paid Worker plan: Unlimited requests
- Or upgrade Railway: $5/month = unlimited hours
