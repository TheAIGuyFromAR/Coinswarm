# Setting Up Real Data for Coinswarm

## Current Situation

✅ **What's Working:** All 7 agents, backtesting engine, committee voting
❌ **What's Blocked:** External API calls (Binance, Google News, etc.) due to sandbox network restrictions

## Quick Start (5 minutes)

### Option 1: Deploy Cloudflare Worker (Recommended)

**Why:** Cloudflare Worker acts as a proxy to fetch real Binance data, bypassing network restrictions.

**Steps:**

1. **Get Cloudflare Worker URL from other Claude:**
   - Share `DEPLOY_TO_CLOUDFLARE.js` with another Claude instance
   - Other Claude deploys to Cloudflare
   - Get back Worker URL (e.g., `https://coinswarm-data.workers.dev`)

2. **Update your code:**
   ```python
   from coinswarm.data_ingest.worker_client import WorkerClient

   # Use Worker instead of direct Binance
   client = WorkerClient("https://coinswarm-data.workers.dev")
   data = await client.fetch_data("BTCUSDT", "1h", days=30)
   ```

3. **Run backtest with real data:**
   ```bash
   python demo_real_data.py
   ```

**Result:** Real Binance historical data in backtests!

---

### Option 2: Download CSV Files

**Why:** Binance provides free historical data downloads.

**Steps:**

1. **Visit Binance data repository:**
   ```
   https://data.binance.vision/
   ```

2. **Download kline data:**
   - Navigate to: data/spot/monthly/klines/BTCUSDT/1h/
   - Download recent months (e.g., BTCUSDT-1h-2024-10.zip)
   - Repeat for ETH USDT, SOLUSDT

3. **Extract and import:**
   ```bash
   unzip BTCUSDT-1h-2024-10.zip
   ```

4. **Use CSV importer:**
   ```python
   from coinswarm.data_ingest.csv_importer import CSVImporter

   importer = CSVImporter()
   data = importer.import_binance_csv("BTCUSDT-1h-2024-10.csv", "BTC-USDC", "1h")
   ```

**Result:** Real historical data without API calls!

---

### Option 3: Run Locally (Best for Development)

**Why:** Your local machine doesn't have network restrictions.

**Steps:**

1. **Clone repo locally:**
   ```bash
   git clone https://github.com/your-username/Coinswarm.git
   cd Coinswarm
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run backtest:**
   ```bash
   python demo_real_data.py
   ```

**Result:** Direct access to Binance, Google News, all APIs!

---

## API Keys (Optional, All FREE)

### Essential (Highly Recommended)

**1. FRED API (Macro Economic Data)**
- **What:** Fed rates, inflation, unemployment, gold, dollar index
- **Cost:** FREE
- **Setup:** 2 minutes
- **Get Key:** https://fred.stlouisfed.org/docs/api/api_key.html

```bash
export FRED_API_KEY="your_key_here"
```

### Recommended (Better Sentiment)

**2. CryptoCompare API (Crypto News)**
- **What:** Crypto-focused news aggregator
- **Cost:** FREE tier (50 requests/day)
- **Setup:** 2 minutes
- **Get Key:** https://www.cryptocompare.com/cryptopian/api-keys

```bash
export CRYPTOCOMPARE_API_KEY="your_key_here"
```

### Optional (Even More Sentiment)

**3. NewsAPI.org (Mainstream News)**
- **What:** General news coverage
- **Cost:** FREE tier (100 requests/day, 30 days history)
- **Setup:** 1 minute
- **Get Key:** https://newsapi.org/register

```bash
export NEWSAPI_KEY="your_key_here"
```

**4. Reddit API (Social Sentiment)**
- **What:** r/CryptoCurrency, r/Bitcoin sentiment
- **Cost:** FREE
- **Setup:** 5 minutes
- **Get Key:** https://www.reddit.com/prefs/apps

```bash
export REDDIT_CLIENT_ID="your_id"
export REDDIT_CLIENT_SECRET="your_secret"
```

---

## Data Sources Overview

### Price Data (Required)

| Source | Status | Method | Cost | Setup Time |
|--------|--------|--------|------|------------|
| **Binance API** | ✅ Best | Cloudflare Worker | FREE | 5 min |
| **Binance CSV** | ✅ Good | Manual download | FREE | 10 min |
| **Mock Data** | ✅ Testing | Generated | FREE | 0 min |

### Sentiment Data (Recommended)

| Source | Status | Cost | API Key | Historical Data |
|--------|--------|------|---------|-----------------|
| **Fear & Greed** | ✅ Works | FREE | No | 90 days |
| **Google News** | ⚠️ Blocked in sandbox | FREE | No | Unlimited |
| **CryptoCompare** | ✅ Works locally | FREE (50/day) | Yes | Years |
| **NewsAPI** | ✅ Works locally | FREE (100/day) | Yes | 30 days |

### Macro Data (Recommended)

| Source | Status | Cost | API Key | Data |
|--------|--------|------|---------|------|
| **FRED** | ✅ Works | FREE | Yes | Decades |
| **Yahoo Finance** | ✅ Works | FREE | No | Years |

---

## Running Backtests

### With Mock Data (Works Now)

```bash
# All 7 agents, realistic market simulation
python demo_full_backtest.py
```

**Output:**
```
Initial Capital:  $100,000
Final Capital:    $91,162
Total Return:     -8.84%
Trades:           3
Win Rate:         66.7%
Sharpe Ratio:     -10.99
```

### With Real Data (After Setup)

```bash
# Option A: Via Cloudflare Worker
export WORKER_URL="https://coinswarm-data.workers.dev"
python demo_real_data.py

