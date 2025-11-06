# Broker and Exchange Selection Strategy

## Phase 0: Foundation Layer

### Overview
This document outlines the broker and exchange selection strategy for Coinswarm's multi-agent trading system. The approach prioritizes rapid prototyping with production-ready migration paths.

---

## Broker/Exchange Options Analysis

### Equities

#### Alpaca
- **Type**: Commission-free stock trading API
- **Pros**:
  - Free paper trading environment
  - REST and WebSocket API support
  - Simple OAuth key authentication
  - Fractional shares support
  - Optional crypto trading
  - Fast iteration and development cycle
  - CCXT library support
- **Cons**:
  - No shorting capabilities
  - Limited instrument coverage
  - Slower fills on live accounts compared to institutional brokers
- **Use Case**: Prototype development and early live testing
- **Priority**: **Primary for Phase 0**

#### Interactive Brokers (IBKR)
- **Type**: Professional-grade broker with global reach
- **Pros**:
  - Deep liquidity across markets
  - Global market access
  - Options and futures support
  - Stable, battle-tested API
  - Institutional-grade execution
- **Cons**:
  - Setup friction (account approval, compliance)
  - Slower API iteration cycle
  - Complex regulatory onboarding
  - Higher learning curve
- **Use Case**: Production deployment after paper trading validation
- **Priority**: **Secondary - Post Phase 0**

---

### Cryptocurrency

#### Coinbase Advanced
- **Type**: Regulated U.S. cryptocurrency exchange
- **Pros**:
  - Fully regulated in the United States
  - Robust REST and WebSocket APIs
  - Good sandbox environment for testing
  - USD trading pairs
  - Clear documentation
  - CCXT library support
  - Compliance-first approach
- **Cons**:
  - Limited perpetual contract offerings
  - Lower liquidity compared to Binance
  - Higher fees than offshore exchanges
- **Use Case**: Compliance-first live crypto trading
- **Priority**: **Primary for Phase 0**

#### Kraken
- **Type**: Established crypto exchange with advanced features
- **Pros**:
  - Solid API infrastructure
  - Funding rate data availability
  - Spot and futures markets
  - Margin trading (optional for later phases)
  - Broader cryptocurrency universe
- **Cons**:
  - Less realistic sandbox environment
  - Higher latency compared to Binance
  - More complex API structure
- **Use Case**: Broader crypto universe testing and futures exploration
- **Priority**: **Tertiary - Future expansion**

---

## Phase 0 Recommendation

### Primary Stack: Alpaca + Coinbase Advanced

**Rationale**:
1. **Free Paper Trading**: Both provide realistic paper trading environments at no cost
2. **API Stability**: Both have mature, well-documented REST and WebSocket APIs
3. **Low Friction**: Minimal compliance requirements for paper trading and development
4. **Fast Iteration**: Quick account setup and API key generation
5. **CCXT Support**: Common library support enables unified interface design
6. **Production Path**: Both support real trading when ready to deploy

**Phase 0 Goals**:
- Validate multi-agent architecture
- Test order routing and execution stack
- Develop pattern learning system
- Refine information gathering pipelines
- Establish oversight and orchestration workflows

---

## API Comparison Matrix

| Feature | Alpaca | IBKR | Coinbase Advanced | Kraken |
|---------|---------|------|-------------------|--------|
| **Authentication** | OAuth API Keys | OAuth + 2FA | API Key + Secret + Passphrase | API Key + Private Key |
| **Rate Limits** | 200 req/min | ~50 req/sec | 10 req/sec (public), 15 req/sec (private) | Varies by tier |
| **Order Types** | Market, Limit, Stop, Stop-Limit, Trailing Stop | All standard + advanced | Market, Limit, Stop-Limit | Market, Limit, Stop-Loss, Take-Profit |
| **Sandbox Realism** | Excellent (real-time paper) | Limited | Good | Fair |
| **WebSocket Data** | Trades, Quotes, Bars | Real-time market data | L2 Order Book, Tickers, Matches | OHLC, Trades, Book |
| **Data Granularity** | 1-min bars minimum | Tick-level | Ticker updates, trade-level | 1-min OHLC minimum |
| **Fractional Trading** | Yes | No | Yes | No |
| **Short Selling** | No | Yes | No (crypto) | Margin optional |
| **Global Markets** | US only | Global | Global crypto | Global crypto |
| **Setup Time** | Minutes | Days/weeks | Hours | Hours |
| **Production Cost** | Free (commission-free) | Tiered fees | 0.4-0.6% taker fee | 0.16-0.26% taker fee |

---

## Migration Path

### Phase 0 → Phase 1 Transition

**Current (Phase 0)**:
- Alpaca (equities paper trading)
- Coinbase Advanced (crypto paper/testnet)

**Target (Phase 1 - Production)**:
- Alpaca (live equities with small capital)
- Coinbase Advanced (live crypto with small capital)
- Begin IBKR integration (parallel paper trading)

**Target (Phase 2 - Scale)**:
- IBKR (primary equities with full capital)
- Coinbase Advanced (primary crypto)
- Kraken (alternative crypto, futures exploration)

---

## Technical Architecture Requirements

### Order Router Abstraction

The system must maintain a **broker-agnostic order router** to enable seamless transitions:

```python
# Abstract interface (all brokers must implement)
class BrokerAdapter:
    def authenticate(self) -> bool
    def get_account_info(self) -> AccountInfo
    def get_positions(self) -> List[Position]
    def get_market_data(self, symbol: str) -> MarketData
    def place_order(self, order: Order) -> OrderResult
    def cancel_order(self, order_id: str) -> bool
    def get_order_status(self, order_id: str) -> OrderStatus
    def subscribe_market_data(self, symbols: List[str], callback: Callable)
```

### Configuration Schema

Broker configurations must be swappable via environment/config files:

```yaml
brokers:
  alpaca:
    enabled: true
    environment: paper  # paper | live
    api_key: ${ALPACA_API_KEY}
    api_secret: ${ALPACA_SECRET_KEY}

  coinbase:
    enabled: true
    environment: sandbox  # sandbox | live
    api_key: ${COINBASE_API_KEY}
    api_secret: ${COINBASE_SECRET}
    api_passphrase: ${COINBASE_PASSPHRASE}

  ibkr:
    enabled: false
    environment: paper
    # ... (future)
```

---

## Decision Log

### Why Not Binance?
- Regulatory uncertainty in the U.S.
- Potential compliance issues for future fundraising/audits
- Risk of sudden service interruption for U.S. users

### Why Not TD Ameritrade?
- API access being phased out post-Schwab acquisition
- Migration uncertainty

### Why Delay IBKR?
- Onboarding friction slows Phase 0 iteration
- Better to validate architecture with simpler brokers first
- IBKR integration can happen in parallel during Phase 1

---

## Next Steps

1. ✅ Document broker selection rationale (this document)
2. ⏳ Create detailed Coinbase API integration plan
3. ⏳ Design MCP server for Coinbase API access
4. ⏳ Implement Alpaca adapter with CCXT
5. ⏳ Implement Coinbase Advanced adapter with CCXT
6. ⏳ Build unified order router abstraction
7. ⏳ Test paper trading workflows on both platforms

---

**Last Updated**: 2025-10-31
**Status**: Planning Phase
**Next Review**: After MCP + API integration docs complete
