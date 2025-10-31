# Coinswarm Architecture Documentation

## Overview

Coinswarm is an intelligent, multi-agent cryptocurrency and equities trading system built on Python. It leverages AI agents to gather information, analyze markets, learn patterns, and execute trades autonomously while maintaining strict risk controls and human oversight.

**Status**: Planning Phase
**Last Updated**: 2025-10-31
**Version**: 0.1.0 (Phase 0)

---

## System Vision

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Master Orchestrator                             │
│              (Strategic Coordinator & Decision Arbiter)                  │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
    ┌───────▼──────┐  ┌──────▼──────┐  ┌────▼─────────┐
    │  Oversight   │  │   Pattern   │  │   Trading    │
    │  Manager     │  │   Learning  │  │   Execution  │
    │  (Risk)      │  │   System    │  │   Layer      │
    └───────┬──────┘  └──────┬──────┘  └────┬─────────┘
            │                │              │
    ────────┴────────────────┴──────────────┴─────────────
            │                │              │
    ┌───────▼──────────┬─────▼──────┬───────▼──────────┐
    │ Information      │ Analysis   │ Pattern & Trade  │
    │ Gathering        │ Agents     │ Agents           │
    └───────┬──────────┴─────┬──────┴───────┬──────────┘
            │                │              │
    ────────┴────────────────┴──────────────┴─────────────
            │                │              │
    ┌───────▼────────────────▼──────────────▼──────────┐
    │          Model Context Protocol (MCP)             │
    │              Coinbase API Server                  │
    └───────┬────────────────┬──────────────┬──────────┘
            │                │              │
    ┌───────▼──────┐  ┌──────▼─────┐  ┌───▼────────┐
    │   Coinbase   │  │   Alpaca   │  │ External   │
    │   Advanced   │  │            │  │ Data APIs  │
    └──────────────┘  └────────────┘  └────────────┘
