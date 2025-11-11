# Real Data Collection Guide

## Problem Identified

The existing 140,050 chaos trades are **useless for pattern discovery** because they only have 6 columns:
- entry_time, exit_time, entry_price, exit_price, pnl_pct, profitable
- **Missing**: RSI, MACD, Bollinger Bands, sentiment, pair info, day of week, etc.

Without full context, we cannot discover meaningful patterns.

## Solution: Fresh Start with REAL Data

### Step 1: Populate Historical Price Data

Since Binance API is blocked from Cloudflare Workers (HTTP 451), run this script **locally** to fetch and upload data:

```bash
cd scripts

# Upload 30 days of BTC data (~8,640 candles at 5m interval)
./upload-binance-data.sh BTCUSDT 5m 8640

# Upload ETH data
./upload-binance-data.sh ETHUSDT 5m 8640

# Upload SOL data
./upload-binance-data.sh SOLUSDT 5m 8640
```

**Why this works:**
- Your local IP isn't blocked by Binance
- Script fetches from Binance directly
- Uploads to Cloudflare Worker's `/upload-candles` endpoint
- Worker stores in `price_data` table

### Step 2: Verify Data Loaded

```bash
curl https://coinswarm-evolution-agent.bamn86.workers.dev/debug/db | jq '.price_data'
```

Should show:
```json
{
  "count": 25920,  // 8640 * 3 pairs
  "sample": [...]
}
```

### Step 3: Generate New Chaos Trades (Coming Next)

Once price_data is populated, we'll:
1. Apply full schema migration (100+ columns to chaos_trades)
2. Rewrite `generateChaosTrades()` to:
   - Query random time segments from price_data
   - Calculate ALL technical indicators
   - Fetch sentiment data for that timestamp
   - Generate trades with FULL context

### Step 4: Clear Old Useless Trades

```sql
-- Mark old trades as invalid
UPDATE chaos_trades SET profitable = -1 WHERE id < 140051;
-- OR delete them entirely
DELETE FROM chaos_trades WHERE id < 140051;
```

## Technical Details

### price_data Schema
```sql
CREATE TABLE price_data (
  id INTEGER PRIMARY KEY,
  symbol TEXT NOT NULL,           -- BTCUSDT, ETHUSDT, SOLUSDT
  timestamp INTEGER NOT NULL,     -- Unix timestamp (seconds)
  timeframe TEXT NOT NULL,        -- 5m, 15m, 1h, 1d
  open REAL NOT NULL,
  high REAL NOT NULL,
  low REAL NOT NULL,
  close REAL NOT NULL,
  volume REAL NOT NULL,
  UNIQUE(symbol, timestamp, timeframe)
);
```

### Full chaos_trades Schema (After Migration)
- **Technical Indicators**: RSI, MACD, Bollinger Bands, SMA, EMA, Stochastic, ATR, momentum
- **Sentiment Data**: Fear & Greed Index, news headline counts, Google Trends
- **Temporal Features**: Day of week, hour of day, month, market hours
- **Market Context**: Trend regime, volatility regime, support/resistance levels

Total: **100+ individual columns** for pattern discovery

## Timeline

1. ✅ Created `/upload-candles` endpoint
2. ✅ Created local upload script
3. ⏳ **YOU RUN**: Upload 30 days of data for BTC/ETH/SOL
4. ⏳ Deploy schema migrations for full chaos_trades schema
5. ⏳ Rewrite chaos generation to use price_data
6. ⏳ Generate fresh trades with full context
7. ✅ Start discovering REAL patterns

## Next Steps

Run the upload script NOW to start collecting real data:

```bash
cd /home/user/Coinswarm/scripts
./upload-binance-data.sh BTCUSDT 5m 8640
```

This will take ~2 minutes to fetch and upload 8,640 candles (30 days at 5-minute intervals).
