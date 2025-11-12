# Temporal Embedding Strategies: Grouping, Persistence, and Vector Cascading

## The Core Question

How do we construct embeddings that capture:
1. **Current state**: Today's headlines, sentiment, technicals
2. **Recent context**: Important events from past few days
3. **Temporal continuity**: Smooth transitions vs. sharp regime changes
4. **Long-term memory**: Major events that influence markets for weeks

## Strategy 1: Simple Daily Snapshot (Current Approach)

### How It Works
```python
def simple_daily_embedding(date):
    headlines = get_top_headlines(date, limit=5)
    sentiment = get_sentiment(date)
    technical = get_technicals(date)

    text = f"""
    Headlines: {headlines[0]}, {headlines[1]}, {headlines[2]}
    Sentiment: {sentiment.score} ({sentiment.direction})
    Technical: RSI {technical.rsi}, MACD {technical.macd}
    """

    return embed(text)
```

### Characteristics
- ✅ Clean separation between days
- ✅ Easy to understand what each embedding represents
- ✅ Can spot exact day when regime changed
- ❌ No memory of previous days
- ❌ "ETF approval day" and "day after ETF approval" seem unrelated
- ❌ Discontinuous jumps between consecutive days

### Best For
- Identifying specific events
- Backtesting discrete signals
- When you want each day independent

---

## Strategy 2: Sliding Window with Text Decay

### How It Works
```python
def sliding_window_embedding(date, lookback_days=7):
    # Current day (full weight)
    today = {
        'headlines': get_headlines(date),
        'sentiment': get_sentiment(date),
        'technical': get_technicals(date),
        'weight': 1.0
    }

    # Historical headlines with importance threshold and decay
    historical_headlines = []
    for days_ago in range(1, lookback_days + 1):
        past_date = date - timedelta(days=days_ago)

        # Only include important headlines (importance > 0.7)
        important = get_headlines(
            past_date,
            min_importance=0.7  # Regulatory, major hacks, etc.
        )

        # Apply exponential decay
        decay_factor = 0.5 ** days_ago
        # Day -1: 0.5x, Day -2: 0.25x, Day -3: 0.125x, etc.

        for headline in important:
            historical_headlines.append({
                'title': headline['title'],
                'weight': headline['importance'] * decay_factor,
                'days_ago': days_ago
            })

    # Build composite text with weighted repetition
    text_components = []

    # Today's content
    text_components.append(f"TODAY: {format_daily_summary(today)}")

    # Historical context (weighted by importance * decay)
    if historical_headlines:
        # Sort by weight (most important/recent first)
        historical_headlines.sort(key=lambda x: x['weight'], reverse=True)

        # Include top 3 historical events
        for h in historical_headlines[:3]:
            text_components.append(
                f"CONTEXT ({h['days_ago']}d ago, weight={h['weight']:.2f}): {h['title']}"
            )

    combined_text = " | ".join(text_components)
    return embed(combined_text)
```

### Example Output

**Day 0 (ETF Approval):**
```
TODAY: SEC approves Bitcoin spot ETF | Sentiment: 0.85 bullish | RSI: 72
```

**Day 1:**
```
TODAY: Bitcoin rallies 15% on ETF approval hype | Sentiment: 0.78 bullish | RSI: 76
CONTEXT (1d ago, weight=0.50): SEC approves Bitcoin spot ETF
```

**Day 2:**
```
TODAY: Institutional buying continues, new ATH | Sentiment: 0.72 bullish | RSI: 78
CONTEXT (1d ago, weight=0.39): Bitcoin rallies 15% on ETF approval hype
CONTEXT (2d ago, weight=0.25): SEC approves Bitcoin spot ETF
```

**Day 3:**
```
TODAY: Profit-taking begins, consolidation | Sentiment: 0.45 neutral | RSI: 68
CONTEXT (1d ago, weight=0.36): Institutional buying continues, new ATH
CONTEXT (2d ago, weight=0.20): Bitcoin rallies 15% on ETF approval hype
CONTEXT (3d ago, weight=0.13): SEC approves Bitcoin spot ETF
```

