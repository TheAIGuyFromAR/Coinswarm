"""
Unit tests for Data Ingest Base Classes

Tests DataPoint, SourceMetadata, DataSource, and related functionality.
"""

from datetime import datetime

import pytest
from coinswarm.data_ingest.base import (
    DataDomain,
    DataPoint,
    DataSource,
    SourceMetadata,
    StreamType,
)


class TestDataPointCreation:
    """Test DataPoint creation and serialization"""

    def test_datapoint_basic_creation(self):
        """Test creating a basic DataPoint"""
        dp = DataPoint(
            source="binance",
            symbol="BTC-USD",
            timeframe="1m",
            timestamp=datetime(2025, 1, 1, 12, 0, 0),
            data={"open": 50000, "close": 50100, "volume": 10.5},
        )

        assert dp.source == "binance"
        assert dp.symbol == "BTC-USD"
        assert dp.timeframe == "1m"
        assert dp.data["open"] == 50000
        assert dp.quality_score == 1.0  # Default
        assert dp.version == "v1"  # Default

    def test_datapoint_to_dict(self):
        """Test DataPoint serialization to dictionary"""
        dp = DataPoint(
            source="binance",
            symbol="BTC-USD",
            timeframe="1m",
            timestamp=datetime(2025, 1, 1, 12, 0, 0),
            data={"price": 50000},
            quality_score=0.95,
        )

        d = dp.to_dict()

        assert d["source"] == "binance"
        assert d["symbol"] == "BTC-USD"
        assert d["timeframe"] == "1m"
        assert d["quality_score"] == 0.95
        assert "2025-01-01" in d["timestamp"]

    def test_datapoint_from_dict(self):
        """Test DataPoint deserialization from dictionary"""
        d = {
            "source": "binance",
            "symbol": "ETH-USD",
            "timeframe": "5m",
            "timestamp": "2025-01-01T12:00:00",
            "data": {"price": 3000},
            "quality_score": 0.99,
            "version": "v1",
            "metadata": {"exchange": "binance"},
        }

        dp = DataPoint.from_dict(d)

        assert dp.source == "binance"
        assert dp.symbol == "ETH-USD"
        assert dp.quality_score == 0.99
        assert dp.metadata["exchange"] == "binance"

    def test_datapoint_quality_score_range(self):
        """Test DataPoint quality_score is within valid range"""
        dp_perfect = DataPoint(
            source="test",
            symbol="BTC-USD",
            timeframe="1m",
            timestamp=datetime.now(),
            data={},
            quality_score=1.0,
        )

        dp_poor = DataPoint(
            source="test",
            symbol="BTC-USD",
            timeframe="1m",
            timestamp=datetime.now(),
            data={},
            quality_score=0.5,
        )

        assert 0.0 <= dp_perfect.quality_score <= 1.0
        assert 0.0 <= dp_poor.quality_score <= 1.0


class TestDataSourceAbstractMethods:
    """Test DataSource abstract base class"""

    @pytest.mark.asyncio
    async def test_datasource_cannot_be_instantiated(self):
        """Test that DataSource cannot be instantiated directly"""
        # This should raise TypeError since DataSource is abstract
        with pytest.raises(TypeError):
            DataSource("test", DataDomain.EXCHANGES)

    @pytest.mark.asyncio
    async def test_datasource_subclass_must_implement_methods(self):
        """Test that DataSource subclass must implement abstract methods"""

        # Incomplete implementation (missing abstract methods)
        class IncompleteSource(DataSource):
            pass

        with pytest.raises(TypeError):
            IncompleteSource("incomplete", DataDomain.EXCHANGES)

    @pytest.mark.asyncio
    async def test_datasource_complete_implementation(self):
        """Test that complete DataSource implementation works"""

        class CompleteSource(DataSource):
            async def fetch_historical(self, symbol, start, end, timeframe="1m", **kwargs):
                return []

            async def stream_realtime(self, symbols, **kwargs):
                yield DataPoint(
                    source="test",
                    symbol="BTC-USD",
                    timeframe="tick",
                    timestamp=datetime.now(),
                    data={},
                )

            async def health_check(self):
                return True

            async def get_metadata(self):
                return SourceMetadata(
                    name="test",
                    domain=DataDomain.EXCHANGES,
                    description="Test source",
                    update_frequency="real-time",
                    rate_limits={},
                    available_symbols=[],
                    available_timeframes=[],
                    supported_streams=[],
                    quality_sla=0.99,
                )

        source = CompleteSource("complete", DataDomain.EXCHANGES)
        assert source.source_name == "complete"
        assert source.domain == DataDomain.EXCHANGES
        assert await source.is_healthy() is True


