"""
Hierarchical Multi-Timescale Memory System

Handles everything from HFT (milliseconds) to long-term holds (years).

Key Insight: Different timescales need different memory representations.

Timescale Hierarchy:
├── Microsecond (HFT): Order book dynamics, latency arbitrage
├── Second: Tick-level patterns, momentum bursts
├── Minute: Intraday patterns, news reactions
├── Hour: Day trading patterns, session effects
├── Day: Swing trading, overnight gaps
├── Week: Position trading, trend following
├── Month: Macro trends, seasonal patterns
└── Year+: Long-term cycles, regime shifts

Memory Tiers:
1. HOT (< 1 hour):  In-memory, 10k episodes, microsecond retrieval
2. WARM (1 hour - 1 week): In-memory, 100k episodes, millisecond retrieval
3. COLD (> 1 week): Disk/DB, unlimited episodes, second retrieval

State Compression:
- HFT: Full 384-dim state (need all microstructure details)
- Day: 256-dim state (aggregate some features)
- Week: 128-dim state (trend-focused)
- Month+: 64-dim state (macro patterns only)

Why This Matters:
- HFT cares about bid-ask spread (bps), order book depth
- Day trading cares about RSI, MACD, intraday patterns
- Swing trading cares about trends, support/resistance
- Long-term cares about fundamentals, macro sentiment

Academic References:
- Chen & Mozer (2019): "A Neural Tensor Network with Memory"
- Hierarchical RL: Dietterich (2000), Sutton et al. (1999)
- Multi-timescale learning: Doya (2002)
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import asyncio

from coinswarm.memory.simple_memory import Episode, Pattern, SimpleMemory

logger = logging.getLogger(__name__)


class Timescale(Enum):
    """Trading timescales"""
    MICROSECOND = "microsecond"  # HFT: < 1ms
    MILLISECOND = "millisecond"  # HFT: 1ms - 1s
    SECOND = "second"            # Scalping: 1s - 1min
    MINUTE = "minute"            # Intraday: 1min - 1h
    HOUR = "hour"                # Day trading: 1h - 1day
    DAY = "day"                  # Swing: 1day - 1week
    WEEK = "week"                # Position: 1week - 1month
    MONTH = "month"              # Long-term: 1month - 1year
    YEAR = "year"                # Ultra long: 1year+

    @property
    def duration_seconds(self) -> float:
        """Get approximate duration in seconds"""
        mapping = {
            Timescale.MICROSECOND: 0.000001,
            Timescale.MILLISECOND: 0.001,
            Timescale.SECOND: 1.0,
            Timescale.MINUTE: 60.0,
            Timescale.HOUR: 3600.0,
            Timescale.DAY: 86400.0,
            Timescale.WEEK: 604800.0,
            Timescale.MONTH: 2592000.0,  # ~30 days
            Timescale.YEAR: 31536000.0,  # ~365 days
        }
        return mapping[self]

    @classmethod
    def from_holding_period(cls, seconds: float) -> 'Timescale':
        """Determine timescale from holding period"""
        if seconds < 0.001:
            return cls.MICROSECOND
        elif seconds < 1.0:
            return cls.MILLISECOND
        elif seconds < 60.0:
            return cls.SECOND
        elif seconds < 3600.0:
            return cls.MINUTE
        elif seconds < 86400.0:
            return cls.HOUR
        elif seconds < 604800.0:
            return cls.DAY
        elif seconds < 2592000.0:
            return cls.WEEK
        elif seconds < 31536000.0:
            return cls.MONTH
        else:
            return cls.YEAR


@dataclass
class TimescaleConfig:
    """Configuration for a specific timescale"""
    timescale: Timescale
    max_episodes: int           # Max episodes to keep
    state_dimensions: int       # State vector size (compression)
    retention_period_days: int  # How long to keep episodes
    storage_tier: str           # "hot", "warm", "cold"
    retrieval_latency_ms: float # Expected retrieval latency

    # Feature importance weights (which features matter most?)
    price_weight: float = 1.0
    technical_weight: float = 1.0
    microstructure_weight: float = 1.0
    sentiment_weight: float = 1.0
    portfolio_weight: float = 1.0
    temporal_weight: float = 1.0


# Default configurations for each timescale
TIMESCALE_CONFIGS = {
    Timescale.MICROSECOND: TimescaleConfig(
        timescale=Timescale.MICROSECOND,
        max_episodes=1000,          # Keep last 1k HFT trades
        state_dimensions=384,       # Full detail
        retention_period_days=1,    # Keep 1 day
        storage_tier="hot",
        retrieval_latency_ms=0.01,  # 10 microseconds
        microstructure_weight=2.0,  # HFT cares most about microstructure
        technical_weight=0.1,       # Less relevant at microsecond scale
    ),
    Timescale.MILLISECOND: TimescaleConfig(
        timescale=Timescale.MILLISECOND,
        max_episodes=5000,
        state_dimensions=384,
        retention_period_days=7,
        storage_tier="hot",
        retrieval_latency_ms=0.1,
        microstructure_weight=2.0,
        technical_weight=0.5,
    ),
    Timescale.SECOND: TimescaleConfig(
        timescale=Timescale.SECOND,
        max_episodes=10000,
        state_dimensions=384,
        retention_period_days=30,
        storage_tier="hot",
        retrieval_latency_ms=1.0,
        microstructure_weight=1.5,
        technical_weight=1.0,
    ),
    Timescale.MINUTE: TimescaleConfig(
        timescale=Timescale.MINUTE,
        max_episodes=50000,
        state_dimensions=256,       # Some compression
        retention_period_days=90,
        storage_tier="warm",
        retrieval_latency_ms=5.0,
        technical_weight=1.5,       # Technicals matter for intraday
        microstructure_weight=1.0,
    ),
    Timescale.HOUR: TimescaleConfig(
        timescale=Timescale.HOUR,
        max_episodes=100000,
        state_dimensions=256,
        retention_period_days=180,
        storage_tier="warm",
        retrieval_latency_ms=10.0,
        technical_weight=2.0,       # Day trading is technical
        sentiment_weight=1.5,       # News matters
    ),
    Timescale.DAY: TimescaleConfig(
        timescale=Timescale.DAY,
        max_episodes=500000,
        state_dimensions=128,       # More compression
        retention_period_days=730,  # 2 years
        storage_tier="warm",
        retrieval_latency_ms=50.0,
        technical_weight=1.5,
        sentiment_weight=2.0,       # Swing trading follows news
        microstructure_weight=0.5,  # Less relevant
    ),
    Timescale.WEEK: TimescaleConfig(
        timescale=Timescale.WEEK,
        max_episodes=1000000,
        state_dimensions=128,
        retention_period_days=1825, # 5 years
        storage_tier="cold",
        retrieval_latency_ms=100.0,
        technical_weight=1.0,
        sentiment_weight=2.0,
        portfolio_weight=1.5,       # Position management matters
    ),
    Timescale.MONTH: TimescaleConfig(
        timescale=Timescale.MONTH,
        max_episodes=2000000,
        state_dimensions=64,        # Heavy compression
        retention_period_days=3650, # 10 years
        storage_tier="cold",
        retrieval_latency_ms=500.0,
        sentiment_weight=3.0,       # Macro sentiment dominates
        technical_weight=0.5,
        microstructure_weight=0.1,
    ),
    Timescale.YEAR: TimescaleConfig(
        timescale=Timescale.YEAR,
        max_episodes=5000000,       # Unlimited long-term memory
        state_dimensions=64,
        retention_period_days=7300, # 20 years
        storage_tier="cold",
        retrieval_latency_ms=1000.0,
        sentiment_weight=5.0,       # Long-term is all macro
        price_weight=2.0,           # Price trends
        technical_weight=0.1,
        microstructure_weight=0.01,
    ),
}


class HierarchicalMemory:
    """
    Multi-timescale memory system.

    Maintains separate memory stores for each timescale:
    - HFT memory (microseconds): Order book patterns
    - Intraday memory (minutes/hours): Day trading patterns
    - Swing memory (days/weeks): Multi-day patterns
    - Long-term memory (months/years): Macro trends

    When queried, returns patterns from appropriate timescale(s).
    """

    def __init__(
        self,
        enabled_timescales: Optional[List[Timescale]] = None
    ):
        """
        Initialize hierarchical memory.

        Args:
            enabled_timescales: Which timescales to enable (default: all)
        """
        if enabled_timescales is None:
            enabled_timescales = list(Timescale)

        # Create memory store for each timescale
        self.memories: Dict[Timescale, SimpleMemory] = {}

        for timescale in enabled_timescales:
            config = TIMESCALE_CONFIGS[timescale]

            self.memories[timescale] = SimpleMemory(
                max_episodes=config.max_episodes,
                pattern_update_frequency=max(100, config.max_episodes // 100),
                min_pattern_samples=max(5, config.max_episodes // 1000)
            )

        # Statistics
        self.stats = {
            "total_episodes_stored": 0,
            "episodes_by_timescale": {ts: 0 for ts in enabled_timescales}
        }

        logger.info(
            f"HierarchicalMemory initialized with {len(self.memories)} timescales: "
            f"{[ts.value for ts in enabled_timescales]}"
        )

    async def store_episode(
        self,
        timescale: Timescale,
        **episode_kwargs
    ) -> str:
        """
        Store episode in appropriate timescale memory.

        Args:
            timescale: Which timescale this episode belongs to
            **episode_kwargs: Episode data (same as SimpleMemory.store_episode)

        Returns:
            episode_id
        """
        if timescale not in self.memories:
            raise ValueError(f"Timescale {timescale} not enabled")

        # Compress state vector if needed
        state = episode_kwargs.get("state")
        if state is not None:
            config = TIMESCALE_CONFIGS[timescale]
            if len(state) > config.state_dimensions:
                # Compress using weighted feature selection
                state = self._compress_state(state, config)
                episode_kwargs["state"] = state

        # Store in appropriate memory
        episode_id = await self.memories[timescale].store_episode(**episode_kwargs)

        # Update stats
        self.stats["total_episodes_stored"] += 1
        self.stats["episodes_by_timescale"][timescale] += 1

        return episode_id

    async def recall_similar(
        self,
        state: np.ndarray,
        timescale: Timescale,
        k: int = 10,
        min_similarity: float = 0.7,
        cross_timescale: bool = False
    ) -> List[Tuple[Episode, float, Timescale]]:
        """
        Recall similar episodes from memory.

        Args:
            state: Current state vector
            timescale: Which timescale to query
            k: Number of similar episodes
            min_similarity: Minimum similarity threshold
            cross_timescale: If True, also check adjacent timescales

        Returns:
            List of (episode, similarity, timescale) tuples
        """
        results = []

        # Query primary timescale
        if timescale in self.memories:
            config = TIMESCALE_CONFIGS[timescale]

            # Compress state if needed
            compressed_state = state
            if len(state) > config.state_dimensions:
                compressed_state = self._compress_state(state, config)

            similar = await self.memories[timescale].recall_similar(
                compressed_state, k=k, min_similarity=min_similarity
            )

            # Add timescale tag
            results.extend([
                (ep, sim, timescale) for ep, sim in similar
            ])

        # Optionally check adjacent timescales
        if cross_timescale:
            adjacent = self._get_adjacent_timescales(timescale)
            for adj_ts in adjacent:
                if adj_ts in self.memories:
                    config = TIMESCALE_CONFIGS[adj_ts]
                    compressed_state = self._compress_state(state, config)

                    similar = await self.memories[adj_ts].recall_similar(
                        compressed_state, k=k//2, min_similarity=min_similarity
                    )

                    results.extend([
                        (ep, sim * 0.8, adj_ts) for ep, sim in similar  # Discount cross-timescale
                    ])

        # Sort by similarity
        results.sort(key=lambda x: x[1], reverse=True)

        return results[:k]

    def suggest_action(
        self,
        state: np.ndarray,
        timescale: Timescale,
        k: int = 10
    ) -> Tuple[str, float, Dict]:
        """
        Suggest best action for given state and timescale.

        Returns:
            (action, confidence, metadata)
        """
        if timescale not in self.memories:
            return "HOLD", 0.0, {"reason": "Timescale not enabled"}

        config = TIMESCALE_CONFIGS[timescale]
        compressed_state = self._compress_state(state, config)

        action, confidence = self.memories[timescale].suggest_action(
            compressed_state, k=k
        )

        metadata = {
            "timescale": timescale.value,
            "state_dimensions": len(compressed_state),
            "memory_size": len(self.memories[timescale].episodes)
        }

        return action, confidence, metadata

    def _compress_state(
        self,
        state: np.ndarray,
        config: TimescaleConfig
    ) -> np.ndarray:
        """
        Compress state vector based on timescale config.

        Uses weighted feature selection:
        - HFT: Keep all microstructure features
        - Day: Keep technical indicators
        - Long-term: Keep only macro sentiment

        Args:
            state: Full 384-dim state vector
            config: Timescale configuration

        Returns:
            Compressed state vector
        """
        if len(state) <= config.state_dimensions:
            return state

        # Feature ranges (from StateBuilder)
        price_range = (0, 24)
        technical_range = (24, 104)
        micro_range = (104, 144)
        sentiment_range = (144, 184)
        portfolio_range = (184, 224)
        temporal_range = (224, 384)

        # Calculate weighted importance for each feature
        importance = np.ones(len(state))

        importance[price_range[0]:price_range[1]] *= config.price_weight
        importance[technical_range[0]:technical_range[1]] *= config.technical_weight
        importance[micro_range[0]:micro_range[1]] *= config.microstructure_weight
        importance[sentiment_range[0]:sentiment_range[1]] *= config.sentiment_weight
        importance[portfolio_range[0]:portfolio_range[1]] *= config.portfolio_weight
        importance[temporal_range[0]:temporal_range[1]] *= config.temporal_weight

        # Select top N features by importance
        top_indices = np.argsort(importance)[-config.state_dimensions:]
        top_indices.sort()  # Maintain order

        compressed = state[top_indices]

        return compressed

    def _get_adjacent_timescales(self, timescale: Timescale) -> List[Timescale]:
        """Get adjacent timescales (one level up and down)"""
        all_scales = list(Timescale)
        idx = all_scales.index(timescale)

        adjacent = []
        if idx > 0:
            adjacent.append(all_scales[idx - 1])  # One level finer
        if idx < len(all_scales) - 1:
            adjacent.append(all_scales[idx + 1])  # One level coarser

        return adjacent

    def get_statistics(self) -> Dict:
        """Get memory statistics across all timescales"""
        stats = {
            "total_episodes": self.stats["total_episodes_stored"],
            "by_timescale": {}
        }

        for timescale, memory in self.memories.items():
            mem_stats = memory.get_statistics()
            stats["by_timescale"][timescale.value] = {
                "episodes": len(memory.episodes),
                "patterns": len(memory.patterns),
                "cache_utilization": mem_stats["cache_utilization"],
                "config": {
                    "max_episodes": TIMESCALE_CONFIGS[timescale].max_episodes,
                    "state_dims": TIMESCALE_CONFIGS[timescale].state_dimensions,
                    "retention_days": TIMESCALE_CONFIGS[timescale].retention_period_days
                }
            }

        return stats

    def __repr__(self):
        total_episodes = sum(len(m.episodes) for m in self.memories.values())
        return (
            f"HierarchicalMemory("
            f"timescales={len(self.memories)}, "
            f"episodes={total_episodes})"
        )
