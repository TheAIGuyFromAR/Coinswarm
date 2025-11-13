#!/usr/bin/env python3
"""
Automated 10x Strategy Discovery

Continuously searches for trading strategies that beat HODL by 10x over 6 months.

Approach:
1. Test random strategy configurations
2. Calculate HODL baseline for each period
3. Compare strategy performance vs HODL
4. Use genetic algorithms to evolve winning strategies
5. Save and display best performers
6. Run continuously until 10x strategies are found

Target: Find strategies with 5-10x HODL returns over 6 months
Success Criteria: Sharpe >2.0, Max DD <25%, Win Rate >55%

Usage:
    python discover_10x_strategies.py
    python discover_10x_strategies.py --symbol BTC-USDC --test-period 180
    python discover_10x_strategies.py --generations 100 --population 50
"""

import argparse
import asyncio
import json
import logging
import random
import statistics
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta

from coinswarm.agents.arbitrage_agent import ArbitrageAgent
from coinswarm.agents.committee import AgentCommittee
from coinswarm.agents.risk_agent import RiskManagementAgent
from coinswarm.agents.trend_agent import TrendFollowingAgent
from coinswarm.backtesting.backtest_engine import BacktestConfig, BacktestEngine
from coinswarm.data_ingest.base import DataPoint

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class StrategyConfig:
    """Configuration for a trading strategy"""
    trend_weight: float
    risk_weight: float
    arbitrage_weight: float
    confidence_threshold: float

    def mutate(self, mutation_rate: float = 0.2) -> 'StrategyConfig':
        """Create a mutated copy of this configuration"""
        return StrategyConfig(
            trend_weight=max(0.1, self.trend_weight * random.uniform(1-mutation_rate, 1+mutation_rate)),
            risk_weight=max(0.1, self.risk_weight * random.uniform(1-mutation_rate, 1+mutation_rate)),
            arbitrage_weight=max(0.1, self.arbitrage_weight * random.uniform(1-mutation_rate, 1+mutation_rate)),
            confidence_threshold=max(0.1, min(0.95, self.confidence_threshold + random.uniform(-0.1, 0.1)))
        )

    @staticmethod
    def crossover(parent1: 'StrategyConfig', parent2: 'StrategyConfig') -> 'StrategyConfig':
        """Create a child configuration by combining two parents"""
        return StrategyConfig(
            trend_weight=(parent1.trend_weight + parent2.trend_weight) / 2,
            risk_weight=(parent1.risk_weight + parent2.risk_weight) / 2,
            arbitrage_weight=(parent1.arbitrage_weight + parent2.arbitrage_weight) / 2,
            confidence_threshold=(parent1.confidence_threshold + parent2.confidence_threshold) / 2
        )


@dataclass
class StrategyResult:
    """Result of a strategy backtest"""
    config: StrategyConfig
    return_pct: float
    hodl_return_pct: float
    vs_hodl_multiple: float  # How many times better than HODL
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    win_rate: float
    total_trades: int
    profit_factor: float
    start_date: datetime
    market_regime: str

    def is_10x_strategy(self) -> bool:
        """Check if this beats HODL by 10x"""
        return (
            self.vs_hodl_multiple >= 10.0 and
            self.sharpe_ratio >= 2.0 and
            self.max_drawdown_pct <= 25.0 and
            self.win_rate >= 0.55
        )

    def is_excellent(self) -> bool:
        """Check if this is an excellent strategy (5x+)"""
        return (
            self.vs_hodl_multiple >= 5.0 and
            self.sharpe_ratio >= 1.5 and
            self.max_drawdown_pct <= 30.0 and
            self.win_rate >= 0.52
        )


def generate_market_data(
    symbol: str,
    start_date: datetime,
    days: int,
    market_regime: str = "random"
) -> tuple[list[DataPoint], float]:
    """
    Generate mock market data and return with HODL return

    Returns:
        (data_points, hodl_return_pct)
    """
    data_points = []
    current_price = 50000.0 if symbol == "BTC-USDC" else 2500.0
    initial_price = current_price
    current_time = start_date

    # Set parameters based on market regime
    if market_regime == "bull":
        drift = 0.003  # 0.3% daily upward drift
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
    else:  # random
        drift = random.gauss(0.001, 0.002)
        volatility = random.uniform(0.015, 0.025)

    # Generate hourly candles
    for hour in range(days * 24):
        change_pct = random.gauss(drift / 24, volatility)
        current_price *= (1 + change_pct)

        # Clamp to reasonable range
        if symbol == "BTC-USDC":
            current_price = max(25000, min(80000, current_price))
        else:
            current_price = max(1000, min(5000, current_price))

        # Create OHLCV data
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

    # Calculate HODL return
    final_price = data_points[-1].data["close"]
    hodl_return_pct = (final_price - initial_price) / initial_price

    return data_points, hodl_return_pct


