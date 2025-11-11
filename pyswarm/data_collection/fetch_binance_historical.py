#!/usr/bin/env python3
"""
Binance Paginated Historical Data Fetcher

Fetches 6+ months to 2+ years of data using Binance's public API
with pagination to overcome the 1000 candle limit.

P0 Requirement: Get 6+ months of data
"""

import asyncio
import httpx
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
import time


class BinancePaginatedFetcher:
    """Fetches historical data from Binance with pagination"""

    def __init__(self, cache_dir: str = "data/historical"):
        self.base_url = "https://api.binance.com/api/v3/klines"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = 30.0

    async def fetch_paginated(
        self,
        symbol: str,
        interval: str,
        days: int
    ) -> List[Dict]:
        """
        Fetch data with pagination to get 6+ months

        Args:
            symbol: BTCUSDT, ETHUSDT, SOLUSDT
            interval: 1h (hourly)
            days: Number of days to fetch

        Returns:
            List of candles
        """
        print(f"\n📊 Fetching {symbol} from Binance for {days} days...")

        all_candles = []
        now_ms = int(time.time() * 1000)
        start_ms = now_ms - (days * 24 * 60 * 60 * 1000)

        current_start = start_ms
        attempts = 0
        max_attempts = (days // 42) + 10  # ~42 days per 1000 hourly candles + buffer

        print(f"  Target period: {datetime.fromtimestamp(start_ms/1000).isoformat()} to {datetime.fromtimestamp(now_ms/1000).isoformat()}")
        print(f"  Max attempts: {max_attempts}")

        while len(all_candles) < days * 24 and attempts < max_attempts:
            attempts += 1

            params = {
                "symbol": symbol,
                "interval": interval,
                "startTime": current_start,
                "endTime": now_ms,
                "limit": 1000
            }

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        self.base_url,
                        params=params,
                        timeout=self.timeout
                    )

                    if response.status_code != 200:
                        print(f"  ❌ Binance HTTP {response.status_code}")
                        break

                    candles = response.json()

                    if not candles or len(candles) == 0:
                        print(f"  ℹ️  No more candles available")
                        break

                    # Convert to our format
                    for candle in candles:
                        all_candles.append({
                            "timestamp": datetime.fromtimestamp(candle[0] / 1000).isoformat(),
                            "open": float(candle[1]),
                            "high": float(candle[2]),
                            "low": float(candle[3]),
                            "close": float(candle[4]),
                            "price": float(candle[4]),
                            "volume": float(candle[5]),
                            "source": "binance"
                        })

                    # Move start time to after last candle
                    last_candle_time = candles[-1][0]
                    current_start = last_candle_time + 1

                    print(f"  ✅ Batch {attempts}/{max_attempts}: {len(candles)} candles | Total: {len(all_candles)} | Last: {datetime.fromtimestamp(last_candle_time/1000).strftime('%Y-%m-%d')}")

                    # Stop if we've reached current time
                    if last_candle_time >= now_ms - (3600 * 1000):
                        print(f"  ✅ Reached current time")
                        break

                    # Rate limit: 50ms delay (Binance allows ~1200 req/min)
                    await asyncio.sleep(0.05)

            except Exception as e:
                print(f"  ❌ Error in batch {attempts}: {e}")
                break

        print(f"\n  📈 Total fetched: {len(all_candles)} candles from {attempts} requests")
        return all_candles

    async def fetch_historical_data(
        self,
        symbol: str,
        days: int,
        force_refresh: bool = False
    ) -> Dict:
        """
        Fetch historical data

        Args:
            symbol: BTC, ETH, SOL, etc.
            days: Number of days (180+ for P0)
            force_refresh: Bypass cache

        Returns:
            Dictionary with candles and metadata
        """
        # Convert symbol to Binance format
        binance_symbol = f"{symbol}USDT"

        cache_file = self.cache_dir / f"{symbol}_{days}d_binance.json"

        # Check cache
        if not force_refresh and cache_file.exists():
            cache_age = time.time() - cache_file.stat().st_mtime
            if cache_age < 3600:  # 1 hour cache
                print(f"📦 Loading from cache: {cache_file} (age: {cache_age/60:.1f}m)")
                with open(cache_file) as f:
                    return json.load(f)

        print(f"\n{'='*70}")
        print(f"🚀 Fetching {days} days of {symbol} from Binance (paginated)")
        print(f"{'='*70}")

        # Fetch with pagination
        candles = await self.fetch_paginated(binance_symbol, "1h", days)

        if not candles:
            raise Exception("No data fetched from Binance")

        # Calculate stats
        first_price = candles[0]["price"]
        last_price = candles[-1]["price"]
        price_change_pct = ((last_price - first_price) / first_price) * 100

        # Calculate actual days covered
        first_ts = datetime.fromisoformat(candles[0]["timestamp"])
        last_ts = datetime.fromisoformat(candles[-1]["timestamp"])
        actual_days = (last_ts - first_ts).days

        result = {
            "symbol": symbol,
            "requested_days": days,
            "actual_days": actual_days,
            "dataPoints": len(candles),
            "source": "binance",
            "first": candles[0]["timestamp"],
            "last": candles[-1]["timestamp"],
            "firstPrice": first_price,
            "lastPrice": last_price,
            "priceChange": f"{'+' if price_change_pct > 0 else ''}{price_change_pct:.2f}%",
            "data": candles,
            "fetchedAt": datetime.now().isoformat()
        }

        # Save to cache
        print(f"\n💾 Saving to cache: {cache_file}")
        with open(cache_file, 'w') as f:
            json.dump(result, f, indent=2)

        # Print summary
        expected_candles = days * 24
        coverage_pct = (len(candles) / expected_candles) * 100

        print(f"\n{'='*70}")
        print(f"✅ SUCCESS: Fetched {len(candles)} candles for {symbol}")
        print(f"{'='*70}")
        print(f"Requested:    {days} days")
        print(f"Actual:       {actual_days} days ({candles[0]['timestamp'][:10]} → {candles[-1]['timestamp'][:10]})")
        print(f"Candles:      {len(candles)}/{expected_candles} ({coverage_pct:.1f}% coverage)")
        print(f"Price:        ${first_price:,.2f} → ${last_price:,.2f}")
        print(f"Change:       {result['priceChange']}")
        print(f"Source:       Binance (paginated)")
        print(f"{'='*70}\n")

        return result


