# Coinswarm Repository Structure

═══════════════════════════════════════════════════════════════════

## Project Overview

Two separate projects coexisting in one repository:
- **PYSWARM** → Python trading system (131 files)
- **COINSWARM** → JavaScript/TypeScript Cloudflare Workers (41 files)

═══════════════════════════════════════════════════════════════════

## PYSWARM/ - Python Trading System (131 files)

### Main Package
```
├── agents/           15 trading agents
├── api/              API clients
├── backtesting/      Backtesting engines
├── core/             Core configuration
├── data_ingest/      Data ingestion (exchanges, macro, news)
├── memory/           Memory & learning systems
├── patterns/         Pattern detection
├── mcp_server/       MCP server
└── utils/            Utilities
```

### Organized Scripts
```
├── demos/            9 demonstration scripts
├── scripts/          5 utility scripts
├── data_collection/  9 data fetching scripts
└── strategy_tools/   7 strategy analysis tools
```

### Testing
```
└── tests/            38 test files (unit, integration, soundness)
```

---

## COINSWARM - JavaScript/TypeScript Cloudflare Workers

### cloudflare-agents/ (33 TypeScript files)
- Trading agents, sentiment analysis
- Data collection & evolution agents
- 11 SQL schemas
- 15 Wrangler configurations

### cloudflare-workers/ (8 JavaScript files)
- Data fetching & backfill workers
- Multi-source data collection

---

## ROOT LEVEL - Shared Resources

### Documentation
```
├── README.md, QUICK_START.md
├── DEPLOYMENT_SCALED_$5_PLAN.md
├── DEPLOY_WORKER_INSTRUCTIONS.md
└── docs/             Comprehensive documentation
```

### Configuration
```
├── pyproject.toml    Python project config
├── docker-compose.yml
├── Dockerfile.evolution
├── wrangler.toml
└── config/           Prometheus monitoring
```

### Deployment Scripts
25+ shell scripts for deployment:
- `deploy-*.sh` - GCP, Cloudflare, agents
- `test-*.sh` - Worker testing
- `monitor-*.sh` - Monitoring

### Data & Schemas
```
├── cloudflare-d1-*.sql       Cloudflare schemas
├── historical-trades-50k.sql Large dataset
└── scripts/                  Database scripts
```

---

## Repository Statistics

| Type | Count | Location |
|------|-------|----------|
| Python Files | 131 | pyswarm/ |
| TypeScript Files | 33 | cloudflare-agents/ |
| JavaScript Files | 12 | cloudflare-workers/ + root |
| Shell Scripts | 25+ | deployment & testing scripts |
| SQL Files | 15+ | schemas and migrations |
| Documentation | 10+ | major docs + docs/ directory |

---

## Clean Separation Achieved ✓

- ✅ All Python code → `pyswarm/`
- ✅ All TypeScript → `cloudflare-agents/`
- ✅ All JavaScript → `cloudflare-workers/` + root scripts
- ✅ `src/coinswarm/` removed (was duplicate Python)

---

## Detailed Structure

