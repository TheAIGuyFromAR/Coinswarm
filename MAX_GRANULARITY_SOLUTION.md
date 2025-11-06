# Maximum Granularity for Maximum History

## 🎯 Goal: Most Granular Data, Going Back as Far as Possible

### 📊 What CryptoCompare Offers (with your API key)

| Interval | Candles/Request | Days/Request | Requests for 2 Years |
|----------|----------------|--------------|---------------------|
| **1 minute** | 2,000 | **1.4 days** | ~520 requests |
| **5 minutes** | 2,000 | **7 days** | ~105 requests |
| **15 minutes** | 2,000 | **21 days** | ~35 requests |
| **30 minutes** | 2,000 | **42 days** | ~18 requests |
| **1 hour** | 2,000 | **83 days** | ~9 requests |

**Your free tier:** 100,000 calls/month = Plenty for any of these!

## 🎯 Best Strategy

**Recommended: 5-minute intervals**
- ✅ Very granular (288 candles per day)
- ✅ ~105 requests for 2 years (well within limit)
- ✅ 525,600 data points for 2 years!
- ✅ Perfect for intraday strategies

**Alternative: 15-minute intervals**
- ✅ Still very granular (96 candles per day)
- ✅ Only ~35 requests for 2 years
- ✅ 175,200 data points for 2 years
- ✅ Good balance of granularity vs API calls

## 📦 Two Approaches

### Approach 1: Worker with Pagination (Best for Production)

**Worker fetches data in batches automatically**

### Approach 2: Python Script (Best for One-Time Bulk Download)

**Fetch all historical data once, save locally, use forever**

---

## 🚀 Approach 1: Worker with Pagination

I'll create a worker that:
1. Accepts start/end dates or "days back"
2. Automatically paginates through CryptoCompare
3. Returns all data in one response (or chunked)

**Example:**
```bash
# Get 2 years of 5-minute data
curl "https://swarm.bamn86.workers.dev/bulk?symbol=BTC&days=730&interval=5min"

# Returns: ~525,000 candles!
```

---

## 🚀 Approach 2: Python Bulk Downloader (RECOMMENDED)

**Better approach:** Download ALL historical data once, save to files, never fetch again!

### Python Script: Fetch 2+ Years of 5-Minute Data

