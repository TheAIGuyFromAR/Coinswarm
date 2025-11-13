"""
Arbitrage Detector

Detects arbitrage opportunities across:
1. Stablecoin pairs (BTC-USDT vs BTC-USDC)
2. Triangular arbitrage (BTC→SOL→USD loop)
3. Statistical arbitrage (mean reversion on spreads)
"""

from dataclasses import dataclass


@dataclass
class ArbitrageOpportunity:
    """Detected arbitrage opportunity"""
    type: str  # "stablecoin", "triangular", "statistical"
    pairs_involved: list[str]
    profit_potential: float  # Percentage profit
    confidence: float
    description: str
    execution_steps: list[str]
    risk_level: str  # "low", "medium", "high"


class ArbitrageDetector:
    """
    Detect arbitrage opportunities across multiple pairs

    Types of arbitrage:
    1. Stablecoin arbitrage: BTC-USDT at $50,000, BTC-USDC at $50,010 → $10 profit
    2. Triangular arbitrage: USD→BTC→SOL→USD loop
    3. Statistical arbitrage: Mean reversion on historical spreads
    """

    def __init__(
        self,
        min_profit_pct: float = 0.001,  # 0.1% minimum
        transaction_cost: float = 0.001  # 0.1% per trade
    ):
        """
        Initialize arbitrage detector

        Args:
            min_profit_pct: Minimum profit percentage to report
            transaction_cost: Estimated transaction cost per trade
        """
        self.min_profit_pct = min_profit_pct
        self.transaction_cost = transaction_cost

    def detect_stablecoin_arbitrage(
        self,
        price_data: dict[str, float]
    ) -> list[ArbitrageOpportunity]:
        """
        Detect arbitrage across stablecoin pairs

        Example:
        BTC-USDT: $50,000
        BTC-USDC: $50,010
        → Buy BTC with USDT, sell for USDC, profit $10/BTC (0.02%)
        """

        opportunities = []

        # Group by base asset
        asset_prices = {}
        for pair, price in price_data.items():
            base, quote = pair.split("-")

            if base not in asset_prices:
                asset_prices[base] = {}

            asset_prices[base][quote] = price

        # Check for price differences across stablecoins
        for base_asset, stablecoin_prices in asset_prices.items():
            stablecoins = list(stablecoin_prices.keys())

            for i, stable1 in enumerate(stablecoins):
                for stable2 in stablecoins[i+1:]:
                    price1 = stablecoin_prices[stable1]
                    price2 = stablecoin_prices[stable2]

                    # Calculate spread
                    spread_pct = abs(price2 - price1) / price1

                    # Account for transaction costs (2 trades)
                    net_profit = spread_pct - (2 * self.transaction_cost)

                    if net_profit > self.min_profit_pct:
                        # Determine direction
                        if price1 < price2:
                            buy_pair = f"{base_asset}-{stable1}"
                            sell_pair = f"{base_asset}-{stable2}"
                        else:
                            buy_pair = f"{base_asset}-{stable2}"
                            sell_pair = f"{base_asset}-{stable1}"

                        opportunities.append(ArbitrageOpportunity(
                            type="stablecoin",
                            pairs_involved=[buy_pair, sell_pair],
                            profit_potential=net_profit * 100,
                            confidence=0.95,  # High confidence (same asset)
                            description=f"Stablecoin arbitrage: {buy_pair} at ${min(price1, price2):.2f} vs {sell_pair} at ${max(price1, price2):.2f}",
                            execution_steps=[
                                f"1. Buy {base_asset} on {buy_pair}",
                                f"2. Sell {base_asset} on {sell_pair}",
                                f"3. Profit: {net_profit*100:.3f}% per trade"
                            ],
                            risk_level="low"
                        ))

        return opportunities

    def detect_triangular_arbitrage(
        self,
        price_data: dict[str, float]
    ) -> list[ArbitrageOpportunity]:
        """
        Detect triangular arbitrage opportunities

        Example:
        BTC-USD: $50,000
        SOL-USD: $100
        BTC-SOL: 490 (implied should be 500)

        → USD→BTC→SOL→USD loop profits from discrepancy
        """

        opportunities = []

        # Find triangular paths
        # For simplicity, focus on common patterns: BTC-USD, SOL-USD, BTC-SOL

        # Check BTC-SOL-USD triangle
        if "BTC-USDT" in price_data and "SOL-USDT" in price_data:
            btc_usd = price_data["BTC-USDT"]
            sol_usd = price_data["SOL-USDT"]

            # Calculate implied BTC-SOL rate
            implied_btc_sol = btc_usd / sol_usd

            # Check if we have direct BTC-SOL pair
            if "BTC-SOL" in price_data:
                direct_btc_sol = price_data["BTC-SOL"]

                # Calculate arbitrage opportunity
                spread = abs(direct_btc_sol - implied_btc_sol) / implied_btc_sol

                # Account for 3 trades
                net_profit = spread - (3 * self.transaction_cost)

                if net_profit > self.min_profit_pct:
                    if direct_btc_sol < implied_btc_sol:
                        # Direct pair is cheaper
                        steps = [
                            "1. Buy BTC with USD",
                            "2. Trade BTC for SOL (direct pair)",
                            "3. Sell SOL for USD",
                            f"4. Profit: {net_profit*100:.3f}%"
                        ]
                    else:
                        # Cross pair is cheaper
                        steps = [
                            "1. Buy SOL with USD",
                            "2. Trade SOL for BTC (direct pair)",
                            "3. Sell BTC for USD",
                            f"4. Profit: {net_profit*100:.3f}%"
                        ]

                    opportunities.append(ArbitrageOpportunity(
                        type="triangular",
                        pairs_involved=["BTC-USDT", "SOL-USDT", "BTC-SOL"],
                        profit_potential=net_profit * 100,
                        confidence=0.8,
                        description=f"Triangular arbitrage: Direct BTC-SOL ({direct_btc_sol:.2f}) vs implied ({implied_btc_sol:.2f})",
                        execution_steps=steps,
                        risk_level="medium"
                    ))

        return opportunities

    def detect_all_arbitrage(
        self,
        price_data: dict[str, float]
    ) -> list[ArbitrageOpportunity]:
        """
        Detect all types of arbitrage opportunities

        Args:
            price_data: Dict of pair -> current price

        Returns:
            List of arbitrage opportunities sorted by profit potential
        """

        all_opportunities = []

        # 1. Stablecoin arbitrage
        all_opportunities.extend(
            self.detect_stablecoin_arbitrage(price_data)
        )

        # 2. Triangular arbitrage
        all_opportunities.extend(
            self.detect_triangular_arbitrage(price_data)
        )

        # TODO: 3. Statistical arbitrage (implement if needed)

        # Sort by profit potential
        all_opportunities.sort(key=lambda x: x.profit_potential, reverse=True)

        return all_opportunities


