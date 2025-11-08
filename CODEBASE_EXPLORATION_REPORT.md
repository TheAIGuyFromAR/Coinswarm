# Coinswarm Codebase Exploration - Comprehensive Report

**Repository**: Coinswarm - Intelligent Multi-Agent Trading System
**Type**: Python-based cryptocurrency and equities trading system with AI agents
**Status**: Phase 0 - Planning/Early Implementation
**Version**: 0.1.0

---

## 1. DIRECTORY STRUCTURE OVERVIEW

### Root Level Structure
```
/home/user/Coinswarm/
├── .github/                          # CI/CD workflows
├── src/coinswarm/                    # Main application code (49 Python modules)
├── tests/                            # Test suite (22 Python test modules)
├── cloudflare-workers/               # Edge functions for data fetching
├── docs/                             # Comprehensive architecture documentation
├── scripts/                          # Deployment and utility scripts
├── config/                           # Configuration files
├── README.md                         # Project overview
├── pyproject.toml                    # Python project configuration
├── docker-compose.yml                # Service orchestration
├── Makefile                          # Development commands
├── .env.example                      # Environment template
└── requirements.txt                  # Python dependencies
```

### Key Directories

#### `/src/coinswarm/` - Main Application (49 Python files)
```
src/coinswarm/
├── agents/                           # Multi-agent system (11 agents)
│   ├── academic_research_agent.py   # Research & analysis
│   ├── arbitrage_agent.py           # Cross-exchange arbitrage
│   ├── base_agent.py                # Base agent interface
│   ├── committee.py                 # Agent voting/consensus
│   ├── hedge_agent.py               # Risk hedging
│   ├── research_agent.py            # Market research
│   ├── risk_agent.py                # Risk management
│   ├── strategy_learning_agent.py   # Pattern learning
│   ├── trade_analysis_agent.py      # Trade analysis
│   ├── trend_agent.py               # Trend following
│   └── __init__.py
│
├── api/                             # External API clients
│   └── coinbase_client.py           # Coinbase Advanced Trade API client
│
├── backtesting/                     # Backtesting engine
│   ├── backtest_engine.py           # Core backtesting logic
│   ├── continuous_backtester.py     # Continuous validation
│   ├── multi_timescale_validator.py # Multi-timeframe validation
│   ├── random_window_validator.py   # Random window testing
│   └── __init__.py
│
├── core/                            # Configuration & settings
│   └── config.py                    # Centralized configuration
│
├── data_ingest/                     # Data acquisition layer
│   ├── base.py                      # Base data ingestor class
│   ├── binance_ingestor.py          # Binance exchange data
│   ├── coinswarm_worker_client.py   # Cloudflare Worker integration
│   ├── csv_importer.py              # CSV data import
│   ├── google_sentiment_fetcher.py  # Google search sentiment
│   ├── historical_data_fetcher.py   # Historical price data
│   ├── macro_trends_fetcher.py      # Macro economic data
│   ├── news_sentiment_fetcher.py    # News sentiment analysis
│   ├── worker_client.py             # Generic worker client
│   ├── exchanges/
│   │   ├── binance.py               # Binance API wrapper
│   │   └── __init__.py
│   ├── macro/
│   │   └── __init__.py
│   ├── news/
│   │   └── __init__.py
│   ├── onchain/
│   │   └── __init__.py
│   ├── processors/
│   │   └── __init__.py
│   ├── registry/
│   │   └── __init__.py
│   └── __init__.py
│
├── memory/                          # Memory & learning systems
│   ├── exploration_strategy.py      # Strategy exploration
│   ├── hierarchical_memory.py       # Hierarchical memory
│   ├── learning_loop.py             # Continuous learning
│   ├── memory_persistence.py        # Memory persistence
│   ├── simple_memory.py             # Simple memory implementation
│   ├── state_builder.py             # State representation
│   └── __init__.py
│
├── mcp_server/                      # Model Context Protocol server
│   ├── server.py                    # MCP server for Coinbase integration
│   └── __init__.py
│
├── utils/                           # Utilities
│   └── __init__.py
│
├── single_user_bot.py               # Monolithic single-user bot (601 lines)
└── py.typed                         # Type hints marker
```

