#!/usr/bin/env python3
"""
Real Data Backtest Demo

Uses the Coinswarm Worker to fetch REAL historical data
from multiple exchanges (Kraken, Coinbase, etc.)

Worker URL: https://coinswarm.bamn86.workers.dev
"""

import asyncio
import logging
from datetime import datetime

from coinswarm.data_ingest.coinswarm_worker_client import CoinswarmWorkerClient
from coinswarm.agents.trend_agent import TrendFollowingAgent
from coinswarm.agents.risk_agent import RiskManagementAgent
from coinswarm.agents.arbitrage_agent import ArbitrageAgent
from coinswarm.agents.committee import AgentCommittee
from coinswarm.backtesting.backtest_engine import BacktestEngine, BacktestConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


async def run_real_data_backtest():
    """Run backtest with real market data from Worker"""

    print("\n" + "="*70)
    print("REAL DATA BACKTEST")
    print("="*70 + "\n")

    print("Data Source: Coinswarm Worker (Multi-Exchange Aggregated)")
    print("  - Kraken")
    print("  - Coinbase")
    print("  - CoinGecko")
    print("  - CryptoCompare")
    print()

    # Initialize Worker client
    worker = CoinswarmWorkerClient()

    # Fetch real BTC data
    print("Step 1: Fetching real BTC price data...")
    print("-" * 70)

    try:
        btc_data = await worker.fetch_price_data("BTC", days=30)

        if not btc_data:
            print("❌ No data received from Worker")
            print("   Worker might be rate limited. Try again in a minute.")
            return

        print(f"✓ Fetched {len(btc_data)} hourly candles")
        print(f"  Date range: {btc_data[0].timestamp.date()} to {btc_data[-1].timestamp.date()}")
        print(f"  Price: ${btc_data[0].data['price']:,.2f} → ${btc_data[-1].data['price']:,.2f}")

        start_price = btc_data[0].data['price']
        end_price = btc_data[-1].data['price']
        return_pct = ((end_price - start_price) / start_price) * 100
        print(f"  Market return: {return_pct:+.2f}%")
        print()

    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        print("   Worker might be rate limited. Try again in a minute.")
        return

    # Show sample data
    print("Sample Data (first 5 hours):")
    print("-" * 70)
    for point in btc_data[:5]:
        price = point.data['price']
        volume = point.data.get('volume', 0)
        variance = point.data.get('variance', 0)
        print(f"{point.timestamp}  ${price:>10,.2f}  Vol: {volume:>8,.1f}  Var: {variance:.2%}")
    print()

    # Create agent committee
    print("Step 2: Creating agent committee...")
    agents = [
        TrendFollowingAgent(name="TrendFollower", weight=1.0),
        RiskManagementAgent(name="RiskManager", weight=2.0),
        ArbitrageAgent(name="ArbitrageHunter", weight=2.0),
    ]

    committee = AgentCommittee(
        agents=agents,
        confidence_threshold=0.6
    )
    print(f"✓ Committee created with {len(agents)} agents")
    print()

    # Configure backtest
    start_date = btc_data[0].timestamp
    end_date = btc_data[-1].timestamp

    config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        initial_capital=100000,
        symbols=["BTC-USD"],
        timeframe="1h",
        commission=0.001,  # 0.1%
        slippage=0.0005    # 0.05%
    )

    print("Step 3: Running backtest on REAL data...")
    print(f"  Initial Capital: ${config.initial_capital:,.0f}")
    print(f"  Period: {start_date.date()} to {end_date.date()} ({len(btc_data)} hours)")
    print(f"  Timeframe: {config.timeframe}")
    print(f"  Commission: {config.commission:.1%}")
    print(f"  Slippage: {config.slippage:.2%}")
    print()

    # Prepare data for backtest
    historical_data = {
        "BTC-USD": btc_data
    }

    # Run backtest
    engine = BacktestEngine(config)
    result = await engine.run_backtest(committee, historical_data)

    # Display results
    print("\n" + "="*70)
    print("BACKTEST RESULTS (REAL DATA)")
    print("="*70)
    print(f"Initial Capital:     ${result.initial_capital:,.0f}")
    print(f"Final Capital:       ${result.final_capital:,.0f}")
    print(f"Total Return:        ${result.total_return:+,.0f} ({result.total_return_pct:+.2%})")
    print()
    print(f"Market Return:       {return_pct:+.2f}%")
    print(f"Alpha:               {(result.total_return_pct * 100 - return_pct):+.2f}%")
    print()
    print(f"Total Trades:        {result.total_trades}")
    print(f"Winning Trades:      {result.winning_trades}")
    print(f"Losing Trades:       {result.losing_trades}")
    print(f"Win Rate:            {result.win_rate:.1%}")
    print()
    print(f"Sharpe Ratio:        {result.sharpe_ratio:.2f}")
    print(f"Sortino Ratio:       {result.sortino_ratio:.2f}")
    print(f"Max Drawdown:        {result.max_drawdown_pct:.1%}")
    print(f"Profit Factor:       {result.profit_factor:.2f}")
    print("="*70 + "\n")

    # Interpretation
    print("ANALYSIS:")
    print("-" * 70)

    if result.total_return_pct * 100 > return_pct:
        alpha = (result.total_return_pct * 100 - return_pct)
        print(f"✅ OUTPERFORMED market by {alpha:+.2f}%")
        print("   Strategy generated positive alpha!")
    elif result.total_return_pct * 100 > 0:
        print(f"✅ POSITIVE returns ({result.total_return_pct:+.2%})")
        print("   But underperformed buy-and-hold")
    else:
        print(f"❌ NEGATIVE returns ({result.total_return_pct:+.2%})")
        print("   Strategy needs tuning")

    print()

    if result.sharpe_ratio > 1.5:
        print("✅ EXCELLENT Sharpe ratio (>1.5) - strong risk-adjusted returns")
    elif result.sharpe_ratio > 1.0:
        print("✅ GOOD Sharpe ratio (>1.0) - returns justify risk")
    else:
        print("⚠️  LOW Sharpe ratio (<1.0) - high risk for returns")

    print()

    if result.win_rate > 0.55:
        print(f"✅ HIGH win rate ({result.win_rate:.1%}) - agents picking winners")
    elif result.win_rate > 0.5:
        print(f"✅ GOOD win rate ({result.win_rate:.1%}) - more wins than losses")
    else:
        print(f"⚠️  LOW win rate ({result.win_rate:.1%}) - need better signals")

    print()

    # Show top trades
    if result.trades:
        print("\nTop 5 Profitable Trades:")
        print("-" * 70)
        sorted_trades = sorted(result.trades, key=lambda t: t.pnl, reverse=True)[:5]
        for i, trade in enumerate(sorted_trades, 1):
            emoji = "✅" if trade.pnl > 0 else "❌"
            print(f"{i}. {emoji} {trade.action} @ ${trade.entry_price:,.2f}")
            print(f"   P&L: ${trade.pnl:+,.2f} ({trade.pnl_pct:+.1%})")

        print()

        print("Top 5 Worst Trades:")
        print("-" * 70)
        worst_trades = sorted(result.trades, key=lambda t: t.pnl)[:5]
        for i, trade in enumerate(worst_trades, 1):
            emoji = "✅" if trade.pnl > 0 else "❌"
            print(f"{i}. {emoji} {trade.action} @ ${trade.entry_price:,.2f}")
            print(f"   P&L: ${trade.pnl:+,.2f} ({trade.pnl_pct:+.1%})")

    print()
    print("="*70)
    print("✅ REAL DATA BACKTEST COMPLETE")
    print("="*70)
    print()
    print("This was REAL market data from multiple exchanges!")
    print("  - Actual BTC price movements")
    print("  - Real volatility and trends")
    print("  - Aggregated from Kraken, Coinbase, etc.")
    print()
    print("Next steps:")
    print("  1. Test different agent weights")
    print("  2. Adjust confidence threshold")
    print("  3. Test on longer periods (60-90 days)")
    print("  4. Try ETH and SOL data")
    print("  5. Validate across multiple random windows")
    print()


if __name__ == "__main__":
    asyncio.run(run_real_data_backtest())
