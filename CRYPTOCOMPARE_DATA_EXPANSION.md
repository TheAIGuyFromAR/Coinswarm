# CryptoCompare Data Expansion Plan

Based on user requirements for:
1. Enhanced news and sentiment
2. On-chain/block data
3. Multi-exchange price data for arbitrage detection

## Currently Collecting

✅ **OHLCV Historical Data**
- Endpoint: `/data/v2/histominute`, `/data/v2/histohour`, `/data/v2/histoday`
- Fields: open, high, low, close, volumefrom, volumeto
- Timeframes: 1m, 1h, 1d

✅ **Basic News Sentiment**
- Endpoint: `/data/v2/news/`
- Storage: `news_articles` table, `sentiment_snapshots`

## NEW: Multi-Exchange Price Data (Arbitrage Detection)

### Endpoint: `/data/pricemulti` or `/data/pricemultifull`
**Purpose:** Get current prices across multiple exchanges simultaneously
**Use Case:** Detect price discrepancies for arbitrage opportunities

**Example Request:**
```
https://min-api.cryptocompare.com/data/pricemultifull?fsyms=BTC,ETH,SOL&tsyms=USD,USDT&e=Coinbase,Binance,Kraken,Gemini
```

**Response includes per exchange:**
- `PRICE`: Current price
- `LASTVOLUME`: Last trade volume
- `LASTVOLUMETO`: Last trade value
- `LASTTRADEID`: Trade ID
- `VOLUME24HOUR`: 24h volume
- `VOLUME24HOURTO`: 24h volume in quote currency
- `OPEN24HOUR`, `HIGH24HOUR`, `LOW24HOUR`
- `CHANGE24HOUR`, `CHANGEPCT24HOUR`
- `LASTUPDATE`: Timestamp

**Schema Addition Needed:**
```sql
CREATE TABLE IF NOT EXISTS exchange_prices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol TEXT NOT NULL,
  exchange TEXT NOT NULL,
  timestamp INTEGER NOT NULL,
  price REAL NOT NULL,
  volume_24h REAL,
  volume_24h_to REAL,
  change_pct_24h REAL,
  bid REAL,
  ask REAL,
  spread_pct REAL,
  created_at INTEGER DEFAULT (unixepoch()),
  UNIQUE(symbol, exchange, timestamp)
);

CREATE INDEX idx_exchange_prices_symbol_time ON exchange_prices(symbol, timestamp DESC);
CREATE INDEX idx_exchange_prices_time ON exchange_prices(timestamp DESC);

-- Arbitrage opportunities detected
CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol TEXT NOT NULL,
  buy_exchange TEXT NOT NULL,
  sell_exchange TEXT NOT NULL,
  buy_price REAL NOT NULL,
  sell_price REAL NOT NULL,
  spread_pct REAL NOT NULL,
  potential_profit_pct REAL NOT NULL,
  volume_available REAL,
  detected_at INTEGER NOT NULL,
  created_at INTEGER DEFAULT (unixepoch())
);

CREATE INDEX idx_arbitrage_symbol_spread ON arbitrage_opportunities(symbol, spread_pct DESC);
CREATE INDEX idx_arbitrage_detected ON arbitrage_opportunities(detected_at DESC);
```

## NEW: On-Chain / Blockchain Data

### Endpoint: `/data/blockchain/latest`
**Purpose:** Get latest blockchain metrics
**Fields Available:**
- Block height
- Hash rate
- Difficulty
- Transaction count
- Average block time
- Average transaction value
- Active addresses (24h)
- New addresses (24h)

### Endpoint: `/data/blockchain/histo/day`
**Purpose:** Historical blockchain metrics
**Use Case:** Detect on-chain trends (accumulation, distribution)

**Schema Addition Needed:**
```sql
CREATE TABLE IF NOT EXISTS blockchain_metrics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol TEXT NOT NULL,
  timestamp INTEGER NOT NULL,

  -- Network activity
  transaction_count INTEGER,
  active_addresses INTEGER,
  new_addresses INTEGER,

  -- Value metrics
  avg_transaction_value REAL,
  median_transaction_value REAL,
  total_transaction_volume REAL,

  -- Network health
  hash_rate REAL,
  difficulty REAL,
  block_time REAL,
  block_height INTEGER,

  -- Exchange flows
  exchange_inflow REAL,   -- CryptoCompare provides this
  exchange_outflow REAL,
  exchange_netflow REAL,

  created_at INTEGER DEFAULT (unixepoch()),
  UNIQUE(symbol, timestamp)
);

CREATE INDEX idx_blockchain_metrics_symbol_time ON blockchain_metrics(symbol, timestamp DESC);
```

## NEW: Enhanced News with Social Metrics

### Endpoint: `/data/v2/news/`
**Current:** Basic news collection
**Enhancement:** Add social metrics

**Additional Fields Available:**
- Source reputation score
- Social media engagement
- Upvotes/downvotes
- Categories (regulation, adoption, hack, etc.)
- Tags (DeFi, NFT, Layer2, etc.)

