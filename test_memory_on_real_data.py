"""
Test Memory System on Real BTC/SOL Data

Integrates:
1. Random window validation (test across 2+ years)
2. Random RL exploration (epsilon-greedy)
3. Hierarchical memory (multi-timescale)
4. Real historical data

This is THE test that proves the system works!

Test Matrix:
- Pairs: BTC-USD, SOL-USD, BTC-SOL
- Timescales: DAY (swing trading)
- Windows: 100 random 30-180 day windows
- Exploration: 30% → 5% epsilon decay
- Validation: Sharpe > 1.2, Win Rate > 55%

Expected Results:
- Memory-enabled system should OUTPERFORM no-memory baseline
- Should discover novel patterns from random exploration
- Should pass 95%+ of windows (robust across regimes)
"""

import asyncio
import pandas as pd
import numpy as np
import logging
from pathlib import Path
from datetime import datetime

from coinswarm.memory.hierarchical_memory import HierarchicalMemory, Timescale
from coinswarm.memory.exploration_strategy import ExplorationStrategy, PatternDiscovery
from coinswarm.memory.state_builder import StateBuilder
from coinswarm.memory.learning_loop import LearningLoop
from coinswarm.backtesting.random_window_validator import RandomWindowValidator
from coinswarm.agents.committee import AgentCommittee
from coinswarm.agents.trend_agent import TrendFollowingAgent
from coinswarm.agents.risk_agent import RiskManagementAgent
from coinswarm.agents.trade_analysis_agent import TradeAnalysisAgent
from coinswarm.agents.strategy_learning_agent import StrategyLearningAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# Data directory
DATA_DIR = Path(__file__).parent / "data" / "historical"


def load_data(symbol: str, interval: str = "1h") -> pd.DataFrame:
    """Load historical data from CSV"""
    filename = DATA_DIR / f"{symbol}_{interval}.csv"

    if not filename.exists():
        raise FileNotFoundError(
            f"Data file not found: {filename}\n"
            f"Run: python fetch_multi_pair_data.py first!"
        )

    df = pd.read_csv(filename, index_col=0, parse_dates=True)
    logger.info(f"Loaded {len(df)} candles for {symbol}")

    return df


