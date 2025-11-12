# Derivative Tracking Guide: Understanding Momentum Changes

## The Physics of Market Sentiment

Just like in physics, tracking higher-order derivatives reveals **hidden momentum** that static values can't show.

### The Derivative Hierarchy

```
VALUE (0th)  →  VELOCITY (1st)  →  ACCELERATION (2nd)  →  JERK (3rd)  →  SNAP (4th)
Position         Speed               Speeding up          Rate of        Explosive
                                    or slowing           speeding up    changes
```

## What Each Derivative Means

### Sentiment Example

**Scenario**: Bitcoin ETF approval rally

```
Day 0 (ETF Approval):
  Sentiment:       0.85 (very bullish)
  Velocity:        +0.20/day (rapidly improving)
  Acceleration:    +0.10/day² (improvement is speeding up)
  Jerk:            +0.05/day³ (momentum is building)
  Snap:            +0.02/day⁴ (parabolic momentum building)

  Interpretation: EXPLOSIVE BULLISH MOMENTUM
  Signal: Strong buy, but watch for bubble

Day 3 (Peak Euphoria):
  Sentiment:       0.95 (euphoric)
  Velocity:        +0.05/day (still improving but slower)
  Acceleration:    -0.05/day² (improvement is slowing)
  Jerk:            -0.03/day³ (momentum is fading)
  Snap:            -0.01/day⁴ (momentum fade is accelerating)

  Interpretation: TOPPING PATTERN
  Signal: Take profits, distribution phase starting

Day 7 (Reversal):
  Sentiment:       0.70 (still positive but declining)
  Velocity:        -0.15/day (declining)
  Acceleration:    -0.08/day² (decline is speeding up)
  Jerk:            -0.04/day³ (negative momentum building)
  Snap:            -0.02/day⁴ (crash risk building)

  Interpretation: EARLY CRASH SIGNAL
  Signal: Exit or short
```

## Trading Interpretation by Derivative

### 0th Order: VALUE
**What it is**: The actual measurement at a point in time

**Sentiment**: 0.85 (bullish)
**Engagement**: 10,000 likes/hour
**News count**: 50 articles/day

**Trading signal**: Baseline context only, not actionable alone

---

### 1st Order: VELOCITY
**What it is**: Rate of change per unit time

```python
velocity = (value_now - value_previous) / time_delta
```

**Examples**:
- **Sentiment velocity**: +0.2/day = Sentiment improving 0.2 points per day
- **Engagement velocity**: +1000/hour = Getting 1000 more engagements per hour
- **News velocity**: +10 articles/day = News coverage accelerating

**Trading signals**:
- `velocity > 0` → Uptrend (bullish)
- `velocity < 0` → Downtrend (bearish)
- `velocity ≈ 0` → Sideways (neutral)
- `|velocity|` large → Strong trend

**Example**:
```
Sentiment: 0.70 → 0.80 → 0.85 (over 3 days)
Velocity: +0.05/day (steady improvement)
Signal: Bullish trend, but is it accelerating?
```

---

### 2nd Order: ACCELERATION
**What it is**: Rate of change of velocity (how fast velocity changes)

```python
acceleration = (velocity_now - velocity_previous) / time_delta
```

**Examples**:
- **Sentiment acceleration**: +0.1/day² = Velocity increasing by 0.1 per day
  - Day 0: velocity = +0.05/day
  - Day 1: velocity = +0.15/day
  - Day 2: velocity = +0.25/day (speeding up!)

**Trading signals**:
- `acceleration > 0, velocity > 0` → **Markup phase** (bull run accelerating)
- `acceleration < 0, velocity > 0` → **Distribution** (rally slowing, top forming)
- `acceleration < 0, velocity < 0` → **Markdown phase** (crash accelerating)
- `acceleration > 0, velocity < 0` → **Accumulation** (decline slowing, bottom forming)

**Example**:
```
Day 0: velocity = +0.05/day
Day 1: velocity = +0.10/day
Day 2: velocity = +0.15/day
Acceleration: +0.05/day²

Interpretation: Not just improving, but improvement is SPEEDING UP
Signal: Strong buy - momentum building
```

---