# Example usage
if __name__ == "__main__":
    detector = ArbitrageDetector(
        min_profit_pct=0.001,  # 0.1% minimum
        transaction_cost=0.001  # 0.1% per trade
    )

    # Mock price data with arbitrage opportunities
    price_data = {
        # BTC prices (stablecoin arbitrage opportunity)
        "BTC-USDT": 50000.00,
        "BTC-USDC": 50015.00,  # $15 higher!
        "BTC-BUSD": 50005.00,

        # SOL prices
        "SOL-USDT": 100.00,
        "SOL-USDC": 100.05,

        # Direct BTC-SOL (triangular arbitrage opportunity)
        "BTC-SOL": 495.00,  # Should be ~500 (50000/100)
    }

    # Detect opportunities
    opportunities = detector.detect_all_arbitrage(price_data)

    print("Detected Arbitrage Opportunities:")
    print("="*80)

    for i, opp in enumerate(opportunities, 1):
        print(f"\n{i}. {opp.type.upper()} ARBITRAGE")
        print(f"   Profit: {opp.profit_potential:.3f}%")
        print(f"   Confidence: {opp.confidence:.0%}")
        print(f"   Risk: {opp.risk_level}")
        print(f"   Description: {opp.description}")
        print("\n   Execution:")
        for step in opp.execution_steps:
            print(f"     {step}")

    print("\n" + "="*80)
