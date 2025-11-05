"""
Historical Data Fetcher

Fetches comprehensive historical data for backtesting:
1. Spot pairs (BTC-USDC, SOL-USDC, ETH-USDC)
2. Cross pairs (BTC-SOL, ETH-BTC, ETH-SOL) for arbitrage
3. Historical news (CoinDesk, Cointelegraph)
4. Twitter/social sentiment
5. Macro trends (Fed rates, CPI, etc.)

Strategy: Random 1-month windows over 3-month period to avoid overfitting
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from random import randint
import aiohttp

from coinswarm.data_ingest.base import DataPoint
from coinswarm.data_ingest.binance_ingestor import BinanceIngestor


logger = logging.getLogger(__name__)


class HistoricalDataFetcher:
    """
    Comprehensive historical data fetcher for backtesting.

    Fetches:
    - Spot pairs (crypto/stablecoin)
    - Cross pairs (crypto/crypto) for arbitrage
    - Historical news and sentiment
    - Macro economic data
    """

    def __init__(self):
        self.binance = BinanceIngestor()

        # Trading pairs
        self.spot_pairs = [
            "BTC-USDC",
            "ETH-USDC",
            "SOL-USDC"
        ]

        self.cross_pairs = [
            "BTC-SOL",   # For triangular arbitrage
            "ETH-BTC",   # Common arb pair
            "ETH-SOL"    # Complete triangle
        ]

        # Map to Binance symbols (they use USDT not USDC)
        self.symbol_map = {
            "BTC-USDC": "BTCUSDT",
            "ETH-USDC": "ETHUSDT",
            "SOL-USDC": "SOLUSDT",
            "BTC-SOL": "BTCSOL",   # May not exist, will check
            "ETH-BTC": "ETHBTC",
            "ETH-SOL": "ETHSOL"    # May not exist
        }

    async def fetch_all_historical_data(
        self,
        months: int = 3,
        timeframe: str = "1m"
    ) -> Dict[str, List[DataPoint]]:
        """
        Fetch historical data for all pairs.

        Args:
            months: How many months of history
            timeframe: Candle interval (1m, 5m, 1h, etc.)

        Returns:
            Dict mapping symbol → list of DataPoints
        """

        end_date = datetime.now()
        start_date = end_date - timedelta(days=30 * months)

        logger.info(f"Fetching {months} months of historical data...")
        logger.info(f"Date range: {start_date} to {end_date}")
        logger.info(f"Timeframe: {timeframe}")

        all_data = {}

        # Fetch spot pairs in parallel
        logger.info("Fetching spot pairs (crypto/stablecoin)...")
        spot_tasks = [
            self._fetch_pair(pair, start_date, end_date, timeframe)
            for pair in self.spot_pairs
        ]
        spot_results = await asyncio.gather(*spot_tasks, return_exceptions=True)

        for pair, data in zip(self.spot_pairs, spot_results):
            if isinstance(data, Exception):
                logger.error(f"Failed to fetch {pair}: {data}")
            else:
                all_data[pair] = data
                logger.info(f"✓ {pair}: {len(data)} ticks")

        # Fetch cross pairs in parallel
        logger.info("Fetching cross pairs (crypto/crypto for arbitrage)...")
        cross_tasks = [
            self._fetch_pair(pair, start_date, end_date, timeframe)
            for pair in self.cross_pairs
        ]
        cross_results = await asyncio.gather(*cross_tasks, return_exceptions=True)

        for pair, data in zip(self.cross_pairs, cross_results):
            if isinstance(data, Exception):
                logger.warning(f"✗ {pair}: {data} (pair may not exist)")
            else:
                all_data[pair] = data
                logger.info(f"✓ {pair}: {len(data)} ticks")

        logger.info(f"Fetched data for {len(all_data)} pairs")

        return all_data

    async def _fetch_pair(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str
    ) -> List[DataPoint]:
        """Fetch data for a single pair"""

        try:
            # Map to Binance symbol
            binance_symbol = self.symbol_map.get(symbol, symbol)

            # Fetch OHLCV data
            data = await self.binance.fetch_ohlcv_range(
                symbol=binance_symbol,
                timeframe=timeframe,
                start_time=start_date,
                end_time=end_date
            )

            # Convert back to our symbol naming
            for point in data:
                point.symbol = symbol

            return data

        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
            raise

    def generate_random_windows(
        self,
        total_months: int = 3,
        window_size_days: int = 30,
        num_windows: int = 10
    ) -> List[Tuple[datetime, datetime]]:
        """
        Generate random 1-month windows over a 3-month period.

        This prevents overfitting to a specific market regime.

        Args:
            total_months: Total period to sample from
            window_size_days: Size of each window (30 = 1 month)
            num_windows: Number of random windows to generate

        Returns:
            List of (start_date, end_date) tuples
        """

        end_date = datetime.now()
        earliest_start = end_date - timedelta(days=30 * total_months)
        latest_start = end_date - timedelta(days=window_size_days)

        windows = []

        for i in range(num_windows):
            # Random start date within valid range
            days_offset = randint(0, (latest_start - earliest_start).days)
            start = earliest_start + timedelta(days=days_offset)
            end = start + timedelta(days=window_size_days)

            windows.append((start, end))

            logger.debug(f"Window {i+1}: {start.date()} to {end.date()}")

        logger.info(f"Generated {num_windows} random {window_size_days}-day windows")

        return windows

    async def fetch_window(
        self,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "1m"
    ) -> Dict[str, List[DataPoint]]:
        """
        Fetch data for a specific time window.

        Used for random window sampling.
        """

        logger.info(f"Fetching window: {start_date.date()} to {end_date.date()}")

        all_data = {}

        # Fetch all pairs for this window
        all_pairs = self.spot_pairs + self.cross_pairs

        tasks = [
            self._fetch_pair(pair, start_date, end_date, timeframe)
            for pair in all_pairs
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for pair, data in zip(all_pairs, results):
            if isinstance(data, Exception):
                logger.warning(f"✗ {pair}: {data}")
            else:
                all_data[pair] = data

        return all_data

    async def fetch_historical_news(
        self,
        start_date: datetime,
        end_date: datetime,
        sources: List[str] = None
    ) -> List[Dict]:
        """
        Fetch historical news articles.

        Sources:
        - CoinDesk API
        - Cointelegraph
        - CryptoSlate
        - Messari news

        Returns:
            List of news articles with timestamp, headline, sentiment
        """

        sources = sources or ["coindesk", "cointelegraph", "cryptoslate"]

        logger.info(f"Fetching historical news from {len(sources)} sources...")
        logger.info(f"Date range: {start_date.date()} to {end_date.date()}")

        news_articles = []

        # TODO: Implement actual news fetching
        # For now, return placeholder

        logger.warning("Historical news fetching not yet implemented")
        logger.info("Will use CoinDesk API, Cointelegraph, CryptoSlate")

        return news_articles

    async def fetch_historical_tweets(
        self,
        start_date: datetime,
        end_date: datetime,
        keywords: List[str] = None
    ) -> List[Dict]:
        """
        Fetch historical tweets about crypto.

        Keywords: BTC, Bitcoin, ETH, Ethereum, SOL, Solana, crypto

        Note: Twitter API has rate limits and costs for historical data.
        May need to use alternative sources or paid API.

        Returns:
            List of tweets with timestamp, text, sentiment, engagement
        """

        keywords = keywords or ["BTC", "Bitcoin", "ETH", "Ethereum", "SOL", "Solana"]

        logger.info(f"Fetching historical tweets for {len(keywords)} keywords...")
        logger.info(f"Date range: {start_date.date()} to {end_date.date()}")

        tweets = []

        # TODO: Implement actual Twitter fetching
        # Options:
        # 1. Twitter API v2 (paid for historical)
        # 2. Alternative data providers (Santiment, LunarCrush)
        # 3. Scraping (legal gray area)

        logger.warning("Historical tweet fetching not yet implemented")
        logger.info("Will need Twitter API v2 or alternative data provider")

        return tweets

    async def fetch_macro_trends(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, List[Dict]]:
        """
        Fetch macro economic data.

        Data sources:
        - FRED (Federal Reserve Economic Data) - free API
        - BLS (Bureau of Labor Statistics) - free
        - Yahoo Finance for stock indices

        Indicators:
        - Fed funds rate
        - CPI (inflation)
        - Unemployment rate
        - S&P 500
        - DXY (dollar index)
        - Gold price
        - 10Y treasury yield

        Returns:
            Dict mapping indicator → list of data points
        """

        logger.info("Fetching macro economic data...")
        logger.info(f"Date range: {start_date.date()} to {end_date.date()}")

        macro_data = {}

        indicators = [
            "FEDFUNDS",   # Fed funds rate
            "CPIAUCSL",   # CPI
            "UNRATE",     # Unemployment
            "SP500",      # S&P 500
            "DEXUSEU",    # Dollar index
            "GOLDAMGBD228NLBM",  # Gold
            "DGS10"       # 10Y treasury
        ]

        # TODO: Implement FRED API calls
        # FRED API is free: https://fred.stlouisfed.org/docs/api/fred/

        logger.warning("Macro data fetching not yet implemented")
        logger.info("Will use FRED API (free) for economic indicators")

        return macro_data

    async def fetch_onchain_data(
        self,
        start_date: datetime,
        end_date: datetime,
        metrics: List[str] = None
    ) -> Dict[str, List[Dict]]:
        """
        Fetch on-chain data.

        Sources:
        - Glassnode API (paid but has free tier)
        - CoinMetrics (paid)
        - Blockchain.com API (free for basic data)

        Metrics:
        - Active addresses
        - Transaction count
        - Exchange inflows/outflows
        - Whale movements
        - Miner balances
        - MVRV ratio

        Returns:
            Dict mapping metric → list of data points
        """

        metrics = metrics or [
            "active_addresses",
            "transaction_count",
            "exchange_flow",
            "whale_transactions"
        ]

        logger.info(f"Fetching on-chain data for {len(metrics)} metrics...")
        logger.info(f"Date range: {start_date.date()} to {end_date.date()}")

        onchain_data = {}

        # TODO: Implement Glassnode/CoinMetrics API calls

        logger.warning("On-chain data fetching not yet implemented")
        logger.info("Will use Glassnode free tier or Blockchain.com API")

        return onchain_data

    def get_max_available_history(self, symbol: str) -> datetime:
        """
        Get earliest available data for a symbol.

        Binance history:
        - BTC: 2017-08-17 (Binance launch)
        - ETH: 2017-08-17
        - SOL: 2020-08-11 (Serum DEX launch)

        Returns:
            Earliest datetime with data
        """

        # Approximate launch dates
        launch_dates = {
            "BTC-USDC": datetime(2017, 8, 17),
            "ETH-USDC": datetime(2017, 8, 17),
            "SOL-USDC": datetime(2020, 8, 11),
            "ETH-BTC": datetime(2017, 8, 17),
        }

        return launch_dates.get(symbol, datetime(2017, 8, 17))


async def demo_fetch():
    """Demo: Fetch historical data"""

    fetcher = HistoricalDataFetcher()

    # Fetch 3 months of data
    data = await fetcher.fetch_all_historical_data(months=3, timeframe="1m")

    print(f"\nFetched data for {len(data)} pairs:")
    for symbol, points in data.items():
        if points:
            print(f"  {symbol}: {len(points)} ticks")
            print(f"    First: {points[0].timestamp}")
            print(f"    Last:  {points[-1].timestamp}")

    # Generate random windows
    windows = fetcher.generate_random_windows(
        total_months=3,
        window_size_days=30,
        num_windows=10
    )

    print(f"\nGenerated {len(windows)} random 30-day windows")
    for i, (start, end) in enumerate(windows[:3], 1):
        print(f"  Window {i}: {start.date()} to {end.date()}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(demo_fetch())