#### `/tests/` - Test Suite (8 categories)
```
tests/
├── unit/                            # Unit tests
│   ├── test_binance_ingestor.py
│   ├── test_coinbase_client.py
│   ├── test_config.py
│   ├── test_data_ingest_base.py
│   ├── test_mcp_server.py
│   └── __init__.py
├── integration/                     # Integration tests
│   ├── test_postgres.py
│   ├── test_redis.py
│   └── __init__.py
├── backtest/                        # Backtesting tests
│   └── __init__.py
├── performance/                     # Performance tests
├── soundness/                       # Economic soundness tests (EDD)
│   ├── base.py
│   ├── test_binance_soundness.py
│   ├── test_coinbase_soundness.py
│   ├── test_mcp_soundness.py
│   └── __init__.py
├── fixtures/                        # Test data & market scenarios
│   ├── market_data/
│   │   ├── golden_cross.py
│   │   ├── high_volatility.py
│   │   ├── mean_reversion.py
│   │   ├── range_bound.py
│   │   └── __init__.py
│   ├── __init__.py
│   └── README.md
└── __init__.py
```

#### `/cloudflare-workers/` - Edge Functions
```
cloudflare-workers/
├── data-fetcher.js                  # Basic historical data fetcher
├── data-fetcher-paginated.js        # Paginated fetcher (2+ years support)
├── multi-source-data-fetcher.js     # Multi-source fetcher (13.7KB)
├── wrangler.toml                    # Basic worker config
├── wrangler-multi-source.toml       # Multi-source config
└── README.md                        # Worker documentation
```

---

## 2. CLOUDFLARE WORKER FILES & ENDPOINTS

### Worker 1: Basic Data Fetcher (`data-fetcher.js`)
**Purpose**: Fetch and cache historical crypto data from Binance
**Endpoints**:
- `GET /fetch` - Fetch fresh data from Binance
- `GET /cached` - Get cached data from KV storage
- `OPTIONS /` - CORS preflight handling

**Parameters**:
- `symbol` - Trading pair (e.g., BTCUSDT, ETHUSDT)
- `timeframe` - Candle interval (1m, 5m, 15m, 1h, 4h, 1d)
- `days` - Historical days (1-365)

**Features**:
- CORS enabled (Access-Control-Allow-Origin: *)
- Binance API integration
- KV storage caching (1-hour TTL)
- Free tier: 100K requests/day, 10ms CPU

### Worker 2: Paginated Data Fetcher (`data-fetcher-paginated.js`)
**Purpose**: Fetch 2+ years of historical data with pagination
**Endpoints**:
- `GET /fetch` - Fetch with pagination support (can get 730+ days)
- `GET /cached` - Get cached paginated data
- `OPTIONS /` - CORS preflight

**Key Features**:
- Pagination to bypass Binance 1000-candle limit
- Supports 2+ years of historical data
- Enhanced from basic fetcher

### Worker 3: Multi-Source Data Fetcher (`multi-source-data-fetcher.js`, 13.7KB)
**Purpose**: Fetch from multiple data sources for redundancy and coverage
**Endpoints**:
- `GET /multi-price` - Multi-source historical data (2+ years)
- `GET /price` - Original price endpoint (Kraken/Coinbase, 30 days)
- `GET /defi` - DeFi protocol data
- `GET /oracle` - Oracle data (Pyth, Switchboard)
- Root `/` - API documentation

**Data Sources**:
1. **Centralized**: CoinGecko, CryptoCompare, Kraken, Coinbase
2. **DeFi**: DeFiLlama, Jupiter (Solana)
3. **Oracles**: Pyth Network, Switchboard

