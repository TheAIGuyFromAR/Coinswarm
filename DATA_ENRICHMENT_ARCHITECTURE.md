# Multi-Agent Data Enrichment Architecture

## Overview

Build a comprehensive system that collects and enriches 5 years of historical crypto price data with technical indicators, sentiment analysis, and macroeconomic context to enable advanced pattern discovery.

---

## Target Dataset

### Tokens
- **BTC** (Bitcoin)
- **SOL** (Solana)
- **Top DeFi tokens on fast, low-fee, high-volume chains**:
  - BSC: CAKE, BNB, BUSD
  - Solana: RAY (Raydium), ORCA, JUP (Jupiter)
  - Arbitrum: ARB, GMX
  - Optimism: OP, VELO
  - Polygon: MATIC, QUICK
  - Base: AERO, BRETT

### Timeframe
- **5 years** of historical data (2020-2025)
- **5-minute candles** for maximum granularity
- ~525,600 candles per token (5 years × 365 days × 24 hours × 12)

### Data Granularity
Each timestamp enriched with **150+ data points**:
- Raw OHLCV (5 fields)
- Technical indicators (50+ fields)
- Sentiment data (30+ fields)
- Macroeconomic context (20+ fields)
- Market microstructure (10+ fields)

---

## Architecture

### Phase 1: Data Collection Layer (Current)

**Worker**: `historical-data-worker.ts`

**Data Sources** (5-tier fallback):
1. CryptoCompare (minute-level CEX data)
2. CoinGecko (daily OHLC)
3. GeckoTerminal (DEX OHLCV for 100+ networks)
4. Binance (public data API)
5. DexScreener (current prices, 50+ chains)

**Storage**: `price_data` table
```sql
CREATE TABLE price_data (
  id INTEGER PRIMARY KEY,
  symbol TEXT NOT NULL,
  timestamp INTEGER NOT NULL,
  timeframe TEXT NOT NULL,
  open REAL NOT NULL,
  high REAL NOT NULL,
  low REAL NOT NULL,
  close REAL NOT NULL,
  volume REAL NOT NULL,
  providers TEXT,              -- JSON array of sources
  data_points INTEGER,          -- Number of sources agreeing
  variance REAL,                -- Price variance across sources
  created_at INTEGER,
  UNIQUE(symbol, timestamp, timeframe)
);
```

**Tasks**:
- ✅ Multi-source API integration (5 sources)
- ⏳ Collect 5 years of raw data for all target tokens
- ⏳ Implement data collation (median, variance detection)

---

### Phase 2: Technical Indicators Agent

**Worker**: `technical-indicators-agent.ts` (new)

**Trigger**: Cloudflare Cron (runs every hour)

**Process**:
1. Query `price_data` for rows without indicators
2. For each symbol, fetch last 200+ candles for context
3. Calculate all technical indicators
4. Update `price_data` with calculated values

**Indicators to Calculate**:

**Trend Indicators**:
- SMA (10, 20, 50, 100, 200)
- EMA (10, 20, 30, 50, 200)
- MACD (12, 26, 9) - line, signal, histogram
- ADX (14) - trend strength

**Momentum Indicators**:
- RSI (14)
- Stochastic (14, 3, 3) - %K, %D
- Williams %R (14)
- CCI (20)
- Momentum (10)
- ROC (12)

**Volatility Indicators**:
- Bollinger Bands (20, 2) - upper, middle, lower, bandwidth, %B
- ATR (14)
- Keltner Channels (20, 2)
- Standard Deviation (20)

**Volume Indicators**:
- OBV (On-Balance Volume)
- Volume SMA (20)
- Volume Rate of Change
- Money Flow Index (14)

**Support/Resistance**:
- Pivot Points (Standard, Fibonacci, Camarilla)
- Swing highs/lows
- Previous day high/low/close

**Market Regime**:
- Trend direction (bullish, bearish, sideways)
- Volatility regime (low, medium, high)
- Volume regime (low, medium, high)

**Fear & Greed Index**:
- Fetch from Alternative.me API for each day
- Cache per-day to avoid redundant calls