### Characteristics
- ✅ Important events persist for multiple days
- ✅ Natural decay - old news becomes less relevant
- ✅ Still text-based, easy to debug
- ✅ "ETF approval" is in embeddings for the next week
- ❌ Headlines repeated verbatim (less elegant)
- ❌ Still somewhat discrete jumps

### Best For
- Capturing event persistence
- Understanding market "regimes" (post-ETF, post-hack, etc.)
- When important news has multi-day impact

---

## Strategy 3: Categorical Persistence

### How It Works

Different event types have different half-lives:

```python
EVENT_PERSISTENCE = {
    'regulatory_approval': 14,     # ETF approvals, legal clarity
    'regulatory_crackdown': 7,     # SEC lawsuits, enforcement
    'major_hack': 5,               # Exchange hacks, exploits
    'institutional_adoption': 10,  # Major companies buying
    'technical_breakout': 2,       # Resistance breaks, ATH
    'macro_news': 21,              # Fed policy, recession
    'protocol_upgrade': 7,         # Ethereum merge, halving
    'social_trend': 1,             # Twitter hype, Reddit trends
}

def categorical_persistence_embedding(date):
    today_events = get_categorized_events(date)

    # Gather historical events based on category persistence
    historical_context = []
    for category, max_days in EVENT_PERSISTENCE.items():
        for days_ago in range(1, max_days + 1):
            past_date = date - timedelta(days=days_ago)
            events = get_events_by_category(past_date, category)

            # Linear decay over category-specific window
            decay = 1.0 - (days_ago / max_days)

            for event in events:
                if event['importance'] > 0.7:
                    historical_context.append({
                        'text': event['title'],
                        'category': category,
                        'weight': event['importance'] * decay,
                        'days_ago': days_ago
                    })

    # Build embedding text
    text = build_composite_text(today_events, historical_context)
    return embed(text)
```

### Example

**Scenario**: ETF approved on Jan 10, hack on Jan 12

**Jan 10:**
```
TODAY: SEC approves Bitcoin spot ETF [regulatory_approval]
```

**Jan 12:**
```
TODAY: Major exchange hacked, $100M stolen [major_hack]
CONTEXT (2d ago): SEC approves Bitcoin spot ETF [still 86% weight, persists 14d]
```

**Jan 14:**
```
TODAY: Market recovers from hack fears [recovery]
CONTEXT (2d ago): Major exchange hacked [60% weight, persists 5d]
CONTEXT (4d ago): SEC approves Bitcoin spot ETF [71% weight, persists 14d]
```

**Jan 17 (hack fully decayed):**
```
TODAY: Continued rally on institutional flows [institutional]
CONTEXT (7d ago): SEC approves Bitcoin spot ETF [50% weight, still present]
# Hack no longer included (5-day window expired)
```

### Characteristics
- ✅ Event-specific decay rates (very realistic)
- ✅ Macro news persists longer than social trends
- ✅ Captures that some events have longer impact
- ✅ Still explainable (text-based)
- ❌ Requires event categorization
- ❌ More complex implementation

### Best For
- Realistic market modeling
- Different trading timeframes
- When event type matters for persistence

---

## Strategy 4: Vector Arithmetic Blending

### How It Works

Instead of including past events in text, directly blend embeddings:

```python
def vector_blending_embedding(date, history_weight=0.3):
    # Generate today's raw embedding
    today_text = build_daily_text(date)
    today_raw = embed(today_text)

    # Get yesterday's FINAL embedding (already blended)
    yesterday_final = get_stored_embedding(date - 1_day)

    if yesterday_final is None:
        return today_raw  # First day

    # Blend: 70% today, 30% yesterday
    today_final = (today_raw * (1 - history_weight) +
                   yesterday_final * history_weight)

    # Normalize to unit length (important for cosine similarity)
    today_final = normalize(today_final)

    return today_final
```

