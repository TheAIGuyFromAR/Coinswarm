# Vectorize Metadata Template with Historical Outcomes

## Overview

This template shows how to store **both indicators AND outcomes** in the same Vectorize record. This enables finding periods with similar setups and INSTANTLY knowing what happened next - no additional lookups needed!

## Two-Phase Storage Strategy

### Phase 1: Create Snapshot (Time T)
Store current market state with NULL outcomes

### Phase 2: Update with Outcomes (Time T + 7/30 days)
Fill in what actually happened after this period

## Complete Metadata Template

```python
{
    "id": "2024-01-15T14:00:00Z",
    "values": [...],  # 384-dim embedding (news + sentiment + technical)

    "metadata": {
        # ================================================================
        # TEMPORAL
        # ================================================================
        "timestamp": 1705329600,
        "day_of_week": 1,
        "hour_of_day": 14,
        "month": 1,

        # ================================================================
        # CURRENT STATE INDICATORS (at time T)
        # ================================================================

        # Trend & Momentum
        "rsi": 68,
        "rsi_range": "neutral",
        "rsi_slope": 0.5,                  # RSI rising 0.5 per hour

        "macd_signal": "bullish",
        "macd_histogram": 450.5,

        "momentum_1": 0.012,               # 1-period momentum
        "momentum_5": 0.032,               # 5-period momentum
        "momentum_10": 0.068,              # 10-period momentum

        "trend": "uptrend",
        "trend_strength": 0.75,

        # Moving Averages
        "sma_20": 43500,
        "sma_50": 42000,
        "sma_200": 38000,
        "price_vs_sma20": 1.03,
        "price_vs_sma50": 1.07,
        "price_vs_sma200": 1.18,
        "sma_slope_20": 0.002,             # SMA-20 trending up
        "sma_alignment": "golden_cross",

        # Volatility
        "atr": 1250.5,
        "atr_pct": 0.028,
        "volatility": "medium",
        "bb_position": 0.85,
        "bb_width": 0.045,

        # Volume
        "volume": 35000000000,
        "volume_ratio": 1.45,              # 45% above average
        "volume_spike": 1,
        "volume_trend": "increasing",

        # Sentiment (THE GOLD!)
        "sentiment_score": 0.65,
        "sentiment_velocity": 0.08,        # 🔥 Improving 0.08/hour
        "sentiment_acceleration": 0.02,    # 🔥 Accelerating!
        "sentiment_jerk": -0.005,          # Acceleration slowing slightly
        "sentiment_direction": "improving",

        "fear_greed": 72,
        "fear_greed_class": "greed",
        "fear_greed_change_24h": 8,        # +8 points in 24h

        # News
        "news_volume_1hr": 8,
        "news_volume_24hr": 47,
        "news_sentiment_1hr": 0.72,
        "primary_category": "regulation",

        # Price
        "btc_price": 45000,                # Entry price
        "price_change_1h": 0.02,
        "price_change_24h": 0.08,

        # Market Phase
        "market_phase": "bull_rally",

        # ================================================================
        # OUTCOMES (filled in after time passes)
        # ================================================================

        # 1-Day Outcomes
        "outcome_1d": 0.023,               # +2.3% return
        "profitable_1d": 1,                # Boolean: profitable
        "max_drawdown_1d": -0.012,         # Worst drawdown: -1.2%
        "peak_return_1d": 0.035,           # Best return during day: +3.5%

        # 7-Day Outcomes
        "outcome_7d": 0.083,               # +8.3% return 🎯
        "profitable_7d": 1,                # Boolean: profitable
        "max_drawdown_7d": -0.025,         # Worst drawdown: -2.5%
        "peak_return_7d": 0.112,           # Best return during period: +11.2%
        "days_to_peak": 5,                 # Took 5 days to reach peak
        "volatility_7d": 0.035,            # Volatility during 7-day period
        "sharpe_7d": 2.3,                  # Risk-adjusted return

        # 30-Day Outcomes
        "outcome_30d": 0.156,              # +15.6% return
        "profitable_30d": 1,               # Boolean: profitable
        "max_drawdown_30d": -0.048,        # Worst drawdown: -4.8%
        "peak_return_30d": 0.203,          # Best return: +20.3%
        "days_to_peak_30d": 18,            # Took 18 days to reach peak
        "volatility_30d": 0.042,           # Volatility during period

        # Outcome Classification
        "outcome_class_7d": "strong_win",  # "strong_win", "weak_win", "weak_loss", "strong_loss"
        "trend_after_7d": "continued",     # "continued", "reversed", "choppy"

        # Risk Metrics
        "hit_stop_loss": 0,                # Did it drop >10%?
        "days_to_recovery": 0,             # If drawdown, days to recover

        # ================================================================
        # TEXT SUMMARIES (for embedding)
        # ================================================================
        "news_summary": "Bitcoin ETF approval drives institutional buying surge",
        "technical_setup": "Strong bullish momentum, RSI 68, MACD bullish",
        "market_conditions": "Bull rally with high volume"
    }
}
```

