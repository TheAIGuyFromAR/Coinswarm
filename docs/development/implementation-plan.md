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

## Phase 2: First Trading Agent (Weeks 5-6)

**Objective**: Build and validate Trend-Following Agent with complete EDD testing suite passing all 7 soundness categories.

**Why This Matters**: This is the first agent that will actually trade. It must be bulletproof. Complete EDD validation here sets the pattern for all future agents.

### Architecture: Agent Base Class + Trend Agent

```
┌─────────────────────────────────────────────────────────┐
│                    AGENT BASE CLASS                      │
├─────────────────────────────────────────────────────────┤
│  Abstract Methods:                                       │
│  ├── decide(state) -> Action                            │
│  ├── update(outcome)                                     │
│  └── get_config() -> dict                               │
│                                                          │
│  Shared Infrastructure:                                  │
│  ├── Safety checks (position/loss limits)               │
│  ├── Memory integration (episodic recall)               │
│  └── Metrics (decisions/sec, win rate, Sharpe)          │
└─────────────────────────────────────────────────────────┘
                          ▲
                          │ inherits
┌─────────────────────────┴───────────────────────────────┐
│                    TREND AGENT                           │
├─────────────────────────────────────────────────────────┤
│  Strategy: Moving Average Crossover + ADX               │
│  ├── Fast MA (10-period)                                │
│  ├── Slow MA (20-period)                                │
│  ├── ADX (14-period) for trend strength                 │
│  └── Position sizing (Kelly criterion)                  │
│                                                          │
│  Entry: Fast MA > Slow MA + ADX > 25                    │
│  Exit: Fast MA < Slow MA OR stop loss                   │
│  Position Size: Kelly fraction * risk_scaling           │
└─────────────────────────────────────────────────────────┘
```

### Week 5: Agent Implementation

#### Days 21-22: Base Agent Class

**Implementation** (4 atomic commits, ~360 lines)

```python
# src/coinswarm/agents/base.py (120 lines)

class BaseAgent(ABC):
    """Base class for all trading agents"""

    def __init__(
        self,
        agent_id: str,
        memory_client: MemoryClient,
        config: AgentConfig
    ):
        self.agent_id = agent_id
        self.memory = memory_client
        self.config = config

        # Safety limits
        self.max_position_size = config.max_position_size
        self.max_loss_per_trade = config.max_loss_per_trade
        self.daily_loss_limit = config.daily_loss_limit

        # Metrics
        self.trades_today = 0
        self.daily_pnl = 0.0
        self.decisions_made = 0

    @abstractmethod
    async def decide(self, state: MarketState) -> Action:
        """Generate trading decision from market state"""
        pass

    @abstractmethod
    async def update(self, outcome: TradeOutcome):
        """Learn from trade outcome"""
        pass

    def check_safety_limits(self, action: Action) -> bool:
        """Validate action against safety constraints"""
        # Position size check
        if action.size > self.max_position_size:
            return False

        # Daily loss limit
        if self.daily_pnl < -self.daily_loss_limit:
            return False

        # Max trades per day
        if self.trades_today >= self.config.max_trades_per_day:
            return False

        return True

    async def recall_similar_states(self, state: MarketState, k=10):
        """Query episodic memory for similar states"""
        embedding = self.embed_state(state)
        return await self.memory.knn_search(embedding, k=k)

    @abstractmethod
    def embed_state(self, state: MarketState) -> np.ndarray:
        """Convert market state to 384-dim embedding"""
        pass


# src/coinswarm/agents/trend.py (240 lines)

class TrendAgent(BaseAgent):
    """Trend-following agent using MA crossover + ADX"""

    def __init__(
        self,
        agent_id: str,
        memory_client: MemoryClient,
        config: TrendAgentConfig
    ):
        super().__init__(agent_id, memory_client, config)

        # Strategy parameters
        self.fast_period = config.fast_period  # Default: 10
        self.slow_period = config.slow_period  # Default: 20
        self.adx_period = config.adx_period    # Default: 14
        self.adx_threshold = config.adx_threshold  # Default: 25

        # Position sizing
        self.kelly_fraction = config.kelly_fraction  # Default: 0.25
        self.risk_scaling = config.risk_scaling      # Default: 1.0

    async def decide(self, state: MarketState) -> Action:
        """Generate trading decision"""

        # Calculate indicators
        fast_ma = self.calculate_ma(state.prices, self.fast_period)
        slow_ma = self.calculate_ma(state.prices, self.slow_period)
        adx = self.calculate_adx(state.prices, self.adx_period)

        # Generate signal
        if fast_ma > slow_ma and adx > self.adx_threshold:
            signal = "BUY"
            confidence = min(adx / 50.0, 1.0)  # Normalize ADX to 0-1
        elif fast_ma < slow_ma and adx > self.adx_threshold:
            signal = "SELL"
            confidence = min(adx / 50.0, 1.0)
        else:
            signal = "HOLD"
            confidence = 0.5

        # Recall similar states from memory
        similar_states = await self.recall_similar_states(state, k=10)
        memory_adjustment = self.calculate_memory_adjustment(similar_states)

        # Adjust confidence based on memory
        confidence *= memory_adjustment

        # Calculate position size
        size = self.calculate_position_size(
            confidence=confidence,
            volatility=state.volatility,
            account_value=state.account_value
        )

        # Create action
        action = Action(
            type=signal,
            confidence=confidence,
            size=size,
            stop_loss=self.calculate_stop_loss(state),
            take_profit=self.calculate_take_profit(state)
        )

        # Safety check
        if not self.check_safety_limits(action):
            return Action(type="HOLD", confidence=0.0, size=0)

        return action

    def calculate_position_size(self, confidence, volatility, account_value):
        """Kelly criterion position sizing"""
        # Kelly: f = (p * b - q) / b
        # Where p = win probability, q = 1 - p, b = win/loss ratio

        # Estimate win probability from confidence
        win_prob = 0.5 + (confidence - 0.5) * 0.3  # 0.5-0.65 range

        # Use historical win/loss ratio (from memory or default)
        win_loss_ratio = 1.5  # TODO: Calculate from memory

        # Kelly fraction
        kelly = (win_prob * win_loss_ratio - (1 - win_prob)) / win_loss_ratio
        kelly = max(0, kelly) * self.kelly_fraction  # Fractional Kelly

        # Adjust for volatility
        volatility_adjustment = 1.0 / (1.0 + volatility)

        # Calculate size
        size = account_value * kelly * volatility_adjustment * self.risk_scaling

        return min(size, self.max_position_size)

    def calculate_stop_loss(self, state: MarketState) -> float:
        """ATR-based stop loss"""
        atr = self.calculate_atr(state.prices, period=14)
        return state.current_price - (2.0 * atr)  # 2 ATR stop

    def calculate_take_profit(self, state: MarketState) -> float:
        """Risk/reward based take profit"""
        atr = self.calculate_atr(state.prices, period=14)
        return state.current_price + (3.0 * atr)  # 3 ATR target (1.5:1 R:R)

    # Technical indicators (moving averages, ADX, ATR)
    # ... implementation details ...
```

**Checkpoint**: Agent base class + Trend Agent implemented

#### Days 23-24: Unit Tests

**Unit Tests** (3 atomic commits, ~135 lines)

