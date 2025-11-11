"""
Continuous Evolution System

The main evolutionary loop that discovers winning strategies.

Process (runs continuously):
1. Run chaos trading simulations (generate trade data)
2. Analyze patterns (find correlations)
3. Test strategies (validate vs random)
4. Rank winners (upvote/downvote)
5. Repeat with more data

This creates an evolutionary pressure towards profitable strategies.
"""

import asyncio
import logging
from pathlib import Path
import subprocess
import time
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class ContinuousEvolutionSystem:
    """
    Main evolutionary loop for strategy discovery.

    Runs chaos → analyze → test → rank in an infinite loop.
    """

    def __init__(
        self,
        chaos_iterations_per_cycle: int = 1000,
        min_trades_for_analysis: int = 5000,
        strategy_test_iterations: int = 100
    ):
        self.chaos_iterations = chaos_iterations_per_cycle
        self.min_trades_for_analysis = min_trades_for_analysis
        self.test_iterations = strategy_test_iterations

        self.cycle_count = 0
        self.total_trades_generated = 0
        self.total_patterns_discovered = 0
        self.total_strategies_tested = 0

    async def run_chaos_trading(self) -> int:
        """
        Run chaos trading simulation to generate trade data.

        Returns number of trades generated.
        """

        logger.info(f"\n{'='*80}")
        logger.info(f"CYCLE {self.cycle_count + 1}: CHAOS TRADING")
        logger.info(f"{'='*80}")
        logger.info(f"Running {self.chaos_iterations} iterations...")

        # Run chaos simulator
        result = subprocess.run(
            ["python", "chaos_trading_simulator.py"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            logger.error(f"Chaos trading failed: {result.stderr}")
            return 0

        # Parse output to get trade count
        output = result.stdout
        for line in output.split("\n"):
            if "Total Trades:" in line:
                try:
                    trades = int(line.split(":")[1].strip())
                    logger.info(f"✓ Generated {trades:,} new trades")
                    return trades
                except:
                    pass

        return 0

    async def analyze_patterns(self) -> int:
        """
        Analyze chaos trading results to find patterns.

        Returns number of patterns discovered.
        """

        logger.info(f"\n{'='*80}")
        logger.info(f"CYCLE {self.cycle_count + 1}: PATTERN ANALYSIS")
        logger.info(f"{'='*80}")
        logger.info(f"Analyzing trades to find patterns...")

        # Run pattern analysis
        result = subprocess.run(
            ["python", "pattern_analysis_agent.py"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            logger.error(f"Pattern analysis failed: {result.stderr}")
            return 0

        # Parse output to get pattern count
        output = result.stdout
        for line in output.split("\n"):
            if "Discovered" in line and "candidate strategies" in line:
                try:
                    # Extract number from "Discovered X candidate strategies"
                    parts = line.split("Discovered")[1].split("candidate")[0].strip()
                    patterns = int(parts)
                    logger.info(f"✓ Discovered {patterns} new patterns")
                    return patterns
                except:
                    pass

        return 0

    async def test_strategies(self) -> dict:
        """
        Test discovered strategies vs random baseline.

        Returns test results summary.
        """

        logger.info(f"\n{'='*80}")
        logger.info(f"CYCLE {self.cycle_count + 1}: STRATEGY TESTING")
        logger.info(f"{'='*80}")
        logger.info(f"Testing strategies ({self.test_iterations} iterations per strategy)...")

        # Run strategy testing
        result = subprocess.run(
            ["python", "strategy_testing_agent.py"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            logger.error(f"Strategy testing failed: {result.stderr}")
            return {}

        # Parse results
        output = result.stdout
        upvotes = output.count("👍 UPVOTE")
        downvotes = output.count("👎 DOWNVOTE")

        logger.info(f"✓ Tested strategies")
        logger.info(f"  Upvotes: {upvotes}")
        logger.info(f"  Downvotes: {downvotes}")

        return {
            "upvotes": upvotes,
            "downvotes": downvotes,
            "tested": upvotes + downvotes
        }

    async def print_summary(self):
        """Print cycle summary"""

        logger.info(f"\n{'='*80}")
        logger.info(f"CYCLE {self.cycle_count + 1} COMPLETE")
        logger.info(f"{'='*80}")
        logger.info(f"Total Cycles:       {self.cycle_count + 1}")
        logger.info(f"Total Trades:       {self.total_trades_generated:,}")
        logger.info(f"Total Patterns:     {self.total_patterns_discovered}")
        logger.info(f"Total Tests:        {self.total_strategies_tested}")

        # Check for winning strategies
        rankings_file = Path("data/strategy_rankings/strategy_rankings.json")
        if rankings_file.exists():
            import json
            with open(rankings_file) as f:
                rankings = json.load(f)

            winners = [r for r in rankings if r["votes"] > 0]
            if winners:
                logger.info(f"\n🏆 WINNING STRATEGIES: {len(winners)}")
                for w in winners[:3]:  # Top 3
                    logger.info(f"  - {w['pattern_name']}: {w['avg_return']:+.2%} return, {w['win_rate']:.1%} win rate")
            else:
                logger.info(f"\n⏳ No winning strategies yet (all downvoted)")

        logger.info(f"{'='*80}\n")

    async def run_cycle(self):
        """Run one complete evolution cycle"""

        cycle_start = time.time()

        # 1. Generate chaos trading data
        trades = await self.run_chaos_trading()
        self.total_trades_generated += trades

        # 2. Analyze patterns (only if we have enough data)
        if trades >= self.min_trades_for_analysis:
            patterns = await self.analyze_patterns()
            self.total_patterns_discovered += patterns

            # 3. Test strategies (only if we discovered patterns)
            if patterns > 0:
                test_results = await self.test_strategies()
                self.total_strategies_tested += test_results.get("tested", 0)

        # 4. Print summary
        await self.print_summary()

        cycle_time = time.time() - cycle_start
        logger.info(f"Cycle completed in {cycle_time:.1f} seconds\n")

        self.cycle_count += 1

    async def run_forever(self, delay_between_cycles: int = 60):
        """
        Run evolution loop forever.

        Args:
            delay_between_cycles: Seconds to wait between cycles
        """

        logger.info("\n" + "="*80)
        logger.info("CONTINUOUS EVOLUTION SYSTEM")
        logger.info("="*80)
        logger.info(f"Chaos iterations per cycle: {self.chaos_iterations}")
        logger.info(f"Strategy test iterations: {self.test_iterations}")
        logger.info(f"Delay between cycles: {delay_between_cycles}s")
        logger.info("="*80)
        logger.info("\nPress Ctrl+C to stop\n")

        try:
            while True:
                await self.run_cycle()

                # Wait before next cycle
                if delay_between_cycles > 0:
                    logger.info(f"Waiting {delay_between_cycles}s before next cycle...")
                    await asyncio.sleep(delay_between_cycles)

        except KeyboardInterrupt:
            logger.info("\n\nStopping evolution system...")
            logger.info(f"\nFinal Statistics:")
            logger.info(f"  Total Cycles: {self.cycle_count}")
            logger.info(f"  Total Trades Generated: {self.total_trades_generated:,}")
            logger.info(f"  Total Patterns Discovered: {self.total_patterns_discovered}")
            logger.info(f"  Total Strategies Tested: {self.total_strategies_tested}")


async def main():
    """Run continuous evolution"""

    # Create evolution system
    system = ContinuousEvolutionSystem(
        chaos_iterations_per_cycle=1000,  # 1000 random trades per cycle
        min_trades_for_analysis=5000,     # Need 5k trades before analyzing
        strategy_test_iterations=100      # Test each strategy 100 times
    )

    # Run forever
    await system.run_forever(delay_between_cycles=10)  # 10 second pause between cycles


if __name__ == "__main__":
    asyncio.run(main())
