"""
State Builder - Convert Market Data to State Vectors

Transforms raw market data into fixed-size state vectors for:
1. Memory similarity matching (cosine similarity)
2. Pattern clustering (k-means)
3. Agent decision making

State Vector Components (384 dimensions):
- Price features (24): normalized price, returns, volatility
- Technical indicators (80): RSI, MACD, MAs, Bollinger, ATR
- Market microstructure (40): spread, depth, volume, order flow
- Sentiment (40): news, social, funding, fear/greed
- Portfolio state (40): positions, cash, drawdown, risk
- Temporal (160): time of day, day of week, market regime embeddings
"""

import logging
from datetime import datetime

import numpy as np

logger = logging.getLogger(__name__)


class StateBuilder:
    """
    Build state vectors from market data.

    Handles:
    - Feature normalization (z-score, min-max)
    - Missing value imputation
    - Temporal encoding (cyclical features)
    - Regime embeddings
    """

    def __init__(
        self,
        state_dim: int = 384,
        normalize: bool = True,
        impute_missing: bool = True
    ):
        """
        Initialize state builder.

        Args:
            state_dim: Dimension of state vector (must be 384)
            normalize: Whether to normalize features
            impute_missing: Whether to impute missing values
        """
        if state_dim != 384:
            raise ValueError(f"State dimension must be 384, got {state_dim}")

        self.state_dim = state_dim
        self.normalize = normalize
        self.impute_missing = impute_missing

        # Feature statistics for normalization (updated online)
        self.feature_means = {}
        self.feature_stds = {}
        self.n_samples = 0

        logger.info(f"StateBuilder initialized: dim={state_dim}, normalize={normalize}")

    def build_state(
        self,
        symbol: str,
        price: float,
        market_context: dict | None = None,
        technical_indicators: dict | None = None,
        sentiment_data: dict | None = None,
        portfolio_state: dict | None = None,
        timestamp: datetime | None = None
    ) -> np.ndarray:
        """
        Build state vector from market data.

        Args:
            symbol: Trading pair (e.g., "BTC-USD")
            price: Current price
            market_context: Market microstructure data
            technical_indicators: Technical indicators
            sentiment_data: Sentiment signals
            portfolio_state: Portfolio state
            timestamp: Current timestamp (defaults to now)

        Returns:
            state: State vector (384 dimensions)
        """
        timestamp = timestamp or datetime.now()
        market_context = market_context or {}
        technical_indicators = technical_indicators or {}
        sentiment_data = sentiment_data or {}
        portfolio_state = portfolio_state or {}

        # Initialize state vector
        state = np.zeros(self.state_dim)
        idx = 0

        # ===== PRICE FEATURES (24 dims) =====
        price_features = self._extract_price_features(price, market_context)
        state[idx:idx+24] = price_features
        idx += 24

        # ===== TECHNICAL INDICATORS (80 dims) =====
        tech_features = self._extract_technical_features(technical_indicators)
        state[idx:idx+80] = tech_features
        idx += 80

        # ===== MARKET MICROSTRUCTURE (40 dims) =====
        micro_features = self._extract_microstructure_features(market_context)
        state[idx:idx+40] = micro_features
        idx += 40

        # ===== SENTIMENT (40 dims) =====
        sentiment_features = self._extract_sentiment_features(sentiment_data)
        state[idx:idx+40] = sentiment_features
        idx += 40

        # ===== PORTFOLIO STATE (40 dims) =====
        portfolio_features = self._extract_portfolio_features(portfolio_state)
        state[idx:idx+40] = portfolio_features
        idx += 40

        # ===== TEMPORAL (160 dims) =====
        temporal_features = self._extract_temporal_features(timestamp, symbol)
        state[idx:idx+160] = temporal_features
        idx += 160

        # Normalize if enabled
        if self.normalize:
            state = self._normalize_state(state)

        # Impute missing values if enabled
        if self.impute_missing:
            state = np.nan_to_num(state, nan=0.0, posinf=0.0, neginf=0.0)

        return state

    def _extract_price_features(self, price: float, market_context: dict) -> np.ndarray:
        """Extract price-based features (24 dims)"""
        features = np.zeros(24)

        # Current price (log-normalized)
        features[0] = np.log(price) if price > 0 else 0

        # Returns at different horizons
        features[1] = market_context.get("return_1h", 0.0)
        features[2] = market_context.get("return_4h", 0.0)
        features[3] = market_context.get("return_1d", 0.0)
        features[4] = market_context.get("return_7d", 0.0)
        features[5] = market_context.get("return_30d", 0.0)

        # Volatility at different horizons
        features[6] = market_context.get("volatility_1h", 0.0)
        features[7] = market_context.get("volatility_4h", 0.0)
        features[8] = market_context.get("volatility_1d", 0.0)
        features[9] = market_context.get("volatility_7d", 0.0)

        # Volume
        features[10] = np.log(market_context.get("volume_24h", 1.0))
        features[11] = market_context.get("volume_ratio", 1.0)  # vs average

        # Price levels
        features[12] = market_context.get("distance_to_52w_high", 0.0)
        features[13] = market_context.get("distance_to_52w_low", 0.0)
        features[14] = market_context.get("distance_to_30d_high", 0.0)
        features[15] = market_context.get("distance_to_30d_low", 0.0)

        # Price momentum
        features[16] = market_context.get("momentum_12h", 0.0)
        features[17] = market_context.get("momentum_1d", 0.0)
        features[18] = market_context.get("momentum_7d", 0.0)

        # Price acceleration
        features[19] = market_context.get("acceleration_1h", 0.0)
        features[20] = market_context.get("acceleration_4h", 0.0)

        # Trend strength
        features[21] = market_context.get("trend_strength", 0.0)
        features[22] = market_context.get("trend_consistency", 0.0)

        # Regime indicator
        features[23] = market_context.get("regime_score", 0.0)

        return features

    def _extract_technical_features(self, indicators: dict) -> np.ndarray:
        """Extract technical indicator features (80 dims)"""
        features = np.zeros(80)

        # RSI (multiple periods)
        features[0] = indicators.get("rsi_14", 50.0) / 100.0  # Normalize to [0,1]
        features[1] = indicators.get("rsi_7", 50.0) / 100.0
        features[2] = indicators.get("rsi_21", 50.0) / 100.0

        # MACD
        features[3] = indicators.get("macd", 0.0)
        features[4] = indicators.get("macd_signal", 0.0)
        features[5] = indicators.get("macd_histogram", 0.0)

        # Moving averages (distance from price)
        features[6] = indicators.get("ma_distance_10", 0.0)
        features[7] = indicators.get("ma_distance_20", 0.0)
        features[8] = indicators.get("ma_distance_50", 0.0)
        features[9] = indicators.get("ma_distance_100", 0.0)
        features[10] = indicators.get("ma_distance_200", 0.0)

        # MA crossovers
        features[11] = 1.0 if indicators.get("ma_10_above_20", False) else 0.0
        features[12] = 1.0 if indicators.get("ma_20_above_50", False) else 0.0
        features[13] = 1.0 if indicators.get("ma_50_above_200", False) else 0.0

        # Bollinger Bands
        features[14] = indicators.get("bb_position", 0.5)  # Position in band
        features[15] = indicators.get("bb_width", 0.0)  # Band width
        features[16] = indicators.get("bb_upper_distance", 0.0)
        features[17] = indicators.get("bb_lower_distance", 0.0)

        # ATR (volatility)
        features[18] = indicators.get("atr_14", 0.0)
        features[19] = indicators.get("atr_ratio", 1.0)  # vs historical average

        # Stochastic
        features[20] = indicators.get("stoch_k", 50.0) / 100.0
        features[21] = indicators.get("stoch_d", 50.0) / 100.0

        # ADX (trend strength)
        features[22] = indicators.get("adx", 0.0) / 100.0
        features[23] = indicators.get("di_plus", 0.0)
        features[24] = indicators.get("di_minus", 0.0)

        # CCI (Commodity Channel Index)
        features[25] = np.clip(indicators.get("cci", 0.0) / 200.0, -1, 1)

        # Williams %R
        features[26] = indicators.get("williams_r", -50.0) / 100.0

        # OBV (On-Balance Volume)
        features[27] = indicators.get("obv_trend", 0.0)

        # Additional indicators (48 dims reserved for future)
        # Can add: Ichimoku, Fibonacci levels, Pivot points, etc.

        return features

    def _extract_microstructure_features(self, market_context: dict) -> np.ndarray:
        """Extract market microstructure features (40 dims)"""
        features = np.zeros(40)

        # Bid-ask spread
        features[0] = market_context.get("bid_ask_spread_bps", 0.0)
        features[1] = market_context.get("spread_ratio", 1.0)  # vs average

        # Orderbook depth
        features[2] = np.log(market_context.get("bid_depth_1pct", 1.0))
        features[3] = np.log(market_context.get("ask_depth_1pct", 1.0))
        features[4] = market_context.get("depth_imbalance", 0.0)  # bid/ask ratio

        # Order flow
        features[5] = market_context.get("buy_volume_ratio", 0.5)
        features[6] = market_context.get("sell_volume_ratio", 0.5)
        features[7] = market_context.get("trade_intensity", 0.0)

        # Liquidity
        features[8] = market_context.get("liquidity_score", 0.0)
        features[9] = market_context.get("price_impact_1bps", 0.0)

        # Trade size distribution
        features[10] = market_context.get("avg_trade_size", 0.0)
        features[11] = market_context.get("large_trade_ratio", 0.0)

        # Additional microstructure features (28 dims reserved)

        return features

    def _extract_sentiment_features(self, sentiment: dict) -> np.ndarray:
        """Extract sentiment features (40 dims)"""
        features = np.zeros(40)

        # News sentiment
        features[0] = sentiment.get("news_sentiment", 0.0)  # -1 to 1
        features[1] = sentiment.get("news_confidence", 0.0)
        features[2] = sentiment.get("news_volume", 0.0)

        # Social sentiment
        features[3] = sentiment.get("twitter_sentiment", 0.0)
        features[4] = sentiment.get("reddit_sentiment", 0.0)
        features[5] = sentiment.get("social_volume", 0.0)

        # Funding rate
        features[6] = sentiment.get("funding_rate", 0.0)
        features[7] = sentiment.get("funding_trend", 0.0)

        # Fear & Greed
        features[8] = sentiment.get("fear_greed_index", 50.0) / 100.0

        # Long/Short ratio
        features[9] = sentiment.get("long_short_ratio", 1.0)
        features[10] = sentiment.get("ls_ratio_trend", 0.0)

        # Open Interest
        features[11] = sentiment.get("open_interest_change", 0.0)
        features[12] = sentiment.get("oi_trend", 0.0)

        # Additional sentiment features (27 dims reserved)

        return features

    def _extract_portfolio_features(self, portfolio: dict) -> np.ndarray:
        """Extract portfolio state features (40 dims)"""
        features = np.zeros(40)

        # Portfolio value
        total_value = portfolio.get("total_value", 100000.0)
        features[0] = np.log(total_value) / np.log(1000000)  # Normalize

        # Cash position
        cash = portfolio.get("cash_available", 50000.0)
        features[1] = cash / total_value if total_value > 0 else 0.5

        # Number of positions
        positions = portfolio.get("positions", {})
        features[2] = len(positions) / 10.0  # Normalize (assume max 10)

        # Largest position size
        if positions:
            max_position = max(abs(v) for v in positions.values())
            features[3] = max_position / total_value if total_value > 0 else 0
        else:
            features[3] = 0.0

        # P&L
        features[4] = portfolio.get("daily_pnl", 0.0) / total_value if total_value > 0 else 0
        features[5] = portfolio.get("weekly_pnl", 0.0) / total_value if total_value > 0 else 0
        features[6] = portfolio.get("monthly_pnl", 0.0) / total_value if total_value > 0 else 0

        # Drawdown
        features[7] = portfolio.get("drawdown", 0.0)
        features[8] = portfolio.get("max_drawdown", 0.0)

        # Risk utilization
        features[9] = portfolio.get("risk_utilization", 0.0)
        features[10] = portfolio.get("leverage", 1.0)

        # Win rate
        features[11] = portfolio.get("win_rate", 0.5)
        features[12] = portfolio.get("profit_factor", 1.0)

        # Sharpe ratio
        features[13] = np.clip(portfolio.get("sharpe_ratio", 0.0) / 3.0, -1, 1)

        # Additional portfolio features (26 dims reserved)

        return features

    def _extract_temporal_features(self, timestamp: datetime, symbol: str) -> np.ndarray:
        """Extract temporal features (160 dims)"""
        features = np.zeros(160)

        # Time of day (cyclical encoding)
        hour = timestamp.hour
        features[0] = np.sin(2 * np.pi * hour / 24)
        features[1] = np.cos(2 * np.pi * hour / 24)

        # Day of week (cyclical encoding)
        dow = timestamp.weekday()
        features[2] = np.sin(2 * np.pi * dow / 7)
        features[3] = np.cos(2 * np.pi * dow / 7)

        # Day of month (cyclical encoding)
        dom = timestamp.day
        features[4] = np.sin(2 * np.pi * dom / 31)
        features[5] = np.cos(2 * np.pi * dom / 31)

        # Month of year (cyclical encoding)
        month = timestamp.month
        features[6] = np.sin(2 * np.pi * month / 12)
        features[7] = np.cos(2 * np.pi * month / 12)

        # Is market hours (crypto = always, for stocks would matter)
        features[8] = 1.0

        # Is weekend
        features[9] = 1.0 if dow >= 5 else 0.0

        # Symbol embedding (one-hot for common pairs)
        common_symbols = ["BTC-USD", "ETH-USD", "SOL-USD", "MATIC-USD", "LINK-USD"]
        if symbol in common_symbols:
            symbol_idx = common_symbols.index(symbol)
            features[10 + symbol_idx] = 1.0

        # Additional temporal features (145 dims reserved)
        # Can add: market regime embeddings, seasonal patterns, etc.

        return features

    def _normalize_state(self, state: np.ndarray) -> np.ndarray:
        """
        Normalize state vector using online statistics.

        Uses incremental mean/std calculation (Welford's algorithm).
        """
        # Update statistics
        self.n_samples += 1
        alpha = 1.0 / self.n_samples

        for i in range(len(state)):
            feature_name = f"f{i}"

            # Initialize if first sample
            if feature_name not in self.feature_means:
                self.feature_means[feature_name] = state[i]
                self.feature_stds[feature_name] = 1.0
            else:
                # Update mean
                old_mean = self.feature_means[feature_name]
                self.feature_means[feature_name] += alpha * (state[i] - old_mean)

                # Update std (simplified)
                delta = state[i] - old_mean
                self.feature_stds[feature_name] = np.sqrt(
                    (1 - alpha) * self.feature_stds[feature_name]**2 + alpha * delta**2
                )

        # Normalize
        normalized = np.zeros_like(state)
        for i in range(len(state)):
            feature_name = f"f{i}"
            mean = self.feature_means[feature_name]
            std = max(self.feature_stds[feature_name], 1e-8)  # Avoid division by zero
            normalized[i] = (state[i] - mean) / std

        return normalized

    def __repr__(self):
        return f"StateBuilder(dim={self.state_dim}, samples={self.n_samples})"