```

---

## Core Principles

### 1. Safety First
- Multiple layers of risk management
- Circuit breakers for automatic halts
- Human oversight and emergency stops
- Paper trading validation before live deployment

### 2. Learning & Adaptation
- Every trade is a learning opportunity
- Continuous pattern discovery and optimization
- Backtesting all strategies before deployment
- A/B testing for new patterns

### 3. Modularity
- Each component is independently testable
- Swappable brokers and data sources
- Agent specialization with clear interfaces
- Easy to add new agents or strategies

### 4. Transparency
- All decisions are logged with reasoning
- Complete audit trail for compliance
- Real-time monitoring dashboards
- Performance attribution per pattern/strategy

---

## Documentation Structure

### Architecture
- **[data-feeds-architecture.md](architecture/data-feeds-architecture.md)**: ⭐⭐⭐ **PRODUCTION SPEC** - Complete data acquisition layer with sources, cadences, and storage for all system layers
- **[hierarchical-temporal-decision-system.md](architecture/hierarchical-temporal-decision-system.md)**: ⭐⭐⭐ **NEW** - 3-layer cognitive hierarchy (Planners/Committee/Memory) with temporal division of labor (11k words)
- **[quorum-memory-system.md](architecture/quorum-memory-system.md)**: ⭐⭐ **PRODUCTION SPEC** - Quorum-governed, self-improving memory (18k words, implementation-ready)
- **[agent-memory-system.md](architecture/agent-memory-system.md)**: Memory-Augmented MARL with Redis vector database (conceptual foundation)
- **[redis-infrastructure.md](architecture/redis-infrastructure.md)**: Redis deployment, optimization, and benchmarking
- **[broker-exchange-selection.md](architecture/broker-exchange-selection.md)**: Broker/exchange selection strategy and migration path
- **[mcp-server-design.md](architecture/mcp-server-design.md)**: Model Context Protocol server for Coinbase API integration
- **[information-sources.md](architecture/information-sources.md)**: Comprehensive data sources strategy

### API Integration
- **[coinbase-api-integration.md](api/coinbase-api-integration.md)**: Complete Coinbase Advanced Trade API documentation with examples

### Agents
- **[multi-agent-architecture.md](agents/multi-agent-architecture.md)**: Detailed agent roles, responsibilities, and communication protocols

### Pattern Learning
- **[pattern-learning-system.md](patterns/pattern-learning-system.md)**: Pattern discovery, storage, optimization, and evolution system

### Testing & Development
- **[evidence-driven-development.md](testing/evidence-driven-development.md)**: ⭐⭐⭐ **CORE DISCIPLINE** - EDD testing strategy (TDD + economic soundness validation, 8k words)

---

## Technology Stack

### Core
- **Language**: Python 3.11+
- **Async Framework**: asyncio, aiohttp
- **Data Processing**: pandas, numpy
- **Machine Learning**: scikit-learn, tensorflow (optional)

### Trading Infrastructure
- **Brokers**: Alpaca (equities), Coinbase Advanced (crypto)
- **Order Router**: CCXT (unified interface)
- **MCP Server**: Model Context Protocol (Anthropic)

### Data Storage
- **Time Series**: InfluxDB (market data, OHLCV candles)
- **Documents**: MongoDB (news, social media, external data)
- **Relational**: PostgreSQL (trades, patterns, metadata, audit logs)
- **Vector Database**: Redis (agent memory, episodic/semantic storage)
  - **Why Redis**: 3.4× higher QPS than Qdrant, 4× lower latency than Milvus
  - **Performance**: Sub-millisecond latency for memory retrieval
  - **Critical for**: Memory-augmented MARL in HFT environment

### Data Sources
- **Market Data**: Coinbase, Alpaca, CoinGecko, Yahoo Finance
- **News**: NewsAPI, Google News, Alpha Vantage
- **Social**: Twitter API, Reddit (PRAW), StockTwits
- **On-Chain**: Etherscan, CryptoQuant, Glassnode, DeFi Llama
- **Macro**: FRED, BLS, Central Bank APIs

### Monitoring & Deployment
- **Metrics**: Prometheus
- **Visualization**: Grafana
- **Logging**: structlog
- **Orchestration**: Docker, docker-compose
- **CI/CD**: GitHub Actions

---

## Phase 0 Roadmap

### Week 1-2: Foundation
- [x] Architecture documentation
- [ ] Set up development environment
- [ ] Initialize Python project structure
- [ ] Set up Coinbase and Alpaca sandbox accounts
- [ ] Create MCP server skeleton

### Week 3-4: MCP Server
- [ ] Implement Coinbase API client (REST + WebSocket)
- [ ] Build MCP resource handlers
- [ ] Build MCP tool handlers
- [ ] Add authentication and rate limiting
- [ ] Write unit tests

### Week 5-6: Agent Framework
- [ ] Implement base agent classes
- [ ] Build message bus for inter-agent communication
- [ ] Create information gathering agents (market data, news)
- [ ] Create analysis agents (technical, sentiment)
- [ ] Orchestrator and oversight manager skeletons

### Week 7-8: Pattern System
- [ ] Trade recording system
- [ ] Pattern extraction engine
- [ ] Pattern library storage (PostgreSQL)
- [ ] Basic pattern matching logic

### Week 9-10: Trading Execution
- [ ] Trading agent implementation
- [ ] Order validation and safety checks
- [ ] Paper trading integration
- [ ] Position tracking

### Week 11-12: Testing & Refinement
- [ ] End-to-end integration tests
- [ ] Paper trading with real market data
- [ ] Performance monitoring setup
- [ ] Documentation refinement

---

## Key Features

### Intelligent Trading
- **Multi-Strategy**: Run multiple strategies in parallel across different products
- **Pattern Learning**: Automatically discover and optimize profitable patterns
- **Adaptive**: Continuously learns from market conditions and trade outcomes
- **Risk-Aware**: All trades evaluated against portfolio risk parameters

### Comprehensive Data
- **Market Data**: Real-time and historical price, volume, order book
- **Sentiment**: News, social media, alternative data
- **On-Chain**: Blockchain metrics for crypto assets
- **Fundamentals**: Financial statements, economic indicators

### Safety & Compliance
- **Risk Controls**: Position limits, daily loss limits, drawdown limits
- **Circuit Breakers**: Automatic halts on anomalies
- **Audit Trail**: Complete record of all decisions and trades
- **Human Oversight**: Manual overrides and approvals

### Scalability
- **Modular Design**: Easy to add new agents, strategies, or data sources
- **Async Architecture**: High-concurrency support
- **Broker Agnostic**: Simple to switch brokers or add new ones
- **Cloud Ready**: Containerized for easy deployment

---

## Getting Started (Future)

Once implemented, the system will be started with:

```bash
# Set up environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure credentials
cp .env.example .env
# Edit .env with API keys

