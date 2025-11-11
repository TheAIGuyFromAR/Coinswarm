#!/usr/bin/env python3
"""
Strategy Explainability Analysis

Analyzes discovered strategies to understand:
1. What conditions trigger trades
2. What patterns they exploit
3. Why they outperform HODL
4. Whether they're robust or overfit

Usage:
    python explain_strategy.py --strategy-file discovered_strategies_BTCUSDC_20251106_002943.json
"""

import asyncio
import argparse
import json
import logging
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
    level=logging.INFO,
    format="%(message)s"
)
logger = logging.getLogger(__name__)


def generate_market_data(symbol: str, start_date: datetime, days: int, market_regime: str = "random") -> List[DataPoint]:
    """Generate mock market data"""
    import random

    data_points = []
    current_price = 50000.0 if symbol == "BTC-USDC" else 2500.0
    current_time = start_date

    if market_regime == "bull":
        drift = 0.003
        volatility = 0.015
    elif market_regime == "bear":
        drift = -0.003
        volatility = 0.015
    elif market_regime == "sideways":
        drift = 0.0
        volatility = 0.01
    elif market_regime == "volatile":
        drift = 0.0
        volatility = 0.035
    else:
        drift = random.gauss(0.001, 0.002)
        volatility = random.uniform(0.015, 0.025)

    for hour in range(days * 24):
        change_pct = random.gauss(drift / 24, volatility)
        current_price *= (1 + change_pct)

        if symbol == "BTC-USDC":
            current_price = max(25000, min(80000, current_price))
        else:
            current_price = max(1000, min(5000, current_price))

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


