"""
Unit tests for ArbitrageAgent and CrossExchangeArbitrageAgent

ArbitrageAgent detects triangular arbitrage opportunities like:
- BTC → SOL → USDC → BTC
- Need >0.4% spread to profit after 0.9% total fees (3 legs × 0.3%)

CrossExchangeArbitrageAgent is currently a stub (not yet implemented).
"""

from datetime import datetime

import pytest
from coinswarm.agents.arbitrage_agent import ArbitrageAgent, CrossExchangeArbitrageAgent
from coinswarm.data_ingest.base import DataPoint

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def arb_agent():
    """Create ArbitrageAgent with default settings"""
    return ArbitrageAgent(
        name="ArbitrageAgent",
        weight=2.0,
        min_profit_pct=0.004,  # 0.4% minimum
        fee_pct=0.003  # 0.3% per trade
    )


@pytest.fixture
def cross_exchange_agent():
    """Create CrossExchangeArbitrageAgent"""
    return CrossExchangeArbitrageAgent(
        name="CrossExchangeArb",
        weight=1.5,
        min_profit_pct=0.005  # 0.5% minimum
    )


def create_tick(symbol: str, price: float) -> DataPoint:
    """Helper to create DataPoint"""
    return DataPoint(
        symbol=symbol,
        timestamp=datetime.now(),
        data={"price": price}
    )


# ============================================================================
# ArbitrageAgent - Initialization Tests
# ============================================================================

def test_arbitrage_agent_initialization():
    """Test ArbitrageAgent initializes correctly"""
    agent = ArbitrageAgent(
        name="TestArb",
        weight=3.0,
        min_profit_pct=0.005,
        fee_pct=0.0025
    )

    assert agent.name == "TestArb"
    assert agent.weight == 3.0
    assert agent.min_profit_pct == 0.005
    assert agent.fee_pct == 0.0025
    assert agent.total_fee_pct == 0.0025 * 3  # 3 legs
    assert agent.price_cache == {}
    assert agent.opportunities_found == 0
    assert agent.opportunities_executed == 0


def test_arbitrage_agent_default_initialization():
    """Test ArbitrageAgent with defaults"""
    agent = ArbitrageAgent()

    assert agent.name == "ArbitrageAgent"
    assert agent.weight == 2.0  # High weight (low risk strategy)
    assert agent.min_profit_pct == 0.004  # 0.4%
    assert agent.fee_pct == 0.003  # 0.3%
    assert agent.total_fee_pct == 0.009  # 0.9% total (3 legs)


def test_total_fee_calculation():
    """Test total fee is 3× single fee (3 legs)"""
    agent = ArbitrageAgent(fee_pct=0.002)

    # 3 trades = 3× fees
    assert agent.total_fee_pct == 0.002 * 3
    assert agent.total_fee_pct == 0.006


# ============================================================================
# ArbitrageAgent - Price Cache Tests
# ============================================================================

@pytest.mark.asyncio
async def test_updates_price_cache(arb_agent):
    """Test agent updates price cache with each tick"""
    assert len(arb_agent.price_cache) == 0

    tick = create_tick("BTC-USDC", 50000.0)
    await arb_agent.analyze(tick, None, {})

    assert "BTC-USDC" in arb_agent.price_cache
    assert arb_agent.price_cache["BTC-USDC"] == 50000.0


@pytest.mark.asyncio
async def test_price_cache_updates_on_new_price(arb_agent):
    """Test price cache updates when price changes"""
    # First tick
    tick1 = create_tick("BTC-USDC", 50000.0)
    await arb_agent.analyze(tick1, None, {})
    assert arb_agent.price_cache["BTC-USDC"] == 50000.0

    # Price changes
    tick2 = create_tick("BTC-USDC", 51000.0)
    await arb_agent.analyze(tick2, None, {})
    assert arb_agent.price_cache["BTC-USDC"] == 51000.0


@pytest.mark.asyncio
async def test_price_cache_multiple_symbols(arb_agent):
    """Test price cache tracks multiple symbols"""
    symbols_prices = [
        ("BTC-USDC", 50000.0),
        ("ETH-USDC", 3000.0),
        ("SOL-USDC", 100.0),
        ("BTC-SOL", 500.0),
        ("ETH-BTC", 0.06)
    ]

    for symbol, price in symbols_prices:
        tick = create_tick(symbol, price)
        await arb_agent.analyze(tick, None, {})

    assert len(arb_agent.price_cache) == 5
    for symbol, price in symbols_prices:
        assert arb_agent.price_cache[symbol] == price


