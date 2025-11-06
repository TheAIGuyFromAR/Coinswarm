# Network-Enabled Claude Code Environment Setup

## STEP 1: Enable Network Access

Add this to your Claude Code workspace settings or `.claude/config.json`:

```json
{
  "network": {
    "allowedDomains": [
      "api.binance.com",
      "data.binance.vision",
      "api.alternative.me",
      "news.google.com",
      "min-api.cryptocompare.com",
      "newsapi.org",
      "api.stlouisfed.org",
      "trends.google.com"
    ],
    "allowExternalRequests": true
  }
}
```

## STEP 2: Set Environment Variables

```bash
# Required
export PYTHONPATH=/home/user/Coinswarm/src

# Optional but recommended (all free):
export FRED_API_KEY=your_key_here
export CRYPTOCOMPARE_API_KEY=your_key_here
```

## STEP 3: Run Real Backtest

```bash
cd /home/user/Coinswarm
python demo_real_data.py
```

## That's It!

With network access enabled, Claude will:
- ✅ Fetch real Binance price data (BTC, ETH, SOL)
- ✅ Fetch Fear & Greed Index (market sentiment)
- ✅ Fetch Google News sentiment (if available)
- ✅ Run backtests with actual historical data
- ✅ Start continuous learning

## If You Want Even Better Data (Optional)

Get these FREE API keys in 2 minutes each:

**FRED API (Macro Data):**
1. Go to https://fred.stlouisfed.org/
2. Sign up
3. Get API key: https://fred.stlouisfed.org/docs/api/api_key.html
4. Set: `export FRED_API_KEY=your_key`

**CryptoCompare (Crypto News):**
1. Go to https://www.cryptocompare.com/cryptopian/api-keys
2. Sign up
3. Get API key
4. Set: `export CRYPTOCOMPARE_API_KEY=your_key`

## You Don't Need Cloudflare Worker

With network access enabled, Claude can call Binance API directly.
The Worker is only needed for restricted environments.

## Commands to Run

```bash
# First real backtest (30 days)
python demo_real_data.py

# Validate strategy (10 random windows)
python validate_strategy.py --windows 10

# Start continuous learning
python -m coinswarm.backtesting.continuous_backtester
```

That's literally all you need!