**Schema Update**:
```sql
ALTER TABLE price_data ADD COLUMN
  -- Moving Averages
  sma_10 REAL,
  sma_20 REAL,
  sma_50 REAL,
  sma_100 REAL,
  sma_200 REAL,
  ema_10 REAL,
  ema_20 REAL,
  ema_30 REAL,
  ema_50 REAL,
  ema_200 REAL,

  -- MACD
  macd_line REAL,
  macd_signal REAL,
  macd_histogram REAL,
  macd_bullish_cross INTEGER,

  -- RSI
  rsi_14 REAL,
  rsi_overbought INTEGER,
  rsi_oversold INTEGER,

  -- Bollinger Bands
  bb_upper REAL,
  bb_middle REAL,
  bb_lower REAL,
  bb_bandwidth REAL,
  bb_percent_b REAL,

  -- Stochastic
  stoch_k REAL,
  stoch_d REAL,

  -- Volatility
  atr_14 REAL,
  volatility_regime TEXT,

  -- Volume
  obv REAL,
  volume_sma_20 REAL,

  -- Market Regime
  trend_direction TEXT,
  trend_strength REAL,

  -- Fear & Greed
  fear_greed_index INTEGER,
  fear_greed_classification TEXT,

  -- Flags
  indicators_calculated INTEGER DEFAULT 0,
  indicators_calculated_at INTEGER
;
```

**Implementation**:
```typescript
// cloudflare-agents/technical-indicators-agent.ts
import { SMA, EMA, MACD, RSI, BollingerBands, ATR, Stochastic } from 'technicalindicators';

interface Env {
  DB: D1Database;
}

export default {
  async scheduled(event: ScheduledEvent, env: Env, ctx: ExecutionContext) {
    // Fetch rows without indicators (batched)
    const rows = await env.DB.prepare(`
      SELECT * FROM price_data
      WHERE indicators_calculated = 0
      ORDER BY timestamp ASC
      LIMIT 1000
    `).all();

    // Group by symbol
    const bySymbol = groupBySymbol(rows.results);

    for (const [symbol, candles] of Object.entries(bySymbol)) {
      // Need historical context for indicators (200 candles)
      const context = await fetchContextCandles(env.DB, symbol, candles[0].timestamp, 200);
      const allCandles = [...context, ...candles];

      // Calculate indicators for each candle
      for (let i = context.length; i < allCandles.length; i++) {
        const indicators = calculateAllIndicators(allCandles.slice(0, i + 1));

        await env.DB.prepare(`
          UPDATE price_data
          SET
            sma_10 = ?, sma_20 = ?, sma_50 = ?,
            ema_10 = ?, ema_20 = ?, ema_30 = ?,
            macd_line = ?, macd_signal = ?, macd_histogram = ?,
            rsi_14 = ?,
            bb_upper = ?, bb_middle = ?, bb_lower = ?,
            atr_14 = ?,
            fear_greed_index = ?,
            indicators_calculated = 1,
            indicators_calculated_at = ?
          WHERE id = ?
        `).bind(
          indicators.sma10, indicators.sma20, indicators.sma50,
          indicators.ema10, indicators.ema20, indicators.ema30,
          indicators.macd.line, indicators.macd.signal, indicators.macd.histogram,
          indicators.rsi,
          indicators.bb.upper, indicators.bb.middle, indicators.bb.lower,
          indicators.atr,
          indicators.fearGreed,
          Date.now(),
          allCandles[i].id
        ).run();
      }
    }
  }
};
```

---

### Phase 3: Sentiment Analysis Agent

**Worker**: `sentiment-analysis-agent.ts` (new)

**Trigger**: Cloudflare Cron (runs every 6 hours)

**Data Sources**:
1. **News Headlines**:
   - CryptoPanic API (free tier: 100 req/day)
   - NewsAPI (free tier: 100 req/day)
   - CoinDesk RSS feed
   - CoinTelegraph RSS feed

2. **Fear & Greed Index**:
   - Alternative.me API (free, no key)
   - Historical data available

3. **Google Trends**:
   - Unofficial API or scraping
   - Search volume for "bitcoin", "crypto", etc.

4. **On-Chain Metrics**:
   - Glassnode (limited free tier)
   - Blockchain.com API (free)
   - Hash rate, miner revenue, exchange flows

5. **Social Media**:
   - Reddit API (sentiment on r/cryptocurrency, r/bitcoin)
   - Twitter API (mention counts, sentiment - paid)

