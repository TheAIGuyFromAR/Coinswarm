# Enhanced Embedding Strategy for Time Period Similarity Search

## Recommended Approach: Smart Daily Aggregation

### Core Concept

**One embedding per day** that intelligently captures:
- Key news headlines (top 3-5 most important)
- Overall market narrative/theme
- Sentiment direction and momentum
- Technical setup summary
- Social media vibe
- Market context

### Embedding Text Construction

```python
def build_embedding_text(date: datetime) -> str:
    """
    Construct rich embedding text that captures the day's "market vibe"
    """

    # 1. Get data
    headlines = get_top_headlines(date, limit=5, min_importance=0.6)
    sentiment = get_sentiment_snapshot(date)
    technicals = get_technical_snapshot(date)
    social = get_social_snapshot(date)

    # 2. Identify primary theme/narrative
    theme = identify_primary_theme(headlines)
    # e.g., "institutional_adoption", "regulation", "macro_uncertainty", etc.

    # 3. Construct embedding text
    text = f"""
{theme.upper()}: {headlines[0]['title']}

Key Events:
- {headlines[0]['title']}
- {headlines[1]['title']}
- {headlines[2]['title']}

Market Narrative: {summarize_narrative(headlines)}

Sentiment: {sentiment['regime']} ({sentiment['score']:.2f})
- Direction: {sentiment['direction']} (velocity: {sentiment['velocity']:.3f})
- Fear/Greed: {sentiment['fear_greed']} ({classify_fear_greed(sentiment['fear_greed'])})
- News tone: {sentiment['news_sentiment_1hr']:.2f}

Technical Setup:
- Trend: {technicals['trend']} ({technicals['trend_strength']:.1f})
- RSI: {technicals['rsi']} ({classify_rsi(technicals['rsi'])})
- MACD: {technicals['macd_signal']} crossover
- Volatility: {technicals['volatility']} regime

Social: {social['mentions']:,} mentions, {classify_social_sentiment(social['sentiment'])} sentiment

Market Phase: {get_market_phase(date)}
    """.strip()

    return text
```

### Example Output

```python
# 2024-01-15 snapshot
embedding_text = """
INSTITUTIONAL_ADOPTION: SEC approves Bitcoin spot ETF applications from BlackRock and Fidelity

Key Events:
- SEC approves Bitcoin spot ETF applications from BlackRock and Fidelity
- Major banks announce cryptocurrency custody services
- Institutional buying surge drives price above $45k

Market Narrative: Regulatory clarity drives institutional adoption. First spot Bitcoin ETF approval
marks turning point for mainstream acceptance. Strong institutional demand with minimal selling pressure.

Sentiment: bullish (0.82)
- Direction: improving (velocity: 0.08)
- Fear/Greed: 75 (greed)
- News tone: 0.78

Technical Setup:
- Trend: uptrend (0.75)
- RSI: 72 (overbought)
- MACD: bullish crossover
- Volatility: medium regime

Social: 45,200 mentions, extremely positive sentiment

Market Phase: bull_rally
"""
```

## Alternative Structures for Different Use Cases

### A. Multi-Coin Support

If tracking multiple coins, use coin-prefixed IDs:

```python
{
    "id": "2024-01-15-BTC",
    "embedding": embed("BTC: ETF approval drives rally..."),
    "metadata": {
        "coin": "BTC",
        "timestamp": ...,
        # ... BTC-specific indicators
    }
}

{
    "id": "2024-01-15-SOL",
    "embedding": embed("SOL: Ecosystem growth continues..."),
    "metadata": {
        "coin": "SOL",
        "timestamp": ...,
        # ... SOL-specific indicators
    }
}
```

Then query with metadata filter:
```python
results = await vectorize.query(
    vector=current_embedding,
    filter={"coin": {"$eq": "BTC"}},
    topK=10
)
```

### B. Intraday Windows (Optional)

For intraday trading, create snapshots at key times:

```python
# Market open (9:30 AM ET)
{
    "id": "2024-01-15T09:30:00Z",
    "embedding": embed("Market open: Overnight ETF news drives strong pre-market..."),
    "metadata": {
        "period": "market_open",
        "timestamp": ...,
    }
}

# Midday (12:00 PM ET)
{
    "id": "2024-01-15T12:00:00Z",
    "embedding": embed("Midday: Rally sustained, institutional buying continues..."),
    "metadata": {
        "period": "midday",
        "timestamp": ...,
    }
}

# Market close (4:00 PM ET)
{
    "id": "2024-01-15T16:00:00Z",
    "embedding": embed("Close: Strong finish, minimal profit-taking..."),
    "metadata": {
        "period": "market_close",
        "timestamp": ...,
    }
}
```

