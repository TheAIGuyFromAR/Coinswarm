# Coinswarm

**Intelligent Multi-Agent Trading System**

Coinswarm is an AI-powered trading system that uses specialized agents to gather information, analyze markets, learn patterns, and execute trades across cryptocurrency and equity markets.

## Status

🚧 **Phase 0: Planning & Design** - Documentation Complete

## Quick Links

- **[Complete Documentation](docs/README.md)** - Architecture overview and system design

**Core Systems**:
- **[Agent Memory System](docs/architecture/agent-memory-system.md)** - ⭐ Memory-Augmented MARL framework
- **[Redis Infrastructure](docs/architecture/redis-infrastructure.md)** - ⭐ Vector DB deployment & benchmarking
- **[Multi-Agent Architecture](docs/agents/multi-agent-architecture.md)** - Agent roles and responsibilities
- **[Pattern Learning System](docs/patterns/pattern-learning-system.md)** - How the system learns and evolves

**Infrastructure**:
- **[Broker Selection](docs/architecture/broker-exchange-selection.md)** - Why Alpaca + Coinbase for Phase 0
- **[Coinbase API Integration](docs/api/coinbase-api-integration.md)** - Complete API documentation
- **[MCP Server Design](docs/architecture/mcp-server-design.md)** - Claude agent integration
- **[Information Sources](docs/architecture/information-sources.md)** - Data pipeline strategy

## Core Features

- 🤖 **Memory-Augmented MARL**: Multi-agent reinforcement learning with explicit episodic/semantic memory
- ⚡ **Ultra-Low Latency**: Redis vector DB for sub-millisecond memory retrieval (3.4× faster than alternatives)
- 🧠 **Pattern Learning**: Automatically discovers and optimizes profitable trading patterns
- 🎯 **Regime Adaptation**: Detects market regime changes and adapts strategies accordingly
- 🛡️ **Risk Management**: Multiple layers of safety controls and circuit breakers
- 📊 **Comprehensive Data**: Market data, sentiment, on-chain metrics, and fundamentals
- 🔄 **Continuous Learning**: Agents learn from collective intelligence and past experiences
- 🔌 **Broker Agnostic**: Unified interface across multiple exchanges and brokers

## System Architecture

```
Master Orchestrator
    ├── Oversight Manager (Risk Controls)
    ├── Pattern Learning System
    └── Trading Execution Layer
        ├── Information Gathering Agents
        ├── Data Analysis Agents
        ├── Market Pattern Agents
        ├── Sentiment Analysis Agent
        └── Trading Agents (per product)
```

## Technology Stack

- **Language**: Python 3.11+
- **Framework**: Multi-Agent Reinforcement Learning (MARL)
- **Memory Layer**: Redis (vector database, sub-ms latency)
- **Brokers**: Alpaca (equities), Coinbase Advanced (crypto)
- **Data Storage**: InfluxDB (time-series), MongoDB (documents), PostgreSQL (relational)
- **MCP**: Model Context Protocol for Claude integration
- **APIs**: CCXT, NewsAPI, Twitter, Reddit, Etherscan, FRED
- **ML**: PyTorch (RL policies), scikit-learn (clustering, analysis)

## Phase 0 Goals

1. ✅ Complete architecture documentation
2. ⏳ Implement MCP server for Coinbase API
3. ⏳ Build multi-agent framework
4. ⏳ Create pattern learning system
5. ⏳ Paper trading validation

## Getting Started

*Coming soon - implementation in progress*

## License

TBD

---

**For detailed documentation, start here: [docs/README.md](docs/README.md)**
