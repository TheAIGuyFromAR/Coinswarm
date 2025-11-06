#!/usr/bin/env python3
"""
Direct Multi-Source Historical Data Fetcher

Fetches 6+ months to 2+ years of data directly from APIs, bypassing
the deployed worker limitation of 30 days.

Sources:
- CryptoCompare (free, 2000 hours/call)
- CoinGecko (free, 365 days/call)
- Kraken (free, ~30 days)

P0 Requirement: Get 6+ months of data
"""

import asyncio
import httpx
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import time


class MultiSourceHistoricalFetcher:
    """Fetches historical data from multiple sources"""

    def __init__(self, cache_dir: str = "data/historical"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = 30.0

    async def fetch_from_cryptocompare(
        self,
        symbol: str,
        days: int
    ) -> List[Dict]:
        """
        Fetch from CryptoCompare (free, 2000 hours per call)
        """
        print(f"\n📊 Fetching {symbol} from CryptoCompare for {days} days...")

        all_candles = []
        hours_needed = days * 24
        calls_needed = (hours_needed // 2000) + 1

        now = int(time.time())

        for i in range(calls_needed):
            to_ts = now - (i * 2000 * 3600)
            limit = min(2000, hours_needed - (i * 2000))

            if limit <= 0:
                break

            url = f"https://min-api.cryptocompare.com/data/v2/histohour"
            params = {
                "fsym": symbol,
                "tsym": "USD",
                "limit": limit,
                "toTs": to_ts
            }

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        url,
                        params=params,
                        timeout=self.timeout,
                        headers={"User-Agent": "Coinswarm/1.0"}
                    )

                    if response.status_code != 200:
                        print(f"  ❌ CryptoCompare HTTP {response.status_code}")
                        continue

                    data = response.json()

                    if data.get("Response") != "Success":
                        print(f"  ❌ CryptoCompare error: {data.get('Message')}")
                        continue

                    candles = data.get("Data", {}).get("Data", [])

                    for candle in candles:
                        all_candles.append({
                            "timestamp": datetime.fromtimestamp(candle["time"]).isoformat(),
                            "open": candle["open"],
                            "high": candle["high"],
                            "low": candle["low"],
                            "close": candle["close"],
                            "price": candle["close"],
                            "volume": candle["volumeto"],
                            "source": "cryptocompare"
                        })

                    print(f"  ✅ Batch {i+1}/{calls_needed}: {len(candles)} candles")

                    # Rate limit: 1 second between calls
                    if i < calls_needed - 1:
                        await asyncio.sleep(1.0)

            except Exception as e:
                print(f"  ❌ Error fetching from CryptoCompare: {e}")
                break

        print(f"  📈 Total from CryptoCompare: {len(all_candles)} candles")
        return all_candles

    async def fetch_from_coingecko(
        self,
        symbol: str,
        days: int
    ) -> List[Dict]:
        """
        Fetch from CoinGecko (free, 365 days at a time)
        """
        print(f"\n📊 Fetching {symbol} from CoinGecko for {days} days...")

        # Map symbols to CoinGecko IDs
        coin_ids = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
            "AVAX": "avalanche-2",
            "MATIC": "matic-network"
        }

        coin_id = coin_ids.get(symbol)
        if not coin_id:
            print(f"  ❌ Unknown CoinGecko ID for {symbol}")
            return []

        all_candles = []
        calls_needed = (days // 365) + 1

        for i in range(calls_needed):
            days_this_call = min(365, days - (i * 365))

            if days_this_call <= 0:
                break

            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
            params = {
                "vs_currency": "usd",
                "days": days_this_call,
                "interval": "hourly"
            }

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        url,
                        params=params,
                        timeout=self.timeout,
                        headers={"User-Agent": "Coinswarm/1.0"}
                    )

                    if response.status_code != 200:
                        print(f"  ❌ CoinGecko HTTP {response.status_code}")
                        continue

                    data = response.json()
                    prices = data.get("prices", [])
                    volumes = data.get("total_volumes", [])

                    for j, (ts, price) in enumerate(prices):
                        volume = volumes[j][1] if j < len(volumes) else 0

                        all_candles.append({
                            "timestamp": datetime.fromtimestamp(ts / 1000).isoformat(),
                            "price": price,
                            "volume": volume,
                            "source": "coingecko"
                        })

                    print(f"  ✅ Batch {i+1}/{calls_needed}: {len(prices)} candles")

                    # Rate limit: 2 seconds (CoinGecko free tier)
                    if i < calls_needed - 1:
                        await asyncio.sleep(2.0)

            except Exception as e:
                print(f"  ❌ Error fetching from CoinGecko: {e}")
                break

        print(f"  📈 Total from CoinGecko: {len(all_candles)} candles")
        return all_candles

    def deduplicate_and_merge(self, candles: List[Dict]) -> List[Dict]:
        """Deduplicate candles by timestamp"""
        seen = {}

        for candle in candles:
            ts = candle["timestamp"]

            if ts not in seen:
                seen[ts] = candle
            else:
                # Average if duplicate
                existing = seen[ts]
                existing["price"] = (existing["price"] + candle["price"]) / 2
                if "volume" in existing and "volume" in candle:
                    existing["volume"] = (existing["volume"] + candle["volume"]) / 2

        # Sort by timestamp
        result = list(seen.values())
        result.sort(key=lambda x: x["timestamp"])

        return result

    async def fetch_historical_data(
        self,
        symbol: str,
        days: int,
        force_refresh: bool = False
    ) -> Dict:
        """
        Fetch historical data from multiple sources

        Args:
            symbol: BTC, ETH, SOL, etc.
            days: Number of days (6+ months = 180+ days is P0)
            force_refresh: Bypass cache

        Returns:
            Dictionary with candles and metadata
        """
        cache_file = self.cache_dir / f"{symbol}_{days}d_multi.json"

        # Check cache
        if not force_refresh and cache_file.exists():
            print(f"📦 Loading from cache: {cache_file}")
            with open(cache_file) as f:
                return json.load(f)

        print(f"\n{'='*70}")
        print(f"🚀 Fetching {days} days of {symbol} historical data")
        print(f"{'='*70}")

        all_candles = []
        sources_used = []

        # Fetch from CryptoCompare
        cc_data = await self.fetch_from_cryptocompare(symbol, days)
        if cc_data:
            all_candles.extend(cc_data)
            sources_used.append("CryptoCompare")

        # Fetch from CoinGecko (if insufficient coverage)
        expected_candles = days * 24
        if len(all_candles) < expected_candles * 0.9:
            cg_data = await self.fetch_from_coingecko(symbol, days)
            if cg_data:
                all_candles.extend(cg_data)
                sources_used.append("CoinGecko")

        # Deduplicate and merge
        print(f"\n🔄 Deduplicating {len(all_candles)} candles...")
        unique_candles = self.deduplicate_and_merge(all_candles)

        if not unique_candles:
            raise Exception("No data fetched from any source")

        # Calculate stats
        first_price = unique_candles[0]["price"]
        last_price = unique_candles[-1]["price"]
        price_change_pct = ((last_price - first_price) / first_price) * 100

        result = {
            "symbol": symbol,
            "days": days,
            "dataPoints": len(unique_candles),
            "sources": sources_used,
            "first": unique_candles[0]["timestamp"],
            "last": unique_candles[-1]["timestamp"],
            "firstPrice": first_price,
            "lastPrice": last_price,
            "priceChange": f"{'+' if price_change_pct > 0 else ''}{price_change_pct:.2f}%",
            "data": unique_candles,
            "fetchedAt": datetime.now().isoformat()
        }

        # Save to cache
        print(f"\n💾 Saving to cache: {cache_file}")
        with open(cache_file, 'w') as f:
            json.dump(result, f, indent=2)

        # Print summary
        print(f"\n{'='*70}")
        print(f"✅ SUCCESS: Fetched {len(unique_candles)} candles for {symbol}")
        print(f"{'='*70}")
        print(f"Period:       {unique_candles[0]['timestamp'][:10]} → {unique_candles[-1]['timestamp'][:10]}")
        print(f"Price:        ${first_price:,.2f} → ${last_price:,.2f}")
        print(f"Change:       {result['priceChange']}")
        print(f"Sources:      {', '.join(sources_used)}")
        print(f"Coverage:     {len(unique_candles)}/{expected_candles} candles ({len(unique_candles)/expected_candles*100:.1f}%)")
        print(f"{'='*70}\n")

        return result