### 3rd Order: JERK
**What it is**: Rate of change of acceleration (how fast acceleration changes)

```python
jerk = (acceleration_now - acceleration_previous) / time_delta
```

**Why it matters**: Reveals **momentum changes** invisible in acceleration

**Examples**:
- **Positive jerk**: Acceleration is increasing → momentum building
- **Negative jerk**: Acceleration is decreasing → momentum fading

**Trading signals**:

**Jerk > 0 (Momentum Building)**:
```
Day 0: acceleration = +0.02/day²
Day 1: acceleration = +0.05/day²
Day 2: acceleration = +0.10/day²
Jerk: +0.04/day³

Interpretation: Momentum is BUILDING
Not just accelerating, but acceleration itself is speeding up
Signal: Early bull run - get in now before parabolic
```

**Jerk < 0 (Momentum Fading)**:
```
Day 0: acceleration = +0.10/day²
Day 1: acceleration = +0.05/day²
Day 2: acceleration = -0.02/day²
Jerk: -0.06/day³

Interpretation: Momentum is FADING
Still accelerating but less so - topping pattern
Signal: Take profits - distribution starting
```

**Real-world analogy**:
- You're in a car accelerating (velocity increasing)
- Jerk > 0: You're pressing the gas pedal harder (acceleration increasing)
- Jerk < 0: You're easing off the gas (acceleration decreasing)

---

### 4th Order: SNAP (Jounce)
**What it is**: Rate of change of jerk

```python
snap = (jerk_now - jerk_previous) / time_delta
```

**Why it matters**: Reveals **explosive changes** and **regime shifts**

**Examples**:

**Positive Snap (Parabolic Growth)**:
```
Day 0: jerk = +0.02/day³
Day 1: jerk = +0.05/day³
Day 2: jerk = +0.10/day³
Snap: +0.04/day⁴

Interpretation: PARABOLIC MOMENTUM BUILDING
The rate at which momentum is building is itself accelerating
Signal: BUBBLE WARNING - extreme FOMO, blow-off top forming
```

**Negative Snap (Crash Incoming)**:
```
Day 0: jerk = -0.02/day³
Day 1: jerk = -0.06/day³
Day 2: jerk = -0.12/day³
Snap: -0.05/day⁴

Interpretation: MOMENTUM COLLAPSE ACCELERATING
The rate at which momentum is fading is accelerating
Signal: CRASH WARNING - capitulation forming
```

**Real-world analogy**:
- Jerk tells you if you're pressing the gas harder or softer
- Snap tells you if the **rate** at which you press is changing
- Snap > 0: You're jamming the gas pedal to the floor faster and faster (panic buying)
- Snap < 0: You're slamming the brakes harder and harder (panic selling)

---

## Regime Classification Using Derivatives

### Wyckoff Market Cycles

```
┌─────────────────────────────────────────────────────────┐
│  ACCUMULATION  │    MARKUP    │ DISTRIBUTION │ MARKDOWN │
│                │              │              │          │
│  Building      │  Bull Run    │  Topping     │  Crash   │
│  from bottom   │              │              │          │
└─────────────────────────────────────────────────────────┘
```

**Derivative Signatures**:

#### 1. ACCUMULATION (Bottom Building)
```
Momentum:        Negative but improving
Velocity:        < 0 (still declining)
Acceleration:    > 0 (decline slowing)
Jerk:            > 0 (momentum building)
Snap:            > 0 (building accelerating)

Example:
Day 0: sentiment = 0.20 (bearish)
Day 1: sentiment = 0.25 (less bearish)
Day 2: sentiment = 0.32 (improving faster)
Day 3: sentiment = 0.42 (improvement accelerating)

Signal: Smart money accumulating, prepare to buy
```

#### 2. MARKUP (Bull Run)
```
Momentum:        Positive and accelerating
Velocity:        > 0 (rising)
Acceleration:    > 0 (rise speeding up)
Jerk:            > 0 (momentum building)
Snap:            0 to +++ (normal to parabolic)

Example:
Day 0: sentiment = 0.50
Day 1: sentiment = 0.60 (+0.10)
Day 2: sentiment = 0.72 (+0.12, accelerating)
Day 3: sentiment = 0.86 (+0.14, still accelerating)

Signal: Bull run in progress
  - If snap > 0: Bubble forming, plan exit
  - If snap ≈ 0: Healthy rally, hold
```