async def test_strategy(
    config: StrategyConfig,
    symbol: str,
    test_days: int,
    market_regime: str = "random"
) -> StrategyResult:
    """Test a strategy configuration and compare to HODL"""

    # Generate random start date
    days_ago = random.randint(test_days + 1, 365)
    start_date = datetime.now() - timedelta(days=days_ago)

    # Generate data and HODL baseline
    price_data, hodl_return = generate_market_data(symbol, start_date, test_days, market_regime)

    # Create agent committee
    agents = [
        TrendFollowingAgent(name="TrendFollower", weight=config.trend_weight),
        RiskManagementAgent(name="RiskManager", weight=config.risk_weight),
        ArbitrageAgent(name="ArbitrageHunter", weight=config.arbitrage_weight),
    ]

    committee = AgentCommittee(
        agents=agents,
        confidence_threshold=config.confidence_threshold
    )

    # Configure backtest
    backtest_config = BacktestConfig(
        start_date=price_data[0].timestamp,
        end_date=price_data[-1].timestamp,
        initial_capital=100000,
        symbols=[symbol],
        timeframe="1h",
        commission=0.001,
        slippage=0.0005
    )

    # Run backtest
    historical_data = {symbol: price_data}
    engine = BacktestEngine(backtest_config)
    result = await engine.run_backtest(committee, historical_data)

    # Calculate vs HODL multiple
    # Handle edge cases where HODL is negative or zero
    if hodl_return > 0:
        vs_hodl = result.total_return_pct / hodl_return
    elif hodl_return < 0 and result.total_return_pct > 0:
        # Strategy is positive when HODL is negative - excellent!
        vs_hodl = abs(result.total_return_pct / hodl_return) + 10.0
    elif hodl_return < 0 and result.total_return_pct < 0:
        # Both negative - how much better?
        vs_hodl = hodl_return / result.total_return_pct if result.total_return_pct != 0 else 0
    else:
        vs_hodl = 0.0

    return StrategyResult(
        config=config,
        return_pct=result.total_return_pct,
        hodl_return_pct=hodl_return,
        vs_hodl_multiple=vs_hodl,
        sharpe_ratio=result.sharpe_ratio,
        sortino_ratio=result.sortino_ratio,
        max_drawdown_pct=result.max_drawdown_pct,
        win_rate=result.win_rate,
        total_trades=result.total_trades,
        profit_factor=result.profit_factor,
        start_date=start_date,
        market_regime=market_regime
    )


