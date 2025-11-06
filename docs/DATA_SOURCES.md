# Coinswarm Data Sources

Complete overview of all data sources integrated into the backtesting system.

## Price Data

### Binance API (via ccxt)
**Status:** ✅ Implemented
**Cost:** FREE (public API)
**Rate Limits:** 1200 requests/minute
**Historical Data:** Back to 2017-08-17 (Binance launch)

**What we fetch:**
- Spot pairs: BTC-USDT, ETH-USDT, SOL-USDT
- Cross pairs: ETH-BTC (for arbitrage)
- OHLCV data: Open, High, Low, Close, Volume
- Timeframes: 1m, 5m, 15m, 1h, 4h, 1d

**Fallback Options:**
1. Cloudflare Worker (bypasses network restrictions)
2. CSV download from https://data.binance.vision/
3. Local ccxt directly

---

## News & Sentiment Data

### 1. Fear & Greed Index (Alternative.me)
**Status:** ✅ Implemented
**Cost:** FREE
**API Key:** Not needed
**Historical Data:** Last 90 days available

**What we fetch:**
- Overall crypto market sentiment (0-100)
- 0 = Extreme Fear
- 50 = Neutral
- 100 = Extreme Greed

**API:** `https://api.alternative.me/fng/`

---

### 2. CryptoCompare News API
**Status:** ✅ Implemented (optional)
**Cost:** FREE tier: 50 requests/day
**API Key:** Required
**Historical Data:** Several years back

**What we fetch:**
- News articles from CryptoCompare, CoinDesk, Cointelegraph
- Up to 100 articles per request
- Article title, body, source, timestamp
- Sentiment analysis on each article

**Get API Key:** https://www.cryptocompare.com/cryptopian/api-keys
**Docs:** https://min-api.cryptocompare.com/documentation

**Usage:**
```python
fetcher = HistoricalDataFetcher(
    cryptocompare_api_key="your_key_here"
)
```

---

### 3. NewsAPI.org
**Status:** ✅ Implemented (optional)
**Cost:** FREE tier: 100 requests/day
**API Key:** Required
**Historical Data:** Last 1 month on free tier

**What we fetch:**
- News articles about Bitcoin, Ethereum, Solana
- Article title, description, URL, timestamp
- Filtered by keyword (Bitcoin, Ethereum, etc.)
- Sentiment analysis on each article

**Get API Key:** https://newsapi.org/register
**Docs:** https://newsapi.org/docs

**Limitation:** Free tier only allows historical data for last 30 days.

**Usage:**
```python
fetcher = HistoricalDataFetcher(
    newsapi_key="your_key_here"
)
```

---

### 4. Reddit Sentiment (via PRAW)
**Status:** 🚧 Not implemented yet
**Cost:** FREE
**API Key:** Required (Reddit app credentials)
**Historical Data:** Available via Pushshift

**What we'll fetch:**
- Posts from r/CryptoCurrency, r/Bitcoin, r/Ethereum
- Comment sentiment
- Upvote/downvote ratios
- Trending topics

**Get API Key:** https://www.reddit.com/prefs/apps
**Docs:** https://praw.readthedocs.io/

**Future Usage:**
```python
fetcher = HistoricalDataFetcher(
    reddit_credentials={
        "client_id": "xxx",
        "client_secret": "xxx",
        "user_agent": "Coinswarm Bot"
    }
)
```

---

### 5. Twitter/X Sentiment
**Status:** 🚧 Not implemented yet
**Cost:** PAID (Twitter API v2 Basic: $100/month for historical)
**API Key:** Required
**Historical Data:** Available but expensive

**What we'd fetch:**
- Tweets mentioning BTC, ETH, SOL
- Tweet sentiment
- Engagement metrics (likes, retweets)
- Influencer tweets

**Alternative:** LunarCrush API (paid but cheaper)

**Reason for not implementing:** Cost prohibitive for historical data.

---

## Macro Economic Data

### 6. FRED (Federal Reserve Economic Data)
**Status:** ✅ Implemented
**Cost:** FREE
**API Key:** Required (free to get)
**Historical Data:** Decades back

**What we fetch:**
- **Fed Funds Rate** (FEDFUNDS) - Interest rates
- **CPI** (CPIAUCSL) - Inflation
- **Unemployment Rate** (UNRATE)
- **10Y Treasury Yield** (DGS10)
- **Dollar Index** (DEXUSEU)
- **Gold Price** (GOLDAMGBD228NLBM)

