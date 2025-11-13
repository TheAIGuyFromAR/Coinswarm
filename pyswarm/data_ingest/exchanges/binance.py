"""
Binance Exchange Data Ingestor

Implements real-time and historical data ingestion from Binance.
"""

import json
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

import ccxt.async_support as ccxt
import websockets
from coinswarm.data_ingest.base import (
    DataPoint,
    ExchangeDataSource,
    SourceMetadata,
    StreamType,
)


class BinanceIngestor(ExchangeDataSource):
    """
    Binance exchange data ingestor.

    Supports:
    - REST API for historical OHLCV, trades, funding rates
    - WebSocket for real-time trades, order book, klines
    """

    def __init__(self, api_key: str | None = None, api_secret: str | None = None):
        super().__init__("binance")

        # Initialize CCXT client for REST API
        self.exchange = ccxt.binance({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
        })

        # WebSocket base URL
        self.ws_base_url = "wss://stream.binance.com:9443/stream"

    async def fetch_historical(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: str = "1m",
        **kwargs,
    ) -> list[DataPoint]:
        """
        Fetch historical OHLCV data from Binance.

        Args:
            symbol: Symbol in BASE-QUOTE format (e.g., "BTC-USD")
            start: Start datetime
            end: End datetime
            timeframe: Candlestick timeframe ("1m", "5m", "1h", etc.)

        Returns:
            List of DataPoint objects with OHLCV data
        """
        try:
            # Convert symbol to Binance format (BTC-USD → BTC/USD)
            binance_symbol = symbol.replace("-", "/")

            # Fetch OHLCV data
            since = int(start.timestamp() * 1000)  # Convert to milliseconds
            ohlcv_data = await self.exchange.fetch_ohlcv(
                binance_symbol, timeframe=timeframe, since=since
            )

            # Convert to DataPoint objects
            data_points = []
            for candle in ohlcv_data:
                timestamp_ms, open_price, high, low, close, volume = candle

                # Skip if beyond end time
                candle_time = datetime.fromtimestamp(timestamp_ms / 1000)
                if candle_time > end:
                    break

                data_points.append(
                    DataPoint(
                        source="binance",
                        symbol=symbol,
                        timeframe=timeframe,
                        timestamp=candle_time,
                        data={
                            "open": open_price,
                            "high": high,
                            "low": low,
                            "close": close,
                            "volume": volume,
                        },
                        quality_score=self._calculate_ohlcv_quality(
                            open_price, high, low, close, volume
                        ),
                        version="v1",
                    )
                )

            self.logger.info(
                "fetched_historical",
                symbol=symbol,
                timeframe=timeframe,
                count=len(data_points),
            )

            return data_points

        except Exception as e:
            self.logger.error("fetch_historical_error", symbol=symbol, error=str(e))
            raise

    async def stream_realtime(
        self,
        symbols: list[str],
        stream_types: list[StreamType] = None,
        **kwargs,
    ) -> AsyncIterator[DataPoint]:
        """
        Stream real-time data from Binance WebSocket.

        Args:
            symbols: List of symbols (e.g., ["BTC-USD", "ETH-USD"])
            stream_types: Types of streams to subscribe to

        Yields:
            DataPoint objects as they arrive
        """
        # Convert symbols to Binance format and lowercase
        if stream_types is None:
            stream_types = [StreamType.TRADE]
        binance_symbols = [s.replace("-", "").lower() for s in symbols]

        # Build stream subscriptions
        stream_names = {
            StreamType.TRADE: "trade",
            StreamType.ORDERBOOK: "depth@100ms",
            StreamType.TICKER: "ticker",
            StreamType.KLINE: "kline_1m",
        }

        subscriptions = [
            f"{sym}@{stream_names[stream_type]}"
            for sym in binance_symbols
            for stream_type in stream_types
        ]

        ws_url = f"{self.ws_base_url}?streams={'/'.join(subscriptions)}"

        self.logger.info("starting_websocket", url=ws_url, streams=subscriptions)

        try:
            async with websockets.connect(ws_url) as ws:
                async for message in ws:
                    data = json.loads(message)

                    if "stream" not in data:
                        continue

                    stream_name = data["stream"]
                    stream_data = data["data"]

                    # Parse based on stream type
                    if "trade" in stream_name:
                        yield self._parse_trade(stream_data, symbols)
                    elif "depth" in stream_name:
                        yield self._parse_orderbook(stream_data, symbols)
                    elif "ticker" in stream_name:
                        yield self._parse_ticker(stream_data, symbols)
                    elif "kline" in stream_name:
                        yield self._parse_kline(stream_data, symbols)

        except Exception as e:
            self.logger.error("websocket_error", error=str(e))
            raise

    async def get_products(self) -> list[dict[str, Any]]:
        """Get list of tradable products from Binance"""
        try:
            markets = await self.exchange.load_markets()
            return [
                {
                    "symbol": self._normalize_symbol(symbol),
                    "base": market["base"],
                    "quote": market["quote"],
                    "active": market["active"],
                    "type": market.get("type", "spot"),
                }
                for symbol, market in markets.items()
            ]
        except Exception as e:
            self.logger.error("get_products_error", error=str(e))
            raise

    async def get_funding_rates(self, symbol: str) -> float | None:
        """
        Get current funding rate for a perpetual futures contract.

        Args:
            symbol: Symbol (e.g., "BTC-USD")

        Returns:
            Current funding rate (annualized), or None if not applicable
        """
        try:
            binance_symbol = symbol.replace("-", "/")
            ticker = await self.exchange.fetch_ticker(binance_symbol)

            # Funding rate is in the info dict for futures
            if "fundingRate" in ticker.get("info", {}):
                return float(ticker["info"]["fundingRate"])

            return None

        except Exception as e:
            self.logger.error("get_funding_rates_error", symbol=symbol, error=str(e))
            return None

    async def get_orderbook(
        self, symbol: str, depth: int = 20
    ) -> dict[str, Any]:
        """
        Get current order book snapshot.

        Args:
            symbol: Symbol (e.g., "BTC-USD")
            depth: Number of levels to fetch

        Returns:
            Order book with bids and asks
        """
        try:
            binance_symbol = symbol.replace("-", "/")
            orderbook = await self.exchange.fetch_order_book(binance_symbol, limit=depth)

            return {
                "symbol": symbol,
                "timestamp": datetime.now(),
                "bids": orderbook["bids"][:depth],  # [[price, size], ...]
                "asks": orderbook["asks"][:depth],
                "spread": orderbook["asks"][0][0] - orderbook["bids"][0][0]
                if orderbook["asks"] and orderbook["bids"]
                else 0,
            }

        except Exception as e:
            self.logger.error("get_orderbook_error", symbol=symbol, error=str(e))
            raise

    async def health_check(self) -> bool:
        """Check if Binance API is accessible"""
        try:
            await self.exchange.fetch_status()
            self._is_healthy = True
            return True
        except Exception as e:
            self.logger.error("health_check_failed", error=str(e))
            self._is_healthy = False
            return False

    async def get_metadata(self) -> SourceMetadata:
        """Get metadata about Binance data source"""
        return SourceMetadata(
            name="binance",
            domain="exchanges",
            description="Binance cryptocurrency exchange - spot and futures trading",
            update_frequency="real-time",
            rate_limits={"requests_per_minute": 2400, "websocket_connections": 300},
            available_symbols=["BTC-USD", "ETH-USD", "BNB-USD"],  # Subset for demo
            available_timeframes=["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d"],
            supported_streams=["trade", "depth", "ticker", "kline", "funding"],
            quality_sla=0.99,
        )

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _parse_trade(self, data: dict[str, Any], symbols: list[str]) -> DataPoint:
        """Parse trade data from WebSocket"""
        raw_symbol = data["s"]  # e.g., "BTCUSDT"
        symbol = self._normalize_symbol_from_binance(raw_symbol, symbols)

        return DataPoint(
            source="binance",
            symbol=symbol,
            timeframe="tick",
            timestamp=datetime.fromtimestamp(data["T"] / 1000),
            data={
                "trade_id": data["t"],
                "price": float(data["p"]),
                "quantity": float(data["q"]),
                "side": "buy" if data["m"] is False else "sell",  # m=true means market maker
                "is_buyer_maker": data["m"],
            },
            quality_score=1.0,
            version="v1",
        )

    def _parse_orderbook(self, data: dict[str, Any], symbols: list[str]) -> DataPoint:
        """Parse order book data from WebSocket"""
        raw_symbol = data["s"]
        symbol = self._normalize_symbol_from_binance(raw_symbol, symbols)

        bids = [[float(p), float(q)] for p, q in data["b"]]
        asks = [[float(p), float(q)] for p, q in data["a"]]

        return DataPoint(
            source="binance",
            symbol=symbol,
            timeframe="snapshot",
            timestamp=datetime.fromtimestamp(data["E"] / 1000),
            data={
                "bids": bids,
                "asks": asks,
                "spread": asks[0][0] - bids[0][0] if bids and asks else 0,
                "bid_volume": sum(q for _, q in bids),
                "ask_volume": sum(q for _, q in asks),
                "imbalance": (sum(q for _, q in bids) - sum(q for _, q in asks))
                / (sum(q for _, q in bids) + sum(q for _, q in asks))
                if bids and asks
                else 0,
            },
            quality_score=1.0,
            version="v1",
        )

    def _parse_ticker(self, data: dict[str, Any], symbols: list[str]) -> DataPoint:
        """Parse ticker data from WebSocket"""
        raw_symbol = data["s"]
        symbol = self._normalize_symbol_from_binance(raw_symbol, symbols)

        return DataPoint(
            source="binance",
            symbol=symbol,
            timeframe="24h",
            timestamp=datetime.fromtimestamp(data["E"] / 1000),
            data={
                "last_price": float(data["c"]),
                "price_change": float(data["p"]),
                "price_change_percent": float(data["P"]),
                "volume": float(data["v"]),
                "high": float(data["h"]),
                "low": float(data["l"]),
                "bid": float(data["b"]),
                "ask": float(data["a"]),
            },
            quality_score=1.0,
            version="v1",
        )

    def _parse_kline(self, data: dict[str, Any], symbols: list[str]) -> DataPoint:
        """Parse kline (candlestick) data from WebSocket"""
        raw_symbol = data["s"]
        symbol = self._normalize_symbol_from_binance(raw_symbol, symbols)
        kline = data["k"]

        return DataPoint(
            source="binance",
            symbol=symbol,
            timeframe=kline["i"],  # e.g., "1m"
            timestamp=datetime.fromtimestamp(kline["t"] / 1000),
            data={
                "open": float(kline["o"]),
                "high": float(kline["h"]),
                "low": float(kline["l"]),
                "close": float(kline["c"]),
                "volume": float(kline["v"]),
                "is_closed": kline["x"],  # Is this kline closed?
            },
            quality_score=1.0,
            version="v1",
        )

    def _normalize_symbol_from_binance(
        self, raw_symbol: str, known_symbols: list[str]
    ) -> str:
        """
        Normalize Binance symbol to standard format.

        Args:
            raw_symbol: Raw Binance symbol (e.g., "BTCUSDT")
            known_symbols: List of known symbols to match against

        Returns:
            Normalized symbol (e.g., "BTC-USD")
        """
        # Convert BTCUSDT → BTC-USD
        # This is a simplified version; production would use exchange metadata
        for symbol in known_symbols:
            base, quote = symbol.split("-")
            if raw_symbol == f"{base}{quote}T":  # Handle USDT
                return f"{base}-USD"
            if raw_symbol == f"{base}{quote}":
                return symbol

        # Fallback: insert hyphen before last 3-4 chars
        if len(raw_symbol) > 6:
            return f"{raw_symbol[:-4]}-{raw_symbol[-4:]}"
        return raw_symbol

    def _calculate_ohlcv_quality(
        self, open_price: float, high: float, low: float, close: float, volume: float
    ) -> float:
        """
        Calculate quality score for OHLCV data.

        Checks for:
        - High >= Low
        - High >= Open, Close
        - Low <= Open, Close
        - Volume >= 0

        Returns:
            Quality score (1.0 if all checks pass, lower otherwise)
        """
        score = 1.0

        # High should be >= all other prices
        if high < low or high < open_price or high < close:
            score -= 0.5

        # Low should be <= all other prices
        if low > high or low > open_price or low > close:
            score -= 0.5

        # Volume should be non-negative
        if volume < 0:
            score -= 0.5

        return max(0.0, score)

    async def close(self):
        """Close exchange connection"""
        await self.exchange.close()
