# Coinswarm

**Intelligent Multi-Agent Trading System**

Coinswarm is an AI-powered trading system that uses specialized agents to gather information, analyze markets, learn patterns, and execute trades across cryptocurrency and equity markets.

## Status

🚧 **Phase 0: Planning & Design** - Documentation Complete

## Quick Links

- **[Complete Documentation](docs/README.md)** - Architecture overview and system design

**Core Systems**:
- **[Hierarchical Temporal Decision System](docs/architecture/hierarchical-temporal-decision-system.md)** - ⭐⭐⭐ **NEW** 3-layer cognitive hierarchy (11k words)
- **[Quorum Memory System](docs/architecture/quorum-memory-system.md)** - ⭐⭐ **PRODUCTION SPEC** (18k words)
- **[Multi-Agent Architecture](docs/agents/multi-agent-architecture.md)** - Complete agent roles with Planners/Committee/Memory
- **[Redis Infrastructure](docs/architecture/redis-infrastructure.md)** - Vector DB deployment & benchmarking
- **[Pattern Learning System](docs/patterns/pattern-learning-system.md)** - How the system learns and evolves

**Infrastructure**:
- **[Broker Selection](docs/architecture/broker-exchange-selection.md)** - Why Alpaca + Coinbase for Phase 0
- **[Coinbase API Integration](docs/api/coinbase-api-integration.md)** - Complete API documentation
- **[MCP Server Design](docs/architecture/mcp-server-design.md)** - Claude agent integration
- **[Information Sources](docs/architecture/information-sources.md)** - Data pipeline strategy

## Core Features

- 🧬 **3-Layer Cognitive Hierarchy**: Planners (strategic, weeks) → Committee (tactical, hours) → Memory (execution, seconds)
- 🤖 **Quorum-Governed Memory**: 3-vote consensus for all mutations (Byzantine fault-tolerant)
- ⚡ **Ultra-Low Latency**: Redis vector DB + NATS (< 2ms end-to-end)
- 🎯 **Temporal Division of Labor**: Each layer optimizes its own timescale without interference
- 🧠 **Online Learning**: Memory improves with every trade (no weight retrains)
- 📊 **Strategic Alignment**: Planners adjust committee weights based on macro sentiment/regimes
- 🎭 **Ensemble Voting**: Committee aggregates specialized agents (Trend, Mean-Rev, Risk, Exec, Arb)
- 🔐 **Complete Auditability**: Deterministic replay of all decisions and memory changes

## System Architecture

```
Self-Reflection Layer (Alignment Monitor)
    ↓
Planners (Strategic: Weeks-Months)
    ├─ Adjust Committee Weights
    ├─ Set Regime Tags
    └─ Update Thresholds
    ↓
Master Orchestrator + Committee (Tactical: Hours-Days)
    ├── Oversight Manager (Risk Controls)
    ├── Memory Managers (Quorum=3)
    └── Domain Agents (Weighted Ensemble)
        ├── Trend Agent
        ├── Mean-Reversion Agent
        ├── Execution Agent
        ├── Risk Agent
        └── Arbitrage Agent
    ↓
Memory Optimizer (Execution: Seconds-Minutes)
    ├── Pattern Recall (kNN retrieval)
    ├── Slippage Modeling
    └── Execution Heuristics
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
