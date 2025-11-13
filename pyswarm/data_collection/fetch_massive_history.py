"""
Fetch massive amounts of historical data for pattern discovery.

Fetches 2+ years of data at 1-hour intervals for multiple symbols.
This gives us ~17,500 data points per symbol for analysis.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY = "da672b9999120841fbd4427fa4550b83b5f23e017c5c03ff33bafe09064abe83"
BASE_URL = "https://min-api.cryptocompare.com/data/v2/histohour"


async def fetch_chunk(session: aiohttp.ClientSession, symbol: str, to_ts: int, limit: int = 2000) -> list[dict]:
    """Fetch one chunk of historical data"""
    params = {
        "fsym": symbol,
        "tsym": "USD",
        "limit": limit,
        "toTs": to_ts,
        "api_key": API_KEY
    }

    async with session.get(BASE_URL, params=params) as response:
        if response.status == 200:
            data = await response.json()
            if data.get("Response") == "Success":
                return data["Data"]["Data"]
        return []


async def fetch_historical_data(symbol: str, days: int = 730) -> list[dict]:
    """
    Fetch historical data for a symbol going back 'days' days.

    CryptoCompare allows max 2000 data points per request.
    For hourly data, 2000 hours = ~83 days.
    So for 730 days (2 years), we need ~9 requests.
    """

    logger.info(f"Fetching {days} days of hourly data for {symbol}...")

    all_data = []
    hours_needed = days * 24
    chunks_needed = (hours_needed // 2000) + 1

    # Start from now and work backwards
    to_ts = int(datetime.now().timestamp())

    async with aiohttp.ClientSession() as session:
        for i in range(chunks_needed):
            logger.info(f"  Chunk {i+1}/{chunks_needed}...")

            chunk = await fetch_chunk(session, symbol, to_ts, limit=2000)

            if not chunk:
                logger.warning(f"  No data returned for chunk {i+1}")
                break

            all_data.extend(chunk)

            # Next chunk starts before the oldest data point we just got
            to_ts = chunk[0]["time"] - 1

            # Rate limiting: be nice to the API
            await asyncio.sleep(1)

    # Remove duplicates and sort by time
    seen = set()
    unique_data = []
    for candle in all_data:
        ts = candle["time"]
        if ts not in seen:
            seen.add(ts)
            unique_data.append(candle)

    unique_data.sort(key=lambda x: x["time"])

    logger.info(f"  ✓ Fetched {len(unique_data)} unique hourly candles for {symbol}")

    return unique_data


async def fetch_all_symbols(symbols: list[str], days: int = 730):
    """Fetch historical data for multiple symbols"""

    logger.info("=" * 80)
    logger.info("MASSIVE HISTORICAL DATA FETCH")
    logger.info("=" * 80)
    logger.info(f"Symbols: {', '.join(symbols)}")
    logger.info(f"Time period: {days} days (~{days/365:.1f} years)")
    logger.info(f"Expected data points per symbol: ~{days * 24}")
    logger.info("=" * 80)

    output_dir = Path("data/historical_massive")
    output_dir.mkdir(parents=True, exist_ok=True)

    for symbol in symbols:
        data = await fetch_historical_data(symbol, days)

        if data:
            # Convert to our format
            formatted_data = {
                "symbol": symbol,
                "timeframe": "1h",
                "count": len(data),
                "start_date": datetime.fromtimestamp(data[0]["time"]).isoformat(),
                "end_date": datetime.fromtimestamp(data[-1]["time"]).isoformat(),
                "data": [
                    {
                        "timestamp": datetime.fromtimestamp(candle["time"]).isoformat() + "Z",
                        "open": candle["open"],
                        "high": candle["high"],
                        "low": candle["low"],
                        "close": candle["close"],
                        "volume": candle["volumefrom"]
                    }
                    for candle in data
                ]
            }

            # Save to file
            filename = output_dir / f"{symbol}_{days}d_hour.json"
            with open(filename, "w") as f:
                json.dump(formatted_data, f, indent=2)

            logger.info(f"💾 Saved {len(data)} candles to {filename}")
            logger.info(f"   Period: {formatted_data['start_date']} to {formatted_data['end_date']}")

            # Calculate some stats
            prices = [c["close"] for c in data]
            price_change = (prices[-1] - prices[0]) / prices[0] * 100
            logger.info(f"   Price change: {price_change:+.2f}%")
            logger.info("")


async def main():
    """Fetch massive historical data for multiple symbols"""

    symbols = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "MATIC"]
    days = 730  # 2 years

    await fetch_all_symbols(symbols, days)

    logger.info("=" * 80)
    logger.info("COMPLETE!")
    logger.info(f"Total expected data points: ~{len(symbols) * days * 24:,}")
    logger.info("All data saved to data/historical_massive/")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
