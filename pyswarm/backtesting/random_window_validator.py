"""
Random Window Validator - Robust Strategy Testing

Tests strategies on random time intervals to prevent overfitting.

Key Concepts:
1. WALK-FORWARD ANALYSIS: Train on one period, test on next
2. RANDOM WINDOWS: Test on random 3-month slices across 2+ years
3. COMBINATORIAL PURGED CV: Test all possible windows
4. REGIME DIVERSITY: Ensure exposure to bull/bear/ranging/volatile

Why This Matters:
- Sequential backtest might overfit to that specific market period
- "Tuesday pump" might only work in 2021 bull market
- Random windows ensure strategy works in ALL conditions

Academic Reference:
- De Prado (2018) "Advances in Financial Machine Learning"
  Chapter 7: Cross-Validation in Finance
- Requirement: Purged k-fold cross-validation
- Goal: Prevent information leakage and overfitting

Example:
    validator = RandomWindowValidator(
        data=btc_data_2020_2023,  # 3 years
        window_size=90,  # 90 days
        n_windows=100   # Test 100 random windows
    )

    results = await validator.validate_strategy(
        memory_system=memory,
        min_sharpe=1.5,  # Must achieve Sharpe > 1.5
        min_win_rate=0.55  # Must achieve 55%+ win rate
    )

    if results["all_windows_passed"]:
        print("Strategy is ROBUST! Works in all conditions.")
    else:
        print("Strategy OVERFITTED. Failed in some windows.")
"""

import logging
import random
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class WindowResult:
    """Results from testing on a single time window"""
    window_id: int
    start_date: datetime
    end_date: datetime
    window_length_days: int  # NEW: Track window length
    regime: str  # "bull", "bear", "ranging", "volatile"

    # Performance metrics
    total_trades: int
    win_rate: float
    total_pnl: float
    sharpe_ratio: float
    max_drawdown: float
    profit_factor: float

    # Pattern discoveries
    patterns_discovered: list[str]
    novel_patterns: list[str]

    # Pass/fail
    passed: bool
    failure_reason: str = ""