```python
# tests/unit/agents/test_trend.py

def test_indicator_calculation():
    """Test MA, ADX, ATR calculations"""
    agent = TrendAgent(config=test_config)
    prices = load_fixture("golden_cross.csv")

    fast_ma = agent.calculate_ma(prices, period=10)
    slow_ma = agent.calculate_ma(prices, period=20)
    adx = agent.calculate_adx(prices, period=14)

    assert len(fast_ma) == len(prices)
    assert fast_ma[-1] > slow_ma[-1]  # Golden cross scenario
    assert 0 <= adx[-1] <= 100

def test_signal_generation():
    """Test BUY/SELL/HOLD signal logic"""
    agent = TrendAgent(config=test_config)
    state = load_market_state("trending_up.json")

    action = agent.decide(state)

    assert action.type == "BUY"
    assert 0.5 <= action.confidence <= 1.0
    assert action.size <= agent.max_position_size

def test_position_sizing():
    """Test Kelly criterion sizing"""
    agent = TrendAgent(config=test_config)

    size = agent.calculate_position_size(
        confidence=0.7,
        volatility=0.02,
        account_value=10000
    )

    assert 0 <= size <= agent.max_position_size
    assert size < 10000 * 0.5  # No more than 50% of account

def test_safety_limits():
    """Test position and loss limit enforcement"""
    agent = TrendAgent(config=test_config)
    agent.daily_pnl = -agent.daily_loss_limit * 0.99  # Near limit

    action = Action(type="BUY", size=1000, confidence=0.8)

    assert not agent.check_safety_limits(action)
```

### Week 6: Full EDD Validation

#### Days 25-26: Soundness Tests

**7 EDD Soundness Categories** (3 atomic commits, ~180 lines)

```python
# tests/soundness/test_trend_soundness.py

# 1. Determinism
def test_trend_agent_determinism():
    """Same inputs → same outputs (no hidden randomness)"""
    agent = TrendAgent(seed=42, config=test_config)
    state = load_market_state("test_case_1.json")

    action1 = agent.decide(state)
    action2 = agent.decide(state)

    assert action1 == action2
    assert action1.type == action2.type
    assert abs(action1.confidence - action2.confidence) < 1e-9

# 2. Statistical Sanity
def test_trend_agent_statistical_sanity():
    """Backtest shows realistic performance metrics"""
    agent = TrendAgent(config=test_config)
    backtest = run_backtest(agent, dataset="2024_Q1_out_of_sample")

    assert 0.5 <= backtest.sharpe_ratio <= 3.0  # Realistic Sharpe
    assert backtest.max_drawdown <= 0.15        # Max 15% DD
    assert 0.50 <= backtest.win_rate <= 0.70    # Realistic win rate
    assert backtest.turnover <= 50              # Not overtrading
    assert backtest.total_trades >= 20          # Enough samples

# 3. Safety Invariants
def test_trend_agent_safety_invariants():
    """Agent never violates position or loss limits"""
    agent = TrendAgent(config=test_config)
    backtest = run_backtest(agent, dataset="2024_Q1")

    for trade in backtest.trades:
        assert trade.size <= agent.max_position_size
        assert trade.loss <= agent.max_loss_per_trade

    assert backtest.max_daily_loss <= agent.daily_loss_limit

# 4. Latency (Performance)
def test_trend_agent_latency():
    """Decision making is fast enough for live trading"""
    agent = TrendAgent(config=test_config)
    state = load_market_state("test_case_1.json")

    latencies = []
    for _ in range(100):
        start = time.perf_counter()
        action = agent.decide(state)
        latency = time.perf_counter() - start
        latencies.append(latency)

    p50 = np.percentile(latencies, 50)
    p99 = np.percentile(latencies, 99)

    assert p50 < 0.010  # 10ms P50
    assert p99 < 0.050  # 50ms P99

# 5. Economic Realism
def test_trend_agent_economic_realism():
    """Accounts for slippage, fees, realistic fills"""
    agent = TrendAgent(config=test_config)
    backtest = run_backtest(
        agent,
        dataset="2024_Q1",
        slippage_model=realistic_slippage,
        fee_bps=10  # 0.1% fees
    )

    # Should still be profitable after costs
    assert backtest.net_pnl > 0
    assert backtest.sharpe_ratio > 1.0

    # Slippage should be realistic
    assert backtest.avg_slippage_bps < 50  # < 0.5%

# 6. Memory Stability
def test_trend_agent_memory_convergence():
    """Memory-augmented decisions improve over time"""
    agent = TrendAgent(config=test_config)

    # Run backtest in two phases
    phase1 = run_backtest(agent, dataset="2024_Q1_first_half")
    phase2 = run_backtest(agent, dataset="2024_Q1_second_half")

    # Performance should improve (or at least not degrade)
    assert phase2.sharpe_ratio >= phase1.sharpe_ratio * 0.8

# 7. Robustness
def test_trend_agent_regime_robustness():
    """Works across multiple market regimes"""
    agent = TrendAgent(config=test_config)

    regimes = ["trending_up", "range_bound", "trending_down", "high_volatility"]

    for regime in regimes:
        backtest = run_backtest(agent, dataset=f"regime_{regime}")

        # Should not blow up in any regime
        assert backtest.max_drawdown <= 0.20
        assert backtest.sharpe_ratio > 0  # At least positive
```

#### Days 27-28: Backtesting & Integration

**Backtest Tests** (2 atomic commits, ~200 lines)

```python
# tests/backtest/test_trend_backtest.py

def test_golden_cross_scenario():
    """Test on golden cross pattern"""
    agent = TrendAgent(config=test_config)
    fixture = load_fixture("golden_cross")

    backtest = run_backtest(agent, data=fixture)

    assert backtest.sharpe_ratio > 1.5
    assert backtest.win_rate > 0.55
    assert backtest.max_drawdown < 0.10

def test_mean_reversion_scenario():
    """Test on mean reversion pattern (should avoid)"""
    agent = TrendAgent(config=test_config)
    fixture = load_fixture("mean_reversion")

    backtest = run_backtest(agent, data=fixture)

    # Should mostly HOLD (not catch whipsaws)
    assert backtest.total_trades < 10
    assert backtest.max_drawdown < 0.10

def test_high_volatility_scenario():
    """Test during volatility spike"""
    agent = TrendAgent(config=test_config)
    fixture = load_fixture("high_volatility")

    backtest = run_backtest(agent, data=fixture)

    # Should reduce position sizes
    assert backtest.avg_position_size < agent.max_position_size * 0.5

def test_live_paper_trading_integration():
    """Test with live Coinbase sandbox data"""
    agent = TrendAgent(config=test_config)
    coinbase_client = CoinbaseClient(sandbox=True)

    # Run for 1 hour in paper trading mode
    results = await run_paper_trading(
        agent=agent,
        data_client=coinbase_client,
        duration_minutes=60
    )

    assert results.decisions_made > 0
    assert results.trades_executed >= 0
    assert results.no_errors
```

**Performance Tests** (1 atomic commit, ~45 lines)

```python
# tests/performance/test_trend_perf.py

def test_decision_throughput():
    """Test decisions per second"""
    agent = TrendAgent(config=test_config)
    states = load_market_states(count=1000)

    start = time.time()
    for state in states:
        action = agent.decide(state)
    duration = time.time() - start

    decisions_per_sec = 1000 / duration

    assert decisions_per_sec > 100  # At least 100 decisions/sec
```

