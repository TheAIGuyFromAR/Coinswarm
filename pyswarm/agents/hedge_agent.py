"""
Hedge Agent - Advanced Risk Management

Manages risk/reward ratios and hedging strategies:
- Stop losses (exit losing trades early)
- Take profit levels (lock in gains)
- Position sizing based on risk
- Hedging with correlated assets
- Portfolio rebalancing
- Risk parity allocation

Finance terms:
- Stop loss: Auto-sell if price drops X%
- Take profit: Auto-sell if price rises X%
- Hedge: Offset risk with opposite position (e.g., short futures to hedge long spot)
- Risk/reward ratio: Potential profit / potential loss (aim for 2:1 or 3:1)
- Sharpe ratio: Return / volatility (higher is better)
- Max drawdown: Largest peak-to-trough decline
- Position sizing: How much to risk per trade (e.g., 1-2% of capital)
"""

import logging
from dataclasses import dataclass

from coinswarm.agents.base_agent import AgentVote, BaseAgent
from coinswarm.data_ingest.base import DataPoint

logger = logging.getLogger(__name__)


@dataclass
class RiskParameters:
    """Risk management parameters"""
    max_position_pct: float = 0.1  # Max 10% of capital per position
    max_portfolio_risk_pct: float = 0.02  # Max 2% portfolio risk per trade
    stop_loss_pct: float = 0.02  # Stop loss at -2%
    take_profit_pct: float = 0.06  # Take profit at +6% (3:1 risk/reward)
    max_drawdown_pct: float = 0.2  # Max 20% drawdown
    min_risk_reward_ratio: float = 2.0  # Minimum 2:1 risk/reward
    correlation_threshold: float = 0.7  # Hedge if correlation > 0.7


@dataclass
class HedgeRecommendation:
    """Hedge recommendation for a position"""
    position_symbol: str
    hedge_symbol: str
    hedge_size: float
    hedge_type: str  # "short", "long", "options"
    correlation: float
    reason: str


