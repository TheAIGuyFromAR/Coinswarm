"""
Base Agent for Trading Swarm

Each agent in the swarm:
- Specializes in a specific strategy (trend, mean reversion, arbitrage, etc.)
- Analyzes market data independently
- Votes with confidence score
- Can veto dangerous trades

Swarm intelligence: Multiple specialized agents vote on each trade.
Committee aggregates votes using weighted confidence.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from coinswarm.data_ingest.base import DataPoint


@dataclass
class AgentVote:
    """Vote from an agent"""
    agent_name: str
    action: str  # "BUY", "SELL", "HOLD"
    confidence: float  # 0.0-1.0
    size: float  # Suggested position size
    reason: str  # Explanation for vote
    veto: bool = False  # Agent can veto trade (e.g., risk too high)


class BaseAgent(ABC):
    """
    Base class for all trading agents in the swarm.

    Each agent:
    1. Receives market data
    2. Analyzes using its specific strategy
    3. Returns a vote with confidence
    4. Can veto dangerous trades
    """

    def __init__(self, name: str, weight: float = 1.0):
        """
        Initialize agent.

        Args:
            name: Agent identifier
            weight: Voting weight (higher = more influence)
        """
        self.name = name
        self.weight = weight
        self.stats = {
            "votes_cast": 0,
            "vetoes_issued": 0,
            "correct_predictions": 0,
            "incorrect_predictions": 0
        }

    @abstractmethod
    async def analyze(
        self,
        tick: DataPoint,
        position: dict | None,
        market_context: dict
    ) -> AgentVote:
        """
        Analyze market data and return vote.

        Args:
            tick: Latest market tick
            position: Current position (if any)
            market_context: Additional market data (orderbook, candles, etc.)

        Returns:
            AgentVote with action, confidence, size, reason
        """
        pass

    def update_performance(self, trade_result: dict):
        """
        Update agent performance stats.

        Called after trade completes to track accuracy.
        """
        if trade_result.get("profitable"):
            self.stats["correct_predictions"] += 1
        else:
            self.stats["incorrect_predictions"] += 1

    @property
    def accuracy(self) -> float:
        """Calculate agent accuracy"""
        total = self.stats["correct_predictions"] + self.stats["incorrect_predictions"]
        if total == 0:
            return 0.5  # Neutral before any trades
        return self.stats["correct_predictions"] / total

    def __repr__(self):
        return f"{self.name}(weight={self.weight}, accuracy={self.accuracy:.2%})"
