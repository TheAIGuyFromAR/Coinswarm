"""
Lead-Lag Analyzer

Detects lead-lag relationships between pairs.

Example: If BTC moves, does SOL follow 15 minutes later?
If yes, we can trade SOL based on BTC's movements!
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class LeadLagPattern:
    """Lead-lag relationship between two pairs"""
    leader: str
    follower: str
    lag_minutes: int  # How many minutes follower lags behind
    correlation: float  # Correlation at optimal lag
    confidence: float
    description: str
    trading_signal: str


class LeadLagAnalyzer:
    """
    Detect lead-lag relationships between trading pairs

    Use case:
    If BTC moves up 2%, and SOL follows 15 minutes later with 3% move,
    we can trade SOL when we see BTC move!
    """

    def __init__(self, max_lag_minutes: int = 60):
        """
        Initialize lead-lag analyzer

        Args:
            max_lag_minutes: Maximum lag to test (in minutes)
        """
        self.max_lag_minutes = max_lag_minutes

    def detect_lead_lag(
        self,
        price1: np.ndarray,
        price2: np.ndarray,
        timestamps1: np.ndarray | None = None,
        timestamps2: np.ndarray | None = None
    ) -> LeadLagPattern | None:
        """
        Detect if one series leads another

        Args:
            price1: First price series
            price2: Second price series
            timestamps1: Timestamps for series 1 (optional)
            timestamps2: Timestamps for series 2 (optional)

        Returns:
            LeadLagPattern if significant relationship found, else None
        """

        # Calculate returns
        returns1 = np.diff(price1) / price1[:-1]
        returns2 = np.diff(price2) / price2[:-1]

        # Align lengths
        min_len = min(len(returns1), len(returns2))
        returns1 = returns1[-min_len:]
        returns2 = returns2[-min_len:]

        # Test different lags
        max_lag_candles = self.max_lag_minutes  # Assuming 1-minute candles
        correlations = []

        for lag in range(-max_lag_candles, max_lag_candles + 1):
            if lag < 0:
                # Test if series1 leads series2
                corr = np.corrcoef(
                    returns1[:lag],
                    returns2[-lag:]
                )[0, 1]
            elif lag > 0:
                # Test if series2 leads series1
                corr = np.corrcoef(
                    returns1[lag:],
                    returns2[:-lag]
                )[0, 1]
            else:
                # No lag
                corr = np.corrcoef(returns1, returns2)[0, 1]

            correlations.append((lag, abs(corr), corr))

        # Find lag with maximum correlation
        best_lag, best_abs_corr, best_corr = max(correlations, key=lambda x: x[1])

        # Only return if correlation is significant
        if best_abs_corr < 0.3:
            return None

        # Determine leader and follower
        if best_lag < 0:
            # Series1 leads series2
            leader_returns = returns1
            follower_returns = returns2
            leader_name = "pair1"
            follower_name = "pair2"
            lag_minutes = abs(best_lag)
        elif best_lag > 0:
            # Series2 leads series1
            leader_returns = returns2
            follower_returns = returns1
            leader_name = "pair2"
            follower_name = "pair1"
            lag_minutes = best_lag
        else:
            # No lag (simultaneous)
            return None

        # Calculate amplification factor
        # How much does follower move relative to leader?
        leader_std = np.std(leader_returns)
        follower_std = np.std(follower_returns)
        amplification = follower_std / leader_std if leader_std > 0 else 1.0

        return {
            "leader": leader_name,
            "follower": follower_name,
            "lag_minutes": lag_minutes,
            "correlation": best_corr,
            "amplification": amplification,
            "confidence": best_abs_corr
        }

    def detect_all_lead_lag_patterns(
        self,
        price_data: dict[str, np.ndarray]
    ) -> list[LeadLagPattern]:
        """
        Detect lead-lag patterns across all pairs

        Returns:
            List of significant lead-lag patterns
        """

        patterns = []
        pairs = list(price_data.keys())

        for i, pair1 in enumerate(pairs):
            for pair2 in pairs[i+1:]:
                # Detect lead-lag
                result = self.detect_lead_lag(
                    price_data[pair1],
                    price_data[pair2]
                )

                if result is None:
                    continue

                # Create pattern
                leader = pair1 if result["leader"] == "pair1" else pair2
                follower = pair2 if result["leader"] == "pair1" else pair1

                pattern = LeadLagPattern(
                    leader=leader,
                    follower=follower,
                    lag_minutes=result["lag_minutes"],
                    correlation=result["correlation"],
                    confidence=result["confidence"],
                    description=f"{leader} leads {follower} by {result['lag_minutes']} minutes with {result['correlation']:.2f} correlation",
                    trading_signal=f"Trade {follower} based on {leader} movements (wait {result['lag_minutes']} min, amplification: {result['amplification']:.2f}x)"
                )

                patterns.append(pattern)

        # Sort by confidence
        patterns.sort(key=lambda x: x.confidence, reverse=True)

        return patterns


# Example usage
if __name__ == "__main__":
    analyzer = LeadLagAnalyzer(max_lag_minutes=30)

    # Simulate BTC leading SOL by 15 minutes
    np.random.seed(42)
    btc_moves = np.random.randn(200).cumsum()

    # SOL follows BTC with 15-minute lag and amplification
    lag = 15
    sol_moves = np.concatenate([
        np.zeros(lag),  # Delay
        btc_moves[:-lag] * 1.5  # Follow with 1.5x amplification
    ]) + np.random.randn(200) * 0.5  # Add noise

    price_data = {
        "BTC-USDT": 50000 + btc_moves * 100,
        "SOL-USDT": 100 + sol_moves * 2,
    }

    # Detect patterns
    patterns = analyzer.detect_all_lead_lag_patterns(price_data)

    print("Detected Lead-Lag Patterns:")
    for pattern in patterns:
        print(f"\n  {pattern.description}")
        print(f"    Confidence: {pattern.confidence:.2f}")
        print(f"    → {pattern.trading_signal}")