### Phase 2 Success Criteria

**Must Pass Before Phase 3**:
1. ✅ All 7 EDD soundness categories passing
   - Determinism ✅
   - Statistical Sanity ✅ (Sharpe > 1.5, Win rate > 55%)
   - Safety Invariants ✅ (No limit violations)
   - Latency ✅ (P50 < 10ms)
   - Economic Realism ✅ (Profitable after fees/slippage)
   - Memory Stability ✅ (Improves over time)
   - Robustness ✅ (Works across regimes)

2. ✅ Backtest performance metrics:
   - Sharpe Ratio ≥ 1.5
   - Win Rate ≥ 55%
   - Max Drawdown ≤ 10%
   - Total Trades ≥ 50 (sufficient sample size)

3. ✅ Paper trading validation:
   - Runs for 24 hours without errors
   - Makes sensible decisions (no wild trades)
   - Respects safety limits
   - Integrates with memory system

4. ✅ Test coverage ≥ 90% on agent code

**Deliverables**:
- 12 atomic commits
- ~600 lines of production code (agent implementation)
- ~560 lines of test code (unit + soundness + backtest + performance)
- First agent ready for live trading (with human oversight)
- EDD validation framework proven

**If Any Fail**: Do not proceed to Phase 3. Fix issues first.

---

## Phase 3: Data Pipeline (Weeks 7-8)

**Objective**: Deploy live data ingestion from 5+ sources feeding all three layers of the hierarchical decision system.

**Why This Matters**: Agents need real-time data to make decisions. Planners need sentiment and macro. Committee needs tick data. Memory needs execution logs.

### Data Architecture (Per data-feeds-architecture.md)

```
SOURCES → INGESTORS → STORAGE → LAYERS
─────────────────────────────────────────────────────────
Exchanges    Binance      InfluxDB    Committee (ms-s)
(Coinbase)   Coinbase     (OHLCV)     ├── Tick data
             → Tick-by-tick           └── Order book

News APIs    NewsAPI      MongoDB     Planners (h-d)
(Twitter)    Twitter      (Documents) ├── Sentiment
Social       Reddit                   ├── News
             → Embeddings             └── Social

Macro Data   FRED         PostgreSQL  Self-Reflection
(FRED)       → Indicators (Structured) └── Aggregates

On-Chain     Etherscan    MongoDB     All Layers
(Glassnode)  → Metrics    (Documents) └── Context
```

### Week 7: Core Data Ingestors

#### Days 29-30: Exchange Ingestors (Already have Binance, add Coinbase)

**Coinbase Ingestor** (2 commits, ~200 lines)
```python
# src/coinswarm/data_ingest/exchanges/coinbase.py
class CoinbaseIngestor(DataSource):
    """Live tick data from Coinbase Advanced"""
    # WebSocket: trades, order book, ticker
    # REST fallback for history
    # Store in InfluxDB (OHLCV), Redis Streams (ticks)
```

**Tests** (2 commits, ~100 lines)
- Unit: WebSocket parsing, reconnection logic
- Integration: Live connection to sandbox
- Soundness: Latency < 100ms, data quality (OHLCV validation)

#### Days 31-32: Sentiment Ingestors (3 data sources)

**NewsAPI Ingestor** (2 commits, ~180 lines)
```python
# src/coinswarm/data_ingest/news/newsapi.py
class NewsAPIIngestor(DataSource):
    """Crypto news from NewsAPI"""
    # Poll every 5 minutes
    # Extract: headline, content, timestamp, source
    # Generate embeddings (sentence-transformers)
    # Store in MongoDB
```

**Twitter/X Ingestor** (2 commits, ~200 lines)
```python
# src/coinswarm/data_ingest/social/twitter.py
class TwitterIngestor(DataSource):
    """Sentiment from crypto Twitter"""
    # Track keywords: #BTC, #ETH, major influencers
    # Extract: tweet text, engagement, timestamp
    # Sentiment scoring (vader or transformer)
    # Store in MongoDB
```

**Reddit Ingestor** (2 commits, ~180 lines)
```python
# src/coinswarm/data_ingest/social/reddit.py
class RedditIngestor(DataSource):
    """Community sentiment from r/cryptocurrency, r/bitcoin"""
    # Poll every 10 minutes
    # Extract: post/comment text, upvotes, timestamp
    # Sentiment scoring
    # Store in MongoDB
```

#### Days 33-34: Macro Data Ingestors

**FRED Ingestor** (2 commits, ~150 lines)
```python
# src/coinswarm/data_ingest/macro/fred.py
class FREDIngestor(DataSource):
    """Macro indicators from Federal Reserve"""
    # Daily updates: DXY, interest rates, treasury yields
    # Store in PostgreSQL
    # Used by Planners for regime detection
```

**Tests for All Ingestors** (4 commits, ~250 lines)
- Unit tests: API parsing, error handling, rate limiting
- Integration tests: Live API connections (with mocks for CI)
- Performance tests: Throughput (should handle 1000 ticks/sec)

**Checkpoint**: All ingestors operational, data flowing into storage

### Week 8: Scheduler & Data Distribution

#### Days 35-36: Prefect Scheduler

**Scheduler Setup** (3 commits, ~300 lines)
```python
# src/coinswarm/data_ingest/scheduler.py

from prefect import flow, task

@task
async def ingest_coinbase_ticks():
    """Run continuously (WebSocket)"""
    ingestor = CoinbaseIngestor()
    await ingestor.run()

@task
async def ingest_news():
    """Run every 5 minutes"""
    ingestor = NewsAPIIngestor()
    await ingestor.fetch()

@task
async def ingest_macro():
    """Run daily at 9:00 AM ET"""
    ingestor = FREDIngestor()
    await ingestor.fetch()

@flow
async def data_pipeline():
    """Orchestrate all data ingestion"""
    # Continuous tasks
    await ingest_coinbase_ticks.submit()

    # Scheduled tasks
    schedule(ingest_news, interval_minutes=5)
    schedule(ingest_macro, cron="0 9 * * *")
```

**Monitoring & Alerts** (2 commits, ~200 lines)
- Prometheus metrics: ingestion rate, latency, errors
- Grafana dashboards: data freshness, source health
- Alerts: data stale > 5min, API errors > 10/min

#### Days 37-38: Data Distribution Layer

**Data Clients for Each Layer** (4 commits, ~400 lines)

```python
# src/coinswarm/data_feeds/committee_client.py
class CommitteeDataClient:
    """Real-time data for Committee agents"""
    async def subscribe_ticks(symbol: str) -> AsyncIterator[Tick]
    async def get_order_book(symbol: str) -> OrderBook
    # Reads from: Redis Streams, InfluxDB

# src/coinswarm/data_feeds/planner_client.py
class PlannerDataClient:
    """Aggregated data for Planners"""
    async def get_sentiment_window(days=7) -> SentimentTimeSeries
    async def get_funding_rates() -> Dict[str, float]
    async def get_macro_indicators() -> MacroData
    # Reads from: MongoDB, PostgreSQL

# src/coinswarm/data_feeds/memory_client.py
class MemoryDataClient:
    """Execution logs for Memory Optimizer"""
    async def log_trade(trade: TradeOutcome)
    async def get_performance_metrics() -> Dict
    # Reads from: PostgreSQL (trades table)
```

