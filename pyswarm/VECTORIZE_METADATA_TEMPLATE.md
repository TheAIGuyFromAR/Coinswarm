# Vectorize Metadata Template for Time Period Snapshots

## Overview

This template defines the optimal metadata structure for storing time period snapshots in Vectorize. The metadata captures the **current state at time T**, which can later be used to find similar periods and analyze outcomes.

**Key Concept**: Store CURRENT indicators, then look FORWARD from timestamps to see outcomes.

## Complete Metadata Template

```python
{
    "id": "2024-01-15T12:00:00Z",  # ISO timestamp
    "values": [...],                # 384-dim embedding (news + sentiment + technical text)

    "metadata": {
        # ================================================================
        # TEMPORAL (for pattern discovery by time)
        # ================================================================
        "timestamp": 1705320000,           # Unix timestamp (CRITICAL!)
        "day_of_week": 1,                  # 0=Mon, 6=Sun
        "hour_of_day": 14,                 # 0-23
        "month": 1,                        # 1-12
        "is_weekend": 0,                   # Boolean
        "is_market_hours": 1,              # Boolean (9:30-16:00 ET)

        # ================================================================
        # TREND & MOMENTUM (most important for pattern matching)
        # ================================================================
        "rsi": 68,                         # Current RSI (0-100)
        "rsi_range": "neutral",            # "oversold" (<30), "neutral", "overbought" (>70)
        "rsi_slope": 0.5,                  # RSI change per hour (is RSI rising/falling?)

        "macd_histogram": 450.5,           # MACD histogram value
        "macd_signal": "bullish",          # "bullish", "bearish", "neutral"
        "macd_strength": "strong",         # "weak", "moderate", "strong"

        "momentum_1": 0.012,               # 1-period momentum (%)
        "momentum_5": 0.032,               # 5-period momentum (%)
        "momentum_10": 0.068,              # 10-period momentum (%)
        "momentum_class": "strong",        # "weak", "moderate", "strong"

        "trend": "uptrend",                # "uptrend", "downtrend", "sideways"
        "trend_strength": 0.75,            # 0-1 (how strong is the trend?)
        "higher_highs": 1,                 # Boolean (making higher highs?)
        "lower_lows": 0,                   # Boolean (making lower lows?)

        # ================================================================
        # MOVING AVERAGES & CROSSOVERS
        # ================================================================
        "sma_20": 43500,                   # 20-day SMA value
        "sma_50": 42000,                   # 50-day SMA value
        "sma_200": 38000,                  # 200-day SMA value

        "price_vs_sma20": 1.03,            # Price / SMA-20 (1.03 = 3% above)
        "price_vs_sma50": 1.07,            # Price / SMA-50
        "price_vs_sma200": 1.18,           # Price / SMA-200

        "above_sma20": 1,                  # Boolean
        "above_sma50": 1,                  # Boolean
        "above_sma200": 1,                 # Boolean

        "sma_alignment": "golden_cross",   # "golden_cross", "death_cross", "bullish", "bearish", "mixed"
        "sma_slope_20": 0.002,             # SMA-20 slope (is it rising/falling?)
        "sma_slope_50": 0.0015,            # SMA-50 slope

        # ================================================================
        # VOLATILITY & BOLLINGER BANDS
        # ================================================================
        "atr": 1250.5,                     # Average True Range (absolute volatility)
        "atr_pct": 0.028,                  # ATR as % of price
        "volatility": "medium",            # "low", "medium", "high"
        "volatility_percentile": 58,       # 0-100 (current volatility vs historical)

        "bb_position": 0.85,               # Position in Bollinger Bands (0-1)
        "bb_width": 0.045,                 # Band width as % of price
        "bb_squeeze": 0,                   # Boolean (bands narrowing = low volatility)
        "bb_expansion": 1,                 # Boolean (bands widening = increasing volatility)
        "at_bb_upper": 0,                  # Boolean (price near upper band)
        "at_bb_lower": 0,                  # Boolean (price near lower band)

        # ================================================================
        # VOLUME (critical for confirmation)
        # ================================================================
        "volume": 35000000000,             # Current volume (USD)
        "volume_sma_20": 24000000000,      # 20-day average volume
        "volume_ratio": 1.45,              # Current / average (1.45 = 45% above avg)
        "volume_spike": 1,                 # Boolean (>2x average)
        "volume_trend": "increasing",      # "increasing", "decreasing", "stable"

        # ================================================================
        # STOCHASTIC (for overbought/oversold)
        # ================================================================
        "stoch_k": 68,                     # Stochastic %K
        "stoch_d": 65,                     # Stochastic %D
        "stoch_range": "neutral",          # "oversold" (<20), "neutral", "overbought" (>80)
        "stoch_bullish_cross": 0,          # Boolean (%K crossed above %D)
        "stoch_bearish_cross": 0,          # Boolean (%K crossed below %D)

        # ================================================================
        # SENTIMENT (EXTREMELY POWERFUL!)
        # ================================================================
        "sentiment_score": 0.65,           # Overall sentiment (-1 to 1)
        "sentiment_regime": "bullish",     # "bearish", "neutral", "bullish"
        "sentiment_direction": "improving",# "improving", "declining", "stable"

        # Sentiment derivatives (GOLD for predictions!)
        "sentiment_velocity": 0.08,        # ΔS/Δt (rate of change per hour)
        "sentiment_acceleration": 0.02,    # Δ²S/Δt² (change in velocity)
        "sentiment_jerk": -0.005,          # Δ³S/Δt³ (change in acceleration)

        # Historical sentiment (for derivative calculations)
        "sentiment_1hr_ago": 0.58,         # Sentiment 1 hour ago
        "sentiment_4hr_ago": 0.52,         # Sentiment 4 hours ago
        "sentiment_24hr_ago": 0.45,        # Sentiment 24 hours ago

        # Fear & Greed Index
        "fear_greed": 72,                  # 0-100
        "fear_greed_class": "greed",       # "fear" (<25), "neutral", "greed" (>75)
        "fear_greed_change_24h": 8,        # Change in last 24h

        # ================================================================
        # NEWS & SOCIAL
        # ================================================================
        "news_volume_1hr": 8,              # Articles in last hour
        "news_volume_24hr": 47,            # Articles in last 24 hours
        "news_sentiment_1hr": 0.72,        # Sentiment of recent news
        "news_sentiment_24hr": 0.58,       # Sentiment of daily news
        "news_importance_avg": 0.68,       # 0-1 (based on source quality)

        "primary_category": "regulation",  # "regulation", "adoption", "technical", "market", "hack"
        "keywords": ["etf", "sec", "approval", "institutional"], # Top keywords
        "social_mentions": 12500,          # Social media mentions
        "social_sentiment": 0.78,          # Social media sentiment

        # ================================================================
        # PRICE & SUPPORT/RESISTANCE
        # ================================================================
        "btc_price": 45000,                # Current price
        "price_change_1h": 0.02,           # 1-hour change (%)
        "price_change_24h": 0.08,          # 24-hour change (%)
        "price_change_7d": 0.15,           # 7-day change (%)

        "near_resistance": 0,              # Boolean (within 2% of resistance)
        "near_support": 0,                 # Boolean (within 2% of support)
        "at_ath": 0,                       # Boolean (all-time high)
        "distance_from_ath": -0.25,        # -25% from ATH

        # ================================================================
        # MARKET PHASE (high-level classification)
        # ================================================================
        "market_phase": "bull_rally",      # "accumulation", "bull_rally", "distribution", "bear_dump"

        # ================================================================
        # TEXT SUMMARIES (for embedding, not filtering)
        # ================================================================
        "news_summary": "Bitcoin ETF approval drives institutional buying surge",
        "technical_setup": "Strong bullish momentum, RSI at 68, MACD bullish crossover",
        "social_summary": "Extremely positive sentiment on Twitter/Reddit",
        "market_conditions": "Bull market confirmed, high volume accumulation"
    }
}
```

