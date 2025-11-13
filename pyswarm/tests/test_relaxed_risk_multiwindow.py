#!/usr/bin/env python3
"""
Test with Relaxed Risk Agent on Multiple Real Data Windows

Give the risk agent a "chill pill" and test on many 1-month windows across 6 months.

Usage:
    python test_relaxed_risk_multiwindow.py
"""

import asyncio
import json
import logging

from coinswarm.agents.arbitrage_agent import ArbitrageAgent
from coinswarm.agents.base_agent import AgentVote, BaseAgent
from coinswarm.agents.committee import AgentCommittee
from coinswarm.agents.trend_agent import TrendFollowingAgent
from coinswarm.backtesting.backtest_engine import BacktestConfig, BacktestEngine
from coinswarm.data_ingest.base import DataPoint
from coinswarm.data_ingest.coinswarm_worker_client import CoinswarmWorkerClient

logger = logging.getLogger(__name__)


class RelaxedRiskAgent(BaseAgent):
    """
    Risk agent with relaxed thresholds - the "chill pill" version

    More permissive than default:
    - Max volatility: 10% (was 5%)
    - Flash crash: 20% (was 10%)
    - Still protects against extreme risk
    """

    def __init__(
        self,
        name: str = "RelaxedRisk",
        weight: float = 2.0,
        max_position_pct: float = 0.15,  # 15% per trade (was 10%)
        max_drawdown_pct: float = 0.30,  # 30% drawdown (was 20%)
        max_volatility: float = 0.10,    # 10% volatility (was 5%)
        flash_crash_threshold: float = 0.20  # 20% move (was 10%)
    ):
        super().__init__(name, weight)
        self.max_position_pct = max_position_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.max_volatility = max_volatility
        self.flash_crash_threshold = flash_crash_threshold
        self.price_history = []
        self.max_history = 100

    async def analyze(
        self,
        tick: DataPoint,
        position: dict | None,
        market_context: dict
    ) -> AgentVote:
        """Analyze risk with relaxed thresholds"""

        price = tick.data.get("price", 0)
        spread = tick.data.get("spread", 0)

        # Update price history
        self.price_history.append(price)
        if len(self.price_history) > self.max_history:
            self.price_history.pop(0)

        veto_reasons = []

        # 1. Check volatility (relaxed threshold)
        if len(self.price_history) >= 20:
            volatility = self._calculate_volatility()
            if volatility > self.max_volatility:
                veto_reasons.append(
                    f"Volatility too high: {volatility:.2%} > {self.max_volatility:.2%}"
                )

        # 2. Check spread
        if spread and price > 0:
            spread_pct = spread / price
            if spread_pct > 0.002:  # 0.2% spread (was 0.1%)
                veto_reasons.append(f"Spread too wide: {spread_pct:.3%}")

        # 3. Check position size
        proposed_size = market_context.get("proposed_size", 0)
        account_value = market_context.get("account_value", 100000)
        if proposed_size * price > account_value * self.max_position_pct:
            veto_reasons.append(
                f"Position too large: ${proposed_size * price:.2f} > "
                f"{self.max_position_pct:.0%} of account"
            )

        # 4. Check drawdown
        current_drawdown = market_context.get("drawdown_pct", 0)
        if current_drawdown > self.max_drawdown_pct:
            veto_reasons.append(
                f"Drawdown too large: {current_drawdown:.1%} > {self.max_drawdown_pct:.1%}"
            )

        # 5. Check for flash crash (RELAXED threshold)
        if len(self.price_history) >= 10:
            recent_change = (price - self.price_history[-10]) / self.price_history[-10]
            if abs(recent_change) > self.flash_crash_threshold:
                veto_reasons.append(
                    f"Flash crash detected: {recent_change:.1%} in 10 ticks"
                )

        # Issue veto if any risk condition triggered
        if veto_reasons:
            return AgentVote(
                agent_name=self.name,
                action="HOLD",
                confidence=1.0,
                size=0.0,
                reason="; ".join(veto_reasons),
                veto=True
            )

        # No risk issues
        return AgentVote(
            agent_name=self.name,
            action="HOLD",
            confidence=0.5,
            size=0.0,
            reason="No risk issues detected"
        )

    def _calculate_volatility(self) -> float:
        """Calculate price volatility"""
        if len(self.price_history) < 2:
            return 0.0

        returns = [
            (self.price_history[i] - self.price_history[i-1]) / self.price_history[i-1]
            for i in range(1, len(self.price_history))
        ]

        if not returns:
            return 0.0

        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        return variance ** 0.5


