"""
Base classes for data ingestion layer

Defines standardized interfaces for all data sources.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import structlog


class DataDomain(str, Enum):
    """Data domain classification"""

    EXCHANGES = "exchanges"
    NEWS = "news"
    ONCHAIN = "onchain"
    MACRO = "macro"
    SENTIMENT = "sentiment"


class StreamType(str, Enum):
    """Exchange stream types"""

    TRADE = "trade"
    ORDERBOOK = "orderbook"
    TICKER = "ticker"
    KLINE = "kline"
    FUNDING = "funding"


@dataclass
class DataPoint:
    """
    Standardized data point with metadata.

    All data ingested into Coinswarm is wrapped in this structure
    for consistent handling, versioning, and quality tracking.
    """

    source: str  # "binance", "newsapi", "etherscan", etc.
    symbol: str  # "BTC-USD", "ETH-USD", "global", etc.
    timeframe: str  # "tick", "1m", "1h", "1d", etc.
    timestamp: datetime
    data: dict[str, Any]
    quality_score: float = 1.0  # 0.0-1.0, default is perfect quality
    version: str = "v1"  # Schema version
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "source": self.source,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "quality_score": self.quality_score,
            "version": self.version,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "DataPoint":
        """Create from dictionary"""
        return cls(
            source=d["source"],
            symbol=d["symbol"],
            timeframe=d["timeframe"],
            timestamp=datetime.fromisoformat(d["timestamp"]),
            data=d["data"],
            quality_score=d.get("quality_score", 1.0),
            version=d.get("version", "v1"),
            metadata=d.get("metadata", {}),
        )


@dataclass
class SourceMetadata:
    """Metadata about a data source"""

    name: str
    domain: DataDomain
    description: str
    update_frequency: str  # "real-time", "1m", "15m", "1h", "daily"
    rate_limits: dict[str, int]  # {"requests_per_second": 10, ...}
    available_symbols: list[str]
    available_timeframes: list[str]
    supported_streams: list[str]
    quality_sla: float  # Expected quality score (0-1)
    registered_at: datetime = field(default_factory=datetime.now)


class DataSource(ABC):
    """
    Abstract base class for all data sources.

    All data ingestors (exchanges, news, on-chain, macro) inherit from this.
    """

    def __init__(self, source_name: str, domain: DataDomain):
        self.source_name = source_name
        self.domain = domain
        self.logger = structlog.get_logger().bind(source=source_name, domain=domain.value)
        self._is_healthy = True

    @abstractmethod
    async def fetch_historical(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: str = "1m",
        **kwargs,
    ) -> list[DataPoint]:
        """
        Fetch historical data for a symbol.

        Args:
            symbol: Symbol identifier (e.g., "BTC-USD")
            start: Start datetime
            end: End datetime
            timeframe: Data granularity ("1m", "5m", "1h", etc.)
            **kwargs: Source-specific parameters

        Returns:
            List of DataPoint objects
        """
        pass

    @abstractmethod
    async def stream_realtime(
        self, symbols: list[str], **kwargs
    ) -> AsyncIterator[DataPoint]:
        """
        Stream real-time data for given symbols.

        Args:
            symbols: List of symbols to stream
            **kwargs: Source-specific parameters (e.g., stream_types)

        Yields:
            DataPoint objects as they arrive
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if data source is healthy and accessible.

        Returns:
            True if healthy, False otherwise
        """
        pass

    @abstractmethod
    async def get_metadata(self) -> SourceMetadata:
        """
        Get metadata about this data source.

        Returns:
            SourceMetadata object with source information
        """
        pass

    async def is_healthy(self) -> bool:
        """Get cached health status"""
        return self._is_healthy

    def _normalize_symbol(self, raw_symbol: str) -> str:
        """
        Normalize symbol to standard format (BASE-QUOTE).

        Override in subclasses for source-specific normalization.

        Args:
            raw_symbol: Raw symbol from source (e.g., "BTCUSDT", "BTC/USD")

        Returns:
            Normalized symbol (e.g., "BTC-USD")
        """
        # Default: uppercase and replace / with -
        return raw_symbol.upper().replace("/", "-")

    def _calculate_quality_score(self, data: dict[str, Any], **kwargs) -> float:
        """
        Calculate quality score for a data point.

        Override in subclasses for source-specific quality metrics.

        Args:
            data: Raw data dictionary
            **kwargs: Additional context for quality calculation

        Returns:
            Quality score between 0.0 and 1.0
        """
        # Default: perfect quality
        # Subclasses can implement checks like:
        # - Required fields present
        # - Values within expected ranges
        # - Timestamps reasonable
        # - No duplicates
        return 1.0


class ExchangeDataSource(DataSource):
    """
    Base class for exchange data sources.

    Provides common functionality for exchanges (Binance, Coinbase, etc.)
    """

    def __init__(self, source_name: str):
        super().__init__(source_name, DataDomain.EXCHANGES)

    @abstractmethod
    async def get_products(self) -> list[dict[str, Any]]:
        """Get list of tradable products"""
        pass

    @abstractmethod
    async def get_funding_rates(self, symbol: str) -> float | None:
        """Get current funding rate for a symbol (if applicable)"""
        pass

    @abstractmethod
    async def get_orderbook(
        self, symbol: str, depth: int = 20
    ) -> dict[str, Any]:
        """Get current order book snapshot"""
        pass


class SentimentDataSource(DataSource):
    """
    Base class for sentiment data sources.

    Handles news, social media, and other sentiment signals.
    """

    def __init__(self, source_name: str):
        super().__init__(source_name, DataDomain.SENTIMENT)

    @abstractmethod
    async def get_sentiment_score(
        self, keywords: list[str], lookback_hours: int = 24
    ) -> float:
        """
        Get aggregated sentiment score for keywords.

        Args:
            keywords: Keywords to search for
            lookback_hours: How far back to look

        Returns:
            Sentiment score (-1.0 to +1.0, where -1 is bearish, +1 is bullish)
        """
        pass

    @abstractmethod
    async def generate_embeddings(
        self, text: str
    ) -> list[float]:
        """
        Generate text embeddings for sentiment analysis.

        Args:
            text: Input text

        Returns:
            Vector embedding (typically 384 or 768 dimensions)
        """
        pass


class MacroDataSource(DataSource):
    """
    Base class for macro economic data sources.

    Handles interest rates, indices, economic indicators, etc.
    """

    def __init__(self, source_name: str):
        super().__init__(source_name, DataDomain.MACRO)

    @abstractmethod
    async def get_indicator(
        self, indicator_name: str, start: datetime, end: datetime
    ) -> list[DataPoint]:
        """
        Get economic indicator time series.

        Args:
            indicator_name: Name of indicator (e.g., "DXY", "DFF", "T10Y")
            start: Start date
            end: End date

        Returns:
            List of DataPoint objects
        """
        pass


class OnChainDataSource(DataSource):
    """
    Base class for on-chain data sources.

    Handles blockchain data, network metrics, etc.
    """

    def __init__(self, source_name: str):
        super().__init__(source_name, DataDomain.ONCHAIN)

    @abstractmethod
    async def get_network_metrics(
        self, chain: str, metrics: list[str]
    ) -> dict[str, Any]:
        """
        Get network-level metrics.

        Args:
            chain: Chain identifier ("ethereum", "bitcoin", etc.)
            metrics: List of metrics to fetch ("hashrate", "active_addresses", etc.)

        Returns:
            Dictionary of metric values
        """
        pass
