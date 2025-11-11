"""
Unit tests for configuration module

Tests configuration loading and validation.
"""

import pytest
from pydantic import ValidationError

from coinswarm.core.config import (
    Settings,
    CoinbaseSettings,
    RedisSettings,
    TradingSettings,
    AgentSettings,
)


class TestCoinbaseSettings:
    """Test Coinbase settings"""

    def test_default_values(self):
        """Test default configuration values"""
        settings = CoinbaseSettings()
        assert settings.coinbase_environment == "sandbox"
        assert settings.coinbase_api_base_url == "https://api.coinbase.com"

    def test_custom_values(self):
        """Test custom configuration values"""
        settings = CoinbaseSettings(
            coinbase_api_key="test_key",
            coinbase_api_secret="test_secret",
            coinbase_environment="production",
        )
        assert settings.coinbase_api_key == "test_key"
        assert settings.coinbase_api_secret == "test_secret"
        assert settings.coinbase_environment == "production"


class TestRedisSettings:
    """Test Redis settings"""

    def test_default_values(self):
        """Test default Redis configuration"""
        settings = RedisSettings()
        assert settings.redis_host == "localhost"
        assert settings.redis_port == 6379
        assert settings.redis_vector_dim == 384
        assert settings.redis_vector_metric == "COSINE"

    def test_url_generation_without_password(self):
        """Test Redis URL generation without password"""
        settings = RedisSettings(redis_host="localhost", redis_port=6379, redis_db=0)
        assert settings.url == "redis://localhost:6379/0"

    def test_url_generation_with_password(self):
        """Test Redis URL generation with password"""
        settings = RedisSettings(
            redis_host="localhost",
            redis_port=6379,
            redis_db=0,
            redis_password="secret123",
        )
        assert settings.url == "redis://:secret123@localhost:6379/0"


class TestTradingSettings:
    """Test trading settings"""

    def test_default_values(self):
        """Test default trading configuration"""
        settings = TradingSettings()
        assert settings.trading_mode == "paper"
        assert settings.max_position_size_pct == 25.0
        assert settings.max_order_value == 1000.0
        assert settings.max_daily_trades == 50
        assert settings.max_concurrent_trades == 5

    def test_risk_limits(self):
        """Test risk limit configuration"""
        settings = TradingSettings()
        assert settings.max_daily_loss_pct == 5.0
        assert settings.max_drawdown_pct == 10.0


class TestAgentSettings:
    """Test agent settings"""

    def test_default_weights(self):
        """Test default agent weights"""
        settings = AgentSettings()
        assert settings.agent_weight_trend == 0.30
        assert settings.agent_weight_mean_rev == 0.25
        assert settings.agent_weight_execution == 0.15
        assert settings.agent_weight_risk == 0.20
        assert settings.agent_weight_arbitrage == 0.10

    def test_weights_sum_to_one(self):
        """Test that default weights sum to 1.0"""
        settings = AgentSettings()
        total = (
            settings.agent_weight_trend
            + settings.agent_weight_mean_rev
            + settings.agent_weight_execution
            + settings.agent_weight_risk
            + settings.agent_weight_arbitrage
        )
        assert abs(total - 1.0) < 0.001  # Allow for floating point precision

    def test_invalid_weight_raises_error(self):
        """Test that weights outside [0, 1] raise validation error"""
        with pytest.raises(ValidationError):
            AgentSettings(agent_weight_trend=1.5)

        with pytest.raises(ValidationError):
            AgentSettings(agent_weight_mean_rev=-0.1)


class TestSettings:
    """Test master Settings object"""

    def test_initialization(self):
        """Test Settings initialization"""
        settings = Settings()

        # Check all sub-settings are initialized
        assert hasattr(settings, "general")
        assert hasattr(settings, "coinbase")
        assert hasattr(settings, "redis")
        assert hasattr(settings, "trading")
        assert hasattr(settings, "agent")

    def test_nested_access(self):
        """Test accessing nested configuration"""
        settings = Settings()

        # Access nested values
        assert settings.redis.redis_host == "localhost"
        assert settings.trading.trading_mode == "paper"
        assert settings.agent.agent_weight_trend == 0.30

    def test_postgres_url_generation(self):
        """Test PostgreSQL URL generation"""
        from coinswarm.core.config import PostgresSettings

        settings = PostgresSettings(
            postgres_host="localhost",
            postgres_port=5432,
            postgres_user="coinswarm",
            postgres_password="test_pass",
            postgres_db="coinswarm",
        )

        expected_url = "postgresql://coinswarm:test_pass@localhost:5432/coinswarm"
        assert settings.url == expected_url