async def fetch_real_data_chunked(symbol: str, days: int) -> list[DataPoint]:
    """Fetch real data in 30-day chunks"""
    client = CoinswarmWorkerClient()

    print(f"📡 Fetching {days} days of real {symbol} data...")

    if days <= 30:
        try:
            data = await client.fetch_price_data(symbol=symbol, days=days, aggregate=True)
            print(f"✅ Got {len(data)} candles ({len(data)/24:.1f} days)")
            return data
        except Exception as e:
            print(f"❌ Error: {e}")
            return None

    # Fetch in chunks
    all_data = []
    chunks = (days + 29) // 30

    for i in range(chunks):
        chunk_days = min(30, days - i * 30)
        print(f"   Chunk {i+1}/{chunks}: {chunk_days} days...", end=" ")

        try:
            chunk_data = await client.fetch_price_data(symbol=symbol, days=chunk_days, aggregate=True)
            all_data.extend(chunk_data)
            print(f"✅ {len(chunk_data)} candles")
        except Exception as e:
            print(f"❌ {e}")
            if not all_data:
                return None
            break

    # Remove duplicates and sort
    unique_data = {point.timestamp: point for point in all_data}
    sorted_data = sorted(unique_data.values(), key=lambda p: p.timestamp)
    print(f"✅ Total: {len(sorted_data)} candles ({len(sorted_data)/24:.1f} days)")
    return sorted_data


def create_overlapping_windows(data: list[DataPoint], window_days: int = 30, step_days: int = 7) -> list[tuple]:
    """
    Create overlapping 1-month windows with 7-day steps

    This gives us many test windows from the data
    """
    window_hours = window_days * 24
    step_hours = step_days * 24

    windows = []
    start_idx = 0

    while start_idx + window_hours <= len(data):
        end_idx = start_idx + window_hours - 1
        windows.append((start_idx, end_idx))
        start_idx += step_hours

    return windows


async def test_window(
    data: list[DataPoint],
    start_idx: int,
    end_idx: int,
    config: dict,
    symbol: str,
    use_relaxed_risk: bool = True
) -> dict:
    """Test strategy on a single window"""

    window_data = data[start_idx:end_idx+1]

    if len(window_data) < 24:
        return None

    initial_price = window_data[0].data["close"]
    final_price = window_data[-1].data["close"]
    hodl_return = (final_price - initial_price) / initial_price

    # Create agents with relaxed or normal risk
    if use_relaxed_risk:
        agents = [
            TrendFollowingAgent(name="Trend", weight=config['trend_weight']),
            RelaxedRiskAgent(name="RelaxedRisk", weight=config['risk_weight']),
            ArbitrageAgent(name="Arb", weight=config['arbitrage_weight']),
        ]
    else:
        from coinswarm.agents.risk_agent import RiskManagementAgent
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
    if hodl_return < 0:
        if result.total_return_pct >= hodl_return:
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
        "profit_factor": result.profit_factor
    }


