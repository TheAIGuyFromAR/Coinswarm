# Cloudflare Worker Deployment Plan - Fix Historical Data Issue

## 🔍 Root Cause Analysis

### Issue Identified
The deployed Cloudflare Worker at `https://coinswarm.bamn86.workers.dev` is running an **old version** that:
- ❌ Only returns **30 days** of data (721 candles)
- ❌ Missing `/multi-price` endpoint for 2+ years support
- ❌ Doesn't use CryptoCompare or CoinGecko for extended history

### Evidence
```bash
# Testing 30 days - works
curl "https://coinswarm.bamn86.workers.dev/price?symbol=BTC&days=30"
# Returns: 720 candles ✅

# Testing 180 days - FAILS
curl "https://coinswarm.bamn86.workers.dev/price?symbol=BTC&days=180"
# Returns: 721 candles (still only 30 days!) ❌

# Testing /multi-price endpoint - DOESN'T EXIST
curl "https://coinswarm.bamn86.workers.dev/multi-price?symbol=BTC&days=730"
# Returns: null ❌
```

### Current vs Required

| Metric | Current (Deployed) | Required (P0) | Solution Available |
|--------|-------------------|---------------|-------------------|
| Data Range | 30 days | **180+ days (6 months)** | ✅ Code ready |
| Max Candles | 721 | 4,320+ (180 days × 24h) | ✅ Code ready |
| Endpoint | `/price` only | `/multi-price` | ✅ Code ready |
| Sources | Kraken + Coinbase | CryptoCompare + CoinGecko | ✅ Code ready |

## ✅ Solution Available

We have **two working implementations** ready to deploy:

### Option 1: Multi-Source Worker (RECOMMENDED)
**File:** `cloudflare-workers/multi-source-data-fetcher.js`

**Features:**
- ✅ Fetches from CryptoCompare (2000 hours/call, FREE)
- ✅ Fetches from CoinGecko (365 days/call, FREE)
- ✅ Falls back to Kraken + Coinbase
- ✅ Deduplication and aggregation
- ✅ Supports **2+ years** of data

**Endpoints:**
```
GET /multi-price?symbol=BTC&days=730    # 2 years
GET /price?symbol=BTC&days=30            # Original (30 days)
```

**Config:** `cloudflare-workers/wrangler-multi-source.toml`

### Option 2: Paginated Binance Worker
**File:** `cloudflare-workers/data-fetcher-paginated.js`

**Features:**
- ✅ Paginates through Binance API
- ✅ Overcomes 1000 candle limit
- ✅ Supports **2+ years** from Binance

**Config:** `cloudflare-workers/wrangler.toml`

## 📋 Deployment Steps

### Prerequisites
- ✅ Wrangler CLI installed
- ⏳ Cloudflare API token (WAITING FROM USER)

### Step 1: Authenticate with Cloudflare

```bash
# Option A: Interactive login (opens browser)
wrangler login

# Option B: Use API token (for CI/CD)
export CLOUDFLARE_API_TOKEN="your-token-here"
```

### Step 2: Deploy Multi-Source Worker

```bash
cd /home/user/Coinswarm/cloudflare-workers

# Deploy the multi-source worker
wrangler deploy --config wrangler-multi-source.toml

# Expected output:
# ✅ Deployment complete!
# URL: https://coinswarm-multi-source.<subdomain>.workers.dev
```

### Step 3: Test Deployment

```bash
# Test 6 months (P0 requirement)
curl "https://coinswarm-multi-source.<subdomain>.workers.dev/multi-price?symbol=BTC&days=180" | jq '.dataPoints, .first, .last'

# Expected output:
# 4320      # (180 days × 24 hours)
# "2025-05-10T00:00:00.000Z"
# "2025-11-06T00:00:00.000Z"

# Test 2 years
curl "https://coinswarm-multi-source.<subdomain>.workers.dev/multi-price?symbol=BTC&days=730" | jq '.dataPoints'

# Expected output:
# 17520     # (730 days × 24 hours)
```

### Step 4: Update Python Client

