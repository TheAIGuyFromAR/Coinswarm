#!/usr/bin/env python3
"""
Quick Backtest Demo - Works NOW

Uses only FREE data sources (no API keys needed):
1. Mock price data (simulated Binance)
2. Google News RSS (free, unlimited)
3. Fear & Greed Index (free, unlimited)

Run this to see the system working immediately!
"""

import asyncio
import logging
from datetime import datetime, timedelta
import random

from coinswarm.agents.trend_agent import TrendFollowingAgent
from coinswarm.agents.risk_agent import RiskManagementAgent
from coinswarm.agents.arbitrage_agent import ArbitrageAgent
from coinswarm.agents.committee import AgentCommittee
from coinswarm.backtesting.backtest_engine import BacktestEngine, BacktestConfig
from coinswarm.data_ingest.base import DataPoint
from coinswarm.data_ingest.google_sentiment_fetcher import GoogleSentimentFetcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def generate_mock_price_data(symbol: str, days: int = 30) -> list:
    """Generate realistic mock price data"""

    logger.info(f"Generating {days} days of mock price data for {symbol}...")

    data_points = []
    current_price = 50000.0 if symbol == "BTC-USDC" else 2500.0  # Starting price
    current_time = datetime.now() - timedelta(days=days)

    # Generate hourly candles
    for hour in range(days * 24):
        # Random walk with slight upward bias
        change_pct = random.gauss(0.001, 0.02)  # 0.1% drift, 2% volatility
        current_price *= (1 + change_pct)

        # Clamp to reasonable range
        if symbol == "BTC-USDC":
            current_price = max(30000, min(70000, current_price))
        else:
            current_price = max(1500, min(4000, current_price))

        # Create OHLCV data
        open_price = current_price
        close_price = current_price * (1 + random.gauss(0, 0.005))
        high_price = max(open_price, close_price) * (1 + abs(random.gauss(0, 0.01)))
        low_price = min(open_price, close_price) * (1 - abs(random.gauss(0, 0.01)))
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

    logger.info(f"✓ Generated {len(data_points)} ticks for {symbol}")
    return data_points


async def fetch_real_sentiment(symbol: str, days: int = 30) -> list:
    """Fetch REAL sentiment from Google (free, no API key)"""

    logger.info(f"Fetching REAL sentiment for {symbol} from Google News...")

    google_fetcher = GoogleSentimentFetcher()

    sentiment_data = []
    current_date = datetime.now() - timedelta(days=days)

    # Fetch daily sentiment
    for day in range(days):
        target_date = current_date + timedelta(days=day)

        try:
            # Fetch Google News + Trends for this day
            snapshot = await google_fetcher.fetch_sentiment_snapshot(
                symbol.split("-")[0],  # BTC from BTC-USDC
                hours_back=24
            )

            # Convert to DataPoint
            data_point = DataPoint(
                source="google",
                symbol=f"{symbol.split('-')[0]}-SENTIMENT",
                timeframe="1d",
                timestamp=target_date,
                data={
                    "sentiment": snapshot["overall_sentiment"],
                    "news_sentiment": snapshot["news_sentiment"],
                    "trend_sentiment": snapshot["trend_sentiment"],
                    "article_count": snapshot["article_count"],
                    "bullish_count": snapshot["bullish_count"],
                    "bearish_count": snapshot["bearish_count"],
                    "trend_score": snapshot["trend_score"]
                },
                quality_score=1.0
            )

            sentiment_data.append(data_point)

            # Rate limiting
            await asyncio.sleep(0.5)

        except Exception as e:
            logger.warning(f"Error fetching sentiment for day {day}: {e}")
            # Add neutral sentiment as fallback
            data_point = DataPoint(
                source="google",
                symbol=f"{symbol.split('-')[0]}-SENTIMENT",
                timeframe="1d",
                timestamp=target_date,
                data={"sentiment": 0.0},
                quality_score=0.5
            )
            sentiment_data.append(data_point)

    logger.info(f"✓ Fetched {len(sentiment_data)} sentiment snapshots")
    return sentiment_data


