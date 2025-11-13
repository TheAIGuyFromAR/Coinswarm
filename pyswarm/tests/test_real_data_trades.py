#!/usr/bin/env python3
"""
Test Strategy on REAL DATA - 1 Month Windows

Fetches real BTC data from Cloudflare Worker and tests discovered strategies
on random 1-month windows to see what actually works.

Usage:
    python test_real_data_trades.py
"""

import asyncio
import json
import random

from coinswarm.agents.arbitrage_agent import ArbitrageAgent
from coinswarm.agents.committee import AgentCommittee
from coinswarm.agents.risk_agent import RiskManagementAgent
from coinswarm.agents.trend_agent import TrendFollowingAgent
from coinswarm.backtesting.backtest_engine import BacktestConfig, BacktestEngine
from coinswarm.data_ingest.base import DataPoint
from coinswarm.data_ingest.coinswarm_worker_client import CoinswarmWorkerClient


async def fetch_real_data(symbol: str, days: int) -> list[DataPoint]:
    """
    Fetch real historical data from Cloudflare Worker

    Worker has timeout limits at ~50 days, so fetch in 30-day chunks
    """
    client = CoinswarmWorkerClient()

    print(f"📡 Fetching {days} days of real {symbol} data from Cloudflare Worker...")

    # For requests under 30 days, fetch directly
    if days <= 30:
        try:
            data = await client.fetch_price_data(symbol=symbol, days=days, aggregate=True)
            print(f"✅ Received {len(data)} hourly candles ({len(data)/24:.1f} days)")
            return data
        except Exception as e:
            print(f"❌ Error fetching data: {e}")
            return None

    # For larger requests, fetch in 30-day chunks
    print("   Fetching in 30-day chunks to avoid Worker timeout...")
    chunk_size = 30
    all_data = []

    chunks_needed = (days + chunk_size - 1) // chunk_size

    for i in range(chunks_needed):
        chunk_days = min(chunk_size, days - i * chunk_size)
        print(f"   Chunk {i+1}/{chunks_needed}: {chunk_days} days...", end=" ")

        try:
            chunk_data = await client.fetch_price_data(symbol=symbol, days=chunk_days, aggregate=True)
            all_data.extend(chunk_data)
            print(f"✅ {len(chunk_data)} candles")
        except Exception as e:
            print(f"❌ Error: {e}")
            if len(all_data) == 0:
                return None
            break

    if all_data:
        # Remove duplicates and sort
        unique_data = {}
        for point in all_data:
            unique_data[point.timestamp] = point
        sorted_data = sorted(unique_data.values(), key=lambda p: p.timestamp)
        print(f"✅ Total: {len(sorted_data)} candles ({len(sorted_data)/24:.1f} days)")
        return sorted_data

    return None


def create_1month_windows(data: list[DataPoint], window_days: int = 30) -> list[tuple]:
    """
    Create random 1-month windows from the dataset

    Returns list of (start_idx, end_idx) tuples
    """
    window_hours = window_days * 24
    max_start = len(data) - window_hours

    if max_start <= 0:
        return [(0, len(data) - 1)]

    # Create windows at random start points
    windows = []
    num_windows = min(10, max_start // (window_hours // 2))  # Max 10 windows, non-overlapping

    for _ in range(num_windows):
        start_idx = random.randint(0, max_start)
        end_idx = min(start_idx + window_hours, len(data) - 1)
        windows.append((start_idx, end_idx))

    return windows


async def test_window(
    data: list[DataPoint],
    start_idx: int,
    end_idx: int,
    config: dict,
    symbol: str
) -> dict:
    """Test strategy on a single window"""

    window_data = data[start_idx:end_idx+1]

    if len(window_data) < 24:
        return None

    initial_price = window_data[0].data["close"]
    final_price = window_data[-1].data["close"]
    hodl_return = (final_price - initial_price) / initial_price

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
        start_date=window_data[0].timestamp,
        end_date=window_data[-1].timestamp,
        initial_capital=100000,
        symbols=[symbol],
        timeframe="1h",
        commission=0.001,
        slippage=0.0005
    )

    historical_data = {symbol: window_data}
    engine = BacktestEngine(backtest_config)
    result = await engine.run_backtest(committee, historical_data)

    # Calculate vs HODL
    # If HODL lost money and strategy did better (even 0%), that's a win
    if hodl_return < 0:
        if result.total_return_pct >= hodl_return:
            # Strategy beat HODL by preserving capital
            vs_hodl = abs(hodl_return) / max(abs(result.total_return_pct), 0.0001)
        else:
            vs_hodl = result.total_return_pct / hodl_return
    elif hodl_return > 0:
        vs_hodl = result.total_return_pct / hodl_return if hodl_return != 0 else 0
    else:
        vs_hodl = 0

    return {
        "start_date": window_data[0].timestamp,
        "end_date": window_data[-1].timestamp,
        "days": len(window_data) / 24,
        "initial_price": initial_price,
        "final_price": final_price,
        "hodl_return": hodl_return,
        "strategy_return": result.total_return_pct,
        "vs_hodl": vs_hodl,
        "total_trades": result.total_trades,
        "win_rate": result.win_rate,
        "sharpe": result.sharpe_ratio,
        "max_dd": result.max_drawdown_pct,
        "avg_win": result.avg_win if result.winning_trades > 0 else 0,
        "avg_loss": result.avg_loss if result.losing_trades > 0 else 0,
        "profit_factor": result.profit_factor
    }