async def genetic_algorithm(
    symbol: str,
    test_days: int,
    population_size: int = 20,
    generations: int = 50,
    elite_size: int = 5,
    mutation_rate: float = 0.2
):
    """
    Run genetic algorithm to discover 10x strategies

    Args:
        symbol: Trading symbol
        test_days: Days per backtest window
        population_size: Number of strategies per generation
        generations: Number of generations to evolve
        elite_size: Number of top strategies to keep each generation
        mutation_rate: Probability and magnitude of mutations
    """

    print("\n" + "="*80)
    print("🧬 AUTOMATED 10X STRATEGY DISCOVERY")
    print("="*80 + "\n")

    print("Configuration:")
    print(f"  Symbol: {symbol}")
    print(f"  Test Period: {test_days} days (~{test_days/30:.1f} months)")
    print(f"  Population Size: {population_size}")
    print(f"  Generations: {generations}")
    print(f"  Elite Size: {elite_size}")
    print(f"  Mutation Rate: {mutation_rate:.0%}")
    print("\n🎯 Goal: Find strategies that beat HODL by 10x")
    print("   Success Criteria: Sharpe >2.0, Max DD <25%, Win Rate >55%\n")

    # Initialize random population
    population = [
        StrategyConfig(
            trend_weight=random.uniform(0.5, 5.0),
            risk_weight=random.uniform(0.5, 5.0),
            arbitrage_weight=random.uniform(0.5, 5.0),
            confidence_threshold=random.uniform(0.4, 0.8)
        )
        for _ in range(population_size)
    ]

    # Track best strategies found
    best_10x_strategies: list[StrategyResult] = []
    best_5x_strategies: list[StrategyResult] = []
    all_time_best: StrategyResult = None

    market_regimes = ["random", "bull", "bear", "sideways", "volatile"]

    # Evolution loop
    for generation in range(generations):
        print(f"\n{'='*80}")
        print(f"Generation {generation + 1}/{generations}")
        print(f"{'='*80}")

        # Test all strategies in population
        results: list[StrategyResult] = []

        for i, config in enumerate(population):
            # Test on random regime
            regime = random.choice(market_regimes)
            result = await test_strategy(config, symbol, test_days, regime)
            results.append(result)

            # Track best strategies
            if result.is_10x_strategy():
                best_10x_strategies.append(result)
                print(f"\n🎉 10X STRATEGY FOUND! #{len(best_10x_strategies)}")
                print(f"   Return: {result.return_pct:+.1%} vs HODL: {result.hodl_return_pct:+.1%} ({result.vs_hodl_multiple:.1f}x)")
                print(f"   Sharpe: {result.sharpe_ratio:.2f} | Win Rate: {result.win_rate:.1%} | Max DD: {result.max_drawdown_pct:.1%}")
                print(f"   Config: T={result.config.trend_weight:.2f} R={result.config.risk_weight:.2f} A={result.config.arbitrage_weight:.2f} C={result.config.confidence_threshold:.2f}")
            elif result.is_excellent():
                best_5x_strategies.append(result)
                print(f"\n⭐ Excellent Strategy! (5x+) #{len(best_5x_strategies)}")
                print(f"   Return: {result.return_pct:+.1%} vs HODL: {result.hodl_return_pct:+.1%} ({result.vs_hodl_multiple:.1f}x)")

            # Track all-time best
            if all_time_best is None or result.vs_hodl_multiple > all_time_best.vs_hodl_multiple:
                all_time_best = result
                print(f"\n🏆 New All-Time Best! {result.vs_hodl_multiple:.2f}x HODL")

            # Show progress
            if (i + 1) % 5 == 0:
                print(f"  Tested {i+1}/{population_size} strategies...")

        # Sort by vs_hodl_multiple
        results.sort(key=lambda r: r.vs_hodl_multiple, reverse=True)

        # Display generation summary
        print(f"\n📊 Generation {generation + 1} Summary:")
        print(f"{'='*80}")
        print(f"  Best vs HODL: {results[0].vs_hodl_multiple:.2f}x (Return: {results[0].return_pct:+.1%} vs {results[0].hodl_return_pct:+.1%})")
        print(f"  Avg vs HODL:  {statistics.mean(r.vs_hodl_multiple for r in results):.2f}x")
        print(f"  10x Strategies Found: {len(best_10x_strategies)}")
        print(f"  5x+ Strategies Found: {len(best_5x_strategies)}")

        # Show top 3
        print("\n  Top 3 This Generation:")
        for i, r in enumerate(results[:3]):
            print(f"    {i+1}. {r.vs_hodl_multiple:.2f}x | Return: {r.return_pct:+.1%} | Sharpe: {r.sharpe_ratio:.2f} | "
                  f"Win: {r.win_rate:.0%} | Trades: {r.total_trades}")

        # Check if we found enough 10x strategies
        if len(best_10x_strategies) >= 5:
            print(f"\n🎊 SUCCESS! Found {len(best_10x_strategies)} strategies that beat HODL by 10x!")
            break

        # Selection: Keep elite + breed new generation
        elite = results[:elite_size]

        # Create next generation
        new_population = []

        # Keep elite
        new_population.extend([r.config for r in elite])

        # Breed new strategies
        while len(new_population) < population_size:
            # Select 2 parents from elite (weighted by performance)
            weights = [r.vs_hodl_multiple for r in elite]
            total_weight = sum(weights)

            if total_weight > 0:
                parent1 = random.choices(elite, weights=weights)[0]
                parent2 = random.choices(elite, weights=weights)[0]

                # Crossover
                child = StrategyConfig.crossover(parent1.config, parent2.config)

                # Mutation
                if random.random() < mutation_rate:
                    child = child.mutate(mutation_rate)

                new_population.append(child)
            else:
                # Random strategy if weights are all zero
                new_population.append(StrategyConfig(
                    trend_weight=random.uniform(0.5, 5.0),
                    risk_weight=random.uniform(0.5, 5.0),
                    arbitrage_weight=random.uniform(0.5, 5.0),
                    confidence_threshold=random.uniform(0.4, 0.8)
                ))

        population = new_population

    # Final summary
    print(f"\n\n{'='*80}")
    print("🏁 DISCOVERY COMPLETE")
    print(f"{'='*80}\n")

    print(f"Total Generations: {generation + 1}")
    print(f"Total Tests: {(generation + 1) * population_size}")
    print(f"10x Strategies Found: {len(best_10x_strategies)}")
    print(f"5x+ Strategies Found: {len(best_5x_strategies)}")

    if all_time_best:
        print("\n🏆 All-Time Best Strategy:")
        print(f"{'='*80}")
        print(f"  vs HODL: {all_time_best.vs_hodl_multiple:.2f}x")
        print(f"  Return: {all_time_best.return_pct:+.2%} (HODL: {all_time_best.hodl_return_pct:+.2%})")
        print(f"  Sharpe: {all_time_best.sharpe_ratio:.2f}")
        print(f"  Sortino: {all_time_best.sortino_ratio:.2f}")
        print(f"  Win Rate: {all_time_best.win_rate:.1%}")
        print(f"  Max Drawdown: {all_time_best.max_drawdown_pct:.1%}")
        print(f"  Total Trades: {all_time_best.total_trades}")
        print(f"  Profit Factor: {all_time_best.profit_factor:.2f}")
        print(f"  Market Regime: {all_time_best.market_regime}")
        print("\n  Configuration:")
        print(f"    Trend Weight: {all_time_best.config.trend_weight:.3f}")
        print(f"    Risk Weight: {all_time_best.config.risk_weight:.3f}")
        print(f"    Arbitrage Weight: {all_time_best.config.arbitrage_weight:.3f}")
        print(f"    Confidence Threshold: {all_time_best.config.confidence_threshold:.3f}")

    # Save best strategies
    if best_10x_strategies or best_5x_strategies:
        strategies_to_save = best_10x_strategies[:10] if best_10x_strategies else best_5x_strategies[:10]

        save_data = {
            "discovered_at": datetime.now().isoformat(),
            "symbol": symbol,
            "test_days": test_days,
            "total_tests": (generation + 1) * population_size,
            "strategies": [
                {
                    "rank": i + 1,
                    "vs_hodl_multiple": s.vs_hodl_multiple,
                    "return_pct": s.return_pct,
                    "hodl_return_pct": s.hodl_return_pct,
                    "sharpe_ratio": s.sharpe_ratio,
                    "win_rate": s.win_rate,
                    "max_drawdown_pct": s.max_drawdown_pct,
                    "total_trades": s.total_trades,
                    "market_regime": s.market_regime,
                    "config": asdict(s.config)
                }
                for i, s in enumerate(strategies_to_save)
            ]
        }

        filename = f"discovered_strategies_{symbol.replace('-', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(save_data, f, indent=2)

        print(f"\n💾 Saved top {len(strategies_to_save)} strategies to: {filename}")

    print(f"\n{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(description="Discover 10x HODL strategies through genetic algorithms")
    parser.add_argument("--symbol", default="BTC-USDC", help="Trading symbol")
    parser.add_argument("--test-period", type=int, default=180, help="Test period in days (default: 180 = 6 months)")
    parser.add_argument("--population", type=int, default=20, help="Population size per generation")
    parser.add_argument("--generations", type=int, default=50, help="Number of generations to evolve")
    parser.add_argument("--elite", type=int, default=5, help="Number of elite strategies to keep")
    parser.add_argument("--mutation-rate", type=float, default=0.2, help="Mutation rate (0.0-1.0)")

    args = parser.parse_args()

    asyncio.run(genetic_algorithm(
        symbol=args.symbol,
        test_days=args.test_period,
        population_size=args.population,
        generations=args.generations,
        elite_size=args.elite,
        mutation_rate=args.mutation_rate
    ))


if __name__ == "__main__":
    main()
