"""
Test fixture: Mean reversion scenario for mean reversion strategy tests.

Creates a price series that oscillates around a mean, suitable for testing
mean reversion strategies.
"""

import numpy as np
import pandas as pd


def create_mean_reversion(
    num_points: int = 100,
    mean_price: float = 50000.0,
    oscillation_amplitude: float = 0.05,
    reversion_speed: float = 0.3,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Create a mean-reverting price series.

    Args:
        num_points: Number of data points
        mean_price: Long-term mean price
        oscillation_amplitude: Max deviation from mean (as fraction)
        reversion_speed: Speed of reversion (0-1, higher = faster)
        seed: Random seed for reproducibility

    Returns:
        DataFrame with columns: timestamp, open, high, low, close, volume
    """
    np.random.seed(seed)

    timestamps = pd.date_range(start="2024-01-01", periods=num_points, freq="1min")

    # Initialize
    close_prices = np.zeros(num_points)
    close_prices[0] = mean_price

    # Generate mean-reverting process
    for i in range(1, num_points):
        # Current deviation from mean
        deviation = close_prices[i - 1] - mean_price

        # Mean reversion force
        reversion = -reversion_speed * deviation

        # Random shock
        shock = np.random.normal(0, mean_price * oscillation_amplitude * 0.1)

        # Next price
        close_prices[i] = close_prices[i - 1] + reversion + shock

    # Generate OHLC
    open_prices = np.roll(close_prices, 1)
    open_prices[0] = mean_price

    high_prices = np.maximum(open_prices, close_prices) * 1.002
    low_prices = np.minimum(open_prices, close_prices) * 0.998

    # Volume (higher at extremes - more trading activity)
    deviations = np.abs(close_prices - mean_price) / mean_price
    volume = 100.0 + (deviations / oscillation_amplitude) * 50.0

    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": open_prices,
            "high": high_prices,
            "low": low_prices,
            "close": close_prices,
            "volume": volume,
        }
    )

    return df


if __name__ == "__main__":
    df = create_mean_reversion()
    df.to_csv("tests/fixtures/market_data/mean_reversion.csv", index=False)
    print(f"Generated mean_reversion.csv with {len(df)} rows")
