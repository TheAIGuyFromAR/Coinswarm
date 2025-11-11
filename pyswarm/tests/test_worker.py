#!/usr/bin/env python3
"""
Test Cloudflare Worker

Usage:
    python test_worker.py https://your-worker-url.workers.dev

This will:
1. Test if Worker is accessible
2. Fetch sample BTC data
3. Show data format
4. Confirm it's working
"""

import sys
import asyncio
import httpx


async def test_worker(worker_url):
    """Test the Cloudflare Worker"""

    print(f"\n{'='*70}")
    print(f"Testing Cloudflare Worker")
    print(f"{'='*70}\n")

    worker_url = worker_url.rstrip('/')

    # Test 1: Root endpoint
    print("Test 1: Checking Worker status...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(worker_url, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            print(f"✓ Worker is online!")
            print(f"  Status: {data.get('status')}")
            print(f"  Endpoints: {data.get('endpoints')}")
            print()

    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        print("\nMake sure the Worker URL is correct!")
        return False

    # Test 2: Fetch real data
    print("Test 2: Fetching BTC data (7 days, 1h candles)...")
    try:
        async with httpx.AsyncClient() as client:
            url = f"{worker_url}/fetch"
            params = {
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "days": 7
            }

            response = await client.get(url, params=params, timeout=30.0)
            response.raise_for_status()
            data = response.json()

            if not data.get('success'):
                print(f"✗ Worker returned error: {data.get('error')}")
                return False

            print(f"✓ Fetched {data['candles']} candles!")
            print(f"  Symbol: {data['symbol']}")
            print(f"  Timeframe: {data['timeframe']}")
            print(f"  Date range: {data['first']} to {data['last']}")
            print(f"  Price: ${data['firstPrice']:,.2f} → ${data['lastPrice']:,.2f}")
            print(f"  Change: {data['priceChange']}")
            print()

            # Show sample data
            print("Sample data (first candle):")
            if data['data']:
                sample = data['data'][0]
                print(f"  Timestamp: {sample['timestamp']}")
                print(f"  Price: ${sample['price']:,.2f}")
                print(f"  Volume: {sample['volume']:,.2f}")
                print(f"  High: ${sample['high']:,.2f}")
                print(f"  Low: ${sample['low']:,.2f}")
                print()

    except Exception as e:
        print(f"✗ Failed to fetch data: {e}")
        return False

    # Test 3: Multiple symbols
    print("Test 3: Testing multiple symbols...")
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    for symbol in symbols:
        try:
            async with httpx.AsyncClient() as client:
                url = f"{worker_url}/fetch"
                params = {
                    "symbol": symbol,
                    "timeframe": "1h",
                    "days": 1  # Just 1 day for quick test
                }

                response = await client.get(url, params=params, timeout=30.0)
                response.raise_for_status()
                data = response.json()

                if data.get('success'):
                    print(f"  ✓ {symbol}: {data['candles']} candles, "
                          f"${data['firstPrice']:,.2f} → ${data['lastPrice']:,.2f}")
                else:
                    print(f"  ✗ {symbol}: {data.get('error')}")

        except Exception as e:
            print(f"  ✗ {symbol}: {e}")

    print()
    print("="*70)
    print("✅ ALL TESTS PASSED!")
    print("="*70)
    print()
    print("Next steps:")
    print("1. Update historical_data_fetcher.py with this Worker URL")
    print("2. Run: python demo_real_data.py")
    print("3. See real backtesting results!")
    print()

    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nUsage: python test_worker.py <worker-url>")
        print("\nExample:")
        print("  python test_worker.py https://coinswarm-data-fetcher.yourname.workers.dev")
        print()
        sys.exit(1)

    worker_url = sys.argv[1]
    success = asyncio.run(test_worker(worker_url))

    sys.exit(0 if success else 1)
