# Hybrid Vector-D1 Search Architecture

## Overview

Two-stage search combining semantic understanding (Vectorize) with technical pattern matching (D1) for maximum coverage and statistical significance.

## Problem Statement

**Goal**: Find historical periods similar to current conditions to predict outcomes.

**Challenge**:
- Pure semantic search (Vectorize only): Small sample size (5-10 periods)
- Pure technical search (D1only): Misses semantic context, hard to define "similar"
- Need: Large sample size + semantic understanding

**Solution**: Two-stage hybrid search

## Architecture

```
Current Market State
├─ News: "Bitcoin ETF approval drives institutional buying"
├─ Sentiment: 0.72
└─ Technical: RSI 68, MACD bullish, sentiment velocity 0.08

                    ↓

┌────────────────────────────────────────────────────────────────┐
│ STAGE 1: SEMANTIC SIMILARITY (Vectorize)                      │
│ Time: ~40ms                                                    │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│ Embed current news → Query Vectorize for similar narratives   │
│                                                                │
│ Returns: 5-10 "anchor" periods                                │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ Period 1: 2024-01-15                                     │ │
│ │ News: "ETF approval, institutional surge"                │ │
│ │ Similarity: 0.89                                         │ │
│ │ Metadata: {rsi: 72, macd: "bullish", sentiment_vel: 0.08}│ │
│ ├──────────────────────────────────────────────────────────┤ │
│ │ Period 2: 2023-06-20                                     │ │
│ │ News: "Major banks adopt crypto custody"                 │ │
│ │ Similarity: 0.84                                         │ │
│ │ Metadata: {rsi: 68, macd: "bullish", sentiment_vel: 0.12}│ │
│ ├──────────────────────────────────────────────────────────┤ │
│ │ Period 3: 2022-11-03                                     │ │
│ │ News: "Regulatory clarity improves sentiment"            │ │
│ │ Similarity: 0.81                                         │ │
│ │ Metadata: {rsi: 75, macd: "bullish", sentiment_vel: 0.06}│ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                                │
│ Key insight: These periods FEEL similar (narrative-wise)      │
└────────────────────────────────────────────────────────────────┘

                    ↓

┌────────────────────────────────────────────────────────────────┐
│ PATTERN EXTRACTION                                             │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│ Extract metadata patterns with tolerance:                     │
│                                                                │
│ Pattern 1 (from Period 1):                                    │
│   RSI: 67-77 (±5), MACD: bullish, Sentiment velocity: 0.06-0.10│
│                                                                │
│ Pattern 2 (from Period 2):                                    │
│   RSI: 63-73 (±5), MACD: bullish, Sentiment velocity: 0.10-0.14│
│                                                                │
│ Pattern 3 (from Period 3):                                    │
│   RSI: 70-80 (±5), MACD: bullish, Sentiment velocity: 0.04-0.08│
│                                                                │
└────────────────────────────────────────────────────────────────┘

                    ↓

┌────────────────────────────────────────────────────────────────┐
│ STAGE 2: TECHNICAL PATTERN EXPANSION (D1)                     │
│ Time: ~50-100ms per pattern                                   │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│ For each pattern, query D1 for ALL matching periods:          │
│                                                                │
│ SQL (Pattern 1):                                              │
│   SELECT * FROM chaos_trades                                  │
│   WHERE entry_rsi_14 BETWEEN 67 AND 77                        │
│     AND entry_macd_bullish_cross = 1                          │
│     AND sentiment_velocity BETWEEN 0.06 AND 0.10              │
│     AND sentiment_fear_greed BETWEEN 58 AND 78                │
│     AND entry_volatility_regime = 'medium'                    │
│                                                                │
│ Returns: 52 matching periods                                  │
│                                                                │
│ SQL (Pattern 2):                                              │
│   [Similar query with different ranges]                       │
│ Returns: 61 matching periods                                  │
│                                                                │
│ SQL (Pattern 3):                                              │
│   [Similar query with different ranges]                       │
│ Returns: 48 matching periods                                  │
│                                                                │
│ Total: 161 matching periods (after deduplication: 156)        │
│                                                                │
│ Key insight: These periods have SIMILAR TECHNICAL SETUPS      │
│              even if news narratives were completely different │
└────────────────────────────────────────────────────────────────┘

                    ↓

┌────────────────────────────────────────────────────────────────┐
│ OUTCOME ANALYSIS                                               │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│ Analyze what happened after all 156 periods:                  │
│                                                                │
│ Statistics:                                                    │
│ • Total periods: 156                                           │
│ • Profitable: 102 (65.4% win rate)                            │
│ • Losing: 54                                                   │
│ • Avg 7-day return: +8.3%                                     │
│ • Avg winning return: +14.2%                                  │
│ • Avg losing return: -6.1%                                    │
│ • Max drawdown: -18.5%                                        │
│ • Sharpe ratio: 1.8                                           │
│                                                                │
│ Confidence: HIGH (sample size = 156)                          │
│                                                                │
│ Decision: BULLISH signal with strong historical precedent     │
└────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
┌─────────────┐
│ Vectorize   │  Stores embeddings + metadata
│ 384-dim     │  - news_summary (embedded)
│ ~1000 vecs  │  - sentiment (embedded)
│             │  - technical_setup (embedded)
│             │  - RSI, MACD, sentiment_velocity (metadata)
│             │  - fear_greed, volatility, trend (metadata)
└──────┬──────┘
       │
       │ Query: Find similar narratives (40ms)
       │ Returns: 5-10 periods with metadata
       ↓
┌─────────────┐
│ D1 Database │  Stores ALL historical trades
│ chaos_trades│  - 50,000+ records
│             │  - Full technical indicators
│             │  - Sentiment derivatives
│             │  - Price data
│             │  - Outcomes
└──────┬──────┘
       │
       │ Query: Find matching patterns (50-100ms per pattern)
       │ Returns: 50-200 periods per pattern
       ↓
┌─────────────┐
│ Analysis    │  Aggregate statistics
│ Engine      │  - Win rates
│             │  - Avg returns
│             │  - Risk metrics
└─────────────┘
```