class TestSourceMetadata:
    """Test SourceMetadata dataclass"""

    def test_source_metadata_creation(self):
        """Test creating SourceMetadata"""
        metadata = SourceMetadata(
            name="binance",
            domain=DataDomain.EXCHANGES,
            description="Binance cryptocurrency exchange",
            update_frequency="real-time",
            rate_limits={"requests_per_minute": 2400},
            available_symbols=["BTC-USD", "ETH-USD"],
            available_timeframes=["1m", "5m", "1h"],
            supported_streams=["trade", "orderbook"],
            quality_sla=0.99,
        )

        assert metadata.name == "binance"
        assert metadata.domain == DataDomain.EXCHANGES
        assert metadata.quality_sla == 0.99
        assert "BTC-USD" in metadata.available_symbols

    def test_source_metadata_rate_limits(self):
        """Test SourceMetadata rate limits structure"""
        metadata = SourceMetadata(
            name="newsapi",
            domain=DataDomain.NEWS,
            description="NewsAPI",
            update_frequency="15m",
            rate_limits={"requests_per_day": 100, "requests_per_hour": 10},
            available_symbols=["global"],
            available_timeframes=["15m"],
            supported_streams=[],
            quality_sla=0.95,
        )

        assert metadata.rate_limits["requests_per_day"] == 100
        assert metadata.rate_limits["requests_per_hour"] == 10


class TestHealthChecks:
    """Test health check functionality"""

    @pytest.mark.asyncio
    async def test_health_check_returns_boolean(self):
        """Test that health_check returns boolean"""

        class TestSource(DataSource):
            async def fetch_historical(self, symbol, start, end, timeframe="1m", **kwargs):
                return []

            async def stream_realtime(self, symbols, **kwargs):
                yield DataPoint(
                    source="test",
                    symbol="BTC-USD",
                    timeframe="tick",
                    timestamp=datetime.now(),
                    data={},
                )

            async def health_check(self):
                return True

            async def get_metadata(self):
                return SourceMetadata(
                    name="test",
                    domain=DataDomain.EXCHANGES,
                    description="Test",
                    update_frequency="real-time",
                    rate_limits={},
                    available_symbols=[],
                    available_timeframes=[],
                    supported_streams=[],
                    quality_sla=0.99,
                )

        source = TestSource("test", DataDomain.EXCHANGES)
        health = await source.health_check()

        assert isinstance(health, bool)
        assert health is True

    @pytest.mark.asyncio
    async def test_is_healthy_cached_status(self):
        """Test is_healthy returns cached health status"""

        class TestSource(DataSource):
            async def fetch_historical(self, symbol, start, end, timeframe="1m", **kwargs):
                return []

            async def stream_realtime(self, symbols, **kwargs):
                yield DataPoint(
                    source="test",
                    symbol="BTC-USD",
                    timeframe="tick",
                    timestamp=datetime.now(),
                    data={},
                )

            async def health_check(self):
                return self._is_healthy

            async def get_metadata(self):
                return SourceMetadata(
                    name="test",
                    domain=DataDomain.EXCHANGES,
                    description="Test",
                    update_frequency="real-time",
                    rate_limits={},
                    available_symbols=[],
                    available_timeframes=[],
                    supported_streams=[],
                    quality_sla=0.99,
                )

        source = TestSource("test", DataDomain.EXCHANGES)

        # Initially healthy
        assert await source.is_healthy() is True

        # Simulate health failure
        source._is_healthy = False
        assert await source.is_healthy() is False


class TestDataDomainEnum:
    """Test DataDomain enum"""

    def test_data_domain_values(self):
        """Test DataDomain enum has correct values"""
        assert DataDomain.EXCHANGES == "exchanges"
        assert DataDomain.NEWS == "news"
        assert DataDomain.ONCHAIN == "onchain"
        assert DataDomain.MACRO == "macro"
        assert DataDomain.SENTIMENT == "sentiment"

    def test_data_domain_is_string(self):
        """Test DataDomain enum values are strings"""
        for domain in DataDomain:
            assert isinstance(domain.value, str)


class TestStreamTypeEnum:
    """Test StreamType enum"""

    def test_stream_type_values(self):
        """Test StreamType enum has correct values"""
        assert StreamType.TRADE == "trade"
        assert StreamType.ORDERBOOK == "orderbook"
        assert StreamType.TICKER == "ticker"
        assert StreamType.KLINE == "kline"
        assert StreamType.FUNDING == "funding"

    def test_stream_type_is_string(self):
        """Test StreamType enum values are strings"""
        for stream_type in StreamType:
            assert isinstance(stream_type.value, str)
