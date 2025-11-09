# Multi-Source Parallel Data Collection Strategy

## Goal
Max out all 5 data sources simultaneously while collecting missing data, then run 25% slower for safety.

---

## Available Data Sources & Rate Limits

### 1. CoinGecko
- **Rate Limit**: 30 calls/min (with API key)
- **Data Type**: Daily OHLC for major tokens (BTC, ETH, SOL, BNB, etc.)
- **Coverage**: All major cryptocurrencies
- **Max Days Per Call**: 365 days

### 2. GeckoTerminal
- **Rate Limit**: 30 calls/min
- **Data Type**: DEX pool OHLCV (5m, 15m, 1h, 4h, 12h, 1d timeframes)
- **Coverage**: 100+ networks (Ethereum, BSC, Solana, Arbitrum, Optimism, etc.)
- **Best For**: DeFi tokens (RAY, ORCA, CAKE, VELO, etc.)

### 3. CryptoCompare
- **Rate Limit**: 30 calls/min (with API key)
- **Data Type**: Minute-level OHLCV for CEX pairs
- **Coverage**: Major CEX tokens
- **Max Per Call**: 2000 data points

### 4. DexScreener
- **Rate Limit**: 300 calls/min (DEX/Pairs endpoints)
- **Data Type**: Current prices + 24h volume (no historical OHLCV)
- **Coverage**: 50+ chains, real-time DEX data
- **Best For**: Price validation, not historical collection

### 5. Binance.US
- **Rate Limit**: 1200 weight/min (IP-based)
- **Data Type**: Klines (OHLCV) for all timeframes
- **Coverage**: Major pairs on Binance.US
- **Max Per Call**: 1000 candles

---

## Parallel Collection Strategy

### Source Assignment by Token Type

**CoinGecko (30 calls/min)**:
- BTC, ETH, SOL, BNB, MATIC
- Daily OHLC, 5 years = 5 tokens × 5 calls (365 days each) = 25 calls
- Time: 1 minute

**GeckoTerminal (30 calls/min)**:
- RAY, ORCA, JUP, ARB, GMX, OP, VELO, QUICK, AERO, CAKE
- 10 DeFi tokens × 5 calls (365 days each) = 50 calls
- Time: 2 minutes (split across 2 rounds)

**CryptoCompare (30 calls/min)**:
- All 15 tokens, minute-level data
- 15 tokens × 61 calls (30 days each, 5 years total) = 915 calls
- Time: 30 minutes (fills gaps with minute granularity)

**Binance.US (1200 calls/min)**:
- All Binance-listed tokens (BTC, ETH, SOL, BNB)
- 4 tokens × 10 calls (200 days each) = 40 calls
- Time: <1 minute (very fast, used for validation)

**DexScreener (300 calls/min)**:
- Real-time price validation only
- Skip historical collection (no OHLCV support)
- Used for error checking/gap detection

---

## Parallel Execution Plan

### Worker 1: CoinGecko Collector (30/min)
```
Loop:
  1. Get next major token (BTC, ETH, SOL, BNB, MATIC)
  2. Fetch 365 days of daily OHLC
  3. Store in price_data with source='coingecko'
  4. Sleep 2 seconds (30 calls/min)
  5. Repeat until all 5 tokens complete
```

### Worker 2: GeckoTerminal Collector (30/min)
```
Loop:
  1. Get next DeFi token (RAY, ORCA, JUP, ARB, etc.)
  2. Search for best pool on relevant network
  3. Fetch 365 days of daily OHLCV
  4. Store in price_data with source='geckoterminal'
  5. Sleep 2 seconds (30 calls/min)
  6. Repeat until all 10 DeFi tokens complete
```

### Worker 3: CryptoCompare Collector (30/min)
```
Loop:
  1. Get next token (any of 15)
  2. Fetch minute-level data (2000 points = ~33 hours)
  3. Store in price_data with source='cryptocompare'
  4. Sleep 2 seconds (30 calls/min)
  5. Repeat for all time ranges
```

### Worker 4: Binance.US Validator (1200/min)
```
Loop:
  1. Get tokens with missing data or gaps
  2. Fetch klines to fill gaps
  3. Store with source='binance'
  4. Sleep 50ms (1200 calls/min)
  5. Run continuously to fill any detected gaps
```

---

## Gap Detection & Filling

### Strategy
1. **Primary collection**: CoinGecko + GeckoTerminal fill bulk daily data
2. **Gap detection**: Query price_data for missing timestamps
3. **Fill gaps**: Use CryptoCompare for minute data, Binance for validation
4. **Cross-validation**: Compare prices across sources, flag anomalies

