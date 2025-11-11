"""
Test fixture: High volatility scenario for stress testing.

Creates volatile price movements to test risk management and safety invariants.
"""

import numpy as np
import pandas as pd


def create_high_volatility(
    num_points: int = 100,
    initial_price: float = 50000.0,
    volatility: float = 0.10,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Create a high-volatility price series with large swings.

    Args:
        num_points: Number of data points
        initial_price: Starting price
        volatility: Daily volatility (annualized / sqrt(252))
        seed: Random seed

    Returns:
        DataFrame with OHLCV data showing high volatility
    """
    np.random.seed(seed)

    timestamps = pd.date_range(start="2024-01-01", periods=num_points, freq="1min")

    # Generate returns with high volatility
    returns = np.random.normal(0, volatility / np.sqrt(252 * 24 * 60), num_points)

    # Price series from returns
    log_prices = np.log(initial_price) + np.cumsum(returns)
    close_prices = np.exp(log_prices)

    # OHLC with wider ranges due to volatility
    open_prices = np.roll(close_prices, 1)
    open_prices[0] = initial_price

    # High volatility = wider OHLC ranges
    range_pct = np.abs(returns) * 3  # Intrabar range
    high_prices = np.maximum(open_prices, close_prices) * (1 + range_pct)
    low_prices = np.minimum(open_prices, close_prices) * (1 - range_pct)

    # Volume spikes during volatile moves
    volume = 100.0 + np.abs(returns) * 10000

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
    df = create_high_volatility()
    df.to_csv("tests/fixtures/market_data/high_volatility.csv", index=False)
    print(f"Generated high_volatility.csv with {len(df)} rows")
