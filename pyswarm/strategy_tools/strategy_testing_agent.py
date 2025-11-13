"""
Strategy Testing Agent

Tests discovered patterns against random baseline to validate they're actually profitable.

Process:
1. Load discovered patterns
2. Test each pattern on random time windows
3. Compare to random trading baseline
4. Rank strategies by performance
5. Upvote winners, downvote losers
"""

import asyncio
import json
import logging
import random
import statistics
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from coinswarm.data_ingest.base import DataPoint

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class StrategyResult:
    """Results from testing a strategy"""
    pattern_id: str
    pattern_name: str
    num_trades: int
    win_rate: float
    avg_return: float
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    vs_random_return: float  # How much better than random
    vs_random_winrate: float  # How much better win rate
    confidence_score: float  # Overall confidence in strategy
    votes: int  # Upvotes - downvotes


class StrategyTestingAgent:
    """
    Agent that validates discovered patterns.

    Compares pattern-based trading vs random trading on same data.
    """

    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital
        self.patterns = []
        self.test_results = []

    def load_patterns(self, filepath: str = "data/discovered_patterns/patterns.json"):
        """Load discovered patterns"""
        with open(filepath) as f:
            self.patterns = json.load(f)

        logger.info(f"Loaded {len(self.patterns)} patterns to test")

    async def test_pattern_on_window(
        self,
        pattern: dict,
        data_window: list[DataPoint]
    ) -> dict:
        """
        Test a single pattern on a data window.

        Returns trade results using this pattern.
        """

        capital = self.initial_capital
        position = None
        trades = []

        for i, tick in enumerate(data_window):
            price = tick.data.get("price", tick.data.get("close", 0))

            # Check entry conditions if we don't have a position
            if not position:
                if self._should_enter(pattern, tick, data_window[:i+1]):
                    # Enter position
                    position_size = capital * 0.05  # Risk 5% per trade
                    shares = position_size / price
                    cost = shares * price * 1.0015  # 0.15% cost

                    if cost <= capital:
                        position = {
                            "entry_price": price * 1.001,
                            "shares": shares,
                            "entry_index": i
                        }
                        capital -= cost

            # Check exit conditions if we have a position
            elif position:
                profit_pct = (price - position["entry_price"]) / position["entry_price"]

                should_exit = False

                # Profit target
                profit_target = pattern.get("exit_rules", {}).get("profit_target", 0.03)
                if profit_pct >= profit_target:
                    should_exit = True

                # Stop loss
                stop_loss = pattern.get("exit_rules", {}).get("stop_loss", -0.02)
                if profit_pct <= stop_loss:
                    should_exit = True

                # Max duration
                duration = i - position["entry_index"]
                if duration > 50:  # Force exit after 50 ticks
                    should_exit = True

                if should_exit or i == len(data_window) - 1:
                    # Exit position
                    revenue = position["shares"] * price * 0.9985
                    capital += revenue

                    cost_basis = position["shares"] * position["entry_price"]
                    pnl = revenue - cost_basis
                    pnl_pct = (price - position["entry_price"]) / position["entry_price"]

                    trades.append({
                        "pnl": pnl,
                        "pnl_pct": pnl_pct,
                        "duration": duration,
                        "profitable": pnl > 0
                    })

                    position = None

        return {
            "final_capital": capital,
            "trades": trades,
            "num_trades": len(trades),
            "win_rate": sum(1 for t in trades if t["profitable"]) / len(trades) if trades else 0,
            "avg_return": statistics.mean([t["pnl_pct"] for t in trades]) if trades else 0,
            "total_return_pct": (capital - self.initial_capital) / self.initial_capital
        }

    def _should_enter(self, pattern: dict, tick: DataPoint, history: list[DataPoint]) -> bool:
        """
        Check if pattern entry conditions are met.
        """

        conditions = pattern.get("conditions", {})

        # Need enough history
        if len(history) < 20:
            return False

        price = tick.data.get("price", tick.data.get("close", 0))

        # Check momentum condition
        if "momentum_1tick" in conditions:
            if len(history) >= 2:
                prev_price = history[-2].data.get("price", history[-2].data.get("close", 0))
                momentum = (price - prev_price) / prev_price

                cond = conditions["momentum_1tick"]
                if not (cond["min"] <= momentum <= cond["max"]):
                    return False

        # Check SMA condition
        if "vs_sma10" in conditions:
            if len(history) >= 10:
                prices = [h.data.get("price", h.data.get("close", 0)) for h in history[-10:]]
                sma10 = sum(prices) / len(prices)
                vs_sma10 = (price - sma10) / sma10

                cond = conditions["vs_sma10"]
                if not (cond["min"] <= vs_sma10 <= cond["max"]):
                    return False

        # Check volume condition
        if "volume_vs_avg" in conditions:
            if len(history) >= 10:
                volume = tick.data.get("volume", 0)
                volumes = [h.data.get("volume", 0) for h in history[-10:]]
                avg_vol = sum(volumes) / len(volumes)

                if avg_vol > 0:
                    volume_vs_avg = (volume - avg_vol) / avg_vol

                    cond = conditions["volume_vs_avg"]
                    if not (cond["min"] <= volume_vs_avg <= cond["max"]):
                        return False

        # All conditions met
        return True

    async def test_random_baseline(self, data_window: list[DataPoint]) -> dict:
        """
        Test random trading as baseline for comparison.
        """

        capital = self.initial_capital
        position = None
        trades = []

        for i, tick in enumerate(data_window):
            price = tick.data.get("price", tick.data.get("close", 0))

            # Randomly enter 20% of the time
            if not position and random.random() < 0.2:
                position_size = capital * 0.05
                shares = position_size / price
                cost = shares * price * 1.0015

                if cost <= capital:
                    position = {
                        "entry_price": price * 1.001,
                        "shares": shares,
                        "entry_index": i
                    }
                    capital -= cost

            # Random exit 30% of the time
            elif position and (random.random() < 0.3 or i == len(data_window) - 1):
                revenue = position["shares"] * price * 0.9985
                capital += revenue

                cost_basis = position["shares"] * position["entry_price"]
                pnl = revenue - cost_basis
                pnl_pct = (price - position["entry_price"]) / position["entry_price"]

                trades.append({
                    "pnl": pnl,
                    "pnl_pct": pnl_pct,
                    "profitable": pnl > 0
                })

                position = None

        return {
            "final_capital": capital,
            "trades": trades,
            "num_trades": len(trades),
            "win_rate": sum(1 for t in trades if t["profitable"]) / len(trades) if trades else 0,
            "avg_return": statistics.mean([t["pnl_pct"] for t in trades]) if trades else 0,
            "total_return_pct": (capital - self.initial_capital) / self.initial_capital
        }

    async def test_strategy(
        self,
        pattern: dict,
        all_data: list[DataPoint],
        num_tests: int = 100
    ) -> StrategyResult:
        """
        Test a strategy multiple times on random windows.

        Compare to random baseline.
        """

        logger.info(f"\n{'='*80}")
        logger.info(f"Testing: {pattern['name']}")
        logger.info(f"{'='*80}")

        pattern_results = []
        random_results = []

        for _i in range(num_tests):
            # Pick random window
            window_size = random.randint(50, 150)
            max_start = len(all_data) - window_size
            if max_start <= 0:
                continue

            start_idx = random.randint(0, max_start)
            data_window = all_data[start_idx:start_idx + window_size]

            # Test pattern
            result = await self.test_pattern_on_window(pattern, data_window)
            pattern_results.append(result)

            # Test random baseline
            baseline = await self.test_random_baseline(data_window)
            random_results.append(baseline)

        # Calculate aggregate statistics
        pattern_returns = [r["total_return_pct"] for r in pattern_results]
        random_returns = [r["total_return_pct"] for r in random_results]

        pattern_winrates = [r["win_rate"] for r in pattern_results]
        random_winrates = [r["win_rate"] for r in random_results]

        avg_pattern_return = statistics.mean(pattern_returns) if pattern_returns else 0
        avg_random_return = statistics.mean(random_returns) if random_returns else 0

        avg_pattern_winrate = statistics.mean(pattern_winrates) if pattern_winrates else 0
        avg_random_winrate = statistics.mean(random_winrates) if random_winrates else 0

        # How much better than random?
        vs_random_return = avg_pattern_return - avg_random_return
        vs_random_winrate = avg_pattern_winrate - avg_random_winrate

        # Calculate confidence score
        confidence = 0.0
        if vs_random_return > 0.001:  # At least 0.1% better
            confidence += 0.3
        if vs_random_winrate > 0.05:  # At least 5% better win rate
            confidence += 0.3
        if avg_pattern_winrate > 0.5:  # Win rate > 50%
            confidence += 0.2
        if avg_pattern_return > 0:  # Profitable
            confidence += 0.2

        # Votes: +1 if beats random, -1 if loses to random
        votes = 1 if vs_random_return > 0 else -1

        result = StrategyResult(
            pattern_id=pattern.get("id", "unknown"),
            pattern_name=pattern.get("name", "Unknown"),
            num_trades=sum(r["num_trades"] for r in pattern_results),
            win_rate=avg_pattern_winrate,
            avg_return=avg_pattern_return,
            total_return=avg_pattern_return * num_tests,
            sharpe_ratio=0.0,  # TODO: Calculate properly
            max_drawdown=0.0,  # TODO: Calculate properly
            vs_random_return=vs_random_return,
            vs_random_winrate=vs_random_winrate,
            confidence_score=confidence,
            votes=votes
        )

        # Log results
        logger.info(f"\n📊 Results ({num_tests} tests):")
        logger.info(f"  Pattern Return:  {avg_pattern_return:+.2%}")
        logger.info(f"  Random Return:   {avg_random_return:+.2%}")
        logger.info(f"  Advantage:       {vs_random_return:+.2%}")
        logger.info("")
        logger.info(f"  Pattern Win Rate: {avg_pattern_winrate:.1%}")
        logger.info(f"  Random Win Rate:  {avg_random_winrate:.1%}")
        logger.info(f"  Advantage:        {vs_random_winrate:+.1%}")
        logger.info("")
        logger.info(f"  Confidence Score: {confidence:.0%}")
        logger.info(f"  Vote: {'👍 UPVOTE' if votes > 0 else '👎 DOWNVOTE'}")

        return result

    def save_results(self):
        """Save test results and rankings"""
        output_dir = Path("data/strategy_rankings")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Sort by confidence score
        sorted_results = sorted(self.test_results, key=lambda x: x.confidence_score, reverse=True)

        rankings = [
            {
                "rank": i + 1,
                "pattern_id": r.pattern_id,
                "pattern_name": r.pattern_name,
                "confidence_score": r.confidence_score,
                "win_rate": r.win_rate,
                "avg_return": r.avg_return,
                "vs_random_return": r.vs_random_return,
                "vs_random_winrate": r.vs_random_winrate,
                "votes": r.votes,
                "num_trades": r.num_trades
            }
            for i, r in enumerate(sorted_results)
        ]

        rankings_file = output_dir / "strategy_rankings.json"
        with open(rankings_file, "w") as f:
            json.dump(rankings, f, indent=2)

        logger.info(f"\n💾 Saved rankings to {rankings_file}")

        # Print leaderboard
        logger.info(f"\n{'='*80}")
        logger.info("STRATEGY LEADERBOARD")
        logger.info(f"{'='*80}")

        for i, r in enumerate(sorted_results[:10]):  # Top 10
            logger.info(f"\n#{i+1}: {r.pattern_name}")
            logger.info(f"  Confidence: {r.confidence_score:.0%}")
            logger.info(f"  Win Rate: {r.win_rate:.1%} (vs random: {r.vs_random_winrate:+.1%})")
            logger.info(f"  Avg Return: {r.avg_return:+.2%} (vs random: {r.vs_random_return:+.2%})")
            logger.info(f"  Votes: {r.votes}")


