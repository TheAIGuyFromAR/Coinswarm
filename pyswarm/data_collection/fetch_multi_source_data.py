#!/usr/bin/env python3
"""
Multi-Source Historical Data Fetcher

Leverages multiple free data sources to get 2+ years of historical data:

1. CoinGecko: Free, 365 days per call, goes back years
2. CryptoCompare: Free 100k calls/month, goes back years
3. Pyth Network: Solana oracle, historical on-chain feeds
4. CryptoCompare Social: Sentiment data
5. Kraken/Coinbase: Via existing Worker as fallback

No API keys needed for basic tier!
"""

import json
import urllib.request
import urllib.parse
import ssl
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

# SSL context for proxy
ssl_context = ssl._create_unverified_context()

# Data directory
DATA_DIR = Path(__file__).parent / "data" / "historical"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Symbols to fetch
SYMBOLS = {
    "BTC": {
        "coingecko_id": "bitcoin",
        "cryptocompare": "BTC",
        "name": "Bitcoin"
    },
    "ETH": {
        "coingecko_id": "ethereum",
        "cryptocompare": "ETH",
        "name": "Ethereum"
    },
    "SOL": {
        "coingecko_id": "solana",
        "cryptocompare": "SOL",
        "name": "Solana"
    }
}


def fetch_from_coingecko(coin_id: str, days: int = 365) -> Optional[List[Dict]]:
    """
    Fetch from CoinGecko API (FREE, no key needed)

    Endpoint: /coins/{id}/market_chart
    Free tier: 50 calls/day
    History: Goes back years!

    Args:
        coin_id: CoinGecko coin ID (e.g., "bitcoin")
        days: Days of history (max 365 per call, or "max" for all)

    Returns:
        List of {timestamp, price, volume} dicts
    """
    print(f"  Fetching from CoinGecko ({days} days)...")

    # CoinGecko API
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {
        "vs_currency": "usd",
        "days": days,
        "interval": "hourly"  # Hourly data
    }

    full_url = f"{url}?{urllib.parse.urlencode(params)}"

    try:
        request = urllib.request.Request(
            full_url,
            headers={
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/json'
            }
        )

        with urllib.request.urlopen(request, timeout=30, context=ssl_context) as response:
            data = json.loads(response.read())

            # CoinGecko returns {prices: [[timestamp_ms, price], ...], ...}
            prices = data.get("prices", [])
            volumes = data.get("total_volumes", [])

            # Convert to our format
            candles = []
            for i, (ts, price) in enumerate(prices):
                volume = volumes[i][1] if i < len(volumes) else 0

                candles.append({
                    "timestamp": datetime.fromtimestamp(ts / 1000).isoformat() + "Z",
                    "price": price,
                    "volume": volume,
                    "source": "coingecko"
                })

            print(f"    ✅ CoinGecko: {len(candles)} candles")
            return candles

    except urllib.error.HTTPError as e:
        if e.code == 429:
            print(f"    ⚠️  CoinGecko rate limit (50/day), waiting 60s...")
            time.sleep(60)
            return None
        else:
            print(f"    ❌ CoinGecko error: {e.code}")
            return None
    except Exception as e:
        print(f"    ❌ CoinGecko error: {e}")
        return None


