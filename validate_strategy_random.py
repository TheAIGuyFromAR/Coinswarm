#!/usr/bin/env python3
"""
Random Window Strategy Validation

Tests the trading strategy across multiple random time windows to validate
robustness and avoid overfitting to a single market period.

Usage:
    python validate_strategy_random.py --windows 10 --days 30
    python validate_strategy_random.py --windows 20 --days 60 --symbol BTC-USDC
"""

import asyncio
import argparse
import logging
import random
from datetime import datetime, timedelta
from typing import List, Dict
import statistics

from coinswarm.agents.trend_agent import TrendFollowingAgent
from coinswarm.agents.risk_agent import RiskManagementAgent
from coinswarm.agents.arbitrage_agent import ArbitrageAgent
from coinswarm.agents.committee import AgentCommittee
from coinswarm.backtesting.backtest_engine import BacktestEngine, BacktestConfig
from coinswarm.data_ingest.base import DataPoint

logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def generate_market_data(
    symbol: str,
    start_date: datetime,
    days: int,
    market_regime: str = "random"
) -> List[DataPoint]:
    """
    Generate mock market data with different regimes

    Args:
        symbol: Trading symbol (e.g. "BTC-USDC")
        start_date: Start date for data
        days: Number of days to generate
        market_regime: One of: random, bull, bear, sideways, volatile
    """

    data_points = []
    current_price = 50000.0 if symbol == "BTC-USDC" else 2500.0
    current_time = start_date

    # Set parameters based on market regime
    if market_regime == "bull":
        drift = 0.003  # 0.3% daily upward drift
        volatility = 0.015  # 1.5% volatility
    elif market_regime == "bear":
        drift = -0.003  # 0.3% daily downward drift
        volatility = 0.015
    elif market_regime == "sideways":
        drift = 0.0
        volatility = 0.01  # Low volatility
    elif market_regime == "volatile":
        drift = 0.0
        volatility = 0.035  # High volatility
    else:  # random
        drift = random.gauss(0.001, 0.002)
        volatility = random.uniform(0.015, 0.025)

    # Generate hourly candles
    for hour in range(days * 24):
        # Random walk with regime-specific parameters
        change_pct = random.gauss(drift / 24, volatility)
        current_price *= (1 + change_pct)

        # Clamp to reasonable range
        if symbol == "BTC-USDC":
            current_price = max(25000, min(80000, current_price))
        else:
            current_price = max(1000, min(5000, current_price))

        # Create OHLCV data
        open_price = current_price
        close_price = current_price * (1 + random.gauss(0, 0.003))
        high_price = max(open_price, close_price) * (1 + abs(random.gauss(0, 0.008)))
        low_price = min(open_price, close_price) * (1 - abs(random.gauss(0, 0.008)))
        volume = random.uniform(1000, 5000)

        data_point = DataPoint(
            source="mock",
            symbol=symbol,
            timeframe="1h",
            timestamp=current_time + timedelta(hours=hour),
            data={
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "price": close_price,
                "volume": volume
            },
            quality_score=1.0
        )

        data_points.append(data_point)

    return data_points


async def run_backtest_window(
    symbol: str,
    start_date: datetime,
    days: int,
    market_regime: str,
    agent_weights: Dict[str, float],
    confidence_threshold: float
) -> Dict:
    """Run a single backtest on a random window"""

    # Generate data for this window
    price_data = generate_market_data(symbol, start_date, days, market_regime)

    # Create agent committee
    agents = [
        TrendFollowingAgent(name="TrendFollower", weight=agent_weights.get("trend", 1.0)),
        RiskManagementAgent(name="RiskManager", weight=agent_weights.get("risk", 2.0)),
        ArbitrageAgent(name="ArbitrageHunter", weight=agent_weights.get("arbitrage", 2.0)),
    ]

    committee = AgentCommittee(
        agents=agents,
        confidence_threshold=confidence_threshold
    )

    # Configure backtest
    config = BacktestConfig(
        start_date=price_data[0].timestamp,
        end_date=price_data[-1].timestamp,
        initial_capital=100000,
        symbols=[symbol],
        timeframe="1h",
        commission=0.001,
        slippage=0.0005
    )

    # Run backtest
    historical_data = {symbol: price_data}
    engine = BacktestEngine(config)
    result = await engine.run_backtest(committee, historical_data)

    return {
        "start_date": start_date,
        "regime": market_regime,
        "return_pct": result.total_return_pct,
        "win_rate": result.win_rate,
        "sharpe": result.sharpe_ratio,
        "sortino": result.sortino_ratio,
        "max_drawdown": result.max_drawdown_pct,
        "total_trades": result.total_trades,
        "profit_factor": result.profit_factor,
    }


