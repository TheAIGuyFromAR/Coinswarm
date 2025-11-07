"""
Cointegration Tester

Tests for cointegration between pairs to find spread trading opportunities.

Example: BTC-USDT and BTC-USDC should be cointegrated (same asset, different stablecoins)
If spread widens beyond normal range → mean reversion trade opportunity
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class CointegrationOpportunity:
    """Spread trading opportunity from cointegration"""
    pair1: str
    pair2: str
    spread: float  # Current spread
    mean_spread: float  # Historical mean
    z_score: float  # How many std devs from mean
    cointegrated: bool  # Are pairs cointegrated?
    confidence: float
    trading_signal: str


class CointegrationTester:
    """
    Test for cointegration and find spread trading opportunities

    Use cases:
    1. BTC-USDT vs BTC-USDC spread trading
    2. Cross-exchange arbitrage (same pair, different exchanges)
    3. Synthetic pair vs direct pair (BTC-SOL synthetic vs direct)
    """

    def __init__(self, lookback_period: int = 100):
        """
        Initialize cointegration tester

        Args:
            lookback_period: Candles for calculating mean/std
        """
        self.lookback_period = lookback_period
        self.spread_history: Dict[tuple, List[float]] = {}

    def test_cointegration(
        self,
        price1: np.ndarray,
        price2: np.ndarray,
        significance_level: float = 0.05
    ) -> Tuple[bool, float]:
        """
        Test if two price series are cointegrated

        Args:
            price1: First price series
            price2: Second price series
            significance_level: P-value threshold

        Returns:
            (is_cointegrated, p_value)
        """

        # Simplified cointegration test
        # In production, use statsmodels.tsa.stattools.coint

        # Calculate spread
        spread = price1 - price2

        # Test if spread is stationary (mean-reverting)
        # Simple test: Check if spread returns to mean frequently

        mean_spread = np.mean(spread)
        std_spread = np.std(spread)

        # Count mean crossings
        above_mean = spread > mean_spread
        crossings = np.sum(np.diff(above_mean.astype(int)) != 0)

        # If spread crosses mean frequently, likely mean-reverting
        expected_crossings = len(spread) / 2
        crossing_ratio = crossings / expected_crossings

        # Cointegrated if crosses mean often (mean-reverting)
        is_cointegrated = crossing_ratio > 0.5
        p_value = 1.0 - crossing_ratio  # Mock p-value

        return is_cointegrated, p_value

    def detect_spread_opportunities(
        self,
        price_data: Dict[str, np.ndarray]
    ) -> List[CointegrationOpportunity]:
        """
        Detect spread trading opportunities across pairs

        Focus on:
        1. Same asset, different stablecoins (BTC-USDT vs BTC-USDC)
        2. Cross-pair opportunities
        """

        opportunities = []
        pairs = list(price_data.keys())

        for i, pair1 in enumerate(pairs):
            for pair2 in pairs[i+1:]:
                # Check if pairs should be cointegrated
                if not self._should_test_cointegration(pair1, pair2):
                    continue

                # Get price series
                prices1 = price_data[pair1]
                prices2 = price_data[pair2]

                # Align lengths
                min_len = min(len(prices1), len(prices2))
                if min_len < self.lookback_period:
                    continue

                prices1 = prices1[-min_len:]
                prices2 = prices2[-min_len:]

                # Test cointegration
                is_cointegrated, p_value = self.test_cointegration(prices1, prices2)

                # Calculate spread
                spread = prices1 - prices2
                current_spread = spread[-1]

                # Calculate statistics
                mean_spread = np.mean(spread[-self.lookback_period:])
                std_spread = np.std(spread[-self.lookback_period:])

                if std_spread == 0:
                    continue

                z_score = (current_spread - mean_spread) / std_spread

                # Track spread history
                pair_key = (pair1, pair2)
                if pair_key not in self.spread_history:
                    self.spread_history[pair_key] = []
                self.spread_history[pair_key].append(current_spread)

                # Detect opportunities

                # Opportunity 1: Spread too wide (buy low, sell high)
                if z_score > 2.0 and is_cointegrated:
                    opportunities.append(CointegrationOpportunity(
                        pair1=pair1,
                        pair2=pair2,
                        spread=current_spread,
                        mean_spread=mean_spread,
                        z_score=z_score,
                        cointegrated=is_cointegrated,
                        confidence=0.8,
                        trading_signal=f"Spread TOO WIDE: Buy {pair2}, Sell {pair1} (spread will narrow)"
                    ))

                # Opportunity 2: Spread too narrow (sell high, buy low)
                elif z_score < -2.0 and is_cointegrated:
                    opportunities.append(CointegrationOpportunity(
                        pair1=pair1,
                        pair2=pair2,
                        spread=current_spread,
                        mean_spread=mean_spread,
                        z_score=z_score,
                        cointegrated=is_cointegrated,
                        confidence=0.8,
                        trading_signal=f"Spread TOO NARROW: Buy {pair1}, Sell {pair2} (spread will widen)"
                    ))

                # Opportunity 3: Mean reversion (currently at extremes)
                elif abs(z_score) > 1.5 and is_cointegrated:
                    opportunities.append(CointegrationOpportunity(
                        pair1=pair1,
                        pair2=pair2,
                        spread=current_spread,
                        mean_spread=mean_spread,
                        z_score=z_score,
                        cointegrated=is_cointegrated,
                        confidence=0.6,
                        trading_signal=f"Potential mean reversion: Spread at {z_score:.1f} std devs"
                    ))

        return opportunities

    def _should_test_cointegration(self, pair1: str, pair2: str) -> bool:
        """
        Determine if two pairs should be tested for cointegration

        Cointegration likely for:
        - Same asset, different stablecoins (BTC-USDT vs BTC-USDC)
        - Same pair, different exchanges (if we had that data)
        """

        # Extract base assets
        base1 = pair1.split("-")[0]
        base2 = pair2.split("-")[0]

        # Same base asset = should be cointegrated
        if base1 == base2:
            return True

        # TODO: Add more sophisticated logic for related pairs
        # e.g., BTC-ETH correlation, stablecoin pairs, etc.

        return False


# Example usage
if __name__ == "__main__":
    tester = CointegrationTester(lookback_period=100)

    # Mock data: BTC-USDT and BTC-USDC (should be cointegrated)
    base_price = np.random.randn(200).cumsum() + 50000

    # BTC-USDT: Base price with small noise
    btc_usdt = base_price + np.random.randn(200) * 10

    # BTC-USDC: Almost same as USDT (cointegrated)
    btc_usdc = base_price + np.random.randn(200) * 8

    # Add a spread anomaly at the end
    btc_usdt[-5:] += 50  # BTC-USDT suddenly $50 higher

    price_data = {
        "BTC-USDT": btc_usdt,
        "BTC-USDC": btc_usdc,
    }

    # Detect opportunities
    opportunities = tester.detect_spread_opportunities(price_data)

    print("Detected Spread Trading Opportunities:")
    for opp in opportunities:
        print(f"\n  {opp.pair1} vs {opp.pair2}:")
        print(f"    Current spread: ${opp.spread:.2f}")
        print(f"    Mean spread: ${opp.mean_spread:.2f}")
        print(f"    Z-score: {opp.z_score:.2f}")
        print(f"    Cointegrated: {opp.cointegrated}")
        print(f"    → {opp.trading_signal}")
