# Multi-Timescale Strategy Guide

**Everything from Market Making (microseconds) to Long-Term Holds (years)**

---

## 🎯 The Complete Timescale Spectrum

```
TIMESCALE         DURATION        STRATEGY TYPES                  MEMORY CONFIG
═══════════════════════════════════════════════════════════════════════════════

MICROSECOND       < 1ms          Market making                    HOT
(HFT)                            - Bid-ask spread capture        - 1k episodes
                                 - Latency arbitrage             - 384-dim state
                                 - Co-location advantage         - 10μs retrieval
                                 Requires:                       - 1 day retention
                                 - Sharpe > 2.0                  Focus:
                                 - Win rate > 51%                - Microstructure 2×
                                 - 1000+ trades/window           - Order book depth
                                 - Max DD < 5%                   - Spread (bps)

MILLISECOND       1ms - 1s       Spread arbitrage                 HOT
(HFT)                            - Cross-exchange arbitrage      - 5k episodes
                                 - Tick scalping                 - 384-dim state
                                 - Momentum bursts               - 100μs retrieval
                                 Same requirements as above       - 7 day retention

SECOND            1s - 1min      High-frequency scalping          HOT
                                 - Tick-level patterns           - 10k episodes
                                 - Order flow imbalance          - 384-dim state
                                 Requires:                       - 1ms retrieval
                                 - Sharpe > 1.8                  - 30 day retention
                                 - Win rate > 52%

MINUTE            1min - 1h      Intraday patterns                WARM
                                 - News reaction trading         - 50k episodes
                                 - Breakout scalping             - 256-dim state
                                 Requires:                       - 5ms retrieval
                                 - Sharpe > 1.5                  - 90 day retention
                                 - Win rate > 55%                Focus:
                                                                 - Technicals 1.5×
                                                                 - Price action

HOUR              1h - 1d        Day trading                      WARM
                                 - Intraday trends               - 100k episodes
                                 - RSI/MACD signals              - 256-dim state
                                 - Support/resistance            - 10ms retrieval
                                 Requires:                       - 180 day retention
                                 - Sharpe > 1.5                  Focus:
                                 - Win rate > 55%                - Technicals 2×
                                 - Max DD < 10%                  - Sentiment 1.5×

DAY               1d - 1w        Swing trading                    WARM
                                 - Multi-day trends              - 500k episodes
                                 - Pattern breakouts             - 128-dim state
                                 - News-driven moves             - 50ms retrieval
                                 Requires:                       - 2 year retention
                                 - Sharpe > 1.2                  Focus:
                                 - Win rate > 55%                - Sentiment 2×
                                 - Max DD < 15%                  - Trend strength

WEEK              1w - 1m        Position trading                 COLD
                                 - Trend following               - 1M episodes
                                 - Regime trading                - 128-dim state
                                 Requires:                       - 100ms retrieval
                                 - Sharpe > 1.0                  - 5 year retention
                                 - Win rate > 50%                Focus:
                                 - Max DD < 20%                  - Portfolio 1.5×

MONTH             1m - 1y        Long-term trading                COLD
                                 - Macro themes                  - 2M episodes
                                 - Fundamental analysis          - 64-dim state
                                 Requires:                       - 500ms retrieval
                                 - Sharpe > 1.0                  - 10 year retention
                                 - Win rate > 50%                Focus:
                                 - Max DD < 25%                  - Sentiment 3×
                                                                 - Macro indicators

YEAR              1y+            Ultra long-term                  COLD
                                 - Secular trends                - 5M episodes
                                 - Economic cycles               - 64-dim state
                                 Requires:                       - 1s retrieval
                                 - Sharpe > 1.0                  - 20 year retention
                                 - Win rate > 50%                Focus:
                                 - Max DD < 30%                  - Sentiment 5×
```

---

## 💱 Market Making Strategy (MICROSECOND)

### What It Is
- Place limit orders on **both sides** of order book
- **Capture spread**: buy at bid, sell at ask
- Make money on price difference (1-5 bps typically)
- Very high volume, very low margin per trade

### Requirements
```python
# HFT Market Making
timescale = Timescale.MICROSECOND
window_size = 1 hour  # Test in 1-hour windows
min_trades = 1000     # Need volume for statistical power
min_sharpe = 2.0      # Low risk per trade → high Sharpe
min_win_rate = 0.51   # Can have low win rate with volume
max_drawdown = 0.05   # Stop quickly if losing
```

