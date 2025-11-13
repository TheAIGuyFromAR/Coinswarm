"""
Base classes for soundness testing.

Implements the 7 categories of EDD soundness validation:
1. Determinism
2. Statistical Sanity
3. Safety Invariants
4. Latency & Throughput
5. Economic Realism
6. Memory Stability
7. Consensus Integrity
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import numpy as np

# ============================================================================
# Result Classes
# ============================================================================


@dataclass
class SoundnessResult:
    """Result of a soundness test"""

    passed: bool
    message: str
    metrics: dict[str, Any]
    tolerance_used: float


@dataclass
class BacktestMetrics:
    """Standard backtest metrics"""

    sharpe_ratio: float
    max_drawdown: float
    total_return: float
    volatility: float
    win_rate: float
    avg_trade_duration: float
    turnover: float
    num_trades: int
    final_pnl: float


# ============================================================================
# Category 1: Determinism Tests
# ============================================================================


class DeterminismTest(ABC):
    """
    Base class for determinism tests.

    Ensures same inputs always produce same outputs (no hidden randomness).
    """

    def __init__(self, seed: int = 42):
        self.seed = seed

    @abstractmethod
    def run_target(self, *args, **kwargs) -> Any:
        """
        Run the target function/agent/system.

        Must be implemented by subclass.
        """
        pass

    def test_determinism(
        self, *args, tolerance: float = 1e-10, **kwargs
    ) -> SoundnessResult:
        """
        Test that running twice with same seed produces identical results.

        Args:
            tolerance: Tolerance for floating point comparisons
        """
        # First run
        np.random.seed(self.seed)
        result1 = self.run_target(*args, **kwargs)

        # Second run (reset seed)
        np.random.seed(self.seed)
        result2 = self.run_target(*args, **kwargs)

        # Compare results
        passed, message = self._compare_results(result1, result2, tolerance)

        return SoundnessResult(
            passed=passed,
            message=message,
            metrics={"result1": result1, "result2": result2},
            tolerance_used=tolerance,
        )

    def _compare_results(
        self, result1: Any, result2: Any, tolerance: float
    ) -> tuple[bool, str]:
        """Compare two results for equality"""
        if isinstance(result1, (int, str, bool)):
            if result1 == result2:
                return True, "Results are identical"
            return False, f"Results differ: {result1} != {result2}"

        elif isinstance(result1, float):
            if abs(result1 - result2) <= tolerance:
                return True, f"Results match within tolerance {tolerance}"
            return False, f"Results differ: {result1} vs {result2} (diff: {abs(result1 - result2)})"

        elif isinstance(result1, (list, tuple)):
            if len(result1) != len(result2):
                return False, f"Length mismatch: {len(result1)} vs {len(result2)}"

            for i, (r1, r2) in enumerate(zip(result1, result2, strict=False)):
                passed, msg = self._compare_results(r1, r2, tolerance)
                if not passed:
                    return False, f"Element {i}: {msg}"

            return True, "All elements match"

        elif isinstance(result1, dict):
            if set(result1.keys()) != set(result2.keys()):
                return False, f"Key mismatch: {result1.keys()} vs {result2.keys()}"

            for key in result1.keys():
                passed, msg = self._compare_results(result1[key], result2[key], tolerance)
                if not passed:
                    return False, f"Key '{key}': {msg}"

            return True, "All keys match"

        elif isinstance(result1, np.ndarray):
            if not np.allclose(result1, result2, atol=tolerance):
                return False, f"Arrays differ (max diff: {np.max(np.abs(result1 - result2))})"
            return True, "Arrays match within tolerance"

        else:
            # Fallback to equality
            if result1 == result2:
                return True, "Results are equal"
            return False, f"Results differ: {type(result1).__name__}"


# ============================================================================
# Category 2: Statistical Sanity Tests
# ============================================================================


class StatisticalSanityTest(ABC):
    """
    Base class for statistical sanity tests.

    Verifies metrics (Sharpe, drawdown, turnover) are within realistic bounds.
    """

    def __init__(
        self,
        sharpe_range: tuple[float, float] = (0.5, 3.0),
        max_drawdown: float = 0.20,
        max_turnover: float = 100.0,
        min_trades: int = 10,
    ):
        self.sharpe_range = sharpe_range
        self.max_drawdown = max_drawdown
        self.max_turnover = max_turnover
        self.min_trades = min_trades

    @abstractmethod
    def run_backtest(self) -> BacktestMetrics:
        """
        Run backtest and return metrics.

        Must be implemented by subclass.
        """
        pass

    def test_statistical_sanity(self, tolerance: float = 0.05) -> SoundnessResult:
        """
        Test that backtest metrics are within realistic bounds.

        Args:
            tolerance: Additional tolerance for boundary checks
        """
        metrics = self.run_backtest()

        checks = [
            self._check_sharpe(metrics, tolerance),
            self._check_drawdown(metrics, tolerance),
            self._check_turnover(metrics, tolerance),
            self._check_trade_count(metrics),
        ]

        failed_checks = [check for check in checks if not check[0]]

        if failed_checks:
            messages = [check[1] for check in failed_checks]
            return SoundnessResult(
                passed=False,
                message=f"Failed {len(failed_checks)} checks: {'; '.join(messages)}",
                metrics=vars(metrics),
                tolerance_used=tolerance,
            )

        return SoundnessResult(
            passed=True,
            message="All statistical sanity checks passed",
            metrics=vars(metrics),
            tolerance_used=tolerance,
        )

    def _check_sharpe(
        self, metrics: BacktestMetrics, tolerance: float
    ) -> tuple[bool, str]:
        """Check Sharpe ratio is within realistic bounds"""
        min_sharpe, max_sharpe = self.sharpe_range

        if min_sharpe - tolerance <= metrics.sharpe_ratio <= max_sharpe + tolerance:
            return True, f"Sharpe {metrics.sharpe_ratio:.2f} is realistic"

        return (
            False,
            f"Sharpe {metrics.sharpe_ratio:.2f} outside range [{min_sharpe}, {max_sharpe}]",
        )

    def _check_drawdown(
        self, metrics: BacktestMetrics, tolerance: float
    ) -> tuple[bool, str]:
        """Check max drawdown is acceptable"""
        if metrics.max_drawdown <= self.max_drawdown + tolerance:
            return True, f"Max drawdown {metrics.max_drawdown:.2%} is acceptable"

        return (
            False,
            f"Max drawdown {metrics.max_drawdown:.2%} exceeds limit {self.max_drawdown:.2%}",
        )

    def _check_turnover(
        self, metrics: BacktestMetrics, tolerance: float
    ) -> tuple[bool, str]:
        """Check turnover is not excessive"""
        if metrics.turnover <= self.max_turnover + tolerance:
            return True, f"Turnover {metrics.turnover:.1f} is reasonable"

        return (
            False,
            f"Turnover {metrics.turnover:.1f} exceeds limit {self.max_turnover}",
        )

    def _check_trade_count(self, metrics: BacktestMetrics) -> tuple[bool, str]:
        """Check sufficient trades for statistical validity"""
        if metrics.num_trades >= self.min_trades:
            return True, f"Sufficient trades ({metrics.num_trades})"

        return (
            False,
            f"Insufficient trades ({metrics.num_trades} < {self.min_trades})",
        )


# ============================================================================
# Category 3: Safety Invariant Tests
# ============================================================================


class SafetyInvariantTest(ABC):
    """
    Base class for safety invariant tests.

    Ensures system never violates risk limits, position caps, or loss thresholds.
    """

    def __init__(
        self,
        max_position_size: float = 1000.0,
        max_daily_loss: float = 0.05,
        max_leverage: float = 1.0,
    ):
        self.max_position_size = max_position_size
        self.max_daily_loss = max_daily_loss
        self.max_leverage = max_leverage

    @abstractmethod
    def run_simulation(self) -> list[dict[str, Any]]:
        """
        Run simulation and return list of trades/events.

        Must be implemented by subclass.
        """
        pass

    def test_safety_invariants(self, tolerance: float = 0.01) -> SoundnessResult:
        """
        Test that all trades respect safety constraints.

        Args:
            tolerance: Additional tolerance for limit checks
        """
        events = self.run_simulation()

        violations = []

        for i, event in enumerate(events):
            # Check position size
            if "position_size" in event:
                if event["position_size"] > self.max_position_size * (1 + tolerance):
                    violations.append(
                        f"Event {i}: Position size {event['position_size']} exceeds limit {self.max_position_size}"
                    )

            # Check daily loss
            if "daily_pnl" in event:
                if event["daily_pnl"] < -self.max_daily_loss * (1 + tolerance):
                    violations.append(
                        f"Event {i}: Daily loss {event['daily_pnl']:.2%} exceeds limit {self.max_daily_loss:.2%}"
                    )

            # Check leverage
            if "leverage" in event:
                if event["leverage"] > self.max_leverage * (1 + tolerance):
                    violations.append(
                        f"Event {i}: Leverage {event['leverage']:.2f}x exceeds limit {self.max_leverage}x"
                    )

        if violations:
            return SoundnessResult(
                passed=False,
                message=f"Found {len(violations)} safety violations",
                metrics={"violations": violations, "total_events": len(events)},
                tolerance_used=tolerance,
            )

        return SoundnessResult(
            passed=True,
            message=f"All {len(events)} events respected safety invariants",
            metrics={"total_events": len(events), "violations": 0},
            tolerance_used=tolerance,
        )


# ============================================================================
# Category 4: Latency & Throughput Tests
# ============================================================================


class LatencyTest(ABC):
    """
    Base class for latency tests.

    Ensures p99 timing is within SLA.
    """

    def __init__(self, p99_sla_ms: float = 100.0, num_samples: int = 100):
        self.p99_sla_ms = p99_sla_ms
        self.num_samples = num_samples

    @abstractmethod
    def run_operation(self) -> Any:
        """
        Run the operation to be timed.

        Must be implemented by subclass.
        """
        pass

    def test_latency(self, tolerance: float = 0.1) -> SoundnessResult:
        """
        Test that p99 latency is within SLA.

        Args:
            tolerance: Additional tolerance as fraction of SLA (0.1 = 10%)
        """
        latencies_ms = []

        for _ in range(self.num_samples):
            start = time.perf_counter()
            self.run_operation()
            latencies_ms.append((time.perf_counter() - start) * 1000)

        p50 = np.percentile(latencies_ms, 50)
        p95 = np.percentile(latencies_ms, 95)
        p99 = np.percentile(latencies_ms, 99)
        mean = np.mean(latencies_ms)

        sla_with_tolerance = self.p99_sla_ms * (1 + tolerance)

        passed = p99 <= sla_with_tolerance

        message = (
            f"p50={p50:.2f}ms, p95={p95:.2f}ms, p99={p99:.2f}ms (SLA: {self.p99_sla_ms}ms)"
            if passed
            else f"p99={p99:.2f}ms exceeds SLA {self.p99_sla_ms}ms (with tolerance {sla_with_tolerance:.2f}ms)"
        )

        return SoundnessResult(
            passed=passed,
            message=message,
            metrics={
                "p50_ms": p50,
                "p95_ms": p95,
                "p99_ms": p99,
                "mean_ms": mean,
                "sla_ms": self.p99_sla_ms,
            },
            tolerance_used=tolerance,
        )


class ThroughputTest(ABC):
    """
    Base class for throughput tests.

    Ensures operations per second meets minimum requirement.
    """

    def __init__(self, min_ops_per_sec: float = 100.0, duration_sec: float = 1.0):
        self.min_ops_per_sec = min_ops_per_sec
        self.duration_sec = duration_sec

    @abstractmethod
    def run_operation(self) -> Any:
        """
        Run the operation to be measured.

        Must be implemented by subclass.
        """
        pass

    def test_throughput(self, tolerance: float = 0.1) -> SoundnessResult:
        """
        Test that throughput meets minimum requirement.

        Args:
            tolerance: Additional tolerance as fraction of requirement (0.1 = 10%)
        """
        start = time.perf_counter()
        ops = 0

        while time.perf_counter() - start < self.duration_sec:
            self.run_operation()
            ops += 1

        actual_duration = time.perf_counter() - start
        ops_per_sec = ops / actual_duration

        min_with_tolerance = self.min_ops_per_sec * (1 - tolerance)
        passed = ops_per_sec >= min_with_tolerance

        message = (
            f"Throughput: {ops_per_sec:.1f} ops/sec (min: {self.min_ops_per_sec})"
            if passed
            else f"Throughput {ops_per_sec:.1f} ops/sec below minimum {self.min_ops_per_sec} (with tolerance {min_with_tolerance:.1f})"
        )

        return SoundnessResult(
            passed=passed,
            message=message,
            metrics={
                "ops_per_sec": ops_per_sec,
                "total_ops": ops,
                "duration_sec": actual_duration,
                "min_required": self.min_ops_per_sec,
            },
            tolerance_used=tolerance,
        )


# ============================================================================
# Category 5: Economic Realism Tests
# ============================================================================


class EconomicRealismTest(ABC):
    """
    Base class for economic realism tests.

    Ensures profits aren't due to impossible fills, look-ahead bias, or
    unrealistic assumptions.
    """

    @abstractmethod
    def run_backtest_with_realism(self) -> dict[str, Any]:
        """
        Run backtest with realistic conditions.

        Should return dict with keys:
        - gross_pnl
        - net_pnl
        - slippage_cost
        - fee_cost
        - fill_rate
        """
        pass

    def test_economic_realism(self, tolerance: float = 0.05) -> SoundnessResult:
        """
        Test that backtest includes realistic costs and constraints.

        Args:
            tolerance: Tolerance for realism checks
        """
        results = self.run_backtest_with_realism()

        checks = [
            self._check_costs_applied(results),
            self._check_fill_rate_realistic(results, tolerance),
            self._check_net_less_than_gross(results),
        ]

        failed_checks = [check for check in checks if not check[0]]

        if failed_checks:
            messages = [check[1] for check in failed_checks]
            return SoundnessResult(
                passed=False,
                message=f"Failed realism checks: {'; '.join(messages)}",
                metrics=results,
                tolerance_used=tolerance,
            )

        return SoundnessResult(
            passed=True,
            message="Economic realism checks passed",
            metrics=results,
            tolerance_used=tolerance,
        )

    def _check_costs_applied(self, results: dict[str, Any]) -> tuple[bool, str]:
        """Check that fees and slippage were applied"""
        if results.get("slippage_cost", 0) > 0 or results.get("fee_cost", 0) > 0:
            return True, "Transaction costs applied"

        return False, "No transaction costs applied (unrealistic)"

    def _check_fill_rate_realistic(
        self, results: dict[str, Any], tolerance: float
    ) -> tuple[bool, str]:
        """Check that fill rate is realistic (not 100%)"""
        fill_rate = results.get("fill_rate", 1.0)

        if 0.3 - tolerance <= fill_rate <= 0.95 + tolerance:
            return True, f"Fill rate {fill_rate:.1%} is realistic"

        return False, f"Fill rate {fill_rate:.1%} is unrealistic"

    def _check_net_less_than_gross(
        self, results: dict[str, Any]
    ) -> tuple[bool, str]:
        """Check that net P&L < gross P&L (costs reduce profit)"""
        gross = results.get("gross_pnl", 0)
        net = results.get("net_pnl", 0)

        if net < gross:
            return True, "Net P&L < Gross P&L (costs applied correctly)"

        return False, f"Net P&L ({net}) >= Gross P&L ({gross}) - costs not applied?"


# ============================================================================
# Category 6: Memory Stability Tests
# ============================================================================


class MemoryStabilityTest(ABC):
    """
    Base class for memory stability tests.

    Ensures pattern statistics converge and weights don't oscillate.
    """

    @abstractmethod
    def run_memory_simulation(self, num_iterations: int) -> dict[str, list[float]]:
        """
        Run memory system simulation.

        Should return dict with time series:
        - weights: List of weight values over time
        - statistics: List of pattern statistics over time
        """
        pass

    def test_memory_stability(
        self, num_iterations: int = 1000, tolerance: float = 0.1
    ) -> SoundnessResult:
        """
        Test that memory statistics converge and weights are stable.

        Args:
            num_iterations: Number of simulation steps
            tolerance: Maximum acceptable coefficient of variation in recent window
        """
        results = self.run_memory_simulation(num_iterations)

        weights = results.get("weights", [])
        statistics = results.get("statistics", [])

        checks = [
            self._check_convergence(statistics, tolerance),
            self._check_no_oscillation(weights, tolerance),
        ]

        failed_checks = [check for check in checks if not check[0]]

        if failed_checks:
            messages = [check[1] for check in failed_checks]
            return SoundnessResult(
                passed=False,
                message=f"Memory stability issues: {'; '.join(messages)}",
                metrics={"weights_std": np.std(weights[-100:]), "num_iterations": num_iterations},
                tolerance_used=tolerance,
            )

        return SoundnessResult(
            passed=True,
            message="Memory is stable and convergent",
            metrics={"weights_std": np.std(weights[-100:]), "num_iterations": num_iterations},
            tolerance_used=tolerance,
        )

    def _check_convergence(
        self, statistics: list[float], tolerance: float
    ) -> tuple[bool, str]:
        """Check that statistics converge (low recent variance)"""
        if len(statistics) < 100:
            return True, "Insufficient data for convergence check"

        recent_window = statistics[-100:]
        cv = np.std(recent_window) / (abs(np.mean(recent_window)) + 1e-8)

        if cv <= tolerance:
            return True, f"Statistics converged (CV={cv:.3f})"

        return False, f"Statistics not converged (CV={cv:.3f} > {tolerance})"

    def _check_no_oscillation(
        self, weights: list[float], tolerance: float
    ) -> tuple[bool, str]:
        """Check that weights don't oscillate wildly"""
        if len(weights) < 20:
            return True, "Insufficient data for oscillation check"

        recent_window = weights[-20:]
        std = np.std(recent_window)

        if std <= tolerance:
            return True, f"Weights stable (std={std:.3f})"

        return False, f"Weights oscillating (std={std:.3f} > {tolerance})"