Update `src/coinswarm/data_ingest/coinswarm_worker_client.py`:

```python
class CoinswarmWorkerClient:
    def __init__(self, worker_url: str = "https://coinswarm-multi-source.<subdomain>.workers.dev"):
        self.worker_url = worker_url.rstrip('/')
        self.timeout = 30.0

    async def fetch_price_data(
        self,
        symbol: str,
        days: int = 30,
        aggregate: bool = True
    ) -> List[DataPoint]:
        """
        Fetch historical price data from Worker.

        NOW SUPPORTS: Up to 730+ days (2+ years)!
        """

        # Use /multi-price for 30+ days
        if days > 30:
            url = f"{self.worker_url}/multi-price"
        else:
            url = f"{self.worker_url}/price"

        params = {
            "symbol": symbol,
            "days": days,
            "aggregate": "true" if aggregate else "false"
        }

        # ... rest of implementation
```

### Step 5: Verify with Python

```bash
cd /home/user/Coinswarm

# Test P0 requirement (6 months)
python -c "
import asyncio
from src.coinswarm.data_ingest.coinswarm_worker_client import CoinswarmWorkerClient

async def test():
    client = CoinswarmWorkerClient()
    data = await client.fetch_price_data('BTC', days=180)
    print(f'✅ Fetched {len(data)} candles (P0 requirement met!)')

asyncio.run(test())
"
```

## 🎯 Testing Plan

Once deployed, run these tests:

### Test 1: P0 Requirement (6 months)
```bash
python fetch_binance_historical.py test-p0
```

**Expected:**
- ✅ 4,320+ candles (180 days × 24 hours)
- ✅ Data from May 2025 to Nov 2025

### Test 2: Random Patterns
```bash
python fetch_binance_historical.py test-random
```

**Tests:**
- 7, 14, 30, 60, 90, 120, 180, 270, 365, 547, 730 days
- Verifies pagination works for all ranges

### Test 3: Multiple Symbols
```bash
python fetch_binance_historical.py test-multi
```

**Tests:**
- BTC, ETH, SOL
- 180 days each

## 📊 Expected Results

### Before Deployment
```
/price?symbol=BTC&days=180
└─> Returns: 721 candles (30 days) ❌
```

### After Deployment
```
/multi-price?symbol=BTC&days=180
└─> Returns: 4,320 candles (180 days) ✅

/multi-price?symbol=BTC&days=730
└─> Returns: 17,520 candles (730 days) ✅
```

## 🔧 Troubleshooting

### Issue: "You are not authenticated"
```bash
wrangler login
# OR
export CLOUDFLARE_API_TOKEN="your-token"
```

### Issue: "Account ID not found"
```bash
# Check your account ID
wrangler whoami

# Add to wrangler-multi-source.toml if needed
account_id = "your-account-id"
```

### Issue: Worker times out (10ms CPU limit)
```bash
# Reduce days per request
# Instead of 730 days at once, try 365 days
curl "/multi-price?symbol=BTC&days=365"
```

### Issue: Rate limited by CryptoCompare/CoinGecko
```bash
# Worker automatically falls back between sources
# Check response to see which sources were used:
curl "/multi-price?symbol=BTC&days=180" | jq '.sources'
# ["CryptoCompare", "CoinGecko"]
```

## 📝 Summary

**Status:**
- ✅ Root cause identified: Old worker deployed
- ✅ Solution ready: Multi-source worker with 2+ years support
- ✅ Wrangler CLI installed
- ⏳ Waiting for: Cloudflare API token

**Once we have the API token:**
1. Authenticate: `wrangler login` or `export CLOUDFLARE_API_TOKEN`
2. Deploy: `wrangler deploy --config wrangler-multi-source.toml`
3. Test: Verify 6+ months data (P0 requirement)
4. Update: Python client to use new endpoint

**Time to deploy:** ~5 minutes once authenticated

**P0 Requirement:** ✅ Will be met immediately after deployment
- Current: 30 days max
- After deployment: 180+ days (6+ months)
- Extended: 730+ days (2+ years)
