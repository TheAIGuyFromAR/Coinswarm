"""
Strategy Learning Agent

Analyzes successful trades to discover and evolve new strategies.

Evolutionary approach:
- Successful strategies get BIGGER + weight
- Unsuccessful strategies get BIGGER - weight (killed off faster)
- Only best strategies survive
- New strategies created by combining successful patterns
- Test new strategies in sandbox first

This is the "memory improver" that invents new strategies.
"""

import logging
import random
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime

from coinswarm.data_ingest.base import DataPoint
from coinswarm.agents.base_agent import BaseAgent, AgentVote


logger = logging.getLogger(__name__)


@dataclass
class Strategy:
    """A trading strategy pattern"""
    id: str
    name: str
    pattern: Dict  # Strategy parameters
    weight: float  # Current weight (+ for good, - for bad)
    win_rate: float
    avg_pnl: float
    trade_count: int
    created_at: datetime
    parent_strategies: List[str]  # Strategies this was derived from
    sandbox_tested: bool = False
    production_ready: bool = False


class StrategyLearningAgent(BaseAgent):
    """
    Strategy learning and evolution agent.

    Process:
    1. Analyze successful trades to extract patterns
    2. Weight strategies: winners get +, losers get BIGGER -
    3. Cull weak strategies (negative weight below threshold)
    4. Breed new strategies from successful parents
    5. Test new strategies in sandbox
    6. Promote to production if successful

    This creates an evolving strategy pool that improves over time.
    """

    def __init__(
        self,
        name: str = "StrategyLearner",
        weight: float = 0.0,  # Doesn't vote on trades
        cull_threshold: float = -0.5,  # Kill strategies below this weight
        mutation_rate: float = 0.1,  # Probability of random mutation
        sandbox_min_trades: int = 10  # Minimum trades in sandbox before production
    ):
        super().__init__(name, weight)

        self.cull_threshold = cull_threshold
        self.mutation_rate = mutation_rate
        self.sandbox_min_trades = sandbox_min_trades

        # Strategy pool
        self.strategies: Dict[str, Strategy] = {}

        # Initialize with base strategies
        self._initialize_base_strategies()

    def _initialize_base_strategies(self):
        """Initialize with known good strategies"""

        base_strategies = [
            Strategy(
                id="trend_uptrend",
                name="Trend Following (Uptrend)",
                pattern={
                    "type": "trend",
                    "direction": "up",
                    "momentum_threshold": 0.02,
                    "rsi_max": 70
                },
                weight=1.0,  # Neutral starting weight
                win_rate=0.5,
                avg_pnl=0.0,
                trade_count=0,
                created_at=datetime.now(),
                parent_strategies=[],
                sandbox_tested=True,  # Base strategies skip sandbox
                production_ready=True
            ),
            Strategy(
                id="mean_reversion_oversold",
                name="Mean Reversion (Oversold)",
                pattern={
                    "type": "mean_reversion",
                    "condition": "oversold",
                    "rsi_min": 30,
                    "deviation_threshold": -2.0
                },
                weight=1.0,
                win_rate=0.5,
                avg_pnl=0.0,
                trade_count=0,
                created_at=datetime.now(),
                parent_strategies=[],
                sandbox_tested=True,
                production_ready=True
            ),
            Strategy(
                id="news_positive",
                name="News Sentiment (Positive)",
                pattern={
                    "type": "news",
                    "sentiment": "positive",
                    "confidence_threshold": 0.7
                },
                weight=1.0,
                win_rate=0.5,
                avg_pnl=0.0,
                trade_count=0,
                created_at=datetime.now(),
                parent_strategies=[],
                sandbox_tested=True,
                production_ready=True
            ),
        ]

        for strategy in base_strategies:
            self.strategies[strategy.id] = strategy

        logger.info(f"Initialized {len(base_strategies)} base strategies")

    async def analyze(
        self,
        tick: DataPoint,
        position: Optional[Dict],
        market_context: Dict
    ) -> AgentVote:
        """
        Strategy learner doesn't vote on new trades.
        Returns neutral HOLD vote.
        """
        return AgentVote(
            agent_name=self.name,
            action="HOLD",
            confidence=0.5,
            size=0.0,
            reason="Strategy learner does not vote on new trades"
        )

    def update_strategy_weights(self, strategy_weights: Dict[str, float]):
        """
        Update strategy weights from trade analysis.

        Key logic:
        - Successful strategies (win_rate > 50%): +weight * 1.5
        - Unsuccessful strategies (win_rate < 50%): -weight * 2.0 (BIGGER penalty)

        This causes bad strategies to die off FASTER than good ones grow.
        """

        for strategy_id, new_weight in strategy_weights.items():
            if strategy_id not in self.strategies:
                continue

            strategy = self.strategies[strategy_id]

            # Apply weight update
            if new_weight > 0:
                # Successful strategy: moderate reward
                strategy.weight += new_weight * 1.5
            else:
                # Unsuccessful strategy: BIGGER penalty
                strategy.weight += new_weight * 2.0

            logger.debug(
                f"Strategy {strategy_id}: weight={strategy.weight:.2f}, "
                f"win_rate={strategy.win_rate:.2%}"
            )

        # Cull weak strategies
        self._cull_weak_strategies()

        # Evolve new strategies
        self._evolve_new_strategies()

    def _cull_weak_strategies(self):
        """
        Remove strategies with weight below threshold.

        Only best strategies survive!
        """

        to_remove = []

        for strategy_id, strategy in self.strategies.items():
            if strategy.weight < self.cull_threshold:
                logger.warning(
                    f"Culling strategy {strategy_id}: "
                    f"weight={strategy.weight:.2f} < {self.cull_threshold:.2f}"
                )
                to_remove.append(strategy_id)

        # Remove culled strategies
        for strategy_id in to_remove:
            del self.strategies[strategy_id]

        if to_remove:
            logger.info(f"Culled {len(to_remove)} weak strategies")

    def _evolve_new_strategies(self):
        """
        Create new strategies by combining successful patterns.

        Genetic algorithm:
        1. Select 2 parent strategies (weighted by success)
        2. Combine their patterns
        3. Apply random mutation
        4. Create new strategy
        5. Mark for sandbox testing
        """

        # Need at least 2 strategies to breed
        production_strategies = [
            s for s in self.strategies.values()
            if s.production_ready and s.weight > 0
        ]

        if len(production_strategies) < 2:
            return

        # Probabilistic breeding (10% chance per evolution cycle)
        if random.random() > 0.1:
            return

        # Select 2 parents (weighted by weight)
        parents = self._select_parents(production_strategies)

        if len(parents) != 2:
            return

        # Breed new strategy
        child = self._breed_strategies(parents[0], parents[1])

        if child:
            self.strategies[child.id] = child
            logger.info(
                f"Evolved new strategy {child.id} from "
                f"{parents[0].id} + {parents[1].id}"
            )

    def _select_parents(self, strategies: List[Strategy]) -> List[Strategy]:
        """
        Select 2 parents for breeding using weighted random selection.

        Higher weight → higher chance of being selected.
        """

        if len(strategies) < 2:
            return []

        # Normalize weights for selection
        total_weight = sum(s.weight for s in strategies)
        if total_weight <= 0:
            return []

        # Weighted random selection
        selected = []
        for _ in range(2):
            rand = random.random() * total_weight
            cumulative = 0.0

            for strategy in strategies:
                cumulative += strategy.weight
                if cumulative >= rand:
                    selected.append(strategy)
                    break

        return selected

    def _breed_strategies(self, parent1: Strategy, parent2: Strategy) -> Optional[Strategy]:
        """
        Breed two strategies to create a child.

        Algorithm:
        1. Combine patterns from both parents
        2. Apply random mutation
        3. Create new strategy ID
        """

        # Generate new strategy ID
        child_id = f"{parent1.id[:10]}_{parent2.id[:10]}_{datetime.now().timestamp()}"

        # Combine patterns (50/50 mix)
        child_pattern = {}

        # Take pattern from parent1
        for key, value in parent1.pattern.items():
            if key in parent2.pattern:
                # Both parents have this parameter
                if isinstance(value, (int, float)):
                    # Average numeric values
                    child_pattern[key] = (value + parent2.pattern[key]) / 2
                else:
                    # Randomly choose for non-numeric
                    child_pattern[key] = random.choice([value, parent2.pattern[key]])
            else:
                child_pattern[key] = value

        # Add unique parameters from parent2
        for key, value in parent2.pattern.items():
            if key not in child_pattern:
                child_pattern[key] = value

        # Apply random mutation
        if random.random() < self.mutation_rate:
            child_pattern = self._mutate_pattern(child_pattern)

        # Create child strategy
        child = Strategy(
            id=child_id,
            name=f"Evolved: {parent1.name} × {parent2.name}",
            pattern=child_pattern,
            weight=0.0,  # Start neutral
            win_rate=0.5,
            avg_pnl=0.0,
            trade_count=0,
            created_at=datetime.now(),
            parent_strategies=[parent1.id, parent2.id],
            sandbox_tested=False,  # Must test in sandbox
            production_ready=False
        )

        return child

    def _mutate_pattern(self, pattern: Dict) -> Dict:
        """
        Apply random mutation to strategy pattern.

        Mutations:
        - Adjust numeric thresholds by ±10%
        - Randomly flip boolean values
        """

        mutated = pattern.copy()

        for key, value in mutated.items():
            if isinstance(value, float):
                # Adjust by ±10%
                mutated[key] = value * random.uniform(0.9, 1.1)
            elif isinstance(value, int):
                # Adjust by ±1
                mutated[key] = value + random.randint(-1, 1)
            elif isinstance(value, bool):
                # 20% chance to flip
                if random.random() < 0.2:
                    mutated[key] = not value

        return mutated

    def mark_sandbox_tested(self, strategy_id: str, success: bool):
        """
        Mark strategy as sandbox tested.

        If successful, promote to production.
        Otherwise, cull immediately.
        """

        if strategy_id not in self.strategies:
            return

        strategy = self.strategies[strategy_id]
        strategy.sandbox_tested = True

        if success:
            strategy.production_ready = True
            logger.info(f"Strategy {strategy_id} promoted to production")
        else:
            # Failed sandbox, cull immediately
            logger.warning(f"Strategy {strategy_id} failed sandbox, culling")
            del self.strategies[strategy_id]

    def get_production_strategies(self) -> List[Strategy]:
        """Get all production-ready strategies"""
        return [
            s for s in self.strategies.values()
            if s.production_ready
        ]

    def get_sandbox_strategies(self) -> List[Strategy]:
        """Get strategies awaiting sandbox testing"""
        return [
            s for s in self.strategies.values()
            if not s.sandbox_tested
        ]

    def get_strategy_summary(self) -> Dict:
        """Get summary of strategy pool"""

        production = self.get_production_strategies()
        sandbox = self.get_sandbox_strategies()

        return {
            "total_strategies": len(self.strategies),
            "production_strategies": len(production),
            "sandbox_strategies": len(sandbox),
            "best_strategy": max(production, key=lambda s: s.weight).id if production else None,
            "worst_strategy": min(production, key=lambda s: s.weight).id if production else None,
            "avg_weight": sum(s.weight for s in production) / len(production) if production else 0.0
        }