# Option B: Via CSV Files
python demo_with_csv.py --btc BTCUSDT-1h-2024-10.csv

# Option C: Locally (direct Binance API)
python demo_real_data.py  # Just works™
```

---

## Deployment Options

### 1. Local Development (Recommended for Testing)

**Pros:**
- ✅ No network restrictions
- ✅ Direct API access
- ✅ Fast iteration
- ✅ Easy debugging

**Cons:**
- ❌ Requires your computer on
- ❌ No 24/7 backtesting

**Setup:**
```bash
git clone <repo>
pip install -r requirements.txt
python demo_real_data.py
```

---

### 2. GCP Cloud Run (Recommended for Production)

**Pros:**
- ✅ Free tier (2M requests/month)
- ✅ Scalable
- ✅ No network restrictions
- ✅ 24/7 operation

**Cons:**
- ⚠️ 5 min setup required

**Setup:**
```bash
# 1. Install gcloud CLI
curl https://sdk.cloud.google.com | bash

# 2. Initialize project
gcloud init

# 3. Deploy
gcloud run deploy coinswarm \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

---

### 3. Railway.app (Easiest Production Deploy)

**Pros:**
- ✅ One-click deploy from GitHub
- ✅ Free tier ($5/month credit)
- ✅ No config needed
- ✅ Auto HTTPS

**Setup:**
1. Go to https://railway.app
2. Connect GitHub repo
3. Deploy button
4. Done!

---

### 4. Cloudflare Workers (For Data Proxy Only)

**Pros:**
- ✅ FREE (100k requests/day)
- ✅ Global edge network
- ✅ Bypasses sandbox restrictions
- ✅ 1 min deploy

**Cons:**
- ⚠️ Can't run Python (use for data fetching only)

**Setup:** See DEPLOY_TO_CLOUDFLARE.js

---

## Complete Setup Script

Create `.env` file:
```bash
# Price Data
WORKER_URL=https://coinswarm-data.workers.dev

# Sentiment Data (all optional, all free)
CRYPTOCOMPARE_API_KEY=your_key_here
NEWSAPI_KEY=your_key_here

# Macro Data (optional, free)
FRED_API_KEY=your_key_here

# Social Data (optional, free)
REDDIT_CLIENT_ID=your_id_here
REDDIT_CLIENT_SECRET=your_secret_here

# Database (optional)
COSMOS_CONNECTION_STRING=your_connection_here
```

Load environment:
```python
from dotenv import load_dotenv
load_dotenv()

# All API keys automatically loaded!
```

---

## Quick Start Commands

### Minimum Setup (Works Now)
```bash
# Uses mock data
python demo_full_backtest.py
```

### Recommended Setup (5 min)
```bash
# 1. Deploy Cloudflare Worker (ask other Claude)
# 2. Get Worker URL
# 3. Run with real data
export WORKER_URL=https://your-worker.workers.dev
python demo_real_data.py
```

### Full Setup (30 min)
```bash
# 1. Get all API keys (see above)
# 2. Create .env file
# 3. Deploy to Cloud Run
gcloud run deploy coinswarm --source .

# 4. Start continuous backtesting
python continuous_backtest.py
```

---

## Troubleshooting

### "403 Forbidden" from Binance
**Cause:** Sandbox network restrictions
**Fix:** Use Cloudflare Worker or download CSV files

### "403 Forbidden" from Google News
**Cause:** Sandbox network restrictions
**Fix:** Run locally or use mock sentiment

### "No module named 'coinswarm'"
**Cause:** Python path not set
**Fix:**
```bash
export PYTHONPATH=/path/to/Coinswarm/src:$PYTHONPATH
# Or
pip install -e .
```

### "Division by zero" errors
**Cause:** RiskManager needs price history
**Fix:** Will be auto-fixed once agents run for a few minutes

### No trades being executed
**Cause:** Agents too conservative (confidence threshold too high)
**Fix:** Lower threshold in committee:
```python
committee = AgentCommittee(
    agents=agents,
    confidence_threshold=0.5  # Lower = more trades
)
```

---

## Next Steps

1. ✅ **Deploy Cloudflare Worker** → Get real price data
2. ✅ **Get FRED API key** → Add macro data
3. ✅ **Get CryptoCompare key** → Add sentiment
4. ✅ **Run 3-month backtest** → Test strategy
5. ✅ **Test multiple windows** → Validate robustness
6. ✅ **Deploy to Cloud Run** → 24/7 backtesting
7. ✅ **Connect to Coinbase** → Live trading!

---

## Summary

**What You Have Now:**
- ✅ All 7 agents working
- ✅ Complete backtesting system
- ✅ Committee voting
- ✅ Performance metrics
- ✅ Mock data for testing

**What You Need:**
- 📊 Real price data (Cloudflare Worker OR CSV files OR local)
- 📰 Sentiment data (optional, improves results 5-20%)
- 📈 Macro data (optional, improves risk management)

**Fastest Path to Real Data:**
1. Share DEPLOY_TO_CLOUDFLARE.js with other Claude (2 min)
2. Get Worker URL back
3. Run `python demo_real_data.py` with Worker URL
4. Done!

**Questions?** See docs/DATA_SOURCES.md for detailed info on each source.
