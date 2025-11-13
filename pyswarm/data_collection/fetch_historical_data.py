#!/usr/bin/env python3
"""
Multi-Month Historical Data Fetcher

Fetches and caches historical data from Coinswarm Worker.
Handles rate limiting, caching, and multi-month downloads.

Usage:
    # Fetch 3 months of BTC data
    python fetch_historical_data.py --symbol BTC --months 3

    # Fetch 2 years of BTC, ETH, SOL data
    python fetch_historical_data.py --symbol BTC ETH SOL --months 24

    # Use cached data (don't re-download)
    python fetch_historical_data.py --symbol BTC --use-cache
"""

import argparse
import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path

from coinswarm.data_ingest.coinswarm_worker_client import CoinswarmWorkerClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class HistoricalDataCache:
    """Cache for historical data to avoid re-fetching"""

    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_path(self, symbol: str, days: int) -> Path:
        """Get cache file path for symbol and period"""
        return self.cache_dir / f"{symbol}_{days}days.json"

    def load(self, symbol: str, days: int) -> list[dict]:
        """Load cached data if available and recent"""
        cache_file = self.get_cache_path(symbol, days)

        if not cache_file.exists():
            return None

        # Check if cache is recent (< 24 hours old)
        age_hours = (time.time() - cache_file.stat().st_mtime) / 3600
        if age_hours > 24:
            logger.info(f"Cache for {symbol} is {age_hours:.1f} hours old, refreshing...")
            return None

        logger.info(f"Loading {symbol} from cache ({age_hours:.1f} hours old)")

        with open(cache_file) as f:
            return json.load(f)

    def save(self, symbol: str, days: int, data: list[dict]):
        """Save data to cache"""
        cache_file = self.get_cache_path(symbol, days)

        logger.info(f"Saving {len(data)} candles for {symbol} to cache")

        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2)


async def fetch_with_retry(
    worker: CoinswarmWorkerClient,
    symbol: str,
    days: int,
    max_retries: int = 3,
    retry_delay: int = 5
) -> list:
    """Fetch data with retry logic for rate limiting"""

    for attempt in range(max_retries):
        try:
            data = await worker.fetch_price_data(symbol, days=days)
            return data

        except Exception as e:
            if "503" in str(e) or "Service Unavailable" in str(e):
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt+2}/{max_retries}...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed after {max_retries} retries")
                    raise
            else:
                raise

    return []


