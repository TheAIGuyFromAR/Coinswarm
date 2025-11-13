#!/usr/bin/env python3
"""
Real Data Demo - Comprehensive Backtesting

Fetches real historical data and runs backtests:
1. Spot pairs (BTC-USDC, ETH-USDC, SOL-USDC)
2. Cross pairs (BTC-SOL, ETH-BTC, ETH-SOL) for arbitrage
3. Random 1-month windows over 3-month period
4. Arbitrage detection
5. Historical news/tweets (coming soon)

No credentials needed - uses public Binance API
"""

import asyncio
import logging
from datetime import datetime, timedelta

from coinswarm.agents.arbitrage_agent import ArbitrageAgent
from coinswarm.agents.committee import AgentCommittee
from coinswarm.agents.risk_agent import RiskManagementAgent
from coinswarm.agents.trend_agent import TrendFollowingAgent
from coinswarm.backtesting.backtest_engine import BacktestConfig, BacktestEngine
from coinswarm.data_ingest.historical_data_fetcher import HistoricalDataFetcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


async def demo_fetch_real_data():
    """Demo 1: Fetch real historical data from Binance"""

    print("\n" + "="*70)
    print("DEMO 1: Fetching Real Historical Data")
    print("="*70 + "\n")

    fetcher = HistoricalDataFetcher()

    # Fetch 3 months of data
    logger.info("Fetching 3 months of real data from Binance...")
    start_time = datetime.now()

    data = await fetcher.fetch_all_historical_data(months=3, timeframe="1h")  # 1h for speed

    duration = (datetime.now() - start_time).total_seconds()

    print(f"\n✓ Fetched data in {duration:.1f}s:")
    print("-" * 70)

    for symbol, points in sorted(data.items()):
        if points:
            first_price = points[0].data.get("price", 0)
            last_price = points[-1].data.get("price", 0)
            change_pct = ((last_price - first_price) / first_price) * 100

            print(f"{symbol:12} {len(points):>6} ticks  "
                  f"${first_price:>10,.2f} → ${last_price:>10,.2f}  "
                  f"({change_pct:+.1f}%)")

    print("="*70 + "\n")

    return data


async def demo_random_windows():
    """Demo 2: Generate random 1-month windows"""

    print("\n" + "="*70)
    print("DEMO 2: Random 1-Month Windows (Avoid Overfitting)")
    print("="*70 + "\n")

    fetcher = HistoricalDataFetcher()

    # Generate 10 random windows
    windows = fetcher.generate_random_windows(
        total_months=3,
        window_size_days=30,
        num_windows=10
    )

    print("Generated 10 random 30-day windows:")
    print("-" * 70)

    for i, (start, end) in enumerate(windows, 1):
        days = (end - start).days
        print(f"Window {i:2}: {start.strftime('%Y-%m-%d')} → {end.strftime('%Y-%m-%d')}  ({days} days)")

    print("="*70 + "\n")

    return windows


async def demo_backtest_with_arbitrage(historical_data):
    """Demo 3: Run backtest with arbitrage agent"""

    print("\n" + "="*70)
    print("DEMO 3: Backtest with Arbitrage Detection")
    print("="*70 + "\n")

    # Create agent committee with arbitrage agent
    agents = [
        TrendFollowingAgent(name="TrendFollower", weight=1.0),
        RiskManagementAgent(name="RiskManager", weight=2.0),
        ArbitrageAgent(name="ArbitrageHunter", weight=2.0),  # ← New!
    ]

    committee = AgentCommittee(
        agents=agents,
        confidence_threshold=0.7
    )

    logger.info(f"Committee: {len(agents)} agents (including ArbitrageAgent)")

    # Select one pair for demo (BTC-USDC)
    btc_data = historical_data.get("BTC-USDC")
    if not btc_data:
        print("❌ No BTC-USDC data available")
        return

    # Configure backtest (use first month)
    start_date = btc_data[0].timestamp
    end_date = start_date + timedelta(days=30)

    config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        initial_capital=100000,
        symbols=["BTC-USDC"],
        timeframe="1h",
        commission=0.001,
        slippage=0.0005
    )

    # Run backtest
    logger.info("Running backtest with arbitrage detection...")
    start_time = datetime.now()

    engine = BacktestEngine(config)
    result = await engine.run_backtest(committee, {"BTC-USDC": btc_data[:720]})  # First 30 days

    duration = (datetime.now() - start_time).total_seconds()

    # Display results
    print("\n" + "="*70)
    print("BACKTEST RESULTS (30 days)")
    print("="*70)
    print(f"Duration:        {duration:.1f}s")
    print(f"Initial Capital: ${result.initial_capital:,.0f}")
    print(f"Final Capital:   ${result.final_capital:,.0f}")
    print(f"Total Return:    ${result.total_return:+,.0f} ({result.total_return_pct:+.2%})")
    print()
    print(f"Total Trades:    {result.total_trades}")
    print(f"Win Rate:        {result.win_rate:.1%}")
    print(f"Sharpe Ratio:    {result.sharpe_ratio:.2f}")
    print(f"Max Drawdown:    {result.max_drawdown_pct:.1%}")
    print("="*70 + "\n")

    # Show arbitrage stats
    arb_agent = agents[2]  # ArbitrageAgent
    arb_stats = arb_agent.get_arbitrage_stats()

    print("ARBITRAGE STATISTICS:")
    print("-"*70)
    print(f"Opportunities Found:    {arb_stats['opportunities_found']}")
    print(f"Opportunities Executed: {arb_stats['opportunities_executed']}")
    print(f"Execution Rate:         {arb_stats['execution_rate']:.1%}")
    print(f"Min Profit Threshold:   {arb_stats['min_profit_threshold']:.2%}")
    print(f"Total Fee (3 legs):     {arb_stats['total_fee_pct']:.2%}")
    print("="*70 + "\n")

    return result


