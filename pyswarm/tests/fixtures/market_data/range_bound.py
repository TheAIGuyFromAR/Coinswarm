"""
Test fixture: Range-bound market for testing consolidation strategies.

Price oscillates within a defined range without trending.
"""

import numpy as np
import pandas as pd


def create_range_bound(
    num_points: int = 100,
    center_price: float = 50000.0,
    range_width: float = 0.03,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Create a range-bound price series.

    Args:
        num_points: Number of data points
        center_price: Center of the range
        range_width: Width of range as fraction (0.03 = 3%)
        seed: Random seed

    Returns:
        DataFrame with price bouncing between support and resistance
    """
    np.random.seed(seed)

    timestamps = pd.date_range(start="2024-01-01", periods=num_points, freq="1min")

    # Support and resistance levels
    support = center_price * (1 - range_width)
    resistance = center_price * (1 + range_width)

    # Start at center
    close_prices = np.zeros(num_points)
    close_prices[0] = center_price

    # Oscillate within range
    for i in range(1, num_points):
        # Bounce off boundaries
        if close_prices[i - 1] >= resistance:
            direction = -1  # Bounce down
        elif close_prices[i - 1] <= support:
            direction = 1  # Bounce up
        else:
            # Random walk toward boundary
            direction = np.random.choice([-1, 1])

        # Move size
        move = np.random.uniform(0, center_price * 0.005) * direction
        close_prices[i] = np.clip(close_prices[i - 1] + move, support, resistance)

    # OHLC
    open_prices = np.roll(close_prices, 1)
    open_prices[0] = center_price

    high_prices = np.maximum(open_prices, close_prices) * 1.001
    low_prices = np.minimum(open_prices, close_prices) * 0.999

    # Volume lower during consolidation
    volume = np.ones(num_points) * 80.0

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
    df = create_range_bound()
    df.to_csv("tests/fixtures/market_data/range_bound.csv", index=False)
    print(f"Generated range_bound.csv with {len(df)} rows")
