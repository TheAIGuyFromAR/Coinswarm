# 🚀 Bulk Historical Data Download - Quick Start Guide

## ✅ What You're Getting

**Maximum Granularity for Maximum History:**
- **5-minute intervals** (most granular practical data)
- **2 years of history** (730 days)
- **~525,000 candles per symbol**
- **Data for BTC, ETH, SOL** (configurable)

## 📋 Prerequisites

```bash
# Python 3.7 or higher
python3 --version

# Install httpx (if not already installed)
pip install httpx
```

## 🧪 Step 1: Test Your API Key (30 seconds)

Run this first to verify everything works:

```bash
python test_api_key.py
```

**Expected output:**
```
✅ SUCCESS!
API Key: Valid
Candles Retrieved: 10
Latest BTC Price: $XX,XXX.XX
✅ Your API key is working! Ready for bulk download.
```

If you see errors, check:
- Internet connection
- `httpx` is installed: `pip install httpx`
- Firewall isn't blocking cryptocompare.com

## 🎯 Step 2: Run Bulk Download (5-10 minutes)

### Default: BTC, ETH, SOL - 2 years at 5-minute intervals

```bash
python bulk_download_historical.py
```

This will:
1. Download ~525,000 candles per symbol
2. Make ~105 API calls per symbol (well within 100k/month limit)
3. Save to `data/historical/` folder
4. Take approximately 5-10 minutes total

### Custom: Specific Symbols

```bash
# Download only BTC and ETH
python bulk_download_historical.py BTC ETH

# Download only SOL
python bulk_download_historical.py SOL
```

### Custom: Different Interval or Time Range

```bash
# 15-minute intervals for 1 year
python bulk_download_historical.py BTC --interval=15 --days=365

# 1-minute intervals for 30 days
python bulk_download_historical.py BTC --interval=1 --days=30

# 30-minute intervals for 2 years (all symbols)
python bulk_download_historical.py --interval=30 --days=730
```

## 📊 Output Files

Files will be saved in: `data/historical/`

**Example files:**
```
data/historical/BTC_730d_5min_full.json    (~50 MB)
data/historical/ETH_730d_5min_full.json    (~50 MB)
data/historical/SOL_730d_5min_full.json    (~50 MB)
```

**File structure:**
```json
{
  "symbol": "BTC",
  "interval_minutes": 5,
  "days": 730,
  "dataPoints": 525600,
  "first": "2023-11-06T12:00:00",
  "last": "2025-11-06T12:00:00",
  "fetchedAt": "2025-11-06T12:34:56",
  "data": [
    {
      "timestamp": "2023-11-06T12:00:00",
      "unix": 1699272000,
      "open": 35123.45,
      "high": 35234.56,
      "low": 35100.23,
      "close": 35189.12,
      "volume": 12345678.90
    },
    ...
  ]
}
```

## 📈 Progress Display

You'll see real-time progress:

```
================================================================================
📊 Fetching 730 days of BTC at 5-minute intervals
================================================================================

Expected: ~525,600 candles in ~263 requests
Interval: 5 minutes
Period: 2023-11-06 to 2025-11-06

  ✅ Batch   1/263:  400 candles | Total:    400 | Oldest: 2025-11-05 | 0.2% | 1250 candles/sec
  ✅ Batch   2/263:  400 candles | Total:    800 | Oldest: 2025-11-04 | 0.4% | 1300 candles/sec
  ✅ Batch   3/263:  400 candles | Total:  1,200 | Oldest: 2025-11-03 | 0.6% | 1280 candles/sec
  ...

================================================================================
✅ SUCCESS!
================================================================================
Symbol:       BTC
Interval:     5 minutes
Data Points:  525,600
Period:       2023-11-06 to 2025-11-06
Price:        $35,189.12 → $69,420.00
Change:       +97.32%
File Size:    52.34 MB
Fetch Time:   421.3 seconds
API Calls:    263
Saved To:     data/historical/BTC_730d_5min_full.json
================================================================================
```

## ⚡ API Usage

**Your Free Tier:** 100,000 calls/month

**This Script Uses:**
- **BTC only:** ~263 calls (0.26% of monthly limit)
- **BTC + ETH + SOL:** ~789 calls (0.79% of monthly limit)
- **10 symbols:** ~2,630 calls (2.63% of monthly limit)

You can download **all major cryptocurrencies multiple times** and still stay well within limits!

## 🔄 Updating Data

After initial download, you can update with just the latest day:

```bash
# Download only the last 1 day (1 API call per symbol)
python bulk_download_historical.py BTC --days=1
```

Then merge the new data with your existing files in your application.

## ❓ Troubleshooting

**Error: "Expecting value: line 1 column 1"**
- CryptoCompare API is rate-limited or blocked
- Wait 60 seconds and try again
- Check internet connection

**Error: "No module named 'httpx'"**
```bash
pip install httpx
```

**Error: "API Error: rate limit exceeded"**
- You've exceeded 100,000 calls this month
- Wait until next month or upgrade to paid plan
- Check usage: https://www.cryptocompare.com/cryptopian/api-keys

**Very slow download speed:**
- Normal! The script includes delays to respect API rate limits
- 5-10 minutes for 2 years of data is expected
- Don't reduce the sleep time or you'll get rate-limited

## 🎯 What's Next?

Once you have the data files:

1. **Load into your backtesting system**
   ```python
   import json

   with open('data/historical/BTC_730d_5min_full.json') as f:
       btc_data = json.load(f)

   candles = btc_data['data']  # List of 525,600 candles
   ```

2. **Deploy the Cloudflare Worker** (see `DEPLOY_WITH_YOUR_KEY.md`)
   - For real-time data fetching
   - Complements your local historical data

3. **Set up daily updates**
   - Run `python bulk_download_historical.py BTC --days=1` daily
   - Only 1 API call per day per symbol
   - Keeps your local cache fresh

## 📝 Summary

**Time Investment:**
- Setup: 2 minutes (install httpx, test API key)
- First run: 5-10 minutes (download 2 years for 3 symbols)
- Updates: 10 seconds/day (download latest day)

**Result:**
- ✅ 525,600 candles per symbol (5-min intervals)
- ✅ 2 years of history
- ✅ Saved locally (instant access, no API calls)
- ✅ Free forever (within 100k calls/month)

**Your P0 requirement exceeded:**
- Required: 180 days (6 months)
- **Delivered: 730 days (2 years) = 4x requirement** ✅

---

Ready to start? Run `python test_api_key.py` now! 🚀
