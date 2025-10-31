# Coinswarm

**Intelligent Multi-Agent Trading System**

Coinswarm is an AI-powered trading system that uses specialized agents to gather information, analyze markets, learn patterns, and execute trades across cryptocurrency and equity markets.

## Status

🚧 **Phase 0: Planning & Design** - Documentation Complete

## Quick Links

- **[Complete Documentation](docs/README.md)** - Architecture overview and system design

**Core Systems**:
- **[Quorum Memory System](docs/architecture/quorum-memory-system.md)** - ⭐⭐ **PRODUCTION SPEC** (18k words)
- **[Multi-Agent Architecture](docs/agents/multi-agent-architecture.md)** - Agent roles with Memory Managers
- **[Agent Memory System](docs/architecture/agent-memory-system.md)** - Memory-Augmented MARL (conceptual)
- **[Redis Infrastructure](docs/architecture/redis-infrastructure.md)** - Vector DB deployment & benchmarking
- **[Pattern Learning System](docs/patterns/pattern-learning-system.md)** - How the system learns and evolves

**Infrastructure**:
- **[Broker Selection](docs/architecture/broker-exchange-selection.md)** - Why Alpaca + Coinbase for Phase 0
- **[Coinbase API Integration](docs/api/coinbase-api-integration.md)** - Complete API documentation
- **[MCP Server Design](docs/architecture/mcp-server-design.md)** - Claude agent integration
- **[Information Sources](docs/architecture/information-sources.md)** - Data pipeline strategy

## Core Features

- 🤖 **Quorum-Governed Memory**: 3-vote consensus for all memory mutations (Byzantine fault-tolerant)
- ⚡ **Ultra-Low Latency**: Redis vector DB + NATS message bus (< 2ms end-to-end)
- 🧠 **Online Learning**: Memory improves with every trade (no weight retrains)
- 🎯 **Episodic Control**: Neural Episodic Control (NEC) with regime-gated retrieval
- 🔐 **Audit Trail**: Complete deterministic replay of all memory changes
- 🛡️ **Safety Overlays**: Independent risk controls + memory quarantine for new patterns
- 📊 **Pattern Semantics**: Automatic clustering and promotion/deprecation of strategies
- 🔄 **Collective Intelligence**: Shared memory pool across all agents

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
- **Framework**: Memory-Augmented MARL with Quorum Consensus
- **Memory Layer**: Redis (vector DB) + NATS (message bus)
- **Governance**: 3-vote quorum (Byzantine fault-tolerant)
- **Brokers**: Alpaca (equities), Coinbase Advanced (crypto)
- **Data Storage**: InfluxDB (time-series), MongoDB (documents), PostgreSQL (relational)
- **MCP**: Model Context Protocol for Claude integration
- **APIs**: CCXT, NewsAPI, Twitter, Reddit, Etherscan, FRED
- **ML**: PyTorch (RL policies), scikit-learn (clustering, pattern extraction)

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
