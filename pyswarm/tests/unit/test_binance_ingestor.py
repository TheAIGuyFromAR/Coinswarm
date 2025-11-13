"""
Unit tests for Binance Exchange Data Ingestor

Tests OHLCV fetching, WebSocket parsing, symbol normalization, and more.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from coinswarm.data_ingest.base import DataPoint
from coinswarm.data_ingest.exchanges.binance import BinanceIngestor


class TestBinanceInitialization:
    """Test Binance ingestor initialization"""

    def test_binance_init_without_keys(self):
        """Test Binance can initialize without API keys (public data)"""
        ingestor = BinanceIngestor()

        assert ingestor.source_name == "binance"
        assert ingestor.exchange is not None
        assert ingestor.ws_base_url == "wss://stream.binance.com:9443/stream"

    def test_binance_init_with_keys(self):
        """Test Binance can initialize with API keys"""
        ingestor = BinanceIngestor(api_key="test_key", api_secret="test_secret")

        assert ingestor.source_name == "binance"
        assert ingestor.exchange is not None

    def test_binance_logger_configured(self):
        """Test Binance logger is properly configured"""
        ingestor = BinanceIngestor()

        assert ingestor.logger is not None
        # Logger should be bound with source="binance"


class TestOHLCVFetching:
    """Test OHLCV (candlestick) data fetching"""

    @pytest.mark.asyncio
    async def test_fetch_historical_ohlcv(self):
        """Test fetching historical OHLCV data"""
        ingestor = BinanceIngestor()

        # Mock the exchange's fetch_ohlcv method
        with patch.object(ingestor.exchange, 'fetch_ohlcv', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = [
                [
                    1704110400000,  # timestamp (ms)
                    50000.0,  # open
                    50500.0,  # high
                    49800.0,  # low
                    50200.0,  # close
                    100.5,  # volume
                ]
            ]

            start = datetime(2025, 1, 1, 12, 0, 0)
            end = datetime(2025, 1, 1, 13, 0, 0)

            data_points = await ingestor.fetch_historical(
                symbol="BTC-USD", start=start, end=end, timeframe="1m"
            )

            assert len(data_points) == 1
            assert isinstance(data_points[0], DataPoint)
            assert data_points[0].source == "binance"
            assert data_points[0].symbol == "BTC-USD"
            assert data_points[0].data["open"] == 50000.0
            assert data_points[0].data["close"] == 50200.0

    @pytest.mark.asyncio
    async def test_fetch_historical_validates_ohlcv_quality(self):
        """Test that OHLCV data is validated for quality"""
        ingestor = BinanceIngestor()

        with patch.object(ingestor.exchange, 'fetch_ohlcv', new_callable=AsyncMock) as mock_fetch:
            # Valid OHLCV data
            mock_fetch.return_value = [
                [1704110400000, 50000.0, 50500.0, 49800.0, 50200.0, 100.5]
            ]

            start = datetime(2025, 1, 1, 12, 0, 0)
            end = datetime(2025, 1, 1, 13, 0, 0)

            data_points = await ingestor.fetch_historical(
                symbol="BTC-USD", start=start, end=end
            )

            # Quality score should be calculated
            assert 0.0 <= data_points[0].quality_score <= 1.0

    @pytest.mark.asyncio
    async def test_fetch_historical_handles_empty_response(self):
        """Test that empty OHLCV response is handled gracefully"""
        ingestor = BinanceIngestor()

        with patch.object(ingestor.exchange, 'fetch_ohlcv', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = []

            start = datetime(2025, 1, 1, 12, 0, 0)
            end = datetime(2025, 1, 1, 13, 0, 0)

            data_points = await ingestor.fetch_historical(
                symbol="BTC-USD", start=start, end=end
            )

            assert data_points == []


class TestWebSocketParsing:
    """Test WebSocket data parsing"""

    def test_parse_trade_data(self):
        """Test parsing WebSocket trade data"""
        ingestor = BinanceIngestor()

        trade_data = {
            "s": "BTCUSDT",  # Symbol
            "t": 12345,  # Trade ID
            "p": "50000.00",  # Price
            "q": "0.5",  # Quantity
            "T": 1704110400000,  # Timestamp
            "m": False,  # Is buyer maker
        }

        symbols = ["BTC-USD"]
        data_point = ingestor._parse_trade(trade_data, symbols)

        assert isinstance(data_point, DataPoint)
        assert data_point.source == "binance"
        assert data_point.timeframe == "tick"
        assert data_point.data["trade_id"] == 12345
        assert data_point.data["price"] == 50000.00
        assert data_point.data["quantity"] == 0.5

    def test_parse_orderbook_data(self):
        """Test parsing WebSocket orderbook data"""
        ingestor = BinanceIngestor()

        orderbook_data = {
            "s": "BTCUSDT",
            "E": 1704110400000,  # Event time
            "b": [["50000", "1.5"], ["49999", "2.0"]],  # Bids
            "a": [["50001", "1.0"], ["50002", "1.5"]],  # Asks
        }

        symbols = ["BTC-USD"]
        data_point = ingestor._parse_orderbook(orderbook_data, symbols)

        assert isinstance(data_point, DataPoint)
        assert data_point.timeframe == "snapshot"
        assert len(data_point.data["bids"]) == 2
        assert len(data_point.data["asks"]) == 2
        assert data_point.data["bids"][0][0] == 50000.0  # Best bid price
        assert data_point.data["asks"][0][0] == 50001.0  # Best ask price

    def test_parse_kline_data(self):
        """Test parsing WebSocket kline (candlestick) data"""
        ingestor = BinanceIngestor()

        kline_data = {
            "s": "BTCUSDT",
            "k": {
                "t": 1704110400000,  # Kline start time
                "i": "1m",  # Interval
                "o": "50000.00",  # Open
                "h": "50500.00",  # High
                "l": "49800.00",  # Low
                "c": "50200.00",  # Close
                "v": "100.5",  # Volume
                "x": True,  # Is closed
            },
        }

        symbols = ["BTC-USD"]
        data_point = ingestor._parse_kline(kline_data, symbols)

        assert isinstance(data_point, DataPoint)
        assert data_point.timeframe == "1m"
        assert data_point.data["open"] == 50000.0
        assert data_point.data["close"] == 50200.0
        assert data_point.data["is_closed"] is True


class TestSymbolNormalization:
    """Test symbol normalization between formats"""

    def test_normalize_symbol_btcusdt_to_btc_usd(self):
        """Test normalizing BTCUSDT to BTC-USD"""
        ingestor = BinanceIngestor()

        raw_symbol = "BTCUSDT"
        known_symbols = ["BTC-USD", "ETH-USD"]

        normalized = ingestor._normalize_symbol_from_binance(raw_symbol, known_symbols)

        assert normalized == "BTC-USD"

    def test_normalize_symbol_fallback(self):
        """Test symbol normalization fallback for unknown symbols"""
        ingestor = BinanceIngestor()

        raw_symbol = "UNKNOWNPAIR"
        known_symbols = ["BTC-USD"]

        # Should fall back to inserting hyphen
        normalized = ingestor._normalize_symbol_from_binance(raw_symbol, known_symbols)

        assert isinstance(normalized, str)

    def test_normalize_symbol_with_base_quote_split(self):
        """Test symbol normalization with explicit base/quote split"""
        ingestor = BinanceIngestor()

        raw_symbol = "ETHUSDT"
        known_symbols = ["BTC-USD", "ETH-USD"]

        normalized = ingestor._normalize_symbol_from_binance(raw_symbol, known_symbols)

        assert normalized == "ETH-USD"


class TestFundingRates:
    """Test funding rate fetching for perpetual futures"""

    @pytest.mark.asyncio
    async def test_get_funding_rates_returns_float(self):
        """Test that funding rates return float or None"""
        ingestor = BinanceIngestor()

        with patch.object(ingestor.exchange, 'fetch_ticker', new_callable=AsyncMock) as mock_ticker:
            mock_ticker.return_value = {
                "info": {"fundingRate": "0.0001"}
            }

            funding_rate = await ingestor.get_funding_rates("BTC-USD")

            assert funding_rate == 0.0001

    @pytest.mark.asyncio
    async def test_get_funding_rates_handles_missing_data(self):
        """Test that missing funding rates return None"""
        ingestor = BinanceIngestor()

        with patch.object(ingestor.exchange, 'fetch_ticker', new_callable=AsyncMock) as mock_ticker:
            mock_ticker.return_value = {"info": {}}  # No funding rate

            funding_rate = await ingestor.get_funding_rates("BTC-USD")

            assert funding_rate is None


class TestOrderbookSnapshot:
    """Test order book snapshot fetching"""

    @pytest.mark.asyncio
    async def test_get_orderbook_snapshot(self):
        """Test fetching orderbook snapshot"""
        ingestor = BinanceIngestor()

        with patch.object(ingestor.exchange, 'fetch_order_book', new_callable=AsyncMock) as mock_ob:
            mock_ob.return_value = {
                "bids": [[50000, 1.5], [49999, 2.0]],
                "asks": [[50001, 1.0], [50002, 1.5]],
            }

            orderbook = await ingestor.get_orderbook("BTC-USD", depth=20)

            assert orderbook["symbol"] == "BTC-USD"
            assert len(orderbook["bids"]) == 2
            assert len(orderbook["asks"]) == 2
            assert orderbook["spread"] == 1.0  # 50001 - 50000

    @pytest.mark.asyncio
    async def test_get_orderbook_calculates_spread(self):
        """Test that orderbook spread is calculated correctly"""
        ingestor = BinanceIngestor()

        with patch.object(ingestor.exchange, 'fetch_order_book', new_callable=AsyncMock) as mock_ob:
            mock_ob.return_value = {
                "bids": [[50000, 1.5]],
                "asks": [[50010, 1.0]],
            }

            orderbook = await ingestor.get_orderbook("BTC-USD")

            assert orderbook["spread"] == 10.0  # 50010 - 50000


class TestProductsListing:
    """Test products/markets listing"""

    @pytest.mark.asyncio
    async def test_get_products_returns_list(self):
        """Test that get_products returns list of products"""
        ingestor = BinanceIngestor()

        with patch.object(ingestor.exchange, 'load_markets', new_callable=AsyncMock) as mock_markets:
            mock_markets.return_value = {
                "BTC/USD": {
                    "base": "BTC",
                    "quote": "USD",
                    "active": True,
                    "type": "spot",
                },
                "ETH/USD": {
                    "base": "ETH",
                    "quote": "USD",
                    "active": True,
                    "type": "spot",
                },
            }

            products = await ingestor.get_products()

            assert len(products) == 2
            assert products[0]["base"] == "BTC"
            assert products[1]["base"] == "ETH"

    @pytest.mark.asyncio
    async def test_get_products_normalizes_symbols(self):
        """Test that get_products normalizes symbol format"""
        ingestor = BinanceIngestor()

        with patch.object(ingestor.exchange, 'load_markets', new_callable=AsyncMock) as mock_markets:
            mock_markets.return_value = {
                "BTC/USD": {
                    "base": "BTC",
                    "quote": "USD",
                    "active": True,
                    "type": "spot",
                }
            }

            products = await ingestor.get_products()

            # Symbol should be normalized to BTC-USD
            assert "BTC-USD" in products[0]["symbol"]


class TestHealthCheck:
    """Test Binance health check"""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test health check returns True when API is accessible"""
        ingestor = BinanceIngestor()

        with patch.object(ingestor.exchange, 'fetch_status', new_callable=AsyncMock) as mock_status:
            mock_status.return_value = {"status": "ok"}

            health = await ingestor.health_check()

            assert health is True
            assert ingestor._is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check returns False when API is unreachable"""
        ingestor = BinanceIngestor()

        with patch.object(ingestor.exchange, 'fetch_status', new_callable=AsyncMock) as mock_status:
            mock_status.side_effect = Exception("API Unreachable")

            health = await ingestor.health_check()

            assert health is False
            assert ingestor._is_healthy is False
