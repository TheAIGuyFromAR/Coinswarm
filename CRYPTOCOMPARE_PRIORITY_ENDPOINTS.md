# CryptoCompare: 7 Priority Endpoints for Evolution Trading

Beyond the already documented endpoints (OHLCV, news, multi-exchange, blockchain, social), here are 7 additional high-value endpoints to implement:

---

## 1. **Top Pairs by Volume** - `/data/v2/pair/mapping/fsym`
**Endpoint:** `topPairs()`
**API:** `https://min-api.cryptocompare.com/data/top/pairs`

**Purpose:** Identify which trading pairs are seeing the most volume RIGHT NOW

**Value for Evolution System:**
- Detect trending pairs before price moves
- Focus data collection on highest liquidity pairs
- Pattern discovery: "When BTC/ETH volume spikes X%, price follows Y% in Z hours"

**Response Data:**
- Symbol pair
- Exchange
- 24h volume (from/to)
- Last price
- Top exchange for pair

**Collection Frequency:** Every 15 minutes

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS top_pairs_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp INTEGER NOT NULL,
  rank INTEGER NOT NULL,
  from_symbol TEXT NOT NULL,
  to_symbol TEXT NOT NULL,
  exchange TEXT NOT NULL,
  volume_24h_from REAL,
  volume_24h_to REAL,
  price REAL,
  created_at INTEGER DEFAULT (unixepoch()),
  UNIQUE(timestamp, rank, from_symbol, to_symbol)
);
```

**Pattern Discovery Potential:**
- "Top 10 volume rank changes predict price moves 78% of time"
- "When BTCUSDT becomes #1 pair on 3+ exchanges, volatility increases"

---

## 2. **Top Exchanges Full Data** - `/data/top/exchanges/full`
**Endpoint:** `topExchangesFull()`
**API:** `https://min-api.cryptocompare.com/data/top/exchanges/full`

**Purpose:** Complete exchange rankings with volume, price, and liquidity metrics

**Value for Evolution System:**
- Enhanced arbitrage detection (already planned, but this adds depth)
- Detect exchange-specific patterns
- Identify which exchanges lead vs lag price moves

**Response Data (per exchange):**
- Exchange name
- From/to symbols
- Volume 24h (both currencies)
- Open, High, Low, Close (24h)
- Change %
- Change absolute
- Supply
- Market cap

**Collection Frequency:** Every 5 minutes

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS exchange_rankings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp INTEGER NOT NULL,
  rank INTEGER NOT NULL,
  exchange TEXT NOT NULL,
  symbol TEXT NOT NULL,
  price REAL NOT NULL,
  volume_24h_from REAL,
  volume_24h_to REAL,
  high_24h REAL,
  low_24h REAL,
  change_pct_24h REAL,
  market_share_pct REAL, -- Calculated: this exchange's volume / total volume
  created_at INTEGER DEFAULT (unixepoch()),
  UNIQUE(timestamp, exchange, symbol)
);
```

**Pattern Discovery Potential:**
- "When Binance volume exceeds Coinbase by >15%, price follows Binance direction"
- "Exchange A leads price moves by 3 minutes on average"

---

## 3. **Mining Equipment Data** - `/data/miningequipment`
**Endpoint:** Mining equipment specifications and profitability
**API:** `https://min-api.cryptocompare.com/data/miningequipment`

**Purpose:** Track mining hardware economics for network health signals

**Value for Evolution System:**
- Mining profitability predicts miner selling pressure
- Hash rate hardware deployment signals
- Network security metrics

**Response Data:**
- Equipment name/model
- Hash rate
- Power consumption
- Algorithm
- Cost
- Profitability
- ROI timeframe

