"""
Simple data fetcher using Cloudflare Worker with multi-source support.

No dependencies needed - uses only Python stdlib.

Fetches 2+ years data from multiple sources:
- CryptoCompare (2000 hours/call, goes back years)
- CoinGecko (365 days/call, goes back years)
- Kraken + Coinbase (backup)

Supports:
- BTC, SOL, ETH, and more
- 2+ years historical data
- Hourly candles

Saves to JSON for testing.
"""

import json
import urllib.request
import urllib.parse
import ssl
import time
from datetime import datetime, timedelta
from pathlib import Path

# Your Cloudflare Worker endpoint - Using original working Worker
# Multi-source Worker deployed but external APIs blocked/timing out
WORKER_URL = "https://coinswarm.bamn86.workers.dev"

# Use original endpoint (multi-source has external API issues)
USE_MULTI_SOURCE = False  # Using original /price for now (30 days)

# Data directory
DATA_DIR = Path(__file__).parent / "data" / "historical"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Symbols to fetch - Worker API uses base symbols (BTC, SOL, ETH)
# Worker automatically aggregates from multiple sources
SYMBOLS = ["BTC", "SOL", "ETH"]

# SSL context that skips cert verification (needed for proxy)
ssl_context = ssl._create_unverified_context()

# Original Worker: 365 days max
# Multi-source Worker: 730+ days (2+ years)
MAX_DAYS_PER_REQUEST = 730 if USE_MULTI_SOURCE else 365


