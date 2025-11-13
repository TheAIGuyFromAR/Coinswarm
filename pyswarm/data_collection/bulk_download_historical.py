#!/usr/bin/env python3
"""
Bulk Historical Data Downloader

Downloads MAXIMUM GRANULARITY data for MAXIMUM HISTORY
- 5-minute intervals (very granular!)
- 2+ years of history
- ~525,000 candles per symbol
- One-time download, save locally, use forever!

Your API Key: da672b9999120841fbd4427fa4550b83b5f23e017c5c03ff33bafe09064abe83
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx


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
        print(f"Interval: {interval_minutes} minutes")
        print(f"Period: {datetime.fromtimestamp(target_start).strftime('%Y-%m-%d')} to {datetime.fromtimestamp(now).strftime('%Y-%m-%d')}\n")

        start_time = time.time()

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
                elapsed = time.time() - start_time
                rate = len(all_candles) / elapsed if elapsed > 0 else 0

                print(f"  ✅ Batch {batch_num:3d}/{expected_requests}: "
                      f"{len(valid_candles):4d} candles | "
                      f"Total: {len(all_candles):6,} | "
                      f"Oldest: {oldest_time.strftime('%Y-%m-%d')} | "
                      f"{progress_pct:.1f}% | "
                      f"{rate:.0f} candles/sec")

                # Move to next batch
                current_to = candles[0]['time'] - 1

                # Check if we've gone back far enough
                if candles[0]['time'] <= target_start:
                    print("\n  🎯 Reached target date!")
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
            total_time = time.time() - start_time

            print(f"\n{'='*80}")
            print("✅ SUCCESS!")
            print(f"{'='*80}")
            print(f"Symbol:       {symbol}")
            print(f"Interval:     {interval_minutes} minutes")
            print(f"Data Points:  {len(all_candles):,}")
            print(f"Period:       {all_candles[0]['timestamp'][:10]} to {all_candles[-1]['timestamp'][:10]}")
            print(f"Price:        ${first_price:,.2f} → ${last_price:,.2f}")
            print(f"Change:       {price_change:+.2f}%")
            print(f"File Size:    {filepath.stat().st_size / (1024*1024):.2f} MB")
            print(f"Fetch Time:   {total_time:.1f} seconds")
            print(f"API Calls:    {batch_num}")
            print(f"Saved To:     {filepath}")
            print(f"{'='*80}\n")

        return result


async def download_max_granularity(symbols=None, interval=5, days=730):
    """
    Download maximum granular data for all symbols

    Args:
        symbols: List of symbols (default: BTC, ETH, SOL)
        interval: Minute interval (default: 5)
        days: Days of history (default: 730 = 2 years)
    """

    api_key = "da672b9999120841fbd4427fa4550b83b5f23e017c5c03ff33bafe09064abe83"
    fetcher = BulkHistoricalFetcher(api_key)

    if symbols is None:
        symbols = ['BTC', 'ETH', 'SOL']

    print(f"\n{'#'*80}")
    print("# BULK HISTORICAL DATA DOWNLOAD")
    print(f"{'#'*80}")
    print("\nConfiguration:")
    print(f"  Symbols:  {', '.join(symbols)}")
    print(f"  Interval: {interval} minutes")
    print(f"  History:  {days} days ({days/365:.1f} years)")
    print(f"  Expected: ~{(days * 24 * 60 // interval):,} candles per symbol")
    print("\n")

    results = {}

    for i, symbol in enumerate(symbols, 1):
        print(f"\n{'#'*80}")
        print(f"# Symbol {i}/{len(symbols)}: {symbol}")
        print(f"{'#'*80}\n")

        try:
            result = await fetcher.fetch_all_history(
                symbol=symbol,
                interval_minutes=interval,
                max_days=days
            )
            results[symbol] = result

            # Small delay between symbols
            if i < len(symbols):
                print("⏳ Waiting 2 seconds before next symbol...\n")
                await asyncio.sleep(2)

        except Exception as e:
            print(f"❌ Failed to fetch {symbol}: {e}\n")
            results[symbol] = {'error': str(e)}

    # Final summary
    print("\n" + "="*80)
    print("🎉 BULK DOWNLOAD COMPLETE!")
    print("="*80)

    print(f"\n{'Symbol':<10} {'Candles':<15} {'Period':<25} {'Size':<10} {'Status':<10}")
    print("-"*80)

    total_candles = 0
    total_size = 0

    for symbol in symbols:
        result = results.get(symbol, {})

        if 'error' in result:
            print(f"{symbol:<10} {'ERROR':<15} {'-':<25} {'-':<10} {'❌':<10}")
        elif result:
            candles = result.get('dataPoints', 0)
            first = result.get('first', '')[:10]
            last = result.get('last', '')[:10]
            period = f"{first} to {last}"

            filepath = Path(f"data/historical/{symbol}_{days}d_{interval}min_full.json")
            size_mb = filepath.stat().st_size / (1024*1024) if filepath.exists() else 0

            print(f"{symbol:<10} {candles:>10,} {'':>4} {period:<25} {size_mb:>5.1f} MB  {'✅':<10}")

            total_candles += candles
            total_size += size_mb

    print("-"*80)
    print(f"{'TOTAL':<10} {total_candles:>10,} {'':>4} {'':<25} {total_size:>5.1f} MB")
    print("="*80)

    print(f"\n✅ Downloaded: {len([r for r in results.values() if 'error' not in r])}/{len(symbols)} symbols")
    print("📁 Location: data/historical/")
    print("🚀 Ready for backtesting!\n")

    return results


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    MAXIMUM GRANULARITY BULK DOWNLOADER                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

This will download the MOST GRANULAR data for the LONGEST PERIOD:

  • 5-minute intervals (very granular!)
  • 2 years of history (730 days)
  • ~525,000 candles per symbol
  • BTC, ETH, SOL

Time: ~5-10 minutes
Cost: FREE (within API limits)

""")

    if len(sys.argv) > 1:
        if sys.argv[1] == '--help':
            print("Usage:")
            print("  python bulk_download_historical.py                    # Default: BTC, ETH, SOL, 5min, 730 days")
            print("  python bulk_download_historical.py BTC ETH            # Specific symbols")
            print("  python bulk_download_historical.py BTC --interval=15  # 15-minute intervals")
            print("  python bulk_download_historical.py BTC --days=365     # 1 year only")
            sys.exit(0)

        # Parse arguments
        symbols = []
        interval = 5
        days = 730

        for arg in sys.argv[1:]:
            if arg.startswith('--interval='):
                interval = int(arg.split('=')[1])
            elif arg.startswith('--days='):
                days = int(arg.split('=')[1])
            else:
                symbols.append(arg)

        if not symbols:
            symbols = ['BTC', 'ETH', 'SOL']

        asyncio.run(download_max_granularity(symbols, interval, days))
    else:
        # Default: BTC, ETH, SOL with 5-minute intervals for 2 years
        asyncio.run(download_max_granularity())