**Parameters**:
- `symbol` - Asset symbol (BTC, ETH, SOL)
- `days` - Historical days (up to 730)
- `aggregate` - Aggregate results (true/false)
- `protocol` - DeFi protocol name
- `chain` - Blockchain (solana, ethereum)
- `source` - Oracle source (pyth, switchboard)

---

## 3. API ENDPOINTS & CONFIGURATIONS

### Coinbase Advanced Trade API Client
**File**: `/src/coinswarm/api/coinbase_client.py` (100+ lines)
**Type**: REST API client with HMAC-SHA256 authentication

**Implemented Classes**:
- `OrderSide` - Enum: BUY, SELL
- `OrderType` - Enum: MARKET, LIMIT, STOP_LIMIT
- `TimeInForce` - Enum: GTC, GTD, IOC, FOK
- `CoinbaseAPIClient` - Main API client

**Async Methods**:
- Authentication with HMAC-SHA256 signature generation
- Automatic retry logic (tenacity library)
- Rate limiting support
- Error handling with structured logging

**Key Features**:
- Context manager support (`async with`)
- Configurable base URL and credentials
- Request signing with timestamp

### MCP Server (Model Context Protocol)
**File**: `/src/coinswarm/mcp_server/server.py` (21.9KB)
**Type**: Server for Claude agent integration via MCP

**Resources Exposed**:
- `coinbase://accounts` - Trading accounts with balances
- `coinbase://products` - Available trading products
- `coinbase://orders` - All orders (open and historical)
- `coinbase://fills` - Executed fills

**Tools Registered**: (via MCP tool handlers)
- Order placement, cancellation
- Account management
- Market data queries

---

## 4. DOCUMENTATION FILES

### Main Documentation Structure (30 files)

**Root Documentation** (`.md` files):
- `README.md` - Project overview
- `GETTING_STARTED.md` - Quick start guide
- `DEVELOPMENT.md` - Development setup
- `DEPLOYMENT_RESULTS.md` - Deployment outcomes
- `FINAL_SUMMARY_MULTI_SOURCE.md` - Multi-source implementation
- `P0_SOLUTION_2PLUS_YEARS.md` - 2+ years data solution
- `STRATEGY_DISCOVERY_FINDINGS.md` - Strategy discovery results
- `MEMORY_SYSTEM_IMPLEMENTATION.md` - Memory system docs
- `ARCHITECTURE_DRIFT_ANALYSIS.md` - Architecture analysis
- `WORKER_DATA_LIMITATION.md` - Worker limitations
- `NETWORK_LIMITATIONS_SUMMARY.md` - Network constraints
- `MULTI_TIMESCALE_STRATEGY_GUIDE.md` - Multi-timeframe strategies

**In `/docs/` Directory**:

**Architecture** (9 files):
1. `data-feeds-architecture.md` ⭐⭐⭐ - Production spec for data layer
2. `hierarchical-temporal-decision-system.md` ⭐⭐⭐ - 3-layer cognitive hierarchy (11k words)
3. `quorum-memory-system.md` ⭐⭐ - Memory with Byzantine quorum (18k words)
4. `agent-memory-system.md` - Memory-augmented MARL foundation
5. `redis-infrastructure.md` - Redis deployment & benchmarking
6. `broker-exchange-selection.md` - Broker selection strategy
7. `mcp-server-design.md` - Model Context Protocol integration
8. `information-sources.md` - Data sources strategy
9. `agent-swarm-architecture.md` - Agent coordination

**API** (1 file):
- `coinbase-api-integration.md` - Complete Coinbase API documentation

**Agents** (1 file):
- `multi-agent-architecture.md` - Agent roles and protocols

**Patterns** (1 file):
- `pattern-learning-system.md` - Pattern discovery and learning

