"""
Chaos Buy Agent - Makes Random Buy Decisions

This agent:
- Randomly decides to buy with varying confidence
- Considers market state (price, volume, volatility, etc.)
- Generates justification for each buy decision
- Stores all decisions + state in memory for pattern analysis

Goal: Generate thousands of random buys to discover what conditions
lead to profitable vs unprofitable trades.
"""

import random

from coinswarm.agents.base_agent import AgentVote, BaseAgent
from coinswarm.data_ingest.base import DataPoint


class ChaosBuyAgent(BaseAgent):
    """
    Agent that makes random buy decisions with justifications.

    Strategy: Pure chaos. Randomly decide to buy or not, but always
    provide reasoning based on current market state. The goal is to
    collect data on what market conditions correlate with success.
    """

    def __init__(
        self,
        name: str = "ChaosBuy",
        weight: float = 1.0,
        buy_probability: float = 0.3,  # 30% chance to suggest buy
        min_confidence: float = 0.5,
        max_confidence: float = 0.95
    ):
        super().__init__(name, weight)
        self.buy_probability = buy_probability
        self.min_confidence = min_confidence
        self.max_confidence = max_confidence

        # Memory: store all decisions with justifications
        self.memory = []

        # Price history for analysis
        self.price_history = []
        self.volume_history = []

    async def analyze(
        self,
        tick: DataPoint,
        position: dict | None,
        market_context: dict
    ) -> AgentVote:
        """
        Randomly decide to buy or not, with justification.
        """

        # Update history
        price = tick.data.get("price", tick.data.get("close", 0))
        volume = tick.data.get("volume", 0)

        self.price_history.append(price)
        self.volume_history.append(volume)

        # Keep last 100 data points
        if len(self.price_history) > 100:
            self.price_history.pop(0)
            self.volume_history.pop(0)

        # Calculate market state features
        state = self._calculate_market_state(tick)

        # Randomly decide to buy or not
        should_buy = random.random() < self.buy_probability

        if should_buy:
            # Random confidence
            confidence = random.uniform(self.min_confidence, self.max_confidence)

            # Random position size (0.5% to 5% of portfolio)
            size_pct = random.uniform(0.005, 0.05)

            # Generate justification based on current state
            justification = self._generate_buy_justification(state, confidence)

            vote = AgentVote(
                agent_name=self.name,
                action="BUY",
                confidence=confidence,
                size=size_pct,
                reason=justification,
                veto=False
            )
        else:
            # Hold - don't interfere
            justification = "Chaos agent holding this round"

            vote = AgentVote(
                agent_name=self.name,
                action="HOLD",
                confidence=0.1,
                size=0.0,
                reason=justification,
                veto=False
            )

        # Store decision + state in memory
        self.memory.append({
            "timestamp": tick.timestamp,
            "price": price,
            "action": vote.action,
            "confidence": vote.confidence,
            "size": vote.size,
            "reason": justification,
            "state": state
        })

        return vote

    def _calculate_market_state(self, tick: DataPoint) -> dict:
        """Calculate current market state features"""

        price = tick.data.get("price", tick.data.get("close", 0))
        volume = tick.data.get("volume", 0)

        state = {
            "price": price,
            "volume": volume,
            "timestamp": tick.timestamp.isoformat()
        }

        if len(self.price_history) >= 2:
            # Price momentum
            state["price_change_1"] = (price - self.price_history[-2]) / self.price_history[-2]

        if len(self.price_history) >= 10:
            avg_10 = sum(self.price_history[-10:]) / 10
            state["price_vs_sma10"] = (price - avg_10) / avg_10
            state["volatility_10"] = self._calculate_volatility(self.price_history[-10:])

        if len(self.price_history) >= 20:
            avg_20 = sum(self.price_history[-20:]) / 20
            state["price_vs_sma20"] = (price - avg_20) / avg_20

        if len(self.volume_history) >= 10:
            avg_vol_10 = sum(self.volume_history[-10:]) / 10
            state["volume_vs_avg"] = (volume - avg_vol_10) / avg_vol_10 if avg_vol_10 > 0 else 0

        return state

    def _calculate_volatility(self, prices) -> float:
        """Calculate price volatility"""
        if len(prices) < 2:
            return 0.0

        mean = sum(prices) / len(prices)
        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        return (variance ** 0.5) / mean

    def _generate_buy_justification(self, state: dict, confidence: float) -> str:
        """
        Generate a justification for buying based on current state.

        This is pseudo-random - we pick reasons based on state features
        to make the justification sound plausible.
        """

        reasons = []

        # Price momentum
        if "price_change_1" in state:
            if state["price_change_1"] > 0:
                reasons.append(f"upward momentum (+{state['price_change_1']:.2%})")
            else:
                reasons.append(f"potential bounce ({state['price_change_1']:.2%})")

        # Vs moving averages
        if "price_vs_sma10" in state:
            if state["price_vs_sma10"] > 0:
                reasons.append(f"above 10-SMA (+{state['price_vs_sma10']:.2%})")
            else:
                reasons.append(f"below 10-SMA ({state['price_vs_sma10']:.2%}) - oversold?")

        # Volume
        if "volume_vs_avg" in state:
            if state["volume_vs_avg"] > 0.2:
                reasons.append(f"high volume (+{state['volume_vs_avg']:.1%})")
            elif state["volume_vs_avg"] < -0.2:
                reasons.append(f"low volume ({state['volume_vs_avg']:.1%}) - breakout?")

        # Volatility
        if "volatility_10" in state:
            if state["volatility_10"] > 0.03:
                reasons.append(f"high volatility ({state['volatility_10']:.1%}) - opportunity")
            else:
                reasons.append(f"stable price ({state['volatility_10']:.1%}) - accumulation?")

        # Random intuition
        vibes = [
            "looks bullish",
            "feeling lucky",
            "why not",
            "FOMO kicking in",
            "gut feeling",
            "chart looks good",
            "might pump",
            "chaos theory says buy",
            "random walk to riches"
        ]
        reasons.append(random.choice(vibes))

        # Confidence modifier
        if confidence > 0.8:
            reasons.append("HIGH CONVICTION")
        elif confidence < 0.6:
            reasons.append("low conviction")

        return "; ".join(reasons)

    def get_memory(self):
        """Get all stored decisions for analysis"""
        return self.memory