async def fetch_multi_month_data(
    symbols: list[str],
    months: int,
    use_cache: bool = True,
    chunk_size: int = 30  # Fetch in 30-day chunks
) -> dict[str, list]:
    """
    Fetch multiple months of data for multiple symbols.

    Args:
        symbols: List of symbols (e.g., ["BTC", "ETH", "SOL"])
        months: Number of months to fetch
        use_cache: Use cached data if available
        chunk_size: Days per chunk (to avoid rate limits)

    Returns:
        Dictionary mapping symbol to list of data points
    """

    cache = HistoricalDataCache()
    worker = CoinswarmWorkerClient()

    all_data = {}

    for symbol in symbols:
        logger.info(f"\n{'='*70}")
        logger.info(f"Fetching {months} months of {symbol} data")
        logger.info(f"{'='*70}\n")

        # Check cache first
        total_days = months * 30
        if use_cache:
            cached_data = cache.load(symbol, total_days)
            if cached_data:
                logger.info(f"✓ Loaded {len(cached_data)} candles from cache")
                # Convert cached dict back to DataPoints
                from coinswarm.data_ingest.base import DataPoint
                data_points = []
                for item in cached_data:
                    dp = DataPoint(
                        source=item['source'],
                        symbol=item['symbol'],
                        timeframe=item['timeframe'],
                        timestamp=datetime.fromisoformat(item['timestamp']),
                        data=item['data'],
                        quality_score=item['quality_score']
                    )
                    data_points.append(dp)

                all_data[symbol] = data_points
                continue

        # Fetch in chunks to avoid rate limits
        all_chunks = []
        chunks_needed = (total_days + chunk_size - 1) // chunk_size  # Round up

        logger.info(f"Fetching {chunks_needed} chunks of {chunk_size} days each...")

        for chunk_num in range(chunks_needed):
            days_to_fetch = min(chunk_size, total_days - (chunk_num * chunk_size))

            if days_to_fetch <= 0:
                break

            logger.info(f"Chunk {chunk_num+1}/{chunks_needed}: Fetching {days_to_fetch} days...")

            try:
                chunk_data = await fetch_with_retry(worker, symbol, days_to_fetch)

                if chunk_data:
                    all_chunks.extend(chunk_data)
                    logger.info(f"  ✓ Got {len(chunk_data)} candles")

                # Wait between chunks to avoid rate limiting
                if chunk_num < chunks_needed - 1:
                    logger.info("  Waiting 10s before next chunk...")
                    await asyncio.sleep(10)

            except Exception as e:
                logger.error(f"  ✗ Failed to fetch chunk: {e}")
                break

        if all_chunks:
            # Save to cache
            cache_data = []
            for dp in all_chunks:
                cache_data.append({
                    'source': dp.source,
                    'symbol': dp.symbol,
                    'timeframe': dp.timeframe,
                    'timestamp': dp.timestamp.isoformat(),
                    'data': dp.data,
                    'quality_score': dp.quality_score
                })

            cache.save(symbol, total_days, cache_data)

            all_data[symbol] = all_chunks

            # Show summary
            if all_chunks:
                start_price = all_chunks[0].data['price']
                end_price = all_chunks[-1].data['price']
                return_pct = ((end_price - start_price) / start_price) * 100

                logger.info(f"\n✅ {symbol}: {len(all_chunks)} candles")
                logger.info(f"   Date range: {all_chunks[0].timestamp.date()} to {all_chunks[-1].timestamp.date()}")
                logger.info(f"   Price: ${start_price:,.2f} → ${end_price:,.2f}")
                logger.info(f"   Return: {return_pct:+.2f}%")
        else:
            logger.warning(f"No data fetched for {symbol}")
            all_data[symbol] = []

    return all_data


async def main():
    parser = argparse.ArgumentParser(description="Fetch historical crypto data")
    parser.add_argument("--symbols", nargs="+", default=["BTC"], help="Symbols to fetch (BTC, ETH, SOL)")
    parser.add_argument("--months", type=int, default=3, help="Months of history (1-24)")
    parser.add_argument("--use-cache", action="store_true", help="Use cached data if available")
    parser.add_argument("--chunk-size", type=int, default=30, help="Days per fetch chunk")

    args = parser.parse_args()

    print("\n" + "="*70)
    print("HISTORICAL DATA FETCHER")
    print("="*70 + "\n")

    print(f"Symbols: {', '.join(args.symbols)}")
    print(f"Months: {args.months}")
    print(f"Use Cache: {args.use_cache}")
    print(f"Chunk Size: {args.chunk_size} days")
    print()

    start_time = time.time()

    # Fetch data
    data = await fetch_multi_month_data(
        symbols=args.symbols,
        months=args.months,
        use_cache=args.use_cache,
        chunk_size=args.chunk_size
    )

    duration = time.time() - start_time

    # Summary
    print("\n" + "="*70)
    print("FETCH COMPLETE")
    print("="*70)
    print(f"Duration: {duration:.1f}s")
    print()

    total_candles = sum(len(d) for d in data.values())
    print(f"Total candles: {total_candles:,}")
    print()

    for symbol, candles in data.items():
        if candles:
            print(f"{symbol}:")
            print(f"  Candles: {len(candles):,}")
            print(f"  Date range: {candles[0].timestamp.date()} to {candles[-1].timestamp.date()}")

            start_price = candles[0].data['price']
            end_price = candles[-1].data['price']
            return_pct = ((end_price - start_price) / start_price) * 100

            print(f"  Price: ${start_price:,.2f} → ${end_price:,.2f}")
            print(f"  Return: {return_pct:+.2f}%")
            print()

    print("Data cached in: data/cache/")
    print()
    print("Next steps:")
    print("  1. Run backtest: python demo_real_data_backtest.py")
    print("  2. Validate: python validate_strategy_random.py --use-cached")
    print()


if __name__ == "__main__":
    asyncio.run(main())
