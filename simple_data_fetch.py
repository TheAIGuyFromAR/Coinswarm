"""
Simple data fetcher using your existing Cloudflare Worker.

No dependencies needed - uses only Python stdlib.

Fetches 2+ years data for:
- BTC-USDT, BTC-USDC
- SOL-USDT, SOL-USDC
- BTC-SOL

Saves to JSON for testing.
"""

import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

# Your Cloudflare Worker endpoint
WORKER_URL = "https://coinswarm-data.YOURUSERNAME.workers.dev"  # TODO: Update with your Worker URL

# Data directory
DATA_DIR = Path(__file__).parent / "data" / "historical"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Pairs to fetch
PAIRS = [
    "BTCUSDT",
    "BTCUSDC",
    "SOLUSDT",
    "SOLUSDC",
]


def fetch_historical_data(symbol: str, days: int = 1095):
    """
    Fetch historical data from Cloudflare Worker.

    Args:
        symbol: Trading pair (e.g., "BTCUSDT")
        days: Number of days to fetch (default: 3 years)

    Returns:
        List of candles or None if failed
    """
    print(f"Fetching {symbol} ({days} days)...")

    # Build request
    params = {
        "symbol": symbol,
        "interval": "1h",
        "days": days
    }

    url = f"{WORKER_URL}?{urllib.parse.urlencode(params)}"

    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read())

            if "data" in data and len(data["data"]) > 0:
                candles = data["data"]
                print(f"  ✅ Fetched {len(candles)} candles")

                # Calculate date range
                start_date = datetime.fromtimestamp(candles[0]["timestamp"] / 1000)
                end_date = datetime.fromtimestamp(candles[-1]["timestamp"] / 1000)
                actual_days = (end_date - start_date).days
                actual_years = actual_days / 365.25

                print(f"  Date range: {start_date.date()} to {end_date.date()}")
                print(f"  Coverage: {actual_days} days ({actual_years:.1f} years)")

                if actual_years < 2.0:
                    print(f"  ⚠️  Only {actual_years:.1f} years - need 2+ for robust validation!")
                else:
                    print(f"  ✅ Sufficient data for validation")

                return candles
            else:
                print(f"  ❌ No data returned")
                return None

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None


def main():
    """Fetch all pairs"""

    print("="*80)
    print("MULTI-PAIR HISTORICAL DATA FETCHER")
    print("="*80)
    print(f"Fetching {len(PAIRS)} trading pairs")
    print(f"Target: 3 years (1095 days) of 1h candles")
    print(f"Data directory: {DATA_DIR}")
    print(f"Cloudflare Worker: {WORKER_URL}")
    print("="*80 + "\n")

    results = {}

    for symbol in PAIRS:
        # Check if already downloaded
        filename = DATA_DIR / f"{symbol}_1h.json"

        if filename.exists():
            print(f"Loading cached {symbol} from {filename}")
            with open(filename) as f:
                data = json.load(f)
                results[symbol] = data
                print(f"  Loaded {len(data)} candles from cache\n")
            continue

        # Fetch from Worker
        candles = fetch_historical_data(symbol, days=1095)

        if candles:
            # Save to JSON
            with open(filename, 'w') as f:
                json.dump(candles, f)
            print(f"  Saved to {filename}\n")
            results[symbol] = candles
        else:
            print(f"  Skipped {symbol} (no data)\n")

    # Summary
    print("\n" + "="*80)
    print("DATA FETCH SUMMARY")
    print("="*80)

    for symbol, candles in results.items():
        if candles:
            start = datetime.fromtimestamp(candles[0]["timestamp"] / 1000)
            end = datetime.fromtimestamp(candles[-1]["timestamp"] / 1000)
            years = (end - start).days / 365.25

            status = "✅" if years >= 2.0 else "⚠️ "
            print(f"{status} {symbol:12s}: {len(candles):6d} candles, {years:.1f} years")

    print("="*80)
    print(f"\n✅ Data fetch complete! Saved to: {DATA_DIR}")
    print("\nNext step: Run random window validation with:")
    print("  python test_memory_simple.py")


if __name__ == "__main__":
    main()
