# Minute-Level Data Solution

## 🎯 Requirement: 5min, 15min, 30min Intervals

**Problem:** Need minute-level granularity for backtesting
- 5 minute candles
- 15 minute candles
- 30 minute candles

**Solution:** Use Kraken API via Cloudflare Worker

## 📊 Available Intervals & Data Limits

| Interval | Candles/Request | Max History | Use Case |
|----------|----------------|-------------|----------|
| **5 min** | 720 | **2.5 days** | High-frequency testing |
| **15 min** | 720 | **7.5 days** | Intraday strategies |
| **30 min** | 720 | **15 days** | Short-term strategies |
| **1 hour** | 720 | **30 days** | Medium-term strategies |
| 4 hour | 720 | 120 days | Long-term patterns |
| Daily | 720 | **2 years** | Historical analysis |

## 🚀 Deploy Instructions

### Step 1: Deploy Worker

1. Go to: https://dash.cloudflare.com/ → Workers & Pages
2. Create new worker: `minute-data`
3. Copy code from: `cloudflare-workers/minute-data-worker.js`
4. Save and Deploy

### Step 2: Test Endpoints

```bash
# 5 minute intervals (2.5 days)
curl "https://minute-data.YOUR-SUBDOMAIN.workers.dev/data?symbol=BTC&interval=5m&limit=720"

# 15 minute intervals (7.5 days)
curl "https://minute-data.YOUR-SUBDOMAIN.workers.dev/data?symbol=BTC&interval=15m&limit=720"

# 30 minute intervals (15 days)
curl "https://minute-data.YOUR-SUBDOMAIN.workers.dev/data?symbol=BTC&interval=30m&limit=720"
```

**Expected Response:**
```json
{
  "success": true,
  "symbol": "BTC",
  "interval": "5m",
  "dataPoints": 720,
  "durationHours": "60.00",
  "firstPrice": 103500,
  "lastPrice": 104200,
  "priceChange": "+0.68%",
  "data": [...]
}
```

## 📈 Getting More History (Pagination)

Since Kraken limits to 720 candles, fetch multiple batches:

```bash
# Step 1: Get most recent 720 candles
curl "https://minute-data.YOUR-SUBDOMAIN.workers.dev/data?symbol=BTC&interval=5m&limit=720" > batch1.json

# Step 2: Get next 720 candles (use 'nextSince' from previous response)
curl "https://minute-data.YOUR-SUBDOMAIN.workers.dev/data?symbol=BTC&interval=5m&limit=720&since=TIMESTAMP" > batch2.json

# Repeat for more history...
```

## 🎯 Practical Limits

**For P0 Requirement (6 months = 180 days):**

| Interval | Total Candles | Requests Needed |
|----------|--------------|-----------------|
| 5 min | 51,840 | 72 requests |
| 15 min | 17,280 | 24 requests |
| 30 min | 8,640 | 12 requests |
| 1 hour | 4,320 | 6 requests |

**Recommendation:** Use **30min or 1h intervals** for 180 days
- Much fewer API calls
- Still high granularity
- Reasonable download size

## 💡 Alternative: Download Once, Store Locally

**Better approach for backtesting:**

1. **One-time fetch:** Get 6 months of 30min data (12 requests)
2. **Save to files:** Store in `data/historical/`
3. **Use for backtesting:** Load from disk (fast!)
4. **Update daily:** Fetch only latest candles

**Script to fetch 6 months of 30min data:**

```python
import asyncio
import httpx
import json
from datetime import datetime, timedelta

async def fetch_historical_minutes(symbol, interval, months):
    """Fetch multiple months of minute data"""

    worker_url = "https://minute-data.YOUR-SUBDOMAIN.workers.dev"
    all_data = []

    # Calculate how many requests needed
    candles_per_interval = {
        '5m': 720,   # 2.5 days per request
        '15m': 720,  # 7.5 days per request
        '30m': 720,  # 15 days per request
        '1h': 720    # 30 days per request
    }

    days_per_request = {
        '5m': 2.5,
        '15m': 7.5,
        '30m': 15,
        '1h': 30
    }

    total_days = months * 30
    requests_needed = int(total_days / days_per_request[interval]) + 1

    print(f"Fetching {total_days} days of {interval} data...")
    print(f"Requests needed: {requests_needed}")

    since = None

    async with httpx.AsyncClient() as client:
        for i in range(requests_needed):
            url = f"{worker_url}/data?symbol={symbol}&interval={interval}&limit=720"
            if since:
                url += f"&since={since}"

            print(f"  Batch {i+1}/{requests_needed}...")

            response = await client.get(url, timeout=30)
            data = response.json()

            if data.get('success'):
                all_data.extend(data['data'])
                since = data.get('nextSince')
                print(f"    ✅ {len(data['data'])} candles")
            else:
                print(f"    ❌ Error: {data.get('error')}")
                break

            # Rate limit
            await asyncio.sleep(1)

    # Save to file
    filename = f"data/historical/{symbol}_{months}mo_{interval}_kraken.json"
    with open(filename, 'w') as f:
        json.dump({
            'symbol': symbol,
            'interval': interval,
            'months': months,
            'dataPoints': len(all_data),
            'data': all_data
        }, f, indent=2)

    print(f"\n✅ Saved {len(all_data)} candles to {filename}")
    return all_data

# Usage
asyncio.run(fetch_historical_minutes('BTC', '30m', 6))  # 6 months of 30min data
```

## 📊 Summary

**For minute-level data:**
- ✅ Deploy `minute-data-worker.js` to Cloudflare
- ✅ Supports 5m, 15m, 30m, 1h intervals
- ✅ Free API (Kraken public endpoint)
- ✅ Up to 720 candles per request
- ✅ Use pagination for longer periods

**For P0 requirement (180 days):**
- **Recommended:** 30min or 1h intervals
- **Fetch once:** Store locally for backtesting
- **Update daily:** Only fetch latest candles

**Deploy now:** `cloudflare-workers/minute-data-worker.js` ✅