**End-to-End Tests** (3 commits, ~300 lines)
```python
# tests/integration/test_data_pipeline_e2e.py

async def test_tick_to_committee_flow():
    """Tick data reaches Committee in < 100ms"""
    # 1. Ingestor receives tick from Coinbase
    # 2. Stores in Redis Stream
    # 3. Committee subscribes and receives
    # 4. Measure end-to-end latency

async def test_sentiment_to_planner_flow():
    """News → Sentiment → Planner in < 10 seconds"""
    # 1. NewsAPI returns article
    # 2. Embedding generated
    # 3. Stored in MongoDB
    # 4. Planner queries aggregated sentiment
    # 5. Validates data freshness

async def test_pipeline_resilience():
    """Pipeline recovers from failures"""
    # 1. Kill Redis
    # 2. Ingestor buffers data
    # 3. Redis restarts
    # 4. Buffered data flushed
    # 5. No data loss
```

### Phase 3 Success Criteria

**Must Pass Before Phase 4**:
1. ✅ 5+ data sources operational:
   - Coinbase ✅ (tick data)
   - NewsAPI ✅ (news sentiment)
   - Twitter ✅ (social sentiment)
   - Reddit ✅ (community sentiment)
   - FRED ✅ (macro indicators)

2. ✅ Data flowing to correct storage:
   - InfluxDB: OHLCV (10k+ ticks/sec)
   - MongoDB: News/social embeddings (100+ docs/min)
   - PostgreSQL: Macro indicators (daily updates)
   - Redis Streams: Live ticks (< 50ms latency)

3. ✅ Scheduler orchestrating all ingestors:
   - Prefect flows running
   - No crashes for 48 hours
   - Auto-recovery from API failures

4. ✅ Data clients for all layers:
   - Committee can subscribe to ticks
   - Planners can query sentiment
   - Memory can log trades

5. ✅ Performance metrics:
   - Tick ingestion: < 100ms P50 latency
   - Sentiment updates: < 5 min freshness
   - Macro data: Daily by 10:00 AM ET

6. ✅ Monitoring operational:
   - Prometheus collecting metrics
   - Grafana dashboards live
   - Alerts configured and tested

**Deliverables**:
- 24 atomic commits
- ~1,810 lines of production code (ingestors + scheduler + clients)
- ~650 lines of test code
- Live data pipeline operational 24/7
- Ready for multi-agent committee

**If Any Fail**: Do not proceed to Phase 4. Fix issues first.

---

## Phase 4: Multi-Agent Committee (Weeks 9-10)

**Objective**: Implement 5 specialized agents with weighted voting committee as specified in hierarchical-temporal-decision-system.md.

**Why This Matters**: Single agent has limited view. Committee aggregates multiple strategies for robustness and better risk-adjusted returns.

### Committee Architecture

```
┌──────────────────────────────────────────────────────┐
│              COMMITTEE (Weighted Ensemble)            │
├──────────────────────────────────────────────────────┤
│  Agents (with dynamic weights):                      │
│  ├── Trend Agent (w=0.30)         [Already built]    │
│  ├── Mean-Reversion Agent (w=0.25)  [New]           │
│  ├── Risk Agent (w=0.20)             [New]           │
│  ├── Execution Agent (w=0.15)        [New]           │
│  └── Arbitrage Agent (w=0.10)        [New]           │
│                                                       │
│  Aggregation: action = Σ w_i * agent_i.action       │
│  Attribution tracking for each agent's contribution  │
└──────────────────────────────────────────────────────┘
```

### Week 9: Four New Agents

#### Days 39-40: Mean-Reversion Agent
**Implementation** (3 commits, ~220 lines)
```python
# src/coinswarm/agents/mean_reversion.py
class MeanReversionAgent(BaseAgent):
    """Trades overbought/oversold conditions"""
    # Strategy: RSI + Bollinger Bands + Z-score
    # Entry: RSI < 30 (oversold) or RSI > 70 (overbought)
    # Exit: Return to mean OR stop loss
```
**Tests** (2 commits, ~150 lines): Unit + soundness (all 7 EDD categories)

#### Days 41-42: Risk Agent
**Implementation** (3 commits, ~200 lines)
```python
# src/coinswarm/agents/risk.py
class RiskAgent(BaseAgent):
    """Monitors portfolio risk and suggests hedges"""
    # Monitors: VaR, correlation matrix, tail risk
    # Votes SELL/SIZE_DOWN when risk exceeds thresholds
    # Votes BUY hedges (inverse positions) during high volatility
```
**Tests** (2 commits, ~140 lines): Unit + soundness

#### Days 43-44: Execution Agent
**Implementation** (3 commits, ~180 lines)
```python
# src/coinswarm/agents/execution.py
class ExecutionAgent(BaseAgent):
    """Optimizes order placement and timing"""
    # Monitors: slippage, fill rates, queue position
    # Votes on SIZE adjustments based on liquidity
    # Suggests HOLD during wide spreads
```
**Tests** (2 commits, ~120 lines): Unit + soundness

#### Days 45-46: Arbitrage Agent
**Implementation** (3 commits, ~160 lines)
```python
# src/coinswarm/agents/arbitrage.py
class ArbitrageAgent(BaseAgent):
    """Identifies cross-exchange opportunities"""
    # Monitors: funding rates, basis spreads, price differentials
    # Opportunistic (low weight)
    # Only votes BUY/SELL when spread > threshold
```
**Tests** (2 commits, ~110 lines): Unit + soundness

#### Days 46.5-47: Research Agent (NEW - Strategy Competition)

**Concept**: After 4+ weeks of pure organic learning (Phases 2-3), Research Agent proposes proven tradfi strategies to **compete** against organically-discovered patterns. The system determines which work better in crypto through head-to-head performance comparison.

**Timeline**:
- ✅ Weeks 5-8: Pure tabula rasa (Trend Agent learns from scratch, patterns emerge)
- ⭐ Week 9: Research Agent proposes tradfi strategies (Days 46-47)
- 🔥 Week 10+: Organic vs Tradfi strategies compete for committee weights

