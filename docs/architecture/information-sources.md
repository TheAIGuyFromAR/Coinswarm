# Information Sources Strategy

## Overview

This document outlines the comprehensive information ecosystem that will feed data to Coinswarm's multi-agent trading system. The agents require diverse, high-quality data sources to make informed decisions across market analysis, sentiment assessment, pattern recognition, and trade execution.

---

## Information Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Multi-Agent System                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Market      │  │  Sentiment   │  │  Pattern Learning    │  │
│  │  Analysis    │  │  Analysis    │  │  Agent               │  │
│  │  Agent       │  │  Agent       │  │                      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└────────┬────────────────────┬──────────────────┬────────────────┘
         │                    │                  │
         ▼                    ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Data Aggregation Layer                       │
│  • Normalization  • Validation  • Caching  • Rate Limiting      │
└─────────┬───────────────────┬───────────────────┬───────────────┘
          │                   │                   │
    ┌─────▼─────┐      ┌──────▼──────┐     ┌────▼─────┐
    │  Market   │      │  Sentiment  │     │  On-Chain│
    │  Data     │      │  Data       │     │  Data    │
    └───────────┘      └─────────────┘     └──────────┘
```

---

## 1. Market Data Sources

### Primary Exchange Data (via MCP)

**Coinbase Advanced**
- **Real-time Data**:
  - Level 2 order book (50 levels)
  - Trade executions (price, size, side)
  - Ticker updates (24h volume, price changes)
- **Historical Data**:
  - OHLCV candles (1m, 5m, 15m, 1h, 4h, 1d)
  - Trade history
  - Order book snapshots
- **Update Frequency**: Real-time via WebSocket
- **Products**: All Coinbase spot pairs

**Alpaca**
- **Real-time Data**:
  - Stock quotes (bid/ask)
  - Trade executions
  - Bars (1m, 5m, 15m)
- **Historical Data**:
  - Daily bars (5+ years)
  - Intraday bars (last 30 days)
- **Update Frequency**: Real-time via WebSocket
- **Coverage**: All U.S. equities

### Supplementary Market Data

**Yahoo Finance (yfinance)**
- Historical price data
- Fundamental data (P/E, market cap, etc.)
- Dividend history
- Stock splits
- **Use Case**: Long-term analysis, fundamental context
- **Cost**: Free
- **Rate Limits**: Reasonable for low-frequency queries

**CoinGecko API**
- Cryptocurrency prices across exchanges
- Market cap rankings
- Volume aggregation
- Exchange rankings
- **Use Case**: Cross-exchange price validation, market overview
- **Cost**: Free tier available (10-50 calls/min)
- **Limitations**: 10-30 second delays on free tier

**CoinMarketCap API**
- Similar to CoinGecko
- Broader coverage
- More detailed metrics
- **Cost**: Free tier (333 calls/day)
- **Use Case**: Backup/validation against CoinGecko

**TradingView (via unofficial API)**
- Technical indicators pre-calculated
- Community sentiment (ideas, scripts)
- Multi-exchange aggregated data
- **Cost**: Free with limitations
- **Caution**: Unofficial API, may break

---

## 2. Sentiment & Social Data Sources

### News Aggregators

**NewsAPI**
- Global news articles
- Filter by keywords, sources, dates
- Headlines and full text
- **Coverage**: 80k+ sources
- **Cost**: Free tier (100 requests/day), Paid ($449/mo for commercial)
- **Use Case**: Real-time news sentiment

**Google News RSS**
- Free news aggregation
- Keyword-based search
- No API key required
- **Limitations**: No rate guarantee, informal scraping
- **Use Case**: Backup news source

**Financial News APIs**
- **Alpha Vantage News**: Free tier, financial news specific
- **Finnhub**: Company news, earnings, IPO calendar
- **Benzinga**: Premium news with low latency

### Social Media

**Twitter/X API**
- **Essential API (Free)**:
  - 1,500 tweets/month
  - Tweet lookup
  - User lookup
- **Basic API ($100/mo)**:
  - 10,000 tweets/month
  - Real-time tweet stream
- **Data Types**:
  - Keyword mentions
  - Hashtag tracking
  - Influential accounts (e.g., @coinbase, @VitalikButerin)
  - Sentiment from trading community
- **Use Case**: Real-time social sentiment, breaking news detection

**Reddit API (PRAW)**
- Subreddit monitoring
- **Key Subreddits**:
  - r/CryptoCurrency
  - r/Bitcoin
  - r/wallstreetbets
  - r/investing
  - r/CryptoMarkets
- **Data Types**:
  - Post sentiment
  - Comment analysis
  - Submission volume
  - Trending topics
- **Cost**: Free
- **Rate Limits**: 60 requests/minute

**StockTwits API**
- Social sentiment specifically for trading
- Bullish/bearish tags
- Message volume
- **Cost**: Free tier available
- **Use Case**: Trader sentiment indicator

### Alternative Data

**Google Trends**
- Search volume for keywords
- Geographic breakdown
- Related queries
- **Cost**: Free (via pytrends)
- **Use Case**: Retail interest indicator

**Fear & Greed Index**
- Crypto Fear & Greed (alternative.me)
- CNN Fear & Greed (stocks)
- **Cost**: Free
- **Update**: Daily
- **Use Case**: Market sentiment indicator

---

## 3. On-Chain Data (Crypto)

### Blockchain Explorers

**Etherscan API**
- Ethereum transactions
- Smart contract events
- Token transfers
- Wallet balances
- **Cost**: Free tier (5 calls/sec)
- **Use Case**: On-chain activity tracking

**Blockchain.com API**
- Bitcoin blockchain data
- Transaction volume
- Hash rate
- Mempool stats
- **Cost**: Free
- **Use Case**: Bitcoin network health

### On-Chain Analytics

**Glassnode**
- Advanced on-chain metrics
- Exchange flows
- Whale activity
- Network health indicators
- **Cost**: Free tier limited, Paid ($29-$799/mo)
- **Use Case**: Deep on-chain analysis

**CryptoQuant**
- Exchange reserves
- Miner flows
- Derivatives data
- **Cost**: Free tier available
- **Use Case**: Supply/demand dynamics

**Dune Analytics**
- Custom on-chain queries
- Community dashboards
- DEX volume, NFT sales, protocol metrics
- **Cost**: Free for public queries
- **Use Case**: DeFi protocol analysis

### DeFi Specific

**DeFi Llama API**
- TVL (Total Value Locked) across protocols
- Protocol revenues
- Token unlocks
- **Cost**: Free
- **Use Case**: DeFi ecosystem monitoring

**The Graph (Subgraphs)**
- Decentralized indexing
- Protocol-specific data
- Custom queries via GraphQL
- **Cost**: Free (with rate limits)
- **Use Case**: Real-time DeFi protocol data

---

## 4. Fundamental Data

### Equity Fundamentals

**Alpha Vantage**
- Company overview
- Income statement
- Balance sheet
- Cash flow
- Earnings calendar
- **Cost**: Free tier (25 requests/day)
- **Use Case**: Fundamental analysis for stocks

**Financial Modeling Prep**
- Financial statements
- Ratios
- DCF analysis
- Insider trading
- **Cost**: Free tier limited, Paid ($14-$99/mo)
- **Use Case**: Detailed fundamental screening

**SEC EDGAR**
- 10-K, 10-Q filings
- 8-K current reports
- Insider transactions
- **Cost**: Free
- **Use Case**: Raw regulatory filings

### Crypto Fundamentals

**Messari API**
- Token metrics
- Project profiles
- Governance data
- **Cost**: Free tier available, Paid for real-time
- **Use Case**: Crypto project research

**TokenTerminal**
- Protocol revenue
- P/F ratios (Price/Fees)
- Active users
- **Cost**: Free tier available
- **Use Case**: Crypto fundamental valuation

---

## 5. Economic & Macro Data

### Economic Indicators

**FRED (Federal Reserve Economic Data)**
- Interest rates
- Inflation data (CPI, PPI)
- Employment statistics
- GDP
- Money supply
- **API**: fredapi Python library
- **Cost**: Free
- **Use Case**: Macro environment context

**BLS (Bureau of Labor Statistics)**
- Employment reports
- Wage data
- Productivity
- **Cost**: Free
- **Use Case**: Economic calendar events

### Central Bank Data

**Federal Reserve APIs**
- FOMC meeting minutes
- Economic projections
- Interest rate decisions
- **Cost**: Free
- **Use Case**: Monetary policy tracking

**ECB (European Central Bank)**
- Similar to Fed for EU
- **Cost**: Free
- **Use Case**: Global macro context

---

## 6. Technical Indicators & Derivatives

### Options & Derivatives

**CBOE (for VIX)**
- VIX (volatility index)
- Put/Call ratios
- **Cost**: Free via various APIs
- **Use Case**: Market fear gauge

**Skew (Crypto Derivatives)**
- Bitcoin futures
- Options flow
- Funding rates
- **Cost**: Some free data
- **Use Case**: Crypto derivatives sentiment

### Pre-calculated Indicators

**TradingView**
- RSI, MACD, Bollinger Bands
- Custom indicators
- **Cost**: Free with limitations
- **Use Case**: Technical analysis shortcut

---

## Data Ingestion Architecture

### Pipeline Design

```python
# data_sources/base.py