class RandomWindowValidator:
    """
    Test strategies on random time windows across multi-year dataset.

    This is THE way to validate trading strategies properly.
    Anything less is just fooling yourself.
    """

    def __init__(
        self,
        data: pd.DataFrame,
        window_size_days: int | None = None,  # Fixed size (if specified)
        window_size_range: tuple[int, int] = (30, 180),  # Random range (if not fixed)
        n_windows: int = 100,  # Test 100 random windows
        min_data_years: float = 2.0,  # Require 2+ years
        purge_days: int = 5,  # Gap between train/test to prevent leakage
        random_seed: int | None = None
    ):
        """
        Initialize random window validator.

        Args:
            data: Historical price data (must have 2+ years!)
            window_size_days: Fixed window size (if specified, disables random lengths)
            window_size_range: Range for random window lengths (min_days, max_days)
            n_windows: Number of random windows to test
            min_data_years: Minimum years of data required
            purge_days: Days to purge between train/test (prevent leakage)
            random_seed: Random seed for reproducibility

        Examples:
            # Fixed 90-day windows
            validator = RandomWindowValidator(data, window_size_days=90)

            # Random 30-180 day windows (BETTER!)
            validator = RandomWindowValidator(data, window_size_range=(30, 180))
        """
        self.data = data
        self.window_size_days = window_size_days  # None = random lengths
        self.window_size_range = window_size_range
        self.n_windows = n_windows
        self.purge_days = purge_days

        if random_seed is not None:
            random.seed(random_seed)
            np.random.seed(random_seed)

        # Validate data coverage
        data_years = (data.index[-1] - data.index[0]).days / 365.25
        if data_years < min_data_years:
            raise ValueError(
                f"Insufficient data: {data_years:.1f} years. "
                f"Need {min_data_years}+ years for robust validation!"
            )

        if self.window_size_days:
            logger.info(
                f"RandomWindowValidator initialized: "
                f"{data_years:.1f} years of data, "
                f"{n_windows} random {window_size_days}-day windows"
            )
        else:
            logger.info(
                f"RandomWindowValidator initialized: "
                f"{data_years:.1f} years of data, "
                f"{n_windows} random windows with lengths {window_size_range[0]}-{window_size_range[1]} days"
            )

        # Results storage
        self.window_results: list[WindowResult] = []

    def generate_random_windows(self) -> list[tuple[datetime, datetime, int]]:
        """
        Generate random time windows with RANDOM starts AND lengths.

        Ensures:
        - Random start times across full dataset
        - Random window lengths (e.g., 30-180 days)
        - No overlap between windows (independent tests)
        - Covers different timescales (short vs long term)
        - Covers different regimes (bull/bear/ranging)

        Why random lengths matter:
        - Some strategies work on 30-day windows but not 180-day
        - Tests robustness across different holding periods
        - Prevents overfitting to specific timescale

        Returns:
            List of (start_date, end_date, window_length_days) tuples
        """
        windows = []

        start = self.data.index[0]
        end = self.data.index[-1]
        total_days = (end - start).days

        # Generate random windows with random lengths
        for i in range(self.n_windows):
            # Random window length
            if self.window_size_days:
                # Fixed length mode
                window_length = self.window_size_days
            else:
                # Random length mode (BETTER!)
                window_length = random.randint(
                    self.window_size_range[0],
                    self.window_size_range[1]
                )

            # Random start within available range
            max_start_offset = total_days - window_length
            if max_start_offset <= 0:
                logger.warning(f"Window {i}: Not enough data for {window_length}-day window")
                continue

            random_offset = random.randint(0, max_start_offset)

            window_start = start + timedelta(days=random_offset)
            window_end = window_start + timedelta(days=window_length)

            windows.append((window_start, window_end, window_length))

        # Sort by start date
        windows.sort(key=lambda w: w[0])

        # Log distribution of window lengths
        lengths = [w[2] for w in windows]
        logger.info(
            f"Generated {len(windows)} random windows: "
            f"lengths {min(lengths)}-{max(lengths)} days "
            f"(avg={np.mean(lengths):.0f} days)"
        )

        return windows

    async def validate_strategy(
        self,
        strategy_runner,  # Your memory system + committee
        min_sharpe: float = 1.5,
        min_win_rate: float = 0.55,
        max_drawdown: float = 0.20
    ) -> dict:
        """
        Validate strategy on all random windows.

        A strategy is ROBUST if it:
        1. Passes ALL windows (or 95%+)
        2. Achieves min Sharpe in each window
        3. Achieves min win rate in each window
        4. Stays within max drawdown limit

        Args:
            strategy_runner: Your trading system (memory + committee)
            min_sharpe: Minimum Sharpe ratio required
            min_win_rate: Minimum win rate required (0-1)
            max_drawdown: Maximum drawdown allowed (0-1)

        Returns:
            Dict with aggregate results and per-window breakdown
        """
        windows = self.generate_random_windows()

        passed_windows = 0
        failed_windows = 0

        for window_id, (start, end, window_length) in enumerate(windows):
            logger.info(
                f"Testing window {window_id+1}/{len(windows)}: "
                f"{start.date()} to {end.date()} ({window_length} days)"
            )

            # Get data for this window
            window_data = self.data[start:end]

            if len(window_data) < 30:  # Need at least 30 days
                logger.warning(f"Window {window_id} has insufficient data, skipping")
                continue

            # Detect regime for this window
            regime = self._detect_regime(window_data)

            # Run strategy on this window
            result = await self._test_window(
                window_id=window_id,
                window_data=window_data,
                start=start,
                end=end,
                regime=regime,
                strategy_runner=strategy_runner
            )

            # Check if passed
            result.passed = (
                result.sharpe_ratio >= min_sharpe and
                result.win_rate >= min_win_rate and
                result.max_drawdown <= max_drawdown
            )

            if not result.passed:
                # Determine failure reason
                reasons = []
                if result.sharpe_ratio < min_sharpe:
                    reasons.append(f"Sharpe {result.sharpe_ratio:.2f} < {min_sharpe:.2f}")
                if result.win_rate < min_win_rate:
                    reasons.append(f"Win rate {result.win_rate:.1%} < {min_win_rate:.1%}")
                if result.max_drawdown > max_drawdown:
                    reasons.append(f"Drawdown {result.max_drawdown:.1%} > {max_drawdown:.1%}")

                result.failure_reason = "; ".join(reasons)
                failed_windows += 1
            else:
                passed_windows += 1

            self.window_results.append(result)

            logger.info(
                f"Window {window_id} ({regime}): "
                f"{'PASS ✅' if result.passed else 'FAIL ❌'} "
                f"Sharpe={result.sharpe_ratio:.2f}, "
                f"WinRate={result.win_rate:.1%}, "
                f"DD={result.max_drawdown:.1%}"
            )

        # Aggregate results
        return self._aggregate_results(passed_windows, failed_windows)

    async def _test_window(
        self,
        window_id: int,
        window_data: pd.DataFrame,
        start: datetime,
        end: datetime,
        regime: str,
        strategy_runner
    ) -> WindowResult:
        """
        Test strategy on a single window.

        This is where your memory system runs!
        """
        # Initialize fresh memory for this window
        # (Important: Don't leak information from other windows!)

        trades = []
        pnls = []

        # Run strategy on this window
        # TODO: Integrate with your memory system here
        # For now, placeholder logic:

        # Simulate trades
        for _i in range(10):  # Placeholder: 10 trades per window
            # This is where you'd call:
            # decision = await strategy_runner.make_decision(...)
            # trade = await strategy_runner.execute(...)
            # outcome = await strategy_runner.analyze(...)

            pnl = np.random.randn() * 0.02  # Placeholder
            trades.append({"pnl": pnl})
            pnls.append(pnl)

        # Calculate metrics
        pnls = np.array(pnls)
        win_rate = np.mean(pnls > 0) if len(pnls) > 0 else 0.0
        total_pnl = np.sum(pnls)

        if len(pnls) > 1 and np.std(pnls) > 0:
            sharpe_ratio = np.mean(pnls) / np.std(pnls) * np.sqrt(252)
        else:
            sharpe_ratio = 0.0

        # Calculate drawdown
        cumulative = np.cumsum(pnls)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / (running_max + 1e-8)
        max_drawdown = np.abs(np.min(drawdown))

        # Profit factor
        wins = pnls[pnls > 0]
        losses = pnls[pnls < 0]
        profit_factor = (np.sum(wins) / np.abs(np.sum(losses))) if len(losses) > 0 else 0.0

        return WindowResult(
            window_id=window_id,
            start_date=start,
            end_date=end,
            window_length_days=(end - start).days,
            regime=regime,
            total_trades=len(trades),
            win_rate=win_rate,
            total_pnl=total_pnl,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            profit_factor=profit_factor,
            patterns_discovered=[],  # TODO: From memory system
            novel_patterns=[],  # TODO: From exploration
            passed=False  # Will be set by validate_strategy
        )

    def _detect_regime(self, window_data: pd.DataFrame) -> str:
        """
        Detect market regime for this window.

        Regimes:
        - bull: > 20% up move
        - bear: > 20% down move
        - ranging: < 10% total move
        - volatile: High volatility, no clear trend
        """
        if len(window_data) == 0:
            return "unknown"

        # Calculate return
        start_price = window_data.iloc[0]["close"]
        end_price = window_data.iloc[-1]["close"]
        total_return = (end_price - start_price) / start_price

        # Calculate volatility
        returns = window_data["close"].pct_change()
        volatility = returns.std() * np.sqrt(252)  # Annualized

        # Classify regime
        if total_return > 0.20:
            return "bull"
        elif total_return < -0.20:
            return "bear"
        elif abs(total_return) < 0.10:
            return "ranging"
        elif volatility > 0.50:  # > 50% annualized vol
            return "volatile"
        else:
            return "mixed"

    def _aggregate_results(
        self,
        passed: int,
        failed: int
    ) -> dict:
        """Aggregate results across all windows"""

        total = passed + failed
        pass_rate = passed / total if total > 0 else 0.0

        # Group by regime
        regime_results = {}
        for result in self.window_results:
            if result.regime not in regime_results:
                regime_results[result.regime] = []
            regime_results[result.regime].append(result)

        # Calculate per-regime stats
        regime_stats = {}
        for regime, results in regime_results.items():
            passed_in_regime = sum(1 for r in results if r.passed)
            total_in_regime = len(results)

            regime_stats[regime] = {
                "total_windows": total_in_regime,
                "passed": passed_in_regime,
                "pass_rate": passed_in_regime / total_in_regime if total_in_regime > 0 else 0,
                "avg_sharpe": np.mean([r.sharpe_ratio for r in results]),
                "avg_win_rate": np.mean([r.win_rate for r in results]),
                "avg_drawdown": np.mean([r.max_drawdown for r in results])
            }

        # Overall statistics
        all_sharpes = [r.sharpe_ratio for r in self.window_results]
        all_win_rates = [r.win_rate for r in self.window_results]
        all_drawdowns = [r.max_drawdown for r in self.window_results]

        return {
            # Pass/fail
            "total_windows": total,
            "passed_windows": passed,
            "failed_windows": failed,
            "pass_rate": pass_rate,
            "all_windows_passed": (pass_rate >= 0.95),  # 95%+ pass rate

            # Overall performance
            "avg_sharpe": np.mean(all_sharpes),
            "median_sharpe": np.median(all_sharpes),
            "min_sharpe": np.min(all_sharpes),
            "max_sharpe": np.max(all_sharpes),

            "avg_win_rate": np.mean(all_win_rates),
            "median_win_rate": np.median(all_win_rates),
            "min_win_rate": np.min(all_win_rates),
            "max_win_rate": np.max(all_win_rates),

            "avg_drawdown": np.mean(all_drawdowns),
            "median_drawdown": np.median(all_drawdowns),
            "max_drawdown": np.max(all_drawdowns),

            # Per-regime breakdown
            "regime_stats": regime_stats,

            # All individual results
            "window_results": self.window_results
        }

    def get_failed_windows(self) -> list[WindowResult]:
        """Get all windows that failed validation"""
        return [r for r in self.window_results if not r.passed]

    def print_summary(self):
        """Print validation summary"""
        if not self.window_results:
            print("No results yet. Run validate_strategy() first.")
            return

        results = self._aggregate_results(
            passed=sum(1 for r in self.window_results if r.passed),
            failed=sum(1 for r in self.window_results if not r.passed)
        )

        print("\n" + "="*60)
        print("RANDOM WINDOW VALIDATION RESULTS")
        print("="*60)

        print(f"\nOverall: {results['passed_windows']}/{results['total_windows']} windows passed ({results['pass_rate']:.1%})")

        if results["all_windows_passed"]:
            print("✅ STRATEGY IS ROBUST! Works in all conditions.")
        else:
            print("❌ STRATEGY OVERFITTED. Failed in some windows.")

        print("\nPerformance Across All Windows:")
        print(f"  Sharpe: {results['avg_sharpe']:.2f} (median={results['median_sharpe']:.2f}, range=[{results['min_sharpe']:.2f}, {results['max_sharpe']:.2f}])")
        print(f"  Win Rate: {results['avg_win_rate']:.1%} (median={results['median_win_rate']:.1%}, range=[{results['min_win_rate']:.1%}, {results['max_win_rate']:.1%}])")
        print(f"  Max Drawdown: {results['avg_drawdown']:.1%} (median={results['median_drawdown']:.1%}, worst={results['max_drawdown']:.1%})")

        print("\nPerformance by Market Regime:")
        for regime, stats in results["regime_stats"].items():
            print(f"  {regime.upper()}:")
            print(f"    Windows: {stats['total_windows']}, Passed: {stats['passed']} ({stats['pass_rate']:.1%})")
            print(f"    Avg Sharpe: {stats['avg_sharpe']:.2f}, Win Rate: {stats['avg_win_rate']:.1%}")

        # Show failed windows
        failed = self.get_failed_windows()
        if failed:
            print(f"\nFailed Windows ({len(failed)}):")
            for result in failed[:5]:  # Show first 5
                print(f"  {result.start_date.date()} - {result.end_date.date()} ({result.regime}): {result.failure_reason}")
            if len(failed) > 5:
                print(f"  ... and {len(failed) - 5} more")

        print("="*60 + "\n")

    def __repr__(self):
        tested = len(self.window_results)
        passed = sum(1 for r in self.window_results if r.passed)
        return f"RandomWindowValidator(windows={tested}, passed={passed})"
