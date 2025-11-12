"""
Temporal Embedding Implementation: Vector Blending with Configurable Strategies

This module implements different temporal embedding strategies for market data,
with focus on vector arithmetic blending and hybrid approaches.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum


class TemporalStrategy(Enum):
    """Available temporal embedding strategies"""
    SIMPLE = "simple"                    # No temporal blending
    VECTOR_BLEND = "vector_blend"        # Pure vector arithmetic (the advice you received)
    TEXT_PERSISTENCE = "text_persistence"  # Text-based with categorical decay
    HYBRID = "hybrid"                    # Combined: text persistence + light vector blend


@dataclass
class EmbeddingConfig:
    """Configuration for temporal embedding generation"""
    strategy: TemporalStrategy = TemporalStrategy.HYBRID

    # Vector blending parameters
    alpha: float = 0.15  # Decay weight: higher = more memory, lower = more reactive
    normalize: bool = True  # Normalize after blending to prevent drift

    # Text persistence parameters
    lookback_days: int = 7
    min_importance: float = 0.75
    max_historical_items: int = 3

    # Categorical persistence (event type → days to persist)
    event_persistence: Dict[str, int] = None

    def __post_init__(self):
        if self.event_persistence is None:
            self.event_persistence = {
                'regulatory_approval': 14,
                'regulatory_crackdown': 7,
                'major_hack': 5,
                'institutional_adoption': 10,
                'technical_breakout': 2,
                'macro_news': 21,
                'protocol_upgrade': 7,
                'social_trend': 1,
            }


class TemporalEmbeddingEngine:
    """
    Generates embeddings with temporal memory using configurable strategies.

    Key insight from the advice: "You cannot embed an embedding.
    You maintain numerical continuity, not textual injection."

    This means:
    - ✅ Blend vectors in vector space: v_t = α*v_{t-1} + (1-α)*embed(text_t)
    - ❌ Don't inject yesterday's embedding into today's text
    """

    def __init__(self, config: EmbeddingConfig, embedding_function):
        """
        Initialize engine.

        Args:
            config: Configuration for temporal embedding
            embedding_function: Callable that takes text and returns embedding vector
                               e.g., lambda text: model.embed(text)
        """
        self.config = config
        self.embed = embedding_function

        # Storage for previous embeddings (in-memory cache)
        # In production, store in D1 or KV
        self.embedding_cache: Dict[str, np.ndarray] = {}

    def normalize(self, vec: np.ndarray) -> np.ndarray:
        """Normalize vector to unit length (prevents drift)"""
        norm = np.linalg.norm(vec)
        if norm == 0:
            return vec
        return vec / norm

    def generate_embedding(
        self,
        date: datetime,
        current_data: Dict,
        historical_data: Optional[List[Dict]] = None
    ) -> Tuple[np.ndarray, Dict]:
        """
        Generate temporal embedding based on configured strategy.

        Args:
            date: Current date
            current_data: Today's market data (headlines, sentiment, technicals)
            historical_data: Past days' important events (for text persistence)

        Returns:
            (embedding_vector, metadata)
        """
        if self.config.strategy == TemporalStrategy.SIMPLE:
            return self._simple_embedding(date, current_data)

        elif self.config.strategy == TemporalStrategy.VECTOR_BLEND:
            return self._vector_blend_embedding(date, current_data)

        elif self.config.strategy == TemporalStrategy.TEXT_PERSISTENCE:
            return self._text_persistence_embedding(date, current_data, historical_data)

        elif self.config.strategy == TemporalStrategy.HYBRID:
            return self._hybrid_embedding(date, current_data, historical_data)

        else:
            raise ValueError(f"Unknown strategy: {self.config.strategy}")

    # =========================================================================
    # STRATEGY 1: Simple Daily Snapshot
    # =========================================================================

    def _simple_embedding(
        self,
        date: datetime,
        current_data: Dict
    ) -> Tuple[np.ndarray, Dict]:
        """No temporal blending - each day independent"""
        text = self._build_daily_text(current_data)
        raw_embedding = self.embed(text)

        # Convert to numpy array if needed
        embedding = np.array(raw_embedding)

        # Cache for potential future use
        self.embedding_cache[date.isoformat()] = embedding

        metadata = {
            'strategy': 'simple',
            'embedding_text': text,
            'blend_weight': 0.0
        }

        return embedding, metadata

    # =========================================================================
    # STRATEGY 2: Pure Vector Blending (THE ADVICE YOU RECEIVED)
    # =========================================================================

    def _vector_blend_embedding(
        self,
        date: datetime,
        current_data: Dict
    ) -> Tuple[np.ndarray, Dict]:
        """
        Pure vector arithmetic blending as described in the advice:

        v_t = normalize(α * v_{t-1} + (1 - α) * embed(text_t))

        This creates cascading memory:
        - Day 0: 100% Day 0
        - Day 1: 85% Day 1 + 15% Day 0  (with α=0.15)
        - Day 2: 85% Day 2 + 12.75% Day 1 + 2.25% Day 0
        - Day 7: 85% Day 7 + ... + 0.05% Day 0

        Each day contains exponentially-decaying echo of all previous days.
        """
        # Build today's text (simple daily snapshot)
        text = self._build_daily_text(current_data)

        # Generate raw embedding for today
        raw_embedding = np.array(self.embed(text))

        # Get yesterday's FINAL embedding (already blended)
        yesterday_date = date - timedelta(days=1)
        yesterday_embedding = self.embedding_cache.get(yesterday_date.isoformat())

        if yesterday_embedding is None:
            # First day - no blending
            final_embedding = raw_embedding
            blend_weight = 0.0
        else:
            # Blend: α * yesterday + (1 - α) * today
            alpha = self.config.alpha
            final_embedding = (alpha * yesterday_embedding +
                             (1 - alpha) * raw_embedding)
            blend_weight = alpha

        # Normalize to prevent drift (CRITICAL!)
        if self.config.normalize:
            final_embedding = self.normalize(final_embedding)

        # Cache for tomorrow
        self.embedding_cache[date.isoformat()] = final_embedding

        metadata = {
            'strategy': 'vector_blend',
            'embedding_text': text,
            'blend_weight': blend_weight,
            'alpha': self.config.alpha,
            'had_previous': yesterday_embedding is not None
        }

        return final_embedding, metadata

    # =========================================================================
    # STRATEGY 3: Text Persistence with Categorical Decay
    # =========================================================================

    def _text_persistence_embedding(
        self,
        date: datetime,
        current_data: Dict,
        historical_data: Optional[List[Dict]] = None
    ) -> Tuple[np.ndarray, Dict]:
        """
        Include important historical events in the text itself,
        with categorical decay based on event type.

        Example output text:
        PRIMARY (2024-01-15):
        - Headlines: Bitcoin rallies 15%, Institutional flows surge
        - Sentiment: 0.82 bullish
        - RSI: 74, MACD: bullish

        CONTEXT (-1d, regulatory_approval, w=0.93): SEC approves Bitcoin ETF
        CONTEXT (-3d, institutional, w=0.70): BlackRock starts trading
        """
        # Build composite text with historical context
        text = self._build_composite_text(date, current_data, historical_data)

        # Generate embedding from rich text
        embedding = np.array(self.embed(text))

        # Cache
        self.embedding_cache[date.isoformat()] = embedding

        metadata = {
            'strategy': 'text_persistence',
            'embedding_text': text,
            'historical_items': len(historical_data) if historical_data else 0
        }

        return embedding, metadata

    # =========================================================================
    # STRATEGY 4: Hybrid (RECOMMENDED)
    # =========================================================================

    def _hybrid_embedding(
        self,
        date: datetime,
        current_data: Dict,
        historical_data: Optional[List[Dict]] = None
    ) -> Tuple[np.ndarray, Dict]:
        """
        Combines text persistence with light vector blending.

        Best of both worlds:
        1. Explicit text persistence (debuggable, categorical decay)
        2. Light vector blending (smooth transitions, prevents jumps)

        Process:
        1. Build composite text with historical events
        2. Generate raw embedding from text
        3. Lightly blend with yesterday's final embedding (15%)
        4. Normalize
        """
        # Step 1: Build composite text (like Strategy 3)
        text = self._build_composite_text(date, current_data, historical_data)

        # Step 2: Generate raw embedding
        raw_embedding = np.array(self.embed(text))

        # Step 3: Light blend with yesterday (like Strategy 2, but lighter)
        yesterday_date = date - timedelta(days=1)
        yesterday_embedding = self.embedding_cache.get(yesterday_date.isoformat())

        if yesterday_embedding is None:
            final_embedding = raw_embedding
            blend_weight = 0.0
        else:
            # Very light blending (config.alpha = 0.15 recommended)
            # This just smooths transitions, doesn't overpower the explicit context
            alpha = self.config.alpha
            final_embedding = (alpha * yesterday_embedding +
                             (1 - alpha) * raw_embedding)
            blend_weight = alpha

        # Step 4: Normalize
        if self.config.normalize:
            final_embedding = self.normalize(final_embedding)

        # Cache
        self.embedding_cache[date.isoformat()] = final_embedding

        metadata = {
            'strategy': 'hybrid',
            'embedding_text': text,
            'blend_weight': blend_weight,
            'alpha': self.config.alpha,
            'historical_items': len(historical_data) if historical_data else 0,
            'had_previous': yesterday_embedding is not None
        }

        return final_embedding, metadata

    # =========================================================================
    # Text Building Helpers
    # =========================================================================

    def _build_daily_text(self, data: Dict) -> str:
        """Build simple daily text (no historical context)"""
        parts = []

        if 'headlines' in data:
            headlines = data['headlines'][:3]  # Top 3
            parts.append(f"Headlines: {', '.join(h['title'] for h in headlines)}")

        if 'sentiment' in data:
            s = data['sentiment']
            parts.append(f"Sentiment: {s['score']:.2f} ({s['direction']})")

        if 'technical' in data:
            t = data['technical']
            parts.append(f"Technical: RSI {t['rsi']:.0f}, MACD {t['macd_signal']}")

        return " | ".join(parts)

    def _build_composite_text(
        self,
        date: datetime,
        current_data: Dict,
        historical_data: Optional[List[Dict]] = None
    ) -> str:
        """
        Build text with historical context and categorical decay.

        historical_data format:
        [
            {
                'date': datetime,
                'title': str,
                'category': str,  # e.g., 'regulatory_approval'
                'importance': float  # 0-1
            },
            ...
        ]
        """
        parts = []

        # Primary content (today)
        parts.append(f"PRIMARY ({date.strftime('%Y-%m-%d')}):")
        parts.append(self._build_daily_text(current_data))

        # Historical context with categorical decay
        if historical_data:
            historical_with_weights = []

            for item in historical_data:
                days_ago = (date - item['date']).days
                category = item.get('category', 'general')

                # Get category-specific persistence window
                max_days = self.config.event_persistence.get(category, 7)

                # Skip if outside window
                if days_ago > max_days:
                    continue

                # Calculate decay
                decay = 1.0 - (days_ago / max_days)
                weight = item['importance'] * decay

                historical_with_weights.append({
                    'title': item['title'],
                    'category': category,
                    'days_ago': days_ago,
                    'weight': weight
                })

            # Sort by weight, take top N
            historical_with_weights.sort(key=lambda x: x['weight'], reverse=True)
            top_historical = historical_with_weights[:self.config.max_historical_items]

            # Add to text
            for h in top_historical:
                parts.append(
                    f"CONTEXT (-{h['days_ago']}d, {h['category']}, w={h['weight']:.2f}): {h['title']}"
                )

        return "\n".join(parts)

    # =========================================================================
    # Advanced: Trend Emphasis (from the advice)
    # =========================================================================

    def compute_embedding_delta(
        self,
        date: datetime,
        current_embedding: np.ndarray
    ) -> Optional[np.ndarray]:
        """
        Compute Δv_t = v_t - v_{t-1} to capture directional change.

        This can be used as an additional feature to detect:
        - Regime changes (large delta)
        - Continuations (small delta)
        - Narrative shifts

        Returns:
            Delta vector, or None if no previous embedding
        """
        yesterday_date = date - timedelta(days=1)
        yesterday_embedding = self.embedding_cache.get(yesterday_date.isoformat())

        if yesterday_embedding is None:
            return None

        # Compute difference
        delta = current_embedding - yesterday_embedding

        return delta

    def get_embedding_magnitude_change(
        self,
        date: datetime,
        current_embedding: np.ndarray
    ) -> Optional[float]:
        """
        Compute ||Δv_t|| to measure how much narrative changed.

        Large magnitude = regime change
        Small magnitude = continuation
        """
        delta = self.compute_embedding_delta(date, current_embedding)

        if delta is None:
            return None

        return np.linalg.norm(delta)


# =============================================================================
# USAGE EXAMPLES
# =============================================================================

def example_pure_vector_blending():
    """
    Example: Pure vector blending (the advice you received)
    """
    from collections import namedtuple

    # Mock embedding function
    def mock_embed(text):
        # In reality: return model.embed(text)
        # For demo: return random vector
        return np.random.randn(1024)

    # Configure for pure vector blending
    config = EmbeddingConfig(
        strategy=TemporalStrategy.VECTOR_BLEND,
        alpha=0.15,  # 15% yesterday, 85% today
        normalize=True
    )

    engine = TemporalEmbeddingEngine(config, mock_embed)

    # Day 0
    day0_data = {
        'headlines': [{'title': 'SEC approves Bitcoin ETF'}],
        'sentiment': {'score': 0.85, 'direction': 'bullish'},
        'technical': {'rsi': 68, 'macd_signal': 'bullish'}
    }

    date0 = datetime(2024, 1, 10)
    emb0, meta0 = engine.generate_embedding(date0, day0_data)
    print(f"Day 0: Blend weight = {meta0['blend_weight']}")
    print(f"       Embedding shape = {emb0.shape}")
    print(f"       Has previous = {meta0['had_previous']}")

    # Day 1 - will blend 15% of Day 0
    day1_data = {
        'headlines': [{'title': 'Bitcoin rallies 15% on ETF hype'}],
        'sentiment': {'score': 0.82, 'direction': 'bullish'},
        'technical': {'rsi': 74, 'macd_signal': 'bullish'}
    }

    date1 = datetime(2024, 1, 11)
    emb1, meta1 = engine.generate_embedding(date1, day1_data)
    print(f"\nDay 1: Blend weight = {meta1['blend_weight']}")
    print(f"       Has previous = {meta1['had_previous']}")

    # Compute change
    change = engine.get_embedding_magnitude_change(date1, emb1)
    print(f"       Magnitude change = {change:.4f}")

    # Day 2 - will blend 15% of Day 1 (which contains 2.25% of Day 0)
    day2_data = {
        'headlines': [{'title': 'Profit-taking begins'}],
        'sentiment': {'score': 0.45, 'direction': 'neutral'},
        'technical': {'rsi': 64, 'macd_signal': 'neutral'}
    }

    date2 = datetime(2024, 1, 12)
    emb2, meta2 = engine.generate_embedding(date2, day2_data)
    print(f"\nDay 2: Blend weight = {meta2['blend_weight']}")

    # Bigger change (regime shift)
    change2 = engine.get_embedding_magnitude_change(date2, emb2)
    print(f"       Magnitude change = {change2:.4f}")
    print(f"       (larger = regime change detected)")


def example_hybrid_approach():
    """
    Example: Hybrid approach (text persistence + light blending)
    """
    # Mock embedding function
    def mock_embed(text):
        return np.random.randn(1024)

    # Configure for hybrid
    config = EmbeddingConfig(
        strategy=TemporalStrategy.HYBRID,
        alpha=0.15,  # Light blending
        lookback_days=7,
        min_importance=0.75,
        max_historical_items=3
    )

    engine = TemporalEmbeddingEngine(config, mock_embed)

    # Day 0
    date0 = datetime(2024, 1, 10)
    day0_data = {
        'headlines': [
            {'title': 'SEC approves Bitcoin ETF', 'importance': 0.95}
        ],
        'sentiment': {'score': 0.85, 'direction': 'bullish'},
        'technical': {'rsi': 68, 'macd_signal': 'bullish'}
    }

    emb0, meta0 = engine.generate_embedding(date0, day0_data)
    print(f"Day 0:")
    print(f"  Text: {meta0['embedding_text'][:100]}...")
    print(f"  Blend weight: {meta0['blend_weight']}")

    # Day 1 - ETF news persists in text
    date1 = datetime(2024, 1, 11)
    day1_data = {
        'headlines': [
            {'title': 'Bitcoin rallies 15%', 'importance': 0.80}
        ],
        'sentiment': {'score': 0.82, 'direction': 'bullish'},
        'technical': {'rsi': 74, 'macd_signal': 'bullish'}
    }

    # Historical context (ETF approval from yesterday)
    historical_data = [
        {
            'date': date0,
            'title': 'SEC approves Bitcoin ETF',
            'category': 'regulatory_approval',  # Persists 14 days
            'importance': 0.95
        }
    ]

    emb1, meta1 = engine.generate_embedding(date1, day1_data, historical_data)
    print(f"\nDay 1:")
    print(f"  Text: {meta1['embedding_text'][:200]}...")
    print(f"  Blend weight: {meta1['blend_weight']}")
    print(f"  Historical items: {meta1['historical_items']}")


if __name__ == "__main__":
    print("=" * 80)
    print("EXAMPLE 1: Pure Vector Blending (The Advice)")
    print("=" * 80)
    example_pure_vector_blending()

    print("\n\n")
    print("=" * 80)
    print("EXAMPLE 2: Hybrid Approach (Recommended)")
    print("=" * 80)
    example_hybrid_approach()
