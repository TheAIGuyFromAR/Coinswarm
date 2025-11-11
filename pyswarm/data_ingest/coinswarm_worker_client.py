"""
Coinswarm Worker Client

Fetches real historical data from the deployed Coinswarm Worker.
Worker aggregates data from multiple sources (Kraken, Coinbase, etc.)
"""

import logging
import httpx
from datetime import datetime
from typing import List, Optional

from coinswarm.data_ingest.base import DataPoint


logger = logging.getLogger(__name__)


class CoinswarmWorkerClient:
    """
    Client for Coinswarm multi-provider data fetcher Worker.

    Worker URL: https://coinswarm.bamn86.workers.dev

    API Endpoints:
    - /price?symbol=BTC&days=7&aggregate=true
    - /defi?protocol=aave
    - /oracle?symbol=SOL&source=pyth
    """

    def __init__(self, worker_url: str = "https://coinswarm.bamn86.workers.dev"):
        """
        Initialize Worker client.

        Args:
            worker_url: URL of deployed Worker
        """
        self.worker_url = worker_url.rstrip('/')
        self.timeout = 30.0

    async def fetch_price_data(
        self,
        symbol: str,
        days: int = 30,
        aggregate: bool = True
    ) -> List[DataPoint]:
        """
        Fetch historical price data from Worker.

        Args:
            symbol: Cryptocurrency symbol (e.g., "BTC", "ETH", "SOL")
            days: Number of days of history (1-365)
            aggregate: Aggregate from multiple exchanges

        Returns:
            List of DataPoint objects with hourly price data
        """

        url = f"{self.worker_url}/price"
        params = {
            "symbol": symbol,
            "days": days,
            "aggregate": "true" if aggregate else "false"
        }

        logger.info(f"Fetching {symbol} for {days} days from Worker...")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    params=params,
                    timeout=self.timeout
                )

                response.raise_for_status()
                data = response.json()

                # Check for errors
                if not data.get("success"):
                    raise Exception(f"Worker error: {data.get('error', 'Unknown error')}")

                # Convert to DataPoint objects
                data_points = []

                for candle in data.get("data", []):
                    data_point = DataPoint(
                        source="coinswarm_worker",
                        symbol=f"{symbol}-USD",
                        timeframe="1h",
                        timestamp=datetime.fromisoformat(candle["timestamp"].replace('Z', '+00:00')),
                        data={
                            "open": candle.get("minPrice", candle["price"]),  # Use min as proxy for open
                            "high": candle.get("maxPrice", candle["price"]),
                            "low": candle.get("minPrice", candle["price"]),
                            "close": candle["price"],
                            "price": candle["price"],
                            "volume": candle.get("volume", 0),
                            "data_points": candle.get("dataPoints", 1),  # Number of exchanges
                            "variance": candle.get("priceVariance", 0)
                        },
                        quality_score=1.0
                    )

                    data_points.append(data_point)

                logger.info(f"Fetched {len(data_points)} candles for {symbol}")
                logger.info(f"  Price range: ${data['firstPrice']:,.2f} → ${data['lastPrice']:,.2f}")
                logger.info(f"  Change: {data['priceChange']}")
                logger.info(f"  Providers: {', '.join(data.get('providersUsed', []))}")

                return data_points

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching from Worker: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching from Worker: {e}")
            raise

    async def fetch_multiple_symbols(
        self,
        symbols: List[str],
        days: int = 30
    ) -> dict:
        """
        Fetch data for multiple symbols.

        Args:
            symbols: List of symbols (e.g., ["BTC", "ETH", "SOL"])
            days: Days of history

        Returns:
            Dictionary mapping symbol to list of DataPoints
        """

        results = {}

        for symbol in symbols:
            try:
                data = await self.fetch_price_data(symbol, days)
                results[f"{symbol}-USD"] = data
            except Exception as e:
                logger.error(f"Failed to fetch {symbol}: {e}")
                results[f"{symbol}-USD"] = []

        return results


# Example usage
if __name__ == "__main__":
    import asyncio

    async def test():
        client = CoinswarmWorkerClient()

        # Fetch BTC data
        print("\nFetching 7 days of BTC data...")
        btc_data = await client.fetch_price_data("BTC", 7)

        print(f"\nFetched {len(btc_data)} hourly candles")
        if btc_data:
            print(f"First: {btc_data[0].timestamp} - ${btc_data[0].data['price']:,.2f}")
            print(f"Last:  {btc_data[-1].timestamp} - ${btc_data[-1].data['price']:,.2f}")

            # Calculate return
            start_price = btc_data[0].data['price']
            end_price = btc_data[-1].data['price']
            return_pct = ((end_price - start_price) / start_price) * 100
            print(f"Return: {return_pct:+.2f}%")

        # Fetch multiple symbols
        print("\n" + "="*70)
        print("Fetching multiple symbols...")
        all_data = await client.fetch_multiple_symbols(["BTC", "ETH", "SOL"], days=7)

        for symbol, data in all_data.items():
            if data:
                start = data[0].data['price']
                end = data[-1].data['price']
                ret = ((end - start) / start) * 100
                print(f"{symbol:8} {len(data):3} candles | ${start:>10,.2f} → ${end:>10,.2f} | {ret:+6.2f}%")

    asyncio.run(test())