#### 3. DISTRIBUTION (Topping)
```
Momentum:        Positive but fading
Velocity:        > 0 (still rising)
Acceleration:    < 0 (rise slowing)
Jerk:            < 0 (momentum fading)
Snap:            < 0 (fade accelerating)

Example:
Day 0: sentiment = 0.90 (+0.15/day)
Day 1: sentiment = 0.95 (+0.05/day, slowing)
Day 2: sentiment = 0.97 (+0.02/day, almost flat)
Day 3: sentiment = 0.96 (-0.01/day, reversal)

Signal: Smart money distributing, prepare to sell
```

#### 4. MARKDOWN (Crash)
```
Momentum:        Negative and accelerating
Velocity:        < 0 (falling)
Acceleration:    < 0 (fall speeding up)
Jerk:            < 0 (negative momentum building)
Snap:            < 0 (crash accelerating)

Example:
Day 0: sentiment = 0.80 (-0.10/day)
Day 1: sentiment = 0.65 (-0.15/day, accelerating)
Day 2: sentiment = 0.45 (-0.20/day, panic)
Day 3: sentiment = 0.20 (-0.25/day, capitulation)

Signal: Crash in progress
  - If snap < 0: Capitulation, crash accelerating
  - If snap > 0: Decline slowing, bottom forming
```

---

## Practical Trading Rules

### Rule 1: Jerk Divergence
```
If price is rising but sentiment_jerk < 0:
  → Momentum is fading despite price rise
  → Distribution phase (smart money selling to retail)
  → Signal: Take profits

If price is falling but sentiment_jerk > 0:
  → Momentum is building despite price fall
  → Accumulation phase (smart money buying the dip)
  → Signal: Buy the dip
```

### Rule 2: Snap as Bubble/Crash Detector
```
If snap > 0.01 and sentiment > 0.8:
  → Parabolic euphoria (2017, 2021 tops)
  → Signal: Extreme bubble warning, exit

If snap < -0.01 and sentiment < 0.3:
  → Parabolic panic (March 2020, FTX collapse)
  → Signal: Capitulation bottom, buy
```

### Rule 3: Multi-Timeframe Derivative Alignment
```
1h jerk > 0 AND 4h jerk > 0 AND 1d jerk > 0:
  → Momentum building across all timeframes
  → Signal: Strong buy (all timeframes agree)

1h jerk > 0 BUT 4h jerk < 0 AND 1d jerk < 0:
  → Short-term bounce in longer-term downtrend
  → Signal: Sell the rally (dead cat bounce)
```

### Rule 4: Engagement-Sentiment Divergence
```
If engagement_jerk > 0 but sentiment_jerk < 0:
  → Going viral but sentiment declining (FUD viral)
  → Signal: Bearish (negative news spreading)

If engagement_jerk < 0 but sentiment_jerk > 0:
  → Low engagement but improving sentiment
  → Signal: Quiet accumulation (smart money)
```

---

## Specific Metrics & Interpretations

### Sentiment Derivatives

| Metric | Unit | Bullish | Bearish |
|--------|------|---------|---------|
| **Sentiment** | -1 to 1 | > 0.6 | < -0.3 |
| **Velocity** | points/day | > 0.1 | < -0.1 |
| **Acceleration** | points/day² | > 0.05 | < -0.05 |
| **Jerk** | points/day³ | > 0.01 | < -0.01 |
| **Snap** | points/day⁴ | > 0.005 (bubble!) | < -0.005 (crash!) |

**Regime Classification**:
```python
if jerk > 0.01 and acceleration > 0:
    regime = "markup"  # Bull run
elif jerk < 0 and acceleration > 0:
    regime = "distribution"  # Topping
elif jerk < -0.01 and acceleration < 0:
    regime = "markdown"  # Crash
elif jerk > 0 and acceleration < 0:
    regime = "accumulation"  # Bottom
```

### Engagement Derivatives

