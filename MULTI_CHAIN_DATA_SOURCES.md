# Multi-Chain Crypto Data Sources

## Overview
Comprehensive data sources for tokens across multiple chains with low gas costs and fast execution.

---

## 1. Universal Aggregators (All Chains)

### DexScreener API ⭐⭐⭐
**Free, no API key, covers ALL DEXes**
- Endpoint: `https://api.dexscreener.com/latest/dex`
- Supports: Ethereum, BSC, Solana, Arbitrum, Optimism, Polygon, Avalanche, Fantom, Base, and 50+ more
- Data: Real-time prices, 24h volume, liquidity, price changes
- Example: `/pairs/solana/USDC` or `/tokens/0x...`

### GeckoTerminal API ⭐⭐⭐
**CoinGecko's DEX aggregator - Free**
- Endpoint: `https://api.geckoterminal.com/api/v2`
- Supports: 100+ networks including all major L2s
- Data: OHLCV, pools, trending tokens
- Example: `/networks/solana/pools` or `/networks/arbitrum/tokens/...`

### 1inch API ⭐⭐
**Multi-chain aggregator**
- Endpoint: `https://api.1inch.dev/swap/v5.2`
- Supports: Ethereum, BSC, Polygon, Arbitrum, Optimism, Avalanche
- Data: Best swap routes, prices across DEXes
- Requires API key (free tier available)

---

## 2. BNB Chain (BSC) - Low Gas, Fast

### PancakeSwap API ⭐⭐⭐
**#1 BSC DEX - Free**
- Endpoint: `https://api.pancakeswap.info/api/v2`
- Data: Token prices, pairs, 24h stats
- Example: `/tokens/0x...` or `/pairs`

### BSCScan API ⭐⭐
**Blockchain explorer API**
- Endpoint: `https://api.bscscan.com/api`
- Data: Token info, transactions, contract data
- Requires API key (free)

### Thena API
**New BSC DEX with good liquidity**
- Endpoint: Check their docs
- Data: Pools, swaps, liquidity

---

## 3. Solana - Ultra Low Cost

### Jupiter Aggregator API ⭐⭐⭐
**Best Solana aggregator - Free**
- Endpoint: `https://quote-api.jup.ag/v6`
- Data: Best prices across all Solana DEXes
- Example: `/quote?inputMint=...&outputMint=...&amount=...`

### Birdeye API ⭐⭐⭐
**Comprehensive Solana data**
- Endpoint: `https://public-api.birdeye.so`
- Data: Token prices, OHLCV, metadata, trending
- Requires API key (free tier)

### Raydium API ⭐⭐
**Major Solana DEX**
- Endpoint: `https://api.raydium.io/v2`
- Data: Pools, pairs, liquidity

### Orca API
**Solana DEX**
- GraphQL endpoint
- Data: Pools, prices, volume

### Pyth Network ⭐⭐⭐
**Solana price oracle - Free**
- Endpoint: `https://hermes.pyth.network/api`
- Data: Real-time oracle prices for 400+ assets
- Example: `/latest_price_feeds?ids[]=...`

---

## 4. Layer 2 Ethereum - Low Gas

### Uniswap V3 Subgraph ⭐⭐⭐
**Works on: Arbitrum, Optimism, Polygon, Base**
- GraphQL endpoints per network
- Arbitrum: `https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3-arbitrum`
- Optimism: `https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3-optimism`
- Polygon: `https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3-polygon`
- Base: `https://api.studio.thegraph.com/query/.../uniswap-v3-base`

### Velodrome API (Optimism) ⭐⭐
**Leading Optimism DEX**
- Endpoint: `https://api.velodrome.finance`
- Data: Pools, APRs, volume

### Camelot API (Arbitrum) ⭐⭐
**Leading Arbitrum DEX**
- Endpoint: Check their API docs
- Data: Pools, liquidity, rewards

### QuickSwap API (Polygon) ⭐⭐
**Leading Polygon DEX**
- Endpoint: `https://api.quickswap.exchange`
- Data: Pairs, prices, liquidity

