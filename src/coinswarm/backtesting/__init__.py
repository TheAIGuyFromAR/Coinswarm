"""
Backtesting Module

Continuous backtesting system that runs 24/7 to keep compute >50% utilized.

Features:
- Fast historical data replay (>1000x real-time)
- Realistic order execution (slippage, fees)
- Performance metrics (Sharpe, Sortino, Calmar, max drawdown)
- Continuous background testing
- Priority queue for strategy testing
- Automatic sandbox validation

Usage:
- Test evolved strategies from StrategyLearningAgent
- Test academic strategies from AcademicResearchAgent
- Validate new agent configurations
- Run during idle time between live trades
"""

from coinswarm.backtesting.backtest_engine import (
    BacktestEngine,
    BacktestConfig,
    BacktestTrade,
    BacktestResult
)
from coinswarm.backtesting.continuous_backtester import (
    ContinuousBacktester,
    BacktestTask
)

__all__ = [
    "BacktestEngine",
    "BacktestConfig",
    "BacktestTrade",
    "BacktestResult",
    "ContinuousBacktester",
    "BacktestTask",
]
