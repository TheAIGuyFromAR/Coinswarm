# Atomic Action Plan - Coinswarm Gap Remediation

**Based on:** gap-analysis.md
**Strategy:** Small, focused commits that can be completed in 15-30 minutes each
**Total Actions:** 100+ atomic steps

---

## Priority 1: Test Coverage for Existing Code (Days 1-2)

**Goal:** Get to 80%+ coverage on what we've already built

### Sprint 1A: MCP Server Tests (6 commits)

| # | Action | File | Lines | Time |
|---|--------|------|-------|------|
| 1 | Test MCP resource listing | `tests/unit/test_mcp_server.py` | 30 | 15min |
| 2 | Test MCP resource reading | `tests/unit/test_mcp_server.py` | 40 | 20min |
| 3 | Test MCP tool listing | `tests/unit/test_mcp_server.py` | 30 | 15min |
| 4 | Test MCP tool execution | `tests/unit/test_mcp_server.py` | 50 | 25min |
| 5 | Test MCP order validation | `tests/unit/test_mcp_server.py` | 40 | 20min |
| 6 | Test MCP error handling | `tests/unit/test_mcp_server.py` | 30 | 15min |

### Sprint 1B: Data Ingest Base Tests (4 commits)

| # | Action | File | Lines | Time |
|---|--------|------|-------|------|
| 7 | Test DataPoint creation | `tests/unit/test_data_ingest_base.py` | 25 | 15min |
| 8 | Test DataSource abstract methods | `tests/unit/test_data_ingest_base.py` | 30 | 15min |
| 9 | Test source metadata | `tests/unit/test_data_ingest_base.py` | 20 | 10min |
| 10 | Test health checks | `tests/unit/test_data_ingest_base.py` | 25 | 15min |

### Sprint 1C: Binance Ingestor Tests (8 commits)

| # | Action | File | Lines | Time |
|---|--------|------|-------|------|
| 11 | Test Binance initialization | `tests/unit/test_binance_ingestor.py` | 20 | 10min |
| 12 | Test OHLCV fetching | `tests/unit/test_binance_ingestor.py` | 40 | 20min |
| 13 | Test WebSocket parsing | `tests/unit/test_binance_ingestor.py` | 50 | 25min |
| 14 | Test symbol normalization | `tests/unit/test_binance_ingestor.py` | 30 | 15min |
| 15 | Test error handling | `tests/unit/test_binance_ingestor.py` | 35 | 20min |
| 16 | Test rate limiting | `tests/unit/test_binance_ingestor.py` | 30 | 15min |
| 17 | Test health check | `tests/unit/test_binance_ingestor.py` | 20 | 10min |
| 18 | Test metadata generation | `tests/unit/test_binance_ingestor.py` | 25 | 15min |

### Sprint 1D: Soundness Tests (6 commits)

| # | Action | File | Lines | Time |
|---|--------|------|-------|------|
| 19 | Config determinism test | `tests/soundness/test_config_soundness.py` | 40 | 20min |
| 20 | Config validation test | `tests/soundness/test_config_soundness.py` | 35 | 15min |
| 21 | MCP determinism test | `tests/soundness/test_mcp_soundness.py` | 45 | 20min |
| 22 | MCP latency test | `tests/soundness/test_mcp_soundness.py` | 40 | 20min |
| 23 | Binance determinism test | `tests/soundness/test_binance_soundness.py` | 40 | 20min |
| 24 | Binance latency test | `tests/soundness/test_binance_soundness.py` | 40 | 20min |

**Total Sprint 1:** 24 commits, ~650 lines, ~7 hours

---

## Priority 2: Integration Tests (Days 3-4)

**Goal:** Validate multi-component interactions work

### Sprint 2A: Database Integration (6 commits)

| # | Action | File | Lines | Time |
|---|--------|------|-------|------|
| 25 | Redis connection test | `tests/integration/test_redis.py` | 30 | 15min |
| 26 | Redis key operations | `tests/integration/test_redis.py` | 40 | 20min |
| 27 | Redis vector search prep | `tests/integration/test_redis.py` | 35 | 20min |
| 28 | PostgreSQL connection test | `tests/integration/test_postgres.py` | 30 | 15min |
| 29 | PostgreSQL CRUD operations | `tests/integration/test_postgres.py` | 50 | 25min |
| 30 | PostgreSQL transaction test | `tests/integration/test_postgres.py` | 40 | 20min |

### Sprint 2B: MCP Integration (5 commits)