**Testing & Development** (7 files):
- `evidence-driven-development.md` ⭐⭐⭐ - EDD discipline (8k words)
- `atomic-action-plan.md` - Implementation roadmap
- `gap-analysis.md` - Current gaps
- `implementation-plan-outline.md` - Plan outline
- `implementation-plan.md` - Detailed plan
- `continuous-backtesting-guide.md` - Backtest methodology
- `single-user-deployment-guide.md` - Deployment guide

**Infrastructure** (6 files):
- `cloudflare-free-tier-maximization.md` - Optimize Cloudflare
- `cloudflare-workers-analysis.md` - Workers analysis
- `exchange-api-latency-optimization.md` - Latency optimization
- `free-tier-performance-analysis.md` - Performance analysis
- `multi-cloud-free-tier-optimization.md` - Multi-cloud strategy
- `single-user-architecture.md` - Single-user architecture

**Setup** (1 file):
- `api-keys-guide.md` - API key setup

**Other** (2 files):
- `DATA_SOURCES.md` - Data source configurations
- `HOW_SENTIMENT_WORKS.md` - Sentiment analysis documentation

---

## 5. CONFIGURATION FILES

### Package & Project Configuration

**`pyproject.toml`** (183 lines)
- **Name**: coinswarm
- **Version**: 0.1.0
- **Python**: >=3.11
- **Build System**: setuptools

**Core Dependencies** (23 packages):
- Async: asyncio-mqtt, aiohttp, aiofiles
- MCP: mcp>=0.9.0
- Trading APIs: ccxt>=4.2.0, alpaca-py>=0.21.0
- Data: pandas>=2.1.0, numpy>=1.26.0, scikit-learn>=1.3.0
- Vector Storage: redis>=5.0.0, redis-om>=0.2.0
- Message Bus: nats-py>=2.6.0
- ML: torch>=2.1.0
- Databases: asyncpg, motor, influxdb-client
- Config: pydantic>=2.5.0, pydantic-settings>=2.1.0
- Logging: structlog>=23.2.0
- Monitoring: prometheus-client>=0.19.0
- Utils: httpx, tenacity, cachetools

**Optional Dependencies**:
- dev: pytest, black, ruff, mypy, ipython
- test: pytest extensions, faker
- docs: mkdocs, mkdocs-material

**Testing Configuration**:
- Test paths: `tests/`
- Markers: unit, integration, performance, soundness, slow
- Coverage: src/coinswarm, excluding tests and __init__.py
- Async mode: auto
- Python path: src/

**Code Quality Tools**:
- Black: 100-char line length, py311
- Ruff: E, W, F, I, B, C4, UP rules
- MyPy: strict mode with type checking
- Pytest: cov, term-missing, strict markers

### Environment Configuration

**`.env.example`**:
- `WORKER_URL` - Cloudflare Worker endpoint
- `CRYPTOCOMPARE_API_KEY` - CryptoCompare (50 req/day)
- `NEWSAPI_KEY` - NewsAPI (100 req/day)
- `FRED_API_KEY` - Federal Reserve data
- `REDDIT_*` - Reddit sentiment API
- `GOOGLE_*` - Google Custom Search

### Cloudflare Workers Configuration

**`wrangler.toml`**:
```toml
name = "coinswarm-data-fetcher"
main = "data-fetcher.js"
compatibility_date = "2024-01-01"

[[kv_namespaces]]
binding = "DATA_CACHE"
id = "your_kv_namespace_id"
```

**`wrangler-multi-source.toml`**:
```toml
name = "coinswarm-multi-source"
main = "multi-source-data-fetcher.js"
compatibility_date = "2024-01-01"
```

### Database Schema

**`cloudflare-d1-schema.sql`** (3.1KB)
- D1 database schema for historical data storage
- Optional for Cloudflare D1 integration

---

## 6. DEPLOYMENT & CI/CD CONFIGURATIONS

### GitHub Actions Workflows

