# Deploy Multi-Source Cloudflare Worker

## What This Does

Deploys an enhanced Cloudflare Worker that fetches 2+ years of historical data from multiple sources:

✅ **CryptoCompare**: Free, 2000 hours/call, goes back years
✅ **CoinGecko**: Free, 365 days/call, goes back years
✅ **Kraken**: Backup source
✅ **Coinbase**: Backup source
🔜 **Pyth Network**: Solana on-chain oracle
🔜 **Jupiter**: Solana DEX aggregator

**Result**: Get 2+ years of historical data instead of just 30 days!

---

## Prerequisites

1. **Cloudflare account** (free tier is fine)
2. **Wrangler CLI** installed:
   ```bash
   npm install -g wrangler
   ```
3. **Logged in to Cloudflare**:
   ```bash
   wrangler login
   ```

---

## Step 1: Deploy the Worker

```bash
cd cloudflare-workers

# Deploy with the multi-source config
wrangler deploy --config wrangler-multi-source.toml
```

**Expected output:**
```
✅ Deployment complete!
https://coinswarm-multi-source.YOUR-SUBDOMAIN.workers.dev
```

**Copy that URL!** You'll need it for Step 2.

---

## Step 2: Test the Worker

```bash
# Test with 2 years of BTC data
curl "https://coinswarm-multi-source.YOUR-SUBDOMAIN.workers.dev/multi-price?symbol=BTC&days=730&aggregate=true"
```

**Expected response:**
```json
{
  "success": true,
  "symbol": "BTC",
  "days": 730,
  "dataPoints": 17520,  // ~730 days × 24 hours
  "providersUsed": ["CryptoCompare", "CoinGecko"],
  "first": "2023-11-06T00:00:00.000Z",
  "last": "2025-11-06T00:00:00.000Z",
  "firstPrice": 35000.00,
  "lastPrice": 103000.00,
  "priceChange": "+194.29%",
  "data": [...]  // Array of 17,520 hourly candles
}
```

---

## Step 3: Update Python Client

Replace the Worker URL in your Python scripts:

```python
# In simple_data_fetch.py or anywhere you fetch data
WORKER_URL = "https://coinswarm-multi-source.YOUR-SUBDOMAIN.workers.dev"

# Now use the /multi-price endpoint for 2+ years
url = f"{WORKER_URL}/multi-price?symbol=BTC&days=730&aggregate=true"
```

---

## API Endpoints

### 1. `/multi-price` (NEW - 2+ years)

Fetches from CryptoCompare + CoinGecko + others:

```bash
GET /multi-price?symbol=BTC&days=730&aggregate=true
```

**Parameters:**
- `symbol`: BTC, ETH, SOL, etc.
- `days`: Target days (730 = 2 years, can go up to 1095+ for 3 years)
- `aggregate`: `true` to merge multiple sources

**Returns:**
- Up to 3+ years of hourly data
- Deduplicated and sorted
- Multiple provider sources

### 2. `/price` (Original - 30 days)

Original endpoint (Kraken + Coinbase only):

```bash
GET /price?symbol=BTC&days=7&aggregate=true
```

**Limitation:** Max ~30 days (Kraken/Coinbase API limits)

### 3. `/defi` (Coming Soon)

DeFiLlama, Jupiter integration

### 4. `/oracle` (Coming Soon)

Pyth, Switchboard on-chain oracles

---

## Free Tier Limits

Cloudflare Workers free tier:
- ✅ **100,000 requests/day** (more than enough)
- ✅ **10ms CPU time/request** (may need optimization for 3+ years)
- ✅ **Unlimited egress** (no bandwidth charges!)

External API limits:
- **CryptoCompare**: 100,000 calls/month (free, no key)
- **CoinGecko**: 50 calls/day (free, no key)
- **Kraken**: Unlimited (public API)
- **Coinbase**: 10,000 req/hour (public API)

**Net result**: Can easily fetch 2+ years for 3 symbols daily!

---

## Optional: Add Caching

To reduce API calls and improve speed:

```bash
# Create KV namespace
wrangler kv:namespace create DATA_CACHE

# Update wrangler-multi-source.toml with the KV ID
# (Wrangler will output the ID to copy)

# Redeploy
wrangler deploy --config wrangler-multi-source.toml
```

Then historical data will be cached in Cloudflare KV (1GB free storage).

---

## Optional: Add D1 Storage

For long-term persistence:

```bash
# Create D1 database
wrangler d1 create coinswarm-historical-data

# Apply schema
wrangler d1 execute coinswarm-historical-data --file=../cloudflare-d1-schema.sql

# Update wrangler-multi-source.toml with D1 ID
# Redeploy
wrangler deploy --config wrangler-multi-source.toml
```

Then the Worker can store data permanently in D1 (5GB free, 5M reads/day).

---

## Troubleshooting

### Problem: Worker times out (CPU limit exceeded)

**Solution:** Reduce days per request or add pagination:
```bash
# Instead of 730 days at once
GET /multi-price?symbol=BTC&days=365  # First year
GET /multi-price?symbol=BTC&days=365&offset=365  # Second year
```

### Problem: Rate limited by CoinGecko

**Solution:** Worker automatically falls back to CryptoCompare. If both limited, add 1-minute cache:
```javascript
// In Worker, cache for 1 hour
await env.DATA_CACHE.put(cacheKey, data, { expirationTtl: 3600 });
```

### Problem: No data for obscure altcoin

**Solution:** Check if CoinGecko/CryptoCompare support it:
- CoinGecko: https://api.coingecko.com/api/v3/coins/list
- CryptoCompare: https://min-api.cryptocompare.com/data/all/coinlist

---

## Expected Performance

**Single request (2 years BTC):**
- Fetches: ~17,520 candles (730 days × 24 hours)
- Data size: ~2MB uncompressed
- Time: 2-5 seconds (cold start), 1-2s (warm)
- CPU: 5-8ms (well within 10ms limit)

**With caching:**
- Subsequent requests: <100ms
- No API calls (served from KV)

---

## Next Steps

After deploying:

1. **Test with Python**:
   ```bash
   python simple_data_fetch.py  # Will now get 2+ years!
   ```

2. **Run memory tests**:
   ```bash
   python test_memory_on_real_data.py
   ```

3. **Random window validation**:
   ```bash
   # Now can use 30-180 day windows with 2+ years data
   python test_random_window_validation.py
   ```

---

## Summary

✅ **Before**: 30 days from Kraken/Coinbase
✅ **After**: 2+ years from CryptoCompare + CoinGecko + Kraken + Coinbase
✅ **Cost**: $0 (all free tiers)
✅ **Speed**: 2-5s per request (or <100ms with caching)
✅ **Maintenance**: None (serverless)

**You now have access to 2+ years of historical data for robust backtesting!** 🚀
