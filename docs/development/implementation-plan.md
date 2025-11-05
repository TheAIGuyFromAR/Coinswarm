# Coinswarm Implementation Plan

**Status:** Production Specification
**Version:** 1.0
**Created:** 2025-11-05
**Timeline:** 12 weeks (Phases 0-5)

---

## Executive Summary

### Current State

**Documentation**: ✅ **Complete and Production-Ready**
- 13 comprehensive architecture documents (~70,000 words)
- Quorum-governed memory system specification (18,000 words)
- Hierarchical temporal decision system (11,000 words)
- Evidence-Driven Development testing strategy (8,000 words)
- Complete data feeds architecture
- Multi-agent system design
- Pattern learning system specification

**Implementation**: ⚠️ **Foundation Started (15% Complete)**
- Python project structure initialized
- Configuration system (config.py) ✅
- Coinbase API client (coinbase_client.py) ✅
- MCP server skeleton (mcp_server/server.py) ✅
- Binance ingestor (data_ingest/exchanges/binance.py) ✅
- Base data ingest classes ✅
- Initial unit tests (config, Coinbase client) ✅
- Docker compose infrastructure ✅
- GitHub Actions CI/CD pipeline ✅

**Testing**: ⚠️ **Partial Coverage**
- EDD framework defined and documented
- Soundness test base classes implemented
- Missing: 80+ unit tests, all integration tests, performance tests
- Current coverage: ~40% (target: 90%+)

**Gap Analysis**: ✅ **Comprehensive**
- 109 atomic actions identified in action plan
- ~7,780 lines of code to implement
- Estimated 40.5 hours of focused development
- Clear priority ordering (P1-P8)

### Implementation Goals

This 12-week plan transforms the comprehensive architecture into a **production-ready, live-trading system** through six distinct phases:

1. **Phase 0 (Weeks 1-2)**: Complete test coverage, fill documentation gaps, validate foundation
2. **Phase 1 (Weeks 3-4)**: Implement core memory system (Redis, PostgreSQL, NATS, quorum voting)
3. **Phase 2 (Weeks 5-6)**: Build and validate first trading agent (Trend Agent with full EDD)
4. **Phase 3 (Weeks 7-8)**: Deploy data ingestion pipeline (live feeds, sentiment, macro)
5. **Phase 4 (Weeks 9-10)**: Implement multi-agent committee with weighted voting
6. **Phase 5 (Weeks 11-12)**: Add planner layer, self-reflection, and production hardening

### Success Metrics

**By End of Week 2 (Phase 0)**:
- ✅ 90%+ test coverage on all existing code
- ✅ All critical planning documents complete
- ✅ CI/CD green with 5-stage EDD validation
- ✅ Zero outstanding P1 gaps from gap-analysis.md

**By End of Week 4 (Phase 1)**:
- ✅ Quorum voting operational (3-vote consensus)
- ✅ Redis vector index storing episodic memories
- ✅ PostgreSQL storing patterns, trades, regimes
- ✅ NATS message bus connecting all components
- ✅ Sub-2ms memory retrieval latency (P50)

**By End of Week 6 (Phase 2)**:
- ✅ Trend Agent passing all 7 EDD soundness categories
- ✅ Paper trading operational with live Coinbase data
- ✅ Sharpe ratio > 1.5 on backtests (multiple regimes)
- ✅ Win rate > 55% on out-of-sample data
- ✅ Zero safety violations (position/loss limits)

**By End of Week 8 (Phase 3)**:
- ✅ Live data feeds from 5+ sources (Coinbase, Binance, Twitter, FRED, NewsAPI)
- ✅ InfluxDB storing tick data (10k+ ticks/sec)
- ✅ MongoDB storing sentiment embeddings
- ✅ Scheduler orchestrating 15+ data ingestors
- ✅ < 100ms end-to-end data latency

**By End of Week 10 (Phase 4)**:
- ✅ 5 specialized agents operational (Trend, Mean-Rev, Risk, Execution, Arbitrage)
- ✅ Committee aggregating votes with dynamic weights
- ✅ All agents passing soundness tests
- ✅ Portfolio Sharpe > 2.0 in paper trading
- ✅ < 5% correlation between agent strategies

**By End of Week 12 (Phase 5)**:
- ✅ Planner layer adjusting committee weights
- ✅ Self-reflection monitoring all 3 layers
- ✅ Production monitoring (Prometheus + Grafana)
- ✅ Security audit complete
- ✅ Live trading with $1,000 seed capital
- ✅ System running 24/7 with < 0.1% downtime