**Implementation** (3 commits, ~280 lines)
```python
# src/coinswarm/agents/research.py

class ResearchAgent:
    """Studies tradfi strategies and proposes them to memory system"""

    STRATEGY_LIBRARY = {
        'momentum': {
            'description': 'Buy assets with strong recent performance',
            'academic_paper': 'Jegadeesh & Titman (1993)',
            'typical_sharpe': 0.8,
            'tradfi_validation': 'Proven in equities 1970-2020',
            'crypto_adaptations': ['shorter lookback', 'higher turnover']
        },
        'pairs_trading': {
            'description': 'Trade correlated pairs when spread widens',
            'academic_paper': 'Gatev et al. (2006)',
            'typical_sharpe': 1.2,
            'tradfi_validation': 'Used by quant hedge funds',
            'crypto_adaptations': ['BTC/ETH pair', 'stablecoin arbitrage']
        },
        'statistical_arbitrage': {
            'description': 'Mean reversion on cointegrated assets',
            'academic_paper': 'Avellaneda & Lee (2010)',
            'typical_sharpe': 1.5,
            'tradfi_validation': 'Renaissance Technologies',
            'crypto_adaptations': ['24/7 markets', 'higher volatility']
        },
        'carry_trade': {
            'description': 'Borrow low-yield, lend high-yield',
            'academic_paper': 'Burnside et al. (2011)',
            'typical_sharpe': 0.6,
            'tradfi_validation': 'FX markets since 1980s',
            'crypto_adaptations': ['funding rate differentials', 'staking yields']
        },
        'volatility_targeting': {
            'description': 'Scale positions inversely with volatility',
            'academic_paper': 'Moreira & Muir (2017)',
            'typical_sharpe': 'Improves by 0.3-0.5',
            'tradfi_validation': 'Risk parity funds',
            'crypto_adaptations': ['faster vol estimation', 'intraday rebalancing']
        }
    }

    async def research_strategies(self) -> List[StrategyProposal]:
        """Research and propose tradfi strategies adapted for crypto"""
        proposals = []

        for strategy_name, info in self.STRATEGY_LIBRARY.items():
            # Check if strategy already exists in pattern library
            if await self.pattern_exists(strategy_name):
                continue

            # Create strategy proposal
            proposal = StrategyProposal(
                name=strategy_name,
                description=info['description'],
                source='tradfi_research',
                academic_backing=info['academic_paper'],
                expected_sharpe=info['typical_sharpe'],
                adaptations=info['crypto_adaptations'],

                # Implementation details
                entry_rules=self.generate_entry_rules(strategy_name),
                exit_rules=self.generate_exit_rules(strategy_name),
                position_sizing=self.generate_sizing_rules(strategy_name),

                # Validation requirements
                requires_backtest=True,
                min_sharpe_threshold=1.0,  # Lower than organic patterns (1.5)
                min_sample_size=50         # Require evidence
            )

            proposals.append(proposal)

        return proposals

    async def submit_strategy_proposal(self, proposal: StrategyProposal):
        """Submit strategy to quorum for approval"""

        # Step 1: Backtest on recent data
        backtest_result = await self.backtest_strategy(
            proposal,
            dataset='last_90_days',
            include_slippage=True,
            include_fees=True
        )

        # Step 2: Only submit if backtest passes
        if backtest_result.sharpe < proposal.min_sharpe_threshold:
            logger.info(f"Strategy {proposal.name} failed backtest: "
                       f"Sharpe {backtest_result.sharpe:.2f}")
            return None

        # Step 3: Create pattern proposal for quorum
        pattern_proposal = PatternProposal(
            change_type='add_pattern',
            pattern_name=proposal.name,
            source='research_agent',
            statistics={
                'backtest_sharpe': backtest_result.sharpe,
                'backtest_win_rate': backtest_result.win_rate,
                'backtest_trades': backtest_result.total_trades,
                'academic_backing': proposal.academic_backing,
                'tradfi_sharpe': proposal.expected_sharpe
            },
            justification={
                'reason': 'Proven tradfi strategy adapted for crypto',
                'academic_paper': proposal.academic_backing,
                'backtest_performance': backtest_result.summary()
            }
        )

        # Step 4: Submit to quorum via NATS
        await self.nats_client.publish('mem.propose', pattern_proposal)

        logger.info(f"Submitted {proposal.name} for quorum approval")
        return pattern_proposal

# Example: Momentum Strategy Implementation
class MomentumStrategy(BaseAgent):
    """Researched strategy: Buy winners, sell losers"""

    def __init__(self):
        super().__init__()
        self.lookback_period = 20  # days (shorter than tradfi 12mo)
        self.holding_period = 5    # days (faster turnover)
        self.source = 'research_agent'

    async def decide(self, state: MarketState) -> Action:
        # Calculate momentum score
        returns = state.prices[-self.lookback_period:].pct_change()
        momentum_score = returns.mean() / returns.std()

        if momentum_score > 1.5:
            return Action(type='BUY', confidence=0.7, size=100)
        elif momentum_score < -1.5:
            return Action(type='SELL', confidence=0.7, size=100)
        else:
            return Action(type='HOLD', confidence=0.5, size=0)
```

**How It Works**:

1. **Research Phase** (Days 46.5):
   - Research Agent studies 5 proven tradfi strategies
   - Each strategy has academic backing (published papers)
   - Adapts strategy parameters for crypto (24/7, higher vol, etc.)

2. **Backtest Phase** (Days 47):
   - Backtest each strategy on recent crypto data (90 days)
   - Include realistic slippage and fees
   - Only propose strategies with Sharpe > 1.0

3. **Quorum Approval** (Days 47):
   - Submit proposals to Memory Managers
   - Managers validate:
     - Academic backing is legitimate
     - Backtest performance meets threshold
     - Strategy doesn't violate safety invariants
   - If approved: Strategy added to pattern library

4. **Competition Phase** (Week 10+):
   - Organic patterns (from Weeks 5-8 trading) vs Tradfi strategies
   - Committee weights adjusted based on live performance
   - If organic pattern outperforms → gets higher weight
   - If tradfi strategy outperforms → gets higher weight
   - **Best strategies win, regardless of source**

**Key Benefits**:
- ✅ **Pure Organic First**: 4 weeks of tabula rasa learning (no tradfi bias)
- ✅ **Head-to-Head Competition**: Empirical test of which strategies work in crypto
- ✅ **Academic Validation**: Tradfi strategies have 50+ years of research backing
- ✅ **Still Validated**: All patterns (organic + tradfi) require quorum approval
- ✅ **Learn What Works**: System discovers if tradfi strategies adapt to crypto
- ✅ **Meritocracy**: Committee weights follow performance, not pedigree

**Integration with Existing System**:
```
Trading Agents (Committee)
├── Organic Patterns (learned from trades)
│   └── Discovered via episodic memory clustering
└── Researched Patterns (tradfi strategies)
    └── Proposed by Research Agent, validated by quorum

Both types require:
- Backtest validation (Sharpe > threshold)
- Quorum approval (3-vote consensus)
- Live performance monitoring
- Can be deprecated if underperform
```

**Tests** (2 commits, ~150 lines): Backtest validation, quorum integration

**Checkpoint**: All 6 agents operational (5 trading + 1 research)

### Week 10: Committee Integration

#### Days 47-48: Committee Class

**Implementation** (4 commits, ~350 lines)
```python
# src/coinswarm/agents/committee.py

class Committee:
    """Aggregates decisions from multiple agents"""

    def __init__(self):
        self.agents = {
            'trend': TrendAgent(),
            'mean_rev': MeanReversionAgent(),
            'risk': RiskAgent(),
            'execution': ExecutionAgent(),
            'arbitrage': ArbitrageAgent()
        }

        # Default weights (overridden by Planner in Phase 5)
        self.weights = {
            'trend': 0.30,
            'mean_rev': 0.25,
            'risk': 0.20,
            'execution': 0.15,
            'arbitrage': 0.10
        }

    async def decide(self, state: MarketState) -> Action:
        """Aggregate agent votes with current weights"""
        votes = {}
        for name, agent in self.agents.items():
            votes[name] = await agent.decide(state)

        # Weighted aggregation
        action_scores = defaultdict(float)
        for name, action in votes.items():
            weight = self.weights[name]
            action_scores[action.type] += weight * action.confidence

        best_action_type = max(action_scores, key=action_scores.get)

        return Action(
            type=best_action_type,
            confidence=action_scores[best_action_type],
            size=self.aggregate_position_size(votes),
            attribution=self.calculate_attribution(votes)
        )

    def update_weights(self, new_weights: Dict[str, float]):
        """Update weights from Planner"""
        assert abs(sum(new_weights.values()) - 1.0) < 1e-6
        self.weights = new_weights
```