**Collection Frequency:** Daily (equipment specs don't change often)

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS mining_profitability (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp INTEGER NOT NULL,
  symbol TEXT NOT NULL,
  equipment_name TEXT NOT NULL,
  hash_rate REAL,
  power_watts REAL,
  daily_revenue_usd REAL,
  daily_cost_usd REAL,
  daily_profit_usd REAL,
  roi_days INTEGER,
  profitability_index REAL, -- Revenue / Cost ratio
  created_at INTEGER DEFAULT (unixepoch()),
  UNIQUE(timestamp, symbol, equipment_name)
);
```

**Pattern Discovery Potential:**
- "When mining profitability drops <$X/day, BTC price drops within 48h (miners selling)"
- "Hash rate changes lag profitability by Y days"

---

## 4. **Constituent Exchange List** - CCCAGG Index Components
**Endpoint:** `constituentExchangeList()`
**API:** `https://min-api.cryptocompare.com/data/cc/v1/constituents/exchanges`

**Purpose:** See which exchanges contribute to the CCCAGG aggregated index

**Value for Evolution System:**
- Understand index construction
- Detect when major exchanges drop out (liquidity crisis)
- Weight data sources by index inclusion

**Response Data:**
- Exchange name
- Inclusion status
- Weight in index
- Excluded reason (if any)
- Last update

**Collection Frequency:** Hourly

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS cccagg_constituents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp INTEGER NOT NULL,
  symbol TEXT NOT NULL,
  exchange TEXT NOT NULL,
  included BOOLEAN NOT NULL,
  weight_pct REAL,
  exclusion_reason TEXT,
  created_at INTEGER DEFAULT (unixepoch()),
  UNIQUE(timestamp, symbol, exchange)
);
```

**Pattern Discovery Potential:**
- "When 2+ major exchanges excluded from CCCAGG, price volatility increases 200%"
- "Index constituent changes predict arbitrage opportunities"

---

## 5. **Volume-Weighted Average Price** - `/data/generateAvg`
**Endpoint:** `generateAvg()`
**API:** `https://min-api.cryptocompare.com/data/generateAvg`

**Purpose:** Calculate VWAP across multiple exchanges in real-time

**Value for Evolution System:**
- Better "true price" than single exchange
- Detect when individual exchanges deviate from VWAP
- Entry/exit signals when price crosses VWAP

**Request Parameters:**
- From/to symbols
- Markets (list of exchanges)

**Response Data:**
- VWAP price
- Volume-weighted from each exchange
- Last trade
- Last volume
- 24h metrics

**Collection Frequency:** Every 1 minute

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS vwap_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp INTEGER NOT NULL,
  symbol TEXT NOT NULL,
  vwap_price REAL NOT NULL,
  total_volume_24h REAL,
  num_exchanges INTEGER,
  exchanges_list TEXT, -- JSON array
  created_at INTEGER DEFAULT (unixepoch()),
  UNIQUE(timestamp, symbol)
);

-- Deviation tracking
CREATE TABLE IF NOT EXISTS exchange_vwap_deviation (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp INTEGER NOT NULL,
  symbol TEXT NOT NULL,
  exchange TEXT NOT NULL,
  exchange_price REAL NOT NULL,
  vwap_price REAL NOT NULL,
  deviation_pct REAL NOT NULL, -- (exchange_price - vwap) / vwap * 100
  volume_weight REAL,
  created_at INTEGER DEFAULT (unixepoch()),
  UNIQUE(timestamp, symbol, exchange)
);
```

**Pattern Discovery Potential:**
- "When Binance price deviates >0.5% from VWAP, reversion occurs within 10 minutes"
- "VWAP crossovers predict trend changes with 72% accuracy"

---

## 6. **Latest Social Stats** - `/data/social/coin/latest`
**Endpoint:** `socialStats()` / `latestSocial()`
**API:** `https://min-api.cryptocompare.com/data/social/coin/latest`

**Purpose:** Real-time social media engagement metrics

**Value for Evolution System:**
- Already have news sentiment, this adds REAL-TIME social signals
- Detect viral moments before price impact
- Reddit/Twitter activity predicts volume spikes

**Response Data:**
- CryptoCompare followers
- Twitter followers
- Twitter account age
- Twitter statuses
- Twitter favorites
- Reddit subscribers
- Reddit active users
- Reddit posts per hour
- Reddit comments per hour
- CodeRepository stats (GitHub stars, forks)

