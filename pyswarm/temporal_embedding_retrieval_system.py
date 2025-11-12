"""
Temporal Embedding Retrieval System for Market Pattern Matching

Combines both pieces of advice:
1. "Never embed an embedding" - blend in vector space (first advice)
2. "Dual embeddings + retrieval" - pure + smoothed for similarity search (second advice)

Architecture:
- Vectorize: Stores embeddings (dual: pure + smoothed)
- D1: Stores metadata (indicators, outcomes)
- Scoring: Combines semantic similarity + numeric similarity
- Query: Find historical analogs → analyze outcomes
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json


@dataclass
class DualEmbedding:
    """
    Store both pure and smoothed embeddings per day.

    Pure: Today's headlines only (sharp transitions)
    Smoothed: Decayed blend with yesterday (emotional persistence)

    From the advice: "Keep both the pure embedding and a smoothed one"
    """
    date: datetime
    pure_embedding: List[float]      # embed(today's headlines)
    smoothed_embedding: List[float]  # α * yesterday_smoothed + (1-α) * pure
    embedding_text: str              # For debugging
    alpha: float                     # Decay factor used


@dataclass
class MarketSnapshot:
    """Complete market snapshot for one day"""
    date: datetime

    # Embeddings (dual)
    pure_embedding: List[float]
    smoothed_embedding: List[float]

    # Text (for debugging)
    headlines: List[str]
    embedding_text: str

    # Technical indicators (stored in D1 metadata)
    rsi: float
    macd_signal: str
    volatility: str
    volume_ratio: float
    btc_price: float

    # Sentiment
    sentiment_score: float
    sentiment_velocity: float
    fear_greed: int

    # Outcomes (backfilled later)
    outcome_1d: Optional[float] = None
    outcome_5d: Optional[float] = None
    outcome_7d: Optional[float] = None

    # Regime classification (optional, from clustering)
    regime: Optional[str] = None  # e.g., "optimistic", "fearful", "uncertain"


class TemporalEmbeddingRetriever:
    """
    Retrieval system for finding similar historical market periods.

    Key insight from advice: "You're not predicting directly from sentiment;
    you're creating a latent memory of market mood."

    Process:
    1. Generate dual embeddings (pure + smoothed) for today
    2. Query Vectorize for similar days (cosine similarity)
    3. Score results combining semantic + numeric similarity
    4. Analyze outcomes of similar periods
    """

    def __init__(
        self,
        vectorize_index,
        d1_database,
        embedding_function,
        alpha: float = 0.3  # Decay for smoothed embedding
    ):
        """
        Initialize retrieval system.

        Args:
            vectorize_index: Cloudflare Vectorize binding
            d1_database: Cloudflare D1 binding
            embedding_function: Function to generate embeddings
            alpha: Decay weight for smoothed embeddings (0.2-0.4 typical)
        """
        self.vectorize = vectorize_index
        self.d1 = d1_database
        self.embed = embedding_function
        self.alpha = alpha

        # Cache for yesterday's smoothed embedding (in production: fetch from Vectorize)
        self._smoothed_cache: Dict[str, List[float]] = {}

    # =========================================================================
    # STEP 1: Generate Dual Embeddings
    # =========================================================================

    async def create_daily_snapshot(
        self,
        date: datetime,
        headlines: List[Dict],
        indicators: Dict,
        sentiment: Dict
    ) -> MarketSnapshot:
        """
        Create complete market snapshot with dual embeddings.

        From advice: "Each day: headline_embedding_t = embed(concat_headlines(day_t))"
        """
        # Build embedding text from headlines
        headline_texts = [h['title'] for h in headlines[:5]]  # Top 5
        embedding_text = " | ".join(headline_texts)

        # Generate PURE embedding (today only)
        pure_embedding = await self.embed(embedding_text)

        # Generate SMOOTHED embedding (with decay from yesterday)
        smoothed_embedding = await self._generate_smoothed_embedding(
            date,
            pure_embedding
        )

        # Build complete snapshot
        snapshot = MarketSnapshot(
            date=date,
            pure_embedding=pure_embedding,
            smoothed_embedding=smoothed_embedding,
            headlines=headline_texts,
            embedding_text=embedding_text,

            # Technical indicators
            rsi=indicators['rsi'],
            macd_signal=indicators['macd_signal'],
            volatility=indicators['volatility'],
            volume_ratio=indicators['volume_ratio'],
            btc_price=indicators['btc_price'],

            # Sentiment
            sentiment_score=sentiment['score'],
            sentiment_velocity=sentiment['velocity'],
            fear_greed=sentiment['fear_greed']
        )

        return snapshot

    async def _generate_smoothed_embedding(
        self,
        date: datetime,
        pure_embedding: List[float]
    ) -> List[float]:
        """
        Generate smoothed embedding with exponential decay.

        From advice: "smoothed_t = normalize(α * smoothed_{t-1} + (1-α) * headline_embedding_t)"

        This models the fading emotional effect of news.
        """
        yesterday = date - timedelta(days=1)
        yesterday_key = yesterday.isoformat()

        # Get yesterday's smoothed embedding
        yesterday_smoothed = self._smoothed_cache.get(yesterday_key)

        if yesterday_smoothed is None:
            # First day or cache miss - fetch from Vectorize
            yesterday_smoothed = await self._fetch_smoothed_from_vectorize(yesterday)

        if yesterday_smoothed is None:
            # Still None - no historical data, return pure
            smoothed = pure_embedding
        else:
            # Blend: α * yesterday_smoothed + (1-α) * pure
            smoothed = [
                self.alpha * yesterday_smoothed[i] + (1 - self.alpha) * pure_embedding[i]
                for i in range(len(pure_embedding))
            ]

            # Normalize (CRITICAL)
            smoothed = self._normalize(smoothed)

        # Cache for tomorrow
        self._smoothed_cache[date.isoformat()] = smoothed

        return smoothed

    async def _fetch_smoothed_from_vectorize(
        self,
        date: datetime
    ) -> Optional[List[float]]:
        """Fetch yesterday's smoothed embedding from Vectorize"""
        # Query by ID
        result = await self.vectorize.getByIds([date.isoformat()])

        if result and len(result) > 0:
            # Extract smoothed embedding from metadata
            return result[0].get('smoothed_embedding')

        return None

    def _normalize(self, vec: List[float]) -> List[float]:
        """Normalize vector to unit length"""
        magnitude = sum(x**2 for x in vec) ** 0.5
        if magnitude == 0:
            return vec
        return [x / magnitude for x in vec]

    # =========================================================================
    # STEP 2: Store in Vectorize + D1
    # =========================================================================

    async def store_snapshot(self, snapshot: MarketSnapshot):
        """
        Store dual embeddings in Vectorize and metadata in D1.

        Architecture from advice:
        - Vector DB: Stores embeddings (we use Vectorize)
        - Metadata store: Holds indicators and outcomes (we use D1)
        """
        # Store in Vectorize (using smoothed for similarity search)
        # Store both pure and smoothed in metadata for flexibility
        await self.vectorize.upsert([{
            'id': snapshot.date.isoformat(),
            'values': snapshot.smoothed_embedding,  # Use smoothed for queries
            'metadata': {
                # Store pure embedding in metadata (for retrieval)
                'pure_embedding': snapshot.pure_embedding,

                # Temporal
                'timestamp': int(snapshot.date.timestamp()),
                'day_of_week': snapshot.date.weekday(),

                # Text (debugging)
                'headlines': json.dumps(snapshot.headlines),
                'embedding_text': snapshot.embedding_text,

                # Technical indicators (for numeric similarity)
                'rsi': snapshot.rsi,
                'macd_signal': snapshot.macd_signal,
                'volatility': snapshot.volatility,
                'volume_ratio': snapshot.volume_ratio,
                'btc_price': snapshot.btc_price,

                # Sentiment
                'sentiment_score': snapshot.sentiment_score,
                'sentiment_velocity': snapshot.sentiment_velocity,
                'fear_greed': snapshot.fear_greed,

                # Outcomes (initially None, backfilled later)
                'outcome_1d': snapshot.outcome_1d,
                'outcome_5d': snapshot.outcome_5d,
                'outcome_7d': snapshot.outcome_7d,

                # Regime
                'regime': snapshot.regime,

                # Config
                'alpha': self.alpha
            }
        }])

    # =========================================================================
    # STEP 3: Retrieval - Find Similar Historical Periods
    # =========================================================================

    async def find_similar_periods(
        self,
        current_snapshot: MarketSnapshot,
        top_k: int = 10,
        min_similarity: float = 0.7,
        exclude_recent_days: int = 30,
        use_pure: bool = False  # Use pure or smoothed embedding?
    ) -> List[Dict]:
        """
        Find historically similar market periods.

        From advice: "Find prior days with cosine similarity > threshold"

        Args:
            current_snapshot: Today's market state
            top_k: Number of similar periods to return
            min_similarity: Minimum cosine similarity threshold
            exclude_recent_days: Don't match periods within N days
            use_pure: Use pure (sharp) or smoothed (emotional) embedding

        Returns:
            List of similar periods with scores and metadata
        """
        # Choose which embedding to use for query
        query_embedding = (
            current_snapshot.pure_embedding if use_pure
            else current_snapshot.smoothed_embedding
        )

        # Query Vectorize
        # Note: Vectorize stores smoothed embeddings in 'values'
        # If querying with pure, similarity scores will reflect pure→smoothed comparison
        cutoff_timestamp = int((current_snapshot.date - timedelta(days=exclude_recent_days)).timestamp())

        results = await self.vectorize.query(
            vector=query_embedding,
            topK=top_k * 2,  # Get extras for filtering
            filter={
                'timestamp': {'$lt': cutoff_timestamp}  # Exclude recent
            },
            returnMetadata: True,
            returnValues: False
        )

        # Filter by similarity threshold
        similar_periods = []
        for match in results.matches:
            if match.score < min_similarity:
                continue

            similar_periods.append({
                'date': match.id,
                'cosine_similarity': match.score,
                'metadata': match.metadata
            })

        # Take top K
        similar_periods = similar_periods[:top_k]

        return similar_periods

    # =========================================================================
    # STEP 4: Scoring - Combine Semantic + Numeric Similarity
    # =========================================================================

    async def find_similar_with_numeric_filter(
        self,
        current_snapshot: MarketSnapshot,
        top_k: int = 10,
        rsi_tolerance: float = 10,  # ±10 RSI points
        volume_tolerance: float = 0.5,  # ±0.5 volume ratio
    ) -> List[Dict]:
        """
        Enhanced retrieval combining semantic AND numeric similarity.

        From advice: "Combine cosine similarity (headline) and numeric similarity
        (volatility, funding, etc.)"

        This finds periods that are:
        - Semantically similar (similar headlines/narrative)
        - Technically similar (similar RSI, volume, etc.)
        """
        # Get candidates via semantic similarity
        candidates = await self.find_similar_periods(
            current_snapshot,
            top_k=top_k * 3,  # Get more candidates
            min_similarity=0.6  # Lower threshold (we'll re-score)
        )

        # Re-score combining semantic + numeric
        scored = []
        for candidate in candidates:
            meta = candidate['metadata']

            # Semantic similarity (from Vectorize)
            semantic_score = candidate['cosine_similarity']

            # Numeric similarity
            rsi_diff = abs(current_snapshot.rsi - meta['rsi'])
            rsi_score = max(0, 1 - (rsi_diff / rsi_tolerance))

            volume_diff = abs(current_snapshot.volume_ratio - meta['volume_ratio'])
            volume_score = max(0, 1 - (volume_diff / volume_tolerance))

            sentiment_diff = abs(current_snapshot.sentiment_score - meta['sentiment_score'])
            sentiment_score = max(0, 1 - sentiment_diff)  # Both in [-1, 1]

            # Volatility match (categorical)
            volatility_score = 1.0 if current_snapshot.volatility == meta['volatility'] else 0.5

            # Combined score (weighted)
            combined_score = (
                0.4 * semantic_score +     # 40% semantic
                0.2 * rsi_score +          # 20% RSI
                0.2 * sentiment_score +    # 20% sentiment
                0.1 * volume_score +       # 10% volume
                0.1 * volatility_score     # 10% volatility
            )

            scored.append({
                **candidate,
                'combined_score': combined_score,
                'semantic_score': semantic_score,
                'rsi_score': rsi_score,
                'sentiment_score': sentiment_score,
                'volume_score': volume_score,
                'volatility_score': volatility_score
            })

        # Sort by combined score
        scored.sort(key=lambda x: x['combined_score'], reverse=True)

        return scored[:top_k]

    # =========================================================================
    # STEP 5: Strategy Patterns - Historical Analogs
    # =========================================================================

    async def get_historical_analog_prediction(
        self,
        current_snapshot: MarketSnapshot,
        lookahead_days: int = 7,
        top_k: int = 10
    ) -> Dict:
        """
        Historical analogs strategy.

        From advice: "Find 10 most similar days. Average their next-1d and
        next-5d returns → conditional expectation."

        Returns:
            {
                'expected_return': float,  # Average outcome of similar periods
                'confidence': float,       # How similar the matches are
                'similar_count': int,      # How many matches found
                'analogs': List[Dict]      # The similar periods
            }
        """
        # Find similar periods with outcomes
        similar = await self.find_similar_with_numeric_filter(
            current_snapshot,
            top_k=top_k
        )

        # Filter to only periods with known outcomes
        outcome_key = f'outcome_{lookahead_days}d'
        with_outcomes = [
            s for s in similar
            if s['metadata'].get(outcome_key) is not None
        ]

        if not with_outcomes:
            return {
                'expected_return': 0.0,
                'confidence': 0.0,
                'similar_count': 0,
                'analogs': []
            }

        # Calculate weighted average of outcomes
        total_weight = 0
        weighted_outcome = 0

        for period in with_outcomes:
            weight = period['combined_score']
            outcome = period['metadata'][outcome_key]

            weighted_outcome += weight * outcome
            total_weight += weight

        expected_return = weighted_outcome / total_weight if total_weight > 0 else 0

        # Confidence = average similarity
        avg_similarity = sum(p['combined_score'] for p in with_outcomes) / len(with_outcomes)

        return {
            'expected_return': expected_return,
            'confidence': avg_similarity,
            'similar_count': len(with_outcomes),
            'analogs': with_outcomes,

            # Stats
            'avg_semantic_similarity': sum(p['semantic_score'] for p in with_outcomes) / len(with_outcomes),
            'outcomes': [p['metadata'][outcome_key] for p in with_outcomes],
            'min_outcome': min(p['metadata'][outcome_key] for p in with_outcomes),
            'max_outcome': max(p['metadata'][outcome_key] for p in with_outcomes)
        }

    # =========================================================================
    # STEP 6: Regime Detection
    # =========================================================================

    async def classify_regime(
        self,
        current_snapshot: MarketSnapshot,
        regime_examples: Dict[str, List[str]]
    ) -> Tuple[str, float]:
        """
        Classify market regime using nearest regime centroid.

        From advice: "Cluster embeddings into 'optimistic,' 'fearful,' etc.
        Use cluster label as a regime feature."

        Args:
            current_snapshot: Today's market state
            regime_examples: Dictionary mapping regime names to example dates
                            e.g., {'optimistic': ['2024-01-10', '2024-01-15'],
                                   'fearful': ['2022-11-09', '2022-06-13']}

        Returns:
            (regime_name, confidence)
        """
        # Fetch embeddings for regime examples
        regime_centroids = {}

        for regime_name, example_dates in regime_examples.items():
            # Fetch embeddings for examples
            embeddings = []
            for date_str in example_dates:
                result = await self.vectorize.getByIds([date_str])
                if result and len(result) > 0:
                    embeddings.append(result[0]['values'])

            if embeddings:
                # Compute centroid (average)
                centroid = [
                    sum(emb[i] for emb in embeddings) / len(embeddings)
                    for i in range(len(embeddings[0]))
                ]
                regime_centroids[regime_name] = self._normalize(centroid)

        # Find nearest centroid
        best_regime = None
        best_similarity = -1

        for regime_name, centroid in regime_centroids.items():
            similarity = self._cosine_similarity(
                current_snapshot.smoothed_embedding,
                centroid
            )

            if similarity > best_similarity:
                best_similarity = similarity
                best_regime = regime_name

        return best_regime, best_similarity

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity"""
        dot = sum(a * b for a, b in zip(vec1, vec2))
        mag1 = sum(x**2 for x in vec1) ** 0.5
        mag2 = sum(x**2 for x in vec2) ** 0.5

        if mag1 == 0 or mag2 == 0:
            return 0

        return dot / (mag1 * mag2)

    # =========================================================================
    # STEP 7: Similarity Drift Detection
    # =========================================================================

    async def detect_similarity_drift(
        self,
        lookback_days: int = 30
    ) -> Dict:
        """
        Detect similarity drift to identify narrative shifts.

        From advice: "Track similarity drift — if embeddings cluster tightly,
        recent news is repetitive; spread implies sentiment change."

        Returns:
            {
                'avg_similarity': float,  # Average consecutive similarity
                'std_similarity': float,  # Standard deviation
                'drift_score': float,     # Higher = more drift
                'interpretation': str     # "repetitive" or "shifting"
            }
        """
        # Fetch recent embeddings
        # (In production: query Vectorize with time filter)
        # For now: simplified example

        similarities = []

        # This would fetch actual data from Vectorize
        # similarities = [consecutive similarity scores over lookback_days]

        # Example logic (would use real data):
        # for i in range(lookback_days - 1):
        #     sim = cosine_similarity(embeddings[i], embeddings[i+1])
        #     similarities.append(sim)

        # Compute stats
        if not similarities:
            return {
                'avg_similarity': 0,
                'std_similarity': 0,
                'drift_score': 0,
                'interpretation': 'insufficient_data'
            }

        avg_sim = sum(similarities) / len(similarities)
        variance = sum((s - avg_sim)**2 for s in similarities) / len(similarities)
        std_sim = variance ** 0.5

        # Drift score: higher std = more drift
        drift_score = std_sim

        # Interpretation
        if avg_sim > 0.9 and std_sim < 0.05:
            interpretation = "repetitive"  # News clustering tightly
        elif avg_sim < 0.7 or std_sim > 0.15:
            interpretation = "shifting"    # Sentiment changing
        else:
            interpretation = "stable"

        return {
            'avg_similarity': avg_sim,
            'std_similarity': std_sim,
            'drift_score': drift_score,
            'interpretation': interpretation,
            'sample_size': len(similarities)
        }


# =============================================================================
# USAGE EXAMPLES
# =============================================================================

async def example_daily_workflow(retriever: TemporalEmbeddingRetriever):
    """
    Complete daily workflow:
    1. Create snapshot with dual embeddings
    2. Store in Vectorize + D1
    3. Find similar historical periods
    4. Get prediction from historical analogs
    5. Classify current regime
    """
    # Today's data
    today = datetime(2024, 1, 15)

    headlines = [
        {'title': 'Bitcoin rallies 12% on institutional buying', 'importance': 0.85},
        {'title': 'ETF flows continue strong', 'importance': 0.80},
        {'title': 'Technical breakout confirmed', 'importance': 0.70}
    ]

    indicators = {
        'rsi': 74,
        'macd_signal': 'bullish',
        'volatility': 'medium',
        'volume_ratio': 2.3,
        'btc_price': 47500
    }

    sentiment = {
        'score': 0.78,
        'velocity': 0.05,
        'fear_greed': 72
    }

    # Step 1: Create snapshot (generates dual embeddings)
    print("Creating daily snapshot with dual embeddings...")
    snapshot = await retriever.create_daily_snapshot(
        today,
        headlines,
        indicators,
        sentiment
    )

    print(f"✓ Pure embedding: {len(snapshot.pure_embedding)} dims")
    print(f"✓ Smoothed embedding: {len(snapshot.smoothed_embedding)} dims")

    # Step 2: Store
    print("\nStoring in Vectorize...")
    await retriever.store_snapshot(snapshot)
    print("✓ Stored")

    # Step 3: Find similar periods
    print("\nFinding similar historical periods...")
    similar = await retriever.find_similar_with_numeric_filter(
        snapshot,
        top_k=10
    )

    print(f"✓ Found {len(similar)} similar periods:")
    for s in similar[:3]:
        print(f"  - {s['date']}: combined_score={s['combined_score']:.3f}")
        print(f"    semantic={s['semantic_score']:.3f}, rsi={s['rsi_score']:.3f}")

    # Step 4: Get prediction from analogs
    print("\nGetting prediction from historical analogs...")
    prediction = await retriever.get_historical_analog_prediction(
        snapshot,
        lookahead_days=7,
        top_k=10
    )

    print(f"✓ Expected 7-day return: {prediction['expected_return']:.2%}")
    print(f"  Confidence: {prediction['confidence']:.3f}")
    print(f"  Based on {prediction['similar_count']} similar periods")

    # Step 5: Classify regime
    print("\nClassifying market regime...")
    regime_examples = {
        'bull_rally': ['2024-01-10', '2024-01-11', '2023-10-15'],
        'bear_capitulation': ['2022-11-09', '2022-06-13'],
        'consolidation': ['2024-01-05', '2023-12-20']
    }

    regime, confidence = await retriever.classify_regime(snapshot, regime_examples)
    print(f"✓ Regime: {regime} (confidence: {confidence:.3f})")

    # Step 6: Detect drift
    print("\nDetecting narrative drift...")
    drift = await retriever.detect_similarity_drift(lookback_days=30)
    print(f"✓ Drift interpretation: {drift['interpretation']}")
    print(f"  Avg similarity: {drift['avg_similarity']:.3f}")
    print(f"  Drift score: {drift['drift_score']:.3f}")


# =============================================================================
# KEY RULES (from the advice)
# =============================================================================

RULES = """
1. Never mix text and vector; always update numerically.
   ✓ v_t = α * v_{t-1} + (1-α) * embed(text_t)
   ✗ Don't embed: embed(text_t + str(v_{t-1}))

2. Use decay for persistence, not re-embedding.
   ✓ Blend vectors with decay factor α
   ✗ Don't repeatedly embed the same text

3. Normalize all embeddings before cosine search.
   ✓ vec / ||vec||
   ✗ Raw unnormalized vectors (similarity scores will drift)

4. Re-evaluate the α decay constant per asset.
   - Crypto: α ≈ 0.2-0.3 (faster moving narratives)
   - Equities: α ≈ 0.3-0.5 (slower moving)

5. Track similarity drift.
   - Tight clustering → repetitive news
   - Spread → sentiment change
   - Use as regime shift indicator

6. Dual embeddings serve different purposes:
   - Pure: Sharp transitions, event detection
   - Smoothed: Emotional persistence, regime matching

7. Combine semantic + numeric similarity.
   - Headlines alone miss technical setup
   - Technicals alone miss narrative
   - Best: weighted combination
"""

if __name__ == "__main__":
    print(RULES)
