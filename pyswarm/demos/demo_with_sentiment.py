#!/usr/bin/env python3
"""
Demo: Backtesting with Sentiment Data

Shows how historical news and sentiment data improves trading decisions.

Features:
1. Fetches real price data + sentiment
2. Agents use sentiment in their decisions
3. Compare results: with vs without sentiment
"""

import asyncio
import logging
from datetime import datetime, timedelta

from coinswarm.data_ingest.historical_data_fetcher import HistoricalDataFetcher
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


async def demo_sentiment_integration():
    """Demo: How sentiment data affects trading decisions"""

    print("\n" + "="*70)
    print("DEMO: Backtesting with Sentiment Data")
    print("="*70 + "\n")

    # Initialize data fetcher
    print("📊 Data Sources:")
    print("  - Price: Binance API (spot + cross pairs)")
    print("  - Sentiment: Fear & Greed Index")
    print("  - News: CryptoCompare (if API key available)")
    print("  - Macro: FRED API (if API key available)")
    print()

    # Check for API keys
    import os
    cryptocompare_key = os.getenv("CRYPTOCOMPARE_API_KEY")
    newsapi_key = os.getenv("NEWSAPI_KEY")
    fred_key = os.getenv("FRED_API_KEY")

    if not any([cryptocompare_key, newsapi_key, fred_key]):
        print("💡 TIP: Set API keys for more data sources:")
        print("   export CRYPTOCOMPARE_API_KEY='your_key'")
        print("   export NEWSAPI_KEY='your_key'")
        print("   export FRED_API_KEY='your_key'")
        print()
        print("   See docs/DATA_SOURCES.md for setup instructions")
        print()
        print("   Fear & Greed Index will still work (no key needed)!")
        print()

    fetcher = HistoricalDataFetcher(
        cryptocompare_api_key=cryptocompare_key,
        newsapi_key=newsapi_key
    )

    # Fetch 30 days of data with sentiment
    print("Fetching 30 days of historical data...")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    try:
        historical_data = await fetcher.fetch_all_historical_data(
            months=1,
            timeframe="1h",
            include_sentiment=True  # ← SENTIMENT ENABLED!
        )

        print()
        print("✓ Data fetched successfully!")
        print()
        print("Available data streams:")
        for symbol, data in sorted(historical_data.items()):
            emoji = "💰" if "USDC" in symbol else "📈" if "BTC" in symbol or "ETH" in symbol or "SOL" in symbol else "📊"
            print(f"  {emoji} {symbol:20} {len(data):>6} data points")

        print()

        # Check if we have sentiment data
        has_sentiment = any("SENTIMENT" in k for k in historical_data.keys())

        if has_sentiment:
            print("✅ Sentiment data available! Agents will use it in decisions.")
            print()

            # Show sample sentiment
            btc_sentiment = historical_data.get("BTC-SENTIMENT")
            if btc_sentiment:
                print("Sample BTC sentiment (last 7 days):")
                print("-" * 70)
                for point in btc_sentiment[-7:]:
                    sentiment = point.data.get("sentiment", 0)
                    fear_greed = point.data.get("fear_greed", 50)
                    articles = point.data.get("article_count", 0)

                    emoji = "🔴" if sentiment < -0.3 else "🟡" if sentiment < 0.3 else "🟢"

                    print(f"{point.timestamp.date()} {emoji}  "
                          f"Sentiment: {sentiment:+.2f}  "
                          f"Fear/Greed: {fear_greed:.0f}  "
                          f"Articles: {articles}")
                print()
        else:
            print("⚠️  No sentiment data (API keys not set or service unavailable)")
            print("    Agents will trade based on price only.")
            print()

    except Exception as e:
        logger.error(f"Failed to fetch data: {e}")
        print("\n❌ Data fetch failed. This might be because:")
        print("  - Network restrictions (try Cloudflare Worker)")
        print("  - API rate limits")
        print("  - Service unavailable")
        print()
        print("See INSTRUCTIONS_FOR_OTHER_CLAUDE.md for Cloudflare Worker setup")
        return

    # Run backtest WITH sentiment
    print("="*70)
    print("BACKTEST 1: WITH Sentiment Data")
    print("="*70)
    print()

    btc_data = historical_data.get("BTC-USDC", [])
    btc_sentiment = historical_data.get("BTC-SENTIMENT", [])

    if not btc_data:
        print("❌ No BTC price data available")
        return

    # Create committee
    agents = [
        TrendFollowingAgent(name="TrendFollower", weight=1.0),
        RiskManagementAgent(name="RiskManager", weight=2.0),
        ArbitrageAgent(name="ArbitrageHunter", weight=2.0),
    ]

    committee = AgentCommittee(
        agents=agents,
        confidence_threshold=0.7
    )

    # Configure backtest
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
    engine = BacktestEngine(config)

    # Merge sentiment into price data context
    merged_data = {"BTC-USDC": btc_data}
    if btc_sentiment:
        merged_data["BTC-SENTIMENT"] = btc_sentiment

    result_with_sentiment = await engine.run_backtest(committee, merged_data)

    # Display results
    print("\n" + "="*70)
    print("RESULTS WITH SENTIMENT")
    print("="*70)
    print(f"Initial Capital:  ${result_with_sentiment.initial_capital:,.0f}")
    print(f"Final Capital:    ${result_with_sentiment.final_capital:,.0f}")
    print(f"Total Return:     ${result_with_sentiment.total_return:+,.0f} "
          f"({result_with_sentiment.total_return_pct:+.2%})")
    print()
    print(f"Total Trades:     {result_with_sentiment.total_trades}")
    print(f"Win Rate:         {result_with_sentiment.win_rate:.1%}")
    print(f"Sharpe Ratio:     {result_with_sentiment.sharpe_ratio:.2f}")
    print(f"Max Drawdown:     {result_with_sentiment.max_drawdown_pct:.1%}")
    print("="*70 + "\n")

    # Compare: without sentiment (for reference)
    if has_sentiment:
        print("="*70)
        print("BACKTEST 2: WITHOUT Sentiment Data (for comparison)")
        print("="*70)
        print()

        # Same config, but only price data
        result_without_sentiment = await engine.run_backtest(
            committee,
            {"BTC-USDC": btc_data}  # No sentiment
        )

        print("\n" + "="*70)
        print("RESULTS WITHOUT SENTIMENT")
        print("="*70)
        print(f"Initial Capital:  ${result_without_sentiment.initial_capital:,.0f}")
        print(f"Final Capital:    ${result_without_sentiment.final_capital:,.0f}")
        print(f"Total Return:     ${result_without_sentiment.total_return:+,.0f} "
              f"({result_without_sentiment.total_return_pct:+.2%})")
        print()
        print(f"Total Trades:     {result_without_sentiment.total_trades}")
        print(f"Win Rate:         {result_without_sentiment.win_rate:.1%}")
        print(f"Sharpe Ratio:     {result_without_sentiment.sharpe_ratio:.2f}")
        print(f"Max Drawdown:     {result_without_sentiment.max_drawdown_pct:.1%}")
        print("="*70 + "\n")

        # Comparison
        print("="*70)
        print("SENTIMENT IMPACT")
        print("="*70)

        return_diff = result_with_sentiment.total_return_pct - result_without_sentiment.total_return_pct
        trades_diff = result_with_sentiment.total_trades - result_without_sentiment.total_trades
        winrate_diff = result_with_sentiment.win_rate - result_without_sentiment.win_rate
        sharpe_diff = result_with_sentiment.sharpe_ratio - result_without_sentiment.sharpe_ratio

        print(f"Return Difference:   {return_diff:+.2%}")
        print(f"Trade Count Change:  {trades_diff:+d}")
        print(f"Win Rate Change:     {winrate_diff:+.1%}")
        print(f"Sharpe Change:       {sharpe_diff:+.2f}")
        print()

        if return_diff > 0:
            print("✅ Sentiment data IMPROVED results!")
            print("   Agents made better decisions with news/sentiment context.")
        elif return_diff < 0:
            print("⚠️  Sentiment data hurt results in this window")
            print("   This can happen in specific market conditions.")
            print("   Test on multiple windows for statistical significance.")
        else:
            print("➖ Sentiment had neutral impact")
            print("   Agents made similar decisions with or without sentiment.")

        print("="*70 + "\n")

    # Summary
    print("="*70)
    print("✅ DEMO COMPLETE!")
    print("="*70)
    print()
    print("What you just saw:")
    print("  1. Real historical price data from Binance")
    print("  2. Real sentiment data from Fear & Greed Index")
    print("  3. Agents using sentiment in trading decisions")
    print("  4. Comparison: with vs without sentiment")
    print()
    print("Next steps:")
    print("  1. Get API keys for more data sources (see docs/DATA_SOURCES.md)")
    print("  2. Test on longer time periods (3+ months)")
    print("  3. Test on multiple random windows")
    print("  4. Add macro trends (FRED API)")
    print("  5. Deploy to production!")
    print()
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(demo_sentiment_integration())
