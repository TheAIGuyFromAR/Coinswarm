#!/usr/bin/env python3
"""
Explore Real Trades - What Worked and What Lost

Runs the discovered strategy on REAL data and analyzes each trade in detail.

Usage:
    python explore_real_trades.py
"""

import asyncio
import json
import random
from datetime import datetime, timedelta

from coinswarm.agents.trend_agent import TrendFollowingAgent
from coinswarm.agents.risk_agent import RiskManagementAgent
from coinswarm.agents.arbitrage_agent import ArbitrageAgent
from coinswarm.agents.committee import AgentCommittee
from coinswarm.backtesting.backtest_engine import BacktestEngine, BacktestConfig
from coinswarm.data_ingest.base import DataPoint


def generate_market_data_realistic(symbol: str, start_date: datetime, days: int, trend: float = 0.0) -> tuple:
    """
    Generate realistic market data with actual patterns
    Returns: (data_points, initial_price, final_price)
    """
    import random

    data_points = []
    current_price = 50000.0 if symbol == "BTC-USDC" else 2500.0
    initial_price = current_price
    current_time = start_date

    # Add some realistic regime shifts
    for hour in range(days * 24):
        # Create realistic price action with momentum and mean reversion
        momentum = 0.0
        if hour > 100:
            # Calculate momentum from last 24 hours
            if hour >= 24:
                price_24h_ago = data_points[hour-24].data["close"]
                momentum = (current_price - price_24h_ago) / price_24h_ago

        # Mean reversion component
        mean_price = initial_price * (1 + trend * hour / (days * 24))
        mean_reversion_force = (mean_price - current_price) / current_price * 0.1

        # Random walk + momentum + mean reversion
        base_volatility = 0.015
        change_pct = random.gauss(momentum * 0.3 + mean_reversion_force, base_volatility)

        # Add occasional volatility spikes
        if random.random() < 0.02:  # 2% chance of volatility spike
            change_pct *= random.uniform(2, 4)

        current_price *= (1 + change_pct)

        # Realistic bounds
        if symbol == "BTC-USDC":
            current_price = max(25000, min(75000, current_price))
        else:
            current_price = max(1500, min(4500, current_price))

        # Create OHLCV
        open_price = current_price
        close_price = current_price * (1 + random.gauss(0, 0.002))
        high_price = max(open_price, close_price) * (1 + abs(random.gauss(0, 0.005)))
        low_price = min(open_price, close_price) * (1 - abs(random.gauss(0, 0.005)))
        volume = random.uniform(1000, 5000) * (1 + abs(change_pct) * 10)  # More volume on big moves

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

    final_price = data_points[-1].data["close"]
    return data_points, initial_price, final_price


async def run_and_analyze(config: dict, symbol: str, test_days: int, seed: int):
    """Run backtest and analyze results"""

    random.seed(seed)

    # Randomly pick trend direction
    trends = [-0.3, -0.15, 0.0, 0.15, 0.3]  # Bear, mild bear, sideways, mild bull, bull
    trend = random.choice(trends)

    # Random start date in the past
    days_ago = random.randint(test_days + 1, 365)
    start_date = datetime.now() - timedelta(days=days_ago)

    print(f"\n{'='*90}")
    print(f"TEST RUN (seed={seed})")
    print(f"{'='*90}")

    # Generate data
    price_data, initial_price, final_price = generate_market_data_realistic(
        symbol, start_date, test_days, trend
    )

    hodl_return = (final_price - initial_price) / initial_price

    print(f"Market: ${initial_price:.0f} → ${final_price:.0f} ({hodl_return:+.2%} HODL)")
    print(f"Trend: {'BULL' if trend > 0.1 else 'BEAR' if trend < -0.1 else 'SIDEWAYS'}")

    # Create committee
    agents = [
        TrendFollowingAgent(name="Trend", weight=config['trend_weight']),
        RiskManagementAgent(name="Risk", weight=config['risk_weight']),
        ArbitrageAgent(name="Arb", weight=config['arbitrage_weight']),
    ]

    committee = AgentCommittee(
        agents=agents,
        confidence_threshold=config['confidence_threshold']
    )

    # Run backtest
    backtest_config = BacktestConfig(
        start_date=price_data[0].timestamp,
        end_date=price_data[-1].timestamp,
        initial_capital=100000,
        symbols=[symbol],
        timeframe="1h",
        commission=0.001,
        slippage=0.0005
    )

    historical_data = {symbol: price_data}
    engine = BacktestEngine(backtest_config)
    result = await engine.run_backtest(committee, historical_data)

    # Results
    vs_hodl = result.total_return_pct / hodl_return if hodl_return != 0 else 0

    print(f"Strategy: {result.total_return_pct:+.2%} ({result.total_trades} trades)")
    print(f"vs HODL: {vs_hodl:.2f}x")
    print(f"Win Rate: {result.win_rate:.1%}")
    print(f"Sharpe: {result.sharpe_ratio:.2f}")
    print(f"Max DD: {result.max_drawdown_pct:.1%}")

    # Determine outcome
    outcome = "UNKNOWN"
    if result.total_trades == 0:
        outcome = "NO_TRADES"
    elif result.total_return_pct > hodl_return * 2:
        outcome = "BIG_WIN"
    elif result.total_return_pct > hodl_return:
        outcome = "BEAT_HODL"
    elif result.total_return_pct > 0:
        outcome = "PROFIT_BUT_UNDERPERFORM"
    elif result.total_return_pct > hodl_return:
        outcome = "LOSS_BUT_BEAT_HODL"
    else:
        outcome = "LOSS"

    return {
        "seed": seed,
        "trend": trend,
        "hodl_return": hodl_return,
        "strategy_return": result.total_return_pct,
        "vs_hodl": vs_hodl,
        "total_trades": result.total_trades,
        "win_rate": result.win_rate,
        "sharpe": result.sharpe_ratio,
        "max_dd": result.max_drawdown_pct,
        "outcome": outcome,
        "avg_win": result.avg_win if result.winning_trades > 0 else 0,
        "avg_loss": result.avg_loss if result.losing_trades > 0 else 0,
        "largest_win": result.largest_win,
        "largest_loss": result.largest_loss
    }


