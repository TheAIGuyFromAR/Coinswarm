# API Rate Limits Documentation

This document outlines the rate limits for all data sources used in the Coinswarm historical data collection system.

## Summary Table

| API Source | Free Tier Rate Limit | Monthly Cap | Paid Plans | Notes |
|-----------|---------------------|-------------|-----------|-------|
| **CoinGecko** | 30 calls/min | 10,000/month | 500-1000 calls/min | Best for daily OHLC data |
| **GeckoTerminal** | 30 calls/min | Unlimited | 500 calls/min | DEX aggregator, 100+ networks |
| **CryptoCompare** | 30 calls/min | ~few thousand/day | 100k-300k calls/month | Requires API key for stable limits |
| **DexScreener** | 300 calls/min | Unlimited | Higher limits available | Best for DEX pairs |
| **Binance.US** | 1200 weight/min (IP) | Unlimited | 6000 weight/min (API key) | 1 weight per klines request |

---

## Detailed Rate Limits

### 1. CoinGecko API

**Free Tier (Demo Plan)**:
- **Rate Limit**: 30 calls per minute
- **Monthly Cap**: 10,000 calls per month
- **Registration**: Free Demo account (recommended for stable limits)
- **Public API**: 5-15 calls per minute (no registration)

**Paid Plans**:
- **Analyst Plan**: 500 calls/min
- **Pro Plan**: 1000 calls/min
- **Enterprise**: Custom limits

**Best Use Case**: Daily OHLC data for major cryptocurrencies (BTC, ETH, SOL, etc.)

**Documentation**: https://www.coingecko.com/en/api/pricing

**Priority**: ⭐⭐⭐⭐⭐ (Primary source - working reliably)

---

### 2. GeckoTerminal API

**Free Tier**:
- **Rate Limit**: 30 calls per minute
- **Monthly Cap**: None
- **Registration**: Not required
- **Recent Update**: Increased from 10 calls/min to 30 calls/min in 2024

**Paid Plans**:
- **Pro Plan**: 500 calls/min (16x increase)
- Available through CoinGecko Pro API subscription

**Best Use Case**: DEX OHLCV data across 100+ networks (Ethereum, BSC, Solana, Arbitrum, Optimism, etc.)

**Documentation**: https://apiguide.geckoterminal.com/

**Priority**: ⭐⭐⭐⭐ (Excellent for multi-chain DEX data)

---

### 3. CryptoCompare API

**Free Tier**:
- **Rate Limit**: ~30 calls per minute (with free API key)
- **Daily Cap**: Few thousand calls per day
- **Registration**: Required for stable limits
- **API Key**: Free tier available

**Paid Plans**:
- **Basic**: $80/month (~100k calls/month)
- **Advanced**: $200/month (~300k calls/month)
- **Enterprise**: Custom pricing

**Best Use Case**: Minute-level historical data with volume for CEX pairs

**Documentation**: https://min-api.cryptocompare.com/pricing

**Priority**: ⭐⭐⭐ (Good for minute-level granularity)

**Note**: Currently hitting rate limits, may need API key registration or switch to other sources.

---

### 4. DexScreener API

**Free Tier**:
- **DEX/Pairs Endpoints**: 300 requests per minute
- **Token Profile/Boost Endpoints**: 60 requests per minute
- **Registration**: Not required
- **Error Response**: Returns 429 "Too Many Requests" when limit exceeded

**Paid Plans**:
- Available for higher rate limits
- Pricing determined during API Services checkout

**Best Use Case**: Real-time DEX pair data across 50+ chains

**Documentation**: https://docs.dexscreener.com/api/reference

**Priority**: ⭐⭐⭐⭐ (Highest rate limit for free tier, covers all chains)

**Endpoints Used**:
- `/search?q={symbol}` - Search tokens (300 req/min)
- `/tokens/{chainId}/{address}` - Get token pairs (300 req/min)

---

### 5. Binance.US API

**IP-based Limits (No API Key)**:
- **Weight Limit**: 1200 weight per minute
- **Klines Endpoint**: 1 weight per request
- **Max Candles**: 1000 candles per request
- **Effective Rate**: ~1200 requests per minute for klines

**API Key Limits**:
- **Weight Limit**: 6000 weight per minute
- **Order Rate**: 20 orders per second, 160,000 orders per day

**Best Use Case**: Historical klines/candlestick data for major crypto pairs (BTC, ETH, SOL, etc.)

**Documentation**: https://docs.binance.us/

**Priority**: ⭐⭐⭐ (Good fallback, but previously had 403 errors from Cloudflare Workers)

**Important Notes**:
- Each klines request has weight of 1
- Can fetch up to 1000 candles per request
- Batching required for historical datasets > 1000 candles
- Previously used `data.binance.com`, now using `api.binance.us`

---

## Multi-Source Fallback Strategy

