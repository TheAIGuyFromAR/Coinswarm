"""
Unit tests for RiskManagementAgent

This agent specializes in risk assessment and has veto power.
It NEVER initiates trades - only vetoes dangerous ones.
"""

import pytest
from datetime import datetime
from coinswarm.agents.risk_agent import RiskManagementAgent
from coinswarm.data_ingest.base import DataPoint


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def risk_agent():
    """Create RiskManagementAgent with default settings"""
    return RiskManagementAgent(
        name="RiskManager",
        weight=2.0,
        max_position_pct=0.1,  # 10% max position
        max_drawdown_pct=0.2,  # 20% max drawdown
        max_volatility=0.05  # 5% max volatility
    )


@pytest.fixture
def sample_tick():
    """Create sample DataPoint"""
    return DataPoint(
        symbol="BTC-USDC",
        timestamp=datetime.now(),
        data={
            "price": 50000.0,
            "volume": 100.0,
            "spread": 10.0  # $10 spread
        }
    )


# ============================================================================
# Initialization Tests
# ============================================================================

def test_initialization():
    """Test RiskManagementAgent initializes correctly"""
    agent = RiskManagementAgent(
        name="TestRisk",
        weight=3.0,
        max_position_pct=0.15,
        max_drawdown_pct=0.25,
        max_volatility=0.06
    )

    assert agent.name == "TestRisk"
    assert agent.weight == 3.0
    assert agent.max_position_pct == 0.15
    assert agent.max_drawdown_pct == 0.25
    assert agent.max_volatility == 0.06
    assert agent.price_history == []
    assert agent.max_history == 100


def test_default_initialization():
    """Test RiskManagementAgent with defaults"""
    agent = RiskManagementAgent()

    assert agent.name == "RiskManager"
    assert agent.weight == 2.0
    assert agent.max_position_pct == 0.1  # 10%
    assert agent.max_drawdown_pct == 0.2  # 20%
    assert agent.max_volatility == 0.05  # 5%


# ============================================================================
# Normal Operation Tests (No Veto)
# ============================================================================

@pytest.mark.asyncio
async def test_returns_hold_when_no_risk(risk_agent, sample_tick):
    """Test agent returns HOLD with no veto when all is safe"""
    market_context = {
        "proposed_size": 0.01,  # Small position
        "account_value": 100000,  # $100k account
        "drawdown_pct": 0.05  # 5% drawdown (within limit)
    }

    vote = await risk_agent.analyze(sample_tick, None, market_context)

    assert vote.action == "HOLD"
    assert vote.confidence == 0.5  # Neutral
    assert vote.size == 0.0
    assert vote.veto is False
    assert "No risk issues detected" in vote.reason


@pytest.mark.asyncio
async def test_never_initiates_trades(risk_agent, sample_tick):
    """Test risk agent NEVER votes BUY or SELL - only HOLD"""
    # Even with perfect conditions, risk agent should not initiate trades
    market_context = {
        "proposed_size": 0.001,  # Tiny position
        "account_value": 1000000,  # $1M account
        "drawdown_pct": 0.0  # No drawdown
    }

    vote = await risk_agent.analyze(sample_tick, None, market_context)

    assert vote.action == "HOLD"
    assert vote.action != "BUY"
    assert vote.action != "SELL"


@pytest.mark.asyncio
async def test_tracks_price_history(risk_agent, sample_tick):
    """Test agent updates price history on each analyze"""
    assert len(risk_agent.price_history) == 0

    await risk_agent.analyze(sample_tick, None, {})
    assert len(risk_agent.price_history) == 1
    assert risk_agent.price_history[0] == 50000.0

    # Add more ticks
    sample_tick.data["price"] = 50100.0
    await risk_agent.analyze(sample_tick, None, {})
    assert len(risk_agent.price_history) == 2
    assert risk_agent.price_history[1] == 50100.0


@pytest.mark.asyncio
async def test_price_history_max_length(risk_agent):
    """Test price history doesn't exceed max_history"""
    # Add 150 ticks (exceeds max of 100)
    for i in range(150):
        tick = DataPoint(
            symbol="BTC-USDC",
            timestamp=datetime.now(),
            data={"price": 50000 + i}
        )
        await risk_agent.analyze(tick, None, {})

    # Should only keep last 100
    assert len(risk_agent.price_history) == 100
    assert risk_agent.price_history[0] == 50050  # First 50 dropped
    assert risk_agent.price_history[-1] == 50149