#### `.github/workflows/ci.yml` (312 lines)
**Evidence-Driven Development Pipeline** with 5 stages:

**Stage 0: Lint & Type Check**
- Ruff linter
- MyPy type checker
- Black code formatting
- Runs on ubuntu-latest

**Stage 1: Unit Tests**
- pytest with coverage
- Depends on: lint
- Coverage reports to Codecov

**Stage 2: Integration Tests**
- Redis 6379 (redis-stack)
- PostgreSQL 5432 (16-alpine)
- Depends on: unit-tests
- Environment variables for DB access

**Stage 3: Performance Tests**
- soundness/ and performance/ directories
- Depends on: integration-tests

**Stage 4: Soundness Tests (EDD)**
- Economic soundness validation
- Safety invariants validation
- Depends on: performance-tests

**Stage 5: Build & Package**
- Python package building
- Depends on: soundness-tests

**Summary Report**: Aggregates all results

#### `.github/workflows/nightly.yml` (228 lines)
**Scheduled Continuous Validation**:
- **Trigger**: Daily at 2 AM UTC (cron: '0 2 * * *')
- **Manual trigger**: workflow_dispatch

**Jobs**:
1. **Full Validation** - Complete test suite with latest data
2. **Soundness Regression** - Detects regressions
3. **Long-Running Tests** - Backtests and simulations (60-minute timeout)
4. **Failure Notifications** - Alert on issues
5. **Success Summary** - Status reporting

### Build & Deployment Scripts

**`Makefile`** (78 lines)
```makefile
Commands:
- make install          # Install production dependencies
- make dev-install      # Install dev dependencies
- make test             # Run tests with coverage
- make lint             # Run linters
- make format           # Format code (black + ruff)
- make clean            # Clean artifacts
- make docker-up        # Start services
- make docker-down      # Stop services
- make docker-logs      # View logs
- make run-mcp          # Run MCP server
- make run-agents       # Run agent system
```

**`deploy-gcp.sh`** (7.6KB)
- GCP Cloud Run deployment
- Docker image building
- Service configuration
- Environment setup

**`cloud-run.yaml`** (3.8KB)
- Google Cloud Run configuration
- Service definition
- Deployment settings

### Docker Composition

**`docker-compose.yml`** (184 lines)
**Services** (8 containers):

1. **redis** (redis/redis-stack:latest)
   - Port: 6379 (client), 8001 (RedisInsight)
   - Volume: redis-data
   - Features: Redis Search module

2. **nats** (nats:latest)
   - Ports: 4222 (clients), 8222 (monitoring), 6222 (cluster)
   - JetStream enabled
   - Volume: nats-data

3. **postgres** (postgres:16-alpine)
   - Port: 5432
   - User: coinswarm
   - Database: coinswarm
   - Init script: scripts/init-db.sql

4. **influxdb** (influxdb:2.7-alpine)
   - Port: 8086
   - Org: coinswarm
   - Bucket: market_data

5. **mongodb** (mongo:7-jammy)
   - Port: 27017
   - User: coinswarm
   - Database: coinswarm

6. **prometheus** (prom/prometheus:latest)
   - Port: 9090
   - Config: config/prometheus.yml

7. **grafana** (grafana/grafana:latest)
   - Port: 3001 (to 3000)
   - Datasources: Prometheus, InfluxDB

**Volumes**: 6 persistent volumes (redis, nats, postgres, influxdb, mongodb, prometheus, grafana)
**Network**: coinswarm-network (bridge driver)

---

## 7. TEST FILES & TESTING INFRASTRUCTURE

### Test Organization (22 Python test modules)

**Unit Tests** (6 files):
- `test_binance_ingestor.py` - Binance data fetcher
- `test_coinbase_client.py` - Coinbase API client
- `test_config.py` - Configuration loading
- `test_data_ingest_base.py` - Base ingestor class
- `test_mcp_server.py` - MCP server functionality