### Timeline Overview

```
Week 1-2   │████████│ Phase 0: Foundation (Testing + Docs)
Week 3-4   │████████│ Phase 1: Memory System
Week 5-6   │████████│ Phase 2: First Agent
Week 7-8   │████████│ Phase 3: Data Pipeline
Week 9-10  │████████│ Phase 4: Multi-Agent Committee
Week 11-12 │████████│ Phase 5: Planners + Production
```

### Risk Assessment

**Low Risk** 🟢:
- Foundation code (already 15% complete)
- Unit testing (clear specifications)
- Documentation (atomic action plan exists)

**Medium Risk** 🟡:
- Memory system performance (Redis latency under load)
- Agent coordination (vote aggregation logic)
- Data feed reliability (third-party APIs)

**High Risk** 🔴:
- Live trading safety (requires extensive validation)
- Quorum consensus under network partitions
- Pattern learning convergence (online learning stability)

**Mitigation**: Each phase has explicit validation gates. No phase begins until previous phase passes all EDD tests.

---

## Phase 0: Foundation & Testing (Weeks 1-2)

**Objective**: Achieve 90%+ test coverage on existing code, complete critical documentation, and establish rock-solid CI/CD foundation.

**Why This Matters**: Cannot build memory system or agents on untested foundation. Every line of existing code must be validated before adding complexity.

### Week 1: Test Coverage Blitz

#### Days 1-2: Unit Tests for Existing Code

**Sprint 1A: MCP Server Tests** (6 atomic commits, ~220 lines)
```
tests/unit/test_mcp_server.py
├── test_mcp_resource_listing()         # 30 lines, 15min
├── test_mcp_resource_reading()         # 40 lines, 20min
├── test_mcp_tool_listing()             # 30 lines, 15min
├── test_mcp_tool_execution()           # 50 lines, 25min
├── test_mcp_order_validation()         # 40 lines, 20min
└── test_mcp_error_handling()           # 30 lines, 15min
```

**Sprint 1B: Data Ingest Base Tests** (4 atomic commits, ~100 lines)
```
tests/unit/test_data_ingest_base.py
├── test_datapoint_creation()           # 25 lines, 15min
├── test_datasource_abstract_methods()  # 30 lines, 15min
├── test_source_metadata()              # 20 lines, 10min
└── test_health_checks()                # 25 lines, 15min
```

**Sprint 1C: Binance Ingestor Tests** (8 atomic commits, ~250 lines)
```
tests/unit/test_binance_ingestor.py
├── test_binance_initialization()       # 20 lines, 10min
├── test_ohlcv_fetching()               # 40 lines, 20min
├── test_websocket_parsing()            # 50 lines, 25min
├── test_symbol_normalization()         # 30 lines, 15min
├── test_error_handling()               # 35 lines, 20min
├── test_rate_limiting()                # 30 lines, 15min
├── test_health_check()                 # 20 lines, 10min
└── test_metadata_generation()          # 25 lines, 15min
```

**Sprint 1D: Soundness Tests** (6 atomic commits, ~240 lines)
```
tests/soundness/test_config_soundness.py
├── test_config_determinism()           # 40 lines, 20min
└── test_config_validation()            # 35 lines, 15min

tests/soundness/test_mcp_soundness.py
├── test_mcp_determinism()              # 45 lines, 20min
└── test_mcp_latency()                  # 40 lines, 20min

tests/soundness/test_binance_soundness.py
├── test_binance_determinism()          # 40 lines, 20min
└── test_binance_latency()              # 40 lines, 20min
```

**End of Day 2 Checkpoint**:
- ✅ 24 atomic commits merged
- ✅ ~810 lines of test code added
- ✅ Test coverage: 40% → 75%
- ✅ All unit tests green

#### Days 3-4: Integration Tests

**Sprint 2A: Database Integration** (6 atomic commits, ~195 lines)
```
tests/integration/test_redis.py
├── test_redis_connection()             # 30 lines, 15min
├── test_redis_key_operations()         # 40 lines, 20min
└── test_redis_vector_search_prep()     # 35 lines, 20min

tests/integration/test_postgres.py
├── test_postgres_connection()          # 30 lines, 15min
├── test_postgres_crud()                # 50 lines, 25min
└── test_postgres_transactions()        # 40 lines, 20min
```