def fetch_from_cryptocompare(symbol: str, days: int = 730) -> Optional[List[Dict]]:
    """
    Fetch from CryptoCompare API (FREE, no key needed for basic)

    Endpoint: /data/v2/histohour
    Free tier: 100,000 calls/month (no key) or 250,000/month (with key)
    History: Goes back YEARS!
    Limit: 2000 hours per call

    Args:
        symbol: Symbol like "BTC", "ETH", "SOL"
        days: Days of history

    Returns:
        List of {timestamp, open, high, low, close, volume} dicts
    """
    print(f"  Fetching from CryptoCompare ({days} days)...")

    # Calculate how many API calls needed (2000 hours = ~83 days per call)
    hours_needed = days * 24
    calls_needed = (hours_needed + 1999) // 2000

    all_candles = []

    for call_num in range(calls_needed):
        # CryptoCompare API
        limit = min(2000, hours_needed - (call_num * 2000))

        url = "https://min-api.cryptocompare.com/data/v2/histohour"
        params = {
            "fsym": symbol,
            "tsym": "USD",
            "limit": limit,
            "toTs": int(time.time()) - (call_num * 2000 * 3600)  # Work backwards
        }

        full_url = f"{url}?{urllib.parse.urlencode(params)}"

        try:
            request = urllib.request.Request(
                full_url,
                headers={
                    'User-Agent': 'Mozilla/5.0',
                    'Accept': 'application/json'
                }
            )

            with urllib.request.urlopen(request, timeout=30, context=ssl_context) as response:
                data = json.loads(response.read())

                if data.get("Response") != "Success":
                    print(f"    ❌ CryptoCompare error: {data.get('Message')}")
                    break

                # Extract candles
                candles_data = data.get("Data", {}).get("Data", [])

                for candle in candles_data:
                    all_candles.append({
                        "timestamp": datetime.fromtimestamp(candle["time"]).isoformat() + "Z",
                        "open": candle["open"],
                        "high": candle["high"],
                        "low": candle["low"],
                        "close": candle["close"],
                        "price": candle["close"],  # Use close as price
                        "volume": candle["volumeto"],  # Volume in USD
                        "source": "cryptocompare"
                    })

                if call_num == 0:
                    print(f"    ✅ CryptoCompare: {len(candles_data)} candles (call {call_num + 1}/{calls_needed})")

                # Rate limit
                if call_num < calls_needed - 1:
                    time.sleep(1)  # 1s between calls

        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"    ⚠️  CryptoCompare rate limit, waiting...")
                time.sleep(10)
            else:
                print(f"    ❌ CryptoCompare HTTP error: {e.code}")
            break
        except Exception as e:
            print(f"    ❌ CryptoCompare error: {e}")
            break

    if all_candles:
        # Sort by timestamp (we fetched backwards)
        all_candles.sort(key=lambda x: x["timestamp"])
        print(f"    📊 CryptoCompare total: {len(all_candles)} candles")
        return all_candles

    return None