### Endpoint: `/data/social/coin/histo/hour`
**Purpose:** Social media metrics (Reddit, Twitter mentions)
**Fields:**
- Comments
- Posts
- Followers
- Points (engagement score)
- Lists (watchlists)
- Account age average

**Schema Enhancement:**
```sql
-- Enhance existing news_articles table (already has some of these)
ALTER TABLE news_articles ADD COLUMN social_score REAL; -- Social media engagement
ALTER TABLE news_articles ADD COLUMN upvotes INTEGER;
ALTER TABLE news_articles ADD COLUMN downvotes INTEGER;
ALTER TABLE news_articles ADD COLUMN tags TEXT; -- JSON array

-- New social metrics table
CREATE TABLE IF NOT EXISTS social_metrics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol TEXT NOT NULL,
  timestamp INTEGER NOT NULL,

  -- Reddit metrics
  reddit_posts_hour INTEGER,
  reddit_comments_hour INTEGER,
  reddit_active_users INTEGER,

  -- Twitter metrics (if available)
  twitter_mentions_hour INTEGER,
  twitter_sentiment REAL, -- -1 to 1

  -- Community engagement
  engagement_score REAL, -- Composite metric
  trending_rank INTEGER, -- How it ranks vs other coins

  created_at INTEGER DEFAULT (unixepoch()),
  UNIQUE(symbol, timestamp)
);
```

## NEW: Order Book / Market Depth

### Endpoint: `/data/ob/l2/snapshot`
**Purpose:** Level 2 order book snapshot
**Use Case:** Detect support/resistance levels, liquidity

**Data:**
- Bid/ask levels (top 100)
- Depth at each price
- Spread metrics
- Liquidity score

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS market_depth_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol TEXT NOT NULL,
  exchange TEXT NOT NULL,
  timestamp INTEGER NOT NULL,

  -- Best bid/ask
  best_bid REAL NOT NULL,
  best_ask REAL NOT NULL,
  spread_pct REAL NOT NULL,

  -- Depth metrics
  bid_depth_1pct REAL, -- Total volume within 1% of best bid
  ask_depth_1pct REAL,
  bid_depth_5pct REAL,
  ask_depth_5pct REAL,

  -- Liquidity score (0-100)
  liquidity_score REAL,

  -- Order book imbalance (-1 to 1, negative = more sellers)
  imbalance REAL,

  created_at INTEGER DEFAULT (unixepoch()),
  UNIQUE(symbol, exchange, timestamp)
);
```

## Implementation Priority

### Phase 1: Multi-Exchange Prices (Immediate Value)
**Worker:** Create `multi-exchange-price-collector-cron.ts`
**Frequency:** Every 1 minute
**Benefit:** Detect arbitrage opportunities that recur
**Endpoints:**
- `/data/pricemultifull`

### Phase 2: On-Chain Metrics (High Value)
**Worker:** Create `blockchain-metrics-cron.ts`
**Frequency:** Every 1 hour
**Benefit:** Detect accumulation/distribution before price moves
**Endpoints:**
- `/data/blockchain/latest`
- `/data/blockchain/histo/day`

### Phase 3: Enhanced Social Metrics
**Worker:** Enhance existing `news-sentiment-agent.ts`
**Frequency:** Every 15 minutes
**Benefit:** Better sentiment accuracy with social signals
**Endpoints:**
- `/data/social/coin/histo/hour`
- `/data/v2/news/` (enhanced fields)

### Phase 4: Market Depth (Advanced)
**Worker:** Create `market-depth-cron.ts`
**Frequency:** Every 5 minutes
**Benefit:** Detect liquidity changes, support/resistance
**Endpoints:**
- `/data/ob/l2/snapshot`

## Rate Limit Strategy

**CryptoCompare Free Tier:**
- 100,000 calls/month
- ~3,333 calls/day
- ~139 calls/hour
- ~2.3 calls/minute

**Current Usage:**
- Historical collection: ~30 calls/hour
- Realtime collection: ~15 calls/minute (900/hour)

**Available Budget:**
- Phase 1 (multi-exchange): 15 calls/min = 900/hour
- Phase 2 (blockchain): 15 calls/hour = 360/day
- Phase 3 (social): 4 calls/hour = 96/day
- Phase 4 (depth): 12 calls/hour = 288/day

**Total if all phases:** ~2,200 calls/hour (within free tier with careful rate limiting)

## Next Steps

1. Create schemas for multi-exchange prices
2. Build multi-exchange-price-collector worker
3. Implement arbitrage opportunity detection
4. Test with small token set first
5. Expand to blockchain metrics
6. Enhance social/news collection

---

**Status:** Planning complete, ready for implementation
**Estimated Timeline:**
- Phase 1: 2-3 hours
- Phase 2: 2-3 hours
- Phase 3: 1-2 hours
- Phase 4: 3-4 hours