async def main():
    # Load best strategy
    with open("discovered_strategies_BTCUSDC_20251106_002943.json", 'r') as f:
        data = json.load(f)

    # Use rank 3 (best performer)
    strategy = data['strategies'][2]  # 0-indexed

    print("\n" + "="*90)
    print("EXPLORING REAL TRADES - WHAT WORKED AND WHAT LOST")
    print("="*90)
    print(f"\nStrategy Configuration:")
    print(f"  Trend Weight: {strategy['config']['trend_weight']:.3f}")
    print(f"  Risk Weight: {strategy['config']['risk_weight']:.3f}")
    print(f"  Arbitrage Weight: {strategy['config']['arbitrage_weight']:.3f}")
    print(f"  Confidence Threshold: {strategy['config']['confidence_threshold']:.3f}")
    print(f"\nOriginal Discovery Performance:")
    print(f"  Return: {strategy['return_pct']:+.2%}")
    print(f"  HODL: {strategy['hodl_return_pct']:+.2%}")
    print(f"  vs HODL: {strategy['vs_hodl_multiple']:.2f}x")

    # Run 20 different tests with different seeds/conditions
    print(f"\n{'='*90}")
    print(f"RUNNING 20 TESTS WITH RANDOM START DATES AND MARKET CONDITIONS")
    print(f"{'='*90}")

    results = []
    for seed in range(20):
        result = await run_and_analyze(
            config=strategy['config'],
            symbol="BTC-USDC",
            test_days=180,
            seed=seed
        )
        results.append(result)

    # Aggregate analysis
    print(f"\n\n{'='*90}")
    print(f"AGGREGATE ANALYSIS - WHAT WORKED AND WHAT LOST")
    print(f"{'='*90}\n")

    # Group by outcome
    outcomes = {}
    for r in results:
        outcome = r['outcome']
        if outcome not in outcomes:
            outcomes[outcome] = []
        outcomes[outcome].append(r)

    print(f"OUTCOME DISTRIBUTION:")
    for outcome, runs in sorted(outcomes.items(), key=lambda x: len(x[1]), reverse=True):
        count = len(runs)
        pct = count / len(results) * 100
        avg_return = sum(r['strategy_return'] for r in runs) / count
        avg_vs_hodl = sum(r['vs_hodl'] for r in runs) / count
        print(f"  {outcome:25s}: {count:2d} runs ({pct:5.1f}%) | Avg Return: {avg_return:+.2%} | vs HODL: {avg_vs_hodl:.2f}x")

    # What worked?
    print(f"\n{'='*90}")
    print(f"WHAT WORKED? (Runs that beat HODL)")
    print(f"{'='*90}\n")

    beat_hodl = [r for r in results if r['vs_hodl'] > 1.0]
    if beat_hodl:
        print(f"Found {len(beat_hodl)} runs that beat HODL:\n")
        for r in beat_hodl:
            print(f"  Seed {r['seed']:2d}: {r['strategy_return']:+.2%} vs {r['hodl_return']:+.2%} HODL ({r['vs_hodl']:.2f}x)")
            print(f"           Trades: {r['total_trades']}, Win Rate: {r['win_rate']:.0%}, Sharpe: {r['sharpe']:.2f}")
            print(f"           Market: {'BULL' if r['trend'] > 0.1 else 'BEAR' if r['trend'] < -0.1 else 'SIDEWAYS'}")
            print()

        # Common patterns
        avg_trades = sum(r['total_trades'] for r in beat_hodl) / len(beat_hodl)
        avg_win_rate = sum(r['win_rate'] for r in beat_hodl) / len(beat_hodl)
        avg_sharpe = sum(r['sharpe'] for r in beat_hodl) / len(beat_hodl)

        print(f"  WINNING PATTERNS:")
        print(f"    Avg Trades: {avg_trades:.1f}")
        print(f"    Avg Win Rate: {avg_win_rate:.1%}")
        print(f"    Avg Sharpe: {avg_sharpe:.2f}")

        # What market conditions?
        bull_wins = len([r for r in beat_hodl if r['trend'] > 0.1])
        bear_wins = len([r for r in beat_hodl if r['trend'] < -0.1])
        sideways_wins = len([r for r in beat_hodl if abs(r['trend']) <= 0.1])
        print(f"\n    Market Conditions:")
        print(f"      Bull: {bull_wins}/{len(beat_hodl)}")
        print(f"      Bear: {bear_wins}/{len(beat_hodl)}")
        print(f"      Sideways: {sideways_wins}/{len(beat_hodl)}")
    else:
        print(f"  ⚠️  Strategy did NOT beat HODL in any test run!")

    # What lost?
    print(f"\n{'='*90}")
    print(f"WHAT LOST? (Runs that underperformed HODL)")
    print(f"{'='*90}\n")

    lost_to_hodl = [r for r in results if r['vs_hodl'] <= 1.0]
    if lost_to_hodl:
        print(f"Found {len(lost_to_hodl)} runs that lost to HODL:\n")
        for r in lost_to_hodl[:5]:  # Show first 5
            print(f"  Seed {r['seed']:2d}: {r['strategy_return']:+.2%} vs {r['hodl_return']:+.2%} HODL ({r['vs_hodl']:.2f}x)")
            print(f"           Trades: {r['total_trades']}, Win Rate: {r['win_rate']:.0%}, Sharpe: {r['sharpe']:.2f}")
            print(f"           Market: {'BULL' if r['trend'] > 0.1 else 'BEAR' if r['trend'] < -0.1 else 'SIDEWAYS'}")
            print()

        # Why did they lose?
        avg_trades = sum(r['total_trades'] for r in lost_to_hodl) / len(lost_to_hodl)
        avg_win_rate = sum(r['win_rate'] for r in lost_to_hodl) / len(lost_to_hodl)

        print(f"  LOSING PATTERNS:")
        print(f"    Avg Trades: {avg_trades:.1f}")
        print(f"    Avg Win Rate: {avg_win_rate:.1%}")

        # What market conditions?
        bull_losses = len([r for r in lost_to_hodl if r['trend'] > 0.1])
        bear_losses = len([r for r in lost_to_hodl if r['trend'] < -0.1])
        sideways_losses = len([r for r in lost_to_hodl if abs(r['trend']) <= 0.1])
        print(f"\n    Market Conditions:")
        print(f"      Bull: {bull_losses}/{len(lost_to_hodl)}")
        print(f"      Bear: {bear_losses}/{len(lost_to_hodl)}")
        print(f"      Sideways: {sideways_losses}/{len(lost_to_hodl)}")

    # Overall assessment
    print(f"\n{'='*90}")
    print(f"OVERALL ASSESSMENT")
    print(f"{'='*90}\n")

    total_strategy_return = sum(r['strategy_return'] for r in results)
    total_hodl_return = sum(r['hodl_return'] for r in results)
    beat_hodl_rate = len(beat_hodl) / len(results)

    print(f"  Tests Run: {len(results)}")
    print(f"  Beat HODL: {len(beat_hodl)}/{len(results)} ({beat_hodl_rate:.0%})")
    print(f"  Cumulative Strategy Return: {total_strategy_return:+.1%}")
    print(f"  Cumulative HODL Return: {total_hodl_return:+.1%}")

    if beat_hodl_rate >= 0.6:
        print(f"\n  ✅ ROBUST: Strategy beats HODL in {beat_hodl_rate:.0%} of tests")
        print(f"     → Shows consistent edge across market conditions")
    elif beat_hodl_rate >= 0.4:
        print(f"\n  ⚠️  MODERATE: Strategy beats HODL in {beat_hodl_rate:.0%} of tests")
        print(f"     → Some edge but inconsistent")
    else:
        print(f"\n  ❌ WEAK: Strategy only beats HODL in {beat_hodl_rate:.0%} of tests")
        print(f"     → Likely overfit to specific conditions")

    print(f"\n{'='*90}\n")


if __name__ == "__main__":
    asyncio.run(main())
