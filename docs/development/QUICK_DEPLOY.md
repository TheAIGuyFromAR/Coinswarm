# Quick Deploy - Free Agents SDK Evolution System

## Prerequisites

1. **Cloudflare account** (free tier is fine)
2. **wrangler installed**: `npm install -g wrangler`
3. **Logged in**: `wrangler login`

## One-Command Deploy

```bash
./deploy-agent.sh
```

This script will:
1. ✅ Check authentication
2. ✅ Create D1 database (if needed)
3. ✅ Initialize database schema
4. ✅ Install dependencies
5. ✅ Deploy the agent
6. ✅ Start the evolution system

## Manual Deploy (if script fails)

### Step 1: Login
```bash
wrangler login
```

### Step 2: Create Database
```bash
cd cloudflare-agents
wrangler d1 create coinswarm-evolution
```

Copy the `database_id` from the output.

### Step 3: Update Configuration
Edit `cloudflare-agents/wrangler.toml`:
```toml
database_id = "YOUR_DATABASE_ID_HERE"  # Replace with actual ID
```

### Step 4: Initialize Schema
```bash
wrangler d1 execute coinswarm-evolution --file=../cloudflare-d1-evolution-schema.sql
```

### Step 5: Deploy
```bash
npm install
npm run deploy
```

### Step 6: Start Agent
```bash
# Get your worker URL from deploy output, then:
curl -X POST https://coinswarm-evolution-agent.YOUR-ACCOUNT.workers.dev/trigger
```

## Verify Deployment

```bash
# Check status
curl https://coinswarm-evolution-agent.YOUR-ACCOUNT.workers.dev/status

# View stats
curl https://coinswarm-evolution-agent.YOUR-ACCOUNT.workers.dev/stats | jq

# Stream logs
wrangler tail
```

## What Happens Next

The agent will:
- Generate 50 chaos trades every 60 seconds
- Analyze patterns every 5 minutes
- Test strategies every 10 minutes
- Run continuously 24/7
- Cost: **$0/month** (stays in free tier)

Expected results:
- **Day 1**: 72,000 trades
- **Week 1**: 504,000 trades, ~50 patterns
- **Month 1**: 2.16M trades, winning strategies identified

## Troubleshooting

**"Not authenticated"**
```bash
wrangler login
```

**"Database already exists"**
```bash
# Get existing database ID
wrangler d1 list

# Update wrangler.toml with the ID
```

**"Deployment failed"**
```bash
# Check logs
wrangler tail

# Try deploying again
npm run deploy
```

**"Agent not running"**
```bash
# Trigger manually
curl -X POST https://your-agent.workers.dev/trigger

# Check status
curl https://your-agent.workers.dev/status
```

## Monitoring

### Check Progress
```bash
# Every 10 seconds
watch -n 10 'curl -s https://your-agent.workers.dev/stats | jq ".database"'
```

### Query Database
```bash
# Total trades
wrangler d1 execute coinswarm-evolution --command="SELECT COUNT(*) FROM chaos_trades"

# Winning patterns
wrangler d1 execute coinswarm-evolution --command="
  SELECT name, votes, accuracy
  FROM discovered_patterns
  WHERE votes > 0
  ORDER BY votes DESC
  LIMIT 10
"
```

## Next Steps

1. **Let it run for 1 week**
2. **Check discovered patterns**
3. **Analyze winning strategies**
4. **Consider scaling up** (see DEPLOYMENT_SCALED_$5_PLAN.md)

🎉 **Your evolution system is now discovering winning strategies 24/7!**
<!-- Cleared: Content moved to Development_strategies.md -->
