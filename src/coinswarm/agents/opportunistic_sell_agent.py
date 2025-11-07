"""
Opportunistic Sell Agent - Tries to Sell at Peaks

This agent:
- Looks at open positions
- Tries to detect "the peak" using various heuristics
- Generates justification for each sell decision
- Stores all decisions + state in memory for pattern analysis

Goal: Learn what conditions indicate a good time to take profits.
"""

import random
from typing import Dict, Optional
from datetime import datetime

from coinswarm.agents.base_agent import BaseAgent, AgentVote
from coinswarm.data_ingest.base import DataPoint


class OpportunisticSellAgent(BaseAgent):
    """
    Agent that tries to detect peaks and sell opportunistically.

    Strategy: Look for signs that price is topping out:
    - Price reversal patterns
    - Profit targets hit
    - Momentum slowing
    - Random "this feels like the top" vibes
    """

    def __init__(
        self,
        name: str = "OpportunisticSell",
        weight: float = 1.0,
        profit_target_min: float = 0.01,   # Min 1% profit to consider selling
        profit_target_max: float = 0.15,   # Max 15% profit target
        peak_detection_threshold: float = 0.4  # 40% chance to detect "peak"
    ):
        super().__init__(name, weight)
        self.profit_target_min = profit_target_min
        self.profit_target_max = profit_target_max
        self.peak_detection_threshold = peak_detection_threshold

        # Memory: store all decisions with justifications
        self.memory = []

        # Price history for peak detection
        self.price_history = []
        self.high_history = []  # Track recent highs

    async def analyze(
        self,
        tick: DataPoint,
        position: Optional[Dict],
        market_context: Dict
    ) -> AgentVote:
        """
        Decide whether to sell based on peak detection.
        """

        # Update history
        price = tick.data.get("price", tick.data.get("close", 0))
        high = tick.data.get("high", price)

        self.price_history.append(price)
        self.high_history.append(high)

        # Keep last 100 data points
        if len(self.price_history) > 100:
            self.price_history.pop(0)
            self.high_history.pop(0)

        # Calculate market state
        state = self._calculate_market_state(tick, position)

        # Only suggest sell if we have a position
        if not position or not position.get("size", 0):
            vote = AgentVote(
                agent_name=self.name,
                action="HOLD",
                confidence=0.1,
                size=0.0,
                reason="No position to sell",
                veto=False
            )

            # Still log the non-decision
            self.memory.append({
                "timestamp": tick.timestamp,
                "price": price,
                "action": "HOLD",
                "reason": "No position",
                "state": state
            })

            return vote

        # Calculate profit on position
        entry_price = position.get("entry_price", price)
        profit_pct = (price - entry_price) / entry_price

        state["profit_pct"] = profit_pct
        state["entry_price"] = entry_price

        # Detect if this might be a peak
        is_peak = self._detect_peak(state, profit_pct)

        if is_peak:
            # Random confidence based on how convinced we are
            confidence = random.uniform(0.6, 0.95)

            # Sell entire position
            size = position.get("size", 0)

            # Generate justification
            justification = self._generate_sell_justification(state, profit_pct, confidence)

            vote = AgentVote(
                agent_name=self.name,
                action="SELL",
                confidence=confidence,
                size=size,
                reason=justification,
                veto=False
            )
        else:
            # Hold - not convinced this is the top yet
            justification = f"Holding for more upside (profit: {profit_pct:+.2%})"

            vote = AgentVote(
                agent_name=self.name,
                action="HOLD",
                confidence=0.2,
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
            "profit_pct": profit_pct,
            "state": state
        })

        return vote

    def _calculate_market_state(self, tick: DataPoint, position: Optional[Dict]) -> Dict:
        """Calculate current market state features"""

        price = tick.data.get("price", tick.data.get("close", 0))
        volume = tick.data.get("volume", 0)

        state = {
            "price": price,
            "volume": volume,
            "timestamp": tick.timestamp.isoformat()
        }

        if len(self.price_history) >= 2:
            # Recent price movement
            state["price_change_1"] = (price - self.price_history[-2]) / self.price_history[-2]

        if len(self.price_history) >= 5:
            # Check if price is falling from recent high
            recent_high = max(self.high_history[-5:])
            state["distance_from_recent_high"] = (price - recent_high) / recent_high

            # Momentum slowing?
            state["momentum_5"] = (price - self.price_history[-5]) / self.price_history[-5]

        if len(self.price_history) >= 20:
            # Long-term high
            long_high = max(self.high_history[-20:])
            state["distance_from_20_high"] = (price - long_high) / long_high

        return state

    def _detect_peak(self, state: Dict, profit_pct: float) -> bool:
        """
        Try to detect if this is a peak using various heuristics.

        Returns True if we should sell.
        """

        peak_signals = 0
        total_signals = 0

        # Signal 1: Hit profit target
        profit_target = random.uniform(self.profit_target_min, self.profit_target_max)
        total_signals += 1
        if profit_pct >= profit_target:
            peak_signals += 1

        # Signal 2: Price falling from recent high
        if "distance_from_recent_high" in state:
            total_signals += 1
            if state["distance_from_recent_high"] < -0.01:  # More than 1% off high
                peak_signals += 1

        # Signal 3: Negative momentum
        if "price_change_1" in state:
            total_signals += 1
            if state["price_change_1"] < 0:
                peak_signals += 1

        # Signal 4: At or near recent high (might reverse)
        if "distance_from_recent_high" in state:
            total_signals += 1
            if abs(state["distance_from_recent_high"]) < 0.005:  # Within 0.5% of high
                peak_signals += 1

        # Signal 5: Random intuition
        total_signals += 1
        if random.random() < self.peak_detection_threshold:
            peak_signals += 1

        # Decision: If enough signals, consider it a peak
        signal_ratio = peak_signals / total_signals if total_signals > 0 else 0

        # Need at least 60% of signals to trigger sell
        return signal_ratio >= 0.6

    def _generate_sell_justification(self, state: Dict, profit_pct: float, confidence: float) -> str:
        """
        Generate justification for selling at this "peak".
        """

        reasons = []

        # Profit level
        if profit_pct > 0.1:
            reasons.append(f"BIG PROFIT: +{profit_pct:.1%}")
        elif profit_pct > 0.05:
            reasons.append(f"good profit: +{profit_pct:.1%}")
        elif profit_pct > 0:
            reasons.append(f"small profit: +{profit_pct:.1%}")
        else:
            reasons.append(f"cutting loss: {profit_pct:.1%}")

        # Distance from high
        if "distance_from_recent_high" in state:
            if state["distance_from_recent_high"] < -0.02:
                reasons.append(f"falling from high ({state['distance_from_recent_high']:.1%})")
            elif abs(state["distance_from_recent_high"]) < 0.01:
                reasons.append("at/near recent high")

        # Momentum
        if "momentum_5" in state:
            if state["momentum_5"] < 0:
                reasons.append(f"losing momentum ({state['momentum_5']:.1%})")

        # Price action
        if "price_change_1" in state:
            if state["price_change_1"] < -0.01:
                reasons.append("price dropping")
            elif state["price_change_1"] < 0:
                reasons.append("slight reversal")

        # Random peak vibes
        vibes = [
            "feels like the top",
            "take profits now",
            "greed is the enemy",
            "better safe than sorry",
            "chart looks toppy",
            "resistance here",
            "sell in May",
            "pigs get slaughtered",
            "nobody went broke taking profit"
        ]
        reasons.append(random.choice(vibes))

        # Confidence modifier
        if confidence > 0.85:
            reasons.append("HIGH CONFIDENCE SELL")
        elif confidence < 0.7:
            reasons.append("tentative exit")

        return "; ".join(reasons)

    def get_memory(self):
        """Get all stored decisions for analysis"""
        return self.memory