async def validate_strategy(
    symbol: str = "BTC-USDC",
    num_windows: int = 10,
    days_per_window: int = 30,
    agent_weights: Dict[str, float] = None,
    confidence_threshold: float = 0.6
):
    """
    Validate strategy across multiple random windows

    Args:
        symbol: Trading symbol
        num_windows: Number of random windows to test
        days_per_window: Length of each window in days
        agent_weights: Dictionary of agent weights
        confidence_threshold: Minimum confidence for trades
    """

    if agent_weights is None:
        agent_weights = {"trend": 1.0, "risk": 2.0, "arbitrage": 2.0}

    print("\n" + "="*70)
    print("RANDOM WINDOW STRATEGY VALIDATION")
    print("="*70 + "\n")

    print(f"Testing Strategy:")
    print(f"  Symbol: {symbol}")
    print(f"  Windows: {num_windows}")
    print(f"  Window Length: {days_per_window} days")
    print(f"  Agent Weights: {agent_weights}")
    print(f"  Confidence Threshold: {confidence_threshold}")
    print()

    # Generate random windows with different market regimes
    market_regimes = ["random", "bull", "bear", "sideways", "volatile"]

    results = []

    print(f"Running {num_windows} backtests...")
    print("-" * 70)

    for i in range(num_windows):
        # Pick random start date in last year
        days_ago = random.randint(days_per_window + 1, 365)
        start_date = datetime.now() - timedelta(days=days_ago)

        # Pick random market regime
        regime = random.choice(market_regimes)

        # Run backtest
        result = await run_backtest_window(
            symbol=symbol,
            start_date=start_date,
            days=days_per_window,
            market_regime=regime,
            agent_weights=agent_weights,
            confidence_threshold=confidence_threshold
        )

        results.append(result)

        # Print progress
        emoji = "✅" if result["return_pct"] > 0 else "❌"
        print(f"{i+1:2d}. {emoji} {result['start_date'].strftime('%Y-%m-%d')} "
              f"({result['regime']:8s}) | Return: {result['return_pct']:+6.1%} | "
              f"Win Rate: {result['win_rate']:5.1%} | Sharpe: {result['sharpe']:5.2f} | "
              f"Trades: {result['total_trades']:3d}")

    print("-" * 70)
    print()

    # Calculate aggregate statistics
    returns = [r["return_pct"] for r in results]
    win_rates = [r["win_rate"] for r in results]
    sharpes = [r["sharpe"] for r in results]
    sortinos = [r["sortino"] for r in results]
    max_drawdowns = [r["max_drawdown"] for r in results]
    total_trades = [r["total_trades"] for r in results]
    profit_factors = [r["profit_factor"] for r in results]

    # Count positive returns
    positive_windows = sum(1 for r in returns if r > 0)

    print("="*70)
    print("AGGREGATE RESULTS")
    print("="*70)
    print()
    print(f"Profitable Windows:  {positive_windows}/{num_windows} ({positive_windows/num_windows:.0%})")
    print()
    print(f"Return %:")
    print(f"  Mean:              {statistics.mean(returns):+.2%}")
    print(f"  Median:            {statistics.median(returns):+.2%}")
    print(f"  Std Dev:           {statistics.stdev(returns):.2%}")
    print(f"  Min:               {min(returns):+.2%}")
    print(f"  Max:               {max(returns):+.2%}")
    print()
    print(f"Win Rate:")
    print(f"  Mean:              {statistics.mean(win_rates):.1%}")
    print(f"  Median:            {statistics.median(win_rates):.1%}")
    print()
    print(f"Sharpe Ratio:")
    print(f"  Mean:              {statistics.mean(sharpes):.2f}")
    print(f"  Median:            {statistics.median(sharpes):.2f}")
    print()
    print(f"Max Drawdown:")
    print(f"  Mean:              {statistics.mean(max_drawdowns):.1%}")
    print(f"  Worst:             {max(max_drawdowns):.1%}")
    print()
    print(f"Trades per Window:")
    print(f"  Mean:              {statistics.mean(total_trades):.0f}")
    print(f"  Total:             {sum(total_trades)}")
    print("="*70)
    print()

    # Interpretation
    print("INTERPRETATION:")
    print("-" * 70)

    mean_return = statistics.mean(returns)
    mean_sharpe = statistics.mean(sharpes)
    mean_win_rate = statistics.mean(win_rates)
    consistency = positive_windows / num_windows

    if mean_return > 0.05 and mean_sharpe > 1.5 and consistency > 0.6:
        print("✅ EXCELLENT: Strategy is robust and profitable across conditions")
        print("   → Ready for paper trading")
    elif mean_return > 0.03 and mean_sharpe > 1.0 and consistency > 0.5:
        print("✅ GOOD: Strategy shows promise but needs refinement")
        print("   → Test with more windows (20+) before going live")
    elif mean_return > 0:
        print("⚠️  MARGINAL: Slight edge but high variance")
        print("   → Tune agent weights and confidence threshold")
        print("   → Test longer windows (60-90 days)")
    else:
        print("❌ POOR: Strategy is not profitable")
        print("   → Major tuning needed")
        print("   → Try different agent combinations")
        print("   → Lower confidence threshold for more trades")

    print()

    # Regime analysis
    print("REGIME ANALYSIS:")
    print("-" * 70)
    regime_stats = {}
    for regime in market_regimes:
        regime_results = [r for r in results if r["regime"] == regime]
        if regime_results:
            regime_returns = [r["return_pct"] for r in regime_results]
            regime_stats[regime] = {
                "count": len(regime_results),
                "mean_return": statistics.mean(regime_returns),
                "positive": sum(1 for r in regime_returns if r > 0)
            }

    for regime, stats in sorted(regime_stats.items()):
        if stats["count"] > 0:
            emoji = "✅" if stats["mean_return"] > 0 else "❌"
            print(f"{emoji} {regime:10s}: {stats['mean_return']:+6.1%} "
                  f"({stats['positive']}/{stats['count']} profitable)")

    print()
    print("="*70)


def main():
    parser = argparse.ArgumentParser(description="Validate trading strategy on random historical windows")
    parser.add_argument("--symbol", default="BTC-USDC", help="Trading symbol")
    parser.add_argument("--windows", type=int, default=10, help="Number of random windows to test")
    parser.add_argument("--days", type=int, default=30, help="Days per window")
    parser.add_argument("--threshold", type=float, default=0.6, help="Confidence threshold")
    parser.add_argument("--trend-weight", type=float, default=1.0, help="Trend agent weight")
    parser.add_argument("--risk-weight", type=float, default=2.0, help="Risk agent weight")
    parser.add_argument("--arb-weight", type=float, default=2.0, help="Arbitrage agent weight")

    args = parser.parse_args()

    agent_weights = {
        "trend": args.trend_weight,
        "risk": args.risk_weight,
        "arbitrage": args.arb_weight,
    }

    asyncio.run(validate_strategy(
        symbol=args.symbol,
        num_windows=args.windows,
        days_per_window=args.days,
        agent_weights=agent_weights,
        confidence_threshold=args.threshold
    ))


if __name__ == "__main__":
    main()