**Sprint 2B: MCP Integration** (5 atomic commits, ~215 lines)
```
tests/integration/test_mcp_e2e.py
├── test_mcp_server_startup()           # 35 lines, 20min
├── test_mcp_resource_flow()            # 45 lines, 25min
├── test_mcp_tool_execution()           # 50 lines, 25min
├── test_mcp_error_propagation()        # 40 lines, 20min
└── test_mcp_concurrent_requests()      # 45 lines, 25min
```

**Sprint 2C: API Integration** (4 atomic commits, ~140 lines)
```
tests/integration/test_coinbase_live.py
├── test_coinbase_sandbox_connection()  # 30 lines, 15min
├── test_coinbase_account_fetch()       # 35 lines, 20min
├── test_coinbase_market_data()         # 40 lines, 20min
└── test_coinbase_rate_limiting()       # 35 lines, 20min
```

**End of Day 4 Checkpoint**:
- ✅ 39 total atomic commits (24 + 15)
- ✅ ~1,360 lines of test code
- ✅ Test coverage: 75% → 88%
- ✅ Integration tests validating multi-component flows

#### Days 5-6: Performance & Contract Tests

**Sprint 4A: Performance Tests** (6 atomic commits, ~300 lines)
```
tests/performance/test_mcp_latency.py          # 50 lines, 25min
tests/performance/test_ingest_throughput.py    # 60 lines, 30min
tests/performance/test_config_perf.py          # 40 lines, 20min
tests/performance/test_crypto_perf.py          # 45 lines, 20min
tests/performance/test_redis_perf.py           # 50 lines, 25min
tests/performance/test_postgres_perf.py        # 55 lines, 30min
```

**Sprint 4B: Contract Tests** (4 atomic commits, ~220 lines)
```
tests/contract/test_mcp_schemas.py             # 70 lines, 35min
tests/contract/test_data_schemas.py            # 50 lines, 25min
tests/contract/test_config_schemas.py          # 45 lines, 20min
tests/contract/test_api_schemas.py             # 55 lines, 25min
```

**End of Week 1 Checkpoint**:
- ✅ 49 total atomic commits
- ✅ ~1,880 lines of test code
- ✅ Test coverage: **92%** 🎯
- ✅ CI/CD pipeline: ALL GREEN
- ✅ Performance baselines established

### Week 2: Documentation & Validation

#### Days 7-8: Critical Planning Documents

**Sprint 3A: Build Roadmap** (3 atomic commits, ~1,000 lines)
```
docs/development/build-roadmap.md
├── Phase 0-2 roadmap                   # 400 lines, 30min
├── Phase 3-5 roadmap                   # 400 lines, 30min
└── Phase 6-8 roadmap                   # 200 lines, 20min
```

**Sprint 3B: Security Plan** (4 atomic commits, ~800 lines)
```
docs/security/security-compliance.md
├── API key management                  # 250 lines, 25min
├── Authentication & authorization      # 200 lines, 20min
├── Data encryption                     # 150 lines, 15min
└── Compliance requirements             # 200 lines, 20min
```

**Sprint 3C: Monitoring Strategy** (3 atomic commits, ~600 lines)
```
docs/operations/monitoring-alerting.md
├── Metrics to collect                  # 250 lines, 25min
├── Alert definitions                   # 200 lines, 20min
└── Dashboard designs                   # 150 lines, 15min
```

**End of Day 8 Checkpoint**:
- ✅ 59 total atomic commits
- ✅ 3 critical planning documents complete
- ✅ ~2,400 words of strategic documentation

#### Days 9-10: Test Strategy & Coverage Requirements

**Sprint 3D: Test Strategy Docs** (4 atomic commits, ~950 lines)
```
docs/testing/coverage-requirements.md          # 200 lines, 20min
docs/testing/test-type-guide.md                # 500 lines, 50min
docs/testing/test-data-strategy.md             # 250 lines, 25min
```

**Final Tasks**:
- Run full test suite (unit + integration + soundness + performance)
- Generate coverage report
- Validate CI/CD 5-stage pipeline
- Review gap-analysis.md and verify all P1 gaps closed

**End of Week 2 / Phase 0 Validation Gate**:

✅ **Test Coverage**: 92%+ on all existing code
✅ **CI/CD**: 5-stage EDD pipeline green
✅ **Documentation**: All critical planning docs complete
✅ **Performance**: Baselines established for all critical paths
✅ **Soundness**: Determinism, latency, safety all validated
✅ **Gap Analysis**: Zero P1 gaps remaining

**Deliverables**:
- 59+ atomic commits
- ~1,880 lines of test code
- ~3,350 lines of documentation
- 92%+ test coverage
- Green CI/CD pipeline
- Ready to build memory system