from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Any
from datetime import datetime

class DataSource(ABC):
    """Base class for all data sources"""

    def __init__(self, config: dict):
        self.config = config
        self.rate_limiter = RateLimiter(
            config.get('rate_limit', 60),
            config.get('rate_period', 60)
        )

    @abstractmethod
    async def fetch(self, params: dict) -> Dict[str, Any]:
        """Fetch data from source"""
        pass

    @abstractmethod
    async def stream(self, params: dict) -> AsyncIterator[Dict[str, Any]]:
        """Stream real-time data"""
        pass

    async def validate(self, data: Dict[str, Any]) -> bool:
        """Validate data quality"""
        pass

    async def normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize to common format"""
        pass
```

### Example: News Source

```python
# data_sources/news/newsapi_source.py

from data_sources.base import DataSource
from newsapi import NewsApiClient

class NewsAPISource(DataSource):
    def __init__(self, config: dict):
        super().__init__(config)
        self.client = NewsApiClient(api_key=config['api_key'])

    async def fetch(self, params: dict) -> Dict[str, Any]:
        await self.rate_limiter.acquire()

        articles = self.client.get_everything(
            q=params.get('query', 'cryptocurrency'),
            language='en',
            sort_by='publishedAt',
            page_size=params.get('limit', 10)
        )

        return await self.normalize(articles)

    async def normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'source': 'newsapi',
            'timestamp': datetime.utcnow().isoformat(),
            'articles': [
                {
                    'title': article['title'],
                    'description': article['description'],
                    'url': article['url'],
                    'published_at': article['publishedAt'],
                    'source': article['source']['name']
                }
                for article in data['articles']
            ]
        }
```

### Example: Social Media Source

```python
# data_sources/social/reddit_source.py

import praw
from data_sources.base import DataSource

class RedditSource(DataSource):
    def __init__(self, config: dict):
        super().__init__(config)
        self.reddit = praw.Reddit(
            client_id=config['client_id'],
            client_secret=config['client_secret'],
            user_agent=config['user_agent']
        )

    async def fetch(self, params: dict) -> Dict[str, Any]:
        subreddit = self.reddit.subreddit(params['subreddit'])
        posts = []

        for submission in subreddit.hot(limit=params.get('limit', 10)):
            posts.append({
                'id': submission.id,
                'title': submission.title,
                'score': submission.score,
                'upvote_ratio': submission.upvote_ratio,
                'num_comments': submission.num_comments,
                'created_utc': submission.created_utc,
                'url': submission.url,
                'selftext': submission.selftext
            })

        return {
            'source': 'reddit',
            'subreddit': params['subreddit'],
            'posts': posts,
            'timestamp': datetime.utcnow().isoformat()
        }
```

---

## Data Storage Strategy

### Time-Series Database

**InfluxDB**
- High-performance time-series storage
- Optimized for market data (OHLCV)
- Retention policies for data lifecycle

**Schema Example**:
```
measurement: market_data
tags:
  - product_id (BTC-USD)
  - source (coinbase)
  - data_type (candle)
fields:
  - open (float)
  - high (float)
  - low (float)
  - close (float)
  - volume (float)
timestamp: nanosecond precision
```

### Document Database

**MongoDB**
- Flexible schema for varied data types
- Good for news, social media, fundamentals
- Easy to query and aggregate

**Collections**:
- `news_articles`
- `social_posts`
- `sentiment_scores`
- `on_chain_events`

### Vector Database

**Pinecone / Weaviate**
- Store embeddings of news, social posts
- Semantic search capabilities
- Pattern matching for similar market conditions

---

## Data Quality & Validation

### Quality Checks

```python
class DataValidator:
    @staticmethod
    def validate_price(price: float, previous_price: float) -> bool:
        """Ensure price isn't wildly different from previous"""
        if previous_price == 0:
            return True
        change_pct = abs((price - previous_price) / previous_price)
        return change_pct < 0.5  # 50% change threshold

    @staticmethod
    def validate_volume(volume: float) -> bool:
        """Ensure volume is positive and reasonable"""
        return volume >= 0 and volume < 1e15

    @staticmethod
    def validate_timestamp(timestamp: datetime) -> bool:
        """Ensure timestamp is recent and not in future"""
        now = datetime.utcnow()
        return timestamp <= now and (now - timestamp).days < 7