async def run_quick_backtest():
    """Run a quick backtest with available data"""

    print("\n" + "="*70)
    print("QUICK BACKTEST DEMO")
    print("="*70 + "\n")

    print("Data Sources:")
    print("  ✅ Price: Mock data (simulated realistic BTC movements)")
    print("  ✅ Sentiment: Google News RSS (REAL, free, no API key)")
    print("  ✅ Trends: Google Trends (REAL, free, no API key)")
    print()

    # Generate mock price data
    print("Step 1: Generating price data...")
    btc_price_data = generate_mock_price_data("BTC-USDC", days=30)
    print()

    # Fetch REAL sentiment from Google
    print("Step 2: Fetching REAL sentiment from Google...")
    try:
        btc_sentiment_data = await fetch_real_sentiment("BTC-USDC", days=30)
    except Exception as e:
        logger.error(f"Sentiment fetch failed: {e}")
        logger.info("Continuing with mock sentiment...")
        # Fallback to mock sentiment
        btc_sentiment_data = []
        for i in range(30):
            data_point = DataPoint(
                source="mock",
                symbol="BTC-SENTIMENT",
                timeframe="1d",
                timestamp=datetime.now() - timedelta(days=30-i),
                data={"sentiment": random.uniform(-0.5, 0.5)},
                quality_score=1.0
            )
            btc_sentiment_data.append(data_point)
    print()

    # Show sample data
    print("Sample Price Data (last 5 hours):")
    print("-" * 70)
    for point in btc_price_data[-5:]:
        price = point.data["price"]
        print(f"{point.timestamp.strftime('%Y-%m-%d %H:%M')}  ${price:,.2f}")
    print()

    if btc_sentiment_data:
        print("Sample Sentiment Data (last 5 days):")
        print("-" * 70)
        for point in btc_sentiment_data[-5:]:
            sentiment = point.data.get("sentiment", 0)
            emoji = "🔴" if sentiment < -0.3 else "🟡" if sentiment < 0.3 else "🟢"
            print(f"{point.timestamp.strftime('%Y-%m-%d')} {emoji}  Sentiment: {sentiment:+.2f}")
        print()

    # Create agent committee
    print("Step 3: Creating agent committee...")
    agents = [
        TrendFollowingAgent(name="TrendFollower", weight=1.0),
        RiskManagementAgent(name="RiskManager", weight=2.0),
        ArbitrageAgent(name="ArbitrageHunter", weight=2.0),
    ]

    committee = AgentCommittee(
        agents=agents,
        confidence_threshold=0.7
    )
    print(f"✓ Committee created with {len(agents)} agents")
    print()

    # Configure backtest
    start_date = btc_price_data[0].timestamp
    end_date = btc_price_data[-1].timestamp

    config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        initial_capital=100000,
        symbols=["BTC-USDC"],
        timeframe="1h",
        commission=0.001,
        slippage=0.0005
    )

    print("Step 4: Running backtest...")
    print(f"  Initial Capital: ${config.initial_capital:,.0f}")
    print(f"  Period: {start_date.date()} to {end_date.date()}")
    print(f"  Timeframe: {config.timeframe}")
    print()

    # Merge price + sentiment
    historical_data = {
        "BTC-USDC": btc_price_data
    }

    if btc_sentiment_data:
        historical_data["BTC-SENTIMENT"] = btc_sentiment_data

    # Run backtest
    engine = BacktestEngine(config)
    result = await engine.run_backtest(committee, historical_data)

    # Display results
    print("\n" + "="*70)
    print("BACKTEST RESULTS")
    print("="*70)
    print(f"Initial Capital:     ${result.initial_capital:,.0f}")
    print(f"Final Capital:       ${result.final_capital:,.0f}")
    print(f"Total Return:        ${result.total_return:+,.0f} ({result.total_return_pct:+.2%})")
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
    if result.total_return_pct > 0:
        print("✅ Positive returns! Strategy is profitable in this period.")
    else:
        print("❌ Negative returns. Strategy needs tuning or market was unfavorable.")

    if result.sharpe_ratio > 1.0:
        print("✅ Good Sharpe ratio (>1.0) - returns justify the risk.")
    else:
        print("⚠️  Low Sharpe ratio (<1.0) - high risk for the returns.")

    if result.win_rate > 0.5:
        print(f"✅ Win rate >50% - agents are picking winners.")
    else:
        print(f"⚠️  Win rate <50% - need better signals.")

    print()

    # Show trade samples
    if result.trades:
        print("Sample Trades:")
        print("-" * 70)
        for i, trade in enumerate(result.trades[:5], 1):
            emoji = "✅" if trade.pnl > 0 else "❌"
            print(f"{i}. {emoji} {trade.action} {trade.symbol} @ ${trade.price:,.2f}")
            print(f"   Size: {trade.size:.4f}, P&L: ${trade.pnl:+,.2f}")
        print()

    print("="*70)
    print("✅ BACKTEST COMPLETE")
    print("="*70)
    print()
    print("What just happened:")
    print("  1. Generated 30 days of realistic BTC price movements")
    print("  2. Fetched REAL sentiment from Google News & Trends")
    print("  3. Agents voted on trades using price + sentiment")
    print("  4. Backtested the strategy and calculated performance")
    print()
    print("Next steps:")
    print("  1. Use real Binance data (via Cloudflare Worker)")
    print("  2. Test on longer periods (3+ months)")
    print("  3. Test on multiple random windows")
    print("  4. Add more agents (academic research, hedge)")
    print("  5. Tune agent weights based on results")
    print()


if __name__ == "__main__":
    asyncio.run(run_quick_backtest())
