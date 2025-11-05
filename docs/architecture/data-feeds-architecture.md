# Data Feeds Architecture

**Status:** ⭐⭐⭐ PRODUCTION SPEC
**Version:** 1.0
**Last Updated:** 2025-10-31

## Overview

This document specifies the complete data acquisition, storage, and distribution architecture for Coinswarm. Each layer of the hierarchical temporal decision system draws data from different sources at different cadences, tuned to its time horizon and decision role.

**Key Principle:** All data pathways are **append-only** and **versioned**, enabling planners to reconstruct context at any point in time and verify that medium/long-term decisions are built on the same factual base the short-term memory experienced.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Layer-Specific Data Feeds](#layer-specific-data-feeds)
3. [Data Sources](#data-sources)
4. [Storage Architecture](#storage-architecture)
5. [Data Ingestion Layer](#data-ingestion-layer)
6. [Data Registry & Versioning](#data-registry--versioning)
7. [Scheduling & Freshness](#scheduling--freshness)
8. [Implementation](#implementation)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      DATA ACQUISITION LAYER                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Exchanges│  │   News   │  │ On-Chain │  │   Macro  │       │
│  │ REST/WS  │  │Sentiment │  │  Funding │  │  FX/Rates│       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
└───────┼─────────────┼─────────────┼─────────────┼──────────────┘
        │             │             │             │
        ▼             ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      STORAGE & ROUTING                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │Redis Streams │  │  PostgreSQL  │  │  InfluxDB    │         │
│  │(ms-s data)   │  │ (patterns)   │  │ (timeseries) │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
        │             │             │             │
        ▼             ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    HIERARCHICAL LAYERS                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ PLANNERS (15min-6h)                                       │  │
│  │ ← Sentiment, Funding, Macro, OHLCV-1h/1d                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ COMMITTEE (ms-s)                                          │  │
│  │ ← LOB ticks, trades, spreads, imbalance                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ MEMORY OPTIMIZER (continuous)                             │  │
│  │ ← Execution logs, micro-performance metrics              │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ SELF-REFLECTION (h-d)                                     │  │
│  │ ← Aggregated performance, audit logs                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Layer-Specific Data Feeds

### 1. Planners (Long/Medium-Term Data Horizon)

**Purpose:** Detect regime and sentiment shifts that warrant committee re-weighting.

**Frequency:** Every 15 minutes to 6 hours
**Storage:** PostgreSQL/Parquet lake partitioned by symbol and source
**Window:** Rolling 30-day windows for regime classification

#### Data Feeds

**Market Structure:**
- OHLCV aggregates (1h–1d bars)
- Realized volatility (30m, 1h, 4h, 1d)
- Volume concentration (% of volume in top 1% of trades)
- Dominance metrics (BTC dominance, ETH/BTC ratio)

**Funding and Positioning:**
- Perpetual funding rates (Binance, Bybit, OKX)
- Open interest across exchanges
- Long/short ratios (exchange-provided)
- CVD (cumulative volume delta) - buy vs sell pressure
- Liquidation heatmaps

**Sentiment / Narrative:**
- News APIs:
  - GDELT (global events)
  - RavenPack (financial news)
  - NewsAPI (general news)
- Social metrics:
  - Twitter/X embeddings (keyword tracking: "BTC", "crypto", "bull", "bear")
  - Reddit sentiment (r/cryptocurrency, r/bitcoin)
  - Binance/Coinbase comments
  - Google Trends indices
- On-chain discussion volume
- GitHub activity (for DeFi protocols)

**Macro Context:**
- DXY (US Dollar Index)
- Interest rates (Fed funds, 10Y treasury)
- BTC/ETH correlation with equities (SPY, QQQ)
- Crypto ETF flows (GBTC, ETHE, spot ETFs)
- Stablecoin supply (USDT, USDC market cap)

#### Access Pattern

```python
# Planners pull rolling windows
data = planner_data_client.get_features(
    symbols=["BTC-USD", "ETH-USD"],
    sources=["funding", "sentiment", "macro"],
    window_days=30,
    granularity="1h"
)
```

---

### 2. Committee Agents (Intra-Day Tactical Layer)

**Purpose:** Respond to real-time order-book and flow conditions.

**Frequency:** Milliseconds to seconds
**Storage:** Redis Streams or Kafka topics with short TTL (minutes)
**Access:** Subscribe to symbol channels via pub/sub

#### Data Feeds

**Exchange Market Data:**
- Tick-by-tick trades (price, size, side)
- Bid/ask depth snapshots (L2 order book)
- Top-of-book spread
- Order book imbalance (bid volume - ask volume)
- Order flow imbalance (recent buy volume - sell volume)
- WebSocket or FIX feeds from:
  - Binance
  - Coinbase Advanced
  - Kraken
  - OKX
  - Bybit

**Cross-Venue Arbitrage:**
- Price differences across exchanges
- Latency differentials
- Arbitrage opportunity alerts

**Volatility Surfaces:**
- Implied volatility from options venues (Deribit)
- ATM/OTM skew

**Execution Feedback:**
- Fill ratios (expected vs actual fills)
- Slippage (order price vs fill price)
- Queue position estimates
- Maker/taker ratios

#### Access Pattern

```python
# Committee agents subscribe to real-time streams
async for message in committee_data_client.subscribe("BTC-USD:trades"):
    trade = parse_trade(message)
    features = extract_features(trade, lookback_window="10s")
    action = agent.decide(features)
```

---

### 3. Memory Optimizer (Short-Term Adaptive Layer)

**Purpose:** Refine execution tactics and pattern clustering.

**Frequency:** Continuous stream
**Storage:** Redis vector store (episodic memory)
**Feedback Loop:** New entries added after every trade completion

#### Data Feeds

**Execution Logs:**
- (state, action, reward) tuples from committee agents
- Full trade context (entry/exit, slippage, fees)

**Micro-Performance Metrics:**
- Per-trade P&L
- Latency (order placement to fill)
- Slippage (expected vs realized)
- Stop-out frequency
- Fill quality

**Derived Signals:**
- Funding rate flips (sign changes)
- Local sentiment bursts (minute-level embeddings)
- Sudden spread widening
- Volume spikes

#### Access Pattern

```python
# Memory optimizer writes after each trade
memory_optimizer.record_episode(
    state_vector=phi_t,
    action=action,
    reward=pnl,
    metadata={
        "slippage_bps": slippage,
        "latency_ms": latency,
        "regime": current_regime
    }
)
```

---

### 4. Self-Reflection & Governance

**Purpose:** Audit and trigger meta-learning.

**Frequency:** Hourly to daily audits
**Storage:** Immutable audit DB (TimescaleDB or ClickHouse)

#### Data Feeds

**Aggregated Results:**
- Realized vs expected P&L (per agent, per symbol)
- Sharpe ratio drift over time
- Violation logs (risk limits, position limits)

**System Health:**
- Committee disagreement rate
- Memory hit ratio (cache effectiveness)
- Latency histograms (p50, p95, p99)
- Error rates

**Governance Metrics:**
- Quorum vote outcomes
- Pattern promotion/deprecation events
- Planner intervention frequency

#### Access Pattern

```python
# Self-reflection pulls hourly aggregates
audit_data = self_reflection.get_metrics(
    time_range="last_24h",
    granularity="1h",
    metrics=["pnl", "sharpe", "violations"]
)
```

---

## Data Sources

### Exchange APIs

| Exchange | REST API | WebSocket | Data Types | Rate Limits |
|----------|----------|-----------|------------|-------------|
| Binance | ✓ | ✓ | OHLCV, Trades, L2, Funding | 2400/min REST, unlimited WS |
| Coinbase Advanced | ✓ | ✓ | OHLCV, Trades, L2 | 10/s public, 15/s private |
| Kraken | ✓ | ✓ | OHLCV, Trades, L2, Funding | 15/s REST |
| OKX | ✓ | ✓ | OHLCV, Trades, L2, Funding, OI | 20/2s REST |
| Bybit | ✓ | ✓ | OHLCV, Trades, L2, Funding, OI | 120/5s REST |

### Sentiment & News

| Source | Type | Update Frequency | Coverage |
|--------|------|------------------|----------|
| NewsAPI | REST | Real-time | General news, crypto keywords |
| GDELT | REST/BigQuery | 15min | Global events, mentions |
| RavenPack | REST | Real-time | Financial news, sentiment scores |
| Twitter/X API | Streaming | Real-time | Social sentiment, embeddings |
| Reddit API | REST | 1min | r/cryptocurrency, r/bitcoin |
| Google Trends | REST | Hourly | Search volume indices |

### On-Chain Data

| Source | Type | Update Frequency | Data |
|--------|------|------------------|------|
| Etherscan | REST | Real-time | Ethereum transactions, gas |
| Glassnode | REST | Daily | Network metrics, holder data |
| DeFi Llama | REST | Hourly | TVL, protocol metrics |
| Exchange APIs | WebSocket | Real-time | Funding, OI, liquidations |

### Macro Data

| Source | Type | Update Frequency | Data |
|--------|------|------------------|------|
| FRED | REST | Daily | Interest rates, economic indicators |
| BLS | REST | Monthly | Inflation, employment |
| Yahoo Finance | REST | Real-time | SPY, QQQ, DXY |
| CoinGecko | REST | 1min | Market cap, dominance |

---

## Storage Architecture

### Real-Time Data (ms-s TTL)

**Redis Streams:**
```redis
XADD trades:BTC-USD * price 50000 size 0.5 side buy ts 1698765432000
XADD orderbook:BTC-USD:snapshot * bids [[49999,1.2],[49998,0.8]] asks [[50001,1.5]]
```

**Kafka Topics:**
```
trades.binance.btcusd
orderbook.coinbase.ethusd
funding.okx.all
```

**TTL:** 5-15 minutes (streaming window only)

### Medium-Term Data (hours-days)

**InfluxDB (Time-Series):**
```
measurement: ohlcv
tags: {symbol, exchange, timeframe}
fields: {open, high, low, close, volume}
retention: 90 days

measurement: funding_rates
tags: {symbol, exchange}
fields: {rate, oi, long_short_ratio}
retention: 90 days
```

**PostgreSQL (Aggregates):**
```sql
CREATE TABLE market_aggregates (
    id UUID PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    timeframe VARCHAR(20) NOT NULL,  -- 1h, 4h, 1d
    timestamp TIMESTAMPTZ NOT NULL,

    -- OHLCV
    open DECIMAL(20, 8),
    high DECIMAL(20, 8),
    low DECIMAL(20, 8),
    close DECIMAL(20, 8),
    volume DECIMAL(20, 8),

    -- Derived metrics
    realized_vol DECIMAL(10, 4),
    volume_concentration DECIMAL(5, 4),

    -- Indexes
    INDEX idx_aggregates_symbol_ts (symbol, timestamp DESC)
);
```

### Long-Term Data (weeks-months)

**Parquet Lake (Object Storage - S3/MinIO):**
```
s3://coinswarm-data/
  raw/
    exchanges/binance/2025/10/31/trades_btcusd.parquet
    news/newsapi/2025/10/31/crypto.parquet
  processed/
    sentiment/2025/10/embeddings.parquet
    funding/2025/10/rates.parquet
```

**Retention:** 1-2 years

---

## Data Ingestion Layer

### Directory Structure

```
src/coinswarm/data_ingest/
├── __init__.py
├── base.py                 # Base classes
├── exchanges/
│   ├── __init__.py
│   ├── binance.py
│   ├── coinbase.py
│   ├── kraken.py
│   └── okx.py
├── news/
│   ├── __init__.py
│   ├── newsapi.py
│   ├── twitter.py
│   └── reddit.py
├── onchain/
│   ├── __init__.py
│   ├── etherscan.py
│   └── glassnode.py
├── macro/
│   ├── __init__.py
│   ├── fred.py
│   └── yahoo.py
├── processors/
│   ├── __init__.py
│   ├── sentiment.py        # Embedding generation
│   ├── aggregators.py      # OHLCV aggregation
│   └── features.py         # Feature extraction
└── registry/
    ├── __init__.py
    └── data_registry.py    # Versioned endpoint manager
```

### Base Data Source Interface

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional

@dataclass
class DataPoint:
    """Standardized data point"""
    source: str           # "binance", "newsapi", etc.
    symbol: str           # "BTC-USD", "global", etc.
    timeframe: str        # "tick", "1m", "1h", etc.
    timestamp: datetime
    data: Dict[str, Any]
    quality_score: float  # 0.0-1.0
    version: str          # Data schema version

class DataSource(ABC):
    """Base class for all data sources"""

    def __init__(self, source_name: str):
        self.source_name = source_name
        self.logger = structlog.get_logger().bind(source=source_name)

    @abstractmethod
    async def fetch_historical(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        **kwargs
    ) -> List[DataPoint]:
        """Fetch historical data"""
        pass

    @abstractmethod
    async def stream_realtime(
        self,
        symbols: List[str],
        **kwargs
    ) -> AsyncIterator[DataPoint]:
        """Stream real-time data"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if data source is healthy"""
        pass
```

### Exchange Data Ingestor

```python
class BinanceIngestor(DataSource):
    """Binance exchange data ingestor"""

    def __init__(self):
        super().__init__("binance")
        self.ws_client = None
        self.rest_client = ccxt.binance()

    async def stream_realtime(
        self,
        symbols: List[str],
        streams: List[str] = ["trade", "depth"]
    ) -> AsyncIterator[DataPoint]:
        """
        Stream real-time data from Binance WebSocket

        Args:
            symbols: List of symbols (e.g., ["BTC-USD", "ETH-USD"])
            streams: Stream types (trade, depth, kline, etc.)
        """
        # Convert symbols to Binance format
        binance_symbols = [s.replace("-", "").lower() for s in symbols]

        # Build stream subscriptions
        subscriptions = [
            f"{sym}@{stream}"
            for sym in binance_symbols
            for stream in streams
        ]

        ws_url = f"wss://stream.binance.com:9443/stream?streams={'/'.join(subscriptions)}"

        async with websockets.connect(ws_url) as ws:
            async for message in ws:
                data = json.loads(message)

                # Parse and standardize
                yield DataPoint(
                    source="binance",
                    symbol=self._normalize_symbol(data["stream"]),
                    timeframe="tick",
                    timestamp=datetime.fromtimestamp(data["data"]["E"] / 1000),
                    data=data["data"],
                    quality_score=1.0,
                    version="v1"
                )
```

---

## Data Registry & Versioning

### Data Registry

All data sources register with a central registry that provides versioned, timestamped access.

```python
class DataRegistry:
    """
    Central registry for all data sources.
    Provides versioned access to data feeds.
    """

    def __init__(self, redis_client, postgres_client):
        self.redis = redis_client
        self.postgres = postgres_client
        self.sources: Dict[str, DataSource] = {}

    def register(self, source: DataSource, metadata: Dict[str, Any]):
        """Register a data source"""
        self.sources[source.source_name] = source

        # Store metadata in Postgres
        self.postgres.execute("""
            INSERT INTO data_sources (name, type, metadata, registered_at)
            VALUES (%s, %s, %s, NOW())
        """, (source.source_name, metadata["type"], json.dumps(metadata)))

    async def get(
        self,
        domain: str,         # "exchanges", "news", "onchain", "macro"
        symbol: str,
        timeframe: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> List[DataPoint]:
        """
        Get data from registry with versioning.

        Endpoint format: /v1/data/{domain}/{symbol}/{timeframe}
        """
        source_key = f"{domain}:{symbol}:{timeframe}"

        # Check cache first (Redis)
        cached = await self._check_cache(source_key, start, end)
        if cached:
            return cached

        # Fetch from source
        source = self._get_source_for_domain(domain)
        data = await source.fetch_historical(symbol, start, end, timeframe=timeframe)

        # Cache for future requests
        await self._cache_data(source_key, data)

        return data
```

### Metadata Schema

Each data point is tagged with:

```python
{
    "source": "binance",           # Source identifier
    "symbol": "BTC-USD",            # Standardized symbol
    "timeframe": "1m",              # Time granularity
    "last_update": "2025-10-31T12:00:00Z",  # Last refresh
    "quality_score": 0.98,          # Data quality (0-1)
    "version": "v1.2",              # Schema version
    "latency_ms": 45                # Ingestion latency
}
```

---

## Scheduling & Freshness

### Scheduler Architecture

Use **Prefect** or **Airflow** to maintain data freshness.

```python
from prefect import flow, task
from datetime import timedelta

@task
async def ingest_funding_rates():
    """Ingest funding rates from all exchanges"""
    ingestor = FundingRateIngestor()
    data = await ingestor.fetch_all_exchanges()
    await storage.write(data)

@task
async def ingest_sentiment():
    """Ingest and process sentiment data"""
    ingestor = SentimentIngestor()
    data = await ingestor.fetch_news_and_social()
    embeddings = await processor.generate_embeddings(data)
    await storage.write(embeddings)

@flow(name="planner_data_refresh")
async def refresh_planner_data():
    """Refresh all planner data sources"""
    await ingest_funding_rates()
    await ingest_sentiment()
    await ingest_macro_indicators()

# Schedule: every 15 minutes
refresh_planner_data.schedule = "*/15 * * * *"
```

### Freshness Monitoring

```python
class FreshnessMonitor:
    """Monitor data freshness and alert on stale data"""

    async def check_freshness(self):
        """Check if all data sources are fresh"""
        sources = await self.registry.list_sources()

        for source in sources:
            last_update = await self.get_last_update(source)
            expected_interval = self.get_expected_interval(source)

            if datetime.now() - last_update > expected_interval * 2:
                self.alert(f"Stale data: {source} (last update: {last_update})")
```

---

## Implementation

### Layer Summary

| Layer | Frequency | Primary Sources | Storage | Purpose |
|-------|-----------|-----------------|---------|---------|
| **Planners** | 15min–6h | Sentiment, funding, macro | PostgreSQL / Parquet | Re-weight committee |
| **Committee** | ms–s | LOB ticks, trades | Redis / Kafka | Decide + execute |
| **Memory** | Continuous | Execution logs, micro features | Redis vector DB | Adapt tactics |
| **Self-Reflection** | h–d | Performance logs | TimescaleDB | Audit and improve |

### Data Flow Example

```
1. Exchange WebSocket → Redis Stream (tick data)
   ↓
2. Committee Agent subscribes → Makes trade decision
   ↓
3. Execution → Memory Optimizer records (state, action, reward)
   ↓
4. Redis Vector DB (episodic memory)
   ↓
5. Hourly: Self-Reflection aggregates performance
   ↓
6. Daily: Planners analyze sentiment + funding → Adjust weights
   ↓
7. Updated committee weights → Better decisions
```

### Quality Assurance

**Data Quality Checks:**
1. **Completeness:** Check for gaps in time series
2. **Consistency:** Cross-validate across sources (e.g., funding rates from multiple exchanges)
3. **Latency:** Monitor ingestion lag
4. **Outliers:** Detect and flag anomalous values

```python
class DataQualityChecker:
    """Validate data quality"""

    async def check_completeness(self, data: List[DataPoint], expected_interval: timedelta):
        """Check for gaps in time series"""
        timestamps = sorted([d.timestamp for d in data])
        gaps = []

        for i in range(1, len(timestamps)):
            if timestamps[i] - timestamps[i-1] > expected_interval * 2:
                gaps.append((timestamps[i-1], timestamps[i]))

        return {"has_gaps": len(gaps) > 0, "gaps": gaps}

    async def check_outliers(self, data: List[DataPoint], field: str):
        """Detect outliers using IQR method"""
        values = [d.data[field] for d in data if field in d.data]
        q1, q3 = np.percentile(values, [25, 75])
        iqr = q3 - q1

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        outliers = [d for d in data if d.data.get(field, 0) < lower_bound or d.data.get(field, 0) > upper_bound]

        return {"has_outliers": len(outliers) > 0, "count": len(outliers)}
```

---

## Next Steps

1. **Implement base data ingestors** for each exchange
2. **Set up Redis Streams** for real-time tick data
3. **Configure Prefect flows** for scheduled data refresh
4. **Build data registry** with versioned endpoints
5. **Add monitoring** for data freshness and quality
6. **Create backfill jobs** for historical data

---

**All data pathways are append-only and versioned**, ensuring reproducibility and auditability across all layers of the system.
