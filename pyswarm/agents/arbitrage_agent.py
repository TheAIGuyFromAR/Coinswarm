"""
Arbitrage Agent

Detects and executes triangular arbitrage opportunities.

Example:
1. Buy BTC with USDC @ $50,000
2. Sell BTC for SOL @ 1 BTC = 1000 SOL
3. Sell SOL for USDC @ $50.10 each = $50,100
4. Profit: $100 (0.2%)
5. After fees (0.3%): -$50 (LOSS ❌)

Need >0.4% spread to profit after fees!

Types of arbitrage:
1. Triangular (BTC→SOL→USDC→BTC)
2. Cross-exchange (Binance vs Coinbase)
3. Funding rate (spot vs futures)
"""

import logging

from coinswarm.agents.base_agent import AgentVote, BaseAgent
from coinswarm.data_ingest.base import DataPoint

logger = logging.getLogger(__name__)


class ArbitrageAgent(BaseAgent):
    """
    Arbitrage detection agent.

    Monitors price differences across pairs to find profitable trades.

    Strategy:
    - Continuously monitor all pairs
    - Calculate theoretical profit from triangular arbitrage
    - Execute if profit > min_profit_threshold (after fees)
    - Fast execution required (<1 second for all legs)
    """

    def __init__(
        self,
        name: str = "ArbitrageAgent",
        weight: float = 2.0,  # High weight (arbitrage is low risk)
        min_profit_pct: float = 0.004,  # 0.4% minimum profit
        fee_pct: float = 0.003  # 0.3% fee per trade (3 trades = 0.9% total)
    ):
        super().__init__(name, weight)

        self.min_profit_pct = min_profit_pct
        self.fee_pct = fee_pct
        self.total_fee_pct = fee_pct * 3  # 3 legs = 3× fees

        # Price cache for arbitrage calculation
        self.price_cache: dict[str, float] = {}

        # Arbitrage opportunities found
        self.opportunities_found = 0
        self.opportunities_executed = 0

    async def analyze(
        self,
        tick: DataPoint,
        position: dict | None,
        market_context: dict
    ) -> AgentVote:
        """
        Analyze for arbitrage opportunities.

        Process:
        1. Update price cache with latest tick
        2. Check all triangular arbitrage paths
        3. Calculate theoretical profit
        4. Return BUY vote if profit > threshold
        """

        symbol = tick.symbol
        price = tick.data.get("price", 0)

        # Update price cache
        self.price_cache[symbol] = price

        # Check for arbitrage opportunities
        opportunity = self._find_best_arbitrage()

        if opportunity:
            path, profit_pct, expected_return = opportunity

            # Check if profitable after fees
            net_profit_pct = profit_pct - self.total_fee_pct

            if net_profit_pct >= self.min_profit_pct:
                self.opportunities_found += 1

                return AgentVote(
                    agent_name=self.name,
                    action="BUY",  # Start arbitrage sequence
                    confidence=min(0.95, 0.7 + (net_profit_pct * 10)),  # Higher profit = higher confidence
                    size=0.01,  # Arbitrage size (1% of capital)
                    reason=f"Arbitrage: {' → '.join(path)} = {net_profit_pct:.2%} profit (after fees)"
                )

        # No opportunity found
        return AgentVote(
            agent_name=self.name,
            action="HOLD",
            confidence=0.5,
            size=0.0,
            reason="No arbitrage opportunities found"
        )

    def _find_best_arbitrage(self) -> tuple[list[str], float, float] | None:
        """
        Find best triangular arbitrage opportunity.

        Checks all possible paths:
        1. BTC → SOL → USDC → BTC
        2. BTC → ETH → USDC → BTC
        3. ETH → SOL → USDC → ETH
        4. BTC → ETH → SOL → BTC
        etc.

        Returns:
            (path, profit_pct, expected_return) or None
        """

        opportunities = []

        # Path 1: BTC → SOL → USDC → BTC
        path1 = self._calculate_triangular_arbitrage(
            start="BTC-USDC",
            leg1="BTC-SOL",
            leg2="SOL-USDC",
            end="BTC-USDC"
        )
        if path1:
            opportunities.append(path1)

        # Path 2: BTC → ETH → USDC → BTC
        path2 = self._calculate_triangular_arbitrage(
            start="BTC-USDC",
            leg1="ETH-BTC",  # Inverse (sell BTC for ETH)
            leg2="ETH-USDC",
            end="BTC-USDC"
        )
        if path2:
            opportunities.append(path2)

        # Path 3: ETH → SOL → USDC → ETH
        path3 = self._calculate_triangular_arbitrage(
            start="ETH-USDC",
            leg1="ETH-SOL",
            leg2="SOL-USDC",
            end="ETH-USDC"
        )
        if path3:
            opportunities.append(path3)

        # Path 4: SOL → BTC → ETH → SOL (complex)
        path4 = self._calculate_complex_arbitrage(
            start="SOL-USDC",
            leg1="BTC-SOL",
            leg2="ETH-BTC",
            leg3="ETH-SOL",
            end="SOL-USDC"
        )
        if path4:
            opportunities.append(path4)

        # Return best opportunity
        if opportunities:
            return max(opportunities, key=lambda x: x[1])  # Max profit_pct

        return None

    def _calculate_triangular_arbitrage(
        self,
        start: str,
        leg1: str,
        leg2: str,
        end: str
    ) -> tuple[list[str], float, float] | None:
        """
        Calculate profit from triangular arbitrage.

        Example:
        start = BTC-USDC (buy BTC with $50,000 USDC)
        leg1 = BTC-SOL (sell 1 BTC for 1000 SOL)
        leg2 = SOL-USDC (sell 1000 SOL for $50,100 USDC)
        end = BTC-USDC (compare to starting $50,000)

        Profit = ($50,100 - $50,000) / $50,000 = 0.2%
        """

        # Check if all prices are available
        if not all(p in self.price_cache for p in [start, leg1, leg2]):
            return None

        try:
            # Starting amount (e.g., $50,000 USDC)
            start_amount = 50000

            # Leg 1: Buy BTC with USDC
            start_price = self.price_cache[start]  # $50,000 per BTC
            btc_amount = start_amount / start_price  # 1 BTC

            # Leg 2: Sell BTC for SOL
            leg1_price = self.price_cache[leg1]  # 1 BTC = 1000 SOL
            sol_amount = btc_amount * leg1_price  # 1000 SOL

            # Leg 3: Sell SOL for USDC
            leg2_price = self.price_cache[leg2]  # $50.10 per SOL
            end_amount = sol_amount * leg2_price  # $50,100 USDC

            # Calculate profit
            profit = end_amount - start_amount  # $100
            profit_pct = profit / start_amount  # 0.2%

            path = [start, leg1, leg2, end]

            return (path, profit_pct, end_amount)

        except Exception as e:
            logger.debug(f"Error calculating arbitrage: {e}")
            return None

    def _calculate_complex_arbitrage(
        self,
        start: str,
        leg1: str,
        leg2: str,
        leg3: str,
        end: str
    ) -> tuple[list[str], float, float] | None:
        """
        Calculate profit from 4-leg arbitrage.

        Example:
        SOL → BTC → ETH → SOL → USDC

        More complex but can find opportunities missed by simple triangular.
        """

        # Check if all prices are available
        if not all(p in self.price_cache for p in [start, leg1, leg2, leg3]):
            return None

        try:
            # Starting amount
            start_amount = 50000

            # Leg 1
            price1 = self.price_cache[start]
            amount1 = start_amount / price1

            # Leg 2
            price2 = self.price_cache[leg1]
            amount2 = amount1 / price2  # May need inverse

            # Leg 3
            price3 = self.price_cache[leg2]
            amount3 = amount2 * price3

            # Leg 4
            price4 = self.price_cache[leg3]
            end_amount = amount3 * price4

            # Calculate profit
            profit = end_amount - start_amount
            profit_pct = profit / start_amount

            path = [start, leg1, leg2, leg3, end]

            return (path, profit_pct, end_amount)

        except Exception as e:
            logger.debug(f"Error calculating complex arbitrage: {e}")
            return None

    def get_arbitrage_stats(self) -> dict:
        """Get arbitrage statistics"""

        return {
            "opportunities_found": self.opportunities_found,
            "opportunities_executed": self.opportunities_executed,
            "execution_rate": (
                self.opportunities_executed / self.opportunities_found
                if self.opportunities_found > 0
                else 0
            ),
            "min_profit_threshold": self.min_profit_pct,
            "total_fee_pct": self.total_fee_pct
        }