### Memory Configuration
```python
# Full microstructure detail
state = [
    # Price (24 dims)
    price, spread_bps, bid_price, ask_price, mid_price, ...

    # Microstructure (40 dims) ← MOST IMPORTANT for HFT!
    bid_depth_1bps, ask_depth_1bps,
    order_imbalance,
    large_order_ratio,
    trade_intensity,
    liquidity_score,
    price_impact,
    ...

    # Technical (80 dims) ← Less relevant for HFT
    # Sentiment (40 dims) ← Not relevant for HFT
    # etc.
]

# Weights
microstructure_weight = 2.0  # HFT cares MOST about this
technical_weight = 0.1       # Barely relevant
sentiment_weight = 0.0       # Not relevant at all
```

### Profitability
```
Trade 1:  BUY  @ $50,000.05 (bid)
         SELL @ $50,000.10 (ask)
         Profit: $0.05 (1 bps)
         Time: 50ms

Trade 2:  BUY  @ $50,001.02
         SELL @ $50,001.08
         Profit: $0.06 (1.2 bps)
         Time: 120ms

... 1000 trades later ...

Total profit: $50 in 1 hour
Sharpe: 2.8 (very consistent!)
Win rate: 52%
Max DD: 2%

✅ PASSED - Market making works on MICROSECOND timescale!
```

---

## 📊 Day Trading Strategy (HOUR)

### What It Is
- Trade intraday moves (hours)
- Use technical indicators (RSI, MACD, Bollinger)
- Close all positions by end of day

### Requirements
```python
timescale = Timescale.HOUR
window_size = 1 day
min_trades = 100
min_sharpe = 1.5
min_win_rate = 0.55
max_drawdown = 0.10
```

### Memory Configuration
```python
state = [
    # Price (24 dims)
    price, returns_1h, returns_4h, volatility, ...

    # Technical (80 dims) ← MOST IMPORTANT for day trading!
    rsi_14, macd, macd_signal,
    ma_20, ma_50,
    bollinger_position,
    stochastic_k, stochastic_d,
    ...

    # Sentiment (40 dims) ← Also important
    news_sentiment,
    twitter_sentiment,
    funding_rate,
    ...
]

# Weights
technical_weight = 2.0    # Day trading is all about technicals
sentiment_weight = 1.5    # News matters
microstructure_weight = 0.5  # Less relevant
```

---

## 📈 Swing Trading Strategy (DAY/WEEK)

### What It Is
- Hold positions for days/weeks
- Trade trends, breakouts, patterns
- Fundamental + technical analysis

### Requirements
```python
timescale = Timescale.DAY
window_size = 30 days
min_trades = 50
min_sharpe = 1.2
min_win_rate = 0.55
max_drawdown = 0.15
```

### Memory Configuration
```python
state = [
    # Compressed to 128 dims (from 384)

    # Focus on trends
    trend_strength,
    trend_consistency,
    support_resistance_levels,

    # Sentiment ← MOST IMPORTANT
    news_sentiment,      # Weight: 2×
    social_sentiment,
    funding_rate_trend,
    fear_greed_index,

    # Portfolio context ← Important for multi-day
    current_positions,
    daily_pnl,
    drawdown,

    # Less microstructure
    # (compress from 40 → 5 dims)
]
```

---

## 🌍 Long-Term Strategy (MONTH/YEAR)

### What It Is
- Hold for months/years
- Macro themes, fundamentals
- Economic cycles

### Requirements
```python
timescale = Timescale.MONTH
window_size = 180 days
min_trades = 20
min_sharpe = 1.0
min_win_rate = 0.50  # Can have 50% if wins are big
max_drawdown = 0.25  # Can tolerate more DD
```

### Memory Configuration
```python
state = [
    # Heavily compressed to 64 dims (from 384)

    # Macro sentiment ← MOST IMPORTANT
    news_sentiment,           # Weight: 5×
    twitter_aggregate,
    regulatory_sentiment,
    institutional_flows,
    macro_indicators,

    # Price trends
    price_vs_200ma,
    long_term_momentum,

    # Almost no microstructure
    # (compress from 40 → 1 dim: "overall liquidity")

    # No short-term technicals
    # (RSI, MACD not relevant for months)
]
```

---

## 🔬 Validation Examples

### Example 1: Market Making (MICROSECOND)
```python
from coinswarm.memory.hierarchical_memory import HierarchicalMemory, Timescale
from coinswarm.backtesting.multi_timescale_validator import MultiTimescaleValidator

# Initialize
memory = HierarchicalMemory(enabled_timescales=[
    Timescale.MICROSECOND,
    Timescale.MILLISECOND
])

validator = MultiTimescaleValidator(data=btc_tick_data_2022_2024)

# Test market making strategy
result = await validator.validate_strategy(
    strategy=market_making_bot,
    strategy_name="Market Making v1.0",
    primary_timescale=Timescale.MICROSECOND,
    test_adjacent=True
)

# Output:
# MULTI-TIMESCALE VALIDATION: Market Making v1.0
# Primary Timescale: microsecond
# Cross-Timescale Robust: ✅ YES
#
# Passed Timescales:
#   ✅ microsecond    - Sharpe=2.8, WinRate=52%
#   ✅ millisecond    - Sharpe=3.2, WinRate=51%
#
# Failed Timescales:
#   ❌ second         - Sharpe=0.3, WinRate=48%
#
# ✅ Strategy works ONLY on HFT timescales (expected!)
```

