"""
Test fixtures for Coinswarm.

Provides easy access to synthetic market data for deterministic testing.
"""

from pathlib import Path
from typing import Optional

import pandas as pd

FIXTURES_DIR = Path(__file__).parent


def load_fixture(name: str, generate_if_missing: bool = True) -> pd.DataFrame:
    """
    Load a test fixture by name.

    Args:
        name: Fixture name (e.g., 'golden_cross', 'mean_reversion')
        generate_if_missing: Generate fixture if CSV doesn't exist

    Returns:
        DataFrame with OHLCV data

    Examples:
        >>> df = load_fixture('golden_cross')
        >>> df = load_fixture('high_volatility')
    """
    csv_path = FIXTURES_DIR / "market_data" / f"{name}.csv"

    # Try to load existing CSV
    if csv_path.exists():
        return pd.read_csv(csv_path, parse_dates=["timestamp"])

    # Generate if requested
    if generate_if_missing:
        generator_path = FIXTURES_DIR / "market_data" / f"{name}.py"

        if not generator_path.exists():
            raise FileNotFoundError(
                f"No fixture generator found: {generator_path}\n"
                f"Available fixtures: {list_fixtures()}"
            )

        # Import and run generator
        import importlib.util

        spec = importlib.util.spec_from_file_location(name, generator_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find create function
        create_func = getattr(module, f"create_{name}")
        df = create_func()

        # Save for next time
        df.to_csv(csv_path, index=False)

        return df

    raise FileNotFoundError(f"Fixture not found: {csv_path}")


def list_fixtures() -> list[str]:
    """List available fixtures."""
    market_data_dir = FIXTURES_DIR / "market_data"

    if not market_data_dir.exists():
        return []

    fixtures = []
    for path in market_data_dir.glob("*.py"):
        if path.name != "__init__.py":
            fixtures.append(path.stem)

    return sorted(fixtures)


__all__ = ["load_fixture", "list_fixtures"]