# ============================================================================
# Volatility Veto Tests
# ============================================================================

@pytest.mark.asyncio
async def test_veto_on_high_volatility(risk_agent):
    """Test agent vetoes when volatility exceeds limit"""
    # Add 20 prices with high volatility
    prices = [50000, 52000, 48000, 53000, 47000, 54000, 46000, 55000, 45000, 56000,
              44000, 57000, 43000, 58000, 42000, 59000, 41000, 60000, 40000, 61000]

    for price in prices:
        tick = DataPoint(
            symbol="BTC-USDC",
            timestamp=datetime.now(),
            data={"price": price}
        )
        await risk_agent.analyze(tick, None, {})

    # Calculate volatility manually to verify
    volatility = risk_agent._calculate_volatility()
    assert volatility > risk_agent.max_volatility

    # Next tick should trigger veto
    tick = DataPoint(
        symbol="BTC-USDC",
        timestamp=datetime.now(),
        data={"price": 62000}
    )

    vote = await risk_agent.analyze(tick, None, {})

    assert vote.veto is True
    assert vote.action == "HOLD"
    assert vote.confidence == 1.0  # 100% confident in veto
    assert "Volatility too high" in vote.reason


@pytest.mark.asyncio
async def test_no_veto_on_low_volatility(risk_agent):
    """Test agent doesn't veto when volatility is acceptable"""
    # Add 20 prices with low volatility (small movements)
    prices = [50000 + i * 10 for i in range(20)]  # Gradual increase

    for price in prices:
        tick = DataPoint(
            symbol="BTC-USDC",
            timestamp=datetime.now(),
            data={"price": price}
        )
        vote = await risk_agent.analyze(tick, None, {})

    # Should not veto
    assert vote.veto is False
    assert "No risk issues detected" in vote.reason


@pytest.mark.asyncio
async def test_volatility_not_checked_with_insufficient_data(risk_agent):
    """Test volatility check skipped when less than 20 prices"""
    # Add only 10 prices with high volatility
    prices = [50000, 60000, 40000, 65000, 35000, 70000, 30000, 75000, 25000, 80000]

    for price in prices:
        tick = DataPoint(
            symbol="BTC-USDC",
            timestamp=datetime.now(),
            data={"price": price}
        )
        vote = await risk_agent.analyze(tick, None, {})

    # Should not veto (not enough data for volatility check)
    assert vote.veto is False


# ============================================================================
# Spread Veto Tests
# ============================================================================

@pytest.mark.asyncio
async def test_veto_on_wide_spread(risk_agent):
    """Test agent vetoes when spread is too wide"""
    tick = DataPoint(
        symbol="BTC-USDC",
        timestamp=datetime.now(),
        data={
            "price": 50000.0,
            "spread": 100.0  # $100 spread = 0.2% (exceeds 0.1% limit)
        }
    )

    vote = await risk_agent.analyze(tick, None, {})

    assert vote.veto is True
    assert "Spread too wide" in vote.reason


@pytest.mark.asyncio
async def test_no_veto_on_tight_spread(risk_agent, sample_tick):
    """Test agent doesn't veto when spread is acceptable"""
    sample_tick.data["spread"] = 10.0  # $10 on $50k = 0.02% (within limit)

    vote = await risk_agent.analyze(sample_tick, None, {})

    assert vote.veto is False


@pytest.mark.asyncio
async def test_handles_missing_spread(risk_agent):
    """Test agent handles missing spread data gracefully"""
    tick = DataPoint(
        symbol="BTC-USDC",
        timestamp=datetime.now(),
        data={"price": 50000.0}  # No spread field
    )

    vote = await risk_agent.analyze(tick, None, {})

    # Should not crash, should not veto based on spread
    assert vote.veto is False


# ============================================================================
# Position Size Veto Tests
# ============================================================================