class CrossExchangeArbitrageAgent(BaseAgent):
    """
    Cross-exchange arbitrage agent.

    Buy on one exchange, sell on another.

    Example:
    - BTC on Binance: $50,000
    - BTC on Coinbase: $50,200
    - Profit: $200 (0.4%)
    - After fees + withdrawal: ~0.1-0.2%

    Challenges:
    - Withdrawal time (minutes to hours)
    - Withdrawal fees
    - Exchange rate differences
    - Capital needs to be split across exchanges
    """

    def __init__(
        self,
        name: str = "CrossExchangeArb",
        weight: float = 1.5,
        min_profit_pct: float = 0.005  # 0.5% minimum (higher than triangular due to complexity)
    ):
        super().__init__(name, weight)
        self.min_profit_pct = min_profit_pct

        # Track prices across exchanges
        self.exchange_prices: dict[str, dict[str, float]] = {}

    async def analyze(
        self,
        tick: DataPoint,
        position: dict | None,
        market_context: dict
    ) -> AgentVote:
        """
        Analyze cross-exchange arbitrage.

        Note: This is more complex than triangular arbitrage
        and requires capital on multiple exchanges.

        For now, returns HOLD (can be implemented later).
        """

        return AgentVote(
            agent_name=self.name,
            action="HOLD",
            confidence=0.5,
            size=0.0,
            reason="Cross-exchange arbitrage not yet implemented"
        )
