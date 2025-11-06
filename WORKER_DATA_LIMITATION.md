# Worker Data Limitation - Only ~30 Days Available

## Current Status

✅ **What Works:**
- Worker is deployed and functional
- Fetches data from Kraken + Coinbase
- Exponential backoff retry logic working
- SSL cert handling for proxy working

❌ **Limitation:**
- **Worker only returns ~30 days** of data even when requesting 365 days
- Each request returns ~721 candles (30 days × 24 hours)
- Need 2+ years (17,520 candles) for robust validation

## Root Cause

The Worker uses Binance's `/api/v3/klines` endpoint which has:
- **Limit: 1000 candles per request**
- For 1-hour candles: 1000 hours = ~42 days max

Current Worker code (cloudflare-workers/data-fetcher.js:71):
```javascript
const binanceUrl = `https://api.binance.com/api/v3/klines?` +
  `symbol=${symbol}&interval=${timeframe}&startTime=${startTime}&endTime=${now}&limit=1000`;
```

**Problem:** Single request, single 1000-candle limit.

## Solution: Paginated Fetching

The Worker needs to be enhanced to fetch multiple pages:

### Option 1: Worker-Side Pagination (Recommended)

Update `data-fetcher.js` to loop and fetch multiple 1000-candle chunks:

```javascript
async function fetchAllCandles(symbol, timeframe, startTime, endTime) {
    const allCandles = [];
    let currentStart = startTime;
    const oneDayMs = 24 * 60 * 60 * 1000;
    const chunkSize = 1000; // Binance limit

    while (currentStart < endTime && allCandles.length < 25000) { // Max 25K candles (~2.8 years)
        const url = `https://api.binance.com/api/v3/klines?` +
            `symbol=${symbol}&interval=${timeframe}&startTime=${currentStart}&limit=${chunkSize}`;

        const response = await fetch(url);
        const candles = await response.json();

        if (candles.length === 0) break;

        allCandles.push(...candles);

        // Move start time to after last candle
        const lastCandleTime = candles[candles.length - 1][0];
        currentStart = lastCandleTime + 1;

        // Rate limit (Binance allows 1200 req/min = 20/sec)
        await new Promise(resolve => setTimeout(resolve, 100)); // 10 req/sec
    }

    return allCandles;
}
```

### Option 2: Client-Side Pagination

Keep Worker as-is, but have the Python client fetch multiple chunks:
- Request days=30 repeatedly with different start times
- Stitch together client-side

**Downside:** More Worker requests, slower, uses more quota.

### Option 3: Pre-populate D1 Database

Run a one-time script to:
1. Fetch 2+ years from Binance directly
2. Store in Cloudflare D1
3. Worker serves from D1 instead of live Binance queries

**Advantages:**
- Fast queries (<10ms from D1)
- No Binance rate limits
- Can store 3+ years easily (5GB free tier)

## Immediate Workaround

For now, we have ~30 days of data for BTC, SOL, ETH. This is:
- ✅ Enough to test memory system functionality
- ✅ Enough to test random window validation (with 3-7 day windows)
- ❌ NOT enough for robust 2+ year validation
- ❌ NOT enough to test regime changes (bull/bear/ranging)

## Action Items

1. **Short-term:** Test memory with 30-day data (sufficient for unit tests)
2. **Medium-term:** Enhance Worker with pagination (get 2+ years)
3. **Long-term:** Migrate to D1 pre-populated database (best performance)

## Data Fetched So Far

```
BTC-USD: 1,442 candles (30 days, Oct 7 - Nov 6, 2025)
SOL-USD: 1,442 candles (30 days)
ETH-USD: 1,442 candles (30 days)
```

All saved to: `/home/user/Coinswarm/data/historical/`

## Testing Strategy

Given 30-day limitation:
1. Use 3-7 day random windows (sufficient samples)
2. Focus on short-term strategy validation
3. Demonstrate memory learning over 30-day period
4. Document need for longer data before production

---

**Status:** ⚠️ Data fetch working but limited to 30 days
**Next Step:** Enhance Worker pagination OR pre-populate D1
