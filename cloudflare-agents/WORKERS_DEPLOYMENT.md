# Coinswarm Cloudflare Workers Deployment Guide

**IMPORTANT:** See `CHAOS_TRADING_ARCHITECTURE.md` for the full philosophical and technical architecture.

## Quick Summary

We use **chaos trading** on **real historical data** to discover novel trading patterns through empirical outcomes, not by curve-fitting to price patterns.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLOUDFLARE WORKERS SYSTEM                     │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────┐      ┌──────────────────────┐
│  Historical Data     │──────▶│  Evolution Agent     │
│  Worker              │      │  (Chaos Discovery)   │
│  - Fetch Binance 5m  │      │  - Random trades     │
│  - Store in KV       │      │  - Real data replay  │
│  - Random segments   │      │  - Pattern discovery │
└──────────────────────┘      └──────────────────────┘
         │                             │
         │                             │
         ▼                             ▼
┌──────────────────────────────────────────────────┐
│         KV Namespace: HISTORICAL_PRICES           │
│  - 5-minute candle data from Binance             │
│  - BTC, SOL, ETH × USDT, USDC, BUSD             │
│  - Random time segments (30+ days)               │
└──────────────────────────────────────────────────┘
         │
         │
         ▼
┌──────────────────────────────────────────────────┐
│         D1 Database: CHAOS_TRADES                 │
│  - Random trade outcomes                         │
│  - Entry/exit prices (REAL historical data)      │
│  - Market state at entry/exit                    │
│  - Profit/loss, win rate, patterns              │
└──────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────┐
│         AI Pattern Analysis                       │
│  - Find patterns in SUCCESSFUL trades            │
│  - Not patterns in price data                    │
│  - Discover novel strategies                     │
└──────────────────────────────────────────────────┘
```

## Workers Overview

### 1. Historical Data Worker
**File:** `historical-data-worker.ts`
**Config:** `wrangler-historical.toml`
**Purpose:** Fetch and store real historical price data from Binance

**Endpoints:**
- `POST /fetch` - Fetch historical data for single pair
- `POST /fetch-all` - Fetch data for all configured pairs
- `GET /data/{pair}/{interval}/{start}/{end}` - Get cached data
- `GET /random` - Get random time segment for testing
- `GET /pairs` - List available pairs

**Features:**
- Real data from Binance API (not mock)
- 5-minute candles (maximum granularity)
- Multi-pair support (BTC, SOL, ETH × stablecoins)
- Automatic batching (handles >1000 candles)
- Random segment selection
- 30-day KV storage

### 2. Evolution Agent (Durable Object)
**File:** `evolution-agent-simple.ts`
**Config:** `wrangler.toml`
**Purpose:** Chaos discovery and pattern evolution

**Endpoints:**
- `GET /status` - System status
- `GET /debug` - Debug information
- `GET /logs` - Recent logs
- `POST /trigger` - Run evolution cycle
- `GET /bulk-import?count=N` - Generate N chaos trades

**Features:**
- **Chaos trading** on REAL historical data
- Random pair, time, entry, hold duration selection
- Real market indicators calculated from historical candles
- Pattern discovery from trade OUTCOMES (not price patterns)
- Agent competition and evolution
- Academic papers testing
- Technical patterns testing
- Multi-layer evolutionary system

## Deployment Steps

### 1. Create KV Namespaces

```bash
# Create HISTORICAL_PRICES namespace
wrangler kv:namespace create HISTORICAL_PRICES

# Create TRADING_KV namespace
wrangler kv:namespace create TRADING_KV
```

Copy the namespace IDs and update them in the wrangler config files.

### 2. Update Wrangler Configs

**wrangler-historical.toml:**
```toml
[[kv_namespaces]]
binding = "HISTORICAL_PRICES"
id = "your_actual_namespace_id_here"  # Replace with ID from step 1
```

**wrangler.toml (Evolution Agent):**
```toml
[[d1_databases]]
binding = "DB"
database_id = "your_d1_database_id"  # Replace with your D1 database ID

[[kv_namespaces]]
binding = "HISTORICAL_PRICES"
id = "your_historical_prices_id_here"  # Same as historical worker
```

### 3. Deploy Workers

```bash
# Deploy historical data worker
wrangler deploy --config wrangler-historical.toml

# Deploy evolution agent
wrangler deploy --config wrangler.toml
```

### 4. Update URLs

After deployment, Cloudflare will give you URLs like:
- `https://coinswarm-historical-data.your-subdomain.workers.dev`
- `https://coinswarm-trading-agent.your-subdomain.workers.dev`
- `https://coinswarm-backtest.your-subdomain.workers.dev`

Update the `HISTORICAL_DATA_URL` in `wrangler-backtest.toml` with the actual historical data worker URL.

## Usage Examples

### Fetch Historical Data

```bash
# Fetch 30 days of 5-minute data for all pairs
curl -X POST https://coinswarm-historical-data.your-subdomain.workers.dev/fetch-all \
  -H "Content-Type: application/json" \
  -d '{
    "interval": "5m",
    "durationDays": 30
  }'
```

### Run Backtest

```bash
# Run backtest on random 30-day segment
curl -X POST https://coinswarm-backtest.your-subdomain.workers.dev/backtest \
  -H "Content-Type: application/json" \
  -d '{
    "pairs": ["BTC-USDT", "BTC-USDC", "BTC-BUSD", "SOL-USDT", "SOL-USDC"],
    "interval": "5m",
    "minDays": 30,
    "initialCapital": 100000,
    "maxPositions": 10,
    "maxPerPairPct": 0.30,
    "minProfitThreshold": 0.001
  }'
```