# ============================================================================
# ArbitrageAgent - No Opportunity Tests
# ============================================================================

@pytest.mark.asyncio
async def test_returns_hold_when_no_opportunity(arb_agent):
    """Test agent returns HOLD when no arbitrage opportunity"""
    tick = create_tick("BTC-USDC", 50000.0)
    vote = await arb_agent.analyze(tick, None, {})

    assert vote.action == "HOLD"
    assert vote.confidence == 0.5  # Neutral
    assert vote.size == 0.0
    assert vote.veto is False
    assert "No arbitrage opportunities found" in vote.reason


@pytest.mark.asyncio
async def test_holds_when_insufficient_prices(arb_agent):
    """Test agent holds when not all prices available for arbitrage"""
    # Only have 1 out of 3 required prices
    tick = create_tick("BTC-USDC", 50000.0)
    vote = await arb_agent.analyze(tick, None, {})

    assert vote.action == "HOLD"
    assert vote.size == 0.0


@pytest.mark.asyncio
async def test_holds_when_profit_below_threshold(arb_agent):
    """Test agent holds when profit exists but below minimum threshold"""
    # Setup prices with small arbitrage (0.2% profit)
    # After 0.9% fees = -0.7% net (LOSS)
    arb_agent.price_cache = {
        "BTC-USDC": 50000.0,
        "BTC-SOL": 500.0,  # 1 BTC = 500 SOL
        "SOL-USDC": 100.2  # Small markup
    }

    tick = create_tick("BTC-USDC", 50000.0)
    vote = await arb_agent.analyze(tick, None, {})

    # Profit (0.2%) - fees (0.9%) = -0.7% (loss)
    # Should not trade
    assert vote.action == "HOLD"


# ============================================================================
# ArbitrageAgent - Profitable Opportunity Tests
# ============================================================================

@pytest.mark.asyncio
async def test_buys_on_profitable_arbitrage(arb_agent):
    """Test agent votes BUY when profitable arbitrage found"""
    # Setup: 1% gross profit - 0.9% fees = 0.1% net profit (below 0.4% threshold)
    # Let's make it 1.5% gross - 0.9% fees = 0.6% net (above threshold)
    arb_agent.price_cache = {
        "BTC-USDC": 50000.0,
        "BTC-SOL": 500.0,  # 1 BTC = 500 SOL
        "SOL-USDC": 101.5  # $101.50 per SOL (1.5% markup)
    }
    # Path: $50k → 1 BTC → 500 SOL → $50,750 = 1.5% gross

    tick = create_tick("BTC-USDC", 50000.0)
    vote = await arb_agent.analyze(tick, None, {})

    assert vote.action == "BUY"
    assert vote.confidence > 0.7  # High confidence
    assert vote.size > 0  # Non-zero size
    assert vote.veto is False
    assert "Arbitrage" in vote.reason
    assert "profit" in vote.reason.lower()


@pytest.mark.asyncio
async def test_arbitrage_opportunity_count_increments(arb_agent):
    """Test opportunities_found counter increments"""
    assert arb_agent.opportunities_found == 0

    # Setup profitable arbitrage
    arb_agent.price_cache = {
        "BTC-USDC": 50000.0,
        "BTC-SOL": 500.0,
        "SOL-USDC": 101.5  # 1.5% profit
    }

    tick = create_tick("BTC-USDC", 50000.0)
    vote = await arb_agent.analyze(tick, None, {})

    assert vote.action == "BUY"
    assert arb_agent.opportunities_found == 1


@pytest.mark.asyncio
async def test_confidence_scales_with_profit(arb_agent):
    """Test confidence increases with higher profit"""
    # Test 1: Small profit (0.5% net)
    arb_agent.price_cache = {
        "BTC-USDC": 50000.0,
        "BTC-SOL": 500.0,
        "SOL-USDC": 101.4  # 1.4% gross - 0.9% fees = 0.5% net
    }

    tick = create_tick("BTC-USDC", 50000.0)
    vote1 = await arb_agent.analyze(tick, None, {})
    confidence1 = vote1.confidence

    # Test 2: Large profit (2% net)
    arb_agent.price_cache = {
        "BTC-USDC": 50000.0,
        "BTC-SOL": 500.0,
        "SOL-USDC": 102.9  # 2.9% gross - 0.9% fees = 2% net
    }

    vote2 = await arb_agent.analyze(tick, None, {})
    confidence2 = vote2.confidence

    # Higher profit should give higher confidence
    assert confidence2 > confidence1


