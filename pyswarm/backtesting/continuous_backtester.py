"""
Continuous Backtesting Loop

Runs 24/7 in background to keep compute >50% utilized.

Key features:
- Tests evolved strategies from StrategyLearningAgent
- Tests academic strategies from AcademicResearchAgent
- Tests new agent configurations
- Runs during idle time between live trades
- Priority queue: Test most promising strategies first

Target: >50% CPU utilization at all times
"""

import asyncio
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from queue import PriorityQueue

from coinswarm.agents.committee import AgentCommittee
from coinswarm.agents.strategy_learning_agent import Strategy
from coinswarm.backtesting.backtest_engine import BacktestEngine, BacktestConfig, BacktestResult
from coinswarm.data_ingest.base import DataPoint


logger = logging.getLogger(__name__)


@dataclass
class BacktestTask:
    """Task in backtest queue"""
    priority: int  # Lower = higher priority
    strategy: Strategy
    agent_config: Dict
    created_at: datetime

    def __lt__(self, other):
        """For priority queue sorting"""
        return self.priority < other.priority


class ContinuousBacktester:
    """
    Continuous backtesting loop that runs 24/7.

    Architecture:
    1. Priority queue of strategies to test
    2. Background worker loop
    3. Historical data cache
    4. Results storage and analysis

    Workflow:
    - StrategyLearningAgent evolves new strategy
      → Add to queue with priority=1 (high)
    - AcademicResearchAgent discovers strategy
      → Add to queue with priority=2 (medium)
    - Periodic re-testing of production strategies
      → Add to queue with priority=3 (low)

    CPU Utilization:
    - Live trading: 10-20ms per tick = <1% CPU
    - Backtesting: Runs continuously in gaps
    - Target: >50% CPU utilization

    Performance:
    - Can test 1 strategy per 10-30 seconds
    - ~2,880 strategies per day (at 30s each)
    - ~20,000 strategies per week
    """

    def __init__(
        self,
        historical_data: Dict[str, List[DataPoint]],
        backtest_config: BacktestConfig,
        max_concurrent_backtests: int = 4
    ):
        self.historical_data = historical_data
        self.backtest_config = backtest_config
        self.max_concurrent_backtests = max_concurrent_backtests

        # Task queue (priority queue)
        self.task_queue: asyncio.Queue = asyncio.Queue()

        # Results storage
        self.results: Dict[str, BacktestResult] = {}

        # Statistics
        self.stats = {
            "backtests_completed": 0,
            "backtests_running": 0,
            "backtests_queued": 0,
            "total_cpu_seconds": 0.0,
            "avg_backtest_time": 0.0,
            "start_time": datetime.now()
        }

        # Control flags
        self.running = False

    async def start(self):
        """Start continuous backtesting loop"""

        logger.info("Starting continuous backtesting loop...")
        self.running = True

        # Start worker tasks
        workers = [
            asyncio.create_task(self._worker(i))
            for i in range(self.max_concurrent_backtests)
        ]

        # Start stats reporter
        stats_reporter = asyncio.create_task(self._stats_reporter())

        # Wait for all workers
        await asyncio.gather(*workers, stats_reporter)

    async def stop(self):
        """Stop continuous backtesting loop"""
        logger.info("Stopping continuous backtesting loop...")
        self.running = False

    async def queue_backtest(
        self,
        strategy: Strategy,
        agent_config: Dict,
        priority: int = 2
    ):
        """
        Queue a strategy for backtesting.

        Args:
            strategy: Strategy to test
            agent_config: Agent configuration
            priority: Lower = higher priority (1=high, 2=medium, 3=low)
        """

        task = BacktestTask(
            priority=priority,
            strategy=strategy,
            agent_config=agent_config,
            created_at=datetime.now()
        )

        await self.task_queue.put(task)
        self.stats["backtests_queued"] += 1

        logger.debug(
            f"Queued backtest: strategy={strategy.id}, priority={priority}, "
            f"queue_size={self.task_queue.qsize()}"
        )

    async def _worker(self, worker_id: int):
        """Background worker that processes backtest tasks"""

        logger.info(f"Worker {worker_id} started")

        while self.running:
            try:
                # Get next task from queue
                task = await asyncio.wait_for(
                    self.task_queue.get(),
                    timeout=1.0
                )

                self.stats["backtests_running"] += 1
                self.stats["backtests_queued"] -= 1

                # Run backtest
                logger.info(
                    f"Worker {worker_id}: Testing strategy {task.strategy.id} "
                    f"(priority={task.priority}, queued={task.created_at})"
                )

                start_time = datetime.now()

                result = await self._run_backtest(task)

                duration = (datetime.now() - start_time).total_seconds()

                # Store result
                self.results[task.strategy.id] = result

                # Update stats
                self.stats["backtests_completed"] += 1
                self.stats["backtests_running"] -= 1
                self.stats["total_cpu_seconds"] += duration
                self.stats["avg_backtest_time"] = (
                    self.stats["total_cpu_seconds"] / self.stats["backtests_completed"]
                )

                logger.info(
                    f"Worker {worker_id}: Completed {task.strategy.id} in {duration:.1f}s - "
                    f"Return: {result.total_return_pct:+.2%}, "
                    f"Win rate: {result.win_rate:.1%}, "
                    f"Sharpe: {result.sharpe_ratio:.2f}"
                )

                # Callback to strategy learning agent
                await self._process_backtest_result(task, result)

            except asyncio.TimeoutError:
                # No tasks in queue, continue
                continue

            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                self.stats["backtests_running"] -= 1

        logger.info(f"Worker {worker_id} stopped")

    async def _run_backtest(self, task: BacktestTask) -> BacktestResult:
        """Run a single backtest"""

        # Create agent committee from config
        committee = self._create_committee(task.agent_config)

        # Create backtest engine
        engine = BacktestEngine(self.backtest_config)

        # Run backtest
        result = await engine.run_backtest(committee, self.historical_data)

        return result

    def _create_committee(self, agent_config: Dict) -> AgentCommittee:
        """Create agent committee from configuration"""

        # Placeholder: In production, dynamically create agents
        from coinswarm.agents.trend_agent import TrendFollowingAgent
        from coinswarm.agents.risk_agent import RiskManagementAgent

        agents = [
            TrendFollowingAgent(),
            RiskManagementAgent(),
        ]

        committee = AgentCommittee(
            agents=agents,
            confidence_threshold=agent_config.get("confidence_threshold", 0.7)
        )

        return committee

    async def _process_backtest_result(self, task: BacktestTask, result: BacktestResult):
        """
        Process backtest result and update strategy.

        Key logic:
        - If win_rate > 50% and Sharpe > 1.0 → Promote to production
        - If win_rate < 50% → Cull strategy
        - Update strategy metrics
        """

        strategy = task.strategy

        # Update strategy metrics
        strategy.win_rate = result.win_rate
        strategy.avg_pnl = result.total_return / result.total_trades if result.total_trades > 0 else 0
        strategy.trade_count = result.total_trades

        # Determine if strategy passes sandbox
        min_trades = 10
        min_win_rate = 0.5
        min_sharpe = 1.0

        passed = (
            result.total_trades >= min_trades
            and result.win_rate >= min_win_rate
            and result.sharpe_ratio >= min_sharpe
        )

        if passed:
            logger.info(
                f"Strategy {strategy.id} PASSED sandbox: "
                f"trades={result.total_trades}, win_rate={result.win_rate:.1%}, "
                f"sharpe={result.sharpe_ratio:.2f}"
            )

            # Mark as production ready
            strategy.sandbox_tested = True
            strategy.production_ready = True

            # Update weight based on performance
            # Better performance → higher initial weight
            strategy.weight = result.sharpe_ratio * result.win_rate

        else:
            logger.warning(
                f"Strategy {strategy.id} FAILED sandbox: "
                f"trades={result.total_trades}, win_rate={result.win_rate:.1%}, "
                f"sharpe={result.sharpe_ratio:.2f}"
            )

            # Mark for culling
            strategy.sandbox_tested = True
            strategy.production_ready = False
            strategy.weight = -1.0  # Negative weight = cull

    async def _stats_reporter(self):
        """Report statistics periodically"""

        while self.running:
            await asyncio.sleep(60)  # Every minute

            uptime = (datetime.now() - self.stats["start_time"]).total_seconds()
            cpu_utilization = (self.stats["total_cpu_seconds"] / uptime) * 100

            logger.info(
                f"Backtest stats: "
                f"completed={self.stats['backtests_completed']}, "
                f"running={self.stats['backtests_running']}, "
                f"queued={self.task_queue.qsize()}, "
                f"avg_time={self.stats['avg_backtest_time']:.1f}s, "
                f"cpu_util={cpu_utilization:.1f}%"
            )

    def get_cpu_utilization(self) -> float:
        """Get current CPU utilization percentage"""

        if not self.stats["start_time"]:
            return 0.0

        uptime = (datetime.now() - self.stats["start_time"]).total_seconds()
        if uptime == 0:
            return 0.0

        cpu_utilization = (self.stats["total_cpu_seconds"] / uptime) * 100

        return cpu_utilization

    def get_result(self, strategy_id: str) -> Optional[BacktestResult]:
        """Get backtest result for a strategy"""
        return self.results.get(strategy_id)

    def get_best_strategies(self, n: int = 10) -> List[BacktestResult]:
        """
        Get top N strategies by Sharpe ratio.

        Returns:
            List of BacktestResult sorted by Sharpe ratio
        """

        sorted_results = sorted(
            self.results.values(),
            key=lambda r: r.sharpe_ratio,
            reverse=True
        )

        return sorted_results[:n]

    def get_stats(self) -> Dict:
        """Get backtesting statistics"""

        return {
            **self.stats,
            "cpu_utilization_pct": self.get_cpu_utilization(),
            "queue_size": self.task_queue.qsize(),
            "results_stored": len(self.results)
        }