async def test_p0_requirement():
    """Test P0 requirement: 6 months of data"""
    fetcher = BinancePaginatedFetcher()

    print("="*70)
    print("P0 REQUIREMENT TEST: Fetch 6+ months of data")
    print("="*70)

    try:
        result = await fetcher.fetch_historical_data("BTC", 180, force_refresh=True)

        if result["actual_days"] >= 180:
            print("✅ P0 REQUIREMENT MET!")
            print(f"   Successfully fetched {result['actual_days']} days of data")
            print(f"   ({result['dataPoints']} candles)")
            return True
        else:
            print("❌ P0 REQUIREMENT NOT MET")
            print(f"   Only got {result['actual_days']} days (need 180+)")
            return False

    except Exception as e:
        print(f"❌ P0 TEST FAILED: {e}")
        return False


async def test_random_patterns():
    """Test random date ranges as requested"""
    fetcher = BinancePaginatedFetcher()

    test_patterns = [
        (7, "1 week - baseline"),
        (14, "2 weeks - random"),
        (30, "1 month - old worker limit"),
        (60, "2 months - random"),
        (90, "3 months - quarter"),
        (120, "4 months - random"),
        (180, "6 months - P0"),
        (270, "9 months - random"),
        (365, "1 year - full validation"),
        (547, "1.5 years - random"),
        (730, "2 years - max validation")
    ]

    print("\n" + "="*70)
    print("RANDOM PATTERN TESTING")
    print("="*70)

    results = {}

    for days, description in test_patterns:
        print(f"\n{'#'*70}")
        print(f"# Test: {days} days - {description}")
        print(f"{'#'*70}")

        try:
            result = await fetcher.fetch_historical_data("BTC", days)
            results[days] = {
                "success": True,
                "actual_days": result["actual_days"],
                "candles": result["dataPoints"],
                "coverage": f"{result['dataPoints']/(days*24)*100:.1f}%",
                "priceChange": result["priceChange"]
            }

            # Small delay between tests
            await asyncio.sleep(1)

        except Exception as e:
            print(f"❌ Failed: {e}")
            results[days] = {
                "success": False,
                "error": str(e)
            }

    # Print summary table
    print(f"\n{'='*70}")
    print("📊 RANDOM PATTERN TEST RESULTS")
    print(f"{'='*70}")
    print(f"{'Days':<8} {'Description':<20} {'Status':<8} {'Actual':<8} {'Candles':<10} {'Coverage':<10}")
    print(f"{'-'*70}")

    for days, description in test_patterns:
        result = results.get(days, {})
        desc_short = description[:20]

        if result.get("success"):
            status = "✅"
            actual = str(result["actual_days"])
            candles = str(result["candles"])
            coverage = result["coverage"]
        else:
            status = "❌"
            actual = "-"
            candles = "-"
            coverage = "-"

        print(f"{days:<8} {desc_short:<20} {status:<8} {actual:<8} {candles:<10} {coverage:<10}")

    print(f"{'='*70}\n")

    return results