## Why This Is Powerful

### Before (Two-Step Lookup):
```python
# 1. Find similar periods
similar = await vectorize.query(current_embedding)
# Returns: [T1, T2, T3, ...]

# 2. Look up outcomes separately (slow!)
for ts in similar:
    outcome = await d1.query("SELECT * WHERE timestamp = ?", [ts])
    # Need to query D1 for each result
```

### After (Outcomes in Metadata):
```python
# 1. Find similar periods (same query)
similar = await vectorize.query(current_embedding)

# 2. Outcomes already included! ✨
for period in similar:
    print(f"Setup: RSI {period.rsi}, sentiment velocity {period.sentiment_velocity}")
    print(f"Outcome: {period.outcome_7d:.1%}")  # Already here!
    print(f"Max drawdown: {period.max_drawdown_7d:.1%}")
    # No additional lookups needed!

# Instant statistics
win_rate = sum(1 for p in similar if p.profitable_7d) / len(similar)
avg_return = mean(p.outcome_7d for p in similar)
avg_drawdown = mean(p.max_drawdown_7d for p in similar)
```

## Implementation: Backfill Worker

Create a worker that periodically updates records with outcomes:

```python
async def backfill_outcomes():
    """
    Run daily to update records with outcomes.
    Updates records that are 7/30 days old.
    """
    # Find records from 7 days ago (no outcomes yet)
    seven_days_ago = int(time.time()) - (7 * 24 * 60 * 60)

    # Query Vectorize for records needing 7-day outcomes
    # (You'd need to track this separately or query all and check)
    records_to_update = await get_records_from_timestamp(seven_days_ago)

    for record in records_to_update:
        entry_timestamp = record.metadata["timestamp"]
        entry_price = record.metadata["btc_price"]

        # Calculate outcomes
        prices_7d = get_prices_for_period(entry_timestamp, days=7)

        outcome_7d = (prices_7d[-1] - entry_price) / entry_price
        max_drawdown = calculate_max_drawdown(prices_7d, entry_price)
        peak_return = calculate_peak_return(prices_7d, entry_price)
        days_to_peak = get_days_to_peak(prices_7d)

        # Update the record in Vectorize
        updated_metadata = {
            **record.metadata,
            "outcome_7d": outcome_7d,
            "profitable_7d": 1 if outcome_7d > 0 else 0,
            "max_drawdown_7d": max_drawdown,
            "peak_return_7d": peak_return,
            "days_to_peak": days_to_peak,
            "outcome_class_7d": classify_outcome(outcome_7d),
        }

        # Upsert (same ID = update)
        await vectorize.upsert([{
            "id": record.id,
            "values": record.values,  # Same embedding
            "metadata": updated_metadata
        }])

    print(f"Updated {len(records_to_update)} records with 7-day outcomes")
```

## Metadata Indexes Priority (with outcomes)

Update your metadata indexes to include outcome fields:

```bash
# Core indicators (unchanged)
wrangler vectorize create-metadata-index pyswarm-time-periods \
  --property-name=timestamp --type=number

wrangler vectorize create-metadata-index pyswarm-time-periods \
  --property-name=rsi --type=number

wrangler vectorize create-metadata-index pyswarm-time-periods \
  --property-name=sentiment_velocity --type=number

# Outcome filters (NEW!)
wrangler vectorize create-metadata-index pyswarm-time-periods \
  --property-name=profitable_7d --type=boolean

wrangler vectorize create-metadata-index pyswarm-time-periods \
  --property-name=outcome_7d --type=number

wrangler vectorize create-metadata-index pyswarm-time-periods \
  --property-name=outcome_class_7d --type=string
```

Now you can query like:
```python
# Find similar periods that were PROFITABLE
filter = {
    "rsi": {"$gte": 65, "$lte": 75},
    "sentiment_velocity": {"$gte": 0.05},
    "profitable_7d": {"$eq": 1},           # Only winners!
    "outcome_7d": {"$gte": 0.05}           # At least 5% return
}
```

## D1 Expansion Query (with outcomes)

