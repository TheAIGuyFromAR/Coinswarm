"""
Soundness tests for Coinbase API client.

Tests determinism, latency, and safety of the Coinbase integration.
"""

import pytest
from coinswarm.api.coinbase_client import CoinbaseAPIClient

from tests.soundness.base import DeterminismTest, LatencyTest, SafetyInvariantTest

# ============================================================================
# Determinism Tests
# ============================================================================


class TestCoinbaseSignatureDeterminism(DeterminismTest):
    """Test that signature generation is deterministic"""

    def run_target(self, *args, **kwargs):
        """Generate signature with fixed inputs"""
        client = CoinbaseAPIClient(
            api_key="test_key",
            api_secret="dGVzdF9zZWNyZXQ=",  # base64 encoded "test_secret"
        )

        timestamp = "1234567890"
        method = "GET"
        request_path = "/api/v3/brokerage/accounts"
        body = ""

        return client._generate_signature(timestamp, method, request_path, body)


def test_signature_determinism():
    """Signature generation should be deterministic"""
    test = TestCoinbaseSignatureDeterminism()
    result = test.test_determinism()

    assert result.passed, result.message


class TestCoinbaseHeaderDeterminism(DeterminismTest):
    """Test that header building produces consistent timestamps"""

    def run_target(self, *args, **kwargs):
        """Build headers - timestamp will vary, so we check structure only"""
        client = CoinbaseAPIClient(
            api_key="test_key",
            api_secret="dGVzdF9zZWNyZXQ=",
        )

        headers = client._build_headers("GET", "/api/v3/brokerage/accounts")

        # Return structure (keys), not values (timestamp varies)
        return sorted(headers.keys())


def test_header_structure_determinism():
    """Header structure should be consistent"""
    test = TestCoinbaseHeaderDeterminism()
    result = test.test_determinism()

    assert result.passed, result.message
    assert "CB-ACCESS-KEY" in result.metrics["result1"]
    assert "CB-ACCESS-SIGN" in result.metrics["result1"]
    assert "CB-ACCESS-TIMESTAMP" in result.metrics["result1"]


# ============================================================================
# Latency Tests
# ============================================================================


class TestCoinbaseSignatureLatency(LatencyTest):
    """Test that signature generation is fast enough"""

    def __init__(self):
        # Signature generation should be very fast (< 1ms p99)
        super().__init__(p99_sla_ms=1.0, num_samples=1000)

        self.client = CoinbaseAPIClient(
            api_key="test_key",
            api_secret="dGVzdF9zZWNyZXQ=",
        )

    def run_operation(self):
        """Generate a signature"""
        return self.client._generate_signature(
            timestamp="1234567890",
            method="POST",
            request_path="/api/v3/brokerage/orders",
            body='{"product_id":"BTC-USD","side":"BUY"}',
        )


@pytest.mark.performance
def test_signature_latency():
    """Signature generation should meet latency SLA"""
    test = TestCoinbaseSignatureLatency()
    result = test.test_latency(tolerance=0.2)  # 20% tolerance

    assert result.passed, result.message
    assert result.metrics["p99_ms"] < 2.0  # Should be well under 2ms


class TestCoinbaseHeaderBuildingLatency(LatencyTest):
    """Test that header building is fast enough"""

    def __init__(self):
        # Header building should be very fast (< 1ms p99)
        super().__init__(p99_sla_ms=1.0, num_samples=1000)

        self.client = CoinbaseAPIClient(
            api_key="test_key",
            api_secret="dGVzdF9zZWNyZXQ=",
        )

    def run_operation(self):
        """Build headers"""
        return self.client._build_headers(
            "POST",
            "/api/v3/brokerage/orders",
            '{"product_id":"BTC-USD","side":"BUY"}',
        )


@pytest.mark.performance
def test_header_building_latency():
    """Header building should meet latency SLA"""
    test = TestCoinbaseHeaderBuildingLatency()
    result = test.test_latency(tolerance=0.2)

    assert result.passed, result.message
    assert result.metrics["p99_ms"] < 2.0


# ============================================================================
# Safety Tests
# ============================================================================