### Phase 0 Success Criteria

**Must Pass Before Phase 1**:
1. ✅ All existing tests pass (unit + integration + soundness)
2. ✅ Test coverage ≥ 90% on src/coinswarm/**/*.py
3. ✅ CI/CD pipeline green for 48 consecutive hours
4. ✅ No outstanding P1 or P2 gaps from gap-analysis.md
5. ✅ All documentation reviewed and merged
6. ✅ Performance baselines documented
7. ✅ Security plan approved

**If Any Fail**: Do not proceed to Phase 1. Fix issues first.

---

## Phase 1: Core Memory System (Weeks 3-4)

**Objective**: Implement the quorum-governed, self-improving memory system as specified in quorum-memory-system.md (18,000 words).

**Why This Matters**: Memory is the brain of Coinswarm. Without it, agents cannot learn from trades, pattern system cannot evolve, and quorum consensus cannot govern decisions.

### Architecture Components

```
┌────────────────────────────────────────────────────────┐
│                   MEMORY SYSTEM                        │
├────────────────────────────────────────────────────────┤
│  Redis (Hot Storage)          PostgreSQL (Cold)        │
│  ├── Episodic Memory          ├── Patterns             │
│  ├── Vector Index (HNSW)      ├── Trades               │
│  └── Regime State             ├── Regimes              │
│                                ├── Episodes             │
│  NATS (Message Bus)           └── Quorum Votes         │
│  ├── Proposals                                         │
│  ├── Votes                    Memory Managers (3+)     │
│  └── Commits                  └── Quorum Voting        │
└────────────────────────────────────────────────────────┘
```

### Week 3: Redis Vector Index & PostgreSQL Models

#### Days 11-12: Redis Vector Index

**Sprint 5A: Vector Index Implementation** (6 atomic commits, ~530 lines)

```python
# src/coinswarm/memory/redis_client.py (100 lines)
class RedisClient:
    """Wrapper for Redis with connection pooling"""
    def __init__(self, host, port, db=0, pool_size=10)
    async def connect()
    async def disconnect()
    async def health_check()
    # Connection pool management, retry logic

# src/coinswarm/memory/vector_index.py (370 lines)
class VectorIndex:
    """Redis-backed HNSW vector index for episodic memory"""

    # Core operations
    async def create_index(dim=384, m=16, ef_construction=200)
    async def add_embedding(id, vector, metadata)
    async def knn_search(query_vector, k=10, filters=None)
    async def delete_embedding(id)

    # Index management
    async def get_index_info()
    async def optimize_index()

    # Health & metrics
    async def get_stats()  # Returns: total entries, index size, QPS
```

**Detailed Tasks**:
```
Day 11:
├── Redis client wrapper                    # 100 lines, 30min
├── Vector index creation                   # 120 lines, 30min
└── Embedding storage (add/get/delete)      # 80 lines, 25min

Day 12:
├── kNN search implementation               # 100 lines, 30min
├── Index management (optimize/rebuild)     # 70 lines, 25min
└── Health checks & Prometheus metrics      # 60 lines, 20min
```

**Sprint 5B: Vector Index Tests** (5 atomic commits, ~245 lines)

```python
# tests/unit/memory/test_vector_index.py
def test_index_creation()           # Index schema validation
def test_embedding_crud()            # Add, retrieve, update, delete
def test_knn_search_accuracy()      # Recall ≥ 0.95 on test vectors

# tests/integration/test_vector_index.py
def test_redis_connection_pooling() # Concurrent operations
def test_index_persistence()        # Survives Redis restart

# tests/performance/test_vector_search.py
def test_search_latency()           # P50 < 1ms, P99 < 5ms
def test_throughput()                # > 1000 QPS sustained
```

**Checkpoint**: Redis vector index operational, < 2ms P50 latency

#### Days 13-14: PostgreSQL Models

**Sprint 6A: SQLAlchemy Models** (7 atomic commits, ~425 lines)

