#!/usr/bin/env python3
"""
Find 10x NOMINAL + 10x HODL Strategies

Searches for strategies that achieve BOTH:
1. 10x nominal returns (1000%+ absolute gains)
2. 10x HODL (beat buy-and-hold by 10x)

This is MUCH harder than just capital preservation.

Usage:
    python find_10x_nominal_strategies.py --test-days 180 --target-count 10
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
class AggressiveStrategyConfig:
    """More aggressive strategy configuration"""
    trend_weight: float
    risk_weight: float
    arbitrage_weight: float
    confidence_threshold: float  # Lower = more trades

    def mutate(self, mutation_rate: float = 0.3) -> 'AggressiveStrategyConfig':
        """Create mutated copy with larger variations"""
        return AggressiveStrategyConfig(
            trend_weight=max(0.1, self.trend_weight * random.uniform(1-mutation_rate, 1+mutation_rate)),
            risk_weight=max(0.1, self.risk_weight * random.uniform(1-mutation_rate, 1+mutation_rate)),
            arbitrage_weight=max(0.1, self.arbitrage_weight * random.uniform(1-mutation_rate, 1+mutation_rate)),
            confidence_threshold=max(0.2, min(0.8, self.confidence_threshold + random.uniform(-0.15, 0.15)))
        )

    @staticmethod
    def crossover(parent1: 'AggressiveStrategyConfig', parent2: 'AggressiveStrategyConfig') -> 'AggressiveStrategyConfig':
        """Breed two configurations"""
        return AggressiveStrategyConfig(
            trend_weight=(parent1.trend_weight + parent2.trend_weight) / 2,
            risk_weight=(parent1.risk_weight + parent2.risk_weight) / 2,
            arbitrage_weight=(parent1.arbitrage_weight + parent2.arbitrage_weight) / 2,
            confidence_threshold=(parent1.confidence_threshold + parent2.confidence_threshold) / 2
        )


@dataclass
class StrategyResult:
    """Extended result tracking"""
    config: AggressiveStrategyConfig
    return_pct: float  # Absolute return
    hodl_return_pct: float
    vs_hodl_multiple: float
    nominal_multiple: float  # How many X capital (e.g., 10x = 1000% return)
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    win_rate: float
    total_trades: int
    profit_factor: float
    start_date: datetime
    market_regime: str

    def is_10x_both(self) -> bool:
        """Check if beats 10x nominal AND 10x HODL"""
        return (
            self.nominal_multiple >= 10.0 and  # 1000%+ absolute returns
            self.vs_hodl_multiple >= 10.0 and  # 10x better than HODL
            self.sharpe_ratio >= 2.0 and       # Strong risk-adjusted returns
            self.max_drawdown_pct <= 40.0 and  # Acceptable drawdown
            self.total_trades >= 10            # Actually trades (not just sitting)
        )

    def is_5x_both(self) -> bool:
        """Less strict criteria for intermediate winners"""
        return (
            self.nominal_multiple >= 5.0 and
            self.vs_hodl_multiple >= 5.0 and
            self.sharpe_ratio >= 1.5
        )


def generate_volatile_market_data(
    symbol: str,
    start_date: datetime,
    days: int,
    volatility_multiplier: float = 1.5
) -> tuple:
    """
    Generate market data with higher volatility for testing aggressive strategies

    Returns: (data_points, initial_price, final_price)
    """
    data_points = []
    current_price = 50000.0 if symbol == "BTC-USDC" else 2500.0
    initial_price = current_price
    current_time = start_date

    # Random market trend
    overall_trend = random.uniform(-0.2, 0.5)  # -20% to +50% over period

    for hour in range(days * 24):
        # Create realistic but volatile price action
        trend_component = overall_trend / (days * 24)

        # Add momentum
        momentum = 0.0
        if hour > 24:
            price_24h_ago = data_points[hour-24].data["close"]
            momentum = (current_price - price_24h_ago) / price_24h_ago * 0.2

        # Base volatility with multiplier for more action
        base_vol = 0.02 * volatility_multiplier

        # Random volatility spikes (10% chance)
        if random.random() < 0.1:
            base_vol *= random.uniform(2, 5)

        change_pct = random.gauss(trend_component + momentum, base_vol)
        current_price *= (1 + change_pct)

        # Wider bounds for more volatility
        if symbol == "BTC-USDC":
            current_price = max(20000, min(100000, current_price))
        else:
            current_price = max(1000, min(6000, current_price))

        # Create OHLCV
        open_price = current_price
        close_price = current_price * (1 + random.gauss(0, 0.003))
        high_price = max(open_price, close_price) * (1 + abs(random.gauss(0, 0.01)))
        low_price = min(open_price, close_price) * (1 - abs(random.gauss(0, 0.01)))
        volume = random.uniform(1000, 10000) * (1 + abs(change_pct) * 20)

        data_point = DataPoint(
            source="mock_volatile",
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

    final_price = data_points[-1].data["close"]
    return data_points, initial_price, final_price


async def test_aggressive_strategy(
    config: AggressiveStrategyConfig,
    symbol: str,
    test_days: int,
    volatility_multiplier: float = 1.5
) -> StrategyResult:
    """Test an aggressive strategy configuration"""

    # Random start date
    days_ago = random.randint(test_days + 1, 365)
    start_date = datetime.now() - timedelta(days=days_ago)

    # Generate volatile market data
    price_data, initial_price, final_price = generate_volatile_market_data(
        symbol, start_date, test_days, volatility_multiplier
    )

    hodl_return = (final_price - initial_price) / initial_price

    # Create committee with aggressive settings
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
    backtest_config = BacktestConfig(
        start_date=price_data[0].timestamp,
        end_date=price_data[-1].timestamp,
        initial_capital=100000,
        symbols=[symbol],
        timeframe="1h",
        commission=0.001,
        slippage=0.0005
    )

    historical_data = {symbol: price_data}
    engine = BacktestEngine(backtest_config)
    result = await engine.run_backtest(committee, historical_data)

    # Calculate metrics
    nominal_multiple = (100000 + result.total_return) / 100000  # How many X initial capital

    # vs HODL calculation
    if hodl_return != 0:
        vs_hodl = result.total_return_pct / hodl_return
    else:
        vs_hodl = 0

    # Market regime
    if hodl_return > 0.2:
        regime = "strong_bull"
    elif hodl_return > 0.05:
        regime = "bull"
    elif hodl_return < -0.2:
        regime = "strong_bear"
    elif hodl_return < -0.05:
        regime = "bear"
    else:
        regime = "sideways"

    return StrategyResult(
        config=config,
        return_pct=result.total_return_pct,
        hodl_return_pct=hodl_return,
        vs_hodl_multiple=vs_hodl,
        nominal_multiple=nominal_multiple,
        sharpe_ratio=result.sharpe_ratio,
        sortino_ratio=result.sortino_ratio,
        max_drawdown_pct=result.max_drawdown_pct,
        win_rate=result.win_rate,
        total_trades=result.total_trades,
        profit_factor=result.profit_factor,
        start_date=start_date,
        market_regime=regime
    )


async def hunt_10x_strategies(
    symbol: str,
    test_days: int,
    target_count: int = 10,
    population_size: int = 30,
    max_generations: int = 100,
    volatility_multiplier: float = 1.5
):
    """
    Hunt for strategies that achieve 10x nominal AND 10x HODL
    """

    print("\n" + "="*90)
    print("🎯 HUNTING FOR 10X NOMINAL + 10X HODL STRATEGIES")
    print("="*90 + "\n")

    print(f"Target: Find {target_count} strategies with:")
    print("  • 10x nominal returns (1000%+ absolute)")
    print("  • 10x HODL (beat buy-and-hold by 10x)")
    print("  • Sharpe > 2.0")
    print("  • Max DD < 40%")
    print("  • At least 10 trades\n")

    print("Search Configuration:")
    print(f"  Symbol: {symbol}")
    print(f"  Test Period: {test_days} days")
    print(f"  Population: {population_size}")
    print(f"  Max Generations: {max_generations}")
    print(f"  Volatility: {volatility_multiplier}x normal\n")

    # Initialize AGGRESSIVE population (lower confidence, more trading)
    population = [
        AggressiveStrategyConfig(
            trend_weight=random.uniform(0.5, 3.0),      # Lower risk weight
            risk_weight=random.uniform(0.5, 2.5),       # Lower risk = more trades
            arbitrage_weight=random.uniform(0.5, 3.0),
            confidence_threshold=random.uniform(0.3, 0.6)  # Lower = more aggressive
        )
        for _ in range(population_size)
    ]

    # Track discoveries
    found_10x_both: list[StrategyResult] = []
    found_5x_both: list[StrategyResult] = []
    all_time_best_nominal: StrategyResult = None
    all_time_best_vs_hodl: StrategyResult = None

    # Evolution loop
    for generation in range(max_generations):
        print(f"\n{'='*90}")
        print(f"Generation {generation + 1}/{max_generations}")
        print(f"{'='*90}")

        # Test population
        results: list[StrategyResult] = []

        for i, config in enumerate(population):
            result = await test_aggressive_strategy(
                config, symbol, test_days, volatility_multiplier
            )
            results.append(result)

            # Check for 10x discoveries
            if result.is_10x_both():
                found_10x_both.append(result)
                print(f"\n🎉🎉🎉 10X BOTH FOUND! #{len(found_10x_both)}")
                print(f"   Nominal: {result.nominal_multiple:.2f}x ({result.return_pct:+.1%})")
                print(f"   vs HODL: {result.vs_hodl_multiple:.2f}x (HODL: {result.hodl_return_pct:+.1%})")
                print(f"   Sharpe: {result.sharpe_ratio:.2f}, Trades: {result.total_trades}, Win%: {result.win_rate:.0%}")
                print(f"   Config: T={result.config.trend_weight:.2f} R={result.config.risk_weight:.2f} A={result.config.arbitrage_weight:.2f} C={result.config.confidence_threshold:.2f}")

            elif result.is_5x_both():
                if len([r for r in found_5x_both if r.config == config]) == 0:  # Don't duplicate
                    found_5x_both.append(result)
                    print(f"\n⭐ 5X BOTH! #{len(found_5x_both)}")
                    print(f"   Nominal: {result.nominal_multiple:.2f}x, vs HODL: {result.vs_hodl_multiple:.2f}x")

            # Track best
            if all_time_best_nominal is None or result.nominal_multiple > all_time_best_nominal.nominal_multiple:
                all_time_best_nominal = result
                print(f"\n🏆 Best Nominal: {result.nominal_multiple:.2f}x ({result.return_pct:+.1%})")

            if all_time_best_vs_hodl is None or result.vs_hodl_multiple > all_time_best_vs_hodl.vs_hodl_multiple:
                all_time_best_vs_hodl = result
                print(f"\n🏆 Best vs HODL: {result.vs_hodl_multiple:.2f}x")

            if (i + 1) % 10 == 0:
                print(f"  Tested {i+1}/{population_size}...")

        # Summary
        print(f"\n📊 Generation {generation + 1} Summary:")
        print(f"  10x Both Found: {len(found_10x_both)}")
        print(f"  5x Both Found: {len(found_5x_both)}")
        print(f"  Best Nominal: {all_time_best_nominal.nominal_multiple:.2f}x")
        print(f"  Best vs HODL: {all_time_best_vs_hodl.vs_hodl_multiple:.2f}x")

        # Show top 3 this generation
        results.sort(key=lambda r: r.nominal_multiple * r.vs_hodl_multiple, reverse=True)
        print("\n  Top 3 This Generation:")
        for i, r in enumerate(results[:3]):
            print(f"    {i+1}. Nominal: {r.nominal_multiple:.2f}x, vs HODL: {r.vs_hodl_multiple:.2f}x, "
                  f"Return: {r.return_pct:+.1%}, Trades: {r.total_trades}")

        # Check if target reached
        if len(found_10x_both) >= target_count:
            print(f"\n🎊 SUCCESS! Found {len(found_10x_both)} strategies meeting 10x BOTH criteria!")
            break

        # Evolution: Prioritize strategies with higher nominal returns AND trades
        # Sort by combined score: nominal × vs_hodl × (trades/100)
        elite_size = 5
        results.sort(
            key=lambda r: r.nominal_multiple * max(r.vs_hodl_multiple, 0.1) * (r.total_trades / 100 + 0.1),
            reverse=True
        )
        elite = results[:elite_size]

        # Create next generation
        new_population = []

        # Keep elite
        new_population.extend([r.config for r in elite])

        # Breed from elite
        while len(new_population) < population_size:
            weights = [r.nominal_multiple * max(r.vs_hodl_multiple, 0.1) for r in elite]
            total_weight = sum(weights)

            if total_weight > 0:
                parent1 = random.choices(elite, weights=weights)[0]
                parent2 = random.choices(elite, weights=weights)[0]
                child = AggressiveStrategyConfig.crossover(parent1.config, parent2.config)

                # Mutate
                if random.random() < 0.4:  # 40% mutation rate
                    child = child.mutate(0.3)

                new_population.append(child)
            else:
                # Random if no good candidates
                new_population.append(AggressiveStrategyConfig(
                    trend_weight=random.uniform(0.5, 3.0),
                    risk_weight=random.uniform(0.5, 2.5),
                    arbitrage_weight=random.uniform(0.5, 3.0),
                    confidence_threshold=random.uniform(0.3, 0.6)
                ))

        population = new_population

    # Final results
    print(f"\n\n{'='*90}")
    print("🏁 HUNT COMPLETE")
    print(f"{'='*90}\n")

    print(f"Generations Run: {generation + 1}")
    print(f"Total Tests: {(generation + 1) * population_size}")
    print(f"10x Both Strategies: {len(found_10x_both)}")
    print(f"5x Both Strategies: {len(found_5x_both)}")

    if found_10x_both:
        print(f"\n{'='*90}")
        print(f"🎉 FOUND {len(found_10x_both)} STRATEGIES WITH 10X BOTH!")
        print(f"{'='*90}\n")

        for i, result in enumerate(found_10x_both):
            print(f"{i+1}. Nominal: {result.nominal_multiple:.2f}x ({result.return_pct:+.1%})")
            print(f"   vs HODL: {result.vs_hodl_multiple:.2f}x (HODL: {result.hodl_return_pct:+.1%})")
            print(f"   Sharpe: {result.sharpe_ratio:.2f}, Sortino: {result.sortino_ratio:.2f}")
            print(f"   Win Rate: {result.win_rate:.1%}, Trades: {result.total_trades}")
            print(f"   Max DD: {result.max_drawdown_pct:.1%}, PF: {result.profit_factor:.2f}")
            print(f"   Regime: {result.market_regime}")
            print(f"   Config: Trend={result.config.trend_weight:.3f}, Risk={result.config.risk_weight:.3f}, "
                  f"Arb={result.config.arbitrage_weight:.3f}, Conf={result.config.confidence_threshold:.3f}")
            print()

        # Save to file
        save_data = {
            "discovered_at": datetime.now().isoformat(),
            "symbol": symbol,
            "test_days": test_days,
            "criteria": "10x_nominal_AND_10x_hodl",
            "total_tests": (generation + 1) * population_size,
            "strategies": [
                {
                    "rank": i + 1,
                    "nominal_multiple": s.nominal_multiple,
                    "return_pct": s.return_pct,
                    "hodl_return_pct": s.hodl_return_pct,
                    "vs_hodl_multiple": s.vs_hodl_multiple,
                    "sharpe_ratio": s.sharpe_ratio,
                    "sortino_ratio": s.sortino_ratio,
                    "win_rate": s.win_rate,
                    "max_drawdown_pct": s.max_drawdown_pct,
                    "total_trades": s.total_trades,
                    "profit_factor": s.profit_factor,
                    "market_regime": s.market_regime,
                    "config": asdict(s.config)
                }
                for i, s in enumerate(found_10x_both)
            ]
        }

        filename = f"10x_both_strategies_{symbol.replace('-', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(save_data, f, indent=2)

        print(f"💾 Saved to: {filename}\n")

    elif found_5x_both:
        print(f"\n⚠️  No 10x BOTH strategies found, but found {len(found_5x_both)} with 5x BOTH")
        print("   Consider: Lower targets, increase volatility, or run more generations")

    else:
        print("\n❌ No strategies met criteria")
        print("\n   Best Achieved:")
        print(f"     Nominal: {all_time_best_nominal.nominal_multiple:.2f}x")
        print(f"     vs HODL: {all_time_best_vs_hodl.vs_hodl_multiple:.2f}x")
        print("\n   Suggestions:")
        print(f"     • Increase volatility multiplier (currently {volatility_multiplier}x)")
        print("     • Lower confidence thresholds more")
        print("     • Increase population size")
        print("     • Run more generations")

    print(f"\n{'='*90}\n")


async def main():
    parser = argparse.ArgumentParser(description="Hunt for 10x nominal + 10x HODL strategies")
    parser.add_argument("--symbol", default="BTC-USDC", help="Trading symbol")
    parser.add_argument("--test-days", type=int, default=180, help="Test period in days")
    parser.add_argument("--target-count", type=int, default=10, help="Number of 10x strategies to find")
    parser.add_argument("--population", type=int, default=30, help="Population size")
    parser.add_argument("--generations", type=int, default=100, help="Max generations")
    parser.add_argument("--volatility", type=float, default=1.5, help="Volatility multiplier")

    args = parser.parse_args()

    await hunt_10x_strategies(
        symbol=args.symbol,
        test_days=args.test_days,
        target_count=args.target_count,
        population_size=args.population,
        max_generations=args.generations,
        volatility_multiplier=args.volatility
    )


if __name__ == "__main__":
    asyncio.run(main())