```

### Missing Data Handling

```python
class MissingDataHandler:
    @staticmethod
    async def handle_missing_candle(product: str, timestamp: datetime):
        """Fill missing candle with interpolation or previous"""
        previous = await get_previous_candle(product, timestamp)
        next_candle = await get_next_candle(product, timestamp)

        if previous and next_candle:
            # Interpolate
            return interpolate_candle(previous, next_candle)
        elif previous:
            # Use previous
            return previous
        else:
            return None  # Skip
```

---

## Cost Management

### Free Tier Optimization

| Source | Free Limit | Cost After | Strategy |
|--------|------------|------------|----------|
| NewsAPI | 100 req/day | $449/mo | Cache aggressively, fetch hourly |
| Twitter Essential | 1,500 tweets/mo | $100/mo | Target high-value accounts only |
| Alpha Vantage | 25 req/day | $50/mo | Spread across endpoints, cache |
| CoinGecko | 10-50 calls/min | $129/mo | Rate limit strictly |
| Reddit | 60 req/min | Free | Generous, no concerns |

### Budget Allocation (if purchasing)

**Phase 0 (Free)**:
- Rely on free tiers
- Focus on Coinbase + Alpaca native data
- Limited external data

**Phase 1 ($100/mo)**:
- Twitter Basic API ($100)
- Use for sentiment boost

**Phase 2 ($500/mo)**:
- NewsAPI Commercial ($449)
- Twitter Basic ($100)

**Phase 3 ($1000+/mo)**:
- Add premium sources as ROI justifies

---

## Data Refresh Cadence

### Real-time (WebSocket)
- Market prices (Coinbase, Alpaca)
- Order book updates
- Trade executions

### High Frequency (1-5 min)
- Ticker snapshots
- Order book snapshots
- Social media sentiment

### Medium Frequency (15-60 min)
- News articles
- Reddit posts
- Fear & Greed indices

### Low Frequency (hourly/daily)
- Fundamentals
- On-chain metrics
- Economic indicators

---

## Integration Roadmap

### Phase 1: Core Market Data
- [ ] Coinbase real-time (WebSocket)
- [ ] Alpaca real-time (WebSocket)
- [ ] Historical candles (both exchanges)
- [ ] Order book snapshots

### Phase 2: Sentiment Foundation
- [ ] Twitter API (targeted accounts)
- [ ] Reddit (key subreddits)
- [ ] NewsAPI (crypto keywords)
- [ ] Fear & Greed Index

### Phase 3: On-Chain & Fundamentals
- [ ] Etherscan (Ethereum data)
- [ ] CryptoQuant (exchange flows)
- [ ] Alpha Vantage (stock fundamentals)
- [ ] FRED (macro data)

### Phase 4: Advanced Sources
- [ ] Glassnode (on-chain analytics)
- [ ] DeFi Llama (DeFi metrics)
- [ ] Options data (Skew, Deribit)
- [ ] Alternative data (Google Trends)

---

**Last Updated**: 2025-10-31
**Status**: Planning Phase
**Next**: Multi-Agent Architecture Documentation