```python
# src/coinswarm/memory/database.py (80 lines)
class Database:
    """PostgreSQL connection and session management"""
    def __init__(self, url, pool_size=5)
    async def connect()
    async def create_tables()
    def get_session() -> Session

# src/coinswarm/memory/models.py (345 lines)

class Trade(Base):
    """Individual trade record"""
    id, symbol, side, entry_price, exit_price, pnl,
    slippage_bps, entry_time, exit_time, agent_id,
    regime_id, pattern_ids

class Pattern(Base):
    """Pattern cluster statistics"""
    id, name, sample_size, mean_pnl, std_dev, sharpe,
    win_rate, tail_5pct, tail_95pct, mean_slippage,
    regime, enabled, last_updated

class Regime(Base):
    """Market regime definition"""
    id, volatility, spread, trend, session, version,
    start_time, end_time

class Episode(Base):
    """Episodic memory metadata"""
    id, bot_id, embedding_id, action, reward, outcome,
    timestamp, regime_id, weight

class AgentState(Base):
    """Agent configuration snapshot"""
    id, agent_id, weights, thresholds, regime_tags,
    timestamp, valid_until

class QuorumVote(Base):
    """Vote record for quorum consensus"""
    id, proposal_id, manager_id, decision, reasons,
    timestamp
```

**Detailed Tasks**:
```
Day 13:
├── Database setup & engine          # 80 lines, 25min
├── Trade model                      # 60 lines, 20min
├── Pattern model                    # 70 lines, 25min
└── Regime model                     # 50 lines, 20min

Day 14:
├── Episode model                    # 60 lines, 20min
├── Agent state model                # 55 lines, 20min
└── Quorum vote model                # 50 lines, 20min
```

**Sprint 6B: Model Tests** (6 atomic commits, ~285 lines)

```python
# tests/unit/memory/test_models.py
def test_trade_model_validation()    # Required fields, constraints
def test_pattern_statistics()        # Sharpe calculation, win rate
def test_regime_versioning()         # Version increments

# tests/integration/test_database.py
def test_database_crud()             # Create, read, update, delete
def test_transactions_rollback()     # ACID guarantees
def test_complex_queries()           # Joins, filters, aggregations
```

**Checkpoint**: PostgreSQL models functional, all CRUD operations tested

### Week 4: NATS Message Bus & Quorum Voting

#### Days 15-16: NATS Client

**Sprint 7A: NATS Implementation** (5 atomic commits, ~330 lines)

```python
# src/coinswarm/core/nats_client.py (330 lines)

class NATSClient:
    """NATS message bus client with pub/sub/request-reply"""

    def __init__(self, servers, cluster_id="coinswarm")

    # Connection management
    async def connect()
    async def disconnect()
    async def reconnect_with_backoff()

    # Publishing
    async def publish(subject, data)
    async def publish_batch(messages)

    # Subscribing
    async def subscribe(subject, callback, queue_group=None)
    async def unsubscribe(subscription_id)

    # Request/Reply
    async def request(subject, data, timeout=2.0)

    # Error handling
    async def on_disconnect(callback)
    async def on_error(callback)
```

**Message Subjects**:
```
mem.propose          # Memory change proposals
mem.vote             # Manager votes on proposals
mem.commit           # Coordinator commits accepted changes
mem.audit            # Audit trail events

planner.propose      # Committee weight changes
planner.vote         # Manager votes on planner proposals
planner.commit       # Accepted planner configurations

agent.action         # Agent decisions
agent.trade          # Trade execution results
```

**Sprint 7B: NATS Tests** (5 atomic commits, ~255 lines)

```python
# tests/unit/test_nats_client.py
def test_connection_management()     # Connect, disconnect, reconnect
def test_publish_subscribe()         # Message delivery

# tests/integration/test_nats.py
def test_pubsub_flow()               # Multi-subscriber delivery
def test_request_reply()             # Synchronous request pattern
def test_queue_groups()              # Load balancing

# tests/performance/test_nats_perf.py
def test_throughput()                # > 10k msg/sec
def test_latency()                   # P50 < 5ms, P99 < 20ms
```

**Checkpoint**: NATS operational, < 5ms P50 latency

#### Days 17-18: Memory Manager & Quorum Voting

**Implementation** (4 atomic commits, ~600 lines)