### Run Multi-Segment Backtest (5 Random Segments)

```bash
# Test across 5 different random time segments
curl -X POST https://coinswarm-backtest.your-subdomain.workers.dev/backtest-multi \
  -H "Content-Type: application/json" \
  -d '{
    "pairs": ["BTC-USDT", "BTC-USDC", "SOL-USDT", "ETH-USDT"],
    "interval": "5m",
    "minDays": 30,
    "randomSegments": 5,
    "initialCapital": 100000
  }'
```

### Scan for Live Opportunities

```bash
# Get current trading opportunities
curl https://coinswarm-trading-agent.your-subdomain.workers.dev/scan
```

### Execute Trade

```bash
# Execute a trade
curl -X POST https://coinswarm-trading-agent.your-subdomain.workers.dev/trade \
  -H "Content-Type: application/json" \
  -d '{
    "action": "BUY",
    "pair": "BTC-USDT",
    "size": 0.01
  }'
```

## Testing Environment Features ✅

**User Requirements Met:**

✅ **Real historical data** (not mock)
   - Fetches from Binance API
   - Stores in KV for replay

✅ **Most granular data** (5-minute candles)
   - Default: 5m interval
   - 288 candles per day vs 24 with 1h

✅ **Random time segment selection**
   - `/random` endpoint selects random segments
   - Prevents overfitting to specific dates

✅ **Significant time lengths** (30+ days minimum)
   - Default: 30 days
   - Configurable via `minDays` parameter

✅ **Multi-pair environment** (not single-pair isolation)
   - Tests across BTC, SOL, ETH simultaneously
   - Shares capital pool across pairs

✅ **BTC-USD with multiple stablecoins**
   - BTC-USDT, BTC-USDC, BTC-BUSD

✅ **SOL-USD with multiple stablecoins**
   - SOL-USDT, SOL-USDC, SOL-BUSD

✅ **BTC-SOL pairings**
   - Direct BTC-SOL pair when available

✅ **Cross-pair pattern detection**
   - Correlation across BTC/SOL/ETH
   - Triangular arbitrage detection

✅ **Arbitrage opportunities across pairs**
   - Stablecoin arbitrage (BTC-USDT vs BTC-USDC)
   - Triangular arbitrage (BTC→SOL→USD)
   - Spread trading (mean reversion)

## Performance Metrics

The backtest worker calculates:

- **Win Rate:** Percentage of profitable trades
- **Total P&L:** Absolute profit/loss
- **P&L %:** Return on initial capital
- **Sharpe Ratio:** Risk-adjusted return
- **Max Drawdown:** Largest equity decline
- **Average Trade Return:** Mean profit per trade

## Pattern Detection Stats

- Total arbitrage opportunities detected
- Total spread opportunities detected
- Best arbitrage profit percentage
- Highest Z-score (spread deviation)

## Data Storage

### KV Structure

**HISTORICAL_PRICES:**
```
historical:BTC-USDT:5m:1698765432000:1701357432000 → {dataset}
index:BTC-USDT:5m → [{startTime, endTime, candleCount}, ...]
index:pairs → ["BTC-USDT", "BTC-USDC", ...]
```

**TRADING_KV:**
```
portfolio_state → {cash, positions, totalEquity, ...}
backtest:{id} → {config, results, trades, equityCurve, ...}
```

## Monitoring

Check worker logs:
```bash
wrangler tail --config wrangler-historical.toml
wrangler tail --config wrangler-trading.toml
wrangler tail --config wrangler-backtest.toml
```

## Rate Limits

**Binance API:**
- Public endpoints: 1200 requests/minute
- Historical data worker batches requests with 200ms delays

**Cloudflare Workers:**
- Free tier: 100,000 requests/day
- Paid tier: Unlimited requests

## Cost Estimate

**Free Tier (sufficient for testing):**
- Workers: 100,000 requests/day (FREE)
- KV: 1 GB storage (FREE)
- KV reads: 100,000/day (FREE)
- KV writes: 1,000/day (FREE)

**For production, upgrade to Paid ($5/month):**
- Workers: Unlimited requests
- KV: $0.50/GB + $0.50/million reads

## Next Steps

1. Deploy all three workers
2. Fetch 30-90 days of historical data for all pairs
3. Run multi-segment backtests (5-10 random segments)
4. Analyze pattern detection statistics
5. Optimize parameters based on backtest results
6. Enable live trading on trading worker

## Architecture Benefits

**Why Cloudflare Workers?**
- ✅ Runs 24/7 in the cloud (no local infrastructure)
- ✅ Global edge network (sub-100ms latency)
- ✅ Serverless (scales automatically)
- ✅ KV storage (fast, distributed)
- ✅ Cost-effective ($5/month for unlimited)

**Why Multiple Workers?**
- Separation of concerns (data ingestion vs trading vs testing)
- Independent scaling
- Easy to test in isolation
- Deploy updates without affecting other components

## Troubleshooting

**Problem:** Binance API returns 429 (rate limit)
**Solution:** Historical data worker already implements 200ms delays. If still rate limited, increase delay in code.

**Problem:** KV namespace not found
**Solution:** Verify namespace IDs in wrangler config match actual created namespaces.

**Problem:** Worker timeout
**Solution:** For large backtests (>60 seconds), consider splitting into smaller segments or using Durable Objects.

**Problem:** No historical data available
**Solution:** Run `/fetch-all` endpoint first to populate KV storage.

## Support

For issues or questions:
- Check worker logs: `wrangler tail`
- Review Cloudflare dashboard analytics
- Verify KV namespace data: `wrangler kv:key list --namespace-id=xxx`
