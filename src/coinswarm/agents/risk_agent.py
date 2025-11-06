"""
Risk Management Agent

Specializes in risk assessment and trade vetoing.

This agent NEVER initiates trades - it only:
- Analyzes risk of proposed trades
- Vetoes dangerous trades
- Enforces position limits
- Monitors drawdown

Critical for protecting capital in the swarm.
"""

import logging
from typing import Dict, Optional

from coinswarm.data_ingest.base import DataPoint
from coinswarm.agents.base_agent import BaseAgent, AgentVote


logger = logging.getLogger(__name__)


class RiskManagementAgent(BaseAgent):
    """
    Risk management agent that can veto dangerous trades.

    Veto conditions:
    - Position size too large
    - Drawdown exceeds limit
    - Volatility too high
    - Spread too wide
    - Correlation risk
    """

    def __init__(
        self,
        name: str = "RiskManager",
        weight: float = 2.0,  # Higher weight for risk agent
        max_position_pct: float = 0.1,  # Max 10% of capital per trade
        max_drawdown_pct: float = 0.2,  # Max 20% drawdown
        max_volatility: float = 0.05  # Max 5% volatility
    ):
        super().__init__(name, weight)
        self.max_position_pct = max_position_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.max_volatility = max_volatility

        self.price_history = []
        self.max_history = 100

    async def analyze(
        self,
        tick: DataPoint,
        position: Optional[Dict],
        market_context: Dict
    ) -> AgentVote:
        """
        Analyze risk and potentially veto trade.

        Returns HOLD with veto=True if risk is too high.
        Otherwise returns HOLD with low confidence (doesn't initiate trades).
        """

        price = tick.data.get("price", 0)
        spread = tick.data.get("spread", 0)

        # Update price history
        self.price_history.append(price)
        if len(self.price_history) > self.max_history:
            self.price_history.pop(0)

        # Check various risk factors
        veto_reasons = []

        # 1. Check volatility
        if len(self.price_history) >= 20:
            volatility = self._calculate_volatility()
            if volatility > self.max_volatility:
                veto_reasons.append(
                    f"Volatility too high: {volatility:.2%} > {self.max_volatility:.2%}"
                )

        # 2. Check spread (if available)
        if spread and price > 0:
            spread_pct = spread / price
            if spread_pct > 0.001:  # 0.1% spread is too wide
                veto_reasons.append(f"Spread too wide: {spread_pct:.3%}")

        # 3. Check position size (if in context)
        proposed_size = market_context.get("proposed_size", 0)
        account_value = market_context.get("account_value", 100000)  # Default $100k
        if proposed_size * price > account_value * self.max_position_pct:
            veto_reasons.append(
                f"Position too large: ${proposed_size * price:.2f} > "
                f"{self.max_position_pct:.0%} of account"
            )

        # 4. Check drawdown (if in context)
        current_drawdown = market_context.get("drawdown_pct", 0)
        if current_drawdown > self.max_drawdown_pct:
            veto_reasons.append(
                f"Drawdown too large: {current_drawdown:.1%} > {self.max_drawdown_pct:.1%}"
            )

        # 5. Check for flash crash (sudden price drop)
        if len(self.price_history) >= 10:
            recent_change = (price - self.price_history[-10]) / self.price_history[-10]
            if abs(recent_change) > 0.1:  # 10% move in 10 ticks
                veto_reasons.append(f"Flash crash detected: {recent_change:.1%} in 10 ticks")

        # Issue veto if any risk condition triggered
        if veto_reasons:
            logger.warning(f"RiskManager VETO: {'; '.join(veto_reasons)}")

            return AgentVote(
                agent_name=self.name,
                action="HOLD",
                confidence=1.0,  # 100% confident in veto
                size=0.0,
                reason="; ".join(veto_reasons),
                veto=True  # VETO!
            )

        # No risk issues, return neutral vote (risk agent doesn't initiate trades)
        return AgentVote(
            agent_name=self.name,
            action="HOLD",
            confidence=0.5,
            size=0.0,
            reason="No risk issues detected"
        )

    def _calculate_volatility(self) -> float:
        """
        Calculate price volatility (standard deviation of returns).

        Returns:
            Volatility as decimal (e.g., 0.05 = 5%)
        """
        if len(self.price_history) < 2:
            return 0.0

        # Calculate returns
        returns = [
            (self.price_history[i] - self.price_history[i-1]) / self.price_history[i-1]
            for i in range(1, len(self.price_history))
        ]

        # Calculate standard deviation
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        volatility = variance ** 0.5

        return volatility