async def explain_strategy(config: Dict, symbol: str, test_days: int, num_tests: int = 10):
    """
    Run detailed analysis of a strategy to understand its behavior
    """

    print(f"\n{'='*80}")
    print(f"STRATEGY EXPLAINABILITY ANALYSIS")
    print(f"{'='*80}\n")

    print(f"Configuration:")
    print(f"  Trend Weight: {config['trend_weight']:.3f}")
    print(f"  Risk Weight: {config['risk_weight']:.3f}")
    print(f"  Arbitrage Weight: {config['arbitrage_weight']:.3f}")
    print(f"  Confidence Threshold: {config['confidence_threshold']:.3f}")
    print()

    # Track patterns across multiple runs
    trade_conditions = []
    market_conditions_at_trade = []
    veto_patterns = []

    for test_num in range(num_tests):
        print(f"\n{'='*80}")
        print(f"Test {test_num + 1}/{num_tests}")
        print(f"{'='*80}")

        # Generate data
        market_regimes = ["sideways", "bull", "bear", "volatile"]
        regime = market_regimes[test_num % len(market_regimes)]

        import random
        random.seed(test_num)  # Reproducible
        days_ago = random.randint(test_days + 1, 365)
        start_date = datetime.now() - timedelta(days=days_ago)

        price_data = generate_market_data(symbol, start_date, test_days, regime)

        # Create committee with instrumentation
        agents = [
            TrendFollowingAgent(name="TrendFollower", weight=config['trend_weight']),
            RiskManagementAgent(name="RiskManager", weight=config['risk_weight']),
            ArbitrageAgent(name="ArbitrageHunter", weight=config['arbitrage_weight']),
        ]

        committee = AgentCommittee(
            agents=agents,
            confidence_threshold=config['confidence_threshold']
        )

        # Configure backtest
        backtest_config = BacktestConfig(
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
        engine = BacktestEngine(backtest_config)
        result = await engine.run_backtest(committee, historical_data)

        # Calculate HODL
        initial_price = price_data[0].data["close"]
        final_price = price_data[-1].data["close"]
        hodl_return = (final_price - initial_price) / initial_price

        print(f"\nMarket Regime: {regime}")
        print(f"Price Movement: ${initial_price:.0f} → ${final_price:.0f} ({hodl_return:+.1%})")
        print(f"Strategy Return: {result.total_return_pct:+.2%}")
        print(f"Total Trades: {result.total_trades}")
        print(f"Win Rate: {result.win_rate:.1%}")
        print(f"Sharpe: {result.sharpe_ratio:.2f}")

        # Analyze trade timing
        if result.total_trades > 0:
            print(f"\nTrade Analysis:")
            for i, trade in enumerate(result.trade_history[:5]):  # Show first 5
                print(f"  Trade {i+1}: {trade.action} {trade.size:.4f} @ ${trade.price:.0f}")
                print(f"    PnL: ${trade.pnl:.2f} ({trade.pnl_pct:+.2%})")
                print(f"    Timestamp: {trade.timestamp}")

        # Collect patterns
        if result.total_trades > 0:
            trade_conditions.append({
                'regime': regime,
                'hodl_return': hodl_return,
                'strategy_return': result.total_return_pct,
                'total_trades': result.total_trades,
                'win_rate': result.win_rate,
                'sharpe': result.sharpe_ratio
            })

    # Aggregate analysis
    print(f"\n\n{'='*80}")
    print(f"AGGREGATE PATTERN ANALYSIS")
    print(f"{'='*80}\n")

    if trade_conditions:
        print(f"Total Test Runs: {len(trade_conditions)}")
        print(f"\nPerformance by Market Regime:")

        for regime in ["sideways", "bull", "bear", "volatile"]:
            regime_data = [t for t in trade_conditions if t['regime'] == regime]
            if regime_data:
                avg_return = statistics.mean([t['strategy_return'] for t in regime_data])
                avg_trades = statistics.mean([t['total_trades'] for t in regime_data])
                avg_win_rate = statistics.mean([t['win_rate'] for t in regime_data])
                print(f"\n  {regime.upper()}:")
                print(f"    Avg Return: {avg_return:+.2%}")
                print(f"    Avg Trades: {avg_trades:.1f}")
                print(f"    Avg Win Rate: {avg_win_rate:.1%}")

        print(f"\n\nKEY INSIGHTS:")
        print(f"{'='*80}")

        # Insight 1: Trade frequency
        avg_trades = statistics.mean([t['total_trades'] for t in trade_conditions])
        print(f"\n1. TRADE FREQUENCY")
        print(f"   - Average {avg_trades:.1f} trades per {test_days}-day period")
        if avg_trades < 10:
            print(f"   - Strategy is VERY SELECTIVE (< 10 trades)")
            print(f"   - Waits for high-confidence setups")
            print(f"   - High confidence threshold ({config['confidence_threshold']:.2f}) filters most signals")

        # Insight 2: Market regime preference
        regime_performance = {}
        for regime in ["sideways", "bull", "bear", "volatile"]:
            regime_data = [t for t in trade_conditions if t['regime'] == regime]
            if regime_data:
                regime_performance[regime] = statistics.mean([t['strategy_return'] for t in regime_data])

        if regime_performance:
            best_regime = max(regime_performance, key=regime_performance.get)
            print(f"\n2. MARKET REGIME PREFERENCE")
            print(f"   - Best Performance: {best_regime.upper()} markets ({regime_performance[best_regime]:+.2%})")
            print(f"   - Strategy appears optimized for {best_regime} conditions")

        # Insight 3: Weight configuration impact
        print(f"\n3. AGENT WEIGHT CONFIGURATION")
        print(f"   - Trend Weight ({config['trend_weight']:.2f}): {'HIGH' if config['trend_weight'] > 2.0 else 'MODERATE'}")
        print(f"   - Risk Weight ({config['risk_weight']:.2f}): {'HIGH' if config['risk_weight'] > 2.0 else 'MODERATE'}")
        print(f"   - Arbitrage Weight ({config['arbitrage_weight']:.2f}): {'LOW' if config['arbitrage_weight'] < 2.0 else 'MODERATE'}")

        if config['risk_weight'] > config['trend_weight']:
            print(f"   → Risk management DOMINATES: Focuses on capital preservation")
        elif config['trend_weight'] > config['risk_weight']:
            print(f"   → Trend following DOMINATES: Focuses on momentum")
        else:
            print(f"   → BALANCED: Equal weight on trend and risk")

        # Insight 4: Success mechanism
        print(f"\n4. SUCCESS MECHANISM")
        profitable_runs = [t for t in trade_conditions if t['strategy_return'] > 0]
        if profitable_runs:
            print(f"   - Profitable in {len(profitable_runs)}/{len(trade_conditions)} test runs ({len(profitable_runs)/len(trade_conditions):.0%})")
            avg_profit = statistics.mean([t['strategy_return'] for t in profitable_runs])
            print(f"   - Average profit when successful: {avg_profit:+.2%}")

            # Compare to HODL
            beat_hodl = [t for t in trade_conditions if t['strategy_return'] > t['hodl_return']]
            print(f"   - Beats HODL in {len(beat_hodl)}/{len(trade_conditions)} runs ({len(beat_hodl)/len(trade_conditions):.0%})")

        print(f"\n5. ROBUSTNESS ASSESSMENT")
        returns = [t['strategy_return'] for t in trade_conditions]
        if len(returns) > 1:
            return_std = statistics.stdev(returns)
            return_mean = statistics.mean(returns)
            consistency = len([r for r in returns if r > 0]) / len(returns)

            print(f"   - Return Volatility: {return_std:.2%}")
            print(f"   - Consistency (% positive): {consistency:.0%}")

            if return_std < 0.05 and consistency > 0.6:
                print(f"   → HIGH ROBUSTNESS: Stable across conditions")
            elif return_std < 0.1:
                print(f"   → MODERATE ROBUSTNESS: Some variance")
            else:
                print(f"   → LOW ROBUSTNESS: High variance, may be overfit")

    print(f"\n{'='*80}")
    print(f"\n⚠️  IMPORTANT LIMITATIONS:")
    print(f"{'='*80}")
    print(f"1. Tested on MOCK DATA, not real market data")
    print(f"2. Mock data may have artifacts the strategy exploits")
    print(f"3. Need validation on REAL historical data before trusting results")
    print(f"4. Need out-of-sample testing on unseen data")
    print(f"5. Need to understand WHY specific trades are made, not just that they work")
    print(f"\n{'='*80}\n")


async def main():
    parser = argparse.ArgumentParser(description="Explain discovered trading strategies")
    parser.add_argument("--strategy-file", required=True, help="JSON file with discovered strategies")
    parser.add_argument("--strategy-rank", type=int, default=1, help="Which strategy to analyze (1-5)")
    parser.add_argument("--num-tests", type=int, default=10, help="Number of test runs")

    args = parser.parse_args()

    # Load strategies
    with open(args.strategy_file, 'r') as f:
        data = json.load(f)

    strategies = data['strategies']
    strategy = strategies[args.strategy_rank - 1]

    print(f"\nAnalyzing Strategy Rank #{args.strategy_rank}")
    print(f"Original Performance: {strategy['vs_hodl_multiple']:.2f}x HODL")
    print(f"Return: {strategy['return_pct']:+.2%}, HODL: {strategy['hodl_return_pct']:+.2%}")

    await explain_strategy(
        config=strategy['config'],
        symbol=data['symbol'],
        test_days=data['test_days'],
        num_tests=args.num_tests
    )


if __name__ == "__main__":
    asyncio.run(main())