async def fetch_multiple_symbols():
    """Fetch 6+ months for multiple symbols"""
    fetcher = BinancePaginatedFetcher()

    symbols = ["BTC", "ETH", "SOL"]
    days = 180  # 6 months (P0)

    print("="*70)
    print(f"FETCHING {days} DAYS FOR MULTIPLE SYMBOLS")
    print("="*70)

    results = {}

    for symbol in symbols:
        try:
            result = await fetcher.fetch_historical_data(symbol, days)
            results[symbol] = result
            await asyncio.sleep(1)
        except Exception as e:
            print(f"❌ Failed to fetch {symbol}: {e}")

    # Summary
    print(f"\n{'='*70}")
    print("📊 MULTI-SYMBOL SUMMARY")
    print(f"{'='*70}")
    print(f"{'Symbol':<10} {'Days':<8} {'Candles':<10} {'Price Change':<15}")
    print(f"{'-'*70}")

    for symbol, result in results.items():
        print(f"{symbol:<10} {result['actual_days']:<8} {result['dataPoints']:<10} {result['priceChange']:<15}")

    print(f"{'='*70}\n")

    return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "test-p0":
            # Test P0 requirement
            asyncio.run(test_p0_requirement())
        elif sys.argv[1] == "test-random":
            # Test random patterns
            asyncio.run(test_random_patterns())
        elif sys.argv[1] == "test-multi":
            # Fetch multiple symbols
            asyncio.run(fetch_multiple_symbols())
        elif sys.argv[1] == "fetch":
            # Fetch specific period
            symbol = sys.argv[2] if len(sys.argv) > 2 else "BTC"
            days = int(sys.argv[3]) if len(sys.argv) > 3 else 180

            async def fetch():
                fetcher = BinancePaginatedFetcher()
                return await fetcher.fetch_historical_data(symbol, days, force_refresh=True)

            asyncio.run(fetch())
        else:
            print("Usage:")
            print("  python fetch_binance_historical.py test-p0       # Test P0: 6 months")
            print("  python fetch_binance_historical.py test-random   # Test random patterns")
            print("  python fetch_binance_historical.py test-multi    # Fetch BTC/ETH/SOL")
            print("  python fetch_binance_historical.py fetch BTC 180 # Fetch specific")
    else:
        # Default: test P0
        print("🎯 Default: Testing P0 requirement (6 months)")
        asyncio.run(test_p0_requirement())