**Tests** (4 commits, ~300 lines)
```python
# tests/unit/agents/test_committee.py

def test_weighted_aggregation():
    """Votes aggregate correctly with weights"""

def test_weight_updates():
    """Weights can be updated dynamically"""

def test_attribution_tracking():
    """Attribution shows which agents contributed"""

# tests/integration/test_committee_e2e.py

async def test_committee_paper_trading():
    """Committee runs for 24 hours in paper trading"""
    # Measure: Sharpe, diversification, correlation
```

#### Days 49-50: Performance Validation

**Backtesting** (3 commits, ~250 lines)
```python
# tests/backtest/test_committee_backtest.py

def test_committee_vs_single_agents():
    """Committee outperforms any single agent"""
    # Run all agents individually
    # Run committee
    # Assert: Committee Sharpe > max(individual Sharpes)

def test_agent_correlation():
    """Agents have low correlation (< 0.5)"""
    # Ensures diversification benefit

def test_regime_adaptability():
    """Committee works across all regimes"""
    # Trending, range-bound, high-vol, low-vol
```

### Phase 4 Success Criteria

**Must Pass Before Phase 5**:
1. ✅ All 5 agents operational (Trend, Mean-Rev, Risk, Execution, Arb)
2. ✅ All agents pass 7 EDD soundness categories
3. ✅ Committee aggregation working (weighted voting)
4. ✅ Portfolio metrics:
   - Sharpe Ratio > 2.0 (better than any single agent)
   - Max Drawdown < 10%
   - Agent correlation < 0.5 (diversification)
5. ✅ Paper trading: 48 hours without errors
6. ✅ Test coverage ≥ 90% on all agent code

**Deliverables**:
- 35 atomic commits (updated with Research Agent)
- ~1,390 lines production code (4 trading + 1 research agent + committee)
- ~970 lines test code
- Multi-agent committee ready for Planner layer
- Proven diversification benefit
- 5 tradfi strategies adapted and validated for crypto

**If Any Fail**: Do not proceed to Phase 5. Fix issues first.

---

## Phase 5: Planners & Production Readiness (Weeks 11-12)

**Objective**: Add strategic Planner layer, self-reflection monitoring, and prepare for live trading with $1,000 seed capital.

**Why This Matters**: Final layer adds regime adaptation. System can now adjust strategy based on macro conditions without human intervention.

### Week 11: Planner Layer

#### Days 51-52: Regime Detection

**Implementation** (3 commits, ~300 lines)
```python
# src/coinswarm/planners/regime_detector.py

class RegimeDetector:
    """Detect market regime from multi-source data"""

    async def detect(self, inputs: PlannerInputs) -> Regime:
        """Return current regime tags"""
        # Inputs: sentiment, funding, volatility, correlations

        tags = []

        # Risk sentiment
        if inputs.twitter_sentiment > 0.6:
            tags.append('risk-on')
        elif inputs.twitter_sentiment < 0.4:
            tags.append('risk-off')

        # Trend detection
        if inputs.btc_trend_strength > 0.7:
            tags.append('trending')
        else:
            tags.append('range-bound')

        # Volatility
        if inputs.realized_vol > 0.05:
            tags.append('high-vol')

        return Regime(
            volatility='high' if inputs.realized_vol > 0.05 else 'low',
            trend='up' if inputs.btc_price_change > 0 else 'down',
            tags=tags
        )
```

#### Days 53-54: Planner Implementation

**Implementation** (4 commits, ~450 lines)
```python
# src/coinswarm/planners/planner.py

class Planner:
    """Strategic layer that adjusts committee weights"""

    async def generate_proposal(self) -> PlannerProposal:
        """Propose new committee configuration"""

        # Collect inputs
        inputs = await self.collect_inputs()

        # Detect regime
        regime = self.regime_detector.detect(inputs)

        # Propose weights for this regime
        if 'trending' in regime.tags:
            weights = {
                'trend': 0.50,      # Increase trend-following
                'mean_rev': 0.10,   # Decrease mean-reversion
                'risk': 0.15,
                'execution': 0.15,
                'arbitrage': 0.10
            }
        elif 'range-bound' in regime.tags:
            weights = {
                'trend': 0.10,
                'mean_rev': 0.50,   # Increase mean-reversion
                'risk': 0.15,
                'execution': 0.15,
                'arbitrage': 0.10
            }
        elif 'high-vol' in regime.tags:
            weights = {
                'trend': 0.20,
                'mean_rev': 0.15,
                'risk': 0.40,       # Increase risk management
                'execution': 0.20,
                'arbitrage': 0.05
            }
        else:
            weights = self.default_weights

        # Backtest proposal
        backtest_result = await self.backtest_weights(weights, days=7)

        if backtest_result.sharpe < 1.0:
            return None  # Reject own proposal

        return PlannerProposal(
            committee_weights=weights,
            regime_tags=regime.tags,
            justification={'backtest_sharpe': backtest_result.sharpe}
        )
```

**Tests** (3 commits, ~220 lines): Regime detection, weight proposals, backtest validation

#### Days 55-56: Self-Reflection Layer

**Implementation** (3 commits, ~300 lines)
```python
# src/coinswarm/reflection/monitor.py

class SelfReflectionMonitor:
    """Monitors alignment across all three layers"""

    def check_alignment(self) -> List[str]:
        """Detect misalignment and trigger interventions"""

        issues = []

        # Planner effectiveness
        if self.metrics.backtest_vs_live_gap > 0.5:
            issues.append('planner_overfit')
            self.trigger_planner_reoptimization()

        # Committee coordination
        if self.metrics.vote_entropy > 2.0:
            issues.append('committee_disagreement')

        # Memory-committee alignment
        if self.metrics.memory_hit_rate < 0.3:
            issues.append('memory_mismatch')
            self.refresh_patterns()

        return issues
```

**Tests** (2 commits, ~150 lines): Alignment checks, intervention triggers

### Week 12: Production Hardening

#### Days 57-58: Security & Compliance

**Implementation** (5 commits, ~400 lines)
- API key rotation system
- Encrypted secrets management (AWS Secrets Manager or Vault)
- Rate limiting per exchange
- Audit log encryption
- Position limit enforcement

**Security Audit Checklist**:
- ✅ No API keys in code
- ✅ All secrets encrypted at rest
- ✅ TLS for all external connections
- ✅ Input validation on all user inputs
- ✅ SQL injection prevention (parameterized queries)
- ✅ CSRF protection
- ✅ Audit trail immutable

#### Days 59-60: Monitoring & Alerting

**Grafana Dashboards** (3 commits)
1. **Trading Dashboard**: P&L, positions, win rate, Sharpe
2. **System Health**: CPU, memory, latency, error rates
3. **Data Pipeline**: Ingestion rates, data freshness, API health