**Get API Key:** https://fred.stlouisfed.org/docs/api/api_key.html (instant approval)
**Docs:** https://fred.stlouisfed.org/docs/api/fred/

**Usage:**
```python
from coinswarm.data_ingest.macro_trends_fetcher import MacroTrendsFetcher

fetcher = MacroTrendsFetcher(fred_api_key="your_key_here")
macro_data = await fetcher.fetch_all_indicators(start_date, end_date)
```

---

### 7. Yahoo Finance (S&P 500, Stock Indices)
**Status:** ✅ Available (via yfinance library)
**Cost:** FREE
**API Key:** Not needed
**Historical Data:** Years back

**What we can fetch:**
- S&P 500 (^GSPC)
- NASDAQ (^IXIC)
- DJI (^DJI)
- Gold futures (GC=F)
- Oil (CL=F)

**Library:** `pip install yfinance`

---

## On-Chain Data

### 8. Glassnode
**Status:** 🚧 Not implemented yet
**Cost:** FREE tier available (limited)
**API Key:** Required
**Historical Data:** Years back (depending on tier)

**What we'd fetch:**
- Active addresses
- Exchange inflows/outflows
- Whale transactions
- Miner balances
- MVRV ratio (market value to realized value)

**Get API Key:** https://glassnode.com/
**Docs:** https://docs.glassnode.com/api/

**Cost:** Free tier is limited, paid plans start at $39/month.

---

### 9. Blockchain.com API
**Status:** 🚧 Not implemented yet
**Cost:** FREE
**API Key:** Not needed for basic data
**Historical Data:** Full blockchain history

**What we can fetch:**
- Bitcoin blockchain stats
- Transaction counts
- Hash rate
- Difficulty
- Mempool size

**Docs:** https://www.blockchain.com/api

---

## Summary Table

| Source | Status | Cost | API Key | Historical Data | What We Get |
|--------|--------|------|---------|-----------------|-------------|
| **Binance API** | ✅ Live | FREE | No | 2017+ | Price OHLCV |
| **Fear & Greed** | ✅ Live | FREE | No | 90 days | Market sentiment |
| **CryptoCompare** | ✅ Optional | FREE (50/day) | Yes | Years | News + sentiment |
| **NewsAPI** | ✅ Optional | FREE (100/day) | Yes | 30 days | News + sentiment |
| **Reddit** | 🚧 Soon | FREE | Yes | Via Pushshift | Social sentiment |
| **Twitter** | ❌ Skip | $100/mo | Yes | Available | Tweets (too expensive) |
| **FRED** | ✅ Live | FREE | Yes | Decades | Macro indicators |
| **Yahoo Finance** | ✅ Available | FREE | No | Years | Stock indices |
| **Glassnode** | 🚧 Future | $39+/mo | Yes | Years | On-chain metrics |
| **Blockchain.com** | 🚧 Future | FREE | No | Full history | BTC blockchain |

---

## What You Need To Get Started

### Minimum (No Setup Required)
**Works out of the box:**
- ✅ Binance price data
- ✅ Fear & Greed Index

**Result:** Basic backtesting with price + market sentiment.

---

### Recommended (5 min setup)
**Get these free API keys:**

1. **FRED API Key** (instant approval)
   - Go to: https://fred.stlouisfed.org/
   - Sign up (free)
   - Request API key: https://fred.stlouisfed.org/docs/api/api_key.html
   - Get macro economic data (inflation, interest rates, unemployment)

2. **CryptoCompare API Key** (instant approval)
   - Go to: https://www.cryptocompare.com/cryptopian/api-keys
   - Sign up (free)
   - Get news + sentiment from crypto-specific sources

**Result:** Price + sentiment + macro trends = much better backtests.

---

### Optional (Better Sentiment)

3. **NewsAPI.org** (instant approval)
   - Go to: https://newsapi.org/register
   - Free tier: 100 requests/day
   - Historical limit: 30 days back
   - Get mainstream news coverage

4. **Reddit API** (5 min approval)
   - Go to: https://www.reddit.com/prefs/apps
   - Create app
   - Get client ID + secret
   - Access social sentiment from crypto communities

**Result:** Comprehensive sentiment from news + social media.

---

## How To Configure