```python
import asyncio
import httpx
import json
from datetime import datetime, timedelta
from pathlib import Path
import time

class BulkHistoricalFetcher:
    """Fetch maximum granular data for maximum history"""

    def __init__(self, api_key: str, cache_dir: str = "data/historical"):
        self.api_key = api_key
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = "https://min-api.cryptocompare.com/data/v2/histominute"

    async def fetch_batch(self, symbol: str, to_timestamp: int, limit: int = 2000):
        """Fetch one batch of minute data"""
        url = f"{self.base_url}?fsym={symbol}&tsym=USD&limit={limit}&toTs={to_timestamp}&api_key={self.api_key}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30)
            data = response.json()

            if data.get('Response') != 'Success':
                raise Exception(f"API Error: {data.get('Message')}")

            candles = data.get('Data', {}).get('Data', [])
            return candles

    async def fetch_all_history(
        self,
        symbol: str,
        interval_minutes: int = 5,
        max_days: int = 730
    ):
        """
        Fetch ALL historical data with maximum granularity

        Args:
            symbol: BTC, ETH, SOL, etc.
            interval_minutes: 1, 5, 15, 30, 60 (5 recommended)
            max_days: How far back to go (730 = 2 years)
        """
        print(f"\n{'='*80}")
        print(f"📊 Fetching {max_days} days of {symbol} at {interval_minutes}-minute intervals")
        print(f"{'='*80}\n")

        all_candles = []
        now = int(time.time())
        target_start = now - (max_days * 24 * 60 * 60)

        current_to = now
        batch_num = 0
        candles_per_request = 2000

        # Calculate expected totals
        expected_candles = (max_days * 24 * 60) // interval_minutes
        expected_requests = (expected_candles // candles_per_request) + 1

        print(f"Expected: ~{expected_candles:,} candles in ~{expected_requests} requests")
        print(f"Interval: {interval_minutes} minutes\n")

        while current_to > target_start:
            batch_num += 1

            try:
                # Fetch batch
                candles = await self.fetch_batch(symbol, current_to, candles_per_request)

                if not candles:
                    print(f"  Batch {batch_num}: No more data available")
                    break

                # Process candles
                valid_candles = []
                for candle in candles:
                    # Filter by interval (e.g., only keep every 5th minute)
                    minute = datetime.fromtimestamp(candle['time']).minute
                    if minute % interval_minutes == 0:
                        valid_candles.append({
                            'timestamp': datetime.fromtimestamp(candle['time']).isoformat(),
                            'unix': candle['time'],
                            'open': candle['open'],
                            'high': candle['high'],
                            'low': candle['low'],
                            'close': candle['close'],
                            'volume': candle['volumeto']
                        })

                all_candles.extend(valid_candles)

                # Update progress
                oldest_time = datetime.fromtimestamp(candles[0]['time'])
                progress_pct = ((now - candles[0]['time']) / (now - target_start)) * 100

                print(f"  ✅ Batch {batch_num:3d}/{expected_requests}: "
                      f"{len(valid_candles):4d} candles | "
                      f"Total: {len(all_candles):6,} | "
                      f"Oldest: {oldest_time.strftime('%Y-%m-%d')} | "
                      f"Progress: {progress_pct:.1f}%")

                # Move to next batch
                current_to = candles[0]['time'] - 1

                # Check if we've gone back far enough
                if candles[0]['time'] <= target_start:
                    print(f"\n  🎯 Reached target date!")
                    break

                # Rate limit (be nice to API)
                await asyncio.sleep(0.2)  # 5 requests/sec = well within limits

            except Exception as e:
                print(f"  ❌ Batch {batch_num} error: {e}")
                break

        # Sort by timestamp (oldest first)
        all_candles.sort(key=lambda x: x['unix'])

        # Save to file
        filename = f"{symbol}_{max_days}d_{interval_minutes}min_full.json"
        filepath = self.cache_dir / filename

        result = {
            'symbol': symbol,
            'interval_minutes': interval_minutes,
            'days': max_days,
            'dataPoints': len(all_candles),
            'first': all_candles[0]['timestamp'] if all_candles else None,
            'last': all_candles[-1]['timestamp'] if all_candles else None,
            'fetchedAt': datetime.now().isoformat(),
            'data': all_candles
        }

        with open(filepath, 'w') as f:
            json.dump(result, f, indent=2)

        # Calculate stats
        if all_candles:
            first_price = all_candles[0]['close']
            last_price = all_candles[-1]['close']
            price_change = ((last_price - first_price) / first_price) * 100

            print(f"\n{'='*80}")
            print(f"✅ SUCCESS!")
            print(f"{'='*80}")
            print(f"Symbol:       {symbol}")
            print(f"Interval:     {interval_minutes} minutes")
            print(f"Data Points:  {len(all_candles):,}")
            print(f"Period:       {all_candles[0]['timestamp'][:10]} to {all_candles[-1]['timestamp'][:10]}")
            print(f"Price:        ${first_price:,.2f} → ${last_price:,.2f}")
            print(f"Change:       {price_change:+.2f}%")
            print(f"File Size:    {filepath.stat().st_size / (1024*1024):.2f} MB")
            print(f"Saved To:     {filepath}")
            print(f"{'='*80}\n")

        return result


async def download_max_granularity():
    """Download maximum granular data for all symbols"""

    api_key = "da672b9999120841fbd4427fa4550b83b5f23e017c5c03ff33bafe09064abe83"
    fetcher = BulkHistoricalFetcher(api_key)

    symbols = ['BTC', 'ETH', 'SOL']

    # Strategy: 5-minute intervals for 2 years
    # This gives us ~525,000 candles per symbol!

    for symbol in symbols:
        print(f"\n{'#'*80}")
        print(f"# {symbol}")
        print(f"{'#'*80}\n")

        try:
            await fetcher.fetch_all_history(
                symbol=symbol,
                interval_minutes=5,  # 5-minute candles
                max_days=730         # 2 years
            )

            # Small delay between symbols
            await asyncio.sleep(2)

        except Exception as e:
            print(f"❌ Failed to fetch {symbol}: {e}\n")

    print("\n" + "="*80)
    print("🎉 ALL DOWNLOADS COMPLETE!")
    print("="*80)
    print("\nYou now have:")
    print("  • 2 years of 5-minute data")
    print("  • ~525,000 candles per symbol")
    print("  • Saved in: data/historical/")
    print("\nReady for backtesting! 🚀\n")


if __name__ == "__main__":
    # Run the bulk download
    asyncio.run(download_max_granularity())
```