async def main():
    print("\n" + "="*90)
    print("TESTING STRATEGY ON REAL DATA - 1 MONTH WINDOWS")
    print("="*90 + "\n")

    # Load best strategy
    with open("discovered_strategies_BTCUSDC_20251106_002943.json") as f:
        data = json.load(f)

    strategy = data['strategies'][2]  # Rank 3 (best)

    print("Strategy Configuration:")
    print(f"  Trend Weight: {strategy['config']['trend_weight']:.3f}")
    print(f"  Risk Weight: {strategy['config']['risk_weight']:.3f}")
    print(f"  Arbitrage Weight: {strategy['config']['arbitrage_weight']:.3f}")
    print(f"  Confidence Threshold: {strategy['config']['confidence_threshold']:.3f}\n")

    # Fetch real data - start with 90 days for multiple test windows
    print("="*90)
    print("PHASE 1: Fetching initial dataset (90 days)")
    print("="*90 + "\n")

    real_data = await fetch_real_data(symbol="BTC", days=90)

    if real_data is None:
        print("\n⚠️  Could not fetch real data. Please check:")
        print("   1. Cloudflare Worker is running at https://coinswarm.bamn86.workers.dev")
        print("   2. Worker has not hit rate limits")
        print("   3. Internet connection is available\n")
        return

    # Create 1-month windows with random start dates
    print("\n" + "="*90)
    print("PHASE 2: Testing on random 1-month windows")
    print("="*90 + "\n")

    windows = create_1month_windows(real_data, window_days=30)
    print(f"Created {len(windows)} random 1-month test windows from the dataset\n")

    # Test each window
    results = []
    for i, (start_idx, end_idx) in enumerate(windows):
        print(f"Window {i+1}/{len(windows)}:")
        print(f"  Data range: {real_data[start_idx].timestamp.date()} to {real_data[end_idx].timestamp.date()}")

        result = await test_window(
            data=real_data,
            start_idx=start_idx,
            end_idx=end_idx,
            config=strategy['config'],
            symbol="BTC-USD"
        )

        if result:
            results.append(result)
            print(f"  Market: ${result['initial_price']:.0f} → ${result['final_price']:.0f} ({result['hodl_return']:+.2%} HODL)")
            print(f"  Strategy: {result['strategy_return']:+.2%} ({result['total_trades']} trades)")
            print(f"  vs HODL: {result['vs_hodl']:.2f}x")
            print(f"  Win Rate: {result['win_rate']:.0%}, Sharpe: {result['sharpe']:.2f}")
            print()

    # Analysis
    if not results:
        print("No results to analyze!")
        return

    print("\n" + "="*90)
    print("RESULTS SUMMARY - WHAT WORKED AND WHAT LOST")
    print("="*90 + "\n")

    # Separate winners and losers
    beat_hodl = [r for r in results if r['vs_hodl'] > 1.0]
    lost_to_hodl = [r for r in results if r['vs_hodl'] <= 1.0]

    print(f"Total Windows Tested: {len(results)}")
    print(f"Beat HODL: {len(beat_hodl)}/{len(results)} ({len(beat_hodl)/len(results):.0%})")
    print(f"Lost to HODL: {len(lost_to_hodl)}/{len(results)} ({len(lost_to_hodl)/len(results):.0%})\n")

    # What worked?
    if beat_hodl:
        print(f"{'='*90}")
        print("✅ WHAT WORKED (Strategies that beat HODL)")
        print(f"{'='*90}\n")

        for i, r in enumerate(beat_hodl):
            print(f"{i+1}. {r['start_date'].date()} to {r['end_date'].date()}:")
            print(f"   Market: ${r['initial_price']:.0f} → ${r['final_price']:.0f} ({r['hodl_return']:+.2%})")
            print(f"   Strategy: {r['strategy_return']:+.2%} ({r['vs_hodl']:.2f}x HODL)")
            print(f"   Trades: {r['total_trades']}, Win Rate: {r['win_rate']:.0%}, Sharpe: {r['sharpe']:.2f}")

            # Why did it work?
            insights = []
            if r['hodl_return'] < 0 and r['strategy_return'] > r['hodl_return']:
                insights.append(f"Protected capital during {r['hodl_return']:.1%} decline")
            if r['total_trades'] < 10:
                insights.append(f"Very selective ({r['total_trades']} trades)")
            if r['win_rate'] > 0.6:
                insights.append(f"High win rate ({r['win_rate']:.0%})")

            if insights:
                print(f"   💡 Why it worked: {', '.join(insights)}")
            print()

    # What lost?
    if lost_to_hodl:
        print(f"\n{'='*90}")
        print("❌ WHAT LOST (Strategies that underperformed HODL)")
        print(f"{'='*90}\n")

        for i, r in enumerate(lost_to_hodl):
            print(f"{i+1}. {r['start_date'].date()} to {r['end_date'].date()}:")
            print(f"   Market: ${r['initial_price']:.0f} → ${r['final_price']:.0f} ({r['hodl_return']:+.2%})")
            print(f"   Strategy: {r['strategy_return']:+.2%} ({r['vs_hodl']:.2f}x HODL)")
            print(f"   Trades: {r['total_trades']}, Win Rate: {r['win_rate']:.0%}, Sharpe: {r['sharpe']:.2f}")

            # Why did it lose?
            insights = []
            if r['hodl_return'] > 0.05 and r['strategy_return'] < r['hodl_return']:
                insights.append(f"Missed upside in {r['hodl_return']:+.1%} rally")
            if r['total_trades'] == 0:
                insights.append("No trades (too conservative)")
            if r['win_rate'] < 0.5 and r['total_trades'] > 0:
                insights.append(f"Low win rate ({r['win_rate']:.0%})")

            if insights:
                print(f"   💔 Why it lost: {', '.join(insights)}")
            print()

    # Overall patterns
    print(f"\n{'='*90}")
    print("OVERALL PATTERNS")
    print(f"{'='*90}\n")

    total_strategy_return = sum(r['strategy_return'] for r in results)
    total_hodl_return = sum(r['hodl_return'] for r in results)
    avg_trades = sum(r['total_trades'] for r in results) / len(results)

    print(f"Cumulative Strategy Return: {total_strategy_return:+.2%}")
    print(f"Cumulative HODL Return: {total_hodl_return:+.2%}")
    print(f"Average Trades per Window: {avg_trades:.1f}")

    if len(beat_hodl) > 0:
        avg_win_rate = sum(r['win_rate'] for r in beat_hodl) / len(beat_hodl)
        avg_sharpe = sum(r['sharpe'] for r in beat_hodl) / len(beat_hodl)
        print("\nWinning Windows Stats:")
        print(f"  Avg Win Rate: {avg_win_rate:.1%}")
        print(f"  Avg Sharpe: {avg_sharpe:.2f}")

    # Final assessment
    beat_rate = len(beat_hodl) / len(results)
    print(f"\n{'='*90}")
    print("ASSESSMENT")
    print(f"{'='*90}\n")

    if beat_rate >= 0.6:
        print(f"✅ ROBUST: Strategy beats HODL in {beat_rate:.0%} of real data tests")
        print("   Ready for paper trading validation")
    elif beat_rate >= 0.4:
        print(f"⚠️  MODERATE: Strategy beats HODL in {beat_rate:.0%} of tests")
        print("   Needs more data and tuning")
    else:
        print(f"❌ WEAK: Strategy only beats HODL in {beat_rate:.0%} of tests")
        print("   May be overfit to specific conditions")

    print(f"\n{'='*90}")
    print("NEXT STEPS")
    print(f"{'='*90}\n")
    print(f"1. ✅ Tested on {len(results)} random 1-month windows from real data")
    print("2. ⏳ Expand dataset to 6 months (need more Worker calls)")
    print("3. ⏳ Then expand to 1 year")
    print("4. ⏳ Eventually reach 2 years of historical data")
    print("5. ⏳ Test across different market cycles\n")


if __name__ == "__main__":
    asyncio.run(main())
