#!/usr/bin/env python3
"""
Random Backtest with Superchill Risk Agent

Uses the fetched historical data and runs backtests with a very relaxed risk agent.

Superchill parameters:
- Max position: 25% (was 10%)
- Max drawdown: 50% (was 20%)
- Max volatility: 20% (was 5%)
- Wide spread tolerance: 1% (was 0.1%)

Usage:
    python backtest_superchill.py
"""

import asyncio
import json
import logging
from datetime import datetime

from coinswarm.agents.arbitrage_agent import ArbitrageAgent
from coinswarm.agents.base_agent import AgentVote, BaseAgent
from coinswarm.agents.committee import AgentCommittee
from coinswarm.agents.trend_agent import TrendFollowingAgent
from coinswarm.backtesting.backtest_engine import BacktestConfig, BacktestEngine
from coinswarm.data_ingest.base import DataPoint

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class SuperchillRiskAgent(BaseAgent):
    """
    Super chill risk agent - lets almost everything through

    Very permissive thresholds:
    - Max volatility: 20% (vs 5% default)
    - Max drawdown: 50% (vs 20% default)
    - Max position: 25% (vs 10% default)
    - Wide spreads OK: 1% (vs 0.1% default)
    """

    def __init__(
        self,
        name: str = "SuperchillRisk",
        weight: float = 1.0,  # Lower weight - less influence
        max_position_pct: float = 0.25,  # 25% per trade
        max_drawdown_pct: float = 0.50,  # 50% drawdown OK
        max_volatility: float = 0.20,    # 20% volatility OK
        max_spread_pct: float = 0.01     # 1% spread OK
    ):
        super().__init__(name, weight)
        self.max_position_pct = max_position_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.max_volatility = max_volatility
        self.max_spread_pct = max_spread_pct
        self.price_history = []
        self.max_history = 100

    async def analyze(
        self,
        tick: DataPoint,
        position: dict | None,
        market_context: dict
    ) -> AgentVote:
        """Analyze risk with superchill thresholds"""

        price = tick.data.get("price", 0) or tick.data.get("close", 0)
        spread = tick.data.get("spread", 0)

        # Update price history
        self.price_history.append(price)
        if len(self.price_history) > self.max_history:
            self.price_history.pop(0)

        veto_reasons = []

        # 1. Check volatility (very relaxed)
        if len(self.price_history) >= 20:
            volatility = self._calculate_volatility()
            if volatility > self.max_volatility:
                veto_reasons.append(
                    f"Volatility extreme: {volatility:.2%} > {self.max_volatility:.2%}"
                )

        # 2. Check spread (very relaxed)
        if spread and price > 0:
            spread_pct = spread / price
            if spread_pct > self.max_spread_pct:
                veto_reasons.append(f"Spread too wide: {spread_pct:.3%}")

        # 3. Check position size (very relaxed)
        proposed_size = market_context.get("proposed_size", 0)
        account_value = market_context.get("account_value", 100000)
        if proposed_size * price > account_value * self.max_position_pct:
            veto_reasons.append(
                f"Position huge: ${proposed_size * price:.2f} > "
                f"{self.max_position_pct:.0%} of account"
            )

        # 4. Check drawdown (very relaxed)
        current_drawdown = market_context.get("current_drawdown", 0)
        if current_drawdown > self.max_drawdown_pct:
            veto_reasons.append(
                f"Drawdown extreme: {current_drawdown:.1%} > {self.max_drawdown_pct:.0%}"
            )

        # Veto only if we have reasons
        has_veto = len(veto_reasons) > 0

        return AgentVote(
            agent_name=self.name,
            action="HOLD",
            confidence=0.1,  # Very low confidence - don't influence much
            size=0.0,  # Not suggesting any position size
            reason="; ".join(veto_reasons) if veto_reasons else "Superchill - all good",
            veto=has_veto
        )

    def _calculate_volatility(self) -> float:
        """Calculate price volatility from history"""
        if len(self.price_history) < 2:
            return 0.0

        returns = []
        for i in range(1, len(self.price_history)):
            if self.price_history[i-1] > 0:
                ret = (self.price_history[i] - self.price_history[i-1]) / self.price_history[i-1]
                returns.append(ret)

        if not returns:
            return 0.0

        # Standard deviation of returns
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        return variance ** 0.5


