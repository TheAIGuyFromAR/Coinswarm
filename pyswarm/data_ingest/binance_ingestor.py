"""
Binance Data Ingestor

Fetches historical and live data from Binance using ccxt library.

Public API (no credentials needed for historical data)
"""

import asyncio
import logging
from datetime import datetime, timedelta

try:
    import ccxt.async_support as ccxt
except ImportError:
    import ccxt

from coinswarm.data_ingest.base import DataPoint

logger = logging.getLogger(__name__)


class BinanceIngestor:
    """
    Binance data ingestor using ccxt.

    Can fetch:
    - Historical OHLCV data
    - Real-time ticker data
    - Order book data
    """

    def __init__(self):
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
            }
        })

        self.source_name = "binance"

    async def fetch_ohlcv_range(
        self,
        symbol: str,
        timeframe: str = "1m",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 1000
    ) -> list[DataPoint]:
        """
        Fetch OHLCV data for a date range.

        Args:
            symbol: Trading pair (e.g., "BTCUSDT", "ETHUSDT")
            timeframe: Candle interval (1m, 5m, 15m, 1h, 4h, 1d)
            start_time: Start datetime
            end_time: End datetime
            limit: Max candles per request (Binance max = 1000)

        Returns:
            List of DataPoint objects
        """

        if not start_time:
            start_time = datetime.now() - timedelta(days=30)

        if not end_time:
            end_time = datetime.now()

        logger.info(f"Fetching {symbol} {timeframe} from {start_time.date()} to {end_time.date()}")

        all_data = []
        current_start = start_time

        # Fetch in chunks (Binance limit = 1000 candles per request)
        while current_start < end_time:
            try:
                # Convert to milliseconds
                since = int(current_start.timestamp() * 1000)

                # Fetch OHLCV
                ohlcv = await self.exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    since=since,
                    limit=limit
                )

                if not ohlcv:
                    break

                # Convert to DataPoint objects
                for candle in ohlcv:
                    timestamp_ms, open_, high, low, close, volume = candle

                    data_point = DataPoint(
                        source=self.source_name,
                        symbol=symbol,
                        timeframe=timeframe,
                        timestamp=datetime.fromtimestamp(timestamp_ms / 1000),
                        data={
                            "open": open_,
                            "high": high,
                            "low": low,
                            "close": close,
                            "price": close,  # Use close as price
                            "volume": volume
                        },
                        quality_score=1.0
                    )

                    # Only add if within range
                    if start_time <= data_point.timestamp <= end_time:
                        all_data.append(data_point)

                # Move to next chunk
                if ohlcv:
                    last_timestamp = datetime.fromtimestamp(ohlcv[-1][0] / 1000)
                    current_start = last_timestamp + timedelta(minutes=1)
                else:
                    break

                # Rate limiting
                await asyncio.sleep(self.exchange.rateLimit / 1000)

            except Exception as e:
                logger.error(f"Error fetching {symbol}: {e}")
                break

        logger.info(f"Fetched {len(all_data)} candles for {symbol}")

        return all_data

    async def close(self):
        """Close exchange connection"""
        await self.exchange.close()
