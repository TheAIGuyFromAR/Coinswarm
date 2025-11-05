# API Keys & Integration Readiness Guide

**Status**: 🟢 Code Ready | 🟡 Keys Needed
**Last Updated**: 2025-11-05

## TL;DR - What You Need

**Critical for Phase 2-3** (Weeks 5-8):
- ✅ **Coinbase** - Code ready, keys needed
- ✅ **Binance** - Code ready, no keys needed (public data)

**Important for Phase 3** (Weeks 7-8):
- 🟡 **NewsAPI** - Code pending, free tier available
- 🟡 **Twitter/X** - Code pending, requires paid API ($100/month)
- 🟡 **Reddit** - Code pending, free API available
- 🟡 **FRED** - Code pending, free API available

**Optional for Phase 3+**:
- 🔵 **Etherscan** - Code pending, free tier available

---

## Implementation Status

### ✅ READY TO USE (Code Implemented)

#### 1. Coinbase Advanced Trade API
**Status**: ✅ Fully implemented
**File**: `src/coinswarm/api/coinbase_client.py` (459 lines)
**Authentication**: HMAC-SHA256 (implemented)
**Capabilities**:
- ✅ Account management (balances, portfolios)
- ✅ Market data (products, tickers, candles)
- ✅ Order management (market, limit, cancel)
- ✅ Fills/executions tracking
- ✅ Rate limiting with retry logic
- ✅ Async/await support

**Environment Variables Needed**:
```bash
COINBASE_API_KEY=your_api_key_here
COINBASE_API_SECRET=your_api_secret_here
COINBASE_ENVIRONMENT=sandbox  # or production
```

**How to Get Keys**:
1. Go to https://www.coinbase.com/settings/api
2. Click "New API Key"
3. Select permissions:
   - ✅ View (account balances, orders)
   - ✅ Trade (create/cancel orders)
   - ⚠️ DO NOT enable Transfer (no withdrawals)
4. Save API Key and API Secret (base64 encoded)
5. **Start with SANDBOX environment for testing**

**Cost**: Free for sandbox, standard trading fees for production
**Rate Limits**: Built into client (auto-retry)

---

#### 2. Binance Exchange API
**Status**: ✅ Fully implemented
**File**: `src/coinswarm/data_ingest/exchanges/binance.py` (439 lines)
**Authentication**: Optional (public data works without keys)
**Capabilities**:
- ✅ Historical OHLCV data
- ✅ Real-time WebSocket (trades, orderbook, klines)
- ✅ Funding rates (for perpetual futures)
- ✅ Order book snapshots
- ✅ Product/market listings

**Environment Variables** (Optional for public data):
```bash
# Leave empty for public data access
BINANCE_API_KEY=
BINANCE_API_SECRET=
```

**How to Get Keys** (if needed for private trading):
1. Go to https://www.binance.com/en/my/settings/api-management
2. Create new API key
3. Enable only "Enable Reading" (for now)
4. Save key and secret

**Cost**: Free for market data
**Rate Limits**: 2400 requests/minute (built-in handling)

---

### 🟡 PENDING IMPLEMENTATION (Phase 3)

#### 3. NewsAPI (News Sentiment)
**Status**: 🟡 Not implemented yet (Week 7-8)
**Will Implement**: `src/coinswarm/data_ingest/news/newsapi.py`
**Authentication**: API key in header

**Environment Variables Needed**:
```bash
NEWSAPI_KEY=your_newsapi_key_here
```

**How to Get Key**:
1. Go to https://newsapi.org/register
2. Sign up for Developer account (FREE)
3. Get API key immediately
4. Free tier: 100 requests/day, 1000/month

**Cost**:
- Free: $0 (100 req/day)
- Business: $449/month (250k req/month)

**Recommendation**: Start with free tier, upgrade if needed

---

#### 4. Twitter/X API (Social Sentiment)
**Status**: 🟡 Not implemented yet (Week 7-8)
**Will Implement**: `src/coinswarm/data_ingest/social/twitter.py`
**Authentication**: OAuth 2.0 Bearer Token