Your D1 still has all the detailed trade records. Use Vectorize to find patterns, then expand:

```python
# Stage 1: Vectorize (semantic + outcome filtering)
anchor_periods = await vectorize.query(
    vector=current_embedding,
    filter={
        "rsi": {"$gte": 65, "$lte": 75},
        "sentiment_velocity": {"$gte": 0.05},
        "profitable_7d": {"$eq": 1}        # Only look at winners
    }
)

# Stage 2: Extract patterns
patterns = extract_patterns(anchor_periods)

# Stage 3: D1 expansion (find more periods with same setup)
all_matches = await d1.query("""
    SELECT *,
        -- Calculate outcomes on the fly if not in Vectorize
        (SELECT close FROM price_data
         WHERE timestamp = ct.entry_time + (7*86400)) as exit_price_7d
    FROM chaos_trades ct
    WHERE entry_rsi_14 BETWEEN ? AND ?
      AND sentiment_velocity BETWEEN ? AND ?
      AND profitable = 1  -- Only winners
""", params)

# Now you have:
# - 5-10 semantically similar winning periods (Vectorize)
# - 50-200 technically similar winning periods (D1)
# - All with outcomes already attached!
```

## Query Examples with Outcomes

### 1. Find Winning Setups
```python
filter = {
    "rsi": {"$gte": 60, "$lte": 70},
    "sentiment_velocity": {"$gte": 0.05},
    "profitable_7d": {"$eq": 1},
    "outcome_7d": {"$gte": 0.08}  # At least 8% return
}
```

### 2. Find Low-Risk Wins
```python
filter = {
    "sentiment_acceleration": {"$gte": 0.01},
    "profitable_7d": {"$eq": 1},
    "max_drawdown_7d": {"$gte": -0.03}  # Max 3% drawdown
}
```

### 3. Find Fast Movers
```python
filter = {
    "momentum_5": {"$gte": 0.03},
    "profitable_7d": {"$eq": 1},
    "days_to_peak": {"$lte": 3}  # Peaked within 3 days
}
```

## Storage Workflow

```
Day 0 (Time T):
├─ Create snapshot with current indicators
├─ Store: rsi=68, sentiment_velocity=0.08, price=45000
└─ Outcomes: NULL (haven't happened yet)

Day 7 (Time T+7):
├─ Backfill worker runs
├─ Calculate: outcome_7d=+8.3%, max_drawdown=-2.5%
├─ Update same record with outcomes
└─ Now searchable by outcomes!

Day 30 (Time T+30):
├─ Backfill worker runs again
├─ Calculate: outcome_30d=+15.6%, max_drawdown_30d=-4.8%
└─ Update record with 30-day outcomes
```

## Benefits

### ✅ Instant Analysis
- No separate outcome lookups
- Everything in one query
- Filter by outcomes directly

### ✅ Better Pattern Discovery
```python
# Find setups that led to strong wins
filter = {
    "rsi": {"$gte": 60},
    "sentiment_velocity": {"$gte": 0.05},
    "outcome_7d": {"$gte": 0.10},  # >10% return
    "max_drawdown_7d": {"$gte": -0.05}  # <5% drawdown
}
# Instantly get all strong, low-risk winning setups!
```

### ✅ Risk Assessment
```python
# What's the typical drawdown for this setup?
similar = await vectorize.query(current_embedding)
avg_drawdown = mean(p.max_drawdown_7d for p in similar)
worst_drawdown = min(p.max_drawdown_7d for p in similar)

print(f"Expected drawdown: {avg_drawdown:.1%}")
print(f"Worst case: {worst_drawdown:.1%}")
```

### ✅ Timing Analysis
```python
# How long until peak?
similar = await vectorize.query(current_embedding)
avg_days_to_peak = mean(p.days_to_peak for p in similar)

print(f"Typically peaks in {avg_days_to_peak:.1f} days")
# Exit strategy: Hold for N days then take profit
```

## Summary

**Store in Vectorize metadata**:
1. **Current indicators** (RSI, sentiment velocity, momentum, etc.)
2. **Outcomes** (what happened 1/7/30 days later)
3. **Risk metrics** (drawdowns, volatility, days to peak)

**Benefits**:
- Instant outcome analysis (no additional lookups)
- Filter by both setup AND outcome
- Better risk assessment
- Faster pattern discovery

**Workflow**:
1. Create snapshot with current indicators
2. 7 days later: Update with 7-day outcomes
3. 30 days later: Update with 30-day outcomes
4. Query by both setup and outcomes!

This gives you **predictive + historical** in one place! 🎯