The historical data worker implements a 5-tier fallback system:

1. **CryptoCompare** (Primary)
   - Minute-level data with volume
   - 30 calls/min free tier
   - May hit rate limit quickly

2. **CoinGecko** (Secondary)
   - Daily OHLC data
   - 30 calls/min, 10k/month
   - **Currently working reliably** ✅

3. **GeckoTerminal** (Tertiary)
   - DEX OHLCV for 100+ networks
   - 30 calls/min free tier
   - Supports 5m, 15m, 1h, 4h, 12h, 1d timeframes

4. **Binance.US** (Quaternary)
   - 1200 weight/min (IP-based)
   - 1 weight per klines request
   - Previously had 403 errors, now using api.binance.us

5. **DexScreener** (Final Fallback)
   - 300 calls/min free tier (highest)
   - Current price only (not historical candles)
   - Covers 50+ chains

---

## Rate Limiting Best Practices

### 1. Implement Request Delays
```typescript
// Wait 200ms between batched requests to Binance
await this.sleep(200);
```

### 2. Track Usage Per Minute
```typescript
// Ensure we stay under 30 calls/min for CoinGecko/GeckoTerminal
const requestsThisMinute = trackRequests();
if (requestsThisMinute >= 28) {
  await waitUntilNextMinute();
}
```

### 3. Use DexScreener for High-Volume Queries
- DexScreener has the highest free tier limit (300 req/min)
- Best for batch operations or large-scale data collection

### 4. Cache Aggressively
- Store fetched data in D1 database
- Use KV namespace for frequently accessed datasets
- Avoid redundant API calls for same timeframes

### 5. Distribute Load
- Use different sources for different tokens
- CoinGecko for BTC/ETH/SOL (major coins)
- GeckoTerminal for DEX tokens (RAY, ORCA, CAKE, etc.)
- DexScreener for real-time price validation

---

## Recommendations

### For 5 Years of Historical Data Collection

**Target**: 15 tokens × 525,600 candles (5 years × 5-min intervals) = 7.8M candles

**Strategy**:
1. **Primary Collection (CoinGecko)**:
   - Use for BTC, ETH, SOL (major coins)
   - Daily OHLC available for 5+ years
   - 30 calls/min = 1800 calls/hour = 43,200 calls/day
   - With 10k/month cap: ~333 calls/day to stay within limits
   - **Estimate**: 3-5 days per token for 5 years of data

2. **DEX Tokens (GeckoTerminal)**:
   - Use for DeFi tokens (RAY, ORCA, CAKE, JUP, etc.)
   - 30 calls/min = 1800 calls/hour
   - No monthly cap (!)
   - **Estimate**: 1-2 days per token

3. **Validation (DexScreener)**:
   - Use 300 calls/min to validate prices
   - Cross-check against CoinGecko/GeckoTerminal
   - Detect anomalies and fill gaps

4. **Fallback (Binance.US)**:
   - Use if CoinGecko/GeckoTerminal fail
   - 1200 weight/min = very fast collection
   - **Estimate**: Few hours per token if needed

### Estimated Total Collection Time

With careful rate limiting:
- **Sequential**: 15 tokens × 3 days = 45 days
- **Parallel** (3 workers): 15 days
- **With caching**: 10-15 days for initial collection

---

## Error Handling

### 429 Too Many Requests
```typescript
if (response.status === 429) {
  // Wait 60 seconds and retry
  await sleep(60000);
  return await retry(request);
}
```

### 403 Forbidden (Binance)
```typescript
// Switch to alternative source immediately
try {
  await binanceClient.fetch();
} catch (e) {
  if (e.status === 403) {
    return await coinGeckoClient.fetch(); // Fallback
  }
}
```

### Rate Limit Headers
Some APIs return rate limit headers:
- `X-RateLimit-Limit`: Max requests per window
- `X-RateLimit-Remaining`: Requests left in window
- `X-RateLimit-Reset`: When the window resets

Monitor these to avoid hitting limits.

---

## Next Steps

1. ✅ **Document all rate limits** (this document)
2. ✅ **Update code with Binance.US endpoint**
3. ⏳ **Test all 5 data sources from Cloudflare Workers**
4. ⏳ **Implement rate limiting logic** (request tracking, delays)
5. ⏳ **Start collecting 5 years of data** for BTC, SOL
6. ⏳ **Expand to all 15 target tokens**

---

## References

- CoinGecko API Pricing: https://www.coingecko.com/en/api/pricing
- GeckoTerminal API Docs: https://apiguide.geckoterminal.com/
- CryptoCompare Pricing: https://min-api.cryptocompare.com/pricing
- DexScreener API Reference: https://docs.dexscreener.com/api/reference
- Binance.US API Docs: https://docs.binance.us/

---

**Last Updated**: November 9, 2025
