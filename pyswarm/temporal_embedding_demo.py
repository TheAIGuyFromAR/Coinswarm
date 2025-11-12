"""
Temporal Embedding Demo - No dependencies

Shows the difference between strategies using simple math
"""

from datetime import datetime, timedelta


def normalize(vec):
    """Normalize vector to unit length"""
    mag = sum(x**2 for x in vec) ** 0.5
    if mag == 0:
        return vec
    return [x / mag for x in vec]


def vector_blend(prev_vec, new_vec, alpha):
    """Blend two vectors: alpha*prev + (1-alpha)*new"""
    return [
        alpha * prev_vec[i] + (1 - alpha) * new_vec[i]
        for i in range(len(new_vec))
    ]


def mock_embed(text):
    """Mock embedding - just use hash for demo"""
    # In reality: return model.embed(text)
    # For demo: create simple vector based on text
    hash_val = hash(text) % 1000
    return [hash_val / 1000.0, (1000 - hash_val) / 1000.0, 0.5, 0.3]


def cosine_similarity(vec1, vec2):
    """Compute cosine similarity between two vectors"""
    dot = sum(a * b for a, b in zip(vec1, vec2))
    mag1 = sum(x**2 for x in vec1) ** 0.5
    mag2 = sum(x**2 for x in vec2) ** 0.5
    if mag1 == 0 or mag2 == 0:
        return 0
    return dot / (mag1 * mag2)


print("=" * 80)
print("TEMPORAL EMBEDDING STRATEGIES COMPARISON")
print("=" * 80)

# Scenario: ETF approval, then rally, then consolidation
scenarios = [
    {
        'date': datetime(2024, 1, 10),
        'text': 'SEC approves Bitcoin ETF | Sentiment: 0.85 bullish | RSI: 68',
        'description': 'ETF APPROVAL DAY'
    },
    {
        'date': datetime(2024, 1, 11),
        'text': 'Bitcoin rallies 15% on ETF hype | Sentiment: 0.82 bullish | RSI: 74',
        'description': 'Rally Day 1'
    },
    {
        'date': datetime(2024, 1, 12),
        'text': 'Institutional buying continues | Sentiment: 0.78 bullish | RSI: 76',
        'description': 'Rally Day 2'
    },
    {
        'date': datetime(2024, 1, 13),
        'text': 'Profit-taking begins, consolidation | Sentiment: 0.45 neutral | RSI: 64',
        'description': 'Consolidation'
    }
]

print("\n" + "=" * 80)
print("STRATEGY 1: Simple Daily (No Memory)")
print("=" * 80)
print("Each day is independent - no blending\n")

simple_embeddings = []
for s in scenarios:
    emb = mock_embed(s['text'])
    simple_embeddings.append(emb)
    print(f"{s['description']:20} → embedding (first 2 dims): [{emb[0]:.3f}, {emb[1]:.3f}]")

# Show similarity between days
print("\nSimilarity between consecutive days:")
for i in range(len(simple_embeddings) - 1):
    sim = cosine_similarity(simple_embeddings[i], simple_embeddings[i+1])
    print(f"  Day {i} → Day {i+1}: {sim:.3f}")

print("\n" + "=" * 80)
print("STRATEGY 2: Pure Vector Blending (THE ADVICE)")
print("=" * 80)
print("Formula: v_t = normalize(α * v_{t-1} + (1-α) * embed(text_t))")
print("Using α = 0.15 (15% yesterday, 85% today)\n")

alpha = 0.15
blended_embeddings = []

for i, s in enumerate(scenarios):
    # Generate raw embedding for today
    raw_emb = mock_embed(s['text'])

    if i == 0:
        # First day - no blending
        final_emb = raw_emb
        print(f"{s['description']:20} → NO BLEND (first day)")
    else:
        # Blend with yesterday
        yesterday_emb = blended_embeddings[i - 1]
        blended = vector_blend(yesterday_emb, raw_emb, alpha)
        final_emb = normalize(blended)

        # Show composition
        print(f"{s['description']:20} → {int((1-alpha)*100)}% today + {int(alpha*100)}% yesterday")

    blended_embeddings.append(final_emb)
    print(f"  {'':20}    Result: [{final_emb[0]:.3f}, {final_emb[1]:.3f}]")

print("\nSimilarity between consecutive days:")
for i in range(len(blended_embeddings) - 1):
    sim = cosine_similarity(blended_embeddings[i], blended_embeddings[i+1])
    print(f"  Day {i} → Day {i+1}: {sim:.3f}")

print("\nCascading Memory (what each day contains):")
print("  Day 0: 100% Day 0")
print("  Day 1: 85% Day 1 + 15% Day 0")
print("  Day 2: 85% Day 2 + 12.75% Day 1 + 2.25% Day 0")
print("  Day 3: 85% Day 3 + 12.75% Day 2 + 2.25% Day 1 + 0.34% Day 0")

print("\n" + "=" * 80)
print("STRATEGY 3: Text Persistence (Categorical Decay)")
print("=" * 80)
print("Important events persist in the TEXT for multiple days\n")

text_persistent_embeddings = []

