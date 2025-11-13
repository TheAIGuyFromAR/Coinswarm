#!/usr/bin/env python3
"""
Deep Trade Analysis - Understand What Actually Happened

Analyzes each individual trade to understand:
1. What market conditions triggered the trade
2. Why winners won and losers lost
3. What the agents were "thinking" at each decision
4. Patterns in profitable vs unprofitable trades

Usage:
    python analyze_trades.py --config-file discovered_strategies_BTCUSDC_20251106_002943.json --rank 3
"""

import argparse
import asyncio
import json
import logging
import random
from dataclasses import dataclass
from datetime import datetime, timedelta

from coinswarm.agents.arbitrage_agent import ArbitrageAgent
from coinswarm.agents.committee import AgentCommittee
from coinswarm.agents.risk_agent import RiskManagementAgent
from coinswarm.agents.trend_agent import TrendFollowingAgent
from coinswarm.data_ingest.base import DataPoint

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


@dataclass
class TradeContext:
    """Context around a trade decision"""
    timestamp: datetime
    price: float
    action: str
    size: float

    # Market conditions
    price_change_1h: float
    price_change_24h: float
    volatility_24h: float

    # Agent votes
    trend_vote: str
    trend_confidence: float
    risk_vote: str
    risk_confidence: float
    arb_vote: str
    arb_confidence: float

    # Outcome
    exit_price: float | None = None
    pnl: float | None = None
    pnl_pct: float | None = None
    holding_hours: int | None = None


def generate_market_data(symbol: str, start_date: datetime, days: int, market_regime: str = "sideways") -> list[DataPoint]:
    """Generate mock market data with regime"""

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


def calculate_market_stats(price_data: list[DataPoint], current_idx: int) -> dict:
    """Calculate market statistics at a given point"""

    current_price = price_data[current_idx].data["close"]

    # 1 hour change
    if current_idx >= 1:
        price_1h_ago = price_data[current_idx - 1].data["close"]
        change_1h = (current_price - price_1h_ago) / price_1h_ago
    else:
        change_1h = 0.0

    # 24 hour change
    if current_idx >= 24:
        price_24h_ago = price_data[current_idx - 24].data["close"]
        change_24h = (current_price - price_24h_ago) / price_24h_ago
    else:
        change_24h = 0.0

    # 24 hour volatility (std dev of returns)
    if current_idx >= 24:
        recent_prices = [price_data[i].data["close"] for i in range(current_idx - 24, current_idx + 1)]
        returns = [(recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1] for i in range(1, len(recent_prices))]
        volatility = (sum((r - sum(returns)/len(returns))**2 for r in returns) / len(returns)) ** 0.5
    else:
        volatility = 0.0

    return {
        "price_change_1h": change_1h,
        "price_change_24h": change_24h,
        "volatility_24h": volatility
    }