# ============================================================================
# Category 7: Consensus Integrity Tests
# ============================================================================


class ConsensusIntegrityTest(ABC):
    """
    Base class for consensus integrity tests.

    Verifies quorum commits match ≥3 identical votes; no split-brain scenarios.
    """

    @abstractmethod
    def run_consensus_protocol(
        self, num_managers: int, num_proposals: int
    ) -> list[dict[str, Any]]:
        """
        Run consensus protocol simulation.

        Should return list of proposal outcomes with keys:
        - proposal_id
        - votes: List of (manager_id, decision, vote_hash)
        - committed: bool
        """
        pass

    def test_consensus_integrity(
        self, num_managers: int = 3, num_proposals: int = 100, quorum_size: int = 3
    ) -> SoundnessResult:
        """
        Test that consensus protocol maintains integrity.

        Args:
            num_managers: Number of memory managers
            num_proposals: Number of proposals to test
            quorum_size: Minimum votes required for commit
        """
        outcomes = self.run_consensus_protocol(num_managers, num_proposals)

        violations = []

        for outcome in outcomes:
            # Check vote consistency
            votes = outcome.get("votes", [])
            vote_hashes = [v[2] for v in votes]  # (manager, decision, hash)

            # All votes for same proposal should have same hash
            if len(set(vote_hashes)) > 1:
                violations.append(
                    f"Proposal {outcome['proposal_id']}: Inconsistent vote hashes"
                )

            # Check quorum requirement
            accept_votes = sum(1 for v in votes if v[1] == "ACCEPT")

            if outcome.get("committed", False):
                if accept_votes < quorum_size:
                    violations.append(
                        f"Proposal {outcome['proposal_id']}: Committed with only {accept_votes} votes (requires {quorum_size})"
                    )

        if violations:
            return SoundnessResult(
                passed=False,
                message=f"Consensus violations: {violations[:5]}",  # Show first 5
                metrics={"total_violations": len(violations), "total_proposals": num_proposals},
                tolerance_used=0.0,
            )

        return SoundnessResult(
            passed=True,
            message=f"All {num_proposals} proposals maintained consensus integrity",
            metrics={"total_proposals": num_proposals, "violations": 0},
            tolerance_used=0.0,
        )