## Why This Works

### Stage 1: Vectorize (Semantic Anchor)

**Purpose**: Find periods that "feel" similar

**Advantages**:
- Semantic understanding: "ETF approval" ≈ "Institutional adoption"
- Fast: ~40ms for top-10 results
- Quality: Returns truly similar market narratives
- Metadata extraction: Get technical indicators from similar periods

**Limitations**:
- Small sample: Only 5-10 periods
- Limited statistical significance
- Dependent on having similar historical narratives

### Stage 2: D1 (Technical Expansion)

**Purpose**: Find ALL periods matching technical conditions

**Advantages**:
- Large sample: 50-200+ periods
- Statistical significance
- Finds periods you might have missed
- Works even if news narrative was different

**Limitations**:
- Slower: 50-100ms per pattern query
- No semantic understanding
- Must know what indicators to search for

### Combined: Best of Both Worlds

| Metric | Vectorize Only | D1 Only | Hybrid |
|--------|---------------|---------|--------|
| Sample size | 5-10 | ??? (hard to define) | 50-200+ |
| Semantic understanding | ✓ | ✗ | ✓ |
| Statistical significance | ✗ | ✓ | ✓ |
| Speed | 40ms | 50-100ms | 200-400ms total |
| Quality | High | Medium | High |

**Result**:
- 19x larger sample size vs Vectorize alone
- Semantic guidance for what to search for
- High statistical confidence

## Implementation

### Step 1: Semantic Search (Vectorize)

```python
# Generate embedding for current conditions
current_embedding = await ai.run("@cf/baai/bge-small-en-v1.5", {
    "text": [f"News: {news} | Sentiment: {sentiment} | Technical: {technical}"]
})

# Find similar periods
results = await vectorize.query({
    "vector": current_embedding,
    "topK": 10,
    "returnMetadata": true
})

# Extract metadata patterns
patterns = []
for match in results.matches:
    patterns.append({
        "rsi": match.metadata.rsi,
        "macd": match.metadata.macd_signal,
        "sentiment_velocity": match.metadata.sentiment_velocity,
        "fear_greed": match.metadata.fear_greed,
        "volatility": match.metadata.volatility,
        "trend": match.metadata.trend
    })
```

