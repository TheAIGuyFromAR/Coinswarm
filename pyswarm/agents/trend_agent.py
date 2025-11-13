"""
Trend Following Agent

Specializes in identifying and riding price trends.

Strategy:
- Analyzes price momentum
- Buys on uptrends
- Sells on downtrends
- Uses moving averages and RSI
"""

import logging

from coinswarm.agents.base_agent import AgentVote, BaseAgent
from coinswarm.data_ingest.base import DataPoint

logger = logging.getLogger(__name__)


class TrendFollowingAgent(BaseAgent):
    """
    Trend following agent using momentum indicators.

    Indicators:
    - Price momentum (% change)
    - Moving average crossover
    - RSI (Relative Strength Index)
    - Volume confirmation
    """

    def __init__(self, name: str = "TrendFollower", weight: float = 1.0):
        super().__init__(name, weight)
        self.price_history = []  # Recent prices
        self.max_history = 100  # Keep last 100 prices

    async def analyze(
        self,
        tick: DataPoint,
        position: dict | None,
        market_context: dict
    ) -> AgentVote:
        """
        Analyze trend and return vote.

        Logic:
        1. Calculate price momentum
        2. Check moving average crossover
        3. Confirm with volume
        4. Return BUY on strong uptrend, SELL on strong downtrend
        """

        price = tick.data.get("price", 0)
        tick.data.get("volume", 0)

        # Update price history
        self.price_history.append(price)
        if len(self.price_history) > self.max_history:
            self.price_history.pop(0)

        # Need at least 20 prices for analysis
        if len(self.price_history) < 20:
            return AgentVote(
                agent_name=self.name,
                action="HOLD",
                confidence=0.5,
                size=0.0,
                reason="Insufficient data for trend analysis"
            )

        # Calculate indicators
        momentum = self._calculate_momentum()
        ma_signal = self._calculate_ma_crossover()
        rsi = self._calculate_rsi()

        # Determine action
        if momentum > 0.02 and ma_signal == "BUY" and rsi < 70:
            # Strong uptrend, not overbought
            confidence = min(0.9, momentum * 10)  # Scale momentum to confidence
            size = self._calculate_position_size(confidence, position)

            return AgentVote(
                agent_name=self.name,
                action="BUY",
                confidence=confidence,
                size=size,
                reason=f"Uptrend: momentum={momentum:.2%}, RSI={rsi:.1f}"
            )

        elif momentum < -0.02 and ma_signal == "SELL" and rsi > 30:
            # Strong downtrend, not oversold
            confidence = min(0.9, abs(momentum) * 10)
            size = self._calculate_position_size(confidence, position)

            return AgentVote(
                agent_name=self.name,
                action="SELL",
                confidence=confidence,
                size=size,
                reason=f"Downtrend: momentum={momentum:.2%}, RSI={rsi:.1f}"
            )

        else:
            # No clear trend or overbought/oversold
            return AgentVote(
                agent_name=self.name,
                action="HOLD",
                confidence=0.6,
                size=0.0,
                reason=f"No clear trend: momentum={momentum:.2%}, RSI={rsi:.1f}"
            )

    def _calculate_momentum(self) -> float:
        """Calculate price momentum (% change over last 10 periods)"""
        if len(self.price_history) < 10:
            return 0.0

        old_price = self.price_history[-10]
        new_price = self.price_history[-1]

        return (new_price - old_price) / old_price

    def _calculate_ma_crossover(self) -> str:
        """
        Calculate moving average crossover signal.

        Returns:
            "BUY" if fast MA > slow MA (golden cross)
            "SELL" if fast MA < slow MA (death cross)
            "HOLD" otherwise
        """
        if len(self.price_history) < 50:
            return "HOLD"

        # Fast MA (10 period)
        fast_ma = sum(self.price_history[-10:]) / 10

        # Slow MA (50 period)
        slow_ma = sum(self.price_history[-50:]) / 50

        if fast_ma > slow_ma * 1.01:  # 1% threshold
            return "BUY"
        elif fast_ma < slow_ma * 0.99:
            return "SELL"
        else:
            return "HOLD"

    def _calculate_rsi(self, period: int = 14) -> float:
        """
        Calculate Relative Strength Index.

        Returns:
            RSI value (0-100)
            > 70 = overbought
            < 30 = oversold
        """
        if len(self.price_history) < period + 1:
            return 50.0  # Neutral

        # Calculate price changes
        changes = [
            self.price_history[i] - self.price_history[i-1]
            for i in range(-period, 0)
        ]

        # Separate gains and losses
        gains = [c for c in changes if c > 0]
        losses = [abs(c) for c in changes if c < 0]

        # Average gain and loss
        avg_gain = sum(gains) / period if gains else 0.0
        avg_loss = sum(losses) / period if losses else 0.0

        # Calculate RSI
        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _calculate_position_size(
        self,
        confidence: float,
        position: dict | None
    ) -> float:
        """
        Calculate position size based on confidence.

        Returns:
            Position size (e.g., 0.01 BTC)
        """

        # Base size (adjust based on your capital)
        base_size = 0.01

        # Scale by confidence
        size = base_size * confidence

        # If already in position, reduce size
        if position:
            size *= 0.5

        return round(size, 4)