### pyswarm/ Full Layout
```
pyswarm/
├── __init__.py
├── single_user_bot.py
├── py.typed
│
├── Cloudflare_Services/
│   └── cloudflare_d1_service.py
│
├── Data_Import/
│   ├── create_local_sqlite.py
│   ├── fetch_and_fill_local.py
│   └── historical_worker.py
│
├── config/
│   ├── pyproject.toml
│   ├── wrangler_historical_import.toml
│   └── wrangler_local.toml
│
├── agents/                      [15 files]
│   ├── __init__.py
│   ├── base_agent.py
│   ├── academic_research_agent.py
│   ├── arbitrage_agent.py
│   ├── chaos_buy_agent.py
│   ├── committee.py
│   ├── enhanced_arbitrage_agent.py
│   ├── hedge_agent.py
│   ├── opportunistic_sell_agent.py
│   ├── research_agent.py
│   ├── risk_agent.py
│   ├── strategy_learning_agent.py
│   ├── trade_analysis_agent.py
│   └── trend_agent.py
│
├── api/                         [2 files]
│   ├── __init__.py
│   └── coinbase_client.py
│
├── backtesting/                 [5 files]
│   ├── __init__.py
│   ├── backtest_engine.py
│   ├── continuous_backtester.py
│   ├── multi_timescale_validator.py
│   └── random_window_validator.py
│
├── core/                        [2 files]
│   ├── __init__.py
│   └── config.py
│
├── data_collection/             [9 files]
│   ├── bulk_download_historical.py
│   ├── fetch-real-historical-data.py
│   ├── fetch_binance_historical.py
│   ├── fetch_historical_data.py
│   ├── fetch_massive_history.py
│   ├── fetch_multi_pair_data.py
│   ├── fetch_multi_source_data.py
│   ├── fetch_multi_source_historical.py
│   └── simple_data_fetch.py
│
├── data_ingest/                 [13 files + subdirs]
│   ├── __init__.py
│   ├── base.py
│   ├── binance_ingestor.py
│   ├── coinswarm_worker_client.py
│   ├── csv_importer.py
│   ├── google_sentiment_fetcher.py
│   ├── historical_data_fetcher.py
│   ├── macro_trends_fetcher.py
│   ├── news_sentiment_fetcher.py
│   ├── worker_client.py
│   ├── exchanges/
│   │   ├── __init__.py
│   │   └── binance.py
│   ├── macro/
│   │   └── __init__.py
│   ├── news/
│   │   └── __init__.py
│   ├── onchain/
│   │   └── __init__.py
│   ├── processors/
│   │   └── __init__.py
│   └── registry/
│       └── __init__.py
│
├── demos/                       [9 files]
│   ├── backtest_superchill.py
│   ├── chaos_trading_simulator.py
│   ├── demo_backtest_now.py
│   ├── demo_full_backtest.py
│   ├── demo_quick.py
│   ├── demo_quick_mock.py
│   ├── demo_real_data.py
│   ├── demo_real_data_backtest.py
│   └── demo_with_sentiment.py
│
├── mcp_server/                  [2 files]
│   ├── __init__.py
│   └── server.py
│
├── memory/                      [7 files]
│   ├── __init__.py
│   ├── exploration_strategy.py
│   ├── hierarchical_memory.py
│   ├── learning_loop.py
│   ├── memory_persistence.py
│   ├── simple_memory.py
│   └── state_builder.py
│
├── patterns/                    [5 files]
│   ├── __init__.py
│   ├── arbitrage_detector.py
│   ├── cointegration_tester.py
│   ├── correlation_detector.py
│   └── lead_lag_analyzer.py
│
├── scripts/                     [5 files]
│   ├── continuous_evolution.py
│   ├── create_evolution_worker.py
│   ├── list_all_workers.py
│   ├── load.py
│   └── save.py
│
├── strategy_tools/              [7 files]
│   ├── analyze_trades.py
│   ├── discover_10x_strategies.py
│   ├── explain_strategy.py
│   ├── explore_real_trades.py
│   ├── find_10x_btc_strategies.py
│   ├── find_10x_nominal_strategies.py
│   └── strategy_testing_agent.py
│
├── tests/                       [38 files]
│   ├── __init__.py
│   ├── test_api_key.py
│   ├── test_integrated_multi_pair.py
│   ├── test_memory_on_real_data.py
│   ├── test_real_data_trades.py
│   ├── test_relaxed_risk_multiwindow.py
│   ├── test_with_historical_trades.py
│   ├── test_worker.py
│   ├── validate_strategy_random.py
│   ├── backtest/
│   │   └── __init__.py
│   ├── fixtures/
│   │   ├── __init__.py
│   │   ├── README.md
│   │   └── market_data/
│   │       ├── golden_cross.py
│   │       ├── high_volatility.py
│   │       ├── mean_reversion.py
│   │       └── range_bound.py
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_postgres.py
│   │   └── test_redis.py
│   ├── performance/
│   │   └── __init__.py
│   ├── soundness/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── test_binance_soundness.py
│   │   ├── test_coinbase_soundness.py
│   │   └── test_mcp_soundness.py
│   └── unit/
│       ├── __init__.py
│       ├── test_agent_committee.py
│       ├── test_arbitrage_agent.py
│       ├── test_binance_ingestor.py
│       ├── test_circuit_breaker.py
│       ├── test_coinbase_client.py
│       ├── test_config.py
│       ├── test_data_ingest_base.py
│       ├── test_hierarchical_memory.py
│       ├── test_master_orchestrator.py
│       ├── test_mcp_server.py
│       ├── test_mean_reversion_agent.py
│       ├── test_oversight_manager.py
│       ├── test_paper_trading_system.py
│       ├── test_risk_agent.py
│       └── test_trend_agent.py
│
└── utils/
    └── __init__.py
```