### Step 2: Pattern Expansion (D1)

```python
all_matches = []

for pattern in patterns:
    # Build SQL with tolerances
    sql = """
        SELECT * FROM chaos_trades
        WHERE entry_rsi_14 BETWEEN ? AND ?
          AND entry_macd_bullish_cross = ?
          AND sentiment_velocity BETWEEN ? AND ?
          AND sentiment_fear_greed BETWEEN ? AND ?
          AND entry_volatility_regime = ?
          AND entry_trend_regime = ?
    """

    params = [
        pattern.rsi - 5, pattern.rsi + 5,
        1 if pattern.macd == "bullish" else 0,
        pattern.sentiment_velocity - 0.02,
        pattern.sentiment_velocity + 0.02,
        pattern.fear_greed - 10,
        pattern.fear_greed + 10,
        pattern.volatility,
        pattern.trend
    ]

    matches = await d1.query(sql, params)
    all_matches.extend(matches.rows)

# Deduplicate
unique_matches = deduplicate(all_matches)
```

### Step 3: Outcome Analysis

```python
# Analyze what happened after each period
outcomes = []
for match in unique_matches:
    future_price = get_price_after(match.timestamp, days=7)
    return_pct = (future_price - match.entry_price) / match.entry_price

    outcomes.append({
        "timestamp": match.timestamp,
        "return_7d": return_pct,
        "profitable": return_pct > 0
    })

# Statistics
win_rate = sum(1 for o in outcomes if o.profitable) / len(outcomes)
avg_return = sum(o.return_7d for o in outcomes) / len(outcomes)

print(f"Win rate: {win_rate:.1%}")
print(f"Avg return: {avg_return:.1%}")
print(f"Sample size: {len(outcomes)}")
```

## Performance

### Latency Breakdown

```
Stage 1: Vectorize semantic search          40ms
Stage 2: Extract patterns                    2ms
Stage 3: D1 queries (3 patterns × 60ms)   180ms
Stage 4: Deduplicate & analyze               8ms
────────────────────────────────────────────────
TOTAL:                                     230ms
```

**Still fast enough for real-time trading decisions!**

### Scalability

| Records in D1 | Vectorize vectors | Total matches | Total time |
|--------------|-------------------|---------------|------------|
| 10,000 | 100 | 30-50 | 180ms |
| 50,000 | 500 | 50-150 | 220ms |
| 100,000 | 1,000 | 100-300 | 280ms |
| 500,000 | 5,000 | 200-500 | 400ms |

## Use Cases

### 1. Trading Signal Validation

```
Current: "ETF approval news, bullish momentum"
↓ Vectorize: Find similar narratives
↓ D1: Expand to all similar technical setups
↓ Result: 156 historical examples
→ Decision: 65% won, avg +8.3% return → STRONG BUY
```

### 2. Risk Assessment

```
Current: "Regulatory uncertainty, choppy price action"
↓ Vectorize: Find similar uncertainty periods
↓ D1: Expand to all similar choppy conditions
↓ Result: 83 historical examples
→ Decision: 42% win rate, high volatility → REDUCE POSITION
```

### 3. Pattern Discovery

```
Hypothesis: "Good news during overbought RSI = reversal?"
↓ Vectorize: Find periods with positive news
↓ Filter metadata: RSI > 70
↓ D1: Get all RSI > 70 periods
↓ Compare outcomes
→ Discovery: Good news + RSI > 70 = 58% win rate (not great!)
```

## Summary

**The hybrid approach combines**:
1. **Semantic understanding** from Vectorize (what does this feel like?)
2. **Technical precision** from metadata extraction (what are the exact conditions?)
3. **Statistical power** from D1 expansion (large sample size)

**Result**:
- Find 5-10 semantically similar periods (Vectorize)
- Expand to 50-200 technically similar periods (D1)
- Analyze outcomes with statistical confidence
- Make better trading decisions

**Total time**: ~200-400ms (still real-time!)
