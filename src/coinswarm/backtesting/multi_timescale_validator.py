"""
Multi-Timescale Strategy Validator

Tests strategies across ALL timescales from HFT to long-term holds.

Strategy Types by Timescale:
├── MICROSECOND (HFT):
│   - Market making (bid-ask spread capture)
│   - Latency arbitrage (co-location advantage)
│   - Order book arbitrage (cross-exchange)
│
├── MILLISECOND-SECOND:
│   - Spread arbitrage
│   - Tick scalping
│   - Momentum bursts
│
├── MINUTE-HOUR (Intraday):
│   - Day trading patterns
│   - News reactions
│   - Technical breakouts
│
├── DAY-WEEK (Swing):
│   - Multi-day trends
│   - Support/resistance
│   - Pattern trading
│
└── MONTH-YEAR (Long-term):
    - Trend following
    - Macro themes
    - Fundamental analysis

Key Insight:
A GOOD strategy should work at its target timescale.
A GREAT strategy should work across MULTIPLE timescales.

Example:
- Momentum strategy might work on 1-hour, 1-day, AND 1-week scales
- Market making ONLY works on microsecond-millisecond scale
- This is expected and OK!

Validation Approach:
1. Test on primary timescale (must pass)
2. Test on adjacent timescales (bonus if passes)
3. Test across regimes (bull/bear/ranging/volatile)
4. Test with random window lengths
5. Require 2+ years data minimum

Academic Reference:
- Zumbach (2009): "Time Reversal Invariance in Finance"
- Dacorogna et al. (1993): "A Geographical Model for the Daily and Weekly Seasonal Volatility"
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from coinswarm.memory.hierarchical_memory import Timescale, HierarchicalMemory
from coinswarm.backtesting.random_window_validator import WindowResult

logger = logging.getLogger(__name__)


@dataclass
class TimescaleRequirement:
    """Performance requirements for a specific timescale"""
    timescale: Timescale
    min_sharpe: float
    min_win_rate: float
    max_drawdown: float
    min_trades: int  # Minimum trades needed for statistical significance

    @classmethod
    def for_hft(cls) -> 'TimescaleRequirement':
        """Requirements for HFT strategies (market making, spread arb)"""
        return cls(
            timescale=Timescale.MILLISECOND,
            min_sharpe=2.0,      # HFT needs high Sharpe (low risk)
            min_win_rate=0.51,   # Can have lower win rate (high volume)
            max_drawdown=0.05,   # Very low drawdown (stop quickly)
            min_trades=1000      # Need lots of trades for statistical power
        )

    @classmethod
    def for_day_trading(cls) -> 'TimescaleRequirement':
        """Requirements for day trading strategies"""
        return cls(
            timescale=Timescale.HOUR,
            min_sharpe=1.5,
            min_win_rate=0.55,
            max_drawdown=0.10,
            min_trades=100
        )

    @classmethod
    def for_swing_trading(cls) -> 'TimescaleRequirement':
        """Requirements for swing trading strategies"""
        return cls(
            timescale=Timescale.DAY,
            min_sharpe=1.2,
            min_win_rate=0.55,
            max_drawdown=0.15,
            min_trades=50
        )

    @classmethod
    def for_long_term(cls) -> 'TimescaleRequirement':
        """Requirements for long-term hold strategies"""
        return cls(
            timescale=Timescale.MONTH,
            min_sharpe=1.0,
            min_win_rate=0.50,   # Can have 50% win rate if wins are big
            max_drawdown=0.25,    # Can tolerate more drawdown
            min_trades=20
        )


@dataclass
class MultiTimescaleResult:
    """Results from testing across multiple timescales"""
    strategy_name: str
    primary_timescale: Timescale

    # Results by timescale
    results_by_timescale: Dict[Timescale, List[WindowResult]]

    # Aggregate performance
    passed_timescales: List[Timescale]
    failed_timescales: List[Timescale]

    # Best/worst
    best_timescale: Optional[Timescale] = None
    worst_timescale: Optional[Timescale] = None

    # Cross-timescale consistency
    is_cross_timescale_robust: bool = False
    timescale_consistency_score: float = 0.0  # 0-1


class MultiTimescaleValidator:
    """
    Validate strategies across multiple timescales.

    Example Usage:
        validator = MultiTimescaleValidator(data=btc_2020_2023)

        # Test market making strategy
        mm_results = await validator.validate_strategy(
            strategy=market_making_strategy,
            primary_timescale=Timescale.MILLISECOND,
            test_adjacent=True  # Also test MICROSECOND and SECOND
        )

        # Test swing trading strategy
        swing_results = await validator.validate_strategy(
            strategy=swing_strategy,
            primary_timescale=Timescale.DAY,
            test_adjacent=True  # Also test HOUR and WEEK
        )

        # Test if strategy works across ALL timescales (rare!)
        universal_results = await validator.validate_strategy(
            strategy=universal_strategy,
            test_all_timescales=True
        )
    """

    def __init__(
        self,
        data: pd.DataFrame,
        min_data_years: float = 2.0
    ):
        """
        Initialize multi-timescale validator.

        Args:
            data: Historical price data (must have 2+ years!)
            min_data_years: Minimum years of data required
        """
        self.data = data

        # Validate data coverage
        data_years = (data.index[-1] - data.index[0]).days / 365.25
        if data_years < min_data_years:
            raise ValueError(
                f"Insufficient data: {data_years:.1f} years. "
                f"Need {min_data_years}+ years for robust validation!"
            )

        logger.info(
            f"MultiTimescaleValidator initialized with {data_years:.1f} years of data"
        )

        # Results storage
        self.validation_results: List[MultiTimescaleResult] = []

    async def validate_strategy(
        self,
        strategy,
        strategy_name: str = "unnamed",
        primary_timescale: Optional[Timescale] = None,
        test_adjacent: bool = True,
        test_all_timescales: bool = False,
        requirements: Optional[Dict[Timescale, TimescaleRequirement]] = None
    ) -> MultiTimescaleResult:
        """
        Validate strategy across timescales.

        Args:
            strategy: Strategy to test
            strategy_name: Name for reporting
            primary_timescale: Main timescale (required if not test_all_timescales)
            test_adjacent: Test adjacent timescales too
            test_all_timescales: Test ALL timescales (for universal strategies)
            requirements: Custom requirements per timescale

        Returns:
            MultiTimescaleResult with performance across timescales
        """
        # Determine which timescales to test
        timescales_to_test = []

        if test_all_timescales:
            timescales_to_test = list(Timescale)
        elif primary_timescale:
            timescales_to_test.append(primary_timescale)

            if test_adjacent:
                all_scales = list(Timescale)
                idx = all_scales.index(primary_timescale)

                if idx > 0:
                    timescales_to_test.append(all_scales[idx - 1])
                if idx < len(all_scales) - 1:
                    timescales_to_test.append(all_scales[idx + 1])
        else:
            raise ValueError("Must specify primary_timescale or test_all_timescales=True")

        logger.info(
            f"Testing strategy '{strategy_name}' on {len(timescales_to_test)} timescales: "
            f"{[ts.value for ts in timescales_to_test]}"
        )

        # Set default requirements if not provided
        if requirements is None:
            requirements = self._get_default_requirements(timescales_to_test)

        # Test each timescale
        results_by_timescale = {}

        for timescale in timescales_to_test:
            logger.info(f"Testing on {timescale.value} timescale...")

            # Get windows appropriate for this timescale
            windows = self._generate_windows_for_timescale(timescale)

            # Run strategy on each window
            window_results = []
            for window_id, (start, end, length) in enumerate(windows):
                result = await self._test_window(
                    window_id=window_id,
                    start=start,
                    end=end,
                    length=length,
                    timescale=timescale,
                    strategy=strategy,
                    requirement=requirements[timescale]
                )
                window_results.append(result)

            results_by_timescale[timescale] = window_results

            # Log summary for this timescale
            passed = sum(1 for r in window_results if r.passed)
            logger.info(
                f"  {timescale.value}: {passed}/{len(window_results)} windows passed "
                f"({passed/len(window_results)*100:.1f}%)"
            )

        # Analyze cross-timescale performance
        result = self._analyze_cross_timescale(
            strategy_name=strategy_name,
            primary_timescale=primary_timescale or timescales_to_test[0],
            results_by_timescale=results_by_timescale,
            requirements=requirements
        )

        self.validation_results.append(result)

        return result

    def _get_default_requirements(
        self,
        timescales: List[Timescale]
    ) -> Dict[Timescale, TimescaleRequirement]:
        """Get default requirements for each timescale"""
        requirements = {}

        for ts in timescales:
            if ts in [Timescale.MICROSECOND, Timescale.MILLISECOND]:
                requirements[ts] = TimescaleRequirement.for_hft()
            elif ts in [Timescale.SECOND, Timescale.MINUTE, Timescale.HOUR]:
                requirements[ts] = TimescaleRequirement.for_day_trading()
            elif ts in [Timescale.DAY, Timescale.WEEK]:
                requirements[ts] = TimescaleRequirement.for_swing_trading()
            else:  # MONTH, YEAR
                requirements[ts] = TimescaleRequirement.for_long_term()

        return requirements

    def _generate_windows_for_timescale(
        self,
        timescale: Timescale
    ) -> List[Tuple[datetime, datetime, int]]:
        """
        Generate test windows appropriate for timescale.

        HFT: 1-hour windows (many short tests)
        Day trading: 1-day to 1-week windows
        Swing: 1-week to 1-month windows
        Long-term: 1-month to 6-month windows
        """
        windows = []
        n_windows = 100  # Always test 100 windows

        # Determine window length range based on timescale
        if timescale in [Timescale.MICROSECOND, Timescale.MILLISECOND]:
            # HFT: 1-hour windows (in seconds)
            min_length_seconds = 3600      # 1 hour
            max_length_seconds = 14400     # 4 hours
        elif timescale in [Timescale.SECOND, Timescale.MINUTE]:
            # Scalping: 4-hour to 1-day windows
            min_length_seconds = 14400     # 4 hours
            max_length_seconds = 86400     # 1 day
        elif timescale == Timescale.HOUR:
            # Day trading: 1-day to 1-week windows
            min_length_seconds = 86400     # 1 day
            max_length_seconds = 604800    # 1 week
        elif timescale == Timescale.DAY:
            # Swing: 1-week to 1-month windows
            min_length_seconds = 604800    # 1 week
            max_length_seconds = 2592000   # 30 days
        elif timescale == Timescale.WEEK:
            # Position: 1-month to 3-month windows
            min_length_seconds = 2592000   # 30 days
            max_length_seconds = 7776000   # 90 days
        else:  # MONTH, YEAR
            # Long-term: 3-month to 6-month windows
            min_length_seconds = 7776000   # 90 days
            max_length_seconds = 15552000  # 180 days

        # Generate random windows
        start = self.data.index[0]
        end = self.data.index[-1]
        total_seconds = (end - start).total_seconds()

        for i in range(n_windows):
            # Random window length
            window_seconds = np.random.randint(min_length_seconds, max_length_seconds)

            # Random start
            max_start_offset = total_seconds - window_seconds
            if max_start_offset <= 0:
                continue

            random_offset = np.random.randint(0, int(max_start_offset))

            window_start = start + timedelta(seconds=random_offset)
            window_end = window_start + timedelta(seconds=window_seconds)

            windows.append((window_start, window_end, int(window_seconds / 86400)))

        # Sort by start
        windows.sort(key=lambda w: w[0])

        return windows

    async def _test_window(
        self,
        window_id: int,
        start: datetime,
        end: datetime,
        length: int,
        timescale: Timescale,
        strategy,
        requirement: TimescaleRequirement
    ) -> WindowResult:
        """Test strategy on a single window at specific timescale"""

        # Get data for this window
        window_data = self.data[start:end]

        if len(window_data) < 10:
            # Insufficient data
            return WindowResult(
                window_id=window_id,
                start_date=start,
                end_date=end,
                window_length_days=length,
                regime="unknown",
                total_trades=0,
                win_rate=0.0,
                total_pnl=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                profit_factor=0.0,
                patterns_discovered=[],
                novel_patterns=[],
                passed=False,
                failure_reason="Insufficient data"
            )

        # TODO: Run strategy here
        # For now, placeholder
        trades = np.random.randint(0, 1000)  # Placeholder
        pnls = np.random.randn(max(1, trades)) * 0.01  # Placeholder

        # Calculate metrics
        win_rate = np.mean(pnls > 0) if len(pnls) > 0 else 0.0
        total_pnl = np.sum(pnls)
        sharpe = (np.mean(pnls) / np.std(pnls) * np.sqrt(252)) if len(pnls) > 1 and np.std(pnls) > 0 else 0.0

        # Drawdown
        cumulative = np.cumsum(pnls)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / (running_max + 1e-8)
        max_dd = abs(np.min(drawdown))

        # Profit factor
        wins = pnls[pnls > 0]
        losses = pnls[pnls < 0]
        profit_factor = (np.sum(wins) / abs(np.sum(losses))) if len(losses) > 0 else 0.0

        # Check if passed
        passed = (
            trades >= requirement.min_trades and
            sharpe >= requirement.min_sharpe and
            win_rate >= requirement.min_win_rate and
            max_dd <= requirement.max_drawdown
        )

        return WindowResult(
            window_id=window_id,
            start_date=start,
            end_date=end,
            window_length_days=length,
            regime="mixed",  # TODO: Detect regime
            total_trades=trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            profit_factor=profit_factor,
            patterns_discovered=[],
            novel_patterns=[],
            passed=passed
        )

    def _analyze_cross_timescale(
        self,
        strategy_name: str,
        primary_timescale: Timescale,
        results_by_timescale: Dict[Timescale, List[WindowResult]],
        requirements: Dict[Timescale, TimescaleRequirement]
    ) -> MultiTimescaleResult:
        """Analyze performance across timescales"""

        passed_timescales = []
        failed_timescales = []

        # Check each timescale
        for timescale, results in results_by_timescale.items():
            passed_windows = sum(1 for r in results if r.passed)
            pass_rate = passed_windows / len(results) if results else 0.0

            if pass_rate >= 0.95:  # 95%+ pass rate
                passed_timescales.append(timescale)
            else:
                failed_timescales.append(timescale)

        # Find best/worst
        avg_sharpes = {
            ts: np.mean([r.sharpe_ratio for r in results])
            for ts, results in results_by_timescale.items()
        }

        best_timescale = max(avg_sharpes, key=avg_sharpes.get)
        worst_timescale = min(avg_sharpes, key=avg_sharpes.get)

        # Calculate consistency score
        sharpe_values = list(avg_sharpes.values())
        consistency = 1.0 - (np.std(sharpe_values) / (np.mean(sharpe_values) + 1e-8))
        consistency = np.clip(consistency, 0, 1)

        # Is cross-timescale robust?
        is_robust = (
            len(passed_timescales) >= 2 and  # Passes at least 2 timescales
            primary_timescale in passed_timescales  # Must pass primary
        )

        return MultiTimescaleResult(
            strategy_name=strategy_name,
            primary_timescale=primary_timescale,
            results_by_timescale=results_by_timescale,
            passed_timescales=passed_timescales,
            failed_timescales=failed_timescales,
            best_timescale=best_timescale,
            worst_timescale=worst_timescale,
            is_cross_timescale_robust=is_robust,
            timescale_consistency_score=consistency
        )

    def print_summary(self, result: MultiTimescaleResult):
        """Print validation summary"""
        print("\n" + "="*80)
        print(f"MULTI-TIMESCALE VALIDATION: {result.strategy_name}")
        print("="*80)

        print(f"\nPrimary Timescale: {result.primary_timescale.value}")
        print(f"Cross-Timescale Robust: {'✅ YES' if result.is_cross_timescale_robust else '❌ NO'}")
        print(f"Consistency Score: {result.timescale_consistency_score:.2%}")

        print(f"\nPassed Timescales ({len(result.passed_timescales)}):")
        for ts in result.passed_timescales:
            results = result.results_by_timescale[ts]
            avg_sharpe = np.mean([r.sharpe_ratio for r in results])
            avg_win_rate = np.mean([r.win_rate for r in results])
            print(f"  ✅ {ts.value:15s} - Sharpe={avg_sharpe:.2f}, WinRate={avg_win_rate:.1%}")

        if result.failed_timescales:
            print(f"\nFailed Timescales ({len(result.failed_timescales)}):")
            for ts in result.failed_timescales:
                results = result.results_by_timescale[ts]
                avg_sharpe = np.mean([r.sharpe_ratio for r in results])
                avg_win_rate = np.mean([r.win_rate for r in results])
                print(f"  ❌ {ts.value:15s} - Sharpe={avg_sharpe:.2f}, WinRate={avg_win_rate:.1%}")

        print(f"\nBest Performance: {result.best_timescale.value}")
        print(f"Worst Performance: {result.worst_timescale.value}")

        print("="*80 + "\n")