| # | Action | File | Lines | Time |
|---|--------|------|-------|------|
| 31 | MCP server startup test | `tests/integration/test_mcp_e2e.py` | 35 | 20min |
| 32 | MCP resource flow test | `tests/integration/test_mcp_e2e.py` | 45 | 25min |
| 33 | MCP tool execution test | `tests/integration/test_mcp_e2e.py` | 50 | 25min |
| 34 | MCP error propagation test | `tests/integration/test_mcp_e2e.py` | 40 | 20min |
| 35 | MCP concurrent requests test | `tests/integration/test_mcp_e2e.py` | 45 | 25min |

### Sprint 2C: API Integration (4 commits)

| # | Action | File | Lines | Time |
|---|--------|------|-------|------|
| 36 | Coinbase connection test (sandbox) | `tests/integration/test_coinbase_live.py` | 30 | 15min |
| 37 | Coinbase account fetch test | `tests/integration/test_coinbase_live.py` | 35 | 20min |
| 38 | Coinbase market data test | `tests/integration/test_coinbase_live.py` | 40 | 20min |
| 39 | Coinbase rate limiting test | `tests/integration/test_coinbase_live.py` | 35 | 20min |

**Total Sprint 2:** 15 commits, ~590 lines, ~6 hours

---

## Priority 3: Critical Documentation (Days 5-6)

**Goal:** Fill strategic planning gaps

### Sprint 3A: Build Roadmap (3 commits)

| # | Action | File | Lines | Time |
|---|--------|------|-------|------|
| 40 | Phase 0-2 roadmap | `docs/development/build-roadmap.md` | 400 | 30min |
| 41 | Phase 3-5 roadmap | `docs/development/build-roadmap.md` | 400 | 30min |
| 42 | Phase 6-8 roadmap | `docs/development/build-roadmap.md` | 200 | 20min |

### Sprint 3B: Security Plan (4 commits)

| # | Action | File | Lines | Time |
|---|--------|------|-------|------|
| 43 | API key management | `docs/security/security-compliance.md` | 250 | 25min |
| 44 | Authentication & authorization | `docs/security/security-compliance.md` | 200 | 20min |
| 45 | Data encryption | `docs/security/security-compliance.md` | 150 | 15min |
| 46 | Compliance requirements | `docs/security/security-compliance.md` | 200 | 20min |

### Sprint 3C: Monitoring Strategy (3 commits)

| # | Action | File | Lines | Time |
|---|--------|------|-------|------|
| 47 | Metrics to collect | `docs/operations/monitoring-alerting.md` | 250 | 25min |
| 48 | Alert definitions | `docs/operations/monitoring-alerting.md` | 200 | 20min |
| 49 | Dashboard designs | `docs/operations/monitoring-alerting.md` | 150 | 15min |

### Sprint 3D: Test Strategy Docs (4 commits)

| # | Action | File | Lines | Time |
|---|--------|------|-------|------|
| 50 | Coverage requirements | `docs/testing/coverage-requirements.md` | 200 | 20min |
| 51 | Test type decision tree | `docs/testing/test-type-guide.md` | 300 | 30min |
| 52 | Mock vs real policy | `docs/testing/test-type-guide.md` | 200 | 20min |
| 53 | Test data strategy | `docs/testing/test-data-strategy.md` | 250 | 25min |

**Total Sprint 3:** 14 commits, ~3,150 lines, ~5 hours

---

## Priority 4: Performance & Contract Tests (Days 7-8)

**Goal:** Add missing test types

### Sprint 4A: Performance Tests (6 commits)

| # | Action | File | Lines | Time |
|---|--------|------|-------|------|
| 54 | MCP latency benchmark | `tests/performance/test_mcp_latency.py` | 50 | 25min |
| 55 | Data ingest throughput | `tests/performance/test_ingest_throughput.py` | 60 | 30min |
| 56 | Config loading performance | `tests/performance/test_config_perf.py` | 40 | 20min |
| 57 | Signature generation bench | `tests/performance/test_crypto_perf.py` | 45 | 20min |
| 58 | Redis operations bench | `tests/performance/test_redis_perf.py` | 50 | 25min |
| 59 | PostgreSQL query bench | `tests/performance/test_postgres_perf.py` | 55 | 30min |

### Sprint 4B: Contract Tests (4 commits)