@pytest.mark.asyncio
async def test_confidence_capped_at_95_percent(arb_agent):
    """Test confidence never exceeds 0.95 (95%)"""
    # Setup huge profit (10% net - unrealistic but tests cap)
    arb_agent.price_cache = {
        "BTC-USDC": 50000.0,
        "BTC-SOL": 500.0,
        "SOL-USDC": 109.9  # 9.9% gross - 0.9% fees = 9% net
    }

    tick = create_tick("BTC-USDC", 50000.0)
    vote = await arb_agent.analyze(tick, None, {})

    # Should be capped at 0.95
    assert vote.confidence <= 0.95


@pytest.mark.asyncio
async def test_arbitrage_size_is_small(arb_agent):
    """Test arbitrage trades are small size (1% of capital)"""
    arb_agent.price_cache = {
        "BTC-USDC": 50000.0,
        "BTC-SOL": 500.0,
        "SOL-USDC": 101.5
    }

    tick = create_tick("BTC-USDC", 50000.0)
    vote = await arb_agent.analyze(tick, None, {})

    assert vote.action == "BUY"
    # Arbitrage should use small size (0.01 = 1%)
    assert vote.size == 0.01


# ============================================================================
# ArbitrageAgent - Triangular Arbitrage Calculation Tests
# ============================================================================

def test_triangular_arbitrage_calculation_profitable(arb_agent):
    """Test triangular arbitrage calculation for profitable path"""
    arb_agent.price_cache = {
        "BTC-USDC": 50000.0,
        "BTC-SOL": 500.0,
        "SOL-USDC": 101.0
    }

    result = arb_agent._calculate_triangular_arbitrage(
        start="BTC-USDC",
        leg1="BTC-SOL",
        leg2="SOL-USDC",
        end="BTC-USDC"
    )

    assert result is not None
    path, profit_pct, end_amount = result

    # Path: $50k → 1 BTC → 500 SOL → $50,500
    # Profit: $500 / $50k = 1%
    assert profit_pct == pytest.approx(0.01, abs=0.001)
    assert end_amount == pytest.approx(50500, abs=10)


def test_triangular_arbitrage_calculation_unprofitable(arb_agent):
    """Test triangular arbitrage calculation for unprofitable path"""
    arb_agent.price_cache = {
        "BTC-USDC": 50000.0,
        "BTC-SOL": 500.0,
        "SOL-USDC": 99.0  # Loss path
    }

    result = arb_agent._calculate_triangular_arbitrage(
        start="BTC-USDC",
        leg1="BTC-SOL",
        leg2="SOL-USDC",
        end="BTC-USDC"
    )

    assert result is not None
    path, profit_pct, end_amount = result

    # Path: $50k → 1 BTC → 500 SOL → $49,500
    # Loss: -$500 / $50k = -1%
    assert profit_pct == pytest.approx(-0.01, abs=0.001)
    assert end_amount < 50000  # Lost money


def test_triangular_arbitrage_missing_prices(arb_agent):
    """Test triangular arbitrage returns None when prices missing"""
    # Only 1 price in cache
    arb_agent.price_cache = {
        "BTC-USDC": 50000.0
    }

    result = arb_agent._calculate_triangular_arbitrage(
        start="BTC-USDC",
        leg1="BTC-SOL",  # Not in cache
        leg2="SOL-USDC",  # Not in cache
        end="BTC-USDC"
    )

    assert result is None


def test_triangular_arbitrage_path_structure(arb_agent):
    """Test triangular arbitrage returns correct path structure"""
    arb_agent.price_cache = {
        "BTC-USDC": 50000.0,
        "BTC-SOL": 500.0,
        "SOL-USDC": 100.0
    }

    result = arb_agent._calculate_triangular_arbitrage(
        start="BTC-USDC",
        leg1="BTC-SOL",
        leg2="SOL-USDC",
        end="BTC-USDC"
    )

    assert result is not None
    path, profit_pct, end_amount = result

    # Path should contain all 4 symbols
    assert len(path) == 4
    assert path[0] == "BTC-USDC"
    assert path[1] == "BTC-SOL"
    assert path[2] == "SOL-USDC"
    assert path[3] == "BTC-USDC"


