"""
Unit tests for TrendFollowingAgent

Tests momentum calculation, MA crossover, RSI, and trading logic.
"""

import pytest
from coinswarm.agents.base_agent import AgentVote
from coinswarm.agents.trend_agent import TrendFollowingAgent
from coinswarm.data_ingest.base import DataPoint


class TestTrendFollowingAgent:
    """Test suite for TrendFollowingAgent"""

    @pytest.fixture
    def agent(self):
        """Create trend following agent"""
        return TrendFollowingAgent(name="TestTrendAgent", weight=1.0)

    def create_tick(self, price: float, volume: float = 100.0):
        """Helper to create market tick"""
        return DataPoint(
            source="test",
            symbol="BTC-USD",
            timestamp="2024-01-01T00:00:00Z",
            data={"price": price, "volume": volume}
        )

    # ========================================================================
    # Initialization Tests
    # ========================================================================

    def test_initialization(self, agent):
        """Test agent initializes correctly"""
        assert agent.name == "TestTrendAgent"
        assert agent.weight == 1.0
        assert agent.price_history == []
        assert agent.max_history == 100

    # ========================================================================
    # Insufficient Data Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_insufficient_data_returns_hold(self, agent):
        """Test agent returns HOLD with insufficient data"""
        tick = self.create_tick(50000.0)

        vote = await agent.analyze(tick, position=None, market_context={})

        assert vote.action == "HOLD"
        assert vote.confidence == 0.5
        assert "Insufficient data" in vote.reason

    @pytest.mark.asyncio
    async def test_builds_price_history(self, agent):
        """Test agent builds price history correctly"""
        for i in range(5):
            tick = self.create_tick(50000.0 + i * 100)
            await agent.analyze(tick, position=None, market_context={})

        assert len(agent.price_history) == 5
        assert agent.price_history[-1] == 50400.0

    # ========================================================================
    # Momentum Calculation Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_positive_momentum_detected(self, agent):
        """Test positive momentum detection"""
        # Create upward trend: 50000, 50500, 51000, ..., 55000
        for i in range(20):
            tick = self.create_tick(50000.0 + i * 500)
            await agent.analyze(tick, position=None, market_context={})

        momentum = agent._calculate_momentum()

        # Momentum should be positive (price increased)
        assert momentum > 0

    @pytest.mark.asyncio
    async def test_negative_momentum_detected(self, agent):
        """Test negative momentum detection"""
        # Create downward trend: 55000, 54500, 54000, ..., 50000
        for i in range(20):
            tick = self.create_tick(55000.0 - i * 500)
            await agent.analyze(tick, position=None, market_context={})

        momentum = agent._calculate_momentum()

        # Momentum should be negative (price decreased)
        assert momentum < 0

    def test_momentum_calculation_formula(self, agent):
        """Test momentum calculation formula"""
        # Manually set price history
        agent.price_history = [50000, 50100, 50200, 50300, 50400, 50500,
                               50600, 50700, 50800, 50900, 51000]

        momentum = agent._calculate_momentum()

        # Momentum = (51000 - 50100) / 50100 ≈ 0.01796 (≈1.8%)
        expected = (51000 - 50100) / 50100
        assert abs(momentum - expected) < 0.001

    # ========================================================================
    # MA Crossover Tests
    # ========================================================================

    def test_golden_cross_buy_signal(self, agent):
        """Test golden cross (fast MA > slow MA) generates BUY signal"""
        # Create scenario where fast MA > slow MA
        # Recent prices higher (fast MA up), older prices lower (slow MA down)
        prices = [40000] * 40  # 40 low prices for slow MA
        prices.extend([50000] * 10)  # 10 high prices for fast MA
        agent.price_history = prices

        signal = agent._calculate_ma_crossover()

        assert signal == "BUY"

    def test_death_cross_sell_signal(self, agent):
        """Test death cross (fast MA < slow MA) generates SELL signal"""
        # Create scenario where fast MA < slow MA
        # Recent prices lower (fast MA down), older prices higher (slow MA up)
        prices = [50000] * 40  # 40 high prices for slow MA
        prices.extend([40000] * 10)  # 10 low prices for fast MA
        agent.price_history = prices

        signal = agent._calculate_ma_crossover()

        assert signal == "SELL"

    def test_ma_crossover_hold_when_close(self, agent):
        """Test HOLD signal when MAs are close together"""
        # All prices similar - no clear crossover
        agent.price_history = [50000] * 50

        signal = agent._calculate_ma_crossover()

        assert signal == "HOLD"

    # ========================================================================
    # RSI Calculation Tests
    # ========================================================================

    def test_rsi_overbought(self, agent):
        """Test RSI > 70 indicates overbought"""
        # Strong upward price movement
        prices = []
        for i in range(30):
            prices.append(50000 + i * 500)  # Consistent gains
        agent.price_history = prices

        rsi = agent._calculate_rsi(period=14)

        # RSI should be high (>70) with consistent gains
        assert rsi > 70

    def test_rsi_oversold(self, agent):
        """Test RSI < 30 indicates oversold"""
        # Strong downward price movement
        prices = []
        for i in range(30):
            prices.append(60000 - i * 500)  # Consistent losses
        agent.price_history = prices

        rsi = agent._calculate_rsi(period=14)

        # RSI should be low (<30) with consistent losses
        assert rsi < 30

    def test_rsi_neutral(self, agent):
        """Test RSI ≈ 50 with sideways price action"""
        # Sideways price action (no trend)
        prices = [50000, 50100, 49900, 50050, 49950] * 6
        agent.price_history = prices

        rsi = agent._calculate_rsi(period=14)

        # RSI should be near 50 with mixed gains/losses
        assert 40 < rsi < 60

    def test_rsi_insufficient_data(self, agent):
        """Test RSI returns neutral with insufficient data"""
        # Only 5 prices (need at least 15 for period=14)
        agent.price_history = [50000] * 5

        rsi = agent._calculate_rsi(period=14)

        # Should return neutral (50.0)
        assert rsi == 50.0

    # ========================================================================
    # Trading Decision Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_buy_signal_strong_uptrend(self, agent):
        """Test BUY signal in strong uptrend"""
        # Create strong uptrend: momentum >2%, golden cross, RSI <70
        prices = []
        # Slow MA base (40 prices)
        for i in range(40):
            prices.append(40000 + i * 100)
        # Fast MA higher (10 prices)
        for i in range(10):
            prices.append(44000 + i * 200)

        for price in prices:
            tick = self.create_tick(price)
            await agent.analyze(tick, position=None, market_context={})

        # Final vote should be BUY
        final_tick = self.create_tick(46000)
        vote = await agent.analyze(final_tick, position=None, market_context={})

        assert vote.action == "BUY"
        assert vote.confidence > 0.0
        assert vote.size > 0.0

    @pytest.mark.asyncio
    async def test_sell_signal_strong_downtrend(self, agent):
        """Test SELL signal in strong downtrend"""
        # Create strong downtrend: momentum <-2%, death cross, RSI >30
        prices = []
        # Slow MA base (40 prices)
        for i in range(40):
            prices.append(50000 - i * 100)
        # Fast MA lower (10 prices)
        for i in range(10):
            prices.append(46000 - i * 200)

        for price in prices:
            tick = self.create_tick(price)
            await agent.analyze(tick, position=None, market_context={})

        # Final vote should be SELL
        final_tick = self.create_tick(44000)
        vote = await agent.analyze(final_tick, position=None, market_context={})

        assert vote.action == "SELL"
        assert vote.confidence > 0.0
        assert vote.size > 0.0

    @pytest.mark.asyncio
    async def test_hold_signal_overbought(self, agent):
        """Test HOLD when RSI is overbought (>70)"""
        # Create overbought scenario: strong momentum but RSI >70
        prices = []
        for i in range(50):
            prices.append(40000 + i * 500)  # Strong uptrend

        for price in prices:
            tick = self.create_tick(price)
            await agent.analyze(tick, position=None, market_context={})

        vote = await agent.analyze(self.create_tick(65000), position=None, market_context={})

        # Should HOLD due to overbought conditions
        # (RSI >70 prevents BUY despite uptrend)
        assert vote.action == "HOLD"

    @pytest.mark.asyncio
    async def test_hold_signal_oversold(self, agent):
        """Test HOLD when RSI is oversold (<30)"""
        # Create oversold scenario: strong downtrend but RSI <30
        prices = []
        for i in range(50):
            prices.append(60000 - i * 500)  # Strong downtrend

        for price in prices:
            tick = self.create_tick(price)
            await agent.analyze(tick, position=None, market_context={})

        vote = await agent.analyze(self.create_tick(35000), position=None, market_context={})

        # Should HOLD due to oversold conditions
        # (RSI <30 prevents SELL despite downtrend)
        assert vote.action == "HOLD"

    # ========================================================================
    # Position Size Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_position_size_based_on_confidence(self, agent):
        """Test position size scales with confidence"""
        # Build price history for valid analysis
        for i in range(50):
            tick = self.create_tick(50000 + i * 100)
            await agent.analyze(tick, position=None, market_context={})

        # High confidence should give larger position
        vote = await agent.analyze(self.create_tick(55000), position=None, market_context={})

        # Position size should be non-zero and scaled by confidence
        assert vote.size > 0
        # Size should be roughly confidence * base_size (0.01)
        # Formula in code: size = base_size * confidence
        expected_size = 0.01 * vote.confidence
        assert abs(vote.size - expected_size) < 0.001

    @pytest.mark.asyncio
    async def test_reduced_size_with_existing_position(self, agent):
        """Test position size reduced when already in position"""
        # Build price history
        for i in range(50):
            tick = self.create_tick(50000 + i * 100)
            await agent.analyze(tick, position=None, market_context={})

        # Vote without position
        vote_no_position = await agent.analyze(
            self.create_tick(55000), position=None, market_context={}
        )

        # Vote with existing position
        vote_with_position = await agent.analyze(
            self.create_tick(55000),
            position={"size": 0.01, "entry_price": 54000},
            market_context={}
        )

        # Size should be smaller with existing position (reduced by 50%)
        assert vote_with_position.size < vote_no_position.size
        assert vote_with_position.size == vote_no_position.size * 0.5

    # ========================================================================
    # Performance Tracking Tests
    # ========================================================================

    def test_update_performance_profitable(self, agent):
        """Test performance update for profitable trade"""
        agent.update_performance({"profitable": True})

        assert agent.stats["correct_predictions"] == 1
        assert agent.stats["incorrect_predictions"] == 0

    def test_update_performance_unprofitable(self, agent):
        """Test performance update for unprofitable trade"""
        agent.update_performance({"profitable": False})

        assert agent.stats["correct_predictions"] == 0
        assert agent.stats["incorrect_predictions"] == 1

    def test_accuracy_calculation(self, agent):
        """Test accuracy calculation"""
        # 7 correct, 3 incorrect = 70% accuracy
        for _ in range(7):
            agent.update_performance({"profitable": True})
        for _ in range(3):
            agent.update_performance({"profitable": False})

        assert abs(agent.accuracy - 0.7) < 0.01

    def test_accuracy_neutral_before_trades(self, agent):
        """Test accuracy is neutral (0.5) before any trades"""
        assert agent.accuracy == 0.5

    # ========================================================================
    # Edge Cases
    # ========================================================================

    def test_price_history_max_length(self, agent):
        """Test price history doesn't exceed max length"""
        # Add more than max_history prices
        for i in range(150):
            agent.price_history.append(50000 + i)

        # Simulate normal analysis flow
        agent.price_history.append(50000)
        if len(agent.price_history) > agent.max_history:
            agent.price_history.pop(0)

        assert len(agent.price_history) <= agent.max_history

    @pytest.mark.asyncio
    async def test_handles_zero_price(self, agent):
        """Test agent handles zero price gracefully"""
        tick = self.create_tick(0.0)
        vote = await agent.analyze(tick, position=None, market_context={})

        # Should not crash, should return HOLD or handle gracefully
        assert vote is not None
        assert isinstance(vote, AgentVote)

    @pytest.mark.asyncio
    async def test_handles_negative_price(self, agent):
        """Test agent handles negative price (invalid data)"""
        tick = self.create_tick(-50000.0)
        vote = await agent.analyze(tick, position=None, market_context={})

        # Should not crash
        assert vote is not None

    # ========================================================================
    # Representation Tests
    # ========================================================================

    def test_repr(self, agent):
        """Test string representation"""
        agent.stats["correct_predictions"] = 7
        agent.stats["incorrect_predictions"] = 3

        repr_str = repr(agent)

        assert "TestTrendAgent" in repr_str
        assert "weight=" in repr_str
        assert "accuracy=" in repr_str or "70" in repr_str
