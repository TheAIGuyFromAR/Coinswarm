#!/usr/bin/env python3
"""
Find 10x BTC-Denominated Strategies

Goal: Profit denominated in BITCOIN, not USD.
- Not keeping up with BTC appreciation = LOSING
- Must beat HODL in absolute BTC accumulation
- Target: 10x more BTC at end than HODL

Example:
- Start: $100K at BTC $50K = 2.0 BTC
- HODL: 2.0 BTC (no change in BTC amount)
- Target: 20.0 BTC (10x more BTC)
- If BTC ends at $100K: Need $2M USD (20 BTC × $100K)
- That's 20x in USD terms to get 10x in BTC terms!

Usage:
    python find_10x_btc_strategies.py --generations 100
"""

import argparse
import asyncio
import json
import random
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta

from coinswarm.agents.arbitrage_agent import ArbitrageAgent
from coinswarm.agents.committee import AgentCommittee
from coinswarm.agents.risk_agent import RiskManagementAgent
from coinswarm.agents.trend_agent import TrendFollowingAgent
from coinswarm.backtesting.backtest_engine import BacktestConfig, BacktestEngine
from coinswarm.data_ingest.base import DataPoint


@dataclass
class BTCStrategyConfig:
    """Configuration optimized for BTC accumulation"""
    trend_weight: float
    risk_weight: float
    arbitrage_weight: float
    confidence_threshold: float

    def mutate(self, rate: float = 0.25) -> 'BTCStrategyConfig':
        return BTCStrategyConfig(
            trend_weight=max(0.1, self.trend_weight * random.uniform(1-rate, 1+rate)),
            risk_weight=max(0.1, self.risk_weight * random.uniform(1-rate, 1+rate)),
            arbitrage_weight=max(0.1, self.arbitrage_weight * random.uniform(1-rate, 1+rate)),
            confidence_threshold=max(0.2, min(0.8, self.confidence_threshold + random.uniform(-0.1, 0.1)))
        )

    @staticmethod
    def crossover(p1: 'BTCStrategyConfig', p2: 'BTCStrategyConfig') -> 'BTCStrategyConfig':
        return BTCStrategyConfig(
            trend_weight=(p1.trend_weight + p2.trend_weight) / 2,
            risk_weight=(p1.risk_weight + p2.risk_weight) / 2,
            arbitrage_weight=(p1.arbitrage_weight + p2.arbitrage_weight) / 2,
            confidence_threshold=(p1.confidence_threshold + p2.confidence_threshold) / 2
        )


@dataclass
class BTCStrategyResult:
    """Result measured in BTC terms"""
    config: BTCStrategyConfig

    # USD metrics
    usd_return_pct: float
    usd_final_capital: float

    # BTC metrics (THE IMPORTANT ONES)
    btc_start: float  # BTC at start
    btc_end: float    # BTC at end
    btc_gained: float  # BTC gained/lost
    btc_gain_pct: float  # % gain in BTC

    # vs HODL in BTC terms
    btc_hodl: float  # BTC if just held
    btc_vs_hodl_multiple: float  # How many X more BTC than HODL

    # Other metrics
    sharpe_ratio: float
    max_drawdown_pct: float
    total_trades: int
    win_rate: float
    market_regime: str

    def is_10x_btc(self) -> bool:
        """Check if beats HODL by 10x in BTC terms"""
        return (
            self.btc_vs_hodl_multiple >= 10.0 and
            self.btc_gained > 0 and  # Actually gained BTC
            self.sharpe_ratio >= 1.5 and
            self.max_drawdown_pct <= 40.0 and
            self.total_trades >= 5
        )