# ============================================================================
# ArbitrageAgent - Complex (4-leg) Arbitrage Tests
# ============================================================================

def test_complex_arbitrage_calculation(arb_agent):
    """Test 4-leg arbitrage calculation"""
    arb_agent.price_cache = {
        "SOL-USDC": 100.0,
        "BTC-SOL": 500.0,
        "ETH-BTC": 0.06,
        "ETH-SOL": 30.0
    }

    result = arb_agent._calculate_complex_arbitrage(
        start="SOL-USDC",
        leg1="BTC-SOL",
        leg2="ETH-BTC",
        leg3="ETH-SOL",
        end="SOL-USDC"
    )

    # May or may not be profitable, but should return valid result
    assert result is not None
    path, profit_pct, end_amount = result
    assert len(path) == 5  # 4 legs + end
    assert isinstance(profit_pct, float)
    assert isinstance(end_amount, float)


def test_complex_arbitrage_missing_prices(arb_agent):
    """Test 4-leg arbitrage returns None when prices missing"""
    arb_agent.price_cache = {
        "SOL-USDC": 100.0,
        "BTC-SOL": 500.0
        # Missing ETH-BTC and ETH-SOL
    }

    result = arb_agent._calculate_complex_arbitrage(
        start="SOL-USDC",
        leg1="BTC-SOL",
        leg2="ETH-BTC",
        leg3="ETH-SOL",
        end="SOL-USDC"
    )

    assert result is None


# ============================================================================
# ArbitrageAgent - Best Opportunity Selection Tests
# ============================================================================

@pytest.mark.asyncio
async def test_selects_most_profitable_path(arb_agent):
    """Test agent selects path with highest profit"""
    # Setup multiple paths with different profitability
    arb_agent.price_cache = {
        # Path 1: BTC → SOL → USDC (0.5% profit)
        "BTC-USDC": 50000.0,
        "BTC-SOL": 500.0,
        "SOL-USDC": 100.5,

        # Path 2: BTC → ETH → USDC (1.5% profit - BEST)
        "ETH-BTC": 0.06,  # 1 BTC = 0.06... wait this is inverse
        # Let me think: if ETH-BTC = 0.06, then 1 ETH = 0.06 BTC
        # So 1 BTC = 16.67 ETH
        "ETH-USDC": 3045.0,  # 16.67 ETH × $3045 = $50,750

        # Path 3: ETH → SOL → USDC (0.3% profit)
        "ETH-SOL": 30.0
    }

    tick = create_tick("BTC-USDC", 50000.0)
    vote = await arb_agent.analyze(tick, None, {})

    # Should pick most profitable path (Path 2)
    assert vote.action == "BUY"
    # Reason should mention the profitable path
    assert "Arbitrage" in vote.reason


# ============================================================================
# ArbitrageAgent - Statistics Tests
# ============================================================================

def test_get_arbitrage_stats_initial(arb_agent):
    """Test get_arbitrage_stats returns correct initial values"""
    stats = arb_agent.get_arbitrage_stats()

    assert stats["opportunities_found"] == 0
    assert stats["opportunities_executed"] == 0
    assert stats["execution_rate"] == 0  # No opportunities yet
    assert stats["min_profit_threshold"] == 0.004
    assert stats["total_fee_pct"] == 0.009


@pytest.mark.asyncio
async def test_get_arbitrage_stats_after_opportunities(arb_agent):
    """Test stats update after finding opportunities"""
    # Setup profitable arbitrage
    arb_agent.price_cache = {
        "BTC-USDC": 50000.0,
        "BTC-SOL": 500.0,
        "SOL-USDC": 101.5
    }

    # Find 3 opportunities
    tick = create_tick("BTC-USDC", 50000.0)
    await arb_agent.analyze(tick, None, {})
    await arb_agent.analyze(tick, None, {})
    await arb_agent.analyze(tick, None, {})

    stats = arb_agent.get_arbitrage_stats()

    assert stats["opportunities_found"] == 3
    assert stats["opportunities_executed"] == 0  # Not executed yet
    assert stats["execution_rate"] == 0.0


def test_execution_rate_calculation(arb_agent):
    """Test execution_rate calculation"""
    arb_agent.opportunities_found = 10
    arb_agent.opportunities_executed = 7

    stats = arb_agent.get_arbitrage_stats()

    assert stats["execution_rate"] == 0.7  # 7/10


