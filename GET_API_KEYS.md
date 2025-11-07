# How to Get Free API Keys

## 🔑 CryptoCompare API Key (FREE - 100K calls/month)

**Best for:** Historical data with minute-level granularity

### Step 1: Sign Up
1. Go to: https://www.cryptocompare.com/
2. Click **"Sign Up"** (top right)
3. Create free account (email + password)
4. Verify your email

### Step 2: Get API Key
1. Login to your account
2. Go to: https://www.cryptocompare.com/cryptopian/api-keys
3. Or: Dashboard → API Keys
4. Click **"Create New Key"**
5. Name it: `Coinswarm`
6. **Copy the API key** (looks like: `abc123def456...`)

### Step 3: Add to Worker
Edit your worker code and add the API key on **line 176**:

```javascript
// Old (line 173):
const url = `https://min-api.cryptocompare.com/data/v2/histohour?fsym=${symbol}&tsym=USD&limit=${limit}&toTs=${toTs}`;

// New (with your API key):
const url = `https://min-api.cryptocompare.com/data/v2/histohour?fsym=${symbol}&tsym=USD&limit=${limit}&toTs=${toTs}&api_key=YOUR_API_KEY_HERE`;
```

**Free Tier Limits:**
- ✅ 100,000 API calls per month
- ✅ Minute, hourly, and daily data
- ✅ Goes back years
- ✅ No credit card required

---

## 🔑 CoinGecko API Key (FREE - 10,000 calls/month)

**Best for:** Daily/hourly data, no key needed for basic use

### Option A: No API Key Needed (Basic)
CoinGecko works without an API key for:
- ✅ Up to 90 days hourly data
- ✅ Up to 365 days daily data
- ✅ 50 calls per minute
- ✅ Already works in our worker!

### Option B: Get Free API Key (Pro Features)
1. Go to: https://www.coingecko.com/en/api
2. Click **"Get Your Free API Key"**
3. Sign up with email
4. Get "Demo API Key" (10-50 calls/min)

**Add to worker (line 251):**
```javascript
// Old:
const response = await fetch(url, {
  headers: { 'User-Agent': 'Coinswarm/1.0' }
});

// New (with API key):
const response = await fetch(url, {
  headers: {
    'User-Agent': 'Coinswarm/1.0',
    'x-cg-demo-api-key': 'YOUR_COINGECKO_KEY'
  }
});
```

---

## 🔑 Binance API Key (OPTIONAL - Not needed for public data)

**Note:** Binance **public API doesn't require a key** for OHLC data!

Our worker uses public endpoints only:
- ✅ No API key needed
- ✅ 1200 requests/minute
- ✅ Minute-level data (1m, 5m, 15m, 30m, 1h)
- ✅ Already works in Cloudflare Worker

**If you want account-specific features:**
1. Go to: https://www.binance.com/
2. Create account
3. Account → API Management
4. Create API key (for trading/account data only)

**We don't need this for historical data!**

---

## 🔑 Alpha Vantage API Key (FREE - Alternative source)

**Good for:** Minute data, stocks + crypto

### Get API Key
1. Go to: https://www.alphavantage.co/support/#api-key
2. Fill form with your email
3. **Instant API key** sent to email
4. No verification needed!

**Add to worker:**
```javascript
const url = `https://www.alphavantage.co/query?function=CRYPTO_INTRADAY&symbol=BTC&market=USD&interval=5min&apikey=YOUR_KEY`;
```

**Free Tier:**
- ✅ 25 API calls per day (very limited!)
- ✅ Minute-level data
- ✅ 1-2 months of history

---

## 📊 Quick Comparison

| Source | Free Calls | API Key Required | Minute Data | History | Best For |
|--------|-----------|------------------|-------------|---------|----------|
| **CryptoCompare** | 100K/month | ✅ Yes | ✅ Yes | Years | **Best overall** |
| **CoinGecko** | 10K/month | ❌ No | ❌ No | 365 days | Daily/hourly |
| **Binance** | 1200/min | ❌ No | ✅ Yes | 1000 candles | Minute data |
| **Kraken** | Unlimited | ❌ No | ✅ Yes | 720 candles | Minute data |
| **Coinbase** | 10K/hour | ❌ No | ✅ Yes | 300 candles | Minute data |
| Alpha Vantage | 25/day | ✅ Yes | ✅ Yes | 1-2 months | Limited use |

---

## 🎯 Recommended Setup for P0 (180 days)

### Best Free Combination:

**1. CryptoCompare (with free API key)**
- Sign up: https://www.cryptocompare.com/
- Get 100,000 calls/month free
- Use for: Bulk historical data (hours/days)

**2. Kraken (no key needed)**
- Already working in worker
- Use for: Recent minute-level data

**3. CoinGecko (no key needed)**
- Already working in worker
- Use for: Backup/validation

### Quick Setup (5 minutes):

1. **Get CryptoCompare key**: https://www.cryptocompare.com/cryptopian/api-keys
2. **Copy the key** (looks like: `abc123...`)
3. **Update worker** at line 176:
   ```javascript
   &api_key=YOUR_KEY_HERE
   ```
4. **Redeploy worker** in Cloudflare Dashboard
5. **Test**: `curl "https://swarm.bamn86.workers.dev/multi-price?symbol=BTC&days=180"`

**Result:** ✅ P0 requirement met with minute-level data!

---

## 🔐 Security Note

**DO NOT commit API keys to git!**

**Option 1: Use Cloudflare Environment Variables**
```javascript
// In worker code:
const API_KEY = env.CRYPTOCOMPARE_API_KEY;

// Set in Cloudflare Dashboard:
// Workers → Your Worker → Settings → Variables
// Add: CRYPTOCOMPARE_API_KEY = your_key_here
```

**Option 2: Use Wrangler Secrets**
```bash
# From command line:
wrangler secret put CRYPTOCOMPARE_API_KEY
# Paste your key when prompted
```

**Option 3: Hardcode (Only for testing)**
```javascript
// TEMPORARY ONLY - Don't commit!
const API_KEY = 'your_key_here';
```

---

## ✅ Summary

**To get P0 (180 days) working:**

1. **CryptoCompare** - Get free key (5 min): https://www.cryptocompare.com/cryptopian/api-keys
2. **Add to worker** - Line 176 of `multi-source-data-fetcher.js`
3. **Redeploy** - Paste updated code to Cloudflare Dashboard
4. **Done!** - Now get 2+ years of minute-level data

**Time:** 5 minutes
**Cost:** $0
**Result:** Full historical data access ✅