def load_historical_data(filepath: str) -> list[DataPoint]:
    """Load historical data from JSON file"""

    logger.info(f"Loading data from {filepath}...")

    with open(filepath) as f:
        data = json.load(f)

    if not data.get('success'):
        raise ValueError(f"Data file indicates failure: {data.get('error')}")

    symbol = data['symbol']
    candles = data['data']

    logger.info(f"Loaded {len(candles)} candles for {symbol}")

    # Convert to DataPoint objects
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
                "price": candle['close'],  # Use close as current price
                "volume": candle['volume']
            }
        )
        data_points.append(dp)

    return data_points


async def run_backtest():
    """Run backtest with superchill risk agent"""

    logger.info("=" * 80)
    logger.info("RANDOM BACKTEST WITH SUPERCHILL RISK AGENT")
    logger.info("=" * 80)

    # Load BTC historical data
    data_points = load_historical_data("data/historical/BTC_180d_hour.json")

    logger.info(f"\n📊 Data: {len(data_points)} hourly candles")
    logger.info(f"   Period: {data_points[0].timestamp} to {data_points[-1].timestamp}")
    logger.info(f"   Symbol: {data_points[0].symbol}")

    # Create agents with superchill risk
    agents = [
        TrendFollowingAgent(name="Trend", weight=1.0),
        ArbitrageAgent(name="Arb", weight=1.0),
        SuperchillRiskAgent(name="SuperchillRisk", weight=1.0)
    ]

    logger.info("\n🤖 Agents:")
    for agent in agents:
        logger.info(f"   - {agent.name} (weight: {agent.weight})")

    # Create committee
    committee = AgentCommittee(
        agents=agents,
        confidence_threshold=0.5  # Only need 50% confidence to trade
    )

    # Configure backtest
    config = BacktestConfig(
        start_date=data_points[0].timestamp,
        end_date=data_points[-1].timestamp,
        initial_capital=100000.0,  # $100k starting capital
        symbols=["BTC-USD"],
        timeframe="1h",
        commission=0.001,          # 0.1% commission
        slippage=0.0005,           # 0.05% slippage
        max_positions=1
    )

    logger.info("\n💰 Backtest Config:")
    logger.info(f"   Initial Capital: ${config.initial_capital:,.2f}")
    logger.info(f"   Commission: {config.commission:.2%}")
    logger.info(f"   Slippage: {config.slippage:.2%}")

    # Create backtest engine
    engine = BacktestEngine(config=config)

    # Run backtest
    logger.info("\n🚀 Running backtest...")
    logger.info("-" * 80)

    # Historical data must be a dict mapping symbol → data points
    historical_data = {"BTC-USD": data_points}

    results = await engine.run_backtest(committee, historical_data)

    # Display results
    logger.info("\n" + "=" * 80)
    logger.info("BACKTEST RESULTS")
    logger.info("=" * 80)

    logger.info("\n💵 Performance:")
    logger.info(f"   Initial Capital:  ${results.initial_capital:,.2f}")
    logger.info(f"   Final Capital:    ${results.final_capital:,.2f}")
    logger.info(f"   Total Return:     {results.total_return_pct:.2f}%")
    logger.info(f"   Total PnL:        ${results.total_pnl:,.2f}")

    logger.info("\n📈 Trade Statistics:")
    logger.info(f"   Total Trades:     {results.total_trades}")
    logger.info(f"   Winning Trades:   {results.winning_trades}")
    logger.info(f"   Losing Trades:    {results.losing_trades}")
    logger.info(f"   Win Rate:         {results.win_rate:.1%}")

    if results.total_trades > 0:
        logger.info(f"   Avg Win:          ${results.avg_win:,.2f}")
        logger.info(f"   Avg Loss:         ${results.avg_loss:,.2f}")
        logger.info(f"   Profit Factor:    {results.profit_factor:.2f}")

    logger.info("\n📊 Risk Metrics:")
    logger.info(f"   Max Drawdown:     {results.max_drawdown_pct:.2f}%")
    logger.info(f"   Sharpe Ratio:     {results.sharpe_ratio:.3f}")
    logger.info(f"   Sortino Ratio:    {results.sortino_ratio:.3f}")
    logger.info(f"   Calmar Ratio:     {results.calmar_ratio:.3f}")

    logger.info("\n" + "=" * 80)

    if results.total_trades > 0:
        logger.info("\n📝 Sample Trades (first 5):")
        for i, trade in enumerate(results.trades[:5]):
            logger.info(f"   {i+1}. {trade.action} {trade.symbol} @ ${trade.entry_price:,.2f} "
                       f"→ ${trade.exit_price or 0:,.2f} - PnL: ${trade.pnl:,.2f} ({trade.pnl_pct:+.2f}%)")

    return results


if __name__ == "__main__":
    asyncio.run(run_backtest())