def generate_btc_market_data(
    start_date: datetime,
    days: int,
    btc_trend: float = 0.0  # Daily BTC appreciation (-1.0 to +1.0)
) -> tuple[list[DataPoint], float, float]:
    """
    Generate BTC price data

    Returns: (data_points, initial_btc_price, final_btc_price)
    """
    data_points = []
    current_price = 50000.0
    initial_price = current_price
    current_time = start_date

    # BTC-specific parameters
    base_volatility = 0.03  # 3% daily volatility

    for hour in range(days * 24):
        # BTC trend component
        trend_component = btc_trend / 24  # Convert daily to hourly

        # Add momentum
        momentum = 0.0
        if hour > 24:
            price_24h_ago = data_points[hour-24].data["close"]
            momentum = (current_price - price_24h_ago) / price_24h_ago * 0.15

        # Volatility
        vol = base_volatility
        if random.random() < 0.05:  # 5% chance of volatility spike
            vol *= random.uniform(1.5, 3.0)

        change_pct = random.gauss(trend_component + momentum, vol)
        current_price *= (1 + change_pct)

        # Realistic BTC bounds
        current_price = max(20000, min(150000, current_price))

        # OHLCV
        open_price = current_price
        close_price = current_price * (1 + random.gauss(0, 0.002))
        high_price = max(open_price, close_price) * (1 + abs(random.gauss(0, 0.008)))
        low_price = min(open_price, close_price) * (1 - abs(random.gauss(0, 0.008)))
        volume = random.uniform(5000, 20000) * (1 + abs(change_pct) * 10)

        data_point = DataPoint(
            source="mock_btc",
            symbol="BTC-USD",
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


async def test_btc_strategy(
    config: BTCStrategyConfig,
    test_days: int,
    btc_trend: float = 0.0
) -> BTCStrategyResult:
    """Test strategy with BTC-denominated accounting"""

    start_date = datetime.now() - timedelta(days=random.randint(test_days + 1, 365))

    # Generate data
    price_data, initial_btc_price, final_btc_price = generate_btc_market_data(
        start_date, test_days, btc_trend
    )

    # Create committee
    agents = [
        TrendFollowingAgent(name="Trend", weight=config.trend_weight),
        RiskManagementAgent(name="Risk", weight=config.risk_weight),
        ArbitrageAgent(name="Arb", weight=config.arbitrage_weight),
    ]

    committee = AgentCommittee(
        agents=agents,
        confidence_threshold=config.confidence_threshold
    )

    # Backtest
    initial_capital = 100000  # $100K USD
    backtest_config = BacktestConfig(
        start_date=price_data[0].timestamp,
        end_date=price_data[-1].timestamp,
        initial_capital=initial_capital,
        symbols=["BTC-USD"],
        timeframe="1h",
        commission=0.001,
        slippage=0.0005
    )

    historical_data = {"BTC-USD": price_data}
    engine = BacktestEngine(backtest_config)
    result = await engine.run_backtest(committee, historical_data)

    # Calculate BTC-denominated metrics
    btc_start = initial_capital / initial_btc_price
    btc_hodl = btc_start  # HODL means BTC amount doesn't change

    final_capital = initial_capital + result.total_return
    btc_end = final_capital / final_btc_price

    btc_gained = btc_end - btc_start
    btc_gain_pct = (btc_end - btc_start) / btc_start

    # vs HODL in BTC terms
    btc_vs_hodl_multiple = btc_end / btc_hodl if btc_hodl > 0 else 0

    # Market regime
    btc_price_change = (final_btc_price - initial_btc_price) / initial_btc_price
    if btc_price_change > 0.3:
        regime = "strong_bull"
    elif btc_price_change > 0.1:
        regime = "bull"
    elif btc_price_change < -0.3:
        regime = "strong_bear"
    elif btc_price_change < -0.1:
        regime = "bear"
    else:
        regime = "sideways"

    return BTCStrategyResult(
        config=config,
        usd_return_pct=result.total_return_pct,
        usd_final_capital=final_capital,
        btc_start=btc_start,
        btc_end=btc_end,
        btc_gained=btc_gained,
        btc_gain_pct=btc_gain_pct,
        btc_hodl=btc_hodl,
        btc_vs_hodl_multiple=btc_vs_hodl_multiple,
        sharpe_ratio=result.sharpe_ratio,
        max_drawdown_pct=result.max_drawdown_pct,
        total_trades=result.total_trades,
        win_rate=result.win_rate,
        market_regime=regime
    )


async def hunt_10x_btc_strategies(
    test_days: int = 180,
    target_count: int = 10,
    population_size: int = 40,
    max_generations: int = 100
):
    """Hunt for strategies that 10x BTC accumulation"""

    print("\n" + "="*90)
    print("₿ HUNTING FOR 10X BTC-DENOMINATED STRATEGIES")
    print("="*90 + "\n")

    print("Goal: Accumulate 10x more BTC than HODL")
    print("Profit Metric: BITCOIN, not USD")
    print("Not keeping up with BTC = LOSING\n")

    print("Target Criteria:")
    print("  • 10x more BTC than HODL")
    print("  • Positive BTC accumulation")
    print("  • Sharpe > 1.5")
    print("  • Max DD < 40%")
    print("  • At least 5 trades\n")

    # Test across different BTC market conditions
    btc_trends = [
        -0.003,  # Bear: -0.3% daily (crashes)
        0.0,     # Sideways
        0.002,   # Bull: +0.2% daily
        0.005,   # Strong bull: +0.5% daily
    ]

    # Initialize population favoring MORE trading (lower confidence)
    population = [
        BTCStrategyConfig(
            trend_weight=random.uniform(0.5, 3.0),
            risk_weight=random.uniform(0.3, 2.0),  # Lower risk weight
            arbitrage_weight=random.uniform(0.5, 3.0),
            confidence_threshold=random.uniform(0.25, 0.55)  # MUCH lower
        )
        for _ in range(population_size)
    ]

    found_10x: list[BTCStrategyResult] = []
    all_time_best: BTCStrategyResult = None

    for generation in range(max_generations):
        print(f"\n{'='*90}")
        print(f"Generation {generation + 1}/{max_generations}")
        print(f"{'='*90}")

        results: list[BTCStrategyResult] = []

        for i, config in enumerate(population):
            # Test on random BTC trend
            btc_trend = random.choice(btc_trends)

            result = await test_btc_strategy(config, test_days, btc_trend)
            results.append(result)

            # Check for 10x BTC
            if result.is_10x_btc():
                found_10x.append(result)
                print(f"\n🎉 10X BTC FOUND! #{len(found_10x)}")
                print(f"   BTC: {result.btc_start:.4f} → {result.btc_end:.4f} (+{result.btc_gained:+.4f} BTC)")
                print(f"   vs HODL: {result.btc_vs_hodl_multiple:.2f}x more BTC")
                print(f"   USD Return: {result.usd_return_pct:+.1%}")
                print(f"   Trades: {result.total_trades}, Win%: {result.win_rate:.0%}, Sharpe: {result.sharpe_ratio:.2f}")

            # Track best
            if all_time_best is None or result.btc_vs_hodl_multiple > all_time_best.btc_vs_hodl_multiple:
                all_time_best = result
                print(f"\n🏆 Best BTC vs HODL: {result.btc_vs_hodl_multiple:.2f}x")
                print(f"   (+{result.btc_gained:+.4f} BTC)")

            if (i + 1) % 10 == 0:
                print(f"  Tested {i+1}/{population_size}...")

        # Summary
        print(f"\n📊 Generation {generation + 1}:")
        print(f"  10x BTC Found: {len(found_10x)}")
        print(f"  Best BTC vs HODL: {all_time_best.btc_vs_hodl_multiple:.2f}x")
        print(f"  Best BTC Gained: {all_time_best.btc_gained:+.4f} BTC")

        # Top 3
        results.sort(key=lambda r: r.btc_vs_hodl_multiple, reverse=True)
        print("\n  Top 3:")
        for i, r in enumerate(results[:3]):
            print(f"    {i+1}. {r.btc_vs_hodl_multiple:.2f}x BTC ({r.btc_gained:+.4f} BTC), "
                  f"USD: {r.usd_return_pct:+.1%}, Trades: {r.total_trades}")

        if len(found_10x) >= target_count:
            print(f"\n🎊 SUCCESS! Found {len(found_10x)} strategies with 10x BTC!")
            break

        # Evolve
        elite_size = 5
        results.sort(key=lambda r: r.btc_vs_hodl_multiple * (r.total_trades / 50 + 0.5), reverse=True)
        elite = results[:elite_size]

        new_population = [r.config for r in elite]

        while len(new_population) < population_size:
            weights = [max(r.btc_vs_hodl_multiple, 0.1) for r in elite]
            total = sum(weights)

            if total > 0:
                p1 = random.choices(elite, weights=weights)[0]
                p2 = random.choices(elite, weights=weights)[0]
                child = BTCStrategyConfig.crossover(p1.config, p2.config)

                if random.random() < 0.35:
                    child = child.mutate(0.25)

                new_population.append(child)
            else:
                new_population.append(BTCStrategyConfig(
                    trend_weight=random.uniform(0.5, 3.0),
                    risk_weight=random.uniform(0.3, 2.0),
                    arbitrage_weight=random.uniform(0.5, 3.0),
                    confidence_threshold=random.uniform(0.25, 0.55)
                ))

        population = new_population

    # Final results
    print(f"\n\n{'='*90}")
    print("🏁 HUNT COMPLETE")
    print(f"{'='*90}\n")

    print(f"Generations: {generation + 1}")
    print(f"Total Tests: {(generation + 1) * population_size}")
    print(f"10x BTC Strategies: {len(found_10x)}\n")

    if found_10x:
        print(f"{'='*90}")
        print(f"🎉 FOUND {len(found_10x)} STRATEGIES WITH 10X BTC!")
        print(f"{'='*90}\n")

        for i, s in enumerate(found_10x):
            print(f"{i+1}. BTC: {s.btc_start:.4f} → {s.btc_end:.4f} ({s.btc_gained:+.4f} BTC)")
            print(f"   vs HODL: {s.btc_vs_hodl_multiple:.2f}x more BTC")
            print(f"   USD Return: {s.usd_return_pct:+.1%}")
            print(f"   Sharpe: {s.sharpe_ratio:.2f}, Win: {s.win_rate:.0%}, Trades: {s.total_trades}")
            print(f"   Regime: {s.market_regime}")
            print(f"   Config: T={s.config.trend_weight:.2f} R={s.config.risk_weight:.2f} "
                  f"A={s.config.arbitrage_weight:.2f} C={s.config.confidence_threshold:.2f}\n")

        # Save
        filename = f"10x_btc_strategies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump({
                "discovered_at": datetime.now().isoformat(),
                "metric": "BTC_accumulation",
                "goal": "10x_more_BTC_than_HODL",
                "strategies": [
                    {
                        "rank": i + 1,
                        "btc_start": s.btc_start,
                        "btc_end": s.btc_end,
                        "btc_gained": s.btc_gained,
                        "btc_gain_pct": s.btc_gain_pct,
                        "btc_vs_hodl_multiple": s.btc_vs_hodl_multiple,
                        "usd_return_pct": s.usd_return_pct,
                        "sharpe": s.sharpe_ratio,
                        "trades": s.total_trades,
                        "win_rate": s.win_rate,
                        "regime": s.market_regime,
                        "config": asdict(s.config)
                    }
                    for i, s in enumerate(found_10x)
                ]
            }, f, indent=2)
        print(f"💾 Saved to: {filename}\n")

    else:
        print("❌ No 10x BTC strategies found")
        print("\nBest Achieved:")
        print(f"  BTC vs HODL: {all_time_best.btc_vs_hodl_multiple:.2f}x")
        print(f"  BTC Gained: {all_time_best.btc_gained:+.4f}")
        print(f"  USD Return: {all_time_best.usd_return_pct:+.1%}\n")

    print(f"{'='*90}\n")


async def main():
    parser = argparse.ArgumentParser(description="Hunt for 10x BTC-denominated strategies")
    parser.add_argument("--test-days", type=int, default=180, help="Test period")
    parser.add_argument("--target-count", type=int, default=10, help="Number to find")
    parser.add_argument("--population", type=int, default=40, help="Population size")
    parser.add_argument("--generations", type=int, default=100, help="Max generations")

    args = parser.parse_args()

    await hunt_10x_btc_strategies(
        test_days=args.test_days,
        target_count=args.target_count,
        population_size=args.population,
        max_generations=args.generations
    )


if __name__ == "__main__":
    asyncio.run(main())