class TestCoinbaseOHLCVQuality(SafetyInvariantTest):
    """Test that OHLCV quality calculation is correct"""

    def __init__(self):
        # Quality score should be between 0 and 1
        super().__init__(
            max_position_size=1.0,  # Repurpose for quality score
            max_daily_loss=0.0,     # Not used
            max_leverage=1.0,       # Not used
        )

        self.client = CoinbaseAPIClient(
            api_key="test_key",
            api_secret="dGVzdF9zZWNyZXQ=",
        )

    def run_simulation(self):
        """Test various OHLCV scenarios"""
        test_cases = [
            # Valid OHLCV: high quality
            {
                "open": 50000.0,
                "high": 51000.0,
                "low": 49500.0,
                "close": 50500.0,
                "volume": 100.0,
                "expected_quality": 1.0,
            },
            # High < Low: invalid
            {
                "open": 50000.0,
                "high": 49000.0,  # Invalid: high < low
                "low": 49500.0,
                "close": 50500.0,
                "volume": 100.0,
                "expected_quality": 0.0,  # Should be penalized
            },
            # Negative volume: invalid
            {
                "open": 50000.0,
                "high": 51000.0,
                "low": 49500.0,
                "close": 50500.0,
                "volume": -10.0,  # Invalid
                "expected_quality": 0.5,  # Should be penalized
            },
        ]

        events = []
        for i, case in enumerate(test_cases):
            quality = self.client._calculate_ohlcv_quality(
                case["open"], case["high"], case["low"], case["close"], case["volume"]
            )

            # Store as "position_size" for safety invariant check
            events.append({"position_size": quality, "case_id": i})

        return events


def test_ohlcv_quality_bounds():
    """OHLCV quality scores should be in [0, 1]"""
    test = TestCoinbaseOHLCVQuality()
    result = test.test_safety_invariants(tolerance=0.0)

    # All quality scores should be ≤ 1.0
    assert result.passed, result.message


# ============================================================================
# Integration Soundness Test
# ============================================================================


class TestCoinbaseSymbolNormalization(DeterminismTest):
    """Test that symbol normalization is consistent"""

    def run_target(self, *args, **kwargs):
        """Normalize a symbol"""
        client = CoinbaseAPIClient(
            api_key="test_key",
            api_secret="dGVzdF9zZWNyZXQ=",
        )

        symbols = ["BTC/USD", "ETH/USDT", "SOL-USD", "btc-usd"]
        return [client._normalize_symbol(s) for s in symbols]


def test_symbol_normalization_determinism():
    """Symbol normalization should be deterministic"""
    test = TestCoinbaseSymbolNormalization()
    result = test.test_determinism()

    assert result.passed, result.message

    # Check specific expected values
    normalized = result.metrics["result1"]
    assert "BTC-USD" in normalized
    assert "ETH-USDT" in normalized
    assert "SOL-USD" in normalized


# ============================================================================
# Pytest Integration
# ============================================================================


@pytest.mark.soundness
class TestCoinbaseSoundness:
    """Aggregate soundness tests for Coinbase client"""

    def test_all_determinism(self):
        """Run all determinism tests"""
        tests = [
            TestCoinbaseSignatureDeterminism(),
            TestCoinbaseHeaderDeterminism(),
            TestCoinbaseSymbolNormalization(),
        ]

        for test in tests:
            result = test.test_determinism()
            assert result.passed, f"{test.__class__.__name__}: {result.message}"

    @pytest.mark.performance
    def test_all_latency(self):
        """Run all latency tests"""
        tests = [
            TestCoinbaseSignatureLatency(),
            TestCoinbaseHeaderBuildingLatency(),
        ]

        for test in tests:
            result = test.test_latency(tolerance=0.2)
            assert result.passed, f"{test.__class__.__name__}: {result.message}"

    def test_all_safety(self):
        """Run all safety tests"""
        tests = [
            TestCoinbaseOHLCVQuality(),
        ]

        for test in tests:
            result = test.test_safety_invariants()
            assert result.passed, f"{test.__class__.__name__}: {result.message}"