class HedgeAgent(BaseAgent):
    """
    Hedge agent for advanced risk management.

    Key responsibilities:
    1. Monitor open positions for stop loss / take profit
    2. Calculate optimal position sizes
    3. Recommend hedges for risky positions
    4. Enforce risk/reward ratios
    5. Prevent excessive drawdowns
    """

    def __init__(
        self,
        name: str = "HedgeManager",
        weight: float = 3.0,  # Very high weight (can veto trades)
        risk_params: RiskParameters | None = None
    ):
        super().__init__(name, weight)

        self.risk_params = risk_params or RiskParameters()

        # Track positions
        self.positions: dict[str, dict] = {}

        # Correlation matrix (for hedging)
        self.correlations: dict[tuple[str, str], float] = {
            ("BTC-USD", "ETH-USD"): 0.85,  # BTC and ETH highly correlated
            ("BTC-USD", "SOL-USD"): 0.75,
            ("ETH-USD", "SOL-USD"): 0.80,
        }

    async def analyze(
        self,
        tick: DataPoint,
        position: dict | None,
        market_context: dict
    ) -> AgentVote:
        """
        Analyze risk and recommend hedges or vetoes.

        Key logic:
        1. Check if proposed trade meets risk/reward criteria
        2. Calculate optimal position size
        3. Recommend hedges if needed
        4. Veto if risk is too high
        """

        symbol = tick.symbol
        price = tick.data.get("price", 0)

        # Get account info from context
        account_value = market_context.get("account_value", 100000)
        current_drawdown = market_context.get("drawdown_pct", 0)
        proposed_action = market_context.get("proposed_action", "HOLD")
        proposed_size = market_context.get("proposed_size", 0)

        # Check drawdown limit
        if current_drawdown > self.risk_params.max_drawdown_pct:
            return AgentVote(
                agent_name=self.name,
                action="HOLD",
                confidence=1.0,
                size=0.0,
                reason=f"Max drawdown exceeded: {current_drawdown:.1%} > {self.risk_params.max_drawdown_pct:.1%}",
                veto=True
            )

        # Check position size limit
        position_value = proposed_size * price
        position_pct = position_value / account_value

        if position_pct > self.risk_params.max_position_pct:
            return AgentVote(
                agent_name=self.name,
                action="HOLD",
                confidence=1.0,
                size=0.0,
                reason=f"Position too large: {position_pct:.1%} > {self.risk_params.max_position_pct:.1%}",
                veto=True
            )

        # Calculate stop loss and take profit levels
        if proposed_action == "BUY":
            stop_loss_price = price * (1 - self.risk_params.stop_loss_pct)
            take_profit_price = price * (1 + self.risk_params.take_profit_pct)

            risk_amount = (price - stop_loss_price) * proposed_size
            reward_amount = (take_profit_price - price) * proposed_size
            risk_reward_ratio = reward_amount / risk_amount if risk_amount > 0 else 0

            # Check risk/reward ratio
            if risk_reward_ratio < self.risk_params.min_risk_reward_ratio:
                return AgentVote(
                    agent_name=self.name,
                    action="HOLD",
                    confidence=1.0,
                    size=0.0,
                    reason=f"Poor risk/reward: {risk_reward_ratio:.1f}:1 < {self.risk_params.min_risk_reward_ratio:.1f}:1",
                    veto=True
                )

        # Check for hedging opportunities
        hedge_recommendation = self._recommend_hedge(symbol, position, market_context)

        if hedge_recommendation:
            reason = f"Approved with hedge: {hedge_recommendation.reason}"
        else:
            reason = "Risk acceptable, no hedge needed"

        # Approve with adjusted size based on risk
        optimal_size = self._calculate_optimal_position_size(
            account_value,
            price,
            self.risk_params.stop_loss_pct
        )

        # Return approval (not a veto)
        return AgentVote(
            agent_name=self.name,
            action="HOLD",  # Hedge agent doesn't initiate trades
            confidence=0.7,
            size=min(optimal_size, proposed_size),  # Suggest smaller size if needed
            reason=reason
        )

    def _calculate_optimal_position_size(
        self,
        account_value: float,
        price: float,
        stop_loss_pct: float
    ) -> float:
        """
        Calculate optimal position size using fixed fractional position sizing.

        Formula:
        Position size = (Account value × Risk per trade) / (Entry price × Stop loss %)

        Example:
        - Account: $100,000
        - Risk per trade: 2% = $2,000
        - Entry: $50,000 (BTC)
        - Stop loss: 2% = $1,000 per BTC
        - Position size: $2,000 / $1,000 = 2 BTC → $100,000 position (too large!)
        - Cap at max_position_pct: 10% = 0.2 BTC
        """

        # Max risk per trade
        max_risk = account_value * self.risk_params.max_portfolio_risk_pct

        # Risk per unit
        risk_per_unit = price * stop_loss_pct

        # Optimal size (units)
        optimal_size = max_risk / risk_per_unit if risk_per_unit > 0 else 0

        # Cap at max position percentage
        max_size_by_value = (account_value * self.risk_params.max_position_pct) / price

        return min(optimal_size, max_size_by_value)

    def _recommend_hedge(
        self,
        symbol: str,
        position: dict | None,
        market_context: dict
    ) -> HedgeRecommendation | None:
        """
        Recommend hedge for position if correlation risk is high.

        Hedging strategies:
        1. Short correlated asset (e.g., short ETH to hedge long BTC)
        2. Buy put options (if available)
        3. Inverse futures
        """

        if not position:
            return None

        # Check correlation with other assets
        for (asset1, asset2), correlation in self.correlations.items():
            if asset1 == symbol and correlation > self.risk_params.correlation_threshold:
                # High correlation → hedge with asset2
                hedge_size = position.get("size", 0) * correlation

                return HedgeRecommendation(
                    position_symbol=symbol,
                    hedge_symbol=asset2,
                    hedge_size=hedge_size,
                    hedge_type="short",
                    correlation=correlation,
                    reason=f"Hedge {symbol} with short {asset2} (corr={correlation:.2f})"
                )

        return None

    def check_stop_loss(self, symbol: str, current_price: float, position: dict) -> bool:
        """
        Check if position should be stopped out.

        Returns:
            True if stop loss triggered, False otherwise
        """

        entry_price = position.get("entry_price", 0)
        action = position.get("action", "BUY")

        if action == "BUY":
            # Long position: stop if price drops below stop loss
            stop_loss_price = entry_price * (1 - self.risk_params.stop_loss_pct)
            if current_price <= stop_loss_price:
                logger.warning(
                    f"STOP LOSS triggered for {symbol}: "
                    f"${current_price:.2f} <= ${stop_loss_price:.2f} "
                    f"(-{self.risk_params.stop_loss_pct:.1%})"
                )
                return True

        else:  # SELL / short position
            # Short position: stop if price rises above stop loss
            stop_loss_price = entry_price * (1 + self.risk_params.stop_loss_pct)
            if current_price >= stop_loss_price:
                logger.warning(
                    f"STOP LOSS triggered for {symbol}: "
                    f"${current_price:.2f} >= ${stop_loss_price:.2f} "
                    f"(+{self.risk_params.stop_loss_pct:.1%})"
                )
                return True

        return False

    def check_take_profit(self, symbol: str, current_price: float, position: dict) -> bool:
        """
        Check if position should take profit.

        Returns:
            True if take profit triggered, False otherwise
        """

        entry_price = position.get("entry_price", 0)
        action = position.get("action", "BUY")

        if action == "BUY":
            # Long position: take profit if price rises above target
            take_profit_price = entry_price * (1 + self.risk_params.take_profit_pct)
            if current_price >= take_profit_price:
                logger.info(
                    f"TAKE PROFIT triggered for {symbol}: "
                    f"${current_price:.2f} >= ${take_profit_price:.2f} "
                    f"(+{self.risk_params.take_profit_pct:.1%})"
                )
                return True

        else:  # SELL / short position
            # Short position: take profit if price drops below target
            take_profit_price = entry_price * (1 - self.risk_params.take_profit_pct)
            if current_price <= take_profit_price:
                logger.info(
                    f"TAKE PROFIT triggered for {symbol}: "
                    f"${current_price:.2f} <= ${take_profit_price:.2f} "
                    f"(-{self.risk_params.take_profit_pct:.1%})"
                )
                return True

        return False

    def calculate_risk_reward_ratio(self, entry_price: float, action: str) -> dict:
        """
        Calculate risk/reward ratio for a trade.

        Returns:
            Dict with stop_loss_price, take_profit_price, risk_amount, reward_amount, ratio
        """

        if action == "BUY":
            stop_loss_price = entry_price * (1 - self.risk_params.stop_loss_pct)
            take_profit_price = entry_price * (1 + self.risk_params.take_profit_pct)

            risk_amount = entry_price - stop_loss_price
            reward_amount = take_profit_price - entry_price

        else:  # SELL
            stop_loss_price = entry_price * (1 + self.risk_params.stop_loss_pct)
            take_profit_price = entry_price * (1 - self.risk_params.take_profit_pct)

            risk_amount = stop_loss_price - entry_price
            reward_amount = entry_price - take_profit_price

        ratio = reward_amount / risk_amount if risk_amount > 0 else 0

        return {
            "stop_loss_price": stop_loss_price,
            "take_profit_price": take_profit_price,
            "risk_amount": risk_amount,
            "reward_amount": reward_amount,
            "risk_reward_ratio": ratio
        }

    def update_position(self, symbol: str, position: dict):
        """Update tracked position"""
        self.positions[symbol] = position

    def remove_position(self, symbol: str):
        """Remove closed position"""
        if symbol in self.positions:
            del self.positions[symbol]

    def get_portfolio_risk(self) -> dict:
        """
        Calculate total portfolio risk.

        Returns:
            Dict with total_risk_pct, position_count, largest_position
        """

        if not self.positions:
            return {
                "total_risk_pct": 0.0,
                "position_count": 0,
                "largest_position": None
            }

        # Sum risk across all positions
        total_risk = sum(
            pos.get("size", 0) * pos.get("entry_price", 0) * self.risk_params.stop_loss_pct
            for pos in self.positions.values()
        )

        # Largest position
        largest_pos = max(
            self.positions.items(),
            key=lambda x: x[1].get("size", 0) * x[1].get("entry_price", 0)
        )

        return {
            "total_risk_amount": total_risk,
            "position_count": len(self.positions),
            "largest_position": largest_pos[0],
            "largest_position_value": largest_pos[1].get("size", 0) * largest_pos[1].get("entry_price", 0)
        }