## Priority by Use Case

### For Finding Similar Technical Setups (D1 Expansion)

**Top 10 to index** (you can only create 10 metadata indexes):

1. **timestamp** (number) - CRITICAL for time-based filtering
2. **rsi** (number) - Most popular technical indicator
3. **sentiment_velocity** (number) - Powerful predictive signal
4. **fear_greed** (number) - Unique sentiment measure
5. **trend** (string) - "uptrend", "downtrend", "sideways"
6. **macd_signal** (string) - "bullish", "bearish", "neutral"
7. **volatility** (string) - "low", "medium", "high"
8. **volume_ratio** (number) - Volume spike detection
9. **day_of_week** (number) - Temporal pattern discovery
10. **primary_category** (string) - News type filtering

### For Semantic Search Only

Store everything else in metadata (no index needed):
- Text summaries (embedded in vector, not filtered)
- Derived indicators (momentum, slopes, etc.)
- Historical values (sentiment_1hr_ago, etc.)
- Boolean flags (golden_cross, volume_spike, etc.)

## Calculating "Forward-Looking" Indicators

These aren't truly forward-looking (you can't know the future), but they indicate DIRECTION:

### 1. Velocity (Rate of Change)

```python
# Sentiment velocity: How fast is sentiment changing?
sentiment_velocity = (sentiment_now - sentiment_1hr_ago) / 1  # per hour

# RSI slope: Is RSI rising or falling?
rsi_slope = (rsi_now - rsi_5_periods_ago) / 5  # per period

# SMA slope: Is moving average trending up or down?
sma_slope = (sma_20_now - sma_20_5_days_ago) / 5  # per day
```

