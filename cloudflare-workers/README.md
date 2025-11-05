# Cloudflare Worker: Data Fetcher

Fetches historical crypto data from Binance and caches it in KV storage.

## Why Use This?

- **Free tier**: 100K requests/day
- **Fast**: Edge network (50-200ms globally)
- **Cached**: KV storage for instant access
- **No credentials**: Uses public Binance API
- **Always available**: 99.99% uptime

## Setup (5 minutes)

### 1. Install Wrangler

```bash
npm install -g wrangler

# Login to Cloudflare
wrangler login
```

### 2. Create KV Namespace

```bash
# Create KV namespace for caching
wrangler kv:namespace create DATA_CACHE

# Output:
# ⛅️ wrangler 3.0.0
# 🌀 Creating namespace with title "coinswarm-data-fetcher-DATA_CACHE"
# ✨ Success!
# Add the following to your wrangler.toml:
# { binding = "DATA_CACHE", id = "abc123..." }

# Copy the ID and update wrangler.toml
```

### 3. Deploy

```bash
cd Coinswarm/cloudflare-workers
wrangler publish

# Output:
# ✨ Built successfully
# 🌍 Deploying...
# ✨ Success! Deployed to:
#    https://coinswarm-data-fetcher.your-subdomain.workers.dev
```

### 4. Test

```bash
# Fetch BTC data (30 days, 1-hour candles)
curl "https://coinswarm-data-fetcher.your-subdomain.workers.dev/fetch?symbol=BTCUSDT&timeframe=1h&days=30"

# Response:
# {
#   "symbol": "BTCUSDT",
#   "timeframe": "1h",
#   "days": 30,
#   "candles": 720,
#   "data": [
#     {
#       "timestamp": "2024-10-06T00:00:00.000Z",
#       "open": 62450.0,
#       "high": 62580.0,
#       "low": 62320.0,
#       "close": 62500.0,
#       "volume": 1234.56
#     },
#     ...
#   ],
#   "cached": true
# }
```

## API Endpoints

### GET /fetch

Fetch fresh data from Binance (and cache it).

**Parameters:**
- `symbol` - Trading pair (e.g., BTCUSDT, ETHUSDT, SOLUSDT)
- `timeframe` - Candle interval (1m, 5m, 15m, 1h, 4h, 1d)
- `days` - How many days of history (1-365)

**Example:**
```bash
GET /fetch?symbol=ETHUSDT&timeframe=1h&days=90
```

### GET /cached

Get cached data (faster, no API call).

**Parameters:**
- Same as /fetch

**Example:**
```bash
GET /cached?symbol=ETHUSDT&timeframe=1h&days=90
```

## Python Client

Use in your backtests:

```python
import httpx
import asyncio

async def fetch_data(symbol="BTCUSDT", timeframe="1h", days=30):
    """Fetch data from Cloudflare Worker"""

    url = "https://coinswarm-data-fetcher.your-subdomain.workers.dev/fetch"
    params = {"symbol": symbol, "timeframe": timeframe, "days": days}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, timeout=30.0)
        response.raise_for_status()
        return response.json()

# Usage
data = asyncio.run(fetch_data("BTCUSDT", "1h", 30))
print(f"Fetched {data['candles']} candles for {data['symbol']}")
```

## Cost Breakdown

**Free Tier (sufficient for testing):**
- 100,000 requests/day
- 10ms CPU per request
- 1GB KV storage
- 1,000 KV writes/day
- 100,000 KV reads/day

**Usage estimate:**
- Fetch data once/hour = 24 requests/day ✅
- Cache = 1 KV write + 1,000 reads ✅
- Total: $0/month ✅

**Paid (if needed):**
- $0.50 per million requests
- $0.50 per GB-month KV storage
- At 1M requests/month = $0.50/month (still cheap!)

## Troubleshooting

**Error: "Binance API error: 418"**
- Rate limit exceeded
- Wait 1 minute and try again
- Solution: Increase cache TTL

**Error: "KV storage not configured"**
- Create KV namespace: `wrangler kv:namespace create DATA_CACHE`
- Update `wrangler.toml` with the namespace ID
- Redeploy: `wrangler publish`

**Slow response:**
- First request is slow (fetches from Binance)
- Subsequent requests are fast (served from cache)
- Use `/cached` endpoint for instant access

## Next Steps

1. Deploy this Worker
2. Update `historical_data_fetcher.py` to use Worker URL
3. Run backtests with real data
4. Add more symbols as needed

## Alternative: Self-Hosted

Don't want to use Cloudflare? Deploy to:
- **Deno Deploy** (similar, also free tier)
- **Vercel Edge Functions** (free tier)
- **AWS Lambda** (free tier)
- **Your own server** (run anywhere)

The Worker code is standard JavaScript - works on any edge platform!