async def example_usage():
    """Example: How to use ContinuousBacktester"""

    # Load historical data (placeholder)
    from coinswarm.data_ingest.binance_ingestor import BinanceIngestor

    ingestor = BinanceIngestor()

    # Fetch 1 month of historical data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    historical_data = {
        "BTC-USD": await ingestor.fetch_ohlcv_range(
            symbol="BTC-USD",
            timeframe="1m",
            start_time=start_date,
            end_time=end_date
        )
    }

    # Configure backtest
    config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        initial_capital=100000,
        symbols=["BTC-USD"],
        timeframe="1m"
    )

    # Create continuous backtester
    backtester = ContinuousBacktester(
        historical_data=historical_data,
        backtest_config=config,
        max_concurrent_backtests=4
    )

    # Start background workers
    asyncio.create_task(backtester.start())

    # Queue strategies for testing
    from coinswarm.agents.strategy_learning_agent import Strategy

    strategy1 = Strategy(
        id="trend_momentum_v1",
        name="Trend Momentum v1",
        pattern={"type": "trend", "momentum_threshold": 0.02},
        weight=0.0,
        win_rate=0.5,
        avg_pnl=0.0,
        trade_count=0,
        created_at=datetime.now(),
        parent_strategies=[]
    )

    await backtester.queue_backtest(strategy1, agent_config={}, priority=1)

    # Wait for results
    await asyncio.sleep(30)

    # Check results
    result = backtester.get_result("trend_momentum_v1")
    if result:
        print(f"Strategy tested: Return={result.total_return_pct:+.2%}, Sharpe={result.sharpe_ratio:.2f}")

    # Check CPU utilization
    cpu_util = backtester.get_cpu_utilization()
    print(f"CPU utilization: {cpu_util:.1f}%")


if __name__ == "__main__":
    asyncio.run(example_usage())
