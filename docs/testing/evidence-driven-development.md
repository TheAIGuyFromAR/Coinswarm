# Evidence-Driven Development (EDD) Testing Strategy

**Status:** ⭐⭐⭐ CORE DEVELOPMENT DISCIPLINE
**Version:** 1.0
**Last Updated:** 2025-10-31

## Overview

Coinswarm uses **Evidence-Driven Development (EDD)** - an evolution of Test-Driven Development (TDD) that adds validation of economic soundness and behavioral stability to the traditional red-green-refactor loop.

**Key Principle:** Every commit must pass both **functional tests** (does it work?) AND **soundness tests** (is it economically rational, stable, and safe?).

---

## Table of Contents

1. [Concept: TDD → EDD](#concept-tdd--edd)
2. [The EDD Loop](#the-edd-loop)
3. [Seven Categories of Soundness](#seven-categories-of-soundness)
4. [Testing Hierarchy](#testing-hierarchy)
5. [CI/CD Pipeline](#cicd-pipeline)
6. [Phase-by-Phase Testing Discipline](#phase-by-phase-testing-discipline)
7. [Continuous Validation](#continuous-validation)
8. [Implementation Guide](#implementation-guide)

---

## Concept: TDD → EDD

### TDD Focus vs EDD Focus

| Stage | TDD Focus | EDD / AI-Agent Focus |
|-------|-----------|---------------------|
| **Red** | Write a failing unit test for one behavior | Define an expected observable outcome or metric (P&L change, latency bound, memory-update validity) that currently fails |
| **Green** | Write code to pass it | Implement minimal logic, agent, or connector to meet that metric |
| **Refactor** | Clean code while keeping tests green | Improve algorithm, then re-run deterministic replay and statistical soundness tests |
| **Evidence** | – | Add validation that the behavior is economically rational, stable under noise, and reproducible |

### Why EDD for Trading Systems?

Traditional TDD ensures **functional correctness** but doesn't validate:
- Economic rationality (not gaming the test data)
- Behavioral stability (works under noise and regime shifts)
- Safety guarantees (position limits, loss limits)
- Performance bounds (latency, throughput)
- Consensus integrity (distributed system correctness)

**EDD adds a higher-order validation loop** that measures soundness: no overfit, no rule violations, consistent across seeds.

---

## The EDD Loop

### Expanded Development Cycle

```
1. Define behavior test (TDD)
   ↓
2. Implement minimal logic to pass
   ↓
3. Validate against soundness metrics (EDD)
   ↓
4. Refactor / simplify
   ↓
5. Commit once BOTH functional AND soundness tests pass
```

### Example: Adding a Trend-Following Agent

#### 1. Red (Define Expected Outcome)

```python
# tests/unit/agents/test_trend_agent.py
def test_trend_agent_buys_on_golden_cross():
    """Agent should buy when fast MA crosses above slow MA"""
    agent = TrendAgent(fast_period=10, slow_period=20)

    # Create synthetic data with golden cross
    prices = create_golden_cross_scenario()

    action = agent.decide(prices)

    assert action.type == ActionType.BUY
    assert action.confidence > 0.6
    assert action.size <= agent.max_position_size
```

#### 2. Green (Minimal Implementation)

```python
class TrendAgent:
    def decide(self, prices):
        fast_ma = prices[-10:].mean()
        slow_ma = prices[-20:].mean()

        if fast_ma > slow_ma:
            return Action(type=ActionType.BUY, confidence=0.7, size=100)
        return Action(type=ActionType.HOLD, confidence=0.5, size=0)
```

#### 3. Evidence (Soundness Validation)

```python
# tests/soundness/test_trend_agent_soundness.py
def test_trend_agent_determinism():
    """Same inputs → same outputs (no hidden randomness)"""
    agent = TrendAgent(fast_period=10, slow_period=20, seed=42)
    prices = load_fixture("golden_cross.csv")

    action1 = agent.decide(prices)
    action2 = agent.decide(prices)

    assert action1 == action2  # Deterministic

def test_trend_agent_statistical_sanity():
    """Backtest on out-of-sample data shows reasonable metrics"""
    agent = TrendAgent(fast_period=10, slow_period=20)
    backtest = run_backtest(agent, dataset="test_2024_Q1")

    assert 0.5 <= backtest.sharpe_ratio <= 3.0  # Realistic Sharpe
    assert backtest.max_drawdown <= 0.15  # Max 15% drawdown
    assert backtest.turnover <= 50  # Not overtrading

def test_trend_agent_safety_invariants():
    """Agent never violates position or loss limits"""
    agent = TrendAgent(fast_period=10, slow_period=20)
    backtest = run_backtest(agent, dataset="test_2024_Q1")

    for trade in backtest.trades:
        assert trade.size <= agent.max_position_size
        assert trade.loss <= agent.max_loss_per_trade
```

#### 4. Refactor

Improve the algorithm (add regime detection, dynamic sizing) while keeping all tests green.

#### 5. Commit

Only commit when **both** functional and soundness tests pass.

---

## Seven Categories of Soundness

### 1. Determinism Tests

**Purpose:** Ensure no hidden randomness - same inputs always produce same outputs.

**Examples:**
```python
def test_agent_determinism(agent_class):
    """Agent produces identical results on replay"""
    agent = agent_class(seed=42)
    data = load_fixture("btc_2024_jan.csv")

    run1 = simulate(agent, data)
    run2 = simulate(agent, data)

    assert run1.actions == run2.actions
    assert run1.final_pnl == run2.final_pnl

def test_memory_determinism():
    """Memory retrieval is deterministic"""
    memory = EpisodicMemory(seed=42)
    state = np.random.rand(384)

    neighbors1 = memory.knn(state, k=10)
    neighbors2 = memory.knn(state, k=10)

    assert neighbors1 == neighbors2
```

**Critical for:** Reproducible research, debugging, compliance audits.

---

### 2. Statistical Sanity Tests

**Purpose:** Verify metrics (Sharpe, drawdown, turnover) are within realistic bounds on out-of-sample data.

**Examples:**
```python
def test_strategy_sharpe_ratio():
    """Sharpe ratio is realistic (not overfitted)"""
    strategy = load_strategy("trend_following_v1")
    backtest = run_backtest(strategy, dataset="oos_2024")

    assert 0.5 <= backtest.sharpe_ratio <= 3.0
    assert backtest.sharpe_ratio >= backtest.train_sharpe * 0.6  # Max 40% decay

def test_strategy_drawdown():
    """Max drawdown is acceptable"""
    strategy = load_strategy("trend_following_v1")
    backtest = run_backtest(strategy, dataset="oos_2024")

    assert backtest.max_drawdown <= 0.20  # Max 20%
    assert backtest.avg_drawdown <= 0.10  # Avg 10%

def test_strategy_turnover():
    """Trading frequency is realistic"""
    strategy = load_strategy("trend_following_v1")
    backtest = run_backtest(strategy, dataset="oos_2024")

    assert backtest.turnover <= 100  # Not overtrading
    assert backtest.avg_holding_period >= timedelta(hours=1)
```

**Critical for:** Avoiding overfitting, ensuring economic viability.

---

### 3. Safety Invariant Tests

**Purpose:** Guarantee system never violates risk limits, position caps, or loss thresholds.

**Examples:**
```python
def test_position_size_limits():
    """No trade exceeds max position size"""
    agent = TradingAgent()
    backtest = run_backtest(agent, dataset="stress_test_high_vol")

    for trade in backtest.trades:
        assert trade.size <= settings.trading.max_position_size_pct / 100 * backtest.portfolio_value
        assert trade.value <= settings.trading.max_order_value

def test_daily_loss_limit():
    """Daily loss never exceeds limit"""
    agent = TradingAgent()
    backtest = run_backtest(agent, dataset="stress_test_drawdown")

    daily_pnl = backtest.group_by_day()

    for day, pnl in daily_pnl.items():
        assert pnl >= -settings.trading.max_daily_loss_pct / 100 * backtest.starting_capital

def test_max_drawdown_circuit_breaker():
    """System halts when max drawdown exceeded"""
    agent = TradingAgent()
    backtest = run_backtest(agent, dataset="stress_test_crash")

    if backtest.max_drawdown >= settings.trading.max_drawdown_pct / 100:
        assert backtest.halted == True
        assert backtest.halt_reason == "MAX_DRAWDOWN_EXCEEDED"
```

**Critical for:** Risk management, regulatory compliance, capital preservation.

---

### 4. Latency & Throughput Tests

**Purpose:** Ensure system meets performance SLAs (99th percentile timing within spec).

**Examples:**
```python
def test_order_placement_latency():
    """Order placement completes within SLA"""
    client = CoinbaseAPIClient()

    latencies = []
    for _ in range(100):
        start = time.perf_counter()
        await client.create_market_order("BTC-USD", OrderSide.BUY, quote_size="10")
        latencies.append(time.perf_counter() - start)

    assert np.percentile(latencies, 99) <= 0.100  # p99 < 100ms

def test_memory_retrieval_latency():
    """kNN memory lookup completes within budget"""
    memory = EpisodicMemory()
    state = np.random.rand(384)

    latencies = []
    for _ in range(1000):
        start = time.perf_counter()
        neighbors = memory.knn(state, k=16)
        latencies.append(time.perf_counter() - start)

    assert np.percentile(latencies, 99) <= 0.005  # p99 < 5ms

def test_decision_throughput():
    """Agent can process minimum required decisions per second"""
    agent = CommitteeAgent()

    start = time.perf_counter()
    for _ in range(1000):
        state = generate_market_state()
        decision = agent.decide(state)
    duration = time.perf_counter() - start

    throughput = 1000 / duration
    assert throughput >= 100  # At least 100 decisions/sec
```

**Critical for:** High-frequency trading, real-time execution, scalability.

---

### 5. Economic Realism Tests

**Purpose:** Verify profits aren't due to impossible fills, look-ahead bias, or unrealistic assumptions.

**Examples:**
```python
def test_no_lookahead_bias():
    """Agent only uses data available at decision time"""
    agent = TrendAgent()

    # Inject future data and verify agent doesn't use it
    past_data = load_fixture("btc_jan_1_to_15.csv")
    future_data = load_fixture("btc_jan_16_to_31.csv")

    decision = agent.decide(past_data)

    # Agent's internal state should not contain future data
    assert not agent._uses_future_data(future_data)

def test_realistic_slippage():
    """Backtest includes realistic slippage model"""
    strategy = load_strategy("mean_reversion")
    backtest = run_backtest(
        strategy,
        dataset="oos_2024",
        slippage_model="historical_knn"  # Uses actual historical slippage
    )

    assert backtest.avg_slippage_bps >= 2.0  # At least 2bps
    assert backtest.slippage_cost > 0

def test_fill_rate_realism():
    """Limit orders have realistic fill rates"""
    strategy = load_strategy("limit_order_strategy")
    backtest = run_backtest(strategy, dataset="oos_2024")

    assert 0.3 <= backtest.fill_rate <= 0.9  # 30-90% fill rate
    assert backtest.unfilled_orders > 0  # Some orders don't fill

def test_transaction_costs():
    """Backtest includes fees and spreads"""
    strategy = load_strategy("hft_strategy")
    backtest = run_backtest(strategy, dataset="oos_2024")

    assert backtest.total_fees > 0
    assert backtest.gross_pnl > backtest.net_pnl  # Fees reduce profit
```

**Critical for:** Realistic performance expectations, avoiding paper trading bias.

---

### 6. Memory Stability Tests

**Purpose:** Ensure pattern statistics converge and weights don't oscillate.

**Examples:**
```python
def test_pattern_convergence():
    """Pattern statistics stabilize after sufficient observations"""
    memory = PatternMemory()

    # Record 1000 trades with same pattern
    for _ in range(1000):
        outcome = simulate_trade(pattern="breakout_v1")
        memory.record(outcome)

    # Stats should converge (low variance in recent window)
    stats_500 = memory.get_stats("breakout_v1", as_of=500)
    stats_1000 = memory.get_stats("breakout_v1", as_of=1000)

    assert abs(stats_500.sharpe - stats_1000.sharpe) <= 0.2

def test_weight_stability():
    """Memory weights don't oscillate wildly"""
    memory = EpisodicMemory()

    # Record sequence of trades
    for t in range(100):
        outcome = simulate_trade()
        memory.update_weights(outcome)

    weights = memory.get_weight_history()

    # Check variance is low (no oscillation)
    assert np.std(weights[-20:]) <= 0.1

def test_credit_assignment_sanity():
    """Credit assignment produces reasonable weight updates"""
    memory = EpisodicMemory()

    # Record a winning trade
    outcome = TradeOutcome(pnl=100, expected_pnl=50)

    neighbors_before = memory.get_neighbors()
    memory.update_weights(outcome)
    neighbors_after = memory.get_neighbors()

    # Weights should increase (positive surprise)
    for nb_before, nb_after in zip(neighbors_before, neighbors_after):
        assert nb_after.weight >= nb_before.weight
```

**Critical for:** Learning stability, avoiding runaway feedback loops.

---

### 7. Consensus Integrity Tests

**Purpose:** Verify quorum commits match ≥3 identical votes; no split-brain scenarios.

**Examples:**
```python
def test_quorum_consensus():
    """Memory update requires ≥3 identical votes"""
    managers = [MemoryManager(id=i) for i in range(3)]
    proposal = MemoryProposal(pattern_id="p1", update={"sharpe": 1.5})

    votes = [mgr.vote(proposal) for mgr in managers]

    # All managers should produce identical votes
    assert all(v.decision == votes[0].decision for v in votes)
    assert all(v.vote_hash == votes[0].vote_hash for v in votes)

    # Commit only if ≥3 accept
    if sum(v.decision == "ACCEPT" for v in votes) >= 3:
        commit = commit_proposal(proposal, votes)
        assert commit.committed == True

def test_no_split_brain():
    """Network partition doesn't cause divergent state"""
    cluster = MemoryCluster(managers=5)

    # Simulate network partition
    partition_a = cluster.managers[:2]
    partition_b = cluster.managers[2:]

    # Both partitions try to commit
    proposal_a = MemoryProposal(pattern_id="p1", update={"sharpe": 1.5})
    proposal_b = MemoryProposal(pattern_id="p1", update={"sharpe": 1.8})

    result_a = partition_a.try_commit(proposal_a)
    result_b = partition_b.try_commit(proposal_b)

    # Only partition with ≥3 nodes should succeed
    assert result_a.committed == False  # Only 2 nodes
    assert result_b.committed == True   # 3 nodes

    # Heal partition
    cluster.heal()

    # All nodes should converge to same state
    assert all(mgr.get_pattern("p1").sharpe == 1.8 for mgr in cluster.managers)

def test_deterministic_replay():
    """Replaying same events produces same state"""
    cluster1 = MemoryCluster(managers=3, seed=42)
    cluster2 = MemoryCluster(managers=3, seed=42)

    events = load_fixture("events_2024_jan.json")

    for event in events:
        cluster1.process(event)
        cluster2.process(event)

    # Final states should be identical
    assert cluster1.state_hash() == cluster2.state_hash()
```

**Critical for:** Distributed system correctness, Byzantine fault tolerance.

---

## Testing Hierarchy

### Test Organization

```
tests/
├── unit/                      # Fast, isolated tests (< 1s each)
│   ├── test_coinbase_client.py
│   ├── test_config.py
│   ├── agents/
│   │   ├── test_trend_agent.py
│   │   └── test_committee.py
│   └── memory/
│       ├── test_episodic.py
│       └── test_quorum.py
│
├── integration/               # Multi-component tests (< 10s each)
│   ├── test_order_flow.py
│   ├── test_data_pipeline.py
│   └── test_mcp_server.py
│
├── performance/               # Latency and throughput tests
│   ├── test_order_latency.py
│   ├── test_memory_latency.py
│   └── test_decision_throughput.py
│
├── soundness/                 # Economic validation (can be slow)
│   ├── test_determinism.py
│   ├── test_statistical_sanity.py
│   ├── test_safety_invariants.py
│   ├── test_economic_realism.py
│   ├── test_memory_stability.py
│   └── test_consensus_integrity.py
│
├── backtest/                  # Full strategy backtests
│   ├── test_trend_strategy.py
│   ├── test_mean_reversion.py
│   └── test_committee_ensemble.py
│
└── fixtures/                  # Test data
    ├── market_data/
    │   ├── btc_2024_jan.csv
    │   └── golden_cross.csv
    ├── events/
    │   └── events_2024_jan.json
    └── snapshots/
        └── memory_state_jan_31.pkl
```

### Test Execution Order

1. **Unit tests** (fast, isolated) - verify individual components
2. **Integration tests** (multi-component) - verify interactions
3. **Performance tests** (latency/throughput) - verify SLAs
4. **Soundness tests** (economic validation) - verify rationality
5. **Backtest tests** (full strategy) - verify end-to-end

---

## CI/CD Pipeline

### Pipeline Stages

```yaml
# .github/workflows/ci.yml

name: Coinswarm CI/CD

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e ".[dev,test]"

      - name: Lint
        run: |
          ruff check src/ tests/
          mypy src/

      - name: Stage 1 - Unit Tests
        run: |
          pytest tests/unit/ -v --cov=src/coinswarm --cov-report=xml
        continue-on-error: false

      - name: Stage 2 - Integration Tests
        run: |
          pytest tests/integration/ -v
        continue-on-error: false

      - name: Stage 3 - Performance Tests
        run: |
          pytest tests/performance/ -v
        continue-on-error: false

      - name: Stage 4 - Soundness Tests
        run: |
          pytest tests/soundness/ -v
        continue-on-error: false

      - name: Stage 5 - Backtest Validation
        run: |
          python -m coinswarm.backtest.runner \
            --dataset fixtures/testset \
            --report reports/test.json
        continue-on-error: false

      - name: Validate Results
        run: |
          python scripts/validate_backtest.py reports/test.json

      - name: Upload Coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

### Commit Blocking Rules

A commit is **blocked** if:
- Any unit test fails
- Any integration test fails
- Any performance test exceeds SLA
- Any soundness test fails
- Backtest Sharpe < baseline - tolerance
- Coverage decreases

### Continuous Validation

**Nightly Jobs:**
```yaml
# .github/workflows/nightly.yml

name: Nightly Validation

on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM daily

jobs:
  full-validation:
    runs-on: ubuntu-latest

    steps:
      - name: Run full test suite on latest data
        run: |
          pytest tests/ -v --full

      - name: Compare live metrics vs baseline
        run: |
          python scripts/compare_metrics.py \
            --live metrics/live_latest.json \
            --baseline metrics/baseline.json \
            --tolerance 0.1

      - name: Flag drift
        if: failure()
        run: |
          python scripts/alert_drift.py \
            --channel slack \
            --severity high
```

---

## Phase-by-Phase Testing Discipline

### Phase 0-1: Connectors

**TDD:**
```python
def test_connector_returns_identical_ohlcv():
    """Connector returns same OHLCV for given timestamp range"""
    connector = BinanceConnector()

    data1 = connector.get_ohlcv("BTC-USD", start, end)
    data2 = connector.get_ohlcv("BTC-USD", start, end)

    assert data1 == data2
```

**EDD:**
```python
def test_connector_latency_sla():
    """Connector latency distribution < target"""
    connector = BinanceConnector()

    latencies = []
    for _ in range(100):
        start_time = time.perf_counter()
        data = connector.get_ohlcv("BTC-USD", start, end)
        latencies.append(time.perf_counter() - start_time)

    assert np.percentile(latencies, 99) <= 0.100  # p99 < 100ms
```

---

### Phase 3: Single Agent

**TDD:**
```python
def test_agent_buys_on_signal():
    """Agent issues buy when fastMA > slowMA + ε"""
    agent = TrendAgent(fast=10, slow=20)

    prices = create_bullish_crossover()
    action = agent.decide(prices)

    assert action.type == ActionType.BUY
```

**EDD:**
```python
def test_agent_position_cap():
    """Agent never breaches position cap"""
    agent = TrendAgent(fast=10, slow=20)
    backtest = run_backtest(agent, dataset="stress_test")

    for trade in backtest.trades:
        assert trade.size <= agent.max_position_size
```

---

### Phase 4: Memory System

**TDD:**
```python
def test_knn_returns_top_k():
    """kNN recall returns top-K cosine-nearest neighbors"""
    memory = EpisodicMemory()

    # Add 100 episodes
    for _ in range(100):
        memory.add(create_episode())

    query = np.random.rand(384)
    neighbors = memory.knn(query, k=10)

    assert len(neighbors) == 10
    assert all(n.similarity >= neighbors[-1].similarity for n in neighbors)
```

**EDD:**
```python
def test_memory_deterministic_pnl_improvement():
    """Simulate replay; verify deterministic PnL improvement within tolerance"""
    memory = EpisodicMemory(seed=42)

    baseline_pnl = run_backtest_without_memory(dataset="test")
    memory_pnl = run_backtest_with_memory(memory, dataset="test")

    # Deterministic improvement
    assert memory_pnl >= baseline_pnl

    # Repeatable
    memory_pnl_2 = run_backtest_with_memory(memory, dataset="test", seed=42)
    assert abs(memory_pnl - memory_pnl_2) < 0.01
```

---

### Phase 6: MCP Modularization

**TDD:**
```python
def test_message_schema_contract():
    """Producer and consumer share schema hash"""
    producer = MCPProducer()
    consumer = MCPConsumer()

    message = producer.create_message(data={"price": 50000})

    assert consumer.validate_schema(message) == True
```

**EDD:**
```python
def test_chaos_container_restart():
    """Restart one container → no data loss"""
    cluster = MCPCluster()

    # Send 1000 messages
    for i in range(1000):
        cluster.send(f"message_{i}")

    # Restart container
    cluster.restart_container("mcp-server-1")

    # All messages should be processed
    assert cluster.processed_count() == 1000
```

---

### Phase 8: Committee/Quorum

**TDD:**
```python
def test_quorum_requires_three_votes():
    """No commit without ≥3 identical votes"""
    quorum = Quorum(size=3)
    proposal = create_proposal()

    votes = [
        Vote(manager=1, decision="ACCEPT"),
        Vote(manager=2, decision="ACCEPT"),
        Vote(manager=3, decision="REJECT"),
    ]

    result = quorum.commit(proposal, votes)

    assert result.committed == False  # Only 2 accept votes
```

**EDD:**
```python
def test_quorum_replay_determinism():
    """Replay with identical data → identical memory state hash"""
    quorum1 = Quorum(size=3, seed=42)
    quorum2 = Quorum(size=3, seed=42)

    events = load_fixture("events_2024_jan.json")

    for event in events:
        quorum1.process(event)
        quorum2.process(event)

    assert quorum1.state_hash() == quorum2.state_hash()
```

---

## Implementation Guide

### 1. Set Up Test Structure

```bash
# Create test directories
mkdir -p tests/{unit,integration,performance,soundness,backtest,fixtures}

# Create fixture directories
mkdir -p tests/fixtures/{market_data,events,snapshots}
```

### 2. Add Soundness Test Base Classes

Create `tests/soundness/base.py`:

```python
from abc import ABC, abstractmethod
import numpy as np

class SoundnessTest(ABC):
    """Base class for soundness tests"""

    @abstractmethod
    def test_passes(self) -> bool:
        """Return True if soundness test passes"""
        pass

    def assert_soundness(self, tolerance=0.05):
        """Assert that test passes within tolerance"""
        assert self.test_passes(), f"Soundness test failed: {self.__class__.__name__}"

class DeterminismTest(SoundnessTest):
    """Base class for determinism tests"""

    def run_twice(self, func, *args, seed=42, **kwargs):
        """Run function twice with same seed"""
        np.random.seed(seed)
        result1 = func(*args, **kwargs)

        np.random.seed(seed)
        result2 = func(*args, **kwargs)

        return result1, result2

    def test_passes(self) -> bool:
        result1, result2 = self.run_twice(self.target_function)
        return result1 == result2

class StatisticalSanityTest(SoundnessTest):
    """Base class for statistical sanity tests"""

    def __init__(self, sharpe_range=(0.5, 3.0), dd_max=0.20):
        self.sharpe_range = sharpe_range
        self.dd_max = dd_max

    def test_passes(self) -> bool:
        backtest = self.run_backtest()

        sharpe_ok = self.sharpe_range[0] <= backtest.sharpe <= self.sharpe_range[1]
        dd_ok = backtest.max_drawdown <= self.dd_max

        return sharpe_ok and dd_ok
```

### 3. Write Your First EDD Test

```python
# tests/soundness/test_trend_agent_soundness.py

from tests.soundness.base import DeterminismTest, StatisticalSanityTest

class TestTrendAgentDeterminism(DeterminismTest):
    def target_function(self):
        agent = TrendAgent(fast=10, slow=20, seed=42)
        data = load_fixture("btc_2024_jan.csv")
        return run_simulation(agent, data)

class TestTrendAgentStatistics(StatisticalSanityTest):
    def run_backtest(self):
        agent = TrendAgent(fast=10, slow=20)
        return run_backtest(agent, dataset="oos_2024")

# Run tests
if __name__ == "__main__":
    test_det = TestTrendAgentDeterminism()
    test_det.assert_soundness()

    test_stats = TestTrendAgentStatistics()
    test_stats.assert_soundness()
```

### 4. Update CI Configuration

Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "unit: Unit tests (fast)",
    "integration: Integration tests",
    "performance: Performance and latency tests",
    "soundness: Economic soundness tests",
    "slow: Slow-running tests",
]
```

Run tests by category:

```bash
pytest tests/unit/ -m unit
pytest tests/soundness/ -m soundness
pytest tests/performance/ -m performance
```

---

## Summary

**EDD = TDD + Economic Validation**

Every commit must demonstrate:
1. **Functional correctness** (passes unit/integration tests)
2. **Performance compliance** (meets latency/throughput SLAs)
3. **Economic soundness** (deterministic, statistically sane, safe)
4. **Behavioral stability** (no oscillation, convergence)
5. **System integrity** (consensus, no split-brain)

**Result:** A provably stable, economically valid development pipeline where every commit is a verified improvement, not just a passing feature.

---

**Next Steps:**
1. Implement soundness test base classes
2. Create test fixtures and datasets
3. Write soundness tests for existing components (Coinbase client, config)
4. Set up GitHub Actions CI/CD pipeline
5. Add nightly validation jobs
6. Establish performance baselines
