"""
Chaos Trading Simulator

Run thousands of random trades with:
- ChaosBuyAgent: Randomly buys with justifications
- OpportunisticSellAgent: Tries to sell at peaks with justifications

No committee, no strategy - just pure chaos to discover patterns.

Process:
1. Pick random time windows from historical data
2. Let chaos agents trade independently
3. Record every decision + state + outcome
4. Analyze patterns in wins vs losses
"""

import asyncio
import json
import logging
import random
from datetime import datetime, timedelta
from typing import List, Dict
from pathlib import Path

from coinswarm.data_ingest.base import DataPoint
from coinswarm.agents.chaos_buy_agent import ChaosBuyAgent
from coinswarm.agents.opportunistic_sell_agent import OpportunisticSellAgent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class ChaosTradingSimulator:
    """
    Simulator for chaos trading experiments.

    Runs independent buy/sell agents on random time windows
    to collect data about what conditions lead to profitable trades.
    """

    def __init__(
        self,
        initial_capital: float = 10000.0,
        commission: float = 0.001,
        slippage: float = 0.0005
    ):
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage

        # Results storage
        self.all_trades = []
        self.all_buy_decisions = []
        self.all_sell_decisions = []

    async def run_iteration(
        self,
        data_window: List[DataPoint],
        iteration: int
    ) -> Dict:
        """
        Run one chaos trading iteration on a data window.

        Returns:
            Dict with iteration results
        """

        # Create fresh agents for this iteration
        buy_agent = ChaosBuyAgent(
            buy_probability=random.uniform(0.2, 0.5)  # Random aggressiveness
        )

        sell_agent = OpportunisticSellAgent(
            profit_target_min=random.uniform(0.005, 0.02),  # 0.5-2%
            profit_target_max=random.uniform(0.05, 0.20),   # 5-20%
            peak_detection_threshold=random.uniform(0.3, 0.6)
        )

        # Trading state
        capital = self.initial_capital
        position = None  # {entry_price, size, entry_time, entry_state}
        trades = []

        # Run through data window
        for i, tick in enumerate(data_window):
            price = tick.data.get("price", tick.data.get("close", 0))

            # Get buy decision (always check)
            buy_vote = await buy_agent.analyze(tick, position, {})

            # Get sell decision (only matters if we have position)
            sell_vote = await sell_agent.analyze(tick, position, {})

            # Execute buy if agent wants to and we have no position
            if buy_vote.action == "BUY" and not position and capital > 0:
                # Calculate position size
                position_value = capital * buy_vote.size
                shares = position_value / (price * (1 + self.slippage))
                cost = shares * price * (1 + self.commission + self.slippage)

                if cost <= capital:
                    position = {
                        "entry_price": price * (1 + self.slippage),
                        "size": shares,
                        "entry_time": tick.timestamp,
                        "entry_index": i,
                        "entry_reason": buy_vote.reason,
                        "entry_confidence": buy_vote.confidence,
                        "entry_state": buy_agent.memory[-1]["state"] if buy_agent.memory else {}
                    }
                    capital -= cost

                    logger.debug(
                        f"[{iteration}] BUY {shares:.6f} @ ${price:,.2f} - {buy_vote.reason}"
                    )

            # Execute sell if agent wants to and we have position
            elif sell_vote.action == "SELL" and position:
                # Calculate proceeds
                shares = position["size"]
                revenue = shares * price * (1 - self.commission - self.slippage)
                capital += revenue

                # Calculate P&L
                cost_basis = position["size"] * position["entry_price"]
                pnl = revenue - cost_basis
                pnl_pct = (price - position["entry_price"]) / position["entry_price"]

                # Record trade
                trade = {
                    "iteration": iteration,
                    "entry_time": position["entry_time"].isoformat(),
                    "exit_time": tick.timestamp.isoformat(),
                    "entry_price": position["entry_price"],
                    "exit_price": price * (1 - self.slippage),
                    "size": shares,
                    "pnl": pnl,
                    "pnl_pct": pnl_pct,
                    "duration_ticks": i - position["entry_index"],
                    "buy_reason": position["entry_reason"],
                    "buy_confidence": position["entry_confidence"],
                    "buy_state": position["entry_state"],
                    "sell_reason": sell_vote.reason,
                    "sell_confidence": sell_vote.confidence,
                    "sell_state": sell_agent.memory[-1]["state"] if sell_agent.memory else {},
                    "profitable": pnl > 0
                }

                trades.append(trade)

                logger.debug(
                    f"[{iteration}] SELL {shares:.6f} @ ${price:,.2f} - "
                    f"PnL: ${pnl:,.2f} ({pnl_pct:+.2%}) - {sell_vote.reason}"
                )

                position = None

        # Close any open position at end of window
        if position:
            final_tick = data_window[-1]
            price = final_tick.data.get("price", final_tick.data.get("close", 0))

            shares = position["size"]
            revenue = shares * price * (1 - self.commission - self.slippage)
            capital += revenue

            cost_basis = position["size"] * position["entry_price"]
            pnl = revenue - cost_basis
            pnl_pct = (price - position["entry_price"]) / position["entry_price"]

            trade = {
                "iteration": iteration,
                "entry_time": position["entry_time"].isoformat(),
                "exit_time": final_tick.timestamp.isoformat(),
                "entry_price": position["entry_price"],
                "exit_price": price * (1 - self.slippage),
                "size": shares,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "duration_ticks": len(data_window) - position["entry_index"],
                "buy_reason": position["entry_reason"],
                "buy_confidence": position["entry_confidence"],
                "buy_state": position["entry_state"],
                "sell_reason": "End of window - forced exit",
                "sell_confidence": 0.5,
                "sell_state": {},
                "profitable": pnl > 0
            }

            trades.append(trade)

        # Calculate iteration results
        final_capital = capital
        total_return = final_capital - self.initial_capital
        total_return_pct = total_return / self.initial_capital

        result = {
            "iteration": iteration,
            "initial_capital": self.initial_capital,
            "final_capital": final_capital,
            "total_return": total_return,
            "total_return_pct": total_return_pct,
            "trades": trades,
            "num_trades": len(trades),
            "num_wins": sum(1 for t in trades if t["profitable"]),
            "num_losses": sum(1 for t in trades if not t["profitable"]),
            "win_rate": sum(1 for t in trades if t["profitable"]) / len(trades) if trades else 0,
            "buy_decisions": buy_agent.get_memory(),
            "sell_decisions": sell_agent.get_memory()
        }

        return result

    async def run_simulation(
        self,
        all_data: List[DataPoint],
        num_iterations: int = 100,
        window_size_range: tuple = (20, 100)  # 20-100 candles per window
    ):
        """
        Run multiple chaos trading iterations on random windows.

        Args:
            all_data: Full historical dataset
            num_iterations: Number of random iterations to run
            window_size_range: (min, max) window size in candles
        """

        logger.info("=" * 80)
        logger.info("CHAOS TRADING SIMULATOR")
        logger.info("=" * 80)
        logger.info(f"Dataset: {len(all_data)} candles")
        logger.info(f"Iterations: {num_iterations}")
        logger.info(f"Window size range: {window_size_range}")
        logger.info(f"Initial capital: ${self.initial_capital:,.2f}")
        logger.info("=" * 80)

        all_results = []

        for i in range(num_iterations):
            # Pick random window size
            window_size = random.randint(window_size_range[0], window_size_range[1])

            # Pick random start point (leaving room for window)
            max_start = len(all_data) - window_size
            if max_start <= 0:
                logger.warning("Dataset too small for window size")
                continue

            start_idx = random.randint(0, max_start)
            data_window = all_data[start_idx:start_idx + window_size]

            # Run iteration
            result = await self.run_iteration(data_window, i)
            all_results.append(result)

            # Progress update
            if (i + 1) % 10 == 0 or i == 0:
                logger.info(
                    f"[{i+1}/{num_iterations}] "
                    f"Window: {data_window[0].timestamp.strftime('%m-%d %H:%M')} - "
                    f"{data_window[-1].timestamp.strftime('%m-%d %H:%M')} "
                    f"({window_size} candles) | "
                    f"Trades: {result['num_trades']} | "
                    f"Return: {result['total_return_pct']:+.2%} | "
                    f"Win Rate: {result['win_rate']:.1%}"
                )

            # Collect all trades and decisions
            self.all_trades.extend(result["trades"])
            self.all_buy_decisions.extend(result["buy_decisions"])
            self.all_sell_decisions.extend(result["sell_decisions"])

        # Analyze overall results
        self._analyze_results(all_results)

        return all_results

    def _analyze_results(self, all_results: List[Dict]):
        """Analyze and display overall simulation results"""

        logger.info("\n" + "=" * 80)
        logger.info("SIMULATION RESULTS")
        logger.info("=" * 80)

        # Overall statistics
        total_iterations = len(all_results)
        total_trades = sum(r["num_trades"] for r in all_results)
        total_wins = sum(r["num_wins"] for r in all_results)
        total_losses = sum(r["num_losses"] for r in all_results)

        logger.info(f"\n📊 Overall Statistics:")
        logger.info(f"   Total Iterations:  {total_iterations}")
        logger.info(f"   Total Trades:      {total_trades}")
        logger.info(f"   Winning Trades:    {total_wins}")
        logger.info(f"   Losing Trades:     {total_losses}")
        logger.info(f"   Overall Win Rate:  {total_wins/total_trades:.1%}" if total_trades > 0 else "   No trades")

        # Profitable iterations
        profitable_iterations = sum(1 for r in all_results if r["total_return"] > 0)
        logger.info(f"   Profitable Runs:   {profitable_iterations}/{total_iterations} ({profitable_iterations/total_iterations:.1%})")

        # Return statistics
        returns = [r["total_return_pct"] for r in all_results]
        avg_return = sum(returns) / len(returns) if returns else 0
        best_return = max(returns) if returns else 0
        worst_return = min(returns) if returns else 0

        logger.info(f"\n💵 Return Statistics:")
        logger.info(f"   Average Return:    {avg_return:+.2%}")
        logger.info(f"   Best Return:       {best_return:+.2%}")
        logger.info(f"   Worst Return:      {worst_return:+.2%}")

        # Trade statistics
        if self.all_trades:
            avg_pnl = sum(t["pnl"] for t in self.all_trades) / len(self.all_trades)
            avg_pnl_pct = sum(t["pnl_pct"] for t in self.all_trades) / len(self.all_trades)

            winning_trades = [t for t in self.all_trades if t["profitable"]]
            losing_trades = [t for t in self.all_trades if not t["profitable"]]

            avg_win = sum(t["pnl"] for t in winning_trades) / len(winning_trades) if winning_trades else 0
            avg_loss = sum(t["pnl"] for t in losing_trades) / len(losing_trades) if losing_trades else 0

            logger.info(f"\n📈 Trade Statistics:")
            logger.info(f"   Avg Trade P&L:     ${avg_pnl:,.2f} ({avg_pnl_pct:+.2%})")
            logger.info(f"   Avg Winning Trade: ${avg_win:,.2f}")
            logger.info(f"   Avg Losing Trade:  ${avg_loss:,.2f}")

        # Save detailed results
        self._save_results(all_results)

    def _save_results(self, all_results: List[Dict]):
        """Save detailed results to JSON for later analysis"""

        output_dir = Path("data/chaos_trading")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Convert datetime objects to strings for JSON serialization
        def convert_datetimes(obj):
            if isinstance(obj, dict):
                return {k: convert_datetimes(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_datetimes(item) for item in obj]
            elif isinstance(obj, datetime):
                return obj.isoformat()
            return obj

        # Save summary
        summary = {
            "timestamp": timestamp,
            "num_iterations": len(all_results),
            "total_trades": len(self.all_trades),
            "results": convert_datetimes(all_results)
        }

        summary_file = output_dir / f"chaos_summary_{timestamp}.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)

        logger.info(f"\n💾 Results saved to: {summary_file}")

        # Save all trades for pattern analysis
        trades_file = output_dir / f"chaos_trades_{timestamp}.json"
        with open(trades_file, "w") as f:
            json.dump(convert_datetimes(self.all_trades), f, indent=2)

        logger.info(f"💾 All trades saved to: {trades_file}")


def load_historical_data(filepath: str) -> List[DataPoint]:
    """Load historical data from JSON file"""
    with open(filepath, 'r') as f:
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
    """Run chaos trading simulation"""

    # Load historical data
    logger.info("Loading historical data...")
    data_points = load_historical_data("data/historical/BTC_180d_hour.json")
    logger.info(f"Loaded {len(data_points)} candles")

    # Create simulator
    simulator = ChaosTradingSimulator(
        initial_capital=10000.0,
        commission=0.001,
        slippage=0.0005
    )

    # Run simulation with many iterations
    await simulator.run_simulation(
        all_data=data_points,
        num_iterations=1000,  # Run 1000 random iterations
        window_size_range=(30, 100)  # 30-100 hour windows
    )


if __name__ == "__main__":
    asyncio.run(main())