def fetch_with_retry(symbol: str, days: int, max_retries: int = 5) -> dict:
    """
    Fetch data with exponential backoff retry for 503 errors.

    Args:
        symbol: Base symbol
        days: Days to fetch (365 for /price, 730+ for /multi-price)
        max_retries: Maximum retry attempts

    Returns:
        API response dict
    """
    params = {
        "symbol": symbol,
        "days": min(days, MAX_DAYS_PER_REQUEST),
        "aggregate": "true"
    }

    # Use multi-source endpoint if enabled (requires enhanced Worker deployed)
    endpoint = "/multi-price" if USE_MULTI_SOURCE else "/price"
    url = f"{WORKER_URL}{endpoint}?{urllib.parse.urlencode(params)}"

    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(url, timeout=60, context=ssl_context) as response:
                return json.loads(response.read())

        except urllib.error.HTTPError as e:
            if e.code == 503:
                # Service unavailable - exponential backoff
                wait_time = 2 ** attempt  # 1s, 2s, 4s, 8s, 16s
                print(f"  ⚠️  503 error, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait_time)
            else:
                raise  # Other HTTP errors, don't retry

        except Exception as e:
            # Non-HTTP errors
            print(f"  ❌ Error: {e}")
            return {"success": False, "error": str(e)}

    # All retries exhausted
    return {"success": False, "error": "Max retries reached (503 errors)"}


def fetch_historical_data(symbol: str, target_days: int = 730):
    """
    Fetch historical data from Cloudflare Worker.

    Worker limit: 365 days per request. This function fetches multiple
    chunks if needed to reach target_days.

    Args:
        symbol: Base symbol (e.g., "BTC", "SOL", "ETH")
        target_days: Total days to fetch (will fetch in 365-day chunks)

    Returns:
        List of candles or None if failed
    """
    print(f"Fetching {symbol} ({target_days} days total)...")

    # Calculate how many chunks we need
    num_chunks = (target_days + MAX_DAYS_PER_REQUEST - 1) // MAX_DAYS_PER_REQUEST
    all_candles = []

    for chunk in range(num_chunks):
        days_this_chunk = min(MAX_DAYS_PER_REQUEST, target_days - (chunk * MAX_DAYS_PER_REQUEST))

        if chunk > 0:
            print(f"  Fetching chunk {chunk + 1}/{num_chunks} ({days_this_chunk} days)...")
            time.sleep(1)  # Rate limit between chunks

        data = fetch_with_retry(symbol, days_this_chunk)

        if data.get("success") and "data" in data:
            candles = data["data"]
            all_candles.extend(candles)

            if chunk == 0:
                print(f"  ✅ Chunk 1: {len(candles)} candles")
                print(f"  Providers: {', '.join(data.get('providersUsed', []))}")
        else:
            error = data.get("error", "Unknown error")
            print(f"  ❌ Chunk {chunk + 1} failed: {error}")
            if chunk == 0:
                return None  # First chunk failed, abort
            else:
                break  # Later chunks failed, return what we have

    # Summary
    if all_candles:
        start_date = datetime.fromisoformat(all_candles[0]["timestamp"].replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(all_candles[-1]["timestamp"].replace('Z', '+00:00'))
        actual_days = (end_date - start_date).days
        actual_years = actual_days / 365.25

        print(f"  📊 Total: {len(all_candles)} candles across {actual_days} days ({actual_years:.1f} years)")
        print(f"  Date range: {start_date.date()} to {end_date.date()}")

        # Get first and last prices from chunks
        first_price = all_candles[0]["price"]
        last_price = all_candles[-1]["price"]
        price_change = ((last_price - first_price) / first_price) * 100

        print(f"  Price: ${first_price:,.2f} → ${last_price:,.2f} ({price_change:+.2f}%)")

        if actual_years < 2.0:
            print(f"  ⚠️  Only {actual_years:.1f} years - need 2+ for robust validation!")
        else:
            print(f"  ✅ Sufficient data for validation")

        return all_candles
    else:
        return None


def main():
    """Fetch all symbols"""

    print("="*80)
    print("MULTI-ASSET HISTORICAL DATA FETCHER")
    print("="*80)
    print(f"Fetching {len(SYMBOLS)} symbols")
    print(f"Target: 2+ years (730+ days) of 1h candles")
    print(f"Data directory: {DATA_DIR}")
    print(f"Cloudflare Worker: {WORKER_URL}")

    if USE_MULTI_SOURCE:
        print(f"Mode: Multi-source (/multi-price)")
        print(f"  Sources: CryptoCompare, CoinGecko, Kraken, Coinbase")
        print(f"  Limit: 730+ days per request (2+ years)")
    else:
        print(f"Mode: Original (/price)")
        print(f"  Sources: Kraken, Coinbase only")
        print(f"  Limit: 365 days/request, will fetch multiple chunks")

    print("="*80 + "\n")

    results = {}

    for symbol in SYMBOLS:
        # Check if already downloaded
        filename = DATA_DIR / f"{symbol}-USD_1h.json"

        if filename.exists():
            print(f"Loading cached {symbol} from {filename}")
            with open(filename) as f:
                data = json.load(f)
                results[symbol] = data
                print(f"  Loaded {len(data)} candles from cache\n")
            continue

        # Fetch from Worker (target 2 years = 730 days)
        candles = fetch_historical_data(symbol, target_days=730)

        if candles:
            # Save to JSON
            with open(filename, 'w') as f:
                json.dump(candles, f)
            print(f"  Saved to {filename}\n")
            results[symbol] = candles
        else:
            print(f"  Skipped {symbol} (no data)\n")

        # Rate limit between symbols
        if symbol != SYMBOLS[-1]:  # Don't sleep after last one
            time.sleep(2)

    # Summary
    print("\n" + "="*80)
    print("DATA FETCH SUMMARY")
    print("="*80)

    for symbol, candles in results.items():
        if candles:
            # Parse ISO timestamps
            start = datetime.fromisoformat(candles[0]["timestamp"].replace('Z', '+00:00'))
            end = datetime.fromisoformat(candles[-1]["timestamp"].replace('Z', '+00:00'))
            years = (end - start).days / 365.25

            status = "✅" if years >= 2.0 else "⚠️ "
            print(f"{status} {symbol:12s}: {len(candles):6d} candles, {years:.1f} years")

    print("="*80)
    print(f"\n✅ Data fetch complete! Saved to: {DATA_DIR}")
    print("\nNext step: Run random window validation with:")
    print("  python test_memory_on_real_data.py")


if __name__ == "__main__":
    main()
