"""
Coinswarm Configuration Module

Centralizes all configuration settings using Pydantic for validation.
Loads from environment variables with .env file support.
"""

from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class GeneralSettings(BaseSettings):
    """General application settings"""

    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    debug: bool = False

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)


class CoinbaseSettings(BaseSettings):
    """Coinbase Advanced Trade API settings"""

    coinbase_api_key: str = ""
    coinbase_api_secret: str = ""
    coinbase_environment: Literal["sandbox", "production"] = "sandbox"
    coinbase_api_base_url: str = "https://api.coinbase.com"

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)


class AlpacaSettings(BaseSettings):
    """Alpaca Trading API settings"""

    alpaca_api_key: str = ""
    alpaca_api_secret: str = ""
    alpaca_environment: Literal["paper", "live"] = "paper"
    alpaca_api_base_url: str = "https://paper-api.alpaca.markets"

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)


class RedisSettings(BaseSettings):
    """Redis configuration for vector database and caching"""

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0
    redis_max_connections: int = 50
    redis_socket_timeout: int = 5
    redis_socket_connect_timeout: int = 5

    # Vector index configuration
    redis_vector_dim: int = 384
    redis_vector_metric: Literal["COSINE", "L2", "IP"] = "COSINE"
    redis_hnsw_m: int = 16
    redis_hnsw_ef_construction: int = 200
    redis_hnsw_ef_runtime: int = 10

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    @property
    def url(self) -> str:
        """Build Redis connection URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


class NatsSettings(BaseSettings):
    """NATS message bus configuration"""

    nats_url: str = "nats://localhost:4222"
    nats_max_reconnect_attempts: int = 10
    nats_reconnect_time_wait: int = 2

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)


class PostgresSettings(BaseSettings):
    """PostgreSQL database settings"""

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "coinswarm"
    postgres_password: str = ""
    postgres_db: str = "coinswarm"
    postgres_max_connections: int = 20

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    @property
    def url(self) -> str:
        """Build PostgreSQL connection URL"""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


class InfluxDBSettings(BaseSettings):
    """InfluxDB time-series database settings"""

    influxdb_url: str = "http://localhost:8086"
    influxdb_token: str = ""
    influxdb_org: str = "coinswarm"
    influxdb_bucket: str = "market_data"

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)


class MongoDBSettings(BaseSettings):
    """MongoDB document storage settings"""

    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db: str = "coinswarm"
    mongodb_max_pool_size: int = 100

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)


class MCPServerSettings(BaseSettings):
    """Model Context Protocol server settings"""

    mcp_server_host: str = "0.0.0.0"
    mcp_server_port: int = 3000
    mcp_server_workers: int = 4
    mcp_rate_limit_requests: int = 100
    mcp_rate_limit_period: int = 60

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)


class TradingSettings(BaseSettings):
    """Trading configuration and limits"""

    trading_mode: Literal["paper", "live"] = "paper"
    max_position_size_pct: float = 25.0
    max_order_value: float = 1000.0
    max_daily_trades: int = 50
    max_concurrent_trades: int = 5
    max_daily_loss_pct: float = 5.0
    max_drawdown_pct: float = 10.0

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)


class RiskSettings(BaseSettings):
    """Risk management settings"""

    stop_loss_default_pct: float = 2.0
    take_profit_default_pct: float = 4.0
    position_size_default: float = 100.0

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)


class MemorySettings(BaseSettings):
    """Memory system configuration"""

    memory_quorum_size: int = 3
    memory_episodic_ttl: int = 2592000  # 30 days
    memory_pattern_min_support: int = 100
    memory_pattern_min_sharpe: float = 1.0
    memory_pattern_max_drawdown: float = 10.0

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)


class AgentSettings(BaseSettings):
    """Agent configuration"""

    agent_heartbeat_interval: int = 30
    agent_max_retry_attempts: int = 3
    agent_timeout: int = 60

    # Committee agent weights
    agent_weight_trend: float = 0.30
    agent_weight_mean_rev: float = 0.25
    agent_weight_execution: float = 0.15
    agent_weight_risk: float = 0.20
    agent_weight_arbitrage: float = 0.10

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    @field_validator("agent_weight_trend", "agent_weight_mean_rev", "agent_weight_execution",
                     "agent_weight_risk", "agent_weight_arbitrage")
    @classmethod
    def validate_weights(cls, v: float) -> float:
        """Ensure weights are between 0 and 1"""
        if not 0 <= v <= 1:
            raise ValueError("Agent weights must be between 0 and 1")
        return v


class DataSourceSettings(BaseSettings):
    """External data source API keys"""

    newsapi_key: str = ""
    twitter_api_key: str = ""
    twitter_api_secret: str = ""
    twitter_bearer_token: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "Coinswarm/0.1.0"
    etherscan_api_key: str = ""
    fred_api_key: str = ""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)


class MonitoringSettings(BaseSettings):
    """Monitoring and observability settings"""

    prometheus_port: int = 9090
    grafana_port: int = 3001
    sentry_dsn: str = ""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)


class Settings(BaseSettings):
    """Master settings object combining all configuration categories"""

    general: GeneralSettings = Field(default_factory=GeneralSettings)
    coinbase: CoinbaseSettings = Field(default_factory=CoinbaseSettings)
    alpaca: AlpacaSettings = Field(default_factory=AlpacaSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    nats: NatsSettings = Field(default_factory=NatsSettings)
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    influxdb: InfluxDBSettings = Field(default_factory=InfluxDBSettings)
    mongodb: MongoDBSettings = Field(default_factory=MongoDBSettings)
    mcp_server: MCPServerSettings = Field(default_factory=MCPServerSettings)
    trading: TradingSettings = Field(default_factory=TradingSettings)
    risk: RiskSettings = Field(default_factory=RiskSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)
    data_sources: DataSourceSettings = Field(default_factory=DataSourceSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# Global settings instance
settings = Settings()