---

## 5. Other Fast Networks

### Trader Joe API (Avalanche) ⭐⭐
**#1 Avalanche DEX**
- Endpoint: `https://api.traderjoexyz.com`
- Data: Pools, prices, APRs
- Works on Avalanche C-Chain (sub-second finality)

### SpookySwap API (Fantom)
**Leading Fantom DEX**
- Endpoint: Check their docs
- Data: Pairs, liquidity, farms

### SushiSwap API (Multi-chain) ⭐⭐
**Deployed on 20+ chains**
- Various endpoints per chain
- Data: Pools, volume, APRs
- Supports: Arbitrum, Optimism, Polygon, Avalanche, Fantom, BSC

---

## 6. On-Chain Oracle Data

### Chainlink Price Feeds ⭐⭐⭐
**Most reliable oracles**
- Read directly from contracts
- Available on: Ethereum, BSC, Polygon, Arbitrum, Optimism, Avalanche
- 1000+ price feeds

### Band Protocol
**Oracle data**
- Endpoint: `https://laozi1.bandchain.org/api/oracle/v1`
- Data: Price references for multiple assets

---

## Implementation Priority

### Phase 1: Universal Aggregators (Easiest)
1. **DexScreener API** - Single endpoint, all chains
2. **GeckoTerminal API** - Comprehensive DEX data
3. Already done: CryptoCompare, CoinGecko, Binance, Coinbase

### Phase 2: Solana (High Volume)
1. **Jupiter API** - Best aggregator
2. **Birdeye API** - Complete Solana data
3. **Pyth Network** - Oracle prices

### Phase 3: Layer 2s (Growing Fast)
1. **Uniswap V3 Subgraphs** - Arbitrum, Optimism, Base, Polygon
2. **Velodrome** (Optimism)
3. **Camelot** (Arbitrum)

### Phase 4: Alt L1s
1. **Trader Joe** (Avalanche)
2. **PancakeSwap** (BSC)
3. **SushiSwap** (multi-chain)

---

## Data Collation Strategy

For each token/pair:
```typescript
{
  symbol: "ARB",
  sources: [
    { name: "dexscreener", price: 0.85, volume24h: 50000000 },
    { name: "geckoterminal", price: 0.851, volume24h: 51000000 },
    { name: "uniswap-arbitrum", price: 0.849, volume24h: 48000000 },
    { name: "camelot", price: 0.852, volume24h: 12000000 }
  ],
  aggregated: {
    median_price: 0.850,
    mean_price: 0.8505,
    price_variance: 0.003,
    total_volume24h: 161000000,
    source_count: 4,
    confidence_score: 0.95  // Low variance = high confidence
  }
}
```

## Benefits of Multi-Source Approach

1. **Enhanced Accuracy**: Cross-validate prices across sources
2. **Detect Anomalies**: Flag outliers (flash crashes, manipulation)
3. **Fill Gaps**: If one source fails, others provide backup
4. **Volume Verification**: Aggregate volume across DEXes
5. **Arbitrage Detection**: Identify price discrepancies
6. **Network Coverage**: Trade opportunities across all chains

---

## Free API Summary

**No API Key Required:**
- ✅ DexScreener
- ✅ GeckoTerminal
- ✅ CryptoCompare
- ✅ CoinGecko
- ✅ Binance
- ✅ Coinbase
- ✅ Jupiter
- ✅ Raydium
- ✅ PancakeSwap
- ✅ Uniswap Subgraphs
- ✅ Pyth Network

**API Key (Free Tier):**
- 🔑 Birdeye (Solana)
- 🔑 BSCScan
- 🔑 1inch
- 🔑 The Graph (higher limits)

---

## Next Steps

1. Add DexScreener + GeckoTerminal to historical worker
2. Add Jupiter + Pyth for Solana
3. Add Uniswap V3 subgraphs for L2s
4. Implement data collation & validation
5. Store multi-source data in price_data table with metadata