@pytest.mark.asyncio
async def test_veto_on_excessive_position_size(risk_agent, sample_tick):
    """Test agent vetoes when position size exceeds limit"""
    market_context = {
        "proposed_size": 0.5,  # 0.5 BTC
        "account_value": 100000  # $100k account
    }
    # 0.5 BTC × $50k = $25k = 25% of account (exceeds 10% limit)

    vote = await risk_agent.analyze(sample_tick, None, market_context)

    assert vote.veto is True
    assert "Position too large" in vote.reason


@pytest.mark.asyncio
async def test_no_veto_on_acceptable_position_size(risk_agent, sample_tick):
    """Test agent doesn't veto when position size is safe"""
    market_context = {
        "proposed_size": 0.1,  # 0.1 BTC
        "account_value": 100000  # $100k account
    }
    # 0.1 BTC × $50k = $5k = 5% of account (within 10% limit)

    vote = await risk_agent.analyze(sample_tick, None, market_context)

    assert vote.veto is False


@pytest.mark.asyncio
async def test_handles_missing_position_data(risk_agent, sample_tick):
    """Test agent handles missing position size gracefully"""
    market_context = {}  # No proposed_size or account_value

    vote = await risk_agent.analyze(sample_tick, None, market_context)

    # Should not crash, should not veto (defaults to 0 size)
    assert vote.veto is False


# ============================================================================
# Drawdown Veto Tests
# ============================================================================

@pytest.mark.asyncio
async def test_veto_on_excessive_drawdown(risk_agent, sample_tick):
    """Test agent vetoes when drawdown exceeds limit"""
    market_context = {
        "drawdown_pct": 0.25  # 25% drawdown (exceeds 20% limit)
    }

    vote = await risk_agent.analyze(sample_tick, None, market_context)

    assert vote.veto is True
    assert "Drawdown too large" in vote.reason
    assert "25.0%" in vote.reason or "25%" in vote.reason


@pytest.mark.asyncio
async def test_no_veto_on_acceptable_drawdown(risk_agent, sample_tick):
    """Test agent doesn't veto when drawdown is within limit"""
    market_context = {
        "drawdown_pct": 0.15  # 15% drawdown (within 20% limit)
    }

    vote = await risk_agent.analyze(sample_tick, None, market_context)

    assert vote.veto is False


@pytest.mark.asyncio
async def test_handles_missing_drawdown(risk_agent, sample_tick):
    """Test agent handles missing drawdown data gracefully"""
    market_context = {}  # No drawdown_pct

    vote = await risk_agent.analyze(sample_tick, None, market_context)

    # Should not crash, should not veto (defaults to 0)
    assert vote.veto is False


# ============================================================================
# Flash Crash Veto Tests
# ============================================================================

@pytest.mark.asyncio
async def test_veto_on_flash_crash_down(risk_agent):
    """Test agent vetoes on sudden price drop (flash crash)"""
    # Add 10 stable prices around $50k
    for i in range(10):
        tick = DataPoint(
            symbol="BTC-USDC",
            timestamp=datetime.now(),
            data={"price": 50000.0}
        )
        await risk_agent.analyze(tick, None, {})

    # Sudden 15% drop
    crash_tick = DataPoint(
        symbol="BTC-USDC",
        timestamp=datetime.now(),
        data={"price": 42500.0}  # -15% from $50k
    )

    vote = await risk_agent.analyze(crash_tick, None, {})

    assert vote.veto is True
    assert "Flash crash detected" in vote.reason


@pytest.mark.asyncio
async def test_veto_on_flash_crash_up(risk_agent):
    """Test agent vetoes on sudden price spike (flash pump)"""
    # Add 10 stable prices around $50k
    for i in range(10):
        tick = DataPoint(
            symbol="BTC-USDC",
            timestamp=datetime.now(),
            data={"price": 50000.0}
        )
        await risk_agent.analyze(tick, None, {})

    # Sudden 15% spike
    spike_tick = DataPoint(
        symbol="BTC-USDC",
        timestamp=datetime.now(),
        data={"price": 57500.0}  # +15% from $50k
    )

    vote = await risk_agent.analyze(spike_tick, None, {})

    assert vote.veto is True
    assert "Flash crash detected" in vote.reason  # Uses same message for up/down