| Metric | Unit | Going Viral | Fading |
|--------|------|-------------|--------|
| **Engagement** | count | > 10,000/hr | < 1,000/hr |
| **Velocity** | count/hr | > 1,000/hr | < 100/hr |
| **Acceleration** | count/hr² | > 500/hr² | < -200/hr² |
| **Jerk** | count/hr³ | > 100/hr³ | < -50/hr³ |
| **Snap** | count/hr⁴ | > 50/hr⁴ (parabolic!) | < -25/hr⁴ |

**Viral Stage Classification**:
```python
if snap > 50 and jerk > 100:
    stage = "parabolic"  # Explosive viral growth
elif jerk > 100:
    stage = "viral"  # Going viral
elif jerk > 0 and acceleration > 0:
    stage = "emerging"  # Starting to gain traction
elif jerk < 0 and velocity > 0:
    stage = "peak"  # Viral but slowing
elif velocity < 0:
    stage = "fading"  # Dying down
```

### Narrative Strength Derivatives

| Metric | Interpretation |
|--------|----------------|
| **News velocity** | +10 articles/hr = Media feeding frenzy |
| **News acceleration** | +5 articles/hr² = Coverage exploding |
| **News jerk** | +2 articles/hr³ = Narrative going parabolic |

**Saturation Detection**:
```python
if news_count > 100/day and news_jerk < 0:
    saturation = True  # Media saturated, narrative dying
```

---

## Code Examples

### Calculate Sentiment Derivatives

```python
async def calculate_sentiment_derivatives(
    symbol: str,
    current_timestamp: int,
    granularity_hours: int = 1
) -> dict:
    """
    Calculate all derivatives for sentiment

    Returns: {
        'value': current sentiment,
        'velocity': 1st derivative,
        'acceleration': 2nd derivative,
        'jerk': 3rd derivative,
        'snap': 4th derivative,
        'regime': classification
    }
    """
    # Fetch last 5 time points (need 5 for 4th derivative)
    dt = granularity_hours * 3600  # seconds

    timestamps = [
        current_timestamp - 4*dt,  # t-4
        current_timestamp - 3*dt,  # t-3
        current_timestamp - 2*dt,  # t-2
        current_timestamp - 1*dt,  # t-1
        current_timestamp          # t0
    ]

    sentiments = []
    for ts in timestamps:
        result = await db.query(
            """SELECT sentiment_value FROM sentiment_timeseries
               WHERE symbol = ? AND timestamp = ?""",
            [symbol, ts]
        )
        sentiments.append(result[0]['sentiment_value'] if result else 0)

    # Calculate derivatives
    s0, s1, s2, s3, s4 = sentiments

    # Velocity (1st derivative)
    v = (s4 - s3) / (dt / 3600.0)  # per hour

    # Acceleration (2nd derivative)
    v_prev = (s3 - s2) / (dt / 3600.0)
    a = (v - v_prev) / (dt / 3600.0)

    # Jerk (3rd derivative)
    v_2 = (s2 - s1) / (dt / 3600.0)
    a_prev = (v_prev - v_2) / (dt / 3600.0)
    j = (a - a_prev) / (dt / 3600.0)

    # Snap (4th derivative)
    v_3 = (s1 - s0) / (dt / 3600.0)
    a_2 = (v_2 - v_3) / (dt / 3600.0)
    j_prev = (a_prev - a_2) / (dt / 3600.0)
    snap = (j - j_prev) / (dt / 3600.0)

    # Classify regime
    regime = classify_regime(v, a, j, snap)

    return {
        'value': s4,
        'velocity': v,
        'acceleration': a,
        'jerk': j,
        'snap': snap,
        'regime': regime
    }

def classify_regime(velocity, acceleration, jerk, snap):
    """Classify market regime based on derivatives"""

    if jerk > 0.01 and snap > 0.005:
        return "parabolic_bull"  # Bubble forming
    elif jerk > 0.01 and acceleration > 0:
        return "markup"  # Bull run
    elif jerk < 0 and velocity > 0:
        return "distribution"  # Topping
    elif jerk < -0.01 and snap < -0.005:
        return "parabolic_bear"  # Crash
    elif jerk < -0.01 and acceleration < 0:
        return "markdown"  # Crash
    elif jerk > 0 and velocity < 0:
        return "accumulation"  # Bottoming
    else:
        return "stable"
```