6. **Company/Treasury News**:
   - SEC filings API (free)
   - Track MicroStrategy, Tesla, etc. holdings

**Storage**: `sentiment_data` table
```sql
CREATE TABLE sentiment_data (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,           -- YYYY-MM-DD
  timestamp INTEGER NOT NULL,   -- Unix timestamp (midnight UTC)

  -- News Headlines
  news_headline_count INTEGER,
  news_positive_count INTEGER,
  news_negative_count INTEGER,
  news_neutral_count INTEGER,
  news_sentiment_score REAL,    -- -1.0 to 1.0
  top_headlines TEXT,            -- JSON array

  -- Fear & Greed
  fear_greed_index INTEGER,
  fear_greed_classification TEXT,

  -- Google Trends
  trends_bitcoin INTEGER,        -- 0-100
  trends_crypto INTEGER,
  trends_altcoin INTEGER,

  -- On-Chain
  btc_hash_rate REAL,
  btc_miner_revenue REAL,
  btc_exchange_inflow REAL,
  btc_exchange_outflow REAL,
  btc_whale_transactions INTEGER,

  -- Social Media
  reddit_mentions INTEGER,
  reddit_sentiment REAL,
  twitter_mentions INTEGER,

  -- Treasury/Corporate
  corporate_buying INTEGER,      -- Boolean
  corporate_selling INTEGER,
  corporate_news TEXT,           -- JSON array

  -- Flags
  enriched INTEGER DEFAULT 0,
  enriched_at INTEGER,

  UNIQUE(date)
);
```

**Process**:
1. Query dates without sentiment data
2. For each date:
   - Fetch news headlines
   - Calculate sentiment scores
   - Fetch Fear & Greed Index
   - Get Google Trends data
   - Fetch on-chain metrics
   - Check for corporate/treasury news
3. Store in `sentiment_data` table
4. Link to `price_data` via date join

---

### Phase 4: Macroeconomic Agent

**Worker**: `macroeconomic-agent.ts` (new)

**Trigger**: Cloudflare Cron (runs daily)

**Data Sources**:
1. **FRED (Federal Reserve Economic Data)**:
   - API key required (free)
   - 500,000+ economic time series

2. **Treasury.gov**:
   - Treasury yields (2Y, 10Y, 30Y)
   - Free, no API key

3. **Yahoo Finance API** (unofficial):
   - Stock indices (S&P 500, NASDAQ, DXY)

4. **BLS (Bureau of Labor Statistics)**:
   - CPI (inflation)
   - Unemployment rate
   - NFP (Non-Farm Payrolls)

**Storage**: `macro_data` table
```sql
CREATE TABLE macro_data (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  timestamp INTEGER NOT NULL,

  -- Interest Rates
  fed_funds_rate REAL,
  treasury_2y REAL,
  treasury_10y REAL,
  treasury_30y REAL,
  yield_curve_2y10y REAL,       -- 10Y - 2Y (inversion indicator)

  -- Stock Market
  sp500_close REAL,
  sp500_change_pct REAL,
  nasdaq_close REAL,
  nasdaq_change_pct REAL,
  vix_close REAL,                -- Volatility index

  -- Dollar Strength
  dxy_close REAL,                -- US Dollar Index
  dxy_change_pct REAL,

  -- Inflation
  cpi REAL,
  cpi_yoy_pct REAL,
  ppi REAL,

  -- Employment
  unemployment_rate REAL,
  nfp INTEGER,                   -- Non-farm payrolls (monthly)

  -- Commodities
  gold_close REAL,
  oil_close REAL,

  -- Flags
  enriched INTEGER DEFAULT 0,
  enriched_at INTEGER,

  UNIQUE(date)
);
```

---

## Data Collation Strategy

For each timestamp, aggregate data from multiple sources:

```typescript
interface CollatedDataPoint {
  timestamp: number;
  symbol: string;

  // Price (from multiple sources)
  sources: Array<{
    name: string;
    price: number;
    volume: number;
  }>;

  // Aggregated Price
  median_price: number;
  mean_price: number;
  price_variance: number;
  source_count: number;
  confidence_score: number;     // 0-1 based on variance

  // Technical Indicators (calculated)
  indicators: TechnicalIndicators;

  // Sentiment (joined from sentiment_data by date)
  sentiment: SentimentData;

  // Macro (joined from macro_data by date)
  macro: MacroData;
}
```