**Alerts** (2 commits)
- Critical: Daily loss > 4%, position limit breach, API down > 5min
- Warning: Sharpe drops < 1.0, memory system slow > 10ms P50, data stale > 10min

#### Day 61: Live Trading Preparation

**Final Validation** (1 day)
1. Run full test suite (1000+ tests)
2. 72-hour paper trading stability test
3. Security audit sign-off
4. Load test: 1000 decisions/sec sustained
5. Disaster recovery drill (kill each service, verify recovery)

**Go-Live Checklist**:
- ✅ All tests passing
- ✅ 72-hour paper trading successful
- ✅ Security audit complete
- ✅ Monitoring dashboards operational
- ✅ Alerts tested and working
- ✅ Disaster recovery tested
- ✅ $1,000 seed capital ready
- ✅ Human oversight dashboard ready
- ✅ Emergency stop button implemented

### Phase 5 Success Criteria

**Must Pass Before Live Trading**:
1. ✅ Planner layer operational (adjusting weights hourly)
2. ✅ Self-reflection detecting misalignments
3. ✅ Security audit passed (no critical vulnerabilities)
4. ✅ 72-hour paper trading with Sharpe > 2.0
5. ✅ Monitoring comprehensive (20+ metrics, 15+ alerts)
6. ✅ Disaster recovery tested (all services)
7. ✅ Test coverage ≥ 90% system-wide
8. ✅ Documentation complete (runbooks, architecture, API docs)

**Deliverables**:
- 26 atomic commits
- ~1,450 lines production code (planner + reflection + security)
- ~370 lines test code
- System ready for live trading
- Comprehensive monitoring and alerting
- Security hardened and audited

**Final Checkpoint: LIVE TRADING**:
- Start with $1,000 seed capital
- Max position size: $250 (25% of capital)
- Max daily loss: $50 (5% of capital)
- Human oversight: Review decisions daily
- Emergency stop button accessible
- Gradual capital increase: +$1,000/month if Sharpe > 1.5

---

## Implementation Summary

### Total Effort Breakdown

| Phase | Duration | Commits | Prod Code | Test Code | Key Deliverables |
|-------|----------|---------|-----------|-----------|------------------|
| **Phase 0** | Weeks 1-2 | 59 | 0 | 1,880 | Test coverage 92%, docs complete |
| **Phase 1** | Weeks 3-4 | 37 | 2,510 | 1,535 | Memory system operational |
| **Phase 2** | Weeks 5-6 | 12 | 600 | 560 | First agent (Trend) validated |
| **Phase 3** | Weeks 7-8 | 24 | 1,810 | 650 | Live data pipeline |
| **Phase 4** | Weeks 9-10 | 35 | 1,390 | 970 | Committee + Research Agent |
| **Phase 5** | Weeks 11-12 | 26 | 1,450 | 370 | Production ready |
| **TOTAL** | **12 weeks** | **193** | **7,760** | **5,965** | **Live trading system** |

### Code Distribution

```
Production Code (7,760 lines):
├── Memory System (2,510 lines)   32.4%
│   ├── Redis vector index
│   ├── PostgreSQL models
│   ├── NATS message bus
│   └── Quorum voting
│
├── Agents (1,990 lines)          25.6%
│   ├── Base agent (120)
│   ├── Trend (240)
│   ├── Mean-Rev (220)
│   ├── Risk (200)
│   ├── Execution (180)
│   ├── Arbitrage (160)
│   ├── Research Agent (280) ⭐ NEW
│   ├── Committee (350)
│   └── 5 tradfi strategies (momentum, pairs, stat arb, carry, vol targeting)
│
├── Data Pipeline (1,810 lines)   23.3%
│   ├── 5+ data ingestors
│   ├── Prefect scheduler
│   └── Data distribution clients
│
├── Planners & Reflection (1,450) 18.7%
│   ├── Regime detection
│   ├── Planner proposals
│   ├── Self-reflection
│   └── Security hardening
│
└── Already Implemented (not counted above)
    ├── Config system
    ├── Coinbase client
    ├── MCP server
    └── Binance ingestor
```

### Test Coverage (5,965 lines)

```
Test Code Distribution:
├── Unit Tests (2,200 lines)      36.9%
├── Integration Tests (1,800)     30.2%
├── Soundness Tests (1,150)       19.3%
├── Performance Tests (565)        9.5%
└── Backtest Tests (250)           4.2%
```

### Technology Stack

**Languages & Frameworks**:
- Python 3.11+ (async/await)
- FastAPI (MCP server)
- Pydantic (data validation)

**Databases**:
- Redis (hot memory, sub-2ms latency)
- PostgreSQL (structured data)
- InfluxDB (time-series OHLCV)
- MongoDB (documents, sentiment)

**Message Bus**:
- NATS (pub/sub, request/reply)

**ML & Data**:
- sentence-transformers (embeddings)
- pandas, numpy (data processing)
- scikit-learn (indicators, statistics)

**Infrastructure**:
- Docker & docker-compose
- Prefect (data orchestration)
- Prometheus + Grafana (monitoring)
- GitHub Actions (CI/CD)

**APIs**:
- Coinbase Advanced Trade API
- Binance API
- NewsAPI, Twitter API, Reddit (PRAW)
- Federal Reserve (FRED)

---

## Risk Management & Mitigation

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Redis latency under load** | Medium | High | Benchmark early (Week 3), add replicas, batch queries |
| **NATS network partition** | Low | High | Implement split-brain detection, coordinator failover |
| **Data source API failures** | High | Medium | Buffering, fallback sources, auto-retry with backoff |
| **Memory overfitting** | Medium | High | Quorum voting prevents bad updates, out-of-sample validation |
| **Agent correlation** | Medium | Medium | Backtest correlation < 0.5 requirement, diversified strategies |

### Operational Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Live trading losses** | Medium | Critical | Start with $1K, strict limits (5% daily loss), human oversight |
| **Security breach** | Low | Critical | Security audit, encrypted secrets, no keys in code, TLS |
| **Compliance violation** | Low | High | Audit trail, trade logs, position limits, transparent reasoning |
| **System downtime** | Medium | High | Docker health checks, auto-restart, disaster recovery tested |
| **Data staleness** | Medium | Medium | Alerts on stale data (> 5min), multiple sources for redundancy |

### Timeline Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Phase overruns** | Medium | Medium | Atomic commits (15-30min each), no phase starts until previous passes |
| **Integration bugs** | High | Medium | Extensive integration tests, end-to-end validation each phase |
| **Testing takes longer** | Medium | Low | Test coverage tracked daily, CI/CD catches issues early |
| **External API changes** | Low | Medium | Abstract API clients, version pinning, fallback implementations |

### Safety Protocols

**Emergency Stop**:
1. Redis command: `SET emergency_stop true`
2. All agents check flag every decision cycle
3. If true: liquidate positions, halt trading
4. Alert sent to human operator

**Circuit Breakers**:
- Daily loss > 4%: halt trading for 24 hours
- Sharpe drops < 0.5: reduce position sizes by 50%
- Data stale > 15 min: HOLD only, no new trades
- Memory latency > 50ms P50: disable memory lookup