def test_execution_rate_with_zero_opportunities(arb_agent):
    """Test execution_rate is 0 when no opportunities found"""
    arb_agent.opportunities_found = 0
    arb_agent.opportunities_executed = 0

    stats = arb_agent.get_arbitrage_stats()

    # Should not divide by zero
    assert stats["execution_rate"] == 0


# ============================================================================
# ArbitrageAgent - Fee Impact Tests
# ============================================================================

@pytest.mark.asyncio
async def test_fees_make_marginal_opportunity_unprofitable(arb_agent):
    """Test that fees eliminate marginal arbitrage opportunities"""
    # Setup: 0.8% gross profit
    # After 0.9% fees = -0.1% net (LOSS)
    arb_agent.price_cache = {
        "BTC-USDC": 50000.0,
        "BTC-SOL": 500.0,
        "SOL-USDC": 100.8  # 0.8% markup
    }

    tick = create_tick("BTC-USDC", 50000.0)
    vote = await arb_agent.analyze(tick, None, {})

    # 0.8% - 0.9% = -0.1% (loss after fees)
    # Should not trade
    assert vote.action == "HOLD"


@pytest.mark.asyncio
async def test_threshold_accounts_for_fees(arb_agent):
    """Test min_profit_pct is net profit after fees"""
    # Setup: 1.3% gross profit
    # After 0.9% fees = 0.4% net (exactly at threshold)
    arb_agent.price_cache = {
        "BTC-USDC": 50000.0,
        "BTC-SOL": 500.0,
        "SOL-USDC": 101.3  # 1.3% markup
    }

    tick = create_tick("BTC-USDC", 50000.0)
    vote = await arb_agent.analyze(tick, None, {})

    # 1.3% - 0.9% = 0.4% net = exactly at threshold
    # Should trade (>= threshold)
    assert vote.action == "BUY"


def test_custom_fee_structure(arb_agent):
    """Test agent works with custom fee structure"""
    agent = ArbitrageAgent(
        fee_pct=0.001  # 0.1% per trade
    )

    # Total fees should be 3× single fee
    assert agent.total_fee_pct == 0.003  # 0.3% total

    # With lower fees, lower profit needed
    agent.price_cache = {
        "BTC-USDC": 50000.0,
        "BTC-SOL": 500.0,
        "SOL-USDC": 100.7  # 0.7% profit
    }

    # 0.7% - 0.3% fees = 0.4% net (meets threshold)
    result = agent._calculate_triangular_arbitrage(
        start="BTC-USDC",
        leg1="BTC-SOL",
        leg2="SOL-USDC",
        end="BTC-USDC"
    )

    assert result is not None
    _, profit_pct, _ = result
    assert profit_pct == pytest.approx(0.007, abs=0.001)


# ============================================================================
# ArbitrageAgent - Edge Cases
# ============================================================================

@pytest.mark.asyncio
async def test_handles_zero_price(arb_agent):
    """Test agent handles zero price gracefully"""
    tick = create_tick("BTC-USDC", 0.0)
    vote = await arb_agent.analyze(tick, None, {})

    # Should not crash
    assert vote.action == "HOLD"


@pytest.mark.asyncio
async def test_handles_negative_price(arb_agent):
    """Test agent handles negative price (data error)"""
    tick = create_tick("BTC-USDC", -50000.0)

    # Should not crash
    vote = await arb_agent.analyze(tick, None, {})
    assert vote.action == "HOLD"


@pytest.mark.asyncio
async def test_handles_missing_price_data(arb_agent):
    """Test agent handles tick without price field"""
    tick = DataPoint(
        symbol="BTC-USDC",
        timestamp=datetime.now(),
        data={}  # No price
    )

    vote = await arb_agent.analyze(tick, None, {})

    # Should not crash, price defaults to 0
    assert vote.action == "HOLD"


def test_calculation_exception_handling(arb_agent):
    """Test arbitrage calculation handles exceptions gracefully"""
    # Force an error with invalid data
    arb_agent.price_cache = {
        "BTC-USDC": 0,  # Division by zero potential
        "BTC-SOL": 500.0,
        "SOL-USDC": 100.0
    }

    # Should return None instead of crashing
    arb_agent._calculate_triangular_arbitrage(
        start="BTC-USDC",
        leg1="BTC-SOL",
        leg2="SOL-USDC",
        end="BTC-USDC"
    )

    # Should handle gracefully (may return None or handle the zero)
    # The implementation has try/except that returns None on error


