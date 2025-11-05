# Instructions for Other Claude

Hi! Please help deploy a Cloudflare Worker for me.

## What I Need

Deploy the code in `DEPLOY_TO_CLOUDFLARE.js` as a Cloudflare Worker.

## Requirements

- Worker name: `coinswarm-data-fetcher`
- The code is in: `DEPLOY_TO_CLOUDFLARE.js`
- No KV namespace needed (removed for simplicity)
- No environment variables needed
- Just deploy as-is

## Steps

1. Read the file `DEPLOY_TO_CLOUDFLARE.js`
2. Create a new Cloudflare Worker named `coinswarm-data-fetcher`
3. Use that code as the Worker script
4. Deploy it
5. Give me the deployed Worker URL

## Expected URL Format

The URL should look like:
```
https://coinswarm-data-fetcher.[something].workers.dev
```

## Test After Deployment

Please test it by fetching:
```
GET https://[your-worker-url]/fetch?symbol=BTCUSDT&timeframe=1h&days=7
```

You should get JSON with ~168 candles of BTC price data.

## What This Worker Does

- Fetches historical crypto prices from Binance (public API)
- Supports any symbol: BTCUSDT, ETHUSDT, SOLUSDT, etc.
- Timeframes: 1m, 5m, 15m, 1h, 4h, 1d
- Returns clean JSON format for my backtesting system

## Why I Need This

I'm building a crypto trading bot and need historical data for backtesting. This Worker fetches data from Binance and makes it available via a simple API.

## Return to Me

Just give me:
1. ✅ The Worker URL
2. ✅ Confirmation it's working (test result)

That's it! Thanks! 🚀
