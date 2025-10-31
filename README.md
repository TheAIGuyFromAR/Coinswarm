# Coinswarm

**Intelligent Multi-Agent Trading System**

Coinswarm is an AI-powered trading system that uses specialized agents to gather information, analyze markets, learn patterns, and execute trades across cryptocurrency and equity markets.

## Status

🚧 **Phase 0: Planning & Design** - Documentation Complete

## Quick Links

- **[Complete Documentation](docs/README.md)** - Architecture overview and system design
- **[Broker Selection](docs/architecture/broker-exchange-selection.md)** - Why Alpaca + Coinbase for Phase 0
- **[Multi-Agent Architecture](docs/agents/multi-agent-architecture.md)** - Agent roles and responsibilities
- **[Pattern Learning System](docs/patterns/pattern-learning-system.md)** - How the system learns and evolves
- **[Coinbase API Integration](docs/api/coinbase-api-integration.md)** - Complete API documentation
- **[MCP Server Design](docs/architecture/mcp-server-design.md)** - Claude agent integration
- **[Information Sources](docs/architecture/information-sources.md)** - Data pipeline strategy

## Core Features

- 🤖 **Multi-Agent System**: Specialized agents for gathering, analysis, learning, and execution
- 🧠 **Pattern Learning**: Automatically discovers and optimizes profitable trading patterns
- 🛡️ **Risk Management**: Multiple layers of safety controls and circuit breakers
- 📊 **Comprehensive Data**: Market data, sentiment, on-chain metrics, and fundamentals
- 🔄 **Adaptive**: Continuously learns from outcomes and market conditions
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
- **Brokers**: Alpaca (equities), Coinbase Advanced (crypto)
- **Data**: InfluxDB, MongoDB, PostgreSQL
- **MCP**: Model Context Protocol for Claude integration
- **APIs**: CCXT, NewsAPI, Twitter, Reddit, Etherscan, FRED

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