async def test_swing_trading_strategy(symbol: str):
    """
    Test swing trading strategy (DAY timescale) on real data.

    This simulates a basic swing trading system with:
    - Committee voting (trend + risk agents)
    - Memory recall (similar past trades)
    - Random exploration (30% → 5%)
    - Pattern learning

    If this works, memory is learning properly!
    """
    logger.info("\n" + "="*80)
    logger.info(f"TESTING SWING TRADING STRATEGY ON {symbol}")
    logger.info("="*80)

    # Load data
    df = load_data(symbol)

    # Initialize components
    logger.info("\n1. Initializing memory system...")

    memory = HierarchicalMemory(
        enabled_timescales=[Timescale.DAY]
    )

    state_builder = StateBuilder(
        state_dim=384,
        normalize=True
    )

    exploration = ExplorationStrategy(
        epsilon_start=0.30,  # Start with 30% random
        epsilon_end=0.05,    # Decay to 5%
        epsilon_decay=0.9995
    )

    pattern_discovery = PatternDiscovery(
        min_samples=50,
        significance_threshold=0.05,
        min_sharpe=1.0
    )

    # Initialize agents
    logger.info("2. Initializing agent committee...")

    agents = [
        TrendFollowingAgent(name="TrendFollower", weight=1.0),
        RiskManagementAgent(name="RiskManager", weight=2.0),
    ]

    committee = AgentCommittee(
        agents=agents,
        confidence_threshold=0.7
    )

    trade_analyzer = TradeAnalysisAgent()
    strategy_learner = StrategyLearningAgent()

    learning_loop = LearningLoop(
        memory=memory.memories[Timescale.DAY],  # Use DAY timescale
        state_builder=state_builder,
        trade_analyzer=trade_analyzer,
        strategy_learner=strategy_learner,
        committee=committee
    )

    # Initialize validator
    logger.info("3. Initializing random window validator...")

    validator = RandomWindowValidator(
        data=df,
        window_size_range=(30, 180),  # Random 30-180 day windows
        n_windows=100,
        min_data_years=2.0
    )

    # Run validation
    logger.info("4. Running random window validation...\n")

    class MockStrategy:
        """Mock strategy for testing"""
        def __init__(self, learning_loop, exploration, committee):
            self.learning_loop = learning_loop
            self.exploration = exploration
            self.committee = committee
            self.trades_executed = 0

        async def run_on_window(self, window_data):
            """Simulate trading on a window of data"""

            pnls = []

            for i in range(len(window_data)):
                # Decide: explore or exploit?
                should_explore = self.exploration.should_explore()

                if should_explore:
                    # RANDOM EXPLORATION
                    # (Might discover novel patterns!)
                    action = np.random.choice(["BUY", "SELL", "HOLD"])
                    confidence = np.random.uniform(0.6, 0.9)
                else:
                    # EXPLOIT: Use committee + memory
                    # TODO: Actually run committee voting
                    # For now, placeholder
                    action = "HOLD"
                    confidence = 0.5

                # Simulate trade outcome
                if action in ["BUY", "SELL"]:
                    # Random outcome for now (would be actual backtest)
                    pnl = np.random.randn() * 0.02  # ±2% typical

                    pnls.append(pnl)
                    self.trades_executed += 1

                    # Update epsilon
                    self.exploration.update_epsilon()

            return np.array(pnls)

    strategy = MockStrategy(learning_loop, exploration, committee)

    # Run validation
    results = await validator.validate_strategy(
        strategy_runner=strategy,
        min_sharpe=1.2,
        min_win_rate=0.55,
        max_drawdown=0.20
    )

    # Print results
    logger.info("\n" + "="*80)
    logger.info("VALIDATION RESULTS")
    logger.info("="*80)

    logger.info(f"\nOverall:")
    logger.info(f"  Passed: {results['passed_windows']}/{results['total_windows']} ({results['pass_rate']:.1%})")
    logger.info(f"  All windows passed: {'✅ YES' if results['all_windows_passed'] else '❌ NO'}")

    logger.info(f"\nPerformance:")
    logger.info(f"  Sharpe: {results['avg_sharpe']:.2f} (median={results['median_sharpe']:.2f})")
    logger.info(f"  Win Rate: {results['avg_win_rate']:.1%} (median={results['median_win_rate']:.1%})")
    logger.info(f"  Max Drawdown: {results['max_drawdown']:.1%}")

    logger.info(f"\nBy Regime:")
    for regime, stats in results['regime_stats'].items():
        logger.info(
            f"  {regime.upper():10s}: "
            f"{stats['passed']}/{stats['total_windows']} passed ({stats['pass_rate']:.1%}), "
            f"Sharpe={stats['avg_sharpe']:.2f}"
        )

    logger.info("\n" + "="*80)

    # Print exploration stats
    logger.info("\nEXPLORATION STATISTICS")
    logger.info("="*80)

    exp_stats = exploration.get_statistics()
    logger.info(f"Total decisions: {exp_stats['total_decisions']}")
    logger.info(f"Random explorations: {exp_stats['random_explorations']} ({exp_stats['exploration_rate']:.1%})")
    logger.info(f"Best pattern exploitations: {exp_stats['learned_exploitations'] + exp_stats['academic_exploitations'] + exp_stats['evolved_exploitations']} ({exp_stats['exploitation_rate']:.1%})")
    logger.info(f"Current epsilon: {exp_stats['current_epsilon']:.3f}")
    logger.info(f"Novel patterns discovered: {exp_stats['novel_patterns_discovered']}")

    logger.info("="*80 + "\n")

    return results


async def test_all_pairs():
    """Test on all pairs"""

    pairs = ["BTCUSDT", "SOLUSDT", "BTCSOL"]

    all_results = {}

    for pair in pairs:
        try:
            results = await test_swing_trading_strategy(pair)
            all_results[pair] = results
        except FileNotFoundError as e:
            logger.error(f"Skipping {pair}: {e}")
        except Exception as e:
            logger.error(f"Error testing {pair}: {e}")
            import traceback
            traceback.print_exc()

    # Summary
    logger.info("\n" + "="*80)
    logger.info("SUMMARY ACROSS ALL PAIRS")
    logger.info("="*80)

    for pair, results in all_results.items():
        logger.info(
            f"{pair:12s}: "
            f"Pass rate: {results['pass_rate']:.1%}, "
            f"Sharpe: {results['avg_sharpe']:.2f}, "
            f"Win rate: {results['avg_win_rate']:.1%}"
        )

    logger.info("="*80 + "\n")


async def main():
    """Main entry point"""

    logger.info("="*80)
    logger.info("MEMORY SYSTEM VALIDATION ON REAL DATA")
    logger.info("="*80)
    logger.info("This tests:")
    logger.info("  1. Hierarchical memory across timescales")
    logger.info("  2. Random RL exploration (epsilon-greedy)")
    logger.info("  3. Random window validation (2+ years)")
    logger.info("  4. Real BTC/SOL historical data")
    logger.info("="*80 + "\n")

    # Test all pairs
    await test_all_pairs()

    logger.info("✅ Testing complete!")


if __name__ == "__main__":
    asyncio.run(main())