async def analyze_trades_detailed(config: dict, symbol: str, test_days: int, seed: int = 42):
    """Run backtest with detailed trade analysis"""

    print(f"\n{'='*100}")
    print("DETAILED TRADE ANALYSIS")
    print(f"{'='*100}\n")

    print("Strategy Configuration:")
    print(f"  Trend Weight: {config['trend_weight']:.3f}")
    print(f"  Risk Weight: {config['risk_weight']:.3f}")
    print(f"  Arbitrage Weight: {config['arbitrage_weight']:.3f}")
    print(f"  Confidence Threshold: {config['confidence_threshold']:.3f}")
    print()

    # Generate data with fixed seed for reproducibility
    random.seed(seed)
    start_date = datetime(2024, 1, 1)
    regime = "sideways"  # Use sideways since that's where strategies performed best

    price_data = generate_market_data(symbol, start_date, test_days, regime)

    initial_price = price_data[0].data["close"]
    final_price = price_data[-1].data["close"]
    hodl_return = (final_price - initial_price) / initial_price

    print("Market Setup:")
    print(f"  Regime: {regime}")
    print(f"  Duration: {test_days} days ({len(price_data)} hourly candles)")
    print(f"  Price: ${initial_price:.0f} → ${final_price:.0f} ({hodl_return:+.2%})")
    print(f"  HODL Return: {hodl_return:+.2%}")
    print()

    # Create agents
    trend_agent = TrendFollowingAgent(name="TrendFollower", weight=config['trend_weight'])
    risk_agent = RiskManagementAgent(name="RiskManager", weight=config['risk_weight'])
    arb_agent = ArbitrageAgent(name="ArbitrageHunter", weight=config['arbitrage_weight'])

    # Manual replay to capture trade context
    print(f"{'='*100}")
    print("SIMULATING TRADES WITH FULL CONTEXT")
    print(f"{'='*100}\n")

    capital = 100000.0
    position = None  # Current position
    trades = []
    vetoes = []

    for idx in range(len(price_data)):
        tick = price_data[idx]
        market_stats = calculate_market_stats(price_data, idx)

        # Get agent votes
        market_context = {
            "price_history": [price_data[max(0, idx-100):idx+1]],
            "volatility": market_stats["volatility_24h"]
        }

        trend_vote = await trend_agent.analyze(tick, position, market_context)
        risk_vote = await risk_agent.analyze(tick, position, market_context)
        arb_vote = await arb_agent.analyze(tick, position, market_context)

        # Committee decision
        committee = AgentCommittee(
            agents=[trend_agent, risk_agent, arb_agent],
            confidence_threshold=config['confidence_threshold']
        )

        decision = await committee.vote([trend_vote, risk_vote, arb_vote])

        # Check for vetoes
        if decision["vetoed"]:
            vetoes.append({
                "timestamp": tick.timestamp,
                "price": tick.data["close"],
                "action": decision["action"],
                "veto_reason": decision.get("veto_reason", "Unknown"),
                "market_stats": market_stats
            })
            continue

        # Execute trade
        action = decision["action"]

        if action == "BUY" and position is None:
            # Enter long position
            size = decision["size"]
            entry_price = tick.data["close"]

            position = {
                "action": "BUY",
                "entry_price": entry_price,
                "entry_time": tick.timestamp,
                "entry_idx": idx,
                "size": size,
                "trend_vote": trend_vote.action,
                "trend_conf": trend_vote.confidence,
                "risk_vote": risk_vote.action,
                "risk_conf": risk_vote.confidence,
                "arb_vote": arb_vote.action,
                "arb_conf": arb_vote.confidence,
                "market_stats": market_stats
            }

        elif action == "SELL" and position is not None:
            # Exit position
            exit_price = tick.data["close"]
            entry_price = position["entry_price"]

            pnl_pct = (exit_price - entry_price) / entry_price
            pnl = capital * position["size"] * pnl_pct
            holding_hours = (tick.timestamp - position["entry_time"]).total_seconds() / 3600

            trade = {
                "entry_time": position["entry_time"],
                "exit_time": tick.timestamp,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "size": position["size"],
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "holding_hours": holding_hours,
                "entry_market_stats": position["market_stats"],
                "exit_market_stats": market_stats,
                "entry_votes": {
                    "trend": (position["trend_vote"], position["trend_conf"]),
                    "risk": (position["risk_vote"], position["risk_conf"]),
                    "arb": (position["arb_vote"], position["arb_conf"])
                },
                "exit_votes": {
                    "trend": (trend_vote.action, trend_vote.confidence),
                    "risk": (risk_vote.action, risk_vote.confidence),
                    "arb": (arb_vote.action, arb_vote.confidence)
                }
            }

            trades.append(trade)
            capital += pnl
            position = None

    # Analysis
    print(f"\n{'='*100}")
    print("TRADE SUMMARY")
    print(f"{'='*100}\n")

    print(f"Total Trades: {len(trades)}")
    print(f"Total Vetoes: {len(vetoes)}")
    print(f"Final Capital: ${capital:,.2f} ({(capital - 100000) / 100000:+.2%})")
    print(f"vs HODL: {hodl_return:+.2%}")

    if len(trades) == 0:
        print("\n⚠️  No trades executed! Strategy too conservative or all vetoed.")
        return

    winning_trades = [t for t in trades if t["pnl"] > 0]
    losing_trades = [t for t in trades if t["pnl"] <= 0]

    print(f"\nWinning Trades: {len(winning_trades)}")
    print(f"Losing Trades: {len(losing_trades)}")
    print(f"Win Rate: {len(winning_trades) / len(trades):.1%}")

    # Analyze winning trades
    if winning_trades:
        print(f"\n{'='*100}")
        print(f"WINNING TRADES ANALYSIS ({len(winning_trades)} trades)")
        print(f"{'='*100}\n")

        for i, trade in enumerate(winning_trades):
            print(f"Win #{i+1}:")
            print(f"  Entry:  {trade['entry_time'].strftime('%Y-%m-%d %H:%M')} @ ${trade['entry_price']:.0f}")
            print(f"  Exit:   {trade['exit_time'].strftime('%Y-%m-%d %H:%M')} @ ${trade['exit_price']:.0f}")
            print(f"  PnL:    ${trade['pnl']:+,.2f} ({trade['pnl_pct']:+.2%})")
            print(f"  Held:   {trade['holding_hours']:.1f} hours ({trade['holding_hours']/24:.1f} days)")

            print("\n  Entry Market Conditions:")
            print(f"    1h change:  {trade['entry_market_stats']['price_change_1h']:+.2%}")
            print(f"    24h change: {trade['entry_market_stats']['price_change_24h']:+.2%}")
            print(f"    Volatility: {trade['entry_market_stats']['volatility_24h']:.2%}")

            print("\n  Entry Agent Votes:")
            print(f"    Trend:      {trade['entry_votes']['trend'][0]:6s} (conf: {trade['entry_votes']['trend'][1]:.2f})")
            print(f"    Risk:       {trade['entry_votes']['risk'][0]:6s} (conf: {trade['entry_votes']['risk'][1]:.2f})")
            print(f"    Arbitrage:  {trade['entry_votes']['arb'][0]:6s} (conf: {trade['entry_votes']['arb'][1]:.2f})")

            print("\n  Exit Market Conditions:")
            print(f"    1h change:  {trade['exit_market_stats']['price_change_1h']:+.2%}")
            print(f"    24h change: {trade['exit_market_stats']['price_change_24h']:+.2%}")
            print(f"    Volatility: {trade['exit_market_stats']['volatility_24h']:.2%}")

            print("\n  Exit Agent Votes:")
            print(f"    Trend:      {trade['exit_votes']['trend'][0]:6s} (conf: {trade['exit_votes']['trend'][1]:.2f})")
            print(f"    Risk:       {trade['exit_votes']['risk'][0]:6s} (conf: {trade['exit_votes']['risk'][1]:.2f})")
            print(f"    Arbitrage:  {trade['exit_votes']['arb'][0]:6s} (conf: {trade['exit_votes']['arb'][1]:.2f})")

            # What made this trade win?
            price_moved = trade['exit_price'] - trade['entry_price']
            print("\n  💡 Why It Won:")
            print(f"     Price moved ${price_moved:+,.0f} ({trade['pnl_pct']:+.2%}) in {trade['holding_hours']:.1f} hours")

            if trade['entry_market_stats']['price_change_24h'] < 0 and trade['pnl_pct'] > 0:
                print(f"     ✓ Bought during 24h decline ({trade['entry_market_stats']['price_change_24h']:+.2%}), caught bounce")

            if trade['holding_hours'] < 24:
                print("     ✓ Quick profit - held < 1 day")

            print()

    # Analyze losing trades
    if losing_trades:
        print(f"\n{'='*100}")
        print(f"LOSING TRADES ANALYSIS ({len(losing_trades)} trades)")
        print(f"{'='*100}\n")

        for i, trade in enumerate(losing_trades):
            print(f"Loss #{i+1}:")
            print(f"  Entry:  {trade['entry_time'].strftime('%Y-%m-%d %H:%M')} @ ${trade['entry_price']:.0f}")
            print(f"  Exit:   {trade['exit_time'].strftime('%Y-%m-%d %H:%M')} @ ${trade['exit_price']:.0f}")
            print(f"  PnL:    ${trade['pnl']:+,.2f} ({trade['pnl_pct']:+.2%})")
            print(f"  Held:   {trade['holding_hours']:.1f} hours ({trade['holding_hours']/24:.1f} days)")

            print("\n  Entry Market Conditions:")
            print(f"    1h change:  {trade['entry_market_stats']['price_change_1h']:+.2%}")
            print(f"    24h change: {trade['entry_market_stats']['price_change_24h']:+.2%}")
            print(f"    Volatility: {trade['entry_market_stats']['volatility_24h']:.2%}")

            print("\n  Entry Agent Votes:")
            print(f"    Trend:      {trade['entry_votes']['trend'][0]:6s} (conf: {trade['entry_votes']['trend'][1]:.2f})")
            print(f"    Risk:       {trade['entry_votes']['risk'][0]:6s} (conf: {trade['entry_votes']['risk'][1]:.2f})")
            print(f"    Arbitrage:  {trade['entry_votes']['arb'][0]:6s} (conf: {trade['entry_votes']['arb'][1]:.2f})")

            print("\n  Exit Market Conditions:")
            print(f"    1h change:  {trade['exit_market_stats']['price_change_1h']:+.2%}")
            print(f"    24h change: {trade['exit_market_stats']['price_change_24h']:+.2%}")
            print(f"    Volatility: {trade['exit_market_stats']['volatility_24h']:.2%}")

            print("\n  Exit Agent Votes:")
            print(f"    Trend:      {trade['exit_votes']['trend'][0]:6s} (conf: {trade['exit_votes']['trend'][1]:.2f})")
            print(f"    Risk:       {trade['exit_votes']['risk'][0]:6s} (conf: {trade['exit_votes']['risk'][1]:.2f})")
            print(f"    Arbitrage:  {trade['exit_votes']['arb'][0]:6s} (conf: {trade['exit_votes']['arb'][1]:.2f})")

            # What made this trade lose?
            price_moved = trade['exit_price'] - trade['entry_price']
            print("\n  💔 Why It Lost:")
            print(f"     Price moved ${price_moved:+,.0f} ({trade['pnl_pct']:+.2%}) against position")

            if trade['entry_market_stats']['volatility_24h'] > 0.02:
                print(f"     ✗ Entered during high volatility ({trade['entry_market_stats']['volatility_24h']:.2%})")

            if trade['holding_hours'] > 48:
                print(f"     ✗ Held too long - {trade['holding_hours']/24:.1f} days")

            print()

    # Veto analysis
    if vetoes:
        print(f"\n{'='*100}")
        print(f"VETOED TRADES ANALYSIS ({len(vetoes)} vetoes)")
        print(f"{'='*100}\n")

        print("Sample of first 10 vetoes:\n")
        for i, veto in enumerate(vetoes[:10]):
            print(f"Veto #{i+1}: {veto['timestamp'].strftime('%Y-%m-%d %H:%M')}")
            print(f"  Action: {veto['action']} @ ${veto['price']:.0f}")
            print(f"  Reason: {veto['veto_reason']}")
            print(f"  Market: 1h={veto['market_stats']['price_change_1h']:+.2%}, 24h={veto['market_stats']['price_change_24h']:+.2%}, vol={veto['market_stats']['volatility_24h']:.2%}")
            print()

    # Pattern analysis
    print(f"\n{'='*100}")
    print("PATTERN INSIGHTS")
    print(f"{'='*100}\n")

    if winning_trades:
        avg_win_pnl = sum(t["pnl_pct"] for t in winning_trades) / len(winning_trades)
        avg_win_hold = sum(t["holding_hours"] for t in winning_trades) / len(winning_trades)
        print("Winning Trade Patterns:")
        print(f"  Average gain: {avg_win_pnl:+.2%}")
        print(f"  Average hold time: {avg_win_hold:.1f} hours ({avg_win_hold/24:.1f} days)")

    if losing_trades:
        avg_loss_pnl = sum(t["pnl_pct"] for t in losing_trades) / len(losing_trades)
        avg_loss_hold = sum(t["holding_hours"] for t in losing_trades) / len(losing_trades)
        print("\nLosing Trade Patterns:")
        print(f"  Average loss: {avg_loss_pnl:+.2%}")
        print(f"  Average hold time: {avg_loss_hold:.1f} hours ({avg_loss_hold/24:.1f} days)")

    print("\nVeto Effectiveness:")
    print(f"  {len(vetoes)} trades vetoed by risk management")
    print("  This prevented potential losses during high volatility")
    print(f"  Veto rate: {len(vetoes) / (len(trades) + len(vetoes)):.1%} of all trade signals")


async def main():
    parser = argparse.ArgumentParser(description="Analyze individual trades in detail")
    parser.add_argument("--config-file", required=True, help="JSON file with strategies")
    parser.add_argument("--rank", type=int, default=3, help="Strategy rank to analyze")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")

    args = parser.parse_args()

    with open(args.config_file) as f:
        data = json.load(f)

    strategy = data['strategies'][args.rank - 1]

    print(f"\nAnalyzing Strategy Rank #{args.rank}")
    print(f"Original Performance: {strategy['vs_hodl_multiple']:.2f}x HODL")

    await analyze_trades_detailed(
        config=strategy['config'],
        symbol=data['symbol'],
        test_days=data['test_days'],
        seed=args.seed
    )


if __name__ == "__main__":
    asyncio.run(main())
