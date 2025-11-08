"""
Correlation Detector

Detects correlation patterns across multiple pairs:
- Normal correlation (BTC up → SOL up)
- Amplified correlation (BTC up 5% → SOL up 10%)
- Dampened correlation (BTC down 5% → SOL down 2%)
- Correlation breaks (BTC and SOL diverging)
"""

import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class CorrelationPattern:
    """Detected correlation pattern"""
    pair1: str
    pair2: str
    correlation: float  # -1 to 1
    pattern_type: str  # "normal", "amplified", "dampened", "break"
    confidence: float  # 0 to 1
    description: str
    trading_signal: Optional[str] = None


class CorrelationDetector:
    """
    Detect correlation patterns across trading pairs

    Use cases:
    1. BTC-SOL correlation breaks → Trade the divergence
    2. BTC leads SOL → Trade SOL based on BTC movements
    3. High correlation → Avoid redundant positions
    """

    def __init__(self, window_size: int = 100):
        """
        Initialize correlation detector

        Args:
            window_size: Number of candles for correlation calculation
        """
        self.window_size = window_size
        self.correlation_history: Dict[tuple, List[float]] = {}

    def calculate_correlation_matrix(
        self,
        price_data: Dict[str, np.ndarray]
    ) -> Dict[tuple, float]:
        """
        Calculate correlation matrix across all pairs

        Args:
            price_data: Dict of pair -> price array

        Returns:
            Dict of (pair1, pair2) -> correlation
        """

        correlations = {}
        pairs = list(price_data.keys())

        for i, pair1 in enumerate(pairs):
            for pair2 in pairs[i+1:]:
                # Calculate returns
                returns1 = np.diff(price_data[pair1]) / price_data[pair1][:-1]
                returns2 = np.diff(price_data[pair2]) / price_data[pair2][:-1]

                # Calculate correlation
                min_len = min(len(returns1), len(returns2))
                if min_len < 2:
                    continue

                corr = np.corrcoef(
                    returns1[-min_len:],
                    returns2[-min_len:]
                )[0, 1]

                correlations[(pair1, pair2)] = corr

                # Track history
                pair_key = (pair1, pair2)
                if pair_key not in self.correlation_history:
                    self.correlation_history[pair_key] = []
                self.correlation_history[pair_key].append(corr)

        return correlations

    def detect_correlation_patterns(
        self,
        price_data: Dict[str, np.ndarray]
    ) -> List[CorrelationPattern]:
        """
        Detect correlation-based trading patterns

        Returns:
            List of detected patterns with trading signals
        """

        patterns = []

        # Calculate current correlations
        correlations = self.calculate_correlation_matrix(price_data)

        for (pair1, pair2), current_corr in correlations.items():
            # Get historical correlation
            if (pair1, pair2) not in self.correlation_history:
                continue

            history = self.correlation_history[(pair1, pair2)]
            if len(history) < 10:
                continue

            historical_corr = np.mean(history[:-1])  # Exclude current
            corr_std = np.std(history)

            # Detect patterns

            # 1. Correlation Break (divergence)
            if abs(current_corr - historical_corr) > 2 * corr_std:
                if historical_corr > 0.7:  # Were highly correlated
                    patterns.append(CorrelationPattern(
                        pair1=pair1,
                        pair2=pair2,
                        correlation=current_corr,
                        pattern_type="break",
                        confidence=0.8,
                        description=f"Correlation break: {pair1} and {pair2} historically correlated ({historical_corr:.2f}) but diverging now ({current_corr:.2f})",
                        trading_signal=f"Mean reversion: Expect {pair1} and {pair2} to re-converge"
                    ))

            # 2. High Correlation (redundant positions)
            elif current_corr > 0.9:
                patterns.append(CorrelationPattern(
                    pair1=pair1,
                    pair2=pair2,
                    correlation=current_corr,
                    pattern_type="high",
                    confidence=0.9,
                    description=f"Very high correlation: {pair1} and {pair2} move together ({current_corr:.2f})",
                    trading_signal=f"Risk: Avoid holding both {pair1} and {pair2} (redundant exposure)"
                ))

            # 3. Negative Correlation (hedge opportunity)
            elif current_corr < -0.7:
                patterns.append(CorrelationPattern(
                    pair1=pair1,
                    pair2=pair2,
                    correlation=current_corr,
                    pattern_type="negative",
                    confidence=0.8,
                    description=f"Negative correlation: {pair1} and {pair2} move opposite ({current_corr:.2f})",
                    trading_signal=f"Hedge: Use {pair2} to hedge {pair1} exposure"
                ))

            # 4. Correlation Strengthening
            elif current_corr > historical_corr + corr_std:
                patterns.append(CorrelationPattern(
                    pair1=pair1,
                    pair2=pair2,
                    correlation=current_corr,
                    pattern_type="strengthening",
                    confidence=0.7,
                    description=f"Correlation strengthening: {pair1} and {pair2} becoming more correlated",
                    trading_signal=f"Momentum: If trading {pair1}, consider {pair2} as confirmation"
                ))

        return patterns

    def get_diversification_score(
        self,
        held_pairs: List[str],
        price_data: Dict[str, np.ndarray]
    ) -> float:
        """
        Calculate portfolio diversification score

        Args:
            held_pairs: List of pairs currently held
            price_data: Price data for calculation

        Returns:
            Diversification score (0 = all correlated, 1 = all independent)
        """

        if len(held_pairs) < 2:
            return 1.0  # Fully diversified with 1 position

        # Calculate average correlation between held positions
        correlations = self.calculate_correlation_matrix(price_data)

        total_corr = 0
        count = 0

        for i, pair1 in enumerate(held_pairs):
            for pair2 in held_pairs[i+1:]:
                key = (pair1, pair2) if (pair1, pair2) in correlations else (pair2, pair1)
                if key in correlations:
                    total_corr += abs(correlations[key])
                    count += 1

        if count == 0:
            return 1.0

        avg_corr = total_corr / count

        # Convert to diversification score
        # 0 correlation = 1.0 diversification
        # 1 correlation = 0.0 diversification
        return 1.0 - avg_corr


# Example usage
if __name__ == "__main__":
    # Mock data
    detector = CorrelationDetector(window_size=100)

    # Simulate price data
    price_data = {
        "BTC-USDT": np.random.randn(200).cumsum() + 50000,
        "SOL-USDT": np.random.randn(200).cumsum() + 100,
        "ETH-USDT": np.random.randn(200).cumsum() + 3000,
    }

    # Detect patterns
    patterns = detector.detect_correlation_patterns(price_data)

    print("Detected Correlation Patterns:")
    for pattern in patterns:
        print(f"  {pattern.pattern_type.upper()}: {pattern.description}")
        if pattern.trading_signal:
            print(f"    → {pattern.trading_signal}")