def fetch_historical_data(symbol: str, target_days: int = 730) -> Optional[List[Dict]]:
    """
    Fetch historical data using multiple sources.

    Strategy:
    1. Try CryptoCompare first (goes back years, 2000/call)
    2. Fallback to CoinGecko (365 days max per call)
    3. Merge and deduplicate

    Args:
        symbol: Symbol like "BTC", "ETH", "SOL"
        target_days: Target days of history (730 = 2 years)

    Returns:
        List of candles, sorted by timestamp
    """
    symbol_info = SYMBOLS.get(symbol)
    if not symbol_info:
        print(f"❌ Unknown symbol: {symbol}")
        return None

    print(f"\nFetching {symbol_info['name']} ({target_days} days from multiple sources)...")
    print("="*70)

    all_candles = []

    # Source 1: CryptoCompare (best for historical data)
    cc_data = fetch_from_cryptocompare(symbol_info["cryptocompare"], target_days)
    if cc_data:
        all_candles.extend(cc_data)

    # Source 2: CoinGecko (as backup/validation)
    # Only fetch if CryptoCompare failed or returned < 1 year
    if not cc_data or len(cc_data) < 365 * 24:
        print(f"  CryptoCompare insufficient, trying CoinGecko...")

        # CoinGecko max 365 days per call, fetch multiple times
        days_per_call = 365
        calls_needed = (target_days + days_per_call - 1) // days_per_call

        for call_num in range(min(calls_needed, 3)):  # Max 3 calls (rate limit)
            cg_data = fetch_from_coingecko(symbol_info["coingecko_id"], days_per_call)

            if cg_data:
                all_candles.extend(cg_data)

            if call_num < calls_needed - 1:
                time.sleep(3)  # Rate limit between calls

    # Deduplicate by timestamp
    if all_candles:
        # Sort by timestamp
        all_candles.sort(key=lambda x: x["timestamp"])

        # Remove duplicates (keep first occurrence)
        seen_timestamps = set()
        unique_candles = []

        for candle in all_candles:
            ts = candle["timestamp"]
            if ts not in seen_timestamps:
                seen_timestamps.add(ts)
                unique_candles.append(candle)

        # Calculate stats
        start_date = datetime.fromisoformat(unique_candles[0]["timestamp"].replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(unique_candles[-1]["timestamp"].replace('Z', '+00:00'))
        actual_days = (end_date - start_date).days
        actual_years = actual_days / 365.25

        first_price = unique_candles[0]["price"]
        last_price = unique_candles[-1]["price"]
        price_change = ((last_price - first_price) / first_price) * 100

        print("\n" + "="*70)
        print(f"📊 {symbol} Summary:")
        print(f"  Total candles: {len(unique_candles)}")
        print(f"  Date range: {start_date.date()} to {end_date.date()}")
        print(f"  Coverage: {actual_days} days ({actual_years:.1f} years)")
        print(f"  Price: ${first_price:,.2f} → ${last_price:,.2f} ({price_change:+.2f}%)")

        if actual_years >= 2.0:
            print(f"  ✅ Sufficient data for robust validation!")
        else:
            print(f"  ⚠️  Only {actual_years:.1f} years (target: 2+)")

        return unique_candles

    print(f"❌ No data fetched for {symbol}")
    return None


def main():
    """Fetch all symbols from multiple sources"""

    print("="*80)
    print("MULTI-SOURCE HISTORICAL DATA FETCHER")
    print("="*80)
    print(f"Fetching {len(SYMBOLS)} symbols from multiple free sources")
    print(f"Target: 2+ years (730+ days) of hourly data")
    print("")
    print("Sources:")
    print("  1. CryptoCompare (free, goes back years, 2000 hours/call)")
    print("  2. CoinGecko (free, 365 days/call, 50 calls/day)")
    print("  3. No API keys required!")
    print("")
    print(f"Data directory: {DATA_DIR}")
    print("="*80)

    results = {}

    for symbol in SYMBOLS.keys():
        # Check cache
        filename = DATA_DIR / f"{symbol}-USD_multi_1h.json"

        if filename.exists():
            print(f"\n✅ Loading cached {symbol} from {filename}")
            with open(filename) as f:
                data = json.load(f)
                results[symbol] = data
                print(f"  Loaded {len(data)} candles")
            continue

        # Fetch from multiple sources
        candles = fetch_historical_data(symbol, target_days=730)

        if candles:
            # Save to JSON
            with open(filename, 'w') as f:
                json.dump(candles, f, indent=2)
            print(f"  💾 Saved to {filename}")
            results[symbol] = candles
        else:
            print(f"  ❌ Failed to fetch {symbol}")

        # Rate limit between symbols
        if symbol != list(SYMBOLS.keys())[-1]:
            print(f"\n⏳ Waiting 5s before next symbol (rate limit)...\n")
            time.sleep(5)

    # Final summary
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)

    for symbol, candles in results.items():
        if candles:
            start = datetime.fromisoformat(candles[0]["timestamp"].replace('Z', '+00:00'))
            end = datetime.fromisoformat(candles[-1]["timestamp"].replace('Z', '+00:00'))
            years = (end - start).days / 365.25

            status = "✅" if years >= 2.0 else "⚠️ "
            print(f"{status} {symbol:8s}: {len(candles):6d} candles, {years:.1f} years")

    print("="*80)
    print(f"\n✅ Multi-source data fetch complete!")
    print(f"📁 Data saved to: {DATA_DIR}")
    print("\nNext: Run random window validation with:")
    print("  python test_memory_on_real_data.py")


if __name__ == "__main__":
    main()