**Human Oversight**:
- Daily review of trades (10 min)
- Weekly Sharpe/drawdown check (30 min)
- Monthly strategy review (2 hours)
- Quarterly security audit (1 day)

---

## Deployment Strategy

### Environment Setup

**Development** (Local):
```bash
# Docker compose with all services
docker-compose -f docker-compose.dev.yml up -d

Services:
- Redis (port 6379)
- PostgreSQL (port 5432)
- InfluxDB (port 8086)
- MongoDB (port 27017)
- NATS (port 4222)
- Prometheus (port 9090)
- Grafana (port 3000)
```

**Staging** (Cloud - Sandbox APIs):
- AWS EC2 or DigitalOcean Droplet
- Same docker-compose setup
- Connected to exchange sandbox APIs
- Paper trading mode enabled

**Production** (Cloud - Live APIs):
- AWS EC2 with auto-scaling
- Managed databases (RDS PostgreSQL, ElastiCache Redis)
- Load balancer for redundancy
- CloudWatch logs + alarms

### Deployment Process

**Week 12, Day 61-84 (3 weeks post-implementation)**:

1. **Days 61-63**: Staging deployment
   - Deploy to staging environment
   - Run 72-hour paper trading
   - Verify all alerts working
   - Load test: 1000 decisions/sec

2. **Days 64-66**: Security hardening
   - Penetration testing (automated + manual)
   - API key rotation setup
   - Secrets manager integration
   - Audit log encryption

3. **Days 67-69**: Monitoring & alerting validation
   - All Grafana dashboards operational
   - Alert delivery tested (email, Slack, PagerDuty)
   - Runbooks created for each alert
   - On-call rotation established

4. **Days 70-72**: Disaster recovery drills
   - Kill Redis → verify recovery
   - Kill PostgreSQL → verify recovery
   - Kill NATS → verify recovery
   - Network partition simulation

5. **Days 73-75**: Final validation
   - Full regression test suite (1000+ tests)
   - End-to-end paper trading (168 hours continuous)
   - Performance benchmarks met
   - Security audit sign-off

6. **Days 76-77**: Production deployment
   - Deploy to production environment
   - Start with $1,000 seed capital
   - Enable live trading (small positions)
   - Human monitoring 24/7 for first week

7. **Days 78-84**: Gradual ramp-up
   - Week 1: $1K capital, max $250 positions
   - Week 2: If Sharpe > 1.5, add $1K → $2K capital
   - Week 3: If stable, add $1K → $3K capital
   - Week 4+: Continue monthly $1K increases if Sharpe > 1.5

### Infrastructure Requirements

**Minimum (Development)**:
- 8 GB RAM
- 4 CPU cores
- 100 GB SSD

**Recommended (Staging)**:
- 16 GB RAM
- 8 CPU cores
- 500 GB SSD

**Production**:
- 32 GB RAM
- 16 CPU cores
- 1 TB SSD
- Auto-scaling group (2-4 instances)
- Load balancer
- Managed databases

**Estimated Cloud Costs**:
- Development: $0 (local)
- Staging: $100/month
- Production: $500-800/month

### Monitoring & Observability

**Key Metrics**:
1. **Trading**: P&L, Sharpe, win rate, drawdown
2. **System**: CPU, memory, disk, network
3. **Latency**: Memory (P50/P99), decisions, data ingestion
4. **Data**: Freshness, ingestion rate, error rate
5. **Quorum**: Vote counts, consensus rate, proposal latency

**Dashboards**:
1. Executive Dashboard: High-level P&L, Sharpe, positions
2. Trading Dashboard: Per-agent attribution, recent trades
3. System Health: All services, resource utilization
4. Data Pipeline: Ingestion rates, data freshness
5. Memory System: Redis performance, quorum stats

**Alerts** (15 critical, 20 warning):
- Critical: Stop loss, position limit, API down, security breach
- Warning: Sharpe drop, high latency, data stale, low disk space

---

## Conclusion

### What We've Built

After 12 weeks (84 days) of focused development, Coinswarm will be a **production-ready, intelligent trading system** featuring:

✅ **Quorum-Governed Memory**: Byzantine fault-tolerant, self-improving episodic memory
✅ **5-Agent Committee**: Diversified strategies with weighted voting
✅ **Hierarchical Decision System**: Planners (weeks), Committee (seconds), Memory (continuous)
✅ **Live Data Pipeline**: 5+ sources feeding all decision layers
✅ **Evidence-Driven Development**: 1000+ tests across 7 soundness categories
✅ **Production Hardening**: Security audited, monitored, disaster-recovery tested

### Performance Targets

**Trading Performance**:
- Sharpe Ratio > 2.0
- Win Rate > 55%
- Max Drawdown < 10%
- Daily decisions: 50-200
- Zero safety violations

**System Performance**:
- Memory retrieval: < 2ms P50
- Decision latency: < 10ms P50
- Data ingestion: < 100ms P50
- Quorum voting: < 10ms P50
- System uptime: > 99.9%

### Success Criteria

**System is successful if**:
1. ✅ Runs continuously for 30 days without critical errors
2. ✅ Achieves Sharpe > 1.5 in first 90 days
3. ✅ Max drawdown stays < 15% in first 90 days
4. ✅ All agents contribute positively (attribution > 0)
5. ✅ Memory system improves performance over time
6. ✅ Quorum consensus > 95% of proposals

### Next Steps After Phase 5

**Month 4-6** (Post-Launch Optimization):
- Add more agents (momentum, volatility, order-flow)
- Expand to more symbols (ETH, SOL, top 20 cryptos)
- Implement options strategies
- Add pairs trading

**Month 7-12** (Scale & Sophistication):
- Integrate more data sources (on-chain, DeFi)
- Advanced ML models (LSTM, Transformers)
- Cross-exchange arbitrage
- Portfolio optimization

**Year 2+** (Institutional Grade):
- Multi-asset class (crypto + equities + forex)
- Global market expansion (IBKR integration)
- Institutional reporting
- API for external capital

---

**Implementation plan complete. Ready to execute. 🚀**

**Total Document**: ~2,450 lines
**Phases**: 6 (0-5)
**Timeline**: 12 weeks
**Commits**: 193 atomic actions
**Code**: 7,760 production + 5,965 test lines
**Agents**: 5 trading + 1 research (6 total)
**Tradfi Strategies**: 5 (momentum, pairs trading, stat arb, carry, vol targeting)
**From Architecture to Live Trading**: 84 days

---

## Key Innovation: Competitive Learning System

**Phase 1: Pure Organic Learning (Weeks 5-8)**:
- System starts from zero (tabula rasa)
- Episodic memory captures every trade
- Patterns emerge from clustering
- No tradfi bias or preconceptions

**Phase 2: Competition Begins (Week 9+)**:
- Research Agent proposes tradfi strategies
- Organic patterns vs Academic strategies
- Committee weights determined by live performance
- **Best strategies win, regardless of source**

**Validation (Both Types)**:
- Quorum voting (3-vote consensus)
- Backtest requirements (Sharpe > threshold)
- EDD soundness tests (all 7 categories)
- Live performance monitoring

**Outcome**: System empirically learns whether:
- Organic crypto-native patterns outperform academia
- Tradfi strategies successfully adapt to crypto
- Hybrid approach (both) is optimal

**This is true evidence-driven development at the strategy level** 🔬