**Integration Tests** (3 files):
- `test_postgres.py` - PostgreSQL integration
- `test_redis.py` - Redis integration

**Soundness Tests** (4 files):
- `test_binance_soundness.py` - Binance data validation
- `test_coinbase_soundness.py` - Coinbase data validation
- `test_mcp_soundness.py` - MCP server validation
- `base.py` - Base soundness test utilities

**Test Fixtures** (4 market scenarios):
- `golden_cross.py` - Golden cross trend scenario
- `high_volatility.py` - Volatile market scenario
- `mean_reversion.py` - Mean reversion scenario
- `range_bound.py` - Range-bound scenario

### Testing Framework & Tools

**Frameworks**:
- pytest>=7.4.0
- pytest-asyncio>=0.21.0 (async test support)
- pytest-cov>=4.1.0 (coverage tracking)
- pytest-mock>=3.12.0 (mocking)

**Test Markers**:
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.performance` - Performance tests
- `@pytest.mark.soundness` - Economic soundness (EDD)
- `@pytest.mark.slow` - Slow/long-running tests

**CI Integration**:
- JUnit XML report generation
- Codecov coverage uploads
- Artifact uploads for review
- Parallel test execution
- Environment-based configuration

---

## 8. KEY ARCHITECTURAL PATTERNS & DECISIONS

### Multi-Agent Architecture
**12 Specialized Agents**:
1. TrendFollowingAgent - Trend analysis
2. RiskManagementAgent - Risk controls
3. ResearchAgent - Market research
4. ArbitrageAgent - Cross-exchange opportunities
5. CrossExchangeArbitrageAgent - Detailed arbitrage
6. HedgeAgent - Risk hedging
7. StrategyLearningAgent - Pattern learning
8. TradeAnalysisAgent - Trade analysis
9. AcademicResearchAgent - Academic research
10. AgentCommittee - Voting/consensus mechanism
11. BaseAgent - Abstract base class
12. Single-user bot coordinator

### Data Layer Architecture
**5-Source Data Fetching**:
1. Binance - Spot market data
2. CoinGecko - Historical crypto prices
3. CryptoCompare - Comprehensive historical data
4. Kraken - Exchange data
5. Coinbase - Exchange data + oracle data (Pyth, Switchboard)

**Data Freshness**:
- Real-time: WebSocket feeds
- Hourly: 1h candles from workers
- Daily: Market snapshots
- Historical: 2+ years via paginated workers

### Storage Architecture
- **Time-Series**: InfluxDB (market data, OHLCV)
- **Documents**: MongoDB (news, sentiment, research)
- **Relational**: PostgreSQL (trades, patterns, metadata, audit logs)
- **Vector DB**: Redis (memory, episodic/semantic storage)
- **Cache**: Cloudflare KV (edge caching)

### Deployment Models
1. **Serverless**: Cloudflare Workers (free tier)
2. **Container**: Docker with docker-compose
3. **Cloud**: GCP Cloud Run (single-user optimization)
4. **Local**: Development setup with full stack

### Code Quality Standards
- **Linting**: Ruff (strict rules: E, W, F, I, B, C4, UP)
- **Type Checking**: MyPy (strict mode)
- **Formatting**: Black (100-char lines)
- **Testing**: Pytest with soundness/EDD validation
- **Coverage**: Term-missing reporting

---

## 9. NOTABLE IMPLEMENTATION DETAILS

### Cloudflare Worker Optimization
- Free tier: 100K requests/day
- Edge locations: Global distribution
- Latency: 50-200ms globally
- KV caching: 1-hour TTL
- Pagination support: 2+ years of data
- CORS enabled: Cross-origin requests

### Single-User Bot Optimization (601 lines)
- Monolithic architecture (0ms internal latency)
- In-memory caching (no external Redis)
- WebSocket streaming (1ms vs 5ms REST)
- Co-located with Coinbase API (2-5ms)
- Parallel processing
- Total execution: 5-15ms

### MCP Server Integration
- Exposes Coinbase API via Model Context Protocol
- Resources: accounts, products, orders, fills
- Tools: trading, order management, queries
- Structured logging with structlog
- Type-safe with Python typing

### Memory System
- Hierarchical memory (exploration, learning, persistence)
- Quorum-based memory mutations (Byzantine fault-tolerant)
- Pattern learning and optimization
- State building for agent decision-making

### Backtesting Infrastructure
- Continuous backtester for validation
- Multi-timescale validator (1m, 5m, 1h, 4h, 1d)
- Random window validator (stress testing)
- Economic soundness checks (EDD)

---

## 10. PROJECT METRICS

### Codebase Size
- **Source Code**: 49 Python modules in src/coinswarm/
- **Test Suite**: 22 Python test modules
- **Main Bot**: 601 lines (single_user_bot.py)
- **MCP Server**: 21.9 KB (server.py)
- **Workers**: 3 JavaScript files (data fetchers)

### Configuration
- **Dependencies**: 23 core + 7 dev + 3 test + 2 docs
- **Services**: 8 Docker containers
- **Databases**: 4 types (PostgreSQL, MongoDB, InfluxDB, Redis)

### API Coverage
- **Coinbase**: Full Advanced Trade API integration
- **Binance**: Spot market data
- **External**: CoinGecko, CryptoCompare, Kraken
- **Sentiment**: NewsAPI, Twitter, Reddit, Google Search

### CI/CD Pipeline
- **Stages**: 6 (lint, unit, integration, performance, soundness, build)
- **Services**: 2 (Redis, PostgreSQL)
- **Schedules**: Push/PR + Nightly (2 AM UTC)
- **Artifacts**: Test reports, coverage, build packages

---

## 11. DEVELOPMENT WORKFLOW

### Quick Start
```bash
make dev-install           # Install dependencies
make init                  # Initialize environment
make test                  # Run tests
make lint                  # Check code quality
make format                # Format code
make docker-up             # Start services
```

### Running Components
```bash
make run-mcp               # Run MCP server
make run-agents            # Run agent system
python -m pytest tests/    # Run specific tests
```

### Deployment
```bash
# GCP Cloud Run
./deploy-gcp.sh