**Benefits**:
1. Cross-validate prices across sources
2. Detect anomalies (flash crashes, manipulation)
3. Fill gaps if one source fails
4. Aggregate volume across DEXes
5. Identify arbitrage opportunities

---

## Implementation Timeline

### Week 1: Data Collection
- ✅ Deploy multi-source historical worker (5 sources)
- ⏳ Test which APIs work from Cloudflare Workers
- ⏳ Collect 5 years of raw OHLCV for BTC, SOL
- ⏳ Expand to top DeFi tokens

### Week 2: Technical Indicators
- Create `technical-indicators-agent.ts`
- Install `technicalindicators` library
- Deploy cron worker
- Process all historical data through indicator calculation
- Verify all 50+ indicators calculated correctly

### Week 3: Sentiment Analysis
- Create `sentiment-analysis-agent.ts`
- Integrate CryptoPanic, NewsAPI
- Integrate Fear & Greed Index
- Integrate on-chain metrics (Glassnode, Blockchain.com)
- Deploy cron worker
- Backfill 5 years of sentiment data

### Week 4: Macroeconomic Enrichment
- Create `macroeconomic-agent.ts`
- Integrate FRED API
- Integrate Treasury data
- Integrate stock market data
- Deploy cron worker
- Backfill 5 years of macro data

### Week 5: Full Pipeline Verification
- Verify all 5 years of data is enriched
- Check data quality (no missing values)
- Calculate coverage metrics
- Optimize queries for pattern discovery

---

## Storage Estimates

### price_data Table
- Tokens: 15 (BTC, SOL, + 13 DeFi)
- Candles per token: 525,600 (5 years × 5-min intervals)
- Total rows: 7,884,000
- Columns: ~100 (OHLCV + indicators)
- Est. size: ~10 GB

### sentiment_data Table
- Rows: 1,825 (5 years × 365 days)
- Columns: ~30
- Est. size: ~10 MB

### macro_data Table
- Rows: 1,825 (5 years × 365 days)
- Columns: ~20
- Est. size: ~5 MB

**Total**: ~10 GB (mostly price_data)

Cloudflare D1 limits:
- Free tier: 5 GB
- Paid tier: 500 GB
- **Action**: Upgrade to paid tier or use separate databases per token

---

## Pattern Discovery Queries

Once fully enriched, queries like:

```sql
-- Find profitable patterns
SELECT
  AVG(entry_rsi_14) as avg_rsi,
  AVG(entry_macd_histogram) as avg_macd,
  AVG(fear_greed_index) as avg_fear_greed,
  AVG(sp500_change_pct) as avg_sp500_change,
  COUNT(*) as occurrences
FROM chaos_trades
JOIN sentiment_data ON DATE(chaos_trades.entry_time / 1000, 'unixepoch') = sentiment_data.date
JOIN macro_data ON DATE(chaos_trades.entry_time / 1000, 'unixepoch') = macro_data.date
WHERE profitable = 1
  AND entry_rsi_14 < 30
  AND entry_bb_percent_b < 0
  AND fear_greed_index < 25
GROUP BY
  ROUND(entry_rsi_14 / 5) * 5,
  entry_macd_histogram > 0
HAVING occurrences > 100;
```

This enables discovery of patterns like:
- "When RSI < 30, MACD histogram positive, Fear & Greed < 25, and S&P 500 down > 2%, BTC tends to rally within 24h with 73% probability"

---

## Next Steps

1. **Immediate**: Test deployed historical worker with 5 data sources
2. **Today**: Start collecting 5 years of BTC/SOL data
3. **This Week**: Build technical indicators agent
4. **Next Week**: Build sentiment agent
5. **Following Week**: Build macro agent
6. **Then**: Fully enriched pattern discovery system ready

---

## Notes

- All workers designed to run on Cloudflare Workers (serverless, global edge)
- Cron triggers ensure continuous enrichment
- Rate limiting handled by multi-source fallback
- Data quality ensured by variance detection
- Ready for ML/AI pattern discovery after enrichment
