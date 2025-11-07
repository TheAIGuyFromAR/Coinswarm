#!/usr/bin/env python3
"""
Quick API Key Test - Run this first to verify your setup

This makes a single API call to verify:
1. Your API key works
2. The CryptoCompare API is accessible
3. Dependencies are installed

Expected time: 2-3 seconds
"""

import asyncio
import httpx
from datetime import datetime

API_KEY = "da672b9999120841fbd4427fa4550b83b5f23e017c5c03ff33bafe09064abe83"

async def test_api():
    print("\n" + "="*60)
    print("🔑 Testing CryptoCompare API Key")
    print("="*60 + "\n")

    # Test endpoint: Get last 10 5-minute candles for BTC
    url = f"https://min-api.cryptocompare.com/data/v2/histominute?fsym=BTC&tsym=USD&limit=10&api_key={API_KEY}"

    print(f"Making test request to CryptoCompare...")
    print(f"Endpoint: histominute")
    print(f"Symbol: BTC")
    print(f"Limit: 10 candles\n")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)

            print(f"Status Code: {response.status_code}")

            if response.status_code != 200:
                print(f"❌ HTTP Error: {response.status_code}")
                print(f"Response: {response.text[:200]}")
                return False

            data = response.json()

            # Check response structure
            if data.get('Response') != 'Success':
                print(f"❌ API Error: {data.get('Message', 'Unknown error')}")
                return False

            candles = data.get('Data', {}).get('Data', [])

            if not candles:
                print("❌ No candle data returned")
                return False

            # Display results
            print(f"✅ SUCCESS!\n")
            print(f"API Key: Valid")
            print(f"Candles Retrieved: {len(candles)}")
            print(f"Time Range: {datetime.fromtimestamp(candles[0]['time']).strftime('%Y-%m-%d %H:%M')} to {datetime.fromtimestamp(candles[-1]['time']).strftime('%Y-%m-%d %H:%M')}")
            print(f"Latest BTC Price: ${candles[-1]['close']:,.2f}")
            print(f"\n" + "="*60)
            print("✅ Your API key is working! Ready for bulk download.")
            print("="*60 + "\n")

            return True

    except httpx.TimeoutException:
        print("❌ Request timed out. Check your internet connection.")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║            CryptoCompare API Key Test                        ║
╚══════════════════════════════════════════════════════════════╝

This will verify your API key works before running the full
bulk download.

Requirements:
  • Internet connection
  • Python 3.7+
  • httpx library (pip install httpx)

""")

    success = asyncio.run(test_api())

    if success:
        print("\n✅ Next step: Run the bulk download:")
        print("   python bulk_download_historical.py\n")
    else:
        print("\n❌ API key test failed. Please check:")
        print("   1. Internet connection is working")
        print("   2. API key is correct")
        print("   3. httpx is installed: pip install httpx\n")