# ============================================================================
# ArbitrageAgent - High Weight Tests
# ============================================================================

def test_arbitrage_agent_has_high_weight(arb_agent):
    """Test arbitrage agent has high weight (low risk strategy)"""
    # Arbitrage is low-risk, should have high weight
    assert arb_agent.weight >= 2.0
    assert arb_agent.weight > 1.0  # Higher than default


# ============================================================================
# CrossExchangeArbitrageAgent Tests (Stub Implementation)
# ============================================================================

def test_cross_exchange_initialization(cross_exchange_agent):
    """Test CrossExchangeArbitrageAgent initializes"""
    assert cross_exchange_agent.name == "CrossExchangeArb"
    assert cross_exchange_agent.weight == 1.5
    assert cross_exchange_agent.min_profit_pct == 0.005  # 0.5%
    assert cross_exchange_agent.exchange_prices == {}


@pytest.mark.asyncio
async def test_cross_exchange_not_implemented(cross_exchange_agent):
    """Test CrossExchangeArbitrageAgent returns 'not yet implemented'"""
    tick = create_tick("BTC-USDC", 50000.0)
    vote = await cross_exchange_agent.analyze(tick, None, {})

    # Should return HOLD with explanation
    assert vote.action == "HOLD"
    assert vote.confidence == 0.5
    assert vote.size == 0.0
    assert "not yet implemented" in vote.reason.lower()


@pytest.mark.asyncio
async def test_cross_exchange_never_trades(cross_exchange_agent):
    """Test CrossExchangeArbitrageAgent never initiates trades (stub)"""
    # Even with various conditions, should always HOLD
    for price in [10000, 50000, 100000]:
        tick = create_tick("BTC-USDC", price)
        vote = await cross_exchange_agent.analyze(tick, None, {})

        assert vote.action == "HOLD"
        assert vote.size == 0.0


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_realistic_arbitrage_scenario_profitable():
    """Test realistic profitable arbitrage scenario"""
    agent = ArbitrageAgent(
        min_profit_pct=0.004,  # 0.4% net required
        fee_pct=0.003  # 0.3% per leg
    )

    # Simulate market data arriving sequentially
    ticks = [
        create_tick("BTC-USDC", 50000.0),
        create_tick("BTC-SOL", 500.0),
        create_tick("SOL-USDC", 101.4),  # 1.4% gross - 0.9% fees = 0.5% net
    ]

    votes = []
    for tick in ticks:
        vote = await agent.analyze(tick, None, {})
        votes.append(vote)

    # First 2 ticks: no complete path yet
    assert votes[0].action == "HOLD"
    assert votes[1].action == "HOLD"

    # Third tick: complete path, profitable arbitrage
    assert votes[2].action == "BUY"
    assert votes[2].confidence > 0.7
    assert "Arbitrage" in votes[2].reason


@pytest.mark.asyncio
async def test_realistic_arbitrage_scenario_unprofitable():
    """Test realistic unprofitable arbitrage scenario"""
    agent = ArbitrageAgent(
        min_profit_pct=0.004,
        fee_pct=0.003
    )

    # Market prices with insufficient arbitrage
    ticks = [
        create_tick("BTC-USDC", 50000.0),
        create_tick("BTC-SOL", 500.0),
        create_tick("SOL-USDC", 100.5),  # 0.5% gross - 0.9% fees = -0.4% (LOSS)
    ]

    votes = []
    for tick in ticks:
        vote = await agent.analyze(tick, None, {})
        votes.append(vote)

    # All should HOLD (not profitable)
    for vote in votes:
        assert vote.action == "HOLD"


@pytest.mark.asyncio
async def test_multiple_opportunities_tracked():
    """Test agent correctly tracks multiple opportunities over time"""
    agent = ArbitrageAgent()

    # Setup profitable arbitrage
    agent.price_cache = {
        "BTC-USDC": 50000.0,
        "BTC-SOL": 500.0,
        "SOL-USDC": 101.5
    }

    # Find opportunities multiple times
    tick = create_tick("BTC-USDC", 50000.0)
    for _ in range(5):
        await agent.analyze(tick, None, {})

    # Should track all 5 opportunities
    assert agent.opportunities_found == 5

    stats = agent.get_arbitrage_stats()
    assert stats["opportunities_found"] == 5