### What This Creates: Cascading Memory

Since yesterday's embedding already contains the day before, this creates a chain:

```
Day 0: 100% of Day 0
Day 1: 70% of Day 1 + 30% of Day 0
Day 2: 70% of Day 2 + 30% of (70% Day 1 + 30% Day 0)
     = 70% Day 2 + 21% Day 1 + 9% Day 0
Day 3: 70% Day 3 + 21% Day 2 + 9% Day 1 + 2.7% Day 0
Day 4: 70% Day 4 + 21% Day 3 + 9% Day 2 + 2.7% Day 1 + 0.8% Day 0
...
```

**Decay Formula**: Weight of day N days ago = `(history_weight)^N * (1 - history_weight)`

With `history_weight = 0.3`:
- Day -1: 21%
- Day -2: 9%
- Day -3: 2.7%
- Day -7: 0.02%
- Day -14: 0.0005%

### Visualizing the Cascade

```
Day 0: [████████████████████████████████████] 100%

Day 1: [████████████████████████ 70% ][█████ 30%]
        ↑ New content              ↑ Day 0

Day 2: [████████████████████████ 70% ][██ 21%][█ 9%]
        ↑ New content              ↑ Day 1  ↑ Day 0

Day 7: [████████████████████████ 70% ][... declining gradient ... <1%]
        ↑ Today                    ↑ Last 6 days blend into background
```

### Characteristics
- ✅ Extremely smooth temporal transitions
- ✅ Automatic exponential decay (no manual tuning)
- ✅ Every embedding contains market "history"
- ✅ Regime persistence (bull markets feel similar day-to-day)
- ❌ Not human-readable (can't see what's in the blend)
- ❌ Over-smoothing can hide regime changes
- ❌ Consecutive days always similar (by construction)
- ❌ Hard to "reset" after major events

### Example Scenarios

**Bull Run Persistence:**
```
Day 0: ETF approved, rally starts
Day 1: Embedding is 70% new rally + 30% ETF news → High similarity to Day 0
Day 2: Still 9% ETF news → Similar to Day 0 and 1
Day 7: Still 0.02% ETF news → Subtle influence
```

**Sharp Regime Change:**
```
Day 0-6: Steady bull market (embeddings smoothly blend)
Day 7: Major hack, market crashes
  - Embedding is still 30% bull market (yesterday) + 70% crash
  - Similarity to Day 6 is artificially high (30% overlap)
  - Takes 2-3 days for "crash regime" to dominate embedding
```

### Best For
- Modeling persistent market regimes
- When most days are continuations of previous days
- Smooth, gradual transitions
- NOT good for identifying sharp turning points

---

## Strategy 5: Hybrid Approach (RECOMMENDED)

### How It Works

Combine text-based persistence with light vector blending:

