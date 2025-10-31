# Test Fixtures

Synthetic market data for deterministic testing.

## Available Fixtures

### Golden Cross (`golden_cross`)
Price series exhibiting a golden cross pattern (fast MA crossing above slow MA).

- **Use Case:** Trend following strategy tests
- **Pattern:** Downtrend → Consolidation → Uptrend
- **Duration:** 100 bars (1-minute)
- **Deterministic:** Yes (seed=42)

### Mean Reversion (`mean_reversion`)
Price oscillating around a mean value.

- **Use Case:** Mean reversion strategy tests
- **Pattern:** Oscillation around $50,000
- **Reversion Speed:** Configurable (default: 0.3)
- **Deterministic:** Yes (seed=42)

### High Volatility (`high_volatility`)
Volatile price movements for stress testing.

- **Use Case:** Safety invariant tests, risk management
- **Volatility:** 10% annualized (default)
- **Volume:** Spikes on large moves
- **Deterministic:** Yes (seed=42)

### Range Bound (`range_bound`)
Price bouncing between support and resistance.

- **Use Case:** Regime detection, consolidation strategies
- **Range:** ±3% from center (default)
- **Pattern:** Bounces off levels
- **Deterministic:** Yes (seed=42)

## Usage

```python
from tests.fixtures import load_fixture, list_fixtures

# Load a fixture (auto-generates if needed)
df = load_fixture('golden_cross')

# List available fixtures
print(list_fixtures())
# ['golden_cross', 'high_volatility', 'mean_reversion', 'range_bound']

# Use in tests
def test_trend_agent():
    prices = load_fixture('golden_cross')
    agent = TrendAgent()
    action = agent.decide(prices)
    assert action.type == ActionType.BUY
```

## Generating Fixtures

Each fixture has a generator script:

```bash
# Generate manually
python tests/fixtures/market_data/golden_cross.py

# Or use loader (auto-generates)
from tests.fixtures import load_fixture
df = load_fixture('golden_cross')  # Creates CSV if missing
```

## Adding New Fixtures

1. Create generator in `market_data/my_fixture.py`
2. Implement `create_my_fixture()` function
3. Return DataFrame with columns: `timestamp, open, high, low, close, volume`
4. Use deterministic seed for reproducibility

Example:

```python
def create_my_fixture(seed=42):
    np.random.seed(seed)
    # ... generate data ...
    return pd.DataFrame({
        'timestamp': timestamps,
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volumes,
    })
```

## Determinism

All fixtures are deterministic (same seed → same data). This ensures:

- ✅ Reproducible tests
- ✅ Determinism soundness validation
- ✅ CI/CD consistency
- ✅ Debugging reliability