**Environment Variables Needed**:
```bash
TWITTER_API_KEY=your_api_key_here
TWITTER_API_SECRET=your_api_secret_here
TWITTER_BEARER_TOKEN=your_bearer_token_here
```

**How to Get Keys**:
1. Go to https://developer.twitter.com/en/portal/dashboard
2. Apply for Developer Account (requires approval)
3. Create a new Project + App
4. Generate API Key, Secret, and Bearer Token

**Cost**:
- Free Tier: DISCONTINUED (no longer available)
- Basic: $100/month (10k tweets/month)
- Pro: $5,000/month (1M tweets/month)

**⚠️ BLOCKER**: Twitter now requires paid API access ($100/month minimum)

**Alternatives**:
- Scrape Twitter via unofficial libraries (against TOS, risky)
- Use Reddit only (free alternative)
- Use sentiment from NewsAPI (limited social coverage)
- Wait for competitor APIs (Bluesky, Mastodon)

**Recommendation**: **Skip Twitter for Phase 3**, use Reddit + NewsAPI instead

---

#### 5. Reddit API (Community Sentiment)
**Status**: 🟡 Not implemented yet (Week 7-8)
**Will Implement**: `src/coinswarm/data_ingest/social/reddit.py`
**Authentication**: OAuth 2.0 Client Credentials

**Environment Variables Needed**:
```bash
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USER_AGENT=Coinswarm/0.1.0
```

**How to Get Keys**:
1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App" or "Create Another App"
3. Select "script" type
4. Fill in details:
   - Name: Coinswarm
   - Description: Crypto trading sentiment analysis
   - About URL: (your repo or website)
   - Redirect URI: http://localhost:8080 (for script apps)
5. Get Client ID (under app name) and Client Secret

**Cost**: FREE (generous rate limits)
**Rate Limits**: 60 requests/minute

**Recommendation**: ✅ Use this as primary social sentiment source

---

#### 6. FRED API (Macro Economic Data)
**Status**: 🟡 Not implemented yet (Week 7-8)
**Will Implement**: `src/coinswarm/data_ingest/macro/fred.py`
**Authentication**: API key in URL parameter

**Environment Variables Needed**:
```bash
FRED_API_KEY=your_fred_api_key_here
```

**How to Get Key**:
1. Go to https://fredaccount.stlouisfed.org/apikeys
2. Sign up for FRED account (FREE)
3. Request API key
4. Get key immediately

**Cost**: FREE
**Rate Limits**: Generous (no strict limits documented)

**Data Available**:
- DXY (US Dollar Index)
- Treasury yields (10Y, 2Y)
- Fed funds rate
- Inflation metrics (CPI, PCE)

**Recommendation**: ✅ Easy win, implement in Phase 3

---

#### 7. Etherscan API (On-Chain Data)
**Status**: 🔵 Optional (Phase 4+)
**Will Implement**: `src/coinswarm/data_ingest/onchain/etherscan.py`
**Authentication**: API key in URL parameter

**Environment Variables Needed**:
```bash
ETHERSCAN_API_KEY=your_etherscan_key_here
```

**How to Get Key**:
1. Go to https://etherscan.io/myapikey
2. Sign up and verify email
3. Create API key
4. Free tier: 5 calls/second

**Cost**: FREE
**Rate Limits**: 5 calls/sec (free), 15 calls/sec (paid $199/month)

**Recommendation**: 🔵 Nice to have, not critical for Phase 0-4

---

## Immediate Action Items

### Before Week 5 (Phase 2 starts):

1. **Create Coinbase Sandbox Account** 🔴 CRITICAL
   ```bash
   # Get API keys from Coinbase
   # Add to .env file
   cp .env.example .env
   # Edit .env and add COINBASE_API_KEY and COINBASE_API_SECRET
   ```

2. **Test Coinbase Client** 🔴 CRITICAL
   ```bash
   # Run existing tests
   pytest tests/unit/test_coinbase_client.py -v

   # Or create a quick integration test
   python -c "
   import asyncio
   from coinswarm.api.coinbase_client import CoinbaseAPIClient

   async def test():
       async with CoinbaseAPIClient() as client:
           accounts = await client.list_accounts()
           print(f'Found {len(accounts)} accounts')

   asyncio.run(test())
   "
   ```