async def main():
    print("\n" + "="*90)
    print("🧘 TESTING WITH RELAXED RISK AGENT ON MULTIPLE REAL DATA WINDOWS")
    print("="*90 + "\n")

    # Load best strategy
    with open("discovered_strategies_BTCUSDC_20251106_002943.json") as f:
        data = json.load(f)

    strategy = data['strategies'][2]  # Rank 3

    print("Strategy Configuration:")
    print(f"  Trend Weight: {strategy['config']['trend_weight']:.3f}")
    print(f"  Risk Weight: {strategy['config']['risk_weight']:.3f} (RELAXED thresholds)")
    print(f"  Arbitrage Weight: {strategy['config']['arbitrage_weight']:.3f}")
    print(f"  Confidence Threshold: {strategy['config']['confidence_threshold']:.3f}\n")

    print("Risk Agent Relaxation:")
    print("  Max Volatility: 10% (was 5%) ✅")
    print("  Flash Crash: 20% (was 10%) ✅")
    print("  Max Drawdown: 30% (was 20%) ✅")
    print("  Max Position: 15% (was 10%) ✅\n")

    # Fetch 6 months of data
    print("="*90)
    print("PHASE 1: Fetching 6 months of real BTC data")
    print("="*90 + "\n")

    real_data = await fetch_real_data_chunked(symbol="BTC", days=180)

    if real_data is None:
        print("\n⚠️  Could not fetch real data")
        return

    # Create overlapping 1-month windows (every 7 days)
    print("\n" + "="*90)
    print("PHASE 2: Creating overlapping 1-month test windows")
    print("="*90 + "\n")

    windows = create_overlapping_windows(real_data, window_days=30, step_days=7)
    print(f"Created {len(windows)} overlapping 1-month windows (7-day step)\n")

    # Test each window
    print("="*90)
    print("PHASE 3: Testing strategy on all windows")
    print("="*90 + "\n")

    results = []
    for i, (start_idx, end_idx) in enumerate(windows):
        print(f"Window {i+1}/{len(windows)}: {real_data[start_idx].timestamp.date()} to {real_data[end_idx].timestamp.date()}")

        result = await test_window(
            data=real_data,
            start_idx=start_idx,
            end_idx=end_idx,
            config=strategy['config'],
            symbol="BTC-USD",
            use_relaxed_risk=True
        )

        if result:
            results.append(result)
            print(f"  Market: ${result['initial_price']:.0f} → ${result['final_price']:.0f} ({result['hodl_return']:+.2%})")
            print(f"  Strategy: {result['strategy_return']:+.2%} ({result['total_trades']} trades)")
            print(f"  vs HODL: {result['vs_hodl']:.2f}x, Win: {result['win_rate']:.0%}")
            print()

    # Analysis
    if not results:
        print("No results!")
        return

    print(f"\n{'='*90}")
    print(f"RESULTS SUMMARY - {len(results)} WINDOWS TESTED")
    print(f"{'='*90}\n")

    # Separate by outcome
    traded = [r for r in results if r['total_trades'] > 0]
    no_trades = [r for r in results if r['total_trades'] == 0]
    beat_hodl = [r for r in results if r['vs_hodl'] > 1.0]
    profitable = [r for r in results if r['strategy_return'] > 0]

    print("Trading Activity:")
    print(f"  Windows with Trades: {len(traded)}/{len(results)} ({len(traded)/len(results):.0%})")
    print(f"  Windows with No Trades: {len(no_trades)}/{len(results)} ({len(no_trades)/len(results):.0%})")
    print()

    print("Performance:")
    print(f"  Beat HODL: {len(beat_hodl)}/{len(results)} ({len(beat_hodl)/len(results):.0%})")
    print(f"  Profitable (>0%): {len(profitable)}/{len(results)} ({len(profitable)/len(results):.0%})")
    print()

    if traded:
        avg_trades = sum(r['total_trades'] for r in traded) / len(traded)
        avg_return = sum(r['strategy_return'] for r in traded) / len(traded)
        avg_win_rate = sum(r['win_rate'] for r in traded) / len(traded)

        print("When Strategy Traded:")
        print(f"  Avg Trades per Window: {avg_trades:.1f}")
        print(f"  Avg Return: {avg_return:+.2%}")
        print(f"  Avg Win Rate: {avg_win_rate:.1%}")
        print()

    # Overall cumulative
    total_strategy = sum(r['strategy_return'] for r in results)
    total_hodl = sum(r['hodl_return'] for r in results)

    print("Cumulative Across All Windows:")
    print(f"  Strategy: {total_strategy:+.2%}")
    print(f"  HODL: {total_hodl:+.2%}")
    print()

    # Best and worst
    if traded:
        best = max(traded, key=lambda r: r['strategy_return'])
        worst = min(traded, key=lambda r: r['strategy_return'])

        print("Best Window:")
        print(f"  {best['start_date'].date()} to {best['end_date'].date()}")
        print(f"  Return: {best['strategy_return']:+.2%} vs HODL: {best['hodl_return']:+.2%}")
        print(f"  Trades: {best['total_trades']}, Win Rate: {best['win_rate']:.0%}")
        print()

        print("Worst Window:")
        print(f"  {worst['start_date'].date()} to {worst['end_date'].date()}")
        print(f"  Return: {worst['strategy_return']:+.2%} vs HODL: {worst['hodl_return']:+.2%}")
        print(f"  Trades: {worst['total_trades']}, Win Rate: {worst['win_rate']:.0%}")
        print()

    # Assessment
    print(f"{'='*90}")
    print("ASSESSMENT")
    print(f"{'='*90}\n")

    if len(traded) == 0:
        print("❌ STILL TOO CONSERVATIVE: No trades in any window")
        print("   Even with relaxed risk, strategy won't trade")
        print("   Need to: Lower confidence threshold OR reduce risk weight")
    elif len(profitable) / len(results) >= 0.6:
        print(f"✅ STRONG: Profitable in {len(profitable)/len(results):.0%} of windows")
        print("   Making real money, not just preserving capital")
    elif len(beat_hodl) / len(results) >= 0.6:
        print("⚠️  DEFENSIVE: Beats HODL but not consistently profitable")
        print("   Good at capital preservation, needs profit optimization")
    else:
        print("❌ WEAK: Inconsistent performance")

    print(f"\n{'='*90}\n")


if __name__ == "__main__":
    asyncio.run(main())