@pytest.mark.asyncio
async def test_no_veto_on_gradual_movement(risk_agent):
    """Test agent doesn't veto on gradual price movements"""
    # Add prices with gradual 8% movement over 10 ticks (below 10% threshold)
    base = 50000
    for i in range(10):
        price = base + (base * 0.08 * i / 10)  # Gradual increase
        tick = DataPoint(
            symbol="BTC-USDC",
            timestamp=datetime.now(),
            data={"price": price}
        )
        vote = await risk_agent.analyze(tick, None, {})

    # Should not veto (movement is gradual)
    assert vote.veto is False


@pytest.mark.asyncio
async def test_flash_crash_not_checked_with_insufficient_data(risk_agent):
    """Test flash crash check skipped when less than 10 prices"""
    # Add only 5 prices
    for i in range(5):
        tick = DataPoint(
            symbol="BTC-USDC",
            timestamp=datetime.now(),
            data={"price": 50000.0}
        )
        await risk_agent.analyze(tick, None, {})

    # Even with big drop, shouldn't veto (not enough history)
    crash_tick = DataPoint(
        symbol="BTC-USDC",
        timestamp=datetime.now(),
        data={"price": 40000.0}  # -20%
    )

    vote = await risk_agent.analyze(crash_tick, None, {})

    assert vote.veto is False  # Not enough data


# ============================================================================
# Multiple Veto Reasons Tests
# ============================================================================

@pytest.mark.asyncio
async def test_multiple_veto_reasons_combined(risk_agent):
    """Test agent combines multiple veto reasons"""
    # Setup: high volatility + wide spread + excessive position
    # First add prices for high volatility
    prices = [50000, 52000, 48000, 53000, 47000, 54000, 46000, 55000, 45000, 56000,
              44000, 57000, 43000, 58000, 42000, 59000, 41000, 60000, 40000, 61000]

    for price in prices:
        tick = DataPoint(
            symbol="BTC-USDC",
            timestamp=datetime.now(),
            data={"price": price}
        )
        await risk_agent.analyze(tick, None, {})

    # Now add tick with wide spread + large position + high drawdown
    tick = DataPoint(
        symbol="BTC-USDC",
        timestamp=datetime.now(),
        data={
            "price": 62000.0,
            "spread": 200.0  # Wide spread
        }
    )

    market_context = {
        "proposed_size": 1.0,  # Large position (1 BTC = $62k)
        "account_value": 100000,  # $100k account
        "drawdown_pct": 0.25  # Excessive drawdown
    }

    vote = await risk_agent.analyze(tick, None, market_context)

    assert vote.veto is True
    assert vote.confidence == 1.0
    # Should contain multiple reasons separated by "; "
    assert ";" in vote.reason  # Multiple reasons combined
    # Check that at least 2 different veto reasons present
    reason_count = vote.reason.count(";") + 1
    assert reason_count >= 2


# ============================================================================
# Volatility Calculation Tests
# ============================================================================

def test_calculate_volatility_empty_history(risk_agent):
    """Test volatility calculation with no data"""
    volatility = risk_agent._calculate_volatility()
    assert volatility == 0.0


def test_calculate_volatility_one_price(risk_agent):
    """Test volatility calculation with only one price"""
    risk_agent.price_history = [50000.0]
    volatility = risk_agent._calculate_volatility()
    assert volatility == 0.0


def test_calculate_volatility_stable_prices(risk_agent):
    """Test volatility calculation with stable prices"""
    # All same price = zero volatility
    risk_agent.price_history = [50000.0] * 20
    volatility = risk_agent._calculate_volatility()
    assert volatility == 0.0


def test_calculate_volatility_formula_correctness(risk_agent):
    """Test volatility calculation formula is correct"""
    # Simple test case: prices = [100, 110, 90, 105]
    risk_agent.price_history = [100.0, 110.0, 90.0, 105.0]

    # Manual calculation:
    # Returns: [0.1, -0.1818, 0.1667]
    # Mean: 0.0283
    # Variance: ((0.1-0.0283)^2 + (-0.1818-0.0283)^2 + (0.1667-0.0283)^2) / 3
    #         = (0.00514 + 0.04414 + 0.01914) / 3 = 0.02281
    # Volatility (sqrt): 0.1510

    volatility = risk_agent._calculate_volatility()

    # Should be around 15% volatility
    assert 0.14 < volatility < 0.16