async def demo_multiple_windows(historical_data):
    """Demo 4: Test multiple random windows"""

    print("\n" + "="*70)
    print("DEMO 4: Test Multiple Random Windows")
    print("="*70 + "\n")

    fetcher = HistoricalDataFetcher()

    # Generate 5 random windows
    windows = fetcher.generate_random_windows(
        total_months=3,
        window_size_days=30,
        num_windows=5
    )

    results = []

    for i, (start, end) in enumerate(windows, 1):
        logger.info(f"Testing window {i}/5: {start.date()} → {end.date()}")

        # Get data for this window
        btc_data = historical_data.get("BTC-USDC", [])
        window_data = [
            d for d in btc_data
            if start <= d.timestamp <= end
        ]

        if len(window_data) < 100:
            logger.warning(f"Not enough data for window {i}, skipping")
            continue

        # Create committee
        agents = [
            TrendFollowingAgent(name="TrendFollower", weight=1.0),
            RiskManagementAgent(name="RiskManager", weight=2.0),
            ArbitrageAgent(name="ArbitrageHunter", weight=2.0),
        ]

        committee = AgentCommittee(agents=agents, confidence_threshold=0.7)

        # Configure backtest
        config = BacktestConfig(
            start_date=start,
            end_date=end,
            initial_capital=100000,
            symbols=["BTC-USDC"],
            timeframe="1h"
        )

        # Run backtest
        engine = BacktestEngine(config)
        result = await engine.run_backtest(committee, {"BTC-USDC": window_data})

        results.append((i, start, end, result))

        logger.info(f"Window {i} complete: return={result.total_return_pct:+.2%}, "
                   f"win_rate={result.win_rate:.1%}, sharpe={result.sharpe_ratio:.2f}")

    # Summary
    print("\n" + "="*70)
    print("MULTI-WINDOW BACKTEST SUMMARY")
    print("="*70)

    if results:
        avg_return = sum(r[3].total_return_pct for r in results) / len(results)
        avg_win_rate = sum(r[3].win_rate for r in results) / len(results)
        avg_sharpe = sum(r[3].sharpe_ratio for r in results) / len(results)

        print(f"Windows Tested:    {len(results)}")
        print(f"Avg Return:        {avg_return:+.2%}")
        print(f"Avg Win Rate:      {avg_win_rate:.1%}")
        print(f"Avg Sharpe Ratio:  {avg_sharpe:.2f}")
        print()

        print("Individual Windows:")
        print("-"*70)

        for i, start, end, result in results:
            status = "✅" if result.total_return_pct > 0 else "❌"
            print(f"Window {i} {status}  {start.strftime('%Y-%m-%d')} → {end.strftime('%Y-%m-%d')}  "
                  f"Return: {result.total_return_pct:+.2%}  "
                  f"Win Rate: {result.win_rate:.1%}  "
                  f"Sharpe: {result.sharpe_ratio:.2f}")

        print("="*70 + "\n")

    return results


async def main():
    """Run all demos"""

    print("\n")
    print("█" * 70)
    print("█" + " " * 68 + "█")
    print("█" + "  COINSWARM - REAL DATA BACKTEST DEMO".center(68) + "█")
    print("█" + "  Testing on real historical data from Binance".center(68) + "█")
    print("█" + " " * 68 + "█")
    print("█" * 70)

    try:
        # Demo 1: Fetch real data
        historical_data = await demo_fetch_real_data()

        if not historical_data:
            print("❌ Failed to fetch historical data")
            return

        # Demo 2: Show random windows
        await demo_random_windows()

        # Demo 3: Single backtest with arbitrage
        await demo_backtest_with_arbitrage(historical_data)

        # Demo 4: Multiple random windows
        await demo_multiple_windows(historical_data)

        # Final summary
        print("\n" + "="*70)
        print("✅ DEMO COMPLETE!")
        print("="*70)
        print()
        print("What you just saw:")
        print("  1. Real historical data from Binance (spot + cross pairs)")
        print("  2. Random 1-month windows to avoid overfitting")
        print("  3. Arbitrage detection (triangular across pairs)")
        print("  4. Multiple window testing (walk-forward validation)")
        print()
        print("Next steps:")
        print("  - Add historical news/tweets (data sources TBD)")
        print("  - Add macro trends (FRED API)")
        print("  - Add on-chain data (Glassnode)")
        print("  - Deploy to Coinbase sandbox")
        print("  - Go live!")
        print("="*70 + "\n")

    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        print("\n❌ Demo encountered an error. Check logs above.")


if __name__ == "__main__":
    asyncio.run(main())