| # | Action | File | Lines | Time |
|---|--------|------|-------|------|
| 60 | MCP schema contracts | `tests/contract/test_mcp_schemas.py` | 70 | 35min |
| 61 | DataPoint schema contract | `tests/contract/test_data_schemas.py` | 50 | 25min |
| 62 | Config schema contract | `tests/contract/test_config_schemas.py` | 45 | 20min |
| 63 | API response contracts | `tests/contract/test_api_schemas.py` | 55 | 25min |

**Total Sprint 4:** 10 commits, ~520 lines, ~4 hours

---

## Priority 5: Redis Vector Index (Days 9-10)

**Goal:** Implement core memory infrastructure

### Sprint 5A: Vector Index Setup (6 commits)

| # | Action | File | Lines | Time |
|---|--------|------|-------|------|
| 64 | Redis client wrapper | `src/coinswarm/memory/redis_client.py` | 100 | 30min |
| 65 | Vector index creation | `src/coinswarm/memory/vector_index.py` | 120 | 30min |
| 66 | Embedding storage | `src/coinswarm/memory/vector_index.py` | 80 | 25min |
| 67 | kNN search implementation | `src/coinswarm/memory/vector_index.py` | 100 | 30min |
| 68 | Index management (create/delete) | `src/coinswarm/memory/vector_index.py` | 70 | 25min |
| 69 | Health checks & metrics | `src/coinswarm/memory/vector_index.py` | 60 | 20min |

### Sprint 5B: Vector Index Tests (5 commits)

| # | Action | File | Lines | Time |
|---|--------|------|-------|------|
| 70 | Unit: Index creation | `tests/unit/memory/test_vector_index.py` | 40 | 20min |
| 71 | Unit: Embedding CRUD | `tests/unit/memory/test_vector_index.py` | 50 | 25min |
| 72 | Unit: kNN search | `tests/unit/memory/test_vector_index.py` | 45 | 20min |
| 73 | Integration: Redis ops | `tests/integration/test_vector_index.py` | 60 | 30min |
| 74 | Performance: Search latency | `tests/performance/test_vector_search.py` | 50 | 25min |

**Total Sprint 5:** 11 commits, ~775 lines, ~5 hours

---

## Priority 6: PostgreSQL Models (Days 11-12)

**Goal:** Implement data persistence layer

### Sprint 6A: SQLAlchemy Models (7 commits)

| # | Action | File | Lines | Time |
|---|--------|------|-------|------|
| 75 | Database setup & engine | `src/coinswarm/memory/database.py` | 80 | 25min |
| 76 | Trade model | `src/coinswarm/memory/models.py` | 60 | 20min |
| 77 | Pattern model | `src/coinswarm/memory/models.py` | 70 | 25min |
| 78 | Regime model | `src/coinswarm/memory/models.py` | 50 | 20min |
| 79 | Episode model | `src/coinswarm/memory/models.py` | 60 | 20min |
| 80 | Agent state model | `src/coinswarm/memory/models.py` | 55 | 20min |
| 81 | Quorum vote model | `src/coinswarm/memory/models.py` | 50 | 20min |

### Sprint 6B: Model Tests (6 commits)

| # | Action | File | Lines | Time |
|---|--------|------|-------|------|
| 82 | Unit: Trade model | `tests/unit/memory/test_models.py` | 40 | 20min |
| 83 | Unit: Pattern model | `tests/unit/memory/test_models.py` | 45 | 20min |
| 84 | Unit: Regime model | `tests/unit/memory/test_models.py` | 35 | 15min |
| 85 | Integration: DB CRUD | `tests/integration/test_database.py` | 60 | 30min |
| 86 | Integration: Transactions | `tests/integration/test_database.py` | 50 | 25min |
| 87 | Integration: Queries | `tests/integration/test_database.py` | 55 | 25min |

**Total Sprint 6:** 13 commits, ~710 lines, ~4.5 hours

---

## Priority 7: NATS Client (Days 13-14)

**Goal:** Implement message bus

### Sprint 7A: NATS Implementation (5 commits)

| # | Action | File | Lines | Time |
|---|--------|------|-------|------|
| 88 | NATS connection manager | `src/coinswarm/core/nats_client.py` | 80 | 25min |
| 89 | Publish operations | `src/coinswarm/core/nats_client.py` | 60 | 20min |
| 90 | Subscribe operations | `src/coinswarm/core/nats_client.py` | 70 | 25min |
| 91 | Request/reply pattern | `src/coinswarm/core/nats_client.py` | 65 | 25min |
| 92 | Error handling & retry | `src/coinswarm/core/nats_client.py` | 55 | 20min |

