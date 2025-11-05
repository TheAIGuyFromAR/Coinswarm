#!/usr/bin/env python3
"""
Complete Backtest Demo - All Agents

Shows the full system with all 7 agents working together:
1. TrendFollowingAgent
2. RiskManagementAgent
3. ArbitrageAgent
4. TradeAnalysisAgent
5. StrategyLearningAgent
6. AcademicResearchAgent
7. HedgeAgent

Uses realistic mock data until Cloudflare Worker is deployed.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from datetime import datetime, timedelta
import random

from coinswarm.agents.trend_agent import TrendFollowingAgent
from coinswarm.agents.risk_agent import RiskManagementAgent
from coinswarm.agents.arbitrage_agent import ArbitrageAgent
from coinswarm.agents.trade_analysis_agent import TradeAnalysisAgent
from coinswarm.agents.strategy_learning_agent import StrategyLearningAgent
from coinswarm.agents.academic_research_agent import AcademicResearchAgent
from coinswarm.agents.hedge_agent import HedgeAgent
from coinswarm.agents.committee import AgentCommittee
from coinswarm.backtesting.backtest_engine import BacktestEngine, BacktestConfig
from coinswarm.data_ingest.base import DataPoint

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def generate_realistic_market_data(symbol: str, days: int = 30) -> list:
    """
    Generate realistic market data with volatility, trends, and noise.

    Simulates different market regimes:
    - Bull market (price rising)
    - Bear market (price falling)
    - Sideways (choppy)
    - High volatility events
    """

    logger.info(f"Generating {days} days of realistic market data for {symbol}...")

    data_points = []

    # Starting price
    if "BTC" in symbol:
        current_price = 50000.0
        volatility = 0.025  # 2.5% daily volatility
    elif "ETH" in symbol:
        current_price = 2500.0
        volatility = 0.03  # 3% daily volatility
    elif "SOL" in symbol:
        current_price = 100.0
        volatility = 0.04  # 4% daily volatility
    else:
        current_price = 1.0
        volatility = 0.001

    current_time = datetime.now() - timedelta(days=days)

    # Market regime (changes every week)
    regime = "bull"  # bull, bear, sideways, volatile
    regime_days = 0

    # Generate hourly candles
    for hour in range(days * 24):
        # Change market regime every 7 days
        if regime_days >= 168:  # 7 days * 24 hours
            regime = random.choice(["bull", "bear", "sideways", "volatile"])
            regime_days = 0
            logger.debug(f"Market regime changed to: {regime}")

        regime_days += 1

        # Price movement based on regime
        if regime == "bull":
            drift = 0.0003  # 0.03% upward drift per hour
            vol = volatility / 24
        elif regime == "bear":
            drift = -0.0003  # 0.03% downward drift per hour
            vol = volatility / 24
        elif regime == "sideways":
            drift = 0.0
            vol = volatility / 48  # Lower volatility
        else:  # volatile
            drift = 0.0
            vol = volatility / 12  # Higher volatility

        # Random walk with drift
        change_pct = random.gauss(drift, vol)
        current_price *= (1 + change_pct)

        # Occasional volatility spikes (1% chance per hour)
        if random.random() < 0.01:
            spike = random.gauss(0, volatility * 2)
            current_price *= (1 + spike)
            logger.debug(f"Volatility spike: {spike:+.2%}")

        # Clamp to reasonable ranges
        if "BTC" in symbol:
            current_price = max(30000, min(70000, current_price))
        elif "ETH" in symbol:
            current_price = max(1500, min(4000, current_price))
        elif "SOL" in symbol:
            current_price = max(50, min(200, current_price))

        # Generate OHLCV
        open_price = current_price
        close_price = current_price * (1 + random.gauss(0, vol / 2))
        high_price = max(open_price, close_price) * (1 + abs(random.gauss(0, vol / 2)))
        low_price = min(open_price, close_price) * (1 - abs(random.gauss(0, vol / 2)))
        volume = random.uniform(1000, 5000) * (2 if regime == "volatile" else 1)

        # Create data point
        timestamp = current_time + timedelta(hours=hour)

        data_point = DataPoint(
            source="mock",
            symbol=symbol,
            timeframe="1h",
            timestamp=timestamp,
            data={
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "price": close_price,
                "volume": volume,
                "regime": regime  # Hidden info for analysis
            },
            quality_score=1.0
        )

        data_points.append(data_point)

    logger.info(f"✓ Generated {len(data_points)} ticks for {symbol}")
    return data_points


def generate_sentiment_data(symbol: str, days: int = 30) -> list:
    """Generate realistic sentiment data aligned with price movements"""

    logger.info(f"Generating sentiment data for {symbol}...")

    sentiment_data = []
    current_date = datetime.now() - timedelta(days=days)

    # Sentiment follows a trend with noise
    sentiment_trend = 0.0  # Starts neutral

    for day in range(days):
        # Sentiment random walk
        sentiment_trend += random.gauss(0, 0.1)
        sentiment_trend = max(-1.0, min(1.0, sentiment_trend))  # Clamp

        # Add daily noise
        daily_sentiment = sentiment_trend + random.gauss(0, 0.2)
        daily_sentiment = max(-1.0, min(1.0, daily_sentiment))

        # Convert to Fear & Greed style (0-100)
        fear_greed = (daily_sentiment + 1) * 50  # -1 to +1 → 0 to 100

        # Article counts (more articles in extreme sentiment)
        article_count = int(random.uniform(5, 20) * (1 + abs(daily_sentiment)))
        bullish_count = int(article_count * (daily_sentiment + 1) / 2)
        bearish_count = article_count - bullish_count

        data_point = DataPoint(
            source="mock",
            symbol=f"{symbol.split('-')[0]}-SENTIMENT",
            timeframe="1d",
            timestamp=current_date + timedelta(days=day),
            data={
                "sentiment": daily_sentiment,
                "news_sentiment": daily_sentiment * 0.8,
                "social_sentiment": daily_sentiment * 0.6,
                "fear_greed": fear_greed,
                "article_count": article_count,
                "bullish_count": bullish_count,
                "bearish_count": bearish_count,
            },
            quality_score=1.0
        )

        sentiment_data.append(data_point)

    logger.info(f"✓ Generated {len(sentiment_data)} sentiment snapshots")
    return sentiment_data


async def run_full_backtest():
    """Run complete backtest with all agents"""

    print("\n" + "="*70)
    print("COMPLETE BACKTEST - ALL 7 AGENTS")
    print("="*70 + "\n")

    print("Agents:")
    print("  1. TrendFollowingAgent     - Identifies trends")
    print("  2. RiskManagementAgent     - Manages position size & risk")
    print("  3. ArbitrageAgent          - Finds arbitrage opportunities")
    print("  4. TradeAnalysisAgent      - Analyzes trade outcomes")
    print("  5. StrategyLearningAgent   - Evolves strategies (genetic)")
    print("  6. AcademicResearchAgent   - Discovers proven strategies")
    print("  7. HedgeAgent              - Stop losses & risk/reward")
    print()

    # Generate market data
    print("="*70)
    print("STEP 1: Generating Market Data")
    print("="*70)
    print()

    print("Generating 30 days of realistic price data...")
    btc_data = generate_realistic_market_data("BTC-USDC", days=30)
    eth_data = generate_realistic_market_data("ETH-USDC", days=30)
    sol_data = generate_realistic_market_data("SOL-USDC", days=30)

    print("Generating sentiment data...")
    btc_sentiment = generate_sentiment_data("BTC-USDC", days=30)
    eth_sentiment = generate_sentiment_data("ETH-USDC", days=30)
    sol_sentiment = generate_sentiment_data("SOL-USDC", days=30)

    print()
    print("Data generated:")
    print(f"  BTC-USDC:  {len(btc_data)} price ticks, {len(btc_sentiment)} sentiment snapshots")
    print(f"  ETH-USDC:  {len(eth_data)} price ticks, {len(eth_sentiment)} sentiment snapshots")
    print(f"  SOL-USDC:  {len(sol_data)} price ticks, {len(sol_sentiment)} sentiment snapshots")
    print()

    # Show sample data
    print("Sample Data (last 3 hours of BTC):")
    print("-"*70)
    for point in btc_data[-3:]:
        price = point.data["price"]
        regime = point.data["regime"]
        print(f"{point.timestamp.strftime('%Y-%m-%d %H:%M')}  ${price:,.2f}  [{regime}]")
    print()

    print("Sample Sentiment (last 3 days of BTC):")
    print("-"*70)
    for point in btc_sentiment[-3:]:
        sentiment = point.data["sentiment"]
        fear_greed = point.data["fear_greed"]
        emoji = "🔴" if sentiment < -0.3 else "🟡" if sentiment < 0.3 else "🟢"
        print(f"{point.timestamp.strftime('%Y-%m-%d')} {emoji}  Sentiment: {sentiment:+.2f}  F&G: {fear_greed:.0f}")
    print()

    # Create agent committee
    print("="*70)
    print("STEP 2: Creating Agent Committee")
    print("="*70)
    print()

    agents = [
        TrendFollowingAgent(name="TrendFollower", weight=1.0),
        RiskManagementAgent(name="RiskManager", weight=2.0),
        ArbitrageAgent(name="ArbitrageHunter", weight=2.0),
        TradeAnalysisAgent(name="TradeAnalyzer", weight=1.5),
        StrategyLearningAgent(name="StrategyLearner", weight=1.5),
        AcademicResearchAgent(name="AcademicResearcher", weight=1.0),
        HedgeAgent(name="HedgeManager", weight=2.0)
    ]

    for agent in agents:
        print(f"  ✓ {agent.name:25} (weight: {agent.weight:.1f})")

    committee = AgentCommittee(
        agents=agents,
        confidence_threshold=0.6  # Lower threshold = more trades
    )

    print()
    print(f"Committee voting threshold: {committee.confidence_threshold:.1%}")
    print()

    # Configure backtest
    print("="*70)
    print("STEP 3: Configuring Backtest")
    print("="*70)
    print()

    start_date = btc_data[0].timestamp
    end_date = btc_data[-1].timestamp

    config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        initial_capital=100000,  # $100k starting capital
        symbols=["BTC-USDC", "ETH-USDC", "SOL-USDC"],
        timeframe="1h",
        commission=0.001,  # 0.1% per trade
        slippage=0.0005     # 0.05% slippage
    )

    print(f"Initial Capital:  ${config.initial_capital:,.0f}")
    print(f"Period:           {start_date.date()} to {end_date.date()} ({(end_date-start_date).days} days)")
    print(f"Symbols:          {', '.join(config.symbols)}")
    print(f"Timeframe:        {config.timeframe}")
    print(f"Commission:       {config.commission:.2%}")
    print(f"Slippage:         {config.slippage:.2%}")
    print()

    # Prepare data
    historical_data = {
        "BTC-USDC": btc_data,
        "ETH-USDC": eth_data,
        "SOL-USDC": sol_data,
        "BTC-SENTIMENT": btc_sentiment,
        "ETH-SENTIMENT": eth_sentiment,
        "SOL-SENTIMENT": sol_sentiment,
    }

    # Run backtest
    print("="*70)
    print("STEP 4: Running Backtest")
    print("="*70)
    print()
    print("This will take a few seconds...")
    print("Agents are voting on every tick and executing trades...")
    print()

    engine = BacktestEngine(config)
    result = await engine.run_backtest(committee, historical_data)

    # Display results
    print("\n" + "="*70)
    print("BACKTEST RESULTS")
    print("="*70)
    print()

    print("PERFORMANCE:")
    print("-"*70)
    print(f"Initial Capital:     ${result.initial_capital:,.0f}")
    print(f"Final Capital:       ${result.final_capital:,.0f}")
    print(f"Total Return:        ${result.total_return:+,.0f}")
    print(f"Return %:            {result.total_return_pct:+.2%}")
    print()

    print("TRADE STATISTICS:")
    print("-"*70)
    print(f"Total Trades:        {result.total_trades}")
    print(f"Winning Trades:      {result.winning_trades} ({result.win_rate:.1%})")
    print(f"Losing Trades:       {result.losing_trades}")
    print(f"Avg Win:             ${result.avg_win:,.2f}" if result.avg_win else "Avg Win:             N/A")
    print(f"Avg Loss:            ${result.avg_loss:,.2f}" if result.avg_loss else "Avg Loss:            N/A")
    print()

    print("RISK METRICS:")
    print("-"*70)
    print(f"Sharpe Ratio:        {result.sharpe_ratio:.2f}")
    print(f"Sortino Ratio:       {result.sortino_ratio:.2f}")
    print(f"Calmar Ratio:        {result.calmar_ratio:.2f}")
    print(f"Max Drawdown:        {result.max_drawdown_pct:.2%}")
    print(f"Profit Factor:       {result.profit_factor:.2f}")
    print()

    # Interpretation
    print("INTERPRETATION:")
    print("-"*70)

    if result.total_return_pct > 0:
        print(f"✅ Positive returns: {result.total_return_pct:+.2%}")
    else:
        print(f"❌ Negative returns: {result.total_return_pct:+.2%}")

    if result.sharpe_ratio > 1.5:
        print("✅ Excellent Sharpe ratio (>1.5) - great risk-adjusted returns")
    elif result.sharpe_ratio > 1.0:
        print("✅ Good Sharpe ratio (>1.0) - decent risk-adjusted returns")
    else:
        print("⚠️  Low Sharpe ratio (<1.0) - returns don't justify risk")

    if result.win_rate > 0.55:
        print(f"✅ Strong win rate: {result.win_rate:.1%}")
    elif result.win_rate > 0.45:
        print(f"➖ Average win rate: {result.win_rate:.1%}")
    else:
        print(f"⚠️  Low win rate: {result.win_rate:.1%}")

    if result.profit_factor > 2.0:
        print(f"✅ Excellent profit factor: {result.profit_factor:.2f}")
    elif result.profit_factor > 1.5:
        print(f"✅ Good profit factor: {result.profit_factor:.2f}")
    elif result.profit_factor > 1.0:
        print(f"➖ Break-even profit factor: {result.profit_factor:.2f}")
    else:
        print(f"❌ Losing profit factor: {result.profit_factor:.2f}")

    print()

    # Show sample trades
    if result.trades and len(result.trades) > 0:
        print("SAMPLE TRADES:")
        print("-"*70)
        for i, trade in enumerate(result.trades[:10], 1):
            emoji = "✅" if trade.pnl and trade.pnl > 0 else "❌"
            pnl_str = f"${trade.pnl:+,.2f}" if trade.pnl else "N/A"
            print(f"{i}. {emoji} {trade.action:4} {trade.symbol:10} @ ${trade.entry_price:,.2f}  "
                  f"Size: {trade.size:.4f}  P&L: {pnl_str}")

        if len(result.trades) > 10:
            print(f"... and {len(result.trades) - 10} more trades")
        print()

    print("="*70)
    print("✅ BACKTEST COMPLETE")
    print("="*70)
    print()

    print("What just happened:")
    print("  1. Generated 30 days of realistic market data (BTC, ETH, SOL)")
    print("  2. Generated sentiment data (news + social + fear/greed)")
    print("  3. All 7 agents voted on every tick (720 ticks × 3 symbols)")
    print("  4. Committee executed trades based on consensus")
    print("  5. Calculated comprehensive performance metrics")
    print()

    print("Next steps:")
    print("  1. Deploy Cloudflare Worker for REAL market data")
    print("  2. Test on longer periods (3+ months)")
    print("  3. Test on multiple random windows (10+)")
    print("  4. Analyze which agents contribute most to returns")
    print("  5. Tune agent weights based on performance")
    print("  6. Add continuous backtesting (24/7 testing)")
    print("  7. Deploy to production!")
    print()

    return result


if __name__ == "__main__":
    asyncio.run(run_full_backtest())