# Cloudflare Workers
cd cloudflare-workers
wrangler publish           # Basic worker
wrangler publish --config wrangler-multi-source.toml  # Multi-source
```

---

## 12. SECURITY & COMPLIANCE CONSIDERATIONS

### API Key Management
- Environment variables via `.env`
- Config management with pydantic-settings
- Example template: `.env.example`

### Rate Limiting
- Tenacity retry logic (exponential backoff)
- Automatic rate limit handling
- API-specific quotas respected

### Testing & Validation
- Unit tests for component isolation
- Integration tests for service interaction
- Economic soundness tests (EDD)
- Performance tests for latency

### Audit & Transparency
- Structured logging (structlog)
- Complete decision tracking
- Deterministic replay capability
- Performance attribution per strategy

---

## SUMMARY TABLE

| Aspect | Details |
|--------|---------|
| **Language** | Python 3.11+ |
| **Type** | AI-Powered Multi-Agent Trading System |
| **Key Components** | 12 Agents, 49 modules, 8 services |
| **APIs** | Coinbase (MCP), Binance, CoinGecko, CryptoCompare |
| **Storage** | PostgreSQL, MongoDB, InfluxDB, Redis, Cloudflare KV |
| **Testing** | Pytest + Soundness/EDD validation |
| **CI/CD** | GitHub Actions (lint → unit → integration → soundness) |
| **Deployment** | Docker, Cloudflare Workers, GCP Cloud Run |
| **Documentation** | 30+ markdown files, 11k-18k word architecture docs |
| **Status** | Phase 0 - Early Implementation |
| **Version** | 0.1.0 |