### Sprint 7B: NATS Tests (5 commits)

| # | Action | File | Lines | Time |
|---|--------|------|-------|------|
| 93 | Unit: Connection mgmt | `tests/unit/test_nats_client.py` | 40 | 20min |
| 94 | Unit: Pub/sub logic | `tests/unit/test_nats_client.py` | 50 | 25min |
| 95 | Integration: NATS server | `tests/integration/test_nats.py` | 60 | 30min |
| 96 | Integration: Message flow | `tests/integration/test_nats.py` | 55 | 25min |
| 97 | Performance: Throughput | `tests/performance/test_nats_perf.py` | 50 | 25min |

**Total Sprint 7:** 10 commits, ~585 lines, ~4 hours

---

## Priority 8: First Agent - Trend Following (Days 15-17)

**Goal:** Implement complete agent with full EDD validation

### Sprint 8A: Trend Agent Core (4 commits)

| # | Action | File | Lines | Time |
|---|--------|------|-------|------|
| 98 | Agent base class | `src/coinswarm/agents/base.py` | 120 | 30min |
| 99 | Trend indicator calculation | `src/coinswarm/agents/trend.py` | 90 | 30min |
| 100 | Trend signal generation | `src/coinswarm/agents/trend.py` | 80 | 25min |
| 101 | Trend position sizing | `src/coinswarm/agents/trend.py` | 70 | 25min |

### Sprint 8B: Trend Agent Tests (8 commits)

| # | Action | File | Lines | Time |
|---|--------|------|-------|------|
| 102 | Unit: Indicator calc | `tests/unit/agents/test_trend.py` | 40 | 20min |
| 103 | Unit: Signal generation | `tests/unit/agents/test_trend.py` | 50 | 25min |
| 104 | Unit: Position sizing | `tests/unit/agents/test_trend.py` | 45 | 20min |
| 105 | Soundness: Determinism | `tests/soundness/test_trend_soundness.py` | 50 | 25min |
| 106 | Soundness: Safety invariants | `tests/soundness/test_trend_soundness.py` | 60 | 30min |
| 107 | Soundness: Statistical sanity | `tests/soundness/test_trend_soundness.py` | 70 | 35min |
| 108 | Performance: Decision latency | `tests/performance/test_trend_perf.py` | 45 | 20min |
| 109 | Backtest: Golden cross | `tests/backtest/test_trend_backtest.py` | 80 | 40min |

**Total Sprint 8:** 12 commits, ~800 lines, ~5 hours

---

## Summary by Priority

| Priority | Sprints | Commits | Lines | Hours |
|----------|---------|---------|-------|-------|
| **P1: Test Coverage** | 4 | 24 | ~650 | 7 |
| **P2: Integration Tests** | 3 | 15 | ~590 | 6 |
| **P3: Documentation** | 4 | 14 | ~3,150 | 5 |
| **P4: Performance/Contract** | 2 | 10 | ~520 | 4 |
| **P5: Vector Index** | 2 | 11 | ~775 | 5 |
| **P6: PostgreSQL** | 2 | 13 | ~710 | 4.5 |
| **P7: NATS** | 2 | 10 | ~585 | 4 |
| **P8: First Agent** | 2 | 12 | ~800 | 5 |
| **TOTAL** | **21** | **109** | **~7,780** | **40.5** |

---

## Execution Strategy

### Daily Rhythm
- **Morning:** 4-5 atomic commits (implementation or tests)
- **Afternoon:** 4-5 atomic commits (documentation or validation)
- **Evening:** Review, push, verify CI/CD

### Weekly Goals
- **Week 1:** Priorities 1-2 (Test coverage, Integration)
- **Week 2:** Priorities 3-5 (Docs, Performance, Vector Index)
- **Week 3:** Priorities 6-8 (PostgreSQL, NATS, First Agent)

### Quality Gates
- ✅ Each commit passes all existing tests
- ✅ Each commit adds tests for new code
- ✅ Each commit is self-contained and reversible
- ✅ Each commit has clear, descriptive message
- ✅ CI/CD stays green throughout

---

## Next 10 Actions (Start Immediately)

1. Test MCP resource listing
2. Test MCP resource reading
3. Test MCP tool listing
4. Test MCP tool execution
5. Test MCP order validation
6. Test MCP error handling
7. Test DataPoint creation
8. Test DataSource abstract methods
9. Test source metadata
10. Test health checks

**Estimated Time for Next 10:** ~2.5 hours
**All can be done today!**
