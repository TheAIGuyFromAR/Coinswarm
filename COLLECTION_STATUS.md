# Data Collection Status

## Setup Complete ✅

All workers deployed and configured to collect historical cryptocurrency price data.

### Active Workers

1. **coinswarm-historical-collection-cron** (Runs hourly)
   - Collects minute-level data from CryptoCompare
   - Collects daily data from CoinGecko  
   - Collects hourly data from Binance.US
   - Target: 5 years of data for 15 tokens
   - Rate limited to 56.25% of API max (safe operation)

2. **coinswarm-realtime-price-cron** (Runs every minute)
   - Real-time price collection using leaky bucket algorithm
   - Round-robin between CoinGecko, CryptoCompare, Binance.US, DexScreener
   - 15 tokens tracked

3. **coinswarm-technical-indicators** (HTTP-triggered after historical collection)
   - Calculates SMA (20, 50, 200)
   - Calculates EMA (12, 26, 50)
   - Bollinger Bands (20-period, 2 std dev)
   - MACD (12, 26, 9)
   - RSI (14-period)
   - Custom Fear/Greed Index
   - Volume indicators

4. **coinswarm-collection-alerts** (Runs every 15 minutes)
   - Monitors collection progress
   - Alerts on milestones (25%, 50%, 75%, 100%)
   - Tracks paused/errored tokens

5. **coinswarm-data-monitor** (Web dashboard)
   - View at: https://coinswarm-data-monitor.bamn86.workers.dev/
   - Live progress tracking
   - Auto-refresh every 30 seconds

### Tokens Being Collected

1. BTCUSDT (Bitcoin)
2. ETHUSDT (Ethereum)
3. SOLUSDT (Solana)
4. BNBUSDT (Binance Coin)
5. CAKEUSDT (PancakeSwap)
6. RAYUSDT (Raydium)
7. ORCAUSDT (Orca)
8. JUPUSDT (Jupiter)
9. ARBUSDT (Arbitrum)
10. GMXUSDT (GMX)
11. OPUSDT (Optimism)
12. VELOUSDT (Velodrome)
13. MATICUSDT (Polygon)
14. QUICKUSDT (QuickSwap)
15. AEROUSDT (Aerodrome)

### Collection Target

- **Minute data**: 5 years = 2,628,000 minutes per token = 39,420,000 total
- **Hourly data**: 5 years = 43,800 hours per token = 657,000 total
- **Daily data**: 5 years = 1,825 days per token = 27,375 total

### Timeline Estimate

At 56.25% rate limiting:
- **CryptoCompare** (minute): 16.875 calls/min = ~97 days for all tokens
- **CoinGecko** (daily): 16.875 calls/min = ~27 hours for all tokens  
- **Binance.US** (hourly): 675 calls/min = ~16 hours for all tokens

**Total collection time**: ~97 days for complete historical dataset

### Next Steps

The workers will now run automatically on their schedules:
- Historical collection runs every hour
- Real-time collection runs every minute
- Technical indicators calculate after each historical run
- Alerts check progress every 15 minutes

Monitor progress at: https://coinswarm-data-monitor.bamn86.workers.dev/

All data is being stored in the `coinswarm-evolution` D1 database with enriched technical indicators.