### Save this as: `bulk_download_historical.py`

### Run it:
```bash
python bulk_download_historical.py
```

**What it does:**
1. Fetches 2 years of 5-minute data for BTC, ETH, SOL
2. Makes ~105 API calls per symbol (well within free limit)
3. Saves to JSON files: `BTC_730d_5min_full.json` (~50MB each)
4. **You only need to run this ONCE**
5. Then use the files for all your backtesting!

**Result:**
- ✅ **525,600 candles per symbol** (2 years × 365 days × 24 hours × 12 5-min intervals)
- ✅ **Minute-level granularity** (every 5 minutes)
- ✅ **Goes back 2+ years**
- ✅ **Saved locally** (no more API calls needed)

---

## 📊 Data Volume Estimates

| Interval | 2 Years | File Size | API Calls |
|----------|---------|-----------|-----------|
| **5 min** | **525,600** | **~50 MB** | **~105** |
| 15 min | 175,200 | ~17 MB | ~35 |
| 30 min | 87,600 | ~8 MB | ~18 |
| 1 hour | 17,520 | ~2 MB | ~9 |

**Recommendation:** Use **5-minute intervals** for maximum useful granularity!

---

## 🔄 Update Strategy

After initial bulk download, update daily:

```python
# Fetch only last 24 hours of new data
async def update_latest():
    fetcher = BulkHistoricalFetcher(api_key)

    # Load existing file
    with open('data/historical/BTC_730d_5min_full.json') as f:
        existing = json.load(f)

    # Fetch last 24 hours (only 1 API call!)
    new_data = await fetcher.fetch_all_history('BTC', 5, 1)

    # Append new candles
    existing['data'].extend(new_data['data'])

    # Remove old data (keep rolling 2-year window)
    existing['data'] = existing['data'][-525600:]  # Keep last 2 years

    # Save
    with open('data/historical/BTC_730d_5min_full.json', 'w') as f:
        json.dump(existing, f, indent=2)

    print("✅ Updated with latest 24 hours")

# Run daily
asyncio.run(update_latest())
```

---

## ✅ Summary

**Best Solution for Maximum Granularity:**

1. **Run bulk download script ONCE**
   - Fetches 2 years of 5-minute data
   - ~525,000 candles per symbol
   - ~105 API calls per symbol
   - Takes ~5-10 minutes

2. **Save to local files**
   - `BTC_730d_5min_full.json`
   - `ETH_730d_5min_full.json`
   - `SOL_730d_5min_full.json`

3. **Use files for backtesting**
   - Load from disk (instant)
   - No more API calls needed
   - Maximum granularity achieved!

4. **Update daily (optional)**
   - Fetch last 24 hours only
   - 1 API call per day per symbol
   - Keep rolling 2-year window

**Result:**
- ✅ Most granular data (5-minute intervals)
- ✅ Maximum history (2+ years)
- ✅ Saved locally (fast access)
- ✅ One-time download (no repeated API calls)

**Ready to download?** Save the script and run it! 🚀