### cloudflare-agents/ Full Layout
```
cloudflare-agents/
├── DOCUMENTATION
│   ├── CHAOS_TRADING_ARCHITECTURE.md
│   ├── DEPLOYMENT_MONITORING_GUIDE.md
│   └── WORKERS_DEPLOYMENT.md
│
├── TYPESCRIPT AGENTS [33 files]
│   ├── academic-papers-agent.ts
│   ├── agent-competition.ts
│   ├── ai-pattern-analyzer.ts
│   ├── collection-alerts-agent.ts
│   ├── cross-agent-learning.ts
│   ├── dashboards-worker.ts
│   ├── data-collection-monitor.ts
│   ├── evolution-agent.ts
│   ├── evolution-agent-scaled.ts
│   ├── evolution-agent-simple.ts
│   ├── grand-competition-agent.ts
│   ├── head-to-head-testing.ts
│   ├── historical-data-collection-cron.ts
│   ├── historical-data-worker.ts
│   ├── init-collection-db.ts
│   ├── model-research-agent.ts
│   ├── multi-exchange-data-worker.ts
│   ├── news-sentiment-agent.ts
│   ├── pattern-detector.ts
│   ├── realtime-price-collection-cron.ts
│   ├── reasoning-agent.ts
│   ├── sentiment-backfill-worker.ts
│   ├── sentiment-enhanced-routes.ts
│   ├── sentiment-timeseries-calculator.ts
│   ├── solana-dex-worker.ts
│   ├── structured-logger.ts
│   ├── technical-indicators.ts
│   ├── technical-indicators-agent.ts
│   ├── technical-patterns-agent.ts
│   ├── trading-worker.ts
│   └── worker-configuration.d.ts
│
├── SQL SCHEMAS & MIGRATIONS [11 files]
│   ├── add-missing-indexes.sql
│   ├── cross-agent-learning-schema.sql
│   ├── d1-schema-technical-indicators.sql
│   ├── grand-competition-schema.sql
│   ├── pattern-recency-weighting.sql
│   ├── price-data-schema.sql
│   ├── reasoning-agent-schema.sql
│   ├── sentiment-advanced-schema.sql
│   ├── sentiment-advanced-schema-safe.sql
│   ├── sentiment-data-schema.sql
│   └── sentiment-data-schema-safe.sql
│
├── WRANGLER CONFIGURATIONS [15 files]
│   ├── wrangler.toml
│   ├── wrangler-collection-alerts.toml
│   ├── wrangler-dashboards.toml
│   ├── wrangler-grand-competition.toml
│   ├── wrangler-historical.toml
│   ├── wrangler-historical-collection-cron.toml
│   ├── wrangler-monitor.toml
│   ├── wrangler-multi-exchange.toml
│   ├── wrangler-news-sentiment.toml
│   ├── wrangler-realtime-price-cron.toml
│   ├── wrangler-scaled.toml
│   ├── wrangler-sentiment-backfill.toml
│   ├── wrangler-solana-dex.toml
│   ├── wrangler-technical-indicators.toml
│   └── wrangler-trading.toml
│
├── CONFIGURATION
│   ├── .gitignore
│   ├── package.json
│   ├── package-lock.json
│   └── tsconfig.json
│
├── dashboards/
├── migrations/
└── public/
```

### cloudflare-workers/ Full Layout
```
cloudflare-workers/
├── README.md
│
├── JAVASCRIPT WORKERS [8 files]
│   ├── comprehensive-data-worker.js
│   ├── data-backfill-worker.js
│   ├── data-fetcher.js
│   ├── data-fetcher-paginated.js
│   ├── evolution-worker.js
│   ├── minute-data-worker.js
│   ├── multi-source-data-fetcher.js
│   └── simple-coingecko-worker.js
│
└── WRANGLER CONFIGURATIONS
    ├── wrangler.toml
    └── wrangler-multi-source.toml
```

### Other Directories

#### docs/ (Documentation)
```
├── README.md
├── agents/              # Agent documentation
├── api/                 # API documentation
├── architecture/        # Architecture docs
├── backtesting/         # Backtesting docs
├── deployment/          # Deployment guides
├── development/         # Development guides
├── infrastructure/      # Infrastructure docs
├── patterns/            # Pattern detection docs
├── setup/               # Setup instructions
├── status-reports/      # Status reports
└── testing/             # Testing documentation
```

#### config/ (Configuration)
```
└── prometheus.yml       # Prometheus monitoring config
```

#### scripts/ (Database & Infrastructure Scripts)
```
├── add-historical-prices-table.sql
├── init-db.sql
├── safe-migrate.sh
└── upload-binance-data.sh
```

#### tests/ (Root Test Directory - Non-Python Tests)
```
├── __init__.py
├── backtest/            # Backtest test files
├── fixtures/            # Test fixtures
├── integration/         # Integration tests
├── performance/         # Performance tests
├── soundness/           # Soundness tests
└── unit/                # Unit tests

Note: Python tests are in pyswarm/tests/
```
