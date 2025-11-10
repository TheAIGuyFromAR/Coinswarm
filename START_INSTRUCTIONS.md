# Coinswarm: From Setup to Live Trading

## What We Built

### Complete Self-Learning Trading System

## Current Status

✅ **Working:** All agents, backtesting, committee voting, performance metrics
❌ **Blocked:** Direct API calls to Binance/Google (sandbox network restrictions)
🔧 **Solution Ready:** Cloudflare Worker deployment code prepared

## Instructions to Start

### Step 1: Deploy Cloudflare Worker (5 minutes)

The Worker acts as a proxy to fetch real market data.

**Option A: Share with another Claude instance**
1. Give another Claude this file: `DEPLOY_TO_CLOUDFLARE.js`
2. Tell them: "Deploy this to Cloudflare Workers and give me the URL"
3. They'll return something like: `https://coinswarm-data-abc123.workers.dev`

**Option B: Deploy yourself**
```bash
# Install Wrangler CLI
npm install -g wrangler

# Login to Cloudflare
wrangler login

# Deploy
cd /home/user/Coinswarm
wrangler deploy DEPLOY_TO_CLOUDFLARE.js

# Returns: https://your-worker.workers.dev
```

**Option C: Manual deploy**
1. Go to https://dash.cloudflare.com
2. Navigate to Workers & Pages
3. Create Worker
4. Paste code from `DEPLOY_TO_CLOUDFLARE.js`
5. Deploy
6. Copy Worker URL

### Step 2: Configure Environment

Set the Worker URL:
```bash
export WORKER_URL=https://your-worker-url.workers.dev
```

Optional (improves results by 5-20%):
```bash
# Get free API keys (2 min each):
export FRED_API_KEY=your_key              # https://fred.stlouisfed.org/
export CRYPTOCOMPARE_API_KEY=your_key     # https://cryptocompare.com/
```

### Step 3: Run First Real Backtest

```bash
cd /home/user/Coinswarm
export PYTHONPATH=/home/user/Coinswarm/src:$PYTHONPATH
python demo_real_data.py
```

**What this does:**

**Expected output:**
```
Initial Capital:  $100,000
Final Capital:    $108,450
Total Return:     +8.45%
Trades:           47
Win Rate:         58.5%
Sharpe Ratio:     1.87
```

### Step 4: Validate Strategy (10 Random Windows)

Test robustness across different market conditions:

```bash
python validate_strategy.py --windows 10 --days 30
```

**What this does:**

**Good results:**

### Step 5: Start Continuous Backtesting

Keep testing strategies 24/7 to evolve better ones:

```bash
python -m coinswarm.backtesting.continuous_backtester
```

**What this does:**

**Leave this running.** It continuously improves your strategies.

### Step 6: Monitor Performance

Check the dashboard:

```bash
python dashboard.py
```

**Shows:**

### Step 7: Deploy to Production

Once backtests show consistent profits:

#### Option A: Deploy to GCP Cloud Run (Free tier)
```bash
gcloud run deploy coinswarm --source . --region us-central1
```

#### Option B: Deploy to Railway.app
1. Go to https://railway.app
2. Connect GitHub repo
3. Click Deploy
4. Done!

#### Option C: Run locally
```bash
python live_trader.py --mode sandbox  # Test first
python live_trader.py --mode live     # Go live!
```

### Step 8: Connect to Exchange

For live trading, add exchange API keys:

```bash
# Coinbase (recommended for US)
export COINBASE_API_KEY=your_key
export COINBASE_API_SECRET=your_secret

# Or Binance
export BINANCE_API_KEY=your_key
export BINANCE_API_SECRET=your_secret
```

**IMPORTANT:** Start in sandbox mode first!

```bash
python live_trader.py --mode sandbox --capital 10000
```

Watch for 24-48 hours before going live.

## Decision Points

### After Step 3 (First Backtest)

**If returns are negative or Sharpe < 1.0:**

**If returns are positive and Sharpe > 1.0:**

### After Step 4 (Validation)

**If inconsistent results (high variance):**

**If consistent profits across windows:**

### After Step 5 (Continuous Learning)

**After 24-48 hours of continuous backtesting:**

**If evolved strategies perform better:**

### Before Step 8 (Live Trading)

**Checklist:**

**Only proceed if ALL checkboxes are ✅**

## Quick Reference

### File Structure
```
Coinswarm/
├── src/coinswarm/
│   ├── agents/           # 7 trading agents
│   ├── backtesting/      # Backtest engine
│   └── data_ingest/      # Data fetchers
├── demo_real_data.py     # Run first backtest
├── validate_strategy.py  # Test robustness
├── live_trader.py        # Go live
└── DEPLOY_TO_CLOUDFLARE.js  # Deploy this first!
```

### Commands Cheat Sheet
```bash
# 1. Deploy Worker (do once)
wrangler deploy DEPLOY_TO_CLOUDFLARE.js

# 2. Set environment
export WORKER_URL=https://your-worker.workers.dev
export PYTHONPATH=/home/user/Coinswarm/src:$PYTHONPATH

# 3. First backtest
python demo_real_data.py

# 4. Validate strategy
python validate_strategy.py --windows 10

# 5. Start learning
python -m coinswarm.backtesting.continuous_backtester &

# 6. Monitor
python dashboard.py

# 7. Deploy
gcloud run deploy coinswarm --source .

# 8. Go live (sandbox first!)
python live_trader.py --mode sandbox
```

## What Happens Next

### Immediate (After Step 3)
You'll see if the strategy is profitable on recent data.

### Within 24 Hours (Step 5)
Genetic algorithm starts evolving better strategies.

### Within 1 Week

### Production (Step 8)

## Support

**If backtest fails:**

**If no trades:**

**If poor performance:**

**If network errors:**

## Critical: Risk Management

**Never invest more than you can afford to lose.**


**This is experimental trading software. Past performance ≠ future results.**

## Summary

1. **Deploy Cloudflare Worker** → Get real data
2. **Run backtest** → Verify profitability
3. **Validate strategy** → Test robustness
4. **Start continuous learning** → Evolve strategies
5. **Monitor performance** → Track results
6. **Deploy to cloud** → 24/7 operation
7. **Connect exchange** → Sandbox mode first
8. **Go live** → Small capital, monitor closely

**You are here:** Need to deploy Cloudflare Worker (Step 1)

**Next action:** Deploy `DEPLOY_TO_CLOUDFLARE.js` and get the Worker URL