### Bubble/Crash Detector

```python
def detect_bubble_crash(snap: float, jerk: float, sentiment: float) -> dict:
    """
    Detect bubble/crash conditions using derivatives
    """
    bubble_risk = 0.0
    crash_risk = 0.0

    # Bubble detection (positive snap + high sentiment)
    if snap > 0.005 and jerk > 0.01 and sentiment > 0.7:
        bubble_risk = min(1.0, snap / 0.01)  # Scale to 0-1

    # Crash detection (negative snap + low sentiment)
    if snap < -0.005 and jerk < -0.01 and sentiment < 0.3:
        crash_risk = min(1.0, abs(snap) / 0.01)

    # Warnings
    warnings = []
    if bubble_risk > 0.7:
        warnings.append("EXTREME BUBBLE WARNING - Parabolic euphoria")
    elif bubble_risk > 0.5:
        warnings.append("Bubble forming - Consider taking profits")

    if crash_risk > 0.7:
        warnings.append("EXTREME CRASH WARNING - Capitulation forming")
    elif crash_risk > 0.5:
        warnings.append("Crash risk elevated - Reduce exposure")

    return {
        'bubble_risk': bubble_risk,
        'crash_risk': crash_risk,
        'warnings': warnings
    }
```

---

## Storage & Calculation

### Granularity Recommendations

| Metric | 1h | 4h | 1d | 7d |
|--------|----|----|----|----|
| **Sentiment** | ✅ | ✅ | ✅ | ✅ |
| **Engagement** | ✅ | ✅ | ❌ | ❌ |
| **News count** | ✅ | ✅ | ✅ | ❌ |
| **Source credibility** | ❌ | ❌ | ✅ | ✅ |
| **Entity sentiment** | ❌ | ✅ | ✅ | ✅ |

**Why**:
- Social metrics change fast → track hourly
- Credibility changes slowly → track daily/weekly
- Price correlation → track at multiple timeframes

### Update Frequency

```python
# Hourly updates
async def update_hourly_derivatives():
    """Update fast-moving metrics"""
    await update_sentiment_timeseries(granularity='1h')
    await update_engagement_timeseries(granularity='1h')
    await update_narrative_strength_timeseries(granularity='1h')

# Daily updates
async def update_daily_derivatives():
    """Update slow-moving metrics"""
    await update_source_credibility_timeseries(granularity='1d')
    await update_entity_sentiment_timeseries(granularity='1d')
    await update_market_correlation_timeseries(granularity='1d')
```

---

## Advanced Patterns

### Cross-Metric Divergences

**Engagement-Sentiment Divergence**:
```
Engagement jerk > 0 (going more viral)
Sentiment jerk < 0 (sentiment declining)

→ Negative news going viral (FUD spreading)
→ Signal: Bearish
```

**News-Price Divergence**:
```
News velocity > 0 (increasing coverage)
Price velocity < 0 (price falling)

→ Bad news dominating or
→ Price ignoring positive news (weakness)
→ Signal: Bearish
```

### Multi-Timeframe Confirmation

```
1h jerk > 0 AND 4h jerk > 0 AND 1d jerk > 0
→ Momentum building across all timeframes
→ Highest conviction signal
→ Action: Maximum position size

1h jerk > 0 BUT 4h jerk < 0
→ Short-term bounce in medium-term downtrend
→ Lower conviction
→ Action: Trade only, don't invest
```

---

## Summary: Why Derivatives Matter

**Static value**: Tells you where you are
**Velocity**: Tells you which direction you're going
**Acceleration**: Tells you if you're speeding up
**Jerk**: Tells you if momentum is building or fading
**Snap**: Tells you if you're going parabolic (bubble/crash)

**Without derivatives**: You see sentiment is 0.80 (bullish)
**With derivatives**: You see sentiment is 0.80, but jerk < 0 and snap < 0
→ Still bullish but momentum is FADING FAST
→ Distribution phase, time to sell

**Trading edge**: Derivatives let you see regime changes BEFORE they show up in price!