```python
# src/coinswarm/memory/manager.py (300 lines)

class MemoryManager:
    """Evaluates proposals and votes on memory changes"""

    def __init__(self, manager_id, nats_client, redis_client, db)

    # Proposal evaluation (deterministic)
    async def evaluate_memory_proposal(proposal) -> Vote
    async def evaluate_planner_proposal(proposal) -> Vote

    # Validation checks
    def check_statistical_soundness(proposal) -> (bool, str)
    def check_safety_invariants(proposal) -> (bool, str)
    def check_pattern_quality(proposal) -> (bool, str)

    # Voting
    async def cast_vote(proposal_id, decision, reasons)

# src/coinswarm/memory/coordinator.py (200 lines)

class MemoryCoordinator:
    """Rotating coordinator that commits accepted proposals"""

    def __init__(self, nats_client, redis_client, db)

    # Quorum logic
    async def collect_votes(proposal_id, timeout=2.0)
    def check_quorum(votes, required=3) -> bool
    def check_consensus(votes) -> bool

    # Commit
    async def commit_memory_change(proposal)
    async def broadcast_commit(proposal_id, decision)

    # Audit trail
    async def log_decision(proposal, votes, decision)

# src/coinswarm/memory/proposals.py (100 lines)

@dataclass
class MemoryProposal:
    """Memory change proposal"""
    id: str
    change_type: str  # 'add_episode', 'update_pattern', 'deprecate_pattern'
    data: dict
    submitter: str
    timestamp: datetime
    justification: dict
```

**Quorum Voting Flow**:
```
1. Trading Bot submits proposal
   └─> NATS: mem.propose

2. Memory Managers (3+) evaluate
   ├─> Check statistical soundness
   ├─> Check safety invariants
   └─> Cast vote: ACCEPT/REJECT
       └─> NATS: mem.vote

3. Coordinator collects votes
   ├─> Wait for quorum (3 votes)
   ├─> Check consensus (all agree)
   └─> If ACCEPT:
       ├─> Apply change to Redis/PostgreSQL
       └─> Broadcast commit
           └─> NATS: mem.commit
```

**Tests** (6 atomic commits, ~350 lines)

```python
# tests/unit/memory/test_manager.py
def test_proposal_evaluation_determinism()  # Same inputs → same vote
def test_statistical_checks()               # Sharpe, win rate validation
def test_safety_checks()                    # Position limits, loss limits

# tests/integration/test_quorum_voting.py
def test_three_manager_consensus()          # All agree → ACCEPT
def test_two_manager_disagreement()         # No consensus → REJECT
def test_coordinator_rotation()             # Leader election works

# tests/soundness/test_quorum_soundness.py
def test_byzantine_fault_tolerance()        # 1 manager fails → system ok
def test_network_partition_handling()       # Split brain detection
```

**Checkpoint**: Quorum voting operational, 3-vote consensus working

#### Days 19-20: End-to-End Memory System Test

**Integration Tests** (3 atomic commits, ~400 lines)

```python
# tests/integration/test_memory_system_e2e.py

async def test_episodic_memory_full_cycle():
    """
    1. Agent executes trade
    2. Submits memory proposal (add episode)
    3. Managers vote (all ACCEPT)
    4. Coordinator commits to Redis
    5. Episode queryable via kNN search
    """

async def test_pattern_promotion():
    """
    1. Submit pattern promotion proposal
    2. Managers check: n ≥ 100, SR ≥ 1.5, DD ≤ 0.10
    3. If pass: pattern enabled
    4. Pattern appears in PostgreSQL
    """

async def test_planner_weight_change():
    """
    1. Planner proposes new committee weights
    2. Managers validate: sum=1.0, backtest improvement
    3. If ACCEPT: weights updated
    4. Committee uses new weights
    """
```

**Performance Validation**:
```python
# tests/performance/test_memory_system_perf.py

def test_end_to_end_latency():
    """Proposal → Vote → Commit: < 10ms P50"""

def test_throughput_under_load():
    """100 proposals/sec sustained for 1 minute"""

def test_memory_retrieval():
    """kNN search with 100k entries: < 2ms P50"""
```

### Phase 1 Success Criteria

**Must Pass Before Phase 2**:
1. ✅ Redis vector index operational (sub-2ms P50 latency)
2. ✅ PostgreSQL models functional (all CRUD operations)
3. ✅ NATS message bus running (< 5ms P50 latency)
4. ✅ Quorum voting works (3-vote consensus)
5. ✅ Memory Manager deterministic (same inputs → same vote)
6. ✅ End-to-end memory cycle tested (proposal → commit)
7. ✅ Performance: > 100 proposals/sec throughput
8. ✅ Soundness: Byzantine fault tolerance validated
9. ✅ All EDD tests passing (determinism, latency, safety)
10. ✅ Test coverage ≥ 90% on memory system code

**Deliverables**:
- 37 atomic commits
- ~2,510 lines of production code
- ~1,535 lines of test code
- Quorum-governed memory system operational
- Sub-2ms memory retrieval latency
- Ready to build first trading agent

**If Any Fail**: Do not proceed to Phase 2. Fix issues first.

---

