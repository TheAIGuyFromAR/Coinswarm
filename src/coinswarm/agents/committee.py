"""
Agent Committee - Swarm Intelligence for Trading

The committee manages a swarm of specialized trading agents:
- Each agent votes independently
- Votes are aggregated using weighted confidence
- Veto system prevents dangerous trades
- Dynamic weight adjustment based on performance

This is the core of the 17000% return strategy:
Multiple specialized agents working together are better than any single agent.
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

from coinswarm.data_ingest.base import DataPoint
from coinswarm.agents.base_agent import BaseAgent, AgentVote


logger = logging.getLogger(__name__)


@dataclass
class CommitteeDecision:
    """Final decision from agent committee"""
    action: str  # "BUY", "SELL", "HOLD"
    confidence: float  # 0.0-1.0 (aggregated from all agents)
    size: float  # Position size
    price: Optional[float] = None
    reason: str = ""  # Summary of all agent votes
    votes: List[AgentVote] = None  # Individual agent votes
    vetoed: bool = False  # If any agent vetoed


class AgentCommittee:
    """
    Committee of trading agents using swarm intelligence.

    Architecture:
    - Multiple specialized agents (trend, mean reversion, arbitrage, etc.)
    - Each agent analyzes independently
    - Votes aggregated using weighted confidence
    - Veto system for risk management
    - Dynamic weight adjustment based on performance

    This is inspired by the 17000% return swarm in tradfi.
    """

    def __init__(self, agents: List[BaseAgent], confidence_threshold: float = 0.7):
        """
        Initialize committee.

        Args:
            agents: List of trading agents
            confidence_threshold: Minimum confidence to execute trade
        """
        self.agents = agents
        self.confidence_threshold = confidence_threshold

        self.stats = {
            "decisions_made": 0,
            "trades_executed": 0,
            "trades_vetoed": 0,
            "profitable_trades": 0,
            "losing_trades": 0
        }

        logger.info(
            f"Committee initialized with {len(agents)} agents: "
            f"{[a.name for a in agents]}"
        )

    async def vote(
        self,
        tick: DataPoint,
        position: Optional[Dict] = None,
        market_context: Optional[Dict] = None
    ) -> CommitteeDecision:
        """
        Get votes from all agents and aggregate into final decision.

        Process:
        1. Each agent analyzes independently
        2. Collect all votes
        3. Check for vetoes (instant HOLD)
        4. Aggregate votes using weighted confidence
        5. Return decision if confidence > threshold

        Args:
            tick: Latest market tick
            position: Current position
            market_context: Additional market data

        Returns:
            CommitteeDecision with action, confidence, size
        """

        self.stats["decisions_made"] += 1

        # Collect votes from all agents
        votes: List[AgentVote] = []

        for agent in self.agents:
            try:
                vote = await agent.analyze(tick, position, market_context or {})
                votes.append(vote)

                # Update agent stats
                agent.stats["votes_cast"] += 1

                logger.debug(
                    f"{agent.name} voted: {vote.action} "
                    f"(confidence={vote.confidence:.2f}, size={vote.size})"
                )

            except Exception as e:
                logger.error(f"Error getting vote from {agent.name}: {e}")

        # Check for vetoes
        vetoed_by = [v.agent_name for v in votes if v.veto]
        if vetoed_by:
            logger.warning(f"Trade vetoed by: {', '.join(vetoed_by)}")
            self.stats["trades_vetoed"] += 1

            for agent in self.agents:
                if agent.name in vetoed_by:
                    agent.stats["vetoes_issued"] += 1

            return CommitteeDecision(
                action="HOLD",
                confidence=0.0,
                size=0.0,
                reason=f"Vetoed by {', '.join(vetoed_by)}",
                votes=votes,
                vetoed=True
            )

        # Aggregate votes
        decision = self._aggregate_votes(votes, tick)

        # Log decision
        if decision.confidence >= self.confidence_threshold:
            logger.info(
                f"Committee decision: {decision.action} {decision.size} "
                f"{tick.symbol} @ {decision.price} "
                f"(confidence={decision.confidence:.2%})"
            )
            self.stats["trades_executed"] += 1
        else:
            logger.debug(
                f"Committee decision: HOLD "
                f"(confidence={decision.confidence:.2%} < {self.confidence_threshold:.2%})"
            )

        return decision

    def _aggregate_votes(self, votes: List[AgentVote], tick: DataPoint) -> CommitteeDecision:
        """
        Aggregate agent votes using weighted confidence.

        Algorithm:
        1. Group votes by action (BUY, SELL, HOLD)
        2. Calculate weighted confidence for each action
        3. Choose action with highest weighted confidence
        4. Calculate position size (average of votes for that action)
        5. Generate summary reason

        Returns:
            CommitteeDecision with aggregated action, confidence, size
        """

        if not votes:
            return CommitteeDecision(
                action="HOLD",
                confidence=0.0,
                size=0.0,
                reason="No votes received",
                votes=[]
            )

        # Group votes by action
        buy_votes = [v for v in votes if v.action == "BUY"]
        sell_votes = [v for v in votes if v.action == "SELL"]
        hold_votes = [v for v in votes if v.action == "HOLD"]

        # Calculate weighted confidence for each action
        def weighted_confidence(action_votes: List[AgentVote]) -> float:
            if not action_votes:
                return 0.0

            # Sum of (agent_weight × confidence)
            weighted_sum = sum(
                self._get_agent_weight(v.agent_name) * v.confidence
                for v in action_votes
            )

            # Normalize by total weight
            total_weight = sum(self._get_agent_weight(v.agent_name) for v in action_votes)

            return weighted_sum / total_weight if total_weight > 0 else 0.0

        buy_confidence = weighted_confidence(buy_votes)
        sell_confidence = weighted_confidence(sell_votes)
        hold_confidence = weighted_confidence(hold_votes)

        # Choose action with highest confidence
        max_confidence = max(buy_confidence, sell_confidence, hold_confidence)

        if max_confidence == buy_confidence and buy_votes:
            action = "BUY"
            action_votes = buy_votes
            confidence = buy_confidence
        elif max_confidence == sell_confidence and sell_votes:
            action = "SELL"
            action_votes = sell_votes
            confidence = sell_confidence
        else:
            action = "HOLD"
            action_votes = hold_votes
            confidence = hold_confidence

        # Calculate position size (average of votes for chosen action)
        size = sum(v.size for v in action_votes) / len(action_votes) if action_votes else 0.0

        # Generate summary reason
        reason_parts = [
            f"{v.agent_name}({v.confidence:.0%}): {v.reason}"
            for v in action_votes[:3]  # Top 3 reasons
        ]
        reason = " | ".join(reason_parts)

        return CommitteeDecision(
            action=action,
            confidence=confidence,
            size=size,
            price=tick.data.get("price"),
            reason=reason,
            votes=votes,
            vetoed=False
        )

    def _get_agent_weight(self, agent_name: str) -> float:
        """Get agent weight by name"""
        for agent in self.agents:
            if agent.name == agent_name:
                return agent.weight
        return 1.0  # Default weight

    def update_weights_by_performance(self):
        """
        Dynamically adjust agent weights based on performance.

        Agents with higher accuracy get more voting power.
        This creates a self-optimizing swarm.
        """

        for agent in self.agents:
            # Adjust weight based on accuracy
            # High accuracy = higher weight
            # Low accuracy = lower weight (but never 0)

            accuracy = agent.accuracy

            if accuracy > 0.6:
                # Good performance, increase weight
                agent.weight = min(2.0, agent.weight * 1.1)
            elif accuracy < 0.4:
                # Poor performance, decrease weight
                agent.weight = max(0.3, agent.weight * 0.9)

            logger.debug(
                f"Agent {agent.name}: accuracy={accuracy:.2%}, weight={agent.weight:.2f}"
            )

    def update_trade_result(self, trade: Dict, profitable: bool):
        """
        Update all agents with trade result.

        This allows agents to learn from outcomes and adjust weights.
        """

        if profitable:
            self.stats["profitable_trades"] += 1
        else:
            self.stats["losing_trades"] += 1

        # Update each agent that voted for this trade
        for agent in self.agents:
            agent.update_performance({"profitable": profitable})

        # Adjust weights based on performance
        self.update_weights_by_performance()

    @property
    def win_rate(self) -> float:
        """Calculate overall win rate"""
        total = self.stats["profitable_trades"] + self.stats["losing_trades"]
        if total == 0:
            return 0.5
        return self.stats["profitable_trades"] / total

    def get_stats(self) -> Dict:
        """Get committee statistics"""
        return {
            "decisions_made": self.stats["decisions_made"],
            "trades_executed": self.stats["trades_executed"],
            "trades_vetoed": self.stats["trades_vetoed"],
            "win_rate": self.win_rate,
            "agents": [
                {
                    "name": agent.name,
                    "weight": agent.weight,
                    "accuracy": agent.accuracy,
                    "votes_cast": agent.stats["votes_cast"],
                    "vetoes_issued": agent.stats["vetoes_issued"]
                }
                for agent in self.agents
            ]
        }

    def __repr__(self):
        return (
            f"AgentCommittee({len(self.agents)} agents, "
            f"win_rate={self.win_rate:.2%}, "
            f"threshold={self.confidence_threshold:.2%})"
        )