for i, s in enumerate(scenarios):
    base_text = s['text']

    # Add historical context for days after ETF approval
    if i > 0:
        # ETF approval persists for 14 days (regulatory_approval category)
        days_since_etf = i
        if days_since_etf <= 14:
            decay = 1.0 - (days_since_etf / 14)
            weight = 0.95 * decay  # importance=0.95 for ETF news
            context = f" | CONTEXT (-{days_since_etf}d, regulatory, w={weight:.2f}): SEC approves ETF"
            enhanced_text = base_text + context
        else:
            enhanced_text = base_text
    else:
        enhanced_text = base_text

    # Generate embedding from enhanced text
    emb = mock_embed(enhanced_text)
    text_persistent_embeddings.append(emb)

    if i == 0:
        print(f"{s['description']:20} → Base text only")
    else:
        print(f"{s['description']:20} → Base + ETF context (weight={weight:.2f})")
    print(f"  {'':20}    Result: [{emb[0]:.3f}, {emb[1]:.3f}]")

print("\nSimilarity between consecutive days:")
for i in range(len(text_persistent_embeddings) - 1):
    sim = cosine_similarity(text_persistent_embeddings[i], text_persistent_embeddings[i+1])
    print(f"  Day {i} → Day {i+1}: {sim:.3f}")

print("\n" + "=" * 80)
print("STRATEGY 4: Hybrid (RECOMMENDED)")
print("=" * 80)
print("Text persistence + light vector blending (15%)\n")

hybrid_embeddings = []

for i, s in enumerate(scenarios):
    # Step 1: Build text with historical context (like Strategy 3)
    base_text = s['text']

    if i > 0:
        days_since_etf = i
        if days_since_etf <= 14:
            decay = 1.0 - (days_since_etf / 14)
            weight = 0.95 * decay
            context = f" | CONTEXT: SEC approves ETF (weight={weight:.2f})"
            enhanced_text = base_text + context
        else:
            enhanced_text = base_text
    else:
        enhanced_text = base_text

    # Step 2: Generate raw embedding from enhanced text
    raw_emb = mock_embed(enhanced_text)

    # Step 3: Light blend with yesterday (like Strategy 2)
    if i == 0:
        final_emb = raw_emb
        print(f"{s['description']:20} → Text context: None | Vector blend: None")
    else:
        yesterday_emb = hybrid_embeddings[i - 1]
        blended = vector_blend(yesterday_emb, raw_emb, alpha)
        final_emb = normalize(blended)
        print(f"{s['description']:20} → Text context: ETF ({weight:.2f}) | Vector blend: 15%")

    hybrid_embeddings.append(final_emb)
    print(f"  {'':20}    Result: [{final_emb[0]:.3f}, {final_emb[1]:.3f}]")

print("\nSimilarity between consecutive days:")
for i in range(len(hybrid_embeddings) - 1):
    sim = cosine_similarity(hybrid_embeddings[i], hybrid_embeddings[i+1])
    print(f"  Day {i} → Day {i+1}: {sim:.3f}")

print("\n" + "=" * 80)
print("COMPARISON: Similarity to ETF Approval Day")
print("=" * 80)
print("Which strategy keeps the 'ETF memory' alive longest?\n")

print(f"{'Strategy':25} Day 1   Day 2   Day 3")
print("-" * 60)

strategies = [
    ("Simple (no memory)", simple_embeddings),
    ("Vector blend (15%)", blended_embeddings),
    ("Text persistence", text_persistent_embeddings),
    ("Hybrid", hybrid_embeddings)
]

for name, embs in strategies:
    sims = [cosine_similarity(embs[0], embs[i]) for i in range(1, 4)]
    print(f"{name:25} {sims[0]:.3f}  {sims[1]:.3f}  {sims[2]:.3f}")

print("\n" + "=" * 80)
print("KEY INSIGHTS")
print("=" * 80)
print("""
1. SIMPLE: Each day independent → low similarity to ETF day
   - Good for: Detecting exact event days
   - Bad for: Understanding persistent market regimes

2. VECTOR BLEND: Automatic exponential decay
   - Good for: Smooth transitions, regime persistence
   - Bad for: Explainability (can't see what's inside)
   - Creates cascading memory without configuration

3. TEXT PERSISTENCE: Explicit event inclusion
   - Good for: Debuggable, realistic (different events persist differently)
   - Bad for: Can have discontinuous jumps

4. HYBRID: Best of both worlds
   - Text persistence: ETF news explicitly in text for 14 days
   - Vector blend: Smooth transitions (15% yesterday)
   - 85% new content: Can still detect regime changes
   - Recommended for production!

The advice you received describes Strategy 2 (pure vector blending).
For trading, Strategy 4 (hybrid) is often better because:
- You can debug what's in each embedding (text is visible)
- Different event types persist appropriately (regulatory vs social)
- Light blending prevents jarring jumps
- Still lets regime changes show through (85% new content)
""")

print("=" * 80)
print("ALPHA PARAMETER TUNING")
print("=" * 80)
print("""
α = decay weight (what % of yesterday to keep)

α = 0.05 (5% yesterday):  Very reactive, minimal memory
α = 0.15 (15% yesterday): Light smoothing (RECOMMENDED for hybrid)
α = 0.30 (30% yesterday): Moderate memory (good for pure blending)
α = 0.50 (50% yesterday): Heavy memory, slow to change

For HYBRID approach:
- Use α = 0.10-0.15 (light smoothing, let text context dominate)

For PURE vector blending (no text persistence):
- Use α = 0.25-0.35 (need more memory since text doesn't persist)

Cascading decay with α = 0.15:
Day -1: 15%   (keeps)
Day -2: 2.25% (0.15 * 0.15)
Day -3: 0.34%
Day -7: 0.05%
Day -14: 0.0004%
""")