### 2. Acceleration (Rate of Change of Velocity)

```python
# Sentiment acceleration: Is improvement accelerating or slowing?
velocity_now = (sentiment_now - sentiment_1hr_ago) / 1
velocity_1hr_ago = (sentiment_1hr_ago - sentiment_2hr_ago) / 1
sentiment_acceleration = velocity_now - velocity_1hr_ago
```

### 3. Relative Position

```python
# How far above/below key levels?
price_vs_sma200 = current_price / sma_200  # 1.08 = 8% above

# Position in Bollinger Bands (0 = lower band, 1 = upper band)
bb_position = (price - bb_lower) / (bb_upper - bb_lower)
```

### 4. Momentum

```python
# Price momentum over different periods
momentum_5 = (price_now - price_5_periods_ago) / price_5_periods_ago
momentum_10 = (price_now - price_10_periods_ago) / price_10_periods_ago
```

## Example: Complete Snapshot

```python
snapshot = {
    "id": "2024-01-15T14:00:00Z",
    "values": embedding_384_dims,
    "metadata": {
        # Time
        "timestamp": 1705329600,
        "day_of_week": 1,  # Monday
        "hour_of_day": 14,

        # Core technicals
        "rsi": 68,
        "rsi_range": "neutral",
        "rsi_slope": 0.5,  # Rising 0.5 points per hour

        "macd_signal": "bullish",
        "macd_histogram": 450.5,

        "trend": "uptrend",
        "momentum_5": 0.032,  # 3.2% momentum over 5 periods

        # Sentiment (the secret sauce!)
        "sentiment_score": 0.65,
        "sentiment_velocity": 0.08,  # Improving 0.08 per hour
        "sentiment_acceleration": 0.02,  # Improvement accelerating
        "fear_greed": 72,

        # Volume
        "volume_ratio": 1.45,  # 45% above average

        # News
        "news_volume_1hr": 8,
        "primary_category": "regulation",

        # Price
        "btc_price": 45000,
        "price_vs_sma200": 1.18,  # 18% above 200-day MA

        # Phase
        "market_phase": "bull_rally",

        # Summaries (for embedding)
        "news_summary": "Bitcoin ETF approval drives rally",
        "technical_setup": "Strong bullish momentum, breaking resistance"
    }
}
```

## What Happens Next (Outcome Analysis)

After finding similar periods, you look FORWARD from their timestamps:

```python
# 1. Find similar periods
similar = await vectorize.query(current_embedding)

# 2. For each similar period, look at outcomes
for period in similar:
    timestamp = period.metadata["timestamp"]
    entry_price = period.metadata["btc_price"]

    # Look forward 1 day, 7 days, 30 days
    price_1d = get_price_at(timestamp + 1*86400)
    price_7d = get_price_at(timestamp + 7*86400)
    price_30d = get_price_at(timestamp + 30*86400)

    return_1d = (price_1d - entry_price) / entry_price
    return_7d = (price_7d - entry_price) / entry_price
    return_30d = (price_30d - entry_price) / entry_price

    print(f"Period {timestamp}:")
    print(f"  1-day return: {return_1d:.1%}")
    print(f"  7-day return: {return_7d:.1%}")
    print(f"  30-day return: {return_30d:.1%}")

# 3. Aggregate statistics
avg_7d_return = mean([r.return_7d for r in results])
win_rate = sum(1 for r in results if r.return_7d > 0) / len(results)

print(f"Average 7-day return: {avg_7d_return:.1%}")
print(f"Win rate: {win_rate:.0%}")
```

## Summary

**Store**: Current state indicators (RSI, MACD, sentiment, etc.)
**NOT**: Future indicators (impossible!)
**Analyze**: Outcomes by looking forward from timestamps

**"Forward-looking" really means**:
- Velocity/slope indicators (showing direction)
- Momentum indicators (showing speed)
- Relative position (where are we vs key levels?)

These help predict what MIGHT happen, but you still need to look at historical outcomes to validate!
