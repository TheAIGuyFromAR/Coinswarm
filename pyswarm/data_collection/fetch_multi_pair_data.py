"""
Fetch 2+ years historical data for multiple trading pairs.

Pairs to fetch:
- BTC-USD (all stablecoin variants: USDT, USDC, BUSD)
- SOL-USD (all stablecoin variants)
- BTC-SOL (direct pair)

Data requirements:
- Minimum 2 years (730 days)
- Prefer 3+ years for robust validation
- 1-hour candles (good for all timescales)
- Include: OHLCV, volume, trades

Sources:
1. Binance (primary): Has all pairs, 3+ years data
2. Coinbase (backup): Good for BTC-USD, SOL-USD
3. Cloudflare Worker (your existing): Already integrated

This script fetches data and saves to CSV for offline testing.
"""

import asyncio
import json
from datetime import datetime, timedelta
import logging
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from coinswarm.data_ingest.coinswarm_worker_client import CoinswarmWorkerClient
except ImportError:
    print("Using standalone implementation (no dependencies needed)")
    # Standalone HTTP client
    import urllib.request
    import urllib.parse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Pairs to fetch
# NOTE: 5m = 5-minute candles (288 per day, 525,600 for 2 years!)
# NOTE: 1h = 1-hour candles (24 per day, 17,520 for 2 years)
PAIRS = [
    # BTC stablecoin pairs - 5 MINUTE candles for maximum granularity
    ("BTC", "USDT", "5m"),
    ("BTC", "USDC", "5m"),
    ("BTC", "BUSD", "5m"),

    # SOL stablecoin pairs - 5 MINUTE candles
    ("SOL", "USDT", "5m"),
    ("SOL", "USDC", "5m"),
    ("SOL", "BUSD", "5m"),

    # ETH stablecoin pairs - 5 MINUTE candles
    ("ETH", "USDT", "5m"),
    ("ETH", "USDC", "5m"),

    # Direct pair - 5 MINUTE candles
    ("BTC", "SOL", "5m"),
    ("SOL", "BTC", "5m"),
]

# Data directory
DATA_DIR = Path(__file__).parent / "data" / "historical"
DATA_DIR.mkdir(parents=True, exist_ok=True)


async def fetch_binance_data(
    base: str,
    quote: str,
    interval: str,
    days: int = 1095  # 3 years
) -> pd.DataFrame:
    """
    Fetch historical data from Binance.

    Args:
        base: Base currency (e.g., "BTC")
        quote: Quote currency (e.g., "USDT")
        interval: Candle interval (e.g., "1h")
        days: Number of days to fetch

    Returns:
        DataFrame with OHLCV data
    """
    symbol = f"{base}{quote}"

    logger.info(f"Fetching {symbol} from Binance ({days} days, {interval} candles)...")

    try:
        ingestor = BinanceIngestor()

        # Calculate start/end dates
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Fetch data
        df = await ingestor.fetch_historical_klines(
            symbol=symbol,
            interval=interval,
            start_time=start_date,
            end_time=end_date
        )

        if df is not None and len(df) > 0:
            logger.info(f"  ✅ Fetched {len(df)} candles for {symbol}")
            logger.info(f"  Date range: {df.index[0]} to {df.index[-1]}")

            # Calculate actual days
            actual_days = (df.index[-1] - df.index[0]).days
            actual_years = actual_days / 365.25

            logger.info(f"  Coverage: {actual_days} days ({actual_years:.1f} years)")

            if actual_years < 2.0:
                logger.warning(f"  ⚠️  Only {actual_years:.1f} years - need 2+ for robust validation!")
            else:
                logger.info(f"  ✅ Sufficient data for validation")

            return df
        else:
            logger.error(f"  ❌ Failed to fetch {symbol}")
            return None

    except Exception as e:
        logger.error(f"  ❌ Error fetching {symbol}: {e}")
        return None


async def fetch_all_pairs():
    """Fetch all pairs and save to CSV"""

    results = {}

    for base, quote, interval in PAIRS:
        symbol = f"{base}{quote}"

        # Check if already downloaded
        filename = DATA_DIR / f"{symbol}_{interval}.csv"

        if filename.exists():
            logger.info(f"Loading cached {symbol} from {filename}")
            df = pd.read_csv(filename, index_col=0, parse_dates=True)
            results[symbol] = df
            logger.info(f"  Loaded {len(df)} candles from cache")
            continue

        # Fetch from Binance
        df = await fetch_binance_data(base, quote, interval, days=1095)

        if df is not None:
            # Save to CSV
            df.to_csv(filename)
            logger.info(f"  Saved to {filename}")
            results[symbol] = df
        else:
            logger.warning(f"  Skipped {symbol} (no data)")

        # Rate limit
        await asyncio.sleep(0.5)

    return results


def validate_data_quality(results: dict):
    """Validate that we have sufficient data"""

    logger.info("\n" + "="*80)
    logger.info("DATA QUALITY VALIDATION")
    logger.info("="*80)

    min_years = 2.0
    all_passed = True

    for symbol, df in results.items():
        if df is None or len(df) == 0:
            logger.error(f"❌ {symbol}: NO DATA")
            all_passed = False
            continue

        # Calculate coverage
        actual_days = (df.index[-1] - df.index[0]).days
        actual_years = actual_days / 365.25

        # Check for gaps
        expected_candles = actual_days * 24  # 1h candles
        actual_candles = len(df)
        completeness = actual_candles / expected_candles if expected_candles > 0 else 0

        # Validate
        if actual_years >= min_years and completeness >= 0.95:
            logger.info(
                f"✅ {symbol:12s}: {actual_years:.1f} years, "
                f"{actual_candles} candles ({completeness:.1%} complete)"
            )
        else:
            logger.warning(
                f"⚠️  {symbol:12s}: {actual_years:.1f} years, "
                f"{actual_candles} candles ({completeness:.1%} complete) "
                f"{'- INSUFFICIENT!' if actual_years < min_years else ''}"
            )
            all_passed = False

    logger.info("="*80)

    if all_passed:
        logger.info("✅ ALL PAIRS HAVE SUFFICIENT DATA (2+ years)")
    else:
        logger.warning("⚠️  SOME PAIRS HAVE INSUFFICIENT DATA")

    return all_passed


async def main():
    """Main entry point"""

    logger.info("="*80)
    logger.info("MULTI-PAIR HISTORICAL DATA FETCHER")
    logger.info("="*80)
    logger.info(f"Fetching {len(PAIRS)} trading pairs")
    logger.info(f"Target: 3 years (1095 days) of 1h candles")
    logger.info(f"Data directory: {DATA_DIR}")
    logger.info("="*80 + "\n")

    # Fetch all pairs
    results = await fetch_all_pairs()

    logger.info(f"\nFetched {len(results)} pairs successfully")

    # Validate data quality
    validate_data_quality(results)

    logger.info("\n✅ Data fetch complete!")
    logger.info(f"Data saved to: {DATA_DIR}")
    logger.info("\nNext step: Run random window validation with:")
    logger.info("  python test_memory_on_real_data.py")


if __name__ == "__main__":
    asyncio.run(main())