def test_calculate_volatility_high_variance(risk_agent):
    """Test volatility calculation with high variance"""
    # Highly volatile prices
    risk_agent.price_history = [50000, 60000, 40000, 65000, 35000, 70000]

    volatility = risk_agent._calculate_volatility()

    # Should be high (>20%)
    assert volatility > 0.2


# ============================================================================
# Edge Cases
# ============================================================================

@pytest.mark.asyncio
async def test_handles_zero_price(risk_agent):
    """Test agent handles zero price gracefully"""
    tick = DataPoint(
        symbol="BTC-USDC",
        timestamp=datetime.now(),
        data={"price": 0.0}
    )

    vote = await risk_agent.analyze(tick, None, {})

    # Should not crash
    assert vote.action == "HOLD"


@pytest.mark.asyncio
async def test_handles_negative_price(risk_agent):
    """Test agent handles negative price (data error)"""
    tick = DataPoint(
        symbol="BTC-USDC",
        timestamp=datetime.now(),
        data={"price": -50000.0}
    )

    vote = await risk_agent.analyze(tick, None, {})

    # Should not crash, may or may not veto
    assert vote.action == "HOLD"


@pytest.mark.asyncio
async def test_handles_zero_account_value(risk_agent, sample_tick):
    """Test agent handles zero account value"""
    market_context = {
        "proposed_size": 0.01,
        "account_value": 0  # Blown account
    }

    vote = await risk_agent.analyze(sample_tick, None, market_context)

    # Should handle gracefully (may veto due to division by zero protection)
    assert vote.action == "HOLD"


@pytest.mark.asyncio
async def test_handles_none_position(risk_agent, sample_tick):
    """Test agent handles None position parameter"""
    vote = await risk_agent.analyze(sample_tick, None, {})

    # Should work fine (position parameter is optional)
    assert vote.action == "HOLD"


@pytest.mark.asyncio
async def test_veto_confidence_always_max(risk_agent, sample_tick):
    """Test veto always has 1.0 confidence"""
    # Trigger veto with excessive drawdown
    market_context = {
        "drawdown_pct": 0.30  # Way over limit
    }

    vote = await risk_agent.analyze(sample_tick, None, market_context)

    assert vote.veto is True
    assert vote.confidence == 1.0  # Always max confidence on veto


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_realistic_trading_scenario_safe(risk_agent):
    """Test realistic scenario where all risk checks pass"""
    # Build up price history with normal volatility
    base_price = 50000
    for i in range(30):
        price = base_price + (i * 50)  # Gradual uptrend
        tick = DataPoint(
            symbol="BTC-USDC",
            timestamp=datetime.now(),
            data={
                "price": price,
                "spread": 5.0  # Tight spread
            }
        )

        market_context = {
            "proposed_size": 0.05,  # 5% position
            "account_value": 100000,
            "drawdown_pct": 0.08  # 8% drawdown
        }

        vote = await risk_agent.analyze(tick, None, market_context)

    # Should not veto
    assert vote.veto is False
    assert vote.action == "HOLD"
    assert vote.confidence == 0.5


@pytest.mark.asyncio
async def test_realistic_trading_scenario_dangerous(risk_agent):
    """Test realistic scenario where risk checks fail"""
    # Build up volatile price history
    prices = []
    for i in range(30):
        # Simulate high volatility
        prices.append(50000 + (1000 if i % 2 == 0 else -1000))

    for price in prices:
        tick = DataPoint(
            symbol="BTC-USDC",
            timestamp=datetime.now(),
            data={
                "price": price,
                "spread": 100.0  # Wide spread during volatility
            }
        )

        market_context = {
            "proposed_size": 0.15,  # 15% position (too large)
            "account_value": 100000,
            "drawdown_pct": 0.22  # 22% drawdown (too much)
        }

        vote = await risk_agent.analyze(tick, None, market_context)

    # Should veto with multiple reasons
    assert vote.veto is True
    assert vote.confidence == 1.0
    assert ";" in vote.reason  # Multiple violations


@pytest.mark.asyncio
async def test_risk_agent_weight_is_high(risk_agent):
    """Test risk agent has high weight (important for committee voting)"""
    # Risk agent should have higher weight than regular agents
    assert risk_agent.weight >= 2.0  # At least 2.0
    assert risk_agent.weight > 1.0  # Higher than default
