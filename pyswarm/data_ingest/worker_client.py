"""
Cloudflare Worker Client

Fetches historical data from deployed Cloudflare Worker.

Alternative to direct Binance API calls (useful when network restricted).
"""

import logging
from datetime import datetime

import httpx
from coinswarm.data_ingest.base import DataPoint

logger = logging.getLogger(__name__)


class WorkerClient:
    """
    Client for Cloudflare Worker data fetcher.

    Usage:
    1. Deploy Worker to Cloudflare
    2. Set WORKER_URL
    3. Fetch data through Worker (bypasses network restrictions)
    """

    def __init__(self, worker_url: str):
        """
        Initialize Worker client.

        Args:
            worker_url: URL of deployed Worker
                       (e.g., "https://coinswarm-data-fetcher.username.workers.dev")
        """
        self.worker_url = worker_url.rstrip('/')
        self.timeout = 30.0

    async def fetch_data(
        self,
        symbol: str,
        timeframe: str = "1h",
        days: int = 30,
        use_cache: bool = True
    ) -> list[DataPoint]:
        """
        Fetch historical data from Worker.

        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            timeframe: Candle interval (1m, 5m, 1h, etc.)
            days: Number of days of history
            use_cache: Use cached data if available

        Returns:
            List of DataPoint objects
        """

        endpoint = "/cached" if use_cache else "/fetch"
        url = f"{self.worker_url}{endpoint}"

        params = {
            "symbol": symbol,
            "timeframe": timeframe,
            "days": days
        }

        logger.info(f"Fetching {symbol} {timeframe} ({days} days) from Worker...")

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
                if "error" in data:
                    if use_cache and "No cached data" in data["error"]:
                        # Try fetching fresh data
                        logger.info("No cache, fetching fresh data...")
                        return await self.fetch_data(symbol, timeframe, days, use_cache=False)
                    else:
                        raise Exception(f"Worker error: {data['error']}")

                # Convert to DataPoint objects
                data_points = []

                for candle in data.get("data", []):
                    data_point = DataPoint(
                        source="worker",
                        symbol=symbol,
                        timeframe=timeframe,
                        timestamp=datetime.fromisoformat(candle["timestamp"].replace('Z', '+00:00')),
                        data={
                            "open": candle["open"],
                            "high": candle["high"],
                            "low": candle["low"],
                            "close": candle["close"],
                            "price": candle["close"],
                            "volume": candle["volume"]
                        },
                        quality_score=1.0
                    )

                    data_points.append(data_point)

                logger.info(f"Fetched {len(data_points)} candles from Worker")

                return data_points

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching from Worker: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching from Worker: {e}")
            raise


# Example usage
if __name__ == "__main__":
    import asyncio

    async def test():
        # Replace with your deployed Worker URL
        worker_url = "https://coinswarm-data-fetcher.your-subdomain.workers.dev"

        client = WorkerClient(worker_url)

        # Fetch BTC data
        data = await client.fetch_data("BTCUSDT", "1h", 30)

        print(f"Fetched {len(data)} candles")
        if data:
            print(f"First: {data[0].timestamp} - ${data[0].data['price']:.2f}")
            print(f"Last: {data[-1].timestamp} - ${data[-1].data['price']:.2f}")

    asyncio.run(test())