```python
def hybrid_temporal_embedding(date):
    # ==========================================
    # STEP 1: Build composite text with explicit persistence
    # ==========================================

    # Today's core data
    today_headlines = get_top_headlines(date, limit=5)
    today_sentiment = get_sentiment(date)
    today_technical = get_technicals(date)

    # Important historical headlines (7-day window)
    historical_headlines = []
    for days_ago in range(1, 8):
        past_date = date - timedelta(days=days_ago)
        important = get_headlines(past_date, min_importance=0.75)

        # Categorize events
        for h in important:
            category = categorize_event(h)
            max_persist = EVENT_PERSISTENCE.get(category, 7)

            # Only include if within category window
            if days_ago <= max_persist:
                # Category-specific decay
                decay = 1.0 - (days_ago / max_persist)
                historical_headlines.append({
                    'title': h['title'],
                    'weight': h['importance'] * decay,
                    'category': category,
                    'days_ago': days_ago
                })

    # Build rich text representation
    text_parts = []

    # Primary content (today)
    text_parts.append(f"""
    PRIMARY ({date.strftime('%Y-%m-%d')}):
    - Headlines: {', '.join(h['title'] for h in today_headlines[:3])}
    - Sentiment: {today_sentiment.score:.2f} ({today_sentiment.direction})
    - Technical: RSI {today_technical.rsi}, MACD {today_technical.macd_signal}
    - Volatility: {today_technical.volatility}, Volume ratio: {today_technical.volume_ratio}
    """.strip())

    # Historical context (top 3 by weight)
    if historical_headlines:
        historical_headlines.sort(key=lambda x: x['weight'], reverse=True)
        for h in historical_headlines[:3]:
            text_parts.append(
                f"CONTEXT (-{h['days_ago']}d, {h['category']}, w={h['weight']:.2f}): {h['title']}"
            )

    combined_text = "\n".join(text_parts)

    # ==========================================
    # STEP 2: Generate embedding from composite text
    # ==========================================
    today_raw = embed(combined_text)

    # ==========================================
    # STEP 3: Light vector blending for continuity
    # ==========================================
    yesterday_final = get_stored_embedding(date - 1_day)

    if yesterday_final:
        # Very light blending (10-15%) just for smoothness
        # This prevents jarring jumps between consecutive days
        # while still letting today's content dominate (85-90%)
        blend_weight = 0.15
        today_final = (today_raw * (1 - blend_weight) +
                       yesterday_final * blend_weight)
        today_final = normalize(today_final)
    else:
        today_final = today_raw

    return today_final
```

### What This Achieves

1. **Explicit Text Persistence** (Step 1)
   - Important events from past week included in text
   - Category-specific decay (regulatory news persists 14d, social trends 1d)
   - Human-readable, debuggable

2. **Semantic Richness** (Step 2)
   - Model naturally understands "post-ETF rally" is similar to "ETF approval"
   - Related events cluster together

3. **Temporal Smoothing** (Step 3)
   - 15% blend with yesterday prevents discontinuous jumps
   - Market regime persistence (bull markets feel coherent)
   - But not so much that regime changes are hidden

### Example: Multi-Day Event

**Jan 10 (ETF Approval):**
```
PRIMARY (2024-01-10):
- Headlines: SEC approves Bitcoin spot ETF, BlackRock launches trading, Institutional flows begin
- Sentiment: 0.85 (bullish)
- Technical: RSI 68, MACD bullish, Volatility medium, Volume ratio 2.3

Embedding: 100% raw (no yesterday to blend)
```

**Jan 11:**
```
PRIMARY (2024-01-11):
- Headlines: Bitcoin surges 12% on ETF hype, Record trading volume, FOMO intensifies
- Sentiment: 0.82 (bullish)
- Technical: RSI 74, MACD bullish, Volatility high, Volume ratio 3.1

CONTEXT (-1d, regulatory_approval, w=0.93): SEC approves Bitcoin spot ETF

Raw embedding generated, then:
Final = 0.85 * raw + 0.15 * Jan10_final
```

**Jan 14:**
```
PRIMARY (2024-01-14):
- Headlines: Profit-taking begins, Consolidation at $48k, Healthy pullback
- Sentiment: 0.45 (neutral)
- Technical: RSI 64, MACD neutral, Volatility medium, Volume ratio 1.2

CONTEXT (-1d, rally, w=0.50): Continued institutional buying
CONTEXT (-4d, regulatory_approval, w=0.71): SEC approves Bitcoin spot ETF

Final = 0.85 * raw + 0.15 * Jan13_final
```

**Jan 24 (ETF news fully decayed):**
```
PRIMARY (2024-01-24):
- Headlines: New resistance at $50k, Technical breakout imminent, Options expiry ahead
- Sentiment: 0.38 (neutral-bullish)
- Technical: RSI 58, MACD neutral, Volatility low, Volume ratio 0.9

# No ETF context (14-day window expired)
CONTEXT (-2d, technical, w=0.33): Support holding at $47k

Final = 0.85 * raw + 0.15 * Jan23_final
```

### Similarity Search Behavior

When searching from "today" (another post-ETF rally day):