async def test_multiple_timeframes(symbol: str = "BTC"):
    """Test different timeframes to verify data retrieval"""
    fetcher = MultiSourceHistoricalFetcher()

    # Test different periods
    test_cases = [
        (7, "1 week - baseline test"),
        (30, "1 month - current worker limit"),
        (90, "3 months - testing extended"),
        (180, "6 months - P0 REQUIREMENT"),
        (365, "1 year - extended validation"),
        (730, "2 years - full validation")
    ]

    results = {}

    for days, description in test_cases:
        print(f"\n{'#'*70}")
        print(f"# Test: {description}")
        print(f"{'#'*70}")

        try:
            result = await fetcher.fetch_historical_data(symbol, days)
            results[days] = {
                "success": True,
                "candles": result["dataPoints"],
                "coverage": f"{result['dataPoints']/(days*24)*100:.1f}%",
                "priceChange": result["priceChange"]
            }

            # Small delay between tests
            await asyncio.sleep(2)

        except Exception as e:
            print(f"❌ Failed: {e}")
            results[days] = {
                "success": False,
                "error": str(e)
            }

    # Print summary
    print(f"\n{'='*70}")
    print("📊 SUMMARY OF ALL TESTS")
    print(f"{'='*70}")
    print(f"{'Period':<15} {'Status':<10} {'Candles':<12} {'Coverage':<12} {'Change':<15}")
    print(f"{'-'*70}")

    for days, description in test_cases:
        result = results.get(days, {})
        if result.get("success"):
            status = "✅ PASS"
            candles = str(result["candles"])
            coverage = result["coverage"]
            change = result["priceChange"]
        else:
            status = "❌ FAIL"
            candles = "-"
            coverage = "-"
            change = result.get("error", "Unknown error")[:20]

        print(f"{description:<15} {status:<10} {candles:<12} {coverage:<12} {change:<15}")

    print(f"{'='*70}\n")

    # Check P0 requirement
    p0_result = results.get(180, {})
    if p0_result.get("success"):
        print("✅ P0 REQUIREMENT MET: Successfully fetched 6+ months of data!")
    else:
        print("❌ P0 REQUIREMENT NOT MET: Failed to fetch 6 months")

    return results


async def fetch_for_backtest(
    symbol: str = "BTC",
    days: int = 180,
    force_refresh: bool = False
):
    """Fetch data specifically for backtesting"""
    fetcher = MultiSourceHistoricalFetcher()
    result = await fetcher.fetch_historical_data(symbol, days, force_refresh)

    # Save in format compatible with existing backtest scripts
    output_file = Path(f"data/historical/{symbol}-USD_{days}d.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"💾 Saved backtest data to: {output_file}")

    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            # Run all tests
            asyncio.run(test_multiple_timeframes("BTC"))
        elif sys.argv[1] == "fetch":
            # Fetch specific period
            symbol = sys.argv[2] if len(sys.argv) > 2 else "BTC"
            days = int(sys.argv[3]) if len(sys.argv) > 3 else 180
            asyncio.run(fetch_for_backtest(symbol, days, force_refresh=True))
        else:
            print("Usage:")
            print("  python fetch_multi_source_historical.py test")
            print("  python fetch_multi_source_historical.py fetch BTC 180")
    else:
        # Default: fetch P0 requirement (6 months)
        print("🎯 Fetching P0 requirement: 6 months (180 days) of BTC data")
        asyncio.run(fetch_for_backtest("BTC", 180, force_refresh=True))