### SQL for Gap Detection
```sql
-- Find missing days for a token
WITH RECURSIVE dates AS (
  SELECT date('2020-01-01') as d
  UNION ALL
  SELECT date(d, '+1 day')
  FROM dates
  WHERE d < date('2025-01-01')
)
SELECT d
FROM dates
LEFT JOIN price_data ON dates.d = date(price_data.timestamp, 'unixepoch')
WHERE price_data.timestamp IS NULL
  AND symbol = 'BTCUSDT'
ORDER BY d;
```

---

## Rate Limiting - 75% of Max

### Current Limits (100%)
- CoinGecko: 30 calls/min
- GeckoTerminal: 30 calls/min
- CryptoCompare: 30 calls/min
- Binance.US: 1200 calls/min
- DexScreener: 300 calls/min

### Target Limits (75%)
- CoinGecko: **22.5 calls/min** → 2.67s delay
- GeckoTerminal: **22.5 calls/min** → 2.67s delay
- CryptoCompare: **22.5 calls/min** → 2.67s delay
- Binance.US: **900 calls/min** → 67ms delay
- DexScreener: **225 calls/min** → 267ms delay

### Then Slow Down 25% More (56.25% of max)
- CoinGecko: **16.9 calls/min** → 3.56s delay
- GeckoTerminal: **16.9 calls/min** → 3.56s delay
- CryptoCompare: **16.9 calls/min** → 3.56s delay
- Binance.US: **675 calls/min** → 89ms delay
- DexScreener: **169 calls/min** → 356ms delay

---

## Implementation Architecture

### Option 1: Single Worker with Parallel Loops
```typescript
async function runParallelCollection(env: Env, ctx: ExecutionContext) {
  // Start all collectors in parallel
  ctx.waitUntil(Promise.all([
    coinGeckoCollector(env),
    geckoTerminalCollector(env),
    cryptoCompareCollector(env),
    binanceValidator(env)
  ]));
}
```

### Option 2: Separate Cron Workers
- Deploy 4 separate workers, each with its own cron schedule
- Each worker focuses on one data source
- Coordinate via shared D1 database

**Recommended**: Option 1 (single worker, parallel async loops)

---

## Data Deduplication & Merging

### Storage Strategy
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
  source TEXT NOT NULL,        -- Which API provided this data
  providers INTEGER DEFAULT 1,  -- How many sources agree
  price_variance REAL DEFAULT 0, -- Variance across sources
  created_at INTEGER,
  UNIQUE(symbol, timestamp, timeframe, source) -- Allow multiple sources for same timestamp
);
```

### Merging Algorithm
```typescript
// When multiple sources have data for same timestamp:
1. Calculate median price across sources
2. Calculate variance
3. Flag high variance (>1%) for review
4. Store all source data separately
5. Create aggregated view with median values
```

---

## Estimated Completion Time

### Parallel Collection (56.25% of limits)
- CoinGecko: 5 tokens × 5 calls ÷ 16.9/min = **1.5 minutes**
- GeckoTerminal: 10 tokens × 5 calls ÷ 16.9/min = **3 minutes**
- CryptoCompare: 915 calls ÷ 16.9/min = **54 minutes**
- Binance: 40 calls ÷ 675/min = **<1 minute** (fills gaps continuously)

**Total time running all in parallel**: ~54 minutes (limited by CryptoCompare)

### Sequential Collection (original plan)
- 915 calls ÷ 16.9/min = **54 minutes**

**Speedup**: Minimal for collection (since CryptoCompare is bottleneck), but huge for coverage (multiple sources, cross-validation, gap filling)

---

## Benefits of Parallel Multi-Source

1. **Redundancy**: If one API fails, others continue
2. **Data Quality**: Cross-validation across sources
3. **Coverage**: Different sources for different tokens
4. **Gap Filling**: Binance fills any detected gaps
5. **Granularity**: Mix of daily (CoinGecko) and minute (CryptoCompare) data
6. **Speed**: All sources working simultaneously
7. **Fault Tolerance**: Auto-pause bad sources, continue with others

---

## Next Steps

1. Modify cron worker to run 4 parallel collectors
2. Implement gap detection SQL queries
3. Add cross-source price validation
4. Set delays to 56.25% of limits (75% × 0.75 = 56.25%)
5. Add logging for source health monitoring
6. Deploy and monitor for 1 hour

---

**Result**: Complete 5-year dataset with multiple sources, cross-validated, gap-free, in ~1 hour.