### Before Week 7 (Phase 3 starts):

3. **Get Free API Keys** 🟡 IMPORTANT
   - [ ] Reddit API (15 min, free)
   - [ ] FRED API (10 min, free)
   - [ ] NewsAPI (5 min, free tier)

4. **Decision on Twitter** 🟡 DECISION NEEDED
   - Option A: Pay $100/month for Twitter Basic API
   - Option B: Skip Twitter, use Reddit + NewsAPI for sentiment
   - **My Recommendation**: Option B (save $100/month, Reddit is better for crypto anyway)

### Optional (Phase 4+):

5. **Etherscan API** 🔵 OPTIONAL
   - Get free API key if you want on-chain data
   - Not critical for initial phases

---

## Cost Summary

### Minimum Viable (MVP):
```
Coinbase Sandbox:           FREE
Binance Market Data:        FREE
Reddit API:                 FREE
FRED API:                   FREE
NewsAPI (free tier):        FREE
─────────────────────────────────
TOTAL (MVP):                $0/month
```

### Recommended (Skip Twitter):
```
Coinbase Sandbox:           FREE
Binance Market Data:        FREE
Reddit API:                 FREE
FRED API:                   FREE
NewsAPI (business):         $449/month (only if >100 req/day)
─────────────────────────────────
TOTAL (Recommended):        $0-449/month
```

### Full Stack (With Twitter):
```
Coinbase Sandbox:           FREE
Binance Market Data:        FREE
Reddit API:                 FREE
FRED API:                   FREE
NewsAPI (business):         $449/month
Twitter Basic API:          $100/month
─────────────────────────────────
TOTAL (Full):               $549/month
```

---

## Testing Checklist

### Phase 0-1 (Weeks 1-4):
- [ ] Verify Coinbase client works with sandbox
- [ ] Test Binance WebSocket connection
- [ ] Confirm .env file loads correctly

### Phase 3 (Weeks 7-8):
- [ ] Test Reddit API connection
- [ ] Test FRED API data fetch
- [ ] Test NewsAPI headlines fetch
- [ ] (Optional) Test Twitter API if going that route

---

## Blockers & Risks

### 🔴 CRITICAL BLOCKERS:
- **None** - Coinbase sandbox is free, Binance public data is free

### 🟡 POTENTIAL BLOCKERS:
1. **Twitter API Cost** ($100/month)
   - **Mitigation**: Use Reddit instead (free, better for crypto)

2. **NewsAPI Rate Limits** (100 req/day free tier)
   - **Mitigation**: Fetch once every 5-10 minutes (8,640 minutes/day ÷ 100 = every 86 minutes max)
   - **Or**: Upgrade to $449/month if needed

3. **Coinbase Sandbox Limitations**
   - Sandbox has limited fake liquidity
   - **Mitigation**: Use for testing only, switch to prod when ready with real $1K

### 🔵 LOW PRIORITY:
- Etherscan rate limits (5 calls/sec is plenty)

---

## Next Steps

1. **RIGHT NOW**: Get Coinbase sandbox API keys (5 minutes)
2. **This Week**: Test Coinbase + Binance clients (30 minutes)
3. **Before Phase 3**: Get Reddit, FRED, NewsAPI keys (30 minutes total)
4. **Decide on Twitter**: Skip or pay $100/month?

**All critical APIs are ready to use.** ✅
**No technical blockers.** ✅
**Only decision needed: Twitter or not?** 🤔

---

## Quick Start Commands

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit .env with your API keys
nano .env  # or vim, code, etc.

# 3. Test configuration
python -c "from coinswarm.core.config import settings; print(settings.coinbase.coinbase_api_key[:10])"

# 4. Run Coinbase test
pytest tests/unit/test_coinbase_client.py -v

# 5. Run Binance test
pytest tests/unit/test_binance_ingestor.py -v
```

**You're ready to start trading! 🚀**