### C. Event-Based Snapshots

For major events, create dedicated snapshots:

```python
{
    "id": "2024-01-15-event-etf-approval",
    "embedding": embed("MAJOR EVENT: SEC approves first Bitcoin spot ETF..."),
    "metadata": {
        "event_type": "regulatory_approval",
        "importance": 0.98,
        "timestamp": ...,
    }
}
```

## Implementation Strategy

### Step 1: Smart Headline Aggregation

```python
def get_top_headlines(date: datetime, limit: int = 5, min_importance: float = 0.6) -> list:
    """
    Get most important headlines for the day
    """
    headlines = fetch_headlines(date)

    # Score by importance
    scored = []
    for h in headlines:
        score = calculate_importance(h)
        if score >= min_importance:
            scored.append((score, h))

    # Sort by importance, take top N
    scored.sort(reverse=True)
    return [h for score, h in scored[:limit]]


def calculate_importance(headline: dict) -> float:
    """
    Score headline importance (0-1)
    """
    score = 0.0

    # Source quality
    if headline['source'] in ['bloomberg', 'reuters', 'wsj']:
        score += 0.3
    elif headline['source'] in ['coindesk', 'cointelegraph']:
        score += 0.2

    # Engagement
    if headline['views'] > 10000:
        score += 0.2

    # Keywords
    important_keywords = ['sec', 'etf', 'regulation', 'hack', 'bankruptcy']
    if any(kw in headline['title'].lower() for kw in important_keywords):
        score += 0.3

    # Sentiment extreme
    if abs(headline['sentiment']) > 0.7:
        score += 0.2

    return min(score, 1.0)
```

### Step 2: Theme Identification

```python
def identify_primary_theme(headlines: list) -> str:
    """
    Identify primary market theme from headlines
    """
    themes = {
        'institutional_adoption': ['etf', 'institutional', 'bank', 'custody', 'fidelity', 'blackrock'],
        'regulation': ['sec', 'cftc', 'regulation', 'law', 'compliance', 'legal'],
        'technical_rally': ['breakout', 'resistance', 'support', 'rally', 'surge'],
        'hack_security': ['hack', 'exploit', 'security', 'breach', 'stolen'],
        'macro_uncertainty': ['fed', 'inflation', 'recession', 'unemployment', 'rates'],
        'ecosystem_growth': ['dex', 'defi', 'tvl', 'volume', 'adoption'],
    }

    theme_scores = {theme: 0 for theme in themes}

    for headline in headlines:
        text = headline['title'].lower()
        for theme, keywords in themes.items():
            for keyword in keywords:
                if keyword in text:
                    theme_scores[theme] += 1

    # Return theme with highest score
    return max(theme_scores, key=theme_scores.get)


def summarize_narrative(headlines: list) -> str:
    """
    One-sentence summary of market narrative
    """
    theme = identify_primary_theme(headlines)

    templates = {
        'institutional_adoption': "Regulatory clarity drives institutional adoption and mainstream acceptance",
        'regulation': "Regulatory developments create uncertainty and market volatility",
        'technical_rally': "Strong technical momentum drives continuation of trend",
        'hack_security': "Security concerns trigger risk-off sentiment and selling pressure",
        'macro_uncertainty': "Macro uncertainty weighs on risk assets",
        'ecosystem_growth': "Ecosystem expansion and adoption drive organic growth",
    }

    return templates.get(theme, "Mixed market conditions with competing narratives")
```

### Step 3: Complete Snapshot Creation

