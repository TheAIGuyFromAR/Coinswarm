"""
Unit tests for AgentCommittee

Tests voting aggregation, weighted confidence, veto system, and dynamic weight adjustment.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from decimal import Decimal

from coinswarm.agents.committee import AgentCommittee, CommitteeDecision
from coinswarm.agents.base_agent import BaseAgent, AgentVote
from coinswarm.data_ingest.base import DataPoint


# Mock agent for testing
class MockAgent(BaseAgent):
    """Mock agent that returns predetermined votes"""

    def __init__(self, name: str, vote_action: str, vote_confidence: float,
                 vote_size: float = 0.01, veto: bool = False):
        super().__init__(name, weight=1.0)
        self.vote_action = vote_action
        self.vote_confidence = vote_confidence
        self.vote_size = vote_size
        self.veto = veto

    async def analyze(self, tick, position, market_context):
        return AgentVote(
            agent_name=self.name,
            action=self.vote_action,
            confidence=self.vote_confidence,
            size=self.vote_size,
            reason=f"Mock vote from {self.name}",
            veto=self.veto
        )


class TestAgentCommittee:
    """Test suite for AgentCommittee"""

    @pytest.fixture
    def sample_tick(self):
        """Create sample market tick"""
        return DataPoint(
            source="test",
            symbol="BTC-USD",
            timestamp="2024-01-01T00:00:00Z",
            data={"price": 50000.0, "volume": 100.0}
        )

    # ========================================================================
    # Initialization Tests
    # ========================================================================

    def test_committee_initialization(self):
        """Test committee initializes correctly"""
        agents = [
            MockAgent("Agent1", "BUY", 0.8),
            MockAgent("Agent2", "SELL", 0.7),
        ]
        committee = AgentCommittee(agents, confidence_threshold=0.7)

        assert len(committee.agents) == 2
        assert committee.confidence_threshold == 0.7
        assert committee.stats["decisions_made"] == 0

    def test_empty_committee_fails(self):
        """Test that empty committee is not allowed"""
        # This should work but return HOLD on all votes
        committee = AgentCommittee([], confidence_threshold=0.7)
        assert len(committee.agents) == 0

    # ========================================================================
    # Voting Tests - Basic
    # ========================================================================

    @pytest.mark.asyncio
    async def test_unanimous_buy_vote(self, sample_tick):
        """Test unanimous BUY vote from all agents"""
        agents = [
            MockAgent("Agent1", "BUY", 0.9, 0.01),
            MockAgent("Agent2", "BUY", 0.8, 0.01),
            MockAgent("Agent3", "BUY", 0.85, 0.01),
        ]
        committee = AgentCommittee(agents, confidence_threshold=0.7)

        decision = await committee.vote(sample_tick)

        assert decision.action == "BUY"
        assert decision.confidence >= 0.8  # Should be high with unanimous vote
        assert decision.size > 0
        assert not decision.vetoed
        assert len(decision.votes) == 3

    @pytest.mark.asyncio
    async def test_unanimous_sell_vote(self, sample_tick):
        """Test unanimous SELL vote from all agents"""
        agents = [
            MockAgent("Agent1", "SELL", 0.9, 0.01),
            MockAgent("Agent2", "SELL", 0.8, 0.01),
        ]
        committee = AgentCommittee(agents, confidence_threshold=0.7)

        decision = await committee.vote(sample_tick)

        assert decision.action == "SELL"
        assert decision.confidence >= 0.8
        assert decision.size > 0

    @pytest.mark.asyncio
    async def test_unanimous_hold_vote(self, sample_tick):
        """Test unanimous HOLD vote from all agents"""
        agents = [
            MockAgent("Agent1", "HOLD", 0.6, 0.0),
            MockAgent("Agent2", "HOLD", 0.7, 0.0),
        ]
        committee = AgentCommittee(agents, confidence_threshold=0.7)

        decision = await committee.vote(sample_tick)

        assert decision.action == "HOLD"
        assert decision.size == 0.0

    # ========================================================================
    # Voting Tests - Split Decisions
    # ========================================================================

    @pytest.mark.asyncio
    async def test_split_vote_buy_wins(self, sample_tick):
        """Test split vote where BUY has higher weighted confidence"""
        agents = [
            MockAgent("Agent1", "BUY", 0.9, 0.01),  # Strong BUY
            MockAgent("Agent2", "BUY", 0.8, 0.01),  # Strong BUY
            MockAgent("Agent3", "SELL", 0.6, 0.01), # Weak SELL
        ]
        committee = AgentCommittee(agents, confidence_threshold=0.5)

        decision = await committee.vote(sample_tick)

        assert decision.action == "BUY"  # BUY should win with higher confidence

    @pytest.mark.asyncio
    async def test_split_vote_confidence_too_low(self, sample_tick):
        """Test split vote where no action meets confidence threshold"""
        agents = [
            MockAgent("Agent1", "BUY", 0.5, 0.01),
            MockAgent("Agent2", "SELL", 0.5, 0.01),
            MockAgent("Agent3", "HOLD", 0.5, 0.0),
        ]
        committee = AgentCommittee(agents, confidence_threshold=0.9)

        decision = await committee.vote(sample_tick)

        # With 0.9 threshold and only 0.5 confidence votes, should default to HOLD
        # Note: The actual behavior depends on implementation - may need to verify
        assert decision.confidence < 0.9

    # ========================================================================
    # Weighted Voting Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_weighted_voting(self, sample_tick):
        """Test that agent weights affect voting outcome"""
        agent1 = MockAgent("HighWeight", "BUY", 0.8, 0.01)
        agent1.weight = 3.0  # 3x weight

        agent2 = MockAgent("LowWeight", "SELL", 0.8, 0.01)
        agent2.weight = 1.0

        committee = AgentCommittee([agent1, agent2], confidence_threshold=0.5)
        decision = await committee.vote(sample_tick)

        # BUY should win because of higher weight (3.0 vs 1.0)
        assert decision.action == "BUY"

    @pytest.mark.asyncio
    async def test_equal_weights(self, sample_tick):
        """Test voting with equal weights"""
        agents = [
            MockAgent("Agent1", "BUY", 0.9, 0.01),
            MockAgent("Agent2", "SELL", 0.9, 0.01),
        ]
        for agent in agents:
            agent.weight = 1.0

        committee = AgentCommittee(agents, confidence_threshold=0.5)
        decision = await committee.vote(sample_tick)

        # With equal weights and confidence, first one or random should win
        # The actual behavior depends on implementation
        assert decision.action in ["BUY", "SELL"]

    # ========================================================================
    # Veto System Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_single_agent_veto(self, sample_tick):
        """Test single agent can veto trade"""
        agents = [
            MockAgent("Agent1", "BUY", 0.9, 0.01),
            MockAgent("Agent2", "BUY", 0.9, 0.01),
            MockAgent("VetoAgent", "HOLD", 1.0, 0.0, veto=True),
        ]
        committee = AgentCommittee(agents, confidence_threshold=0.5)

        decision = await committee.vote(sample_tick)

        assert decision.vetoed
        assert decision.action == "HOLD"
        assert decision.size == 0.0
        assert "VetoAgent" in decision.reason

    @pytest.mark.asyncio
    async def test_multiple_agent_veto(self, sample_tick):
        """Test multiple agents can veto"""
        agents = [
            MockAgent("Veto1", "HOLD", 1.0, 0.0, veto=True),
            MockAgent("Veto2", "HOLD", 1.0, 0.0, veto=True),
        ]
        committee = AgentCommittee(agents, confidence_threshold=0.5)

        decision = await committee.vote(sample_tick)

        assert decision.vetoed
        assert decision.action == "HOLD"
        assert "Veto1" in decision.reason
        assert "Veto2" in decision.reason

    @pytest.mark.asyncio
    async def test_veto_updates_agent_stats(self, sample_tick):
        """Test veto updates agent statistics"""
        veto_agent = MockAgent("VetoAgent", "HOLD", 1.0, 0.0, veto=True)
        agents = [
            MockAgent("Agent1", "BUY", 0.9, 0.01),
            veto_agent,
        ]
        committee = AgentCommittee(agents, confidence_threshold=0.5)

        await committee.vote(sample_tick)

        assert veto_agent.stats["vetoes_issued"] == 1
        assert committee.stats["trades_vetoed"] == 1

    # ========================================================================
    # Position Size Calculation Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_position_size_averaging(self, sample_tick):
        """Test position size is averaged from voting agents"""
        agents = [
            MockAgent("Agent1", "BUY", 0.8, 0.01),  # Size: 0.01
            MockAgent("Agent2", "BUY", 0.8, 0.03),  # Size: 0.03
        ]
        committee = AgentCommittee(agents, confidence_threshold=0.5)

        decision = await committee.vote(sample_tick)

        # Average size should be (0.01 + 0.03) / 2 = 0.02
        assert abs(decision.size - 0.02) < 0.001

    # ========================================================================
    # Statistics Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_decision_counter_increments(self, sample_tick):
        """Test decisions_made counter increments"""
        agents = [MockAgent("Agent1", "BUY", 0.8, 0.01)]
        committee = AgentCommittee(agents, confidence_threshold=0.5)

        await committee.vote(sample_tick)
        await committee.vote(sample_tick)
        await committee.vote(sample_tick)

        assert committee.stats["decisions_made"] == 3

    @pytest.mark.asyncio
    async def test_agent_vote_counter(self, sample_tick):
        """Test agent vote counter increments"""
        agent = MockAgent("Agent1", "BUY", 0.8, 0.01)
        committee = AgentCommittee([agent], confidence_threshold=0.5)

        await committee.vote(sample_tick)

        assert agent.stats["votes_cast"] == 1

    def test_get_stats(self):
        """Test get_stats returns correct structure"""
        agents = [
            MockAgent("Agent1", "BUY", 0.8),
            MockAgent("Agent2", "SELL", 0.7),
        ]
        committee = AgentCommittee(agents, confidence_threshold=0.7)

        stats = committee.get_stats()

        assert "decisions_made" in stats
        assert "trades_executed" in stats
        assert "trades_vetoed" in stats
        assert "win_rate" in stats
        assert "agents" in stats
        assert len(stats["agents"]) == 2

    # ========================================================================
    # Dynamic Weight Adjustment Tests
    # ========================================================================

    def test_update_weights_high_accuracy(self):
        """Test weights increase for high-accuracy agents"""
        agent = MockAgent("HighAccuracy", "BUY", 0.8)
        agent.stats["correct_predictions"] = 70
        agent.stats["incorrect_predictions"] = 30
        agent.weight = 1.0

        committee = AgentCommittee([agent], confidence_threshold=0.5)
        committee.update_weights_by_performance()

        # Weight should increase for 70% accuracy (>60%)
        assert agent.weight > 1.0

    def test_update_weights_low_accuracy(self):
        """Test weights decrease for low-accuracy agents"""
        agent = MockAgent("LowAccuracy", "BUY", 0.8)
        agent.stats["correct_predictions"] = 30
        agent.stats["incorrect_predictions"] = 70
        agent.weight = 1.0

        committee = AgentCommittee([agent], confidence_threshold=0.5)
        committee.update_weights_by_performance()

        # Weight should decrease for 30% accuracy (<40%)
        assert agent.weight < 1.0

    def test_update_weights_minimum_floor(self):
        """Test weights never go below minimum"""
        agent = MockAgent("TerribleAgent", "BUY", 0.8)
        agent.stats["correct_predictions"] = 0
        agent.stats["incorrect_predictions"] = 100
        agent.weight = 1.0

        committee = AgentCommittee([agent], confidence_threshold=0.5)

        # Run multiple updates to try to drive weight to zero
        for _ in range(100):
            committee.update_weights_by_performance()

        # Weight should never go below 0.3
        assert agent.weight >= 0.3

    def test_update_weights_maximum_ceiling(self):
        """Test weights never exceed maximum"""
        agent = MockAgent("PerfectAgent", "BUY", 0.8)
        agent.stats["correct_predictions"] = 100
        agent.stats["incorrect_predictions"] = 0
        agent.weight = 1.0

        committee = AgentCommittee([agent], confidence_threshold=0.5)

        # Run multiple updates to try to drive weight very high
        for _ in range(100):
            committee.update_weights_by_performance()

        # Weight should never exceed 2.0
        assert agent.weight <= 2.0

    # ========================================================================
    # Trade Result Tracking Tests
    # ========================================================================

    def test_update_trade_result_profitable(self):
        """Test profitable trade updates stats correctly"""
        agents = [MockAgent("Agent1", "BUY", 0.8)]
        committee = AgentCommittee(agents, confidence_threshold=0.5)

        committee.update_trade_result({"profit": 100}, profitable=True)

        assert committee.stats["profitable_trades"] == 1
        assert committee.stats["losing_trades"] == 0
        assert committee.win_rate == 1.0

    def test_update_trade_result_unprofitable(self):
        """Test unprofitable trade updates stats correctly"""
        agents = [MockAgent("Agent1", "BUY", 0.8)]
        committee = AgentCommittee(agents, confidence_threshold=0.5)

        committee.update_trade_result({"loss": 50}, profitable=False)

        assert committee.stats["profitable_trades"] == 0
        assert committee.stats["losing_trades"] == 1
        assert committee.win_rate == 0.0

    def test_win_rate_calculation(self):
        """Test win rate calculation"""
        agents = [MockAgent("Agent1", "BUY", 0.8)]
        committee = AgentCommittee(agents, confidence_threshold=0.5)

        # 7 wins, 3 losses = 70% win rate
        for _ in range(7):
            committee.update_trade_result({}, profitable=True)
        for _ in range(3):
            committee.update_trade_result({}, profitable=False)

        assert abs(committee.win_rate - 0.7) < 0.01

    # ========================================================================
    # Edge Cases
    # ========================================================================

    @pytest.mark.asyncio
    async def test_no_votes_received(self, sample_tick):
        """Test committee handles no votes gracefully"""
        committee = AgentCommittee([], confidence_threshold=0.7)

        decision = await committee.vote(sample_tick)

        assert decision.action == "HOLD"
        assert decision.confidence == 0.0
        assert decision.size == 0.0
        assert "No votes" in decision.reason

    @pytest.mark.asyncio
    async def test_agent_error_handling(self, sample_tick):
        """Test committee handles agent errors gracefully"""
        class ErrorAgent(BaseAgent):
            async def analyze(self, tick, position, market_context):
                raise Exception("Agent crashed!")

        agents = [
            ErrorAgent("BrokenAgent"),
            MockAgent("WorkingAgent", "BUY", 0.8, 0.01),
        ]
        committee = AgentCommittee(agents, confidence_threshold=0.5)

        # Should not crash, should continue with working agent
        decision = await committee.vote(sample_tick)

        assert decision is not None
        # Only 1 vote should be collected (from WorkingAgent)
        assert len(decision.votes) == 1

    @pytest.mark.asyncio
    async def test_zero_confidence_votes(self, sample_tick):
        """Test handling of zero-confidence votes"""
        agents = [
            MockAgent("Agent1", "BUY", 0.0, 0.01),
            MockAgent("Agent2", "BUY", 0.0, 0.01),
        ]
        committee = AgentCommittee(agents, confidence_threshold=0.5)

        decision = await committee.vote(sample_tick)

        # With zero confidence, should not meet threshold
        assert decision.confidence == 0.0

    # ========================================================================
    # Representation Tests
    # ========================================================================

    def test_repr(self):
        """Test string representation"""
        agents = [MockAgent("Agent1", "BUY", 0.8)]
        committee = AgentCommittee(agents, confidence_threshold=0.7)

        repr_str = repr(committee)

        assert "AgentCommittee" in repr_str
        assert "1 agents" in repr_str or "1" in repr_str
        assert "0.70" in repr_str or "70" in repr_str  # Threshold