**Environment Variables (Recommended):**
```bash
export CRYPTOCOMPARE_API_KEY="your_key"
export NEWSAPI_KEY="your_key"
export FRED_API_KEY="your_key"
export REDDIT_CLIENT_ID="your_id"
export REDDIT_CLIENT_SECRET="your_secret"
```

**Or pass to fetcher:**
```python
from coinswarm.data_ingest.historical_data_fetcher import HistoricalDataFetcher

fetcher = HistoricalDataFetcher(
    cryptocompare_api_key="your_key",
    newsapi_key="your_key",
    reddit_credentials={
        "client_id": "xxx",
        "client_secret": "xxx",
        "user_agent": "Coinswarm Bot"
    }
)
```

---

## Sentiment Calculation

We aggregate sentiment from multiple sources:

**Formula:**
```
overall_sentiment = (
    news_sentiment * 0.4 +
    social_sentiment * 0.4 +
    (fear_greed_index - 50) / 50 * 0.2
)
```

**Result:** -1.0 (very bearish) to +1.0 (very bullish)

**Components:**
- **news_sentiment**: Weighted average from CryptoCompare + NewsAPI articles
- **social_sentiment**: Reddit + Twitter (when implemented)
- **fear_greed_index**: Market-wide sentiment (normalized to -1 to +1)

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│  HistoricalDataFetcher.fetch_all_historical_data()          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ├──────────────────────┐
                              │                      │
                              ▼                      ▼
                    ┌──────────────────┐   ┌──────────────────┐
                    │  BinanceIngestor │   │ NewsSentiment    │
                    │                  │   │ Fetcher          │
                    │  - Spot pairs    │   │                  │
                    │  - Cross pairs   │   │  - Fear & Greed  │
                    │  - OHLCV data    │   │  - CryptoCompare │
                    └──────────────────┘   │  - NewsAPI       │
                                           │  - Reddit        │
                                           └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  MacroTrends     │
                    │  Fetcher         │
                    │                  │
                    │  - FRED API      │
                    │  - Yahoo Finance │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  DataPoint[]     │
                    │  (unified format)│
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  BacktestEngine  │
                    │  (replay + test) │
                    └──────────────────┘
```

---

## Next Steps

1. **Get FRED API key** (5 min) - Free, instant, essential for macro data
2. **Get CryptoCompare key** (2 min) - Free, instant, great for crypto news
3. **Optional: Get NewsAPI key** - For mainstream news coverage
4. **Run backtest with sentiment** - See how sentiment improves strategy

**Example:**
```python
from coinswarm.data_ingest.historical_data_fetcher import HistoricalDataFetcher

fetcher = HistoricalDataFetcher(
    cryptocompare_api_key="your_key",
    fred_api_key="your_key"
)

# Fetch 3 months of price + sentiment + macro data
data = await fetcher.fetch_all_historical_data(
    months=3,
    timeframe="1h",
    include_sentiment=True  # ← Sentiment enabled!
)

# Now data includes:
# - BTC-USDC, ETH-USDC, SOL-USDC (price)
# - BTC-SENTIMENT, ETH-SENTIMENT, SOL-SENTIMENT
# - MACRO (Fed rates, CPI, unemployment, etc.)
```

---

## Performance

**With all sources enabled:**
- Price data: ~2,160 candles per pair per month (1h timeframe)
- Sentiment: ~30 snapshots per symbol per month (daily)
- Macro: ~20 data points per month (varies by indicator)
- News articles: Varies (typically 10-100 per day)

**Fetch time:**
- 3 months of data: 10-30 seconds
- Parallel fetching for speed
- Caching to avoid duplicate requests

---

## Cost Summary

**What's FREE forever:**
- ✅ Binance price data (unlimited)
- ✅ Fear & Greed Index (unlimited)
- ✅ FRED macro data (unlimited)
- ✅ Yahoo Finance (unlimited)
- ✅ Blockchain.com (basic data)

**What's FREE but limited:**
- ⚠️ CryptoCompare (50 requests/day)
- ⚠️ NewsAPI (100 requests/day, 30 days history)
- ⚠️ Reddit (within rate limits)

**What costs money (we can skip these):**
- ❌ Twitter API ($100/month for historical)
- ❌ Glassnode Pro ($39+/month for full data)

**Recommendation:** Use the free sources. They're more than enough for excellent backtesting.