1. **Jan 11** will rank high:
   - Text includes "ETF approval" context
   - Vector blend includes Jan 10 (ETF day)
   - Semantic similarity to "post-approval rally"

2. **Jan 14** will rank medium:
   - Still includes ETF context (decayed)
   - But primary content is "consolidation"
   - Similarity score lower due to different regime

3. **Jan 24** will rank low:
   - No ETF context in text
   - Primary content is technical (different theme)
   - Only faint trace via vector cascade (<1%)

### Characteristics
- ✅ Best of both worlds: explicit + implicit persistence
- ✅ Human-readable (text-based) + smooth (vector blend)
- ✅ Category-specific decay (realistic)
- ✅ Light blending prevents discontinuities without over-smoothing
- ✅ Can still detect regime changes (85% new content)
- ✅ Debuggable: can inspect what's in each embedding
- ❌ Most complex implementation
- ❌ Requires event categorization

### Best For
- **Production trading systems** (recommended)
- Balancing accuracy and realism
- When you want explainability + performance

---

## Comparison Table

| Strategy | Explainability | Regime Persistence | Detects Sharp Changes | Complexity | Recommended For |
|----------|---------------|-------------------|----------------------|------------|-----------------|
| **Simple Daily** | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐ | Backtesting discrete signals |
| **Sliding Window** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | Understanding event impact |
| **Categorical Persistence** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | Realistic market modeling |
| **Vector Blending** | ⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐ | Regime-persistent markets |
| **Hybrid** ⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | **Production systems** |

---

## Implementation Recommendations

### For Your Use Case (Daily Trading Decisions)

**Use Hybrid Approach with these parameters:**

```python
HYBRID_CONFIG = {
    # Text-based persistence
    'lookback_days': 7,
    'min_importance_threshold': 0.75,  # Only major news persists
    'max_historical_headlines': 3,     # Top 3 by weight

    # Category-specific persistence
    'event_persistence': {
        'regulatory_approval': 14,
        'regulatory_crackdown': 7,
        'major_hack': 5,
        'institutional_adoption': 10,
        'technical_breakout': 2,
        'macro_news': 21,
        'protocol_upgrade': 7,
        'social_trend': 1,
    },

    # Vector blending
    'blend_weight': 0.15,  # 15% yesterday, 85% today
    'normalize_after_blend': True,
}
```

### For Intraday Trading

Use **lighter persistence**:
- `lookback_days`: 3
- `blend_weight`: 0.05 (5% yesterday)
- Only include events with `importance > 0.9`

### For Swing/Position Trading

Use **heavier persistence**:
- `lookback_days`: 14
- `blend_weight`: 0.25 (25% yesterday)
- Include events with `importance > 0.6`

---

## Testing Different Strategies

Create a comparison script:

```python
async def compare_strategies(date):
    """Generate embeddings using all strategies for comparison"""

    strategies = {
        'simple': simple_daily_embedding(date),
        'sliding': sliding_window_embedding(date, lookback_days=7),
        'categorical': categorical_persistence_embedding(date),
        'vector_blend': vector_blending_embedding(date, history_weight=0.3),
        'hybrid': hybrid_temporal_embedding(date),
    }

    # Find similar periods using each strategy
    for name, embedding in strategies.items():
        results = await vectorize.query(
            vector=embedding,
            topK=10,
            filter={'outcome_7d': {'$gt': 0}}  # Only winners
        )

        print(f"\n{name.upper()} Strategy:")
        for match in results.matches:
            print(f"  {match.id}: {match.score:.3f} - {match.metadata.get('headline_1')}")
```

This will show you how different persistence strategies affect which historical periods are found!

---

## Next Steps

1. **Implement hybrid approach** as default
2. **Create event categorizer** for categorical persistence
3. **Add importance scorer** for headlines
4. **Build comparison dashboard** to visualize different strategies
5. **Backtest** which strategy yields best trading signals

The hybrid approach gives you the best balance of explainability, realism, and performance for daily trading decisions.
