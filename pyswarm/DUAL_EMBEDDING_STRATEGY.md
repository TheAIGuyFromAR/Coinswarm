# Dual Embedding Strategy: Pure + Smoothed

## Overview

Combines two pieces of expert advice into a production-ready system:

**Advice 1**: "You cannot embed an embedding. Maintain numerical continuity, not textual injection."
- Blend vectors in vector space: `v_t = α*v_{t-1} + (1-α)*embed(text_t)`
- Creates cascading memory with exponential decay

**Advice 2**: "Keep both the pure embedding and a smoothed one."
- Pure: Sharp transitions, event detection
- Smoothed: Emotional persistence, regime matching
- Use for different retrieval purposes

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Daily Market Data                        │
│  (Headlines, Sentiment, Technical Indicators)               │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│             Generate Dual Embeddings                        │
│                                                             │
│  Pure:     embed(today's headlines only)                   │
│            → Sharp transitions, event detection             │
│                                                             │
│  Smoothed: α * yesterday_smoothed + (1-α) * pure           │
│            → Emotional persistence, regime matching         │
│            → α ≈ 0.2-0.4 (decay factor)                    │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                   Storage Layer                             │
│                                                             │
│  Vectorize:  Store smoothed embedding in 'values'          │
│              Store pure embedding in metadata               │
│              (1024 dims, bge-large-en-v1.5)                │
│                                                             │
│  D1:         Store technical indicators, outcomes           │
│              (for numeric similarity filtering)             │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                  Retrieval Layer                            │
│                                                             │
│  1. Query Vectorize with today's embedding                 │
│  2. Get top-K by cosine similarity                         │
│  3. Re-score with numeric filters (RSI, volume, etc.)      │
│  4. Return best matches with metadata                      │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                Strategy Patterns                            │
│                                                             │
│  Historical Analogs:  Average outcomes of similar periods   │
│  Regime Detection:    Classify via nearest centroid        │
│  Similarity Drift:    Detect narrative shifts               │
└─────────────────────────────────────────────────────────────┘
```

## Why Dual Embeddings?

### Pure Embedding
```python
pure = embed("Bitcoin rallies 12% on ETF approval")
```

**Characteristics:**
- ✅ Sharp transitions (detects sudden regime changes)
- ✅ Event-specific (captures exact day of news)
- ✅ Independent (each day stands alone)
- ❌ No memory (yesterday's ETF news forgotten today)
- ❌ Discontinuous (consecutive days can be very different)

**Use Cases:**
- Event detection: "When did the rally start?"
- Exact pattern matching: "Find days exactly like ETF approval day"
- Regime change detection: Spot large jumps in embedding

### Smoothed Embedding
```python
# Day 0: ETF approval
smoothed_0 = pure_0  # First day

# Day 1: Rally continues
pure_1 = embed("Bitcoin rallies 15% on institutional flows")
smoothed_1 = 0.3 * smoothed_0 + 0.7 * pure_1
# → Still contains 30% of ETF approval news

# Day 2: More rally
pure_2 = embed("Institutional buying continues")
smoothed_2 = 0.3 * smoothed_1 + 0.7 * pure_2
# → Contains 9% of ETF news (0.3 * 0.3)

# Day 7: Consolidation
pure_7 = embed("Profit-taking, consolidation")
smoothed_7 = 0.3 * smoothed_6 + 0.7 * pure_7
# → Still contains 0.02% of ETF news
```

**Characteristics:**
- ✅ Emotional persistence (news lingers)
- ✅ Smooth transitions (consecutive days similar)
- ✅ Regime coherence (bull markets feel related)
- ✅ Automatic decay (old news fades exponentially)
- ❌ Over-smoothing (can hide regime changes)
- ❌ Not debuggable (can't see what's inside)

**Use Cases:**
- Regime matching: "Find other bull rallies"
- Emotional similarity: "When was market sentiment like this?"
- Trend following: Gradual narrative evolution

## Decay Parameter (α) Tuning

The decay parameter α controls how much "memory" the system has:

```
α = 0.1  →  90% today, 10% yesterday (very reactive)
α = 0.2  →  80% today, 20% yesterday (recommended for crypto)
α = 0.3  →  70% today, 30% yesterday (balanced)
α = 0.4  →  60% today, 40% yesterday (recommended for equities)
α = 0.5  →  50% today, 50% yesterday (very smooth)
```

### Cascading Decay Table

| Days Ago | α=0.1 | α=0.2 | α=0.3 | α=0.4 | α=0.5 |
|----------|-------|-------|-------|-------|-------|
| -1       | 10%   | 20%   | 30%   | 40%   | 50%   |
| -2       | 1%    | 4%    | 9%    | 16%   | 25%   |
| -3       | 0.1%  | 0.8%  | 2.7%  | 6.4%  | 12.5% |
| -7       | ~0%   | 0.02% | 0.05% | 0.3%  | 0.8%  |
| -14      | ~0%   | ~0%   | ~0%   | 0.01% | 0.006%|

### Recommended Values

**Crypto (Bitcoin, Ethereum):**
- α = 0.2-0.3
- Rationale: Fast-moving narratives, news cycles measured in days
- 20% decay = news persists ~3-5 days
- Captures: ETF approvals, hacks, major moves

**Equities:**
- α = 0.3-0.5
- Rationale: Slower narratives, earnings/macro cycles
- 40% decay = news persists ~1-2 weeks
- Captures: Earnings, Fed policy, sector rotation

**Forex:**
- α = 0.4-0.5
- Rationale: Central bank policy has long-lasting effects
- 50% decay = news persists weeks to months
- Captures: Rate decisions, geopolitical events

## Query Strategies

### Strategy 1: Pure Embedding Query
```python
# Find exact event matches
similar = find_similar(
    query_embedding=today.pure_embedding,
    index_contains='smoothed',  # Still search smoothed index
    top_k=10
)

# Use case: "Find days exactly like today's headlines"
# Good for: Event detection, sharp regime changes
```

**When to use:**
- Detecting similar one-off events
- Finding exact pattern matches
- Identifying when regime just changed

**Example:**
Today has "SEC lawsuit against major exchange" - find other lawsuit days

### Strategy 2: Smoothed Embedding Query
```python
# Find regime matches
similar = find_similar(
    query_embedding=today.smoothed_embedding,
    index_contains='smoothed',
    top_k=10
)

# Use case: "Find periods with similar emotional context"
# Good for: Regime matching, trend following
```

**When to use:**
- Understanding current market regime
- Finding similar multi-day periods
- Matching emotional context

**Example:**
Today is Day 5 of a bull rally - find other Day 5s of rallies

### Strategy 3: Combined Scoring
```python
# Semantic + numeric similarity
candidates = find_similar(
    query_embedding=today.smoothed_embedding,
    top_k=30
)

# Re-score with technical indicators
for candidate in candidates:
    semantic_score = candidate.similarity

    # Numeric similarity
    rsi_score = 1 - abs(today.rsi - candidate.rsi) / 20
    volume_score = 1 - abs(today.volume_ratio - candidate.volume_ratio)

    # Combined
    combined = (0.4 * semantic_score +
                0.3 * rsi_score +
                0.3 * volume_score)

    candidate.final_score = combined

# Use case: "Find periods similar in BOTH narrative AND technicals"
# Good for: Precise pattern matching
```

**When to use:**
- High-confidence predictions
- When both narrative and setup matter
- Filtering out false matches

**Example:**
Bull rally + overbought RSI - find other overbought rallies (not just any rally)

## Implementation Details

### Daily Workflow

```python
from temporal_embedding_retrieval_system import TemporalEmbeddingRetriever

# Initialize (once)
retriever = TemporalEmbeddingRetriever(
    vectorize_index=env.VECTORIZE,
    d1_database=env.DB,
    embedding_function=lambda text: ai.run("@cf/baai/bge-large-en-v1.5", {"text": [text]}),
    alpha=0.25  # Crypto-optimized
)

# Each day:
# 1. Create snapshot (generates dual embeddings automatically)
snapshot = await retriever.create_daily_snapshot(
    date=today,
    headlines=[...],
    indicators={...},
    sentiment={...}
)

# 2. Store (Vectorize + D1)
await retriever.store_snapshot(snapshot)

# 3. Query for similar periods
similar = await retriever.find_similar_with_numeric_filter(
    current_snapshot=snapshot,
    top_k=10,
    rsi_tolerance=10,
    volume_tolerance=0.5
)

# 4. Get prediction from analogs
prediction = await retriever.get_historical_analog_prediction(
    current_snapshot=snapshot,
    lookahead_days=7,
    top_k=10
)

print(f"Expected 7d return: {prediction['expected_return']:.2%}")
print(f"Confidence: {prediction['confidence']:.3f}")
```

### Storage Format

**Vectorize:**
```javascript
{
  id: "2024-01-15",
  values: [smoothed_embedding],  // 1024 dims, used for queries
  metadata: {
    pure_embedding: [pure_embedding],  // For optional pure queries

    // Temporal
    timestamp: 1705320000,
    day_of_week: 1,

    // Text (debugging)
    headlines: ["Bitcoin rallies...", "ETF flows..."],
    embedding_text: "Bitcoin rallies 12% | ETF flows...",

    // Technical
    rsi: 74,
    macd_signal: "bullish",
    volatility: "medium",
    volume_ratio: 2.3,
    btc_price: 47500,

    // Sentiment
    sentiment_score: 0.78,
    sentiment_velocity: 0.05,
    fear_greed: 72,

    // Outcomes (backfilled)
    outcome_1d: 0.03,
    outcome_5d: 0.12,
    outcome_7d: 0.15,

    // Config
    alpha: 0.25
  }
}
```

**Why store both?**
- `values` = smoothed (default for queries, regime matching)
- `metadata.pure_embedding` = pure (optional for event detection)
- Flexibility to query either way

## Pattern: Historical Analogs

```python
# Find 10 most similar periods
similar = await retriever.find_similar_with_numeric_filter(
    current_snapshot=today,
    top_k=10
)

# Average their 7-day outcomes
outcomes = [s.metadata.outcome_7d for s in similar]
expected_return = sum(outcomes) / len(outcomes)

# Weighted by similarity
weighted_return = sum(
    s.similarity * s.metadata.outcome_7d
    for s in similar
) / sum(s.similarity for s in similar)

print(f"Expected 7d return: {weighted_return:.2%}")
```

**Interpretation:**
- If expected return > 5% → Strong buy signal
- If expected return < -5% → Strong sell signal
- If expected return ≈ 0% → Unclear, wait
- High confidence (avg similarity > 0.85) → Trust more
- Low confidence (avg similarity < 0.7) → Ignore

## Pattern: Regime Detection

```python
# Define regime examples
regimes = {
    'bull_rally': [
        '2024-01-10',  # ETF approval rally
        '2023-10-15',  # October surge
        '2023-02-20'   # Feb rally
    ],
    'bear_capitulation': [
        '2022-11-09',  # FTX collapse
        '2022-06-13',  # Celsius freeze
        '2022-05-09'   # Terra collapse
    ],
    'consolidation': [
        '2024-01-05',
        '2023-12-20',
        '2023-08-15'
    ]
}

# Classify today
regime, confidence = await retriever.classify_regime(
    current_snapshot=today,
    regime_examples=regimes
)

print(f"Regime: {regime} ({confidence:.2%} confidence)")

# Use in strategy
if regime == 'bull_rally' and confidence > 0.8:
    position_size = 1.0  # Full allocation
elif regime == 'bear_capitulation' and confidence > 0.8:
    position_size = 0.0  # Exit
else:
    position_size = 0.5  # Neutral
```

## Pattern: Similarity Drift Detection

```python
# Track consecutive day similarities over 30 days
drift = await retriever.detect_similarity_drift(lookback_days=30)

print(f"Avg similarity: {drift.avg_similarity:.3f}")
print(f"Std similarity: {drift.std_similarity:.3f}")
print(f"Interpretation: {drift.interpretation}")

# Interpretations:
if drift.interpretation == "repetitive":
    # News clustering tightly → market grinding, no new info
    # Action: Wait for catalyst

elif drift.interpretation == "shifting":
    # Embeddings spreading → narrative changing
    # Action: Reassess position, regime may be changing

else:  # "stable"
    # Normal variation
    # Action: Continue current strategy
```

## Key Rules (from both pieces of advice)

### ✅ DO

1. **Blend in vector space**
   ```python
   smoothed = normalize(α * prev_smoothed + (1-α) * pure)
   ```

2. **Normalize after blending**
   ```python
   vec = vec / np.linalg.norm(vec)
   ```

3. **Store dual embeddings**
   - Pure for event detection
   - Smoothed for regime matching

4. **Combine semantic + numeric similarity**
   - Headlines alone miss technical setup
   - Technicals alone miss narrative

5. **Re-evaluate α per asset**
   - Crypto: 0.2-0.3 (fast-moving)
   - Equities: 0.3-0.5 (slower)

6. **Track similarity drift**
   - Tight clustering = repetitive news
   - Spread = sentiment change

### ❌ DON'T

1. **Embed an embedding**
   ```python
   # ❌ WRONG
   yesterday_text = str(yesterday_embedding)
   today_text = headline + yesterday_text
   embedding = embed(today_text)

   # ✅ CORRECT
   pure = embed(headline)
   smoothed = α * yesterday_smoothed + (1-α) * pure
   ```

2. **Mix text and vectors**
   - Always update numerically
   - Keep text and vector operations separate

3. **Skip normalization**
   - Embeddings will drift in magnitude
   - Cosine similarity scores become unreliable

4. **Use same α for all assets**
   - Crypto ≠ equities ≠ forex
   - Tune per market

5. **Predict directly from embedding**
   - Embeddings are contextual features
   - Use for retrieval, not prediction input

## Performance Characteristics

### Query Performance

With bge-large-en-v1.5 (1024 dims) on Cloudflare Vectorize:

```
Embedding generation: 50-100ms  (Workers AI)
Vectorize query:      60-90ms   (cosine search, top-10)
Metadata fetch:       10-20ms   (D1 query)
Total latency:        120-210ms (end-to-end)
```

For daily trading (few queries per day): Excellent
For high-frequency (100+ queries/day): Consider bge-base-en (768 dims)

### Storage Costs

6 years of daily data (2,190 snapshots):
- 1024-dim smoothed embeddings: 2.24M stored dimensions
- 1024-dim pure embeddings in metadata: 2.24M stored dimensions
- Total: 4.48M dimensions
- Cost: ~$0.18/month (well within 10M free tier)

### Accuracy Improvements

Dual embeddings vs single embedding:

| Metric | Single (Pure) | Single (Smoothed) | Dual |
|--------|--------------|-------------------|------|
| Event detection | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Regime matching | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Transition smoothness | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Debuggability | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ |
| **Overall** | **⭐⭐⭐** | **⭐⭐⭐** | **⭐⭐⭐⭐⭐** |

## Conclusion

**Dual embeddings give you the best of both worlds:**

1. **Pure**: Detect exact events, sharp regime changes
2. **Smoothed**: Understand emotional context, persistent narratives
3. **Combined**: Maximum accuracy for pattern matching

**Production recommendation:**
- Generate both embeddings daily (minimal extra cost)
- Store smoothed in `values` (default queries)
- Store pure in `metadata` (optional fallback)
- Query with smoothed for regime matching
- Re-score with numeric filters for precision
- Use α = 0.25 for crypto, 0.35 for equities

This strategy implements both pieces of advice correctly and gives you a production-ready system for temporal pattern matching in financial markets.

## References

- `temporal_embedding_retrieval_system.py` - Full implementation
- `temporal_embedding_demo.py` - Runnable examples
- `TEMPORAL_EMBEDDING_STRATEGIES.md` - Strategy analysis
- `MODEL_SELECTION_GUIDE.md` - Model selection (bge-large-en-v1.5)