```python
async def create_daily_snapshot(date: datetime, d1_service, embedding_worker_url: str):
    """
    Create complete daily snapshot with smart embedding
    """

    # 1. Gather data
    headlines = get_top_headlines(date, limit=5)
    sentiment = get_sentiment_snapshot(date)
    technicals = get_technical_snapshot(date, coin="BTC")
    social = get_social_snapshot(date, coin="BTC")

    # 2. Build embedding text
    embedding_text = build_embedding_text(date)

    # 3. Generate embedding
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{embedding_worker_url}/embed",
            json={"text": embedding_text, "model": "bge-base-en"}
        ) as resp:
            result = await resp.json()
            embedding = result["embeddings"][0]

    # 4. Build metadata
    metadata = {
        # Temporal
        "timestamp": int(date.timestamp()),
        "day_of_week": date.weekday(),
        "month": date.month,

        # Headlines (for reference)
        "headline_1": headlines[0]['title'] if len(headlines) > 0 else "",
        "headline_2": headlines[1]['title'] if len(headlines) > 1 else "",
        "headline_3": headlines[2]['title'] if len(headlines) > 2 else "",

        # Theme
        "primary_theme": identify_primary_theme(headlines),
        "narrative_summary": summarize_narrative(headlines),

        # Sentiment
        "sentiment_score": sentiment['score'],
        "sentiment_velocity": sentiment['velocity'],
        "sentiment_acceleration": sentiment['acceleration'],
        "fear_greed": sentiment['fear_greed'],

        # Technicals
        "rsi": technicals['rsi'],
        "macd_signal": technicals['macd_signal'],
        "trend": technicals['trend'],
        "volatility": technicals['volatility'],
        "volume_ratio": technicals['volume_ratio'],

        # Social
        "social_mentions": social['mentions'],
        "social_sentiment": social['sentiment'],

        # Price
        "btc_price": technicals['close'],
        "price_change_24h": technicals['price_change_24h'],

        # Outcomes (backfilled later)
        "outcome_7d": None,  # Fill after 7 days
        "profitable_7d": None,
    }

    # 5. Return snapshot
    return {
        "id": date.isoformat(),
        "values": embedding,
        "metadata": metadata
    }
```

## Query Examples

### Find Similar Market Narratives

```python
# Current market
current_text = build_embedding_text(datetime.now())
current_embedding = await generate_embedding(current_text)

# Find similar
results = await vectorize.query(
    vector=current_embedding,
    filter={
        "primary_theme": {"$eq": "institutional_adoption"},  # Same theme
        "profitable_7d": {"$eq": 1}  # Only winners
    },
    topK=10
)

# Results: Periods with similar "institutional adoption" narratives that won
```

### Find Similar Technical Setups (Regardless of News)

```python
# Find by metadata only (ignore news narrative)
results = await vectorize.query(
    vector=[0] * 768,  # Dummy vector
    filter={
        "rsi": {"$gte": 65, "$lte": 75},
        "sentiment_velocity": {"$gte": 0.05},
        "trend": {"$eq": "uptrend"}
    },
    topK=100
)

# Results: Periods matching technical conditions (any news theme)
```

### Hybrid: Similar Theme + Technical Range

```python
# Combine semantic + metadata
results = await vectorize.query(
    vector=current_embedding,  # Similar narratives
    filter={
        "rsi": {"$gte": 60, "$lte": 80},  # Technical range
        "profitable_7d": {"$eq": 1}  # Only winners
    },
    topK=20
)

# Results: Similar narratives within technical range that won
```

## Storage Requirements

### Daily Snapshots
- 365 days/year × 6 years = **2,190 snapshots**
- 768 dimensions each
- **Total**: 1.68M dimensions stored
- **Cost**: ~$0.07/month storage

### Per-Coin (if needed)
- 3 coins (BTC, ETH, SOL) × 365 days × 6 years = **6,570 snapshots**
- **Total**: 5.05M dimensions stored
- **Cost**: ~$0.20/month storage

### Intraday Windows (if needed)
- 3 snapshots/day × 365 days × 6 years = **6,570 snapshots**
- **Total**: 5.05M dimensions stored
- **Cost**: ~$0.20/month storage

All well within Vectorize limits (10M stored dimensions free tier)!

## Recommendation Summary

**Use: Smart Daily Aggregation**

1. ✅ One embedding per day
2. ✅ Combine top 3-5 headlines
3. ✅ Add narrative summary
4. ✅ Include sentiment + technical context
5. ✅ Store theme/category in metadata
6. ✅ Attach all indicators + outcomes

**Benefits**:
- Captures overall "market vibe"
- Manageable dataset size (2,190 snapshots)
- Fast queries (<70ms)
- Perfect for daily trading decisions
- Can still filter by theme/coin/technical via metadata

**Optional Enhancements**:
- Add per-coin snapshots if trading multiple assets independently
- Add intraday windows if doing intraday trading
- Add event-based snapshots for major events

This gives you the best balance of semantic richness and query performance! 🎯
