"""
Test fixture: Golden cross scenario for trend following tests.

This fixture provides a synthetic price series that exhibits a golden cross
(fast MA crossing above slow MA), which should trigger buy signals in trend
following strategies.
"""

import numpy as np
import pandas as pd


def create_golden_cross(
    num_points: int = 100,
    initial_price: float = 50000.0,
    trend_strength: float = 0.02,
    noise_level: float = 0.01,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Create a price series with a golden cross pattern.

    Args:
        num_points: Number of data points
        initial_price: Starting price
        trend_strength: Strength of upward trend after cross
        noise_level: Random noise amplitude
        seed: Random seed for reproducibility

    Returns:
        DataFrame with columns: timestamp, open, high, low, close, volume
    """
    np.random.seed(seed)

    # Create timestamps (1-minute bars)
    timestamps = pd.date_range(start="2024-01-01", periods=num_points, freq="1min")

    # Phase 1: Downtrend (first 30 points) - fast MA below slow MA
    downtrend = np.linspace(initial_price, initial_price * 0.95, 30)

    # Phase 2: Consolidation (points 30-50) - MAs converge
    consolidation = np.ones(20) * (initial_price * 0.95)

    # Phase 3: Uptrend (points 50-100) - fast MA crosses above slow MA
    uptrend = np.linspace(
        initial_price * 0.95, initial_price * (1 + trend_strength), num_points - 50
    )

    # Combine phases
    close_prices = np.concatenate([downtrend, consolidation, uptrend])

    # Add random noise
    noise = np.random.normal(0, initial_price * noise_level, num_points)
    close_prices = close_prices + noise

    # Generate OHLC from close
    open_prices = np.roll(close_prices, 1)
    open_prices[0] = initial_price

    high_prices = np.maximum(open_prices, close_prices) * (1 + np.abs(noise) / initial_price)
    low_prices = np.minimum(open_prices, close_prices) * (1 - np.abs(noise) / initial_price)

    # Volume (higher during trend)
    volume = np.ones(num_points) * 100.0
    volume[50:] *= 1.5  # Higher volume during uptrend

    # Create DataFrame
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
    # Generate and save fixture
    df = create_golden_cross()
    df.to_csv("tests/fixtures/market_data/golden_cross.csv", index=False)
    print(f"Generated golden_cross.csv with {len(df)} rows")
    print(f"\nFirst 5 rows:")
    print(df.head())
    print(f"\nLast 5 rows:")
    print(df.tail())