### Example 2: Universal Strategy (Rare!)
```python
# Test if strategy works across ALL timescales
result = await validator.validate_strategy(
    strategy=universal_momentum_bot,
    strategy_name="Universal Momentum",
    test_all_timescales=True
)

# Output:
# MULTI-TIMESCALE VALIDATION: Universal Momentum
# Cross-Timescale Robust: ✅ YES
# Consistency Score: 87%
#
# Passed Timescales (6):
#   ✅ second         - Sharpe=1.8, WinRate=55%
#   ✅ minute         - Sharpe=1.9, WinRate=56%
#   ✅ hour           - Sharpe=2.1, WinRate=58%
#   ✅ day            - Sharpe=1.7, WinRate=54%
#   ✅ week           - Sharpe=1.5, WinRate=53%
#   ✅ month          - Sharpe=1.3, WinRate=51%
#
# Failed Timescales (2):
#   ❌ microsecond    - Sharpe=0.5, WinRate=49%
#   ❌ year           - Sharpe=0.8, WinRate=48%
#
# 🎉 RARE! Strategy works across 6 timescales!
# → Momentum is a universal pattern in markets
```

---

## 📊 Expected Performance by Strategy Type

| Strategy Type | Timescale | Win Rate | Sharpe | Max DD | Trades/Day |
|--------------|-----------|----------|--------|--------|------------|
| Market Making | MICRO | 51-52% | 2.0-3.0 | 3-5% | 1000-10000 |
| Spread Arb | MILLI | 50-52% | 2.0-3.5 | 5-8% | 100-1000 |
| Scalping | SECOND | 52-55% | 1.5-2.5 | 8-12% | 50-200 |
| Day Trading | HOUR | 55-60% | 1.5-2.0 | 10-15% | 5-20 |
| Swing Trading | DAY | 55-65% | 1.2-1.8 | 15-20% | 0.5-2 |
| Position | WEEK | 50-60% | 1.0-1.5 | 20-25% | 0.1-0.5 |
| Long-term | MONTH+ | 45-55% | 0.8-1.2 | 25-40% | 0.01-0.1 |

**Key Insights**:
- HFT: High Sharpe, low win rate OK (volume compensates)
- Day trading: High win rate needed (fewer trades)
- Long-term: Can have low win rate if wins are BIG

---

## 🎯 Strategy Selection Guide

### "I want to make money on market making"
```python
timescale = Timescale.MICROSECOND
requirements:
  - Co-location (< 1ms latency to exchange)
  - Full order book data (L2/L3)
  - High capital ($100k+ for meaningful profits)
  - Focus on microstructure features
  - Test on 1-hour windows
  - Need 1000+ trades for statistical power
```

### "I want to day trade"
```python
timescale = Timescale.HOUR
requirements:
  - Technical indicators (RSI, MACD, Bollinger)
  - News sentiment feed
  - Test on 1-day to 1-week windows
  - Need 100+ trades
  - Focus on technical + sentiment features
```

### "I want to swing trade"
```python
timescale = Timescale.DAY
requirements:
  - Multi-day data
  - News + social sentiment
  - Test on 1-week to 1-month windows
  - Need 50+ trades
  - Focus on sentiment + trends
```

### "I want long-term holds"
```python
timescale = Timescale.MONTH
requirements:
  - Macro data (rates, inflation, GDP)
  - Fundamental analysis
  - Test on 3-month to 6-month windows
  - Need only 20+ trades
  - Focus on macro sentiment
  - Can tolerate 25% drawdown
```

---

## 🚀 Next Steps

1. **Choose Your Timescale**
   - Market making → MICROSECOND
   - Day trading → HOUR
   - Swing trading → DAY
   - Long-term → MONTH

2. **Configure Memory**
   ```python
   memory = HierarchicalMemory(
       enabled_timescales=[your_timescale]
   )
   ```

3. **Build Strategy**
   - Focus on relevant features for your timescale
   - Use appropriate requirements

4. **Validate Properly**
   ```python
   validator = MultiTimescaleValidator(data=historical_data_2yr)
   result = await validator.validate_strategy(...)
   ```

5. **Deploy**
   - HFT: Co-located servers
   - Day trading: Cloud with low latency
   - Swing: Regular cloud is fine
   - Long-term: Anywhere is fine

---

**You now have a system that works for EVERYTHING from microsecond market making to multi-year holds! 🎉**