**Collection Frequency:** Every 15 minutes

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS social_stats_realtime (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp INTEGER NOT NULL,
  symbol TEXT NOT NULL,

  -- Twitter
  twitter_followers INTEGER,
  twitter_statuses INTEGER,
  twitter_favorites INTEGER,
  twitter_lists INTEGER,
  twitter_following INTEGER,

  -- Reddit
  reddit_subscribers INTEGER,
  reddit_active_users INTEGER,
  reddit_posts_hour INTEGER,
  reddit_comments_hour INTEGER,

  -- GitHub (if applicable)
  github_stars INTEGER,
  github_forks INTEGER,
  github_watchers INTEGER,

  -- Composite scores
  social_volume_score REAL, -- Posts + comments + tweets
  social_engagement_score REAL, -- Favorites + upvotes + stars

  created_at INTEGER DEFAULT (unixepoch()),
  UNIQUE(timestamp, symbol)
);
```

**Pattern Discovery Potential:**
- "Reddit comments spike >200% = price move within 4 hours (65% accuracy)"
- "Twitter follower velocity predicts sustained trends"
- "GitHub commit activity on DeFi projects = price leading indicator"

---

## 7. **Top Coins by Volume (Full Data)** - `/data/top/totalvolfull`
**Endpoint:** `topVolumeFull()`
**API:** `https://min-api.cryptocompare.com/data/top/totalvolfull`

**Purpose:** Complete market overview - which coins are hot right now

**Value for Evolution System:**
- Identify rotation between coins
- Detect "risk-on" vs "risk-off" shifts
- Allocate agent focus to highest volume assets

**Response Data (per coin):**
- Coin symbol/name
- Total volume 24h (USD)
- Market cap
- Supply (circulating/total)
- Price
- Change % (1h, 24h, 7d)
- Rank

**Collection Frequency:** Every 10 minutes

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS top_coins_volume (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp INTEGER NOT NULL,
  rank INTEGER NOT NULL,
  symbol TEXT NOT NULL,
  name TEXT NOT NULL,
  total_volume_24h_usd REAL NOT NULL,
  market_cap_usd REAL,
  price_usd REAL,
  circulating_supply REAL,
  change_pct_1h REAL,
  change_pct_24h REAL,
  change_pct_7d REAL,
  created_at INTEGER DEFAULT (unixepoch()),
  UNIQUE(timestamp, rank)
);

-- Track rank changes
CREATE TABLE IF NOT EXISTS coin_rank_movements (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol TEXT NOT NULL,
  from_rank INTEGER NOT NULL,
  to_rank INTEGER NOT NULL,
  rank_change INTEGER NOT NULL,
  timestamp_start INTEGER NOT NULL,
  timestamp_end INTEGER NOT NULL,
  duration_minutes INTEGER NOT NULL,
  created_at INTEGER DEFAULT (unixepoch())
);
```

**Pattern Discovery Potential:**
- "When BTC drops out of top 3 volume = market fear, alts dump"
- "Coins jumping >10 ranks in volume = 85% chance of continued rally"
- "Volume rotation from BTC→ETH→Alts = bull market signature"

---

## Implementation Priority

1. **Top Pairs by Volume** - Quickest to implement, immediate pattern value
2. **VWAP Across Exchanges** - Critical for accurate pricing
3. **Latest Social Stats** - Real-time sentiment (complement existing news)
4. **Top Exchanges Full** - Enhance arbitrage detection
5. **Top Coins by Volume** - Market context/rotation signals
6. **Constituent Exchange List** - Index understanding
7. **Mining Profitability** - Longer-term network health signals

---

## Rate Limit Impact

**Free Tier Budget:** 100,000 calls/month (~3,333/day, ~139/hour)

**New Endpoint Usage:**
- Top Pairs: 4/hour = 96/day
- VWAP: 60/hour = 1,440/day ⚠️ (Largest consumer)
- Social Stats: 4/hour = 96/day
- Top Exchanges: 12/hour = 288/day
- Top Coins: 6/hour = 144/day
- Constituents: 1/hour = 24/day
- Mining: 1/day = 1/day

**Total New:** ~2,089/day additional

**Combined with existing:** ~2,500-3,000/day (still within free tier!)

---

## Evolution System Benefits

These endpoints enable NEW pattern categories:

1. **Volume Migration Patterns:** Track how volume flows between pairs/exchanges/coins
2. **Social→Price Lag Patterns:** Reddit spike → price move timing
3. **Exchange Leader/Follower:** Which exchanges predict vs follow
4. **VWAP Reversion:** Mean reversion trades around volume-weighted averages
5. **Rank Change Momentum:** Coin ranking changes as momentum signals
6. **Mining Economics:** Network economics predict selling pressure
7. **Constituent Changes:** Index adjustments = volatility opportunities

**Total Pattern Expansion:** 7 new pattern categories × 196,749 existing chaos trades = **massive discovery potential**