# Start MCP server
python -m mcp_server.coinbase_server

# Start agent system
python -m agents.orchestrator --config config/agents.yaml
```

---

## Configuration

The system is configured via YAML files in the `config/` directory:

- **agents.yaml**: Agent configurations, strategies, risk parameters
- **mcp_server.yaml**: MCP server settings, rate limits, safety
- **data_sources.yaml**: Data source configurations and API keys
- **brokers.yaml**: Broker credentials and environments

---

## Monitoring

### Real-Time Dashboards
- Portfolio value and P&L
- Open positions and orders
- Risk utilization
- Agent health status
- Pattern performance

### Alerts
- Risk limit breaches
- Circuit breaker triggers
- API errors
- Unusual market conditions

---

## Risk Management

### Position Limits
- Max position size: 25% of portfolio
- Max order value: $1,000 (Phase 0)
- Max daily trades: 50
- Max concurrent trades: 5

### Loss Limits
- Max daily loss: 5% of portfolio
- Max drawdown: 10% of portfolio
- Stop loss on all positions

### Approval Thresholds
- Orders > $500: Requires confirmation
- New patterns: Requires backtesting (Sharpe > 1.5, Win rate > 60%)
- Strategy changes: Requires approval

---

## Success Metrics

### Trading Performance
- Sharpe Ratio > 1.5
- Win Rate > 60%
- Max Drawdown < 10%
- Profit Factor > 2.0

### System Performance
- API uptime > 99.5%
- Order fill rate > 95%
- Average order latency < 500ms
- Error rate < 1%

### Learning System
- Pattern library size > 100
- Pattern discovery rate > 5/week
- Pattern optimization improvement > 10%/quarter

---

## Future Enhancements

### Phase 1 (Months 3-6)
- Live trading with small capital
- Options strategies
- Pairs trading
- Multi-timeframe analysis

### Phase 2 (Months 6-12)
- Advanced ML models (LSTMs, Transformers)
- Reinforcement learning for strategy optimization
- Multi-exchange arbitrage
- Portfolio optimization algorithms

### Phase 3 (Year 2+)
- Global market expansion (IBKR integration)
- DeFi protocol integration
- Automated strategy discovery
- Institutional-grade reporting

---

## Contributing

This project is currently in the planning phase. Once implementation begins, contribution guidelines will be added.

---

## License

TBD

---

## Contact

For questions or feedback, please open an issue on GitHub.

---

## Appendix: Document Cross-References

### When designing brokers/exchanges
→ See [broker-exchange-selection.md](architecture/broker-exchange-selection.md)

### When implementing Coinbase integration
→ See [coinbase-api-integration.md](api/coinbase-api-integration.md)
→ See [mcp-server-design.md](architecture/mcp-server-design.md)

### When adding data sources
→ See [information-sources.md](architecture/information-sources.md)

### When creating new agents
→ See [multi-agent-architecture.md](agents/multi-agent-architecture.md)

### When working on pattern learning
→ See [pattern-learning-system.md](patterns/pattern-learning-system.md)

### When implementing agent memory or vector database
→ See [agent-memory-system.md](architecture/agent-memory-system.md)
→ See [redis-infrastructure.md](architecture/redis-infrastructure.md)

---

## Research References

The Coinswarm architecture integrates cutting-edge research in multi-agent reinforcement learning and vector databases:

### Multi-Agent Reinforcement Learning (MARL)

1. **Ning, Z. et al. (2024)**
   - "A survey on multi-agent reinforcement learning and its applications"
   - Comprehensive overview of MARL methods, challenges, and applications
   - Key concepts: Centralized training/decentralized execution, credit assignment, non-stationarity

2. **Wei, X. et al. (2024)**
   - "Multi-Agent Reinforcement Learning for High-Frequency Trading Strategy Optimization"
   - Applied MARL to HFT with strong results (Sharpe ratio 2.87)
   - Demonstrates feasibility of multi-agent coordination in financial markets

3. **Zong, J. et al. (2024)**
   - "MacroHFT: Memory Augmented Context-aware Reinforcement Learning On High Frequency Trading"
   - **Key innovation**: Memory mechanism for regime adaptation in HFT
   - Architecture: Sub-agents per regime + hyper-agent with memory
   - Validates using explicit memory (not just model weights) for agent adaptation

4. **Shavandi, A. (2022)**
   - "A multi-agent deep reinforcement learning framework for trade on the collective intelligence"
   - Concrete RL system applying multi-agent deep RL in trading domain
   - Supports using separate agents in swarm with shared information

5. **Fang, J. et al. (2022)**
   - "Imitate then Transcend: Multi-Agent Optimal Execution with Dual-Window Denoise PPO"
   - MARL for optimal execution (key HFT sub-task)
   - Combines imitation learning + multi-agent RL for noisy markets

### Vector Database Performance

6. **Redis (2024)**
   - "Benchmarking results for vector databases"
   - **Key finding**: Redis achieved 3.4× higher QPS than Qdrant, 4× lower latency than Milvus
   - Recall ≥ 0.98 maintained across tests
   - Justifies Redis as primary vector store for sub-millisecond memory retrieval

7. **Redis (2024)**
   - "Announcing faster Redis Query Engine and our vector database leads benchmarks"
   - 16× throughput improvement in Redis Query Engine
   - Outperforms top 7 vector DBs under identical hardware

8. **Pixion (2025)**
   - "Vector Database Benchmark – Overview"
   - Comparative analysis: Redis, Milvus, Chroma, Qdrant
   - Redis leads in latency/QPS for certain dimensions
   - Trade-offs exist: Milvus better for indexing, but slower queries

9. **Qdrant (2024)**
   - "Vector Database Benchmarks"
   - **Important caveat**: Redis latency increases with concurrency
   - Single-thread: excellent; high concurrency: degradation
   - Informs our query batching and replica strategy

### Application to Coinswarm

**Design Decisions Based on Research**:
- ✅ Multi-agent architecture with memory (MacroHFT, Wei et al.)
- ✅ Redis for ultra-low latency vector lookups (Redis benchmarks)
- ✅ Episodic + semantic memory structure (Zong et al.)
- ✅ Regime detection and adaptation (MacroHFT)
- ✅ Shared memory pool for collective intelligence (Shavandi)
- ✅ Concurrency mitigation: batching, pooling, replicas (Qdrant benchmarks)

**Performance Targets** (informed by research):
- Memory retrieval latency: < 1ms (P50), < 5ms (P99)
- Sharpe ratio: > 2.0 (Wei et al. achieved 2.87)
- Regime adaptation: < 10 seconds to detect shift
- Pattern matching: 1000+ queries/second across 10+ agents

---

**Ready to build the future of intelligent trading? Let's start coding.**