def load_historical_data(filepath: str) -> list[DataPoint]:
    """Load historical data from JSON file"""
    with open(filepath) as f:
        data = json.load(f)

    symbol = data.get("symbol", "BTC")
    candles = data.get("data", [])

    data_points = []
    for candle in candles:
        dp = DataPoint(
            source="cryptocompare",
            symbol=f"{symbol}-USD",
            timeframe="1h",
            timestamp=datetime.fromisoformat(candle['timestamp'].replace('Z', '+00:00')),
            data={
                "open": candle['open'],
                "high": candle['high'],
                "low": candle['low'],
                "close": candle['close'],
                "price": candle['close'],
                "volume": candle['volume']
            }
        )
        data_points.append(dp)

    return data_points


async def main():
    """Test all discovered patterns"""

    # Load historical data
    logger.info("Loading historical data...")
    data_points = load_historical_data("data/historical/BTC_180d_hour.json")
    logger.info(f"Loaded {len(data_points)} candles")

    # Create agent
    agent = StrategyTestingAgent()

    # Load patterns
    agent.load_patterns()

    # Test each pattern
    for pattern in agent.patterns:
        result = await agent.test_strategy(pattern, data_points, num_tests=100)
        agent.test_results.append(result)

    # Save rankings
    agent.save_results()


if __name__ == "__main__":
    asyncio.run(main())
