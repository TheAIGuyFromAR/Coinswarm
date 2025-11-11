"""
Simple In-Memory Learning System

Phase 0 implementation: In-memory storage without Redis/NATS/Quorum complexity.

Features:
- Episodic memory: Store (state, action, reward) tuples
- Pattern recall: Find similar past situations using cosine similarity
- Performance tracking: Learn which actions work in which contexts
- LRU eviction: Keep most recent 1000 entries

Future: Upgrade to Redis vector DB + quorum voting when scaling to multi-user.
"""

import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class Episode:
    """
    Single trading episode stored in memory.

    Captures complete context: what trade was made, why it was made,
    all information that informed the decision, and the outcome.
    """

    # ==================== WHAT WAS DONE ====================

    # Action taken
    action: str  # "BUY", "SELL", "HOLD"
    symbol: str
    price: float  # Execution price
    size: float  # Position size
    timestamp: datetime

    # ==================== WHY IT WAS DONE ====================

    # Committee decision
    confidence: float = 0.0  # Committee confidence (0-1)
    reason: str = ""  # Human-readable explanation

    # Individual agent votes (for attribution)
    agent_votes: Dict[str, Dict] = field(default_factory=dict)
    # Format: {"TrendFollower": {"action": "BUY", "confidence": 0.85, "reason": "..."}}

    # ==================== MARKET CONTEXT ====================

    # State embedding (compressed features for similarity matching)
    state: np.ndarray = field(default_factory=lambda: np.array([]))  # Shape: (n_features,)

    # Raw market data at decision time
    market_context: Dict = field(default_factory=dict)
    # Contains:
    # - "price": current price
    # - "volume_24h": 24h volume
    # - "bid_ask_spread": spread in bps
    # - "orderbook_depth": top of book depth
    # - "recent_volatility": recent volatility measure

    # Technical indicators
    technical_indicators: Dict = field(default_factory=dict)
    # Contains:
    # - "rsi": RSI value
    # - "macd": MACD value
    # - "ma_20": 20-period MA
    # - "ma_50": 50-period MA
    # - "bollinger_upper/lower": Bollinger bands
    # - "atr": Average True Range

    # Sentiment signals
    sentiment_data: Dict = field(default_factory=dict)
    # Contains:
    # - "news_sentiment": Aggregated news sentiment (-1 to 1)
    # - "social_sentiment": Twitter/Reddit sentiment
    # - "funding_rate": Perpetual funding rate
    # - "fear_greed_index": Market fear/greed

    # ==================== PORTFOLIO STATE ====================

    # Current portfolio state when trade was made
    portfolio_state: Dict = field(default_factory=dict)
    # Contains:
    # - "total_value": Total portfolio value
    # - "cash_available": Available cash
    # - "positions": Current positions {symbol: size}
    # - "daily_pnl": P&L today
    # - "drawdown": Current drawdown from peak
    # - "risk_utilization": % of risk budget used

    # ==================== OUTCOME ====================

    # Trade outcome
    reward: float = 0.0  # Actual P&L (can be negative)
    holding_period: float = 0.0  # How long position was held (hours)
    exit_reason: str = ""  # "take_profit", "stop_loss", "signal_reverse", etc.

    # Execution quality
    slippage: float = 0.0  # Actual fill vs expected (bps)
    fill_time: float = 0.0  # Execution time (ms)
    transaction_cost: float = 0.0  # Fees + slippage

    # ==================== METADATA ====================

    episode_id: str = ""  # Unique identifier
    regime: str = ""  # Market regime: "trending_up", "ranging", "volatile", etc.
    trade_type: str = ""  # "momentum", "mean_reversion", "breakout", etc.

    def __post_init__(self):
        """Validate and generate defaults"""
        if self.action not in ["BUY", "SELL", "HOLD"]:
            raise ValueError(f"Invalid action: {self.action}")

        # Generate episode ID if not provided
        if not self.episode_id:
            self.episode_id = f"{self.symbol}_{self.timestamp.timestamp()}"

        # Validate state vector if provided
        if len(self.state) > 0 and self.state.ndim != 1:
            raise ValueError(f"State must be 1D array, got shape {self.state.shape}")


@dataclass
class Pattern:
    """Cluster of similar episodes with aggregate statistics"""

    # Pattern identity
    pattern_id: str
    centroid: np.ndarray  # Average state vector

    # Episodes in this pattern
    episodes: List[Episode] = field(default_factory=list)

    # Statistics
    n_samples: int = 0
    mean_reward: float = 0.0
    std_reward: float = 0.0
    win_rate: float = 0.0
    sharpe_ratio: float = 0.0

    # Action distribution
    action_counts: Dict[str, int] = field(default_factory=lambda: {"BUY": 0, "SELL": 0, "HOLD": 0})

    # Performance by action
    reward_by_action: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

    def update_statistics(self):
        """Recalculate statistics from episodes"""
        if not self.episodes:
            return

        self.n_samples = len(self.episodes)

        # Reward statistics
        rewards = [ep.reward for ep in self.episodes]
        self.mean_reward = np.mean(rewards)
        self.std_reward = np.std(rewards)

        # Win rate
        wins = sum(1 for r in rewards if r > 0)
        self.win_rate = wins / len(rewards) if rewards else 0.0

        # Sharpe ratio (annualized, assuming daily frequency)
        self.sharpe_ratio = (self.mean_reward / self.std_reward * np.sqrt(365)) if self.std_reward > 0 else 0.0

        # Action distribution
        self.action_counts = {"BUY": 0, "SELL": 0, "HOLD": 0}
        for ep in self.episodes:
            self.action_counts[ep.action] += 1

        # Performance by action
        self.reward_by_action = defaultdict(list)
        for ep in self.episodes:
            self.reward_by_action[ep.action].append(ep.reward)

        # Update centroid
        states = np.array([ep.state for ep in self.episodes])
        self.centroid = np.mean(states, axis=0)

        self.last_updated = datetime.now()

    def get_best_action(self) -> Tuple[str, float]:
        """
        Determine best action for this pattern based on historical performance.

        Returns:
            (action, expected_reward)
        """
        action_rewards = {}
        for action in ["BUY", "SELL", "HOLD"]:
            if self.reward_by_action[action]:
                action_rewards[action] = np.mean(self.reward_by_action[action])
            else:
                action_rewards[action] = 0.0

        best_action = max(action_rewards, key=action_rewards.get)
        expected_reward = action_rewards[best_action]

        return best_action, expected_reward


class SimpleMemory:
    """
    Simple in-memory episodic learning system.

    This is Phase 0: Single-process, in-memory only.
    No Redis, no NATS, no quorum voting.

    Features:
    - Store trading episodes with outcomes
    - Recall similar past situations
    - Learn which actions work in which contexts
    - Pattern extraction (clustering)
    - Performance attribution

    Usage:
        memory = SimpleMemory(max_episodes=1000)

        # After each trade
        await memory.store_episode(
            state=state_features,
            action="BUY",
            reward=pnl,
            symbol="BTC-USD",
            price=50000,
            size=0.01
        )

        # Before making decision
        similar = await memory.recall_similar(state_features, k=10)
        best_action, confidence = memory.suggest_action(state_features)
    """

    def __init__(
        self,
        max_episodes: int = 1000,
        pattern_update_frequency: int = 100,  # Update patterns every N episodes
        min_pattern_samples: int = 5  # Minimum episodes to form a pattern
    ):
        """
        Initialize simple memory system.

        Args:
            max_episodes: Maximum episodes to keep (LRU eviction)
            pattern_update_frequency: How often to recompute patterns
            min_pattern_samples: Minimum samples required to form pattern
        """
        self.max_episodes = max_episodes
        self.pattern_update_frequency = pattern_update_frequency
        self.min_pattern_samples = min_pattern_samples

        # Storage
        self.episodes: List[Episode] = []
        self.patterns: Dict[str, Pattern] = {}

        # Statistics
        self.total_episodes_stored = 0
        self.episodes_evicted = 0
        self.pattern_updates = 0

        logger.info(
            f"SimpleMemory initialized: max_episodes={max_episodes}, "
            f"pattern_freq={pattern_update_frequency}"
        )

    async def store_episode(
        self,
        # Core trade info
        action: str,
        symbol: str,
        price: float,
        size: float,
        # Decision context
        confidence: float = 0.0,
        reason: str = "",
        agent_votes: Optional[Dict[str, Dict]] = None,
        # Market context
        state: Optional[np.ndarray] = None,
        market_context: Optional[Dict] = None,
        technical_indicators: Optional[Dict] = None,
        sentiment_data: Optional[Dict] = None,
        # Portfolio state
        portfolio_state: Optional[Dict] = None,
        # Outcome
        reward: float = 0.0,
        holding_period: float = 0.0,
        exit_reason: str = "",
        slippage: float = 0.0,
        fill_time: float = 0.0,
        transaction_cost: float = 0.0,
        # Metadata
        regime: str = "",
        trade_type: str = ""
    ) -> str:
        """
        Store a completed trade episode with full context.

        This captures:
        1. WHAT: action, symbol, price, size
        2. WHY: confidence, reason, agent_votes
        3. MARKET CONTEXT: state vector, market data, technicals, sentiment
        4. PORTFOLIO STATE: positions, cash, drawdown, risk
        5. OUTCOME: reward, holding period, exit reason, execution quality

        Args:
            action: Action taken ("BUY", "SELL", "HOLD")
            symbol: Trading pair (e.g., "BTC-USD")
            price: Execution price
            size: Position size
            confidence: Committee confidence (0-1)
            reason: Human-readable explanation
            agent_votes: Individual agent votes with reasoning
            state: State feature vector (for similarity matching)
            market_context: Raw market data (price, volume, spread, etc.)
            technical_indicators: Technical indicators (RSI, MACD, etc.)
            sentiment_data: Sentiment signals (news, social, funding)
            portfolio_state: Portfolio state (value, positions, drawdown)
            reward: Realized P&L
            holding_period: How long position was held (hours)
            exit_reason: Why position was closed
            slippage: Execution slippage (bps)
            fill_time: Fill time (ms)
            transaction_cost: Total costs (fees + slippage)
            regime: Market regime tag
            trade_type: Trade type classification

        Returns:
            episode_id: Unique identifier for this episode
        """
        episode = Episode(
            # Core
            action=action,
            symbol=symbol,
            price=price,
            size=size,
            timestamp=datetime.now(),
            # Decision
            confidence=confidence,
            reason=reason,
            agent_votes=agent_votes or {},
            # Market
            state=state if state is not None else np.array([]),
            market_context=market_context or {},
            technical_indicators=technical_indicators or {},
            sentiment_data=sentiment_data or {},
            # Portfolio
            portfolio_state=portfolio_state or {},
            # Outcome
            reward=reward,
            holding_period=holding_period,
            exit_reason=exit_reason,
            slippage=slippage,
            fill_time=fill_time,
            transaction_cost=transaction_cost,
            # Metadata
            regime=regime,
            trade_type=trade_type
        )

        # Add to storage
        self.episodes.append(episode)
        self.total_episodes_stored += 1

        # LRU eviction if over capacity
        if len(self.episodes) > self.max_episodes:
            evicted = self.episodes.pop(0)
            self.episodes_evicted += 1
            logger.debug(f"Evicted episode from {evicted.timestamp}")

        # Update patterns periodically
        if self.total_episodes_stored % self.pattern_update_frequency == 0:
            await self._update_patterns()

        logger.info(
            f"Stored episode {episode.episode_id}: {action} {symbol} @ {price}, "
            f"reward={reward:.4f}, confidence={confidence:.2f}, "
            f"reason='{reason[:50]}...', total={len(self.episodes)}"
        )

        return episode.episode_id

    async def recall_similar(
        self,
        state: np.ndarray,
        k: int = 10,
        min_similarity: float = 0.7
    ) -> List[Tuple[Episode, float]]:
        """
        Find k most similar past episodes using cosine similarity.

        Args:
            state: Current state vector
            k: Number of similar episodes to return
            min_similarity: Minimum cosine similarity threshold

        Returns:
            List of (episode, similarity) tuples, sorted by similarity
        """
        if not self.episodes:
            return []

        # Compute similarities
        similarities = []
        for episode in self.episodes:
            sim = self._cosine_similarity(state, episode.state)
            if sim >= min_similarity:
                similarities.append((episode, sim))

        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Return top k
        return similarities[:k]

    def suggest_action(
        self,
        state: np.ndarray,
        k: int = 10
    ) -> Tuple[str, float]:
        """
        Suggest best action for given state based on similar past episodes.

        Args:
            state: Current state vector
            k: Number of similar episodes to consider

        Returns:
            (suggested_action, confidence)
            confidence = expected reward normalized to [0, 1]
        """
        similar = self.recall_similar(state, k=k)

        if not similar:
            return "HOLD", 0.0

        # Aggregate rewards by action (weighted by similarity)
        action_rewards = defaultdict(list)
        action_weights = defaultdict(list)

        for episode, similarity in similar:
            action_rewards[episode.action].append(episode.reward)
            action_weights[episode.action].append(similarity)

        # Calculate weighted average reward for each action
        weighted_rewards = {}
        for action in action_rewards:
            rewards = np.array(action_rewards[action])
            weights = np.array(action_weights[action])
            weighted_rewards[action] = np.average(rewards, weights=weights)

        # Choose action with highest expected reward
        best_action = max(weighted_rewards, key=weighted_rewards.get)
        expected_reward = weighted_rewards[best_action]

        # Normalize confidence to [0, 1]
        # Assuming rewards are typically in [-0.1, 0.1] range (±10%)
        confidence = np.clip((expected_reward + 0.1) / 0.2, 0, 1)

        return best_action, confidence

    async def _update_patterns(self) -> None:
        """
        Extract patterns from episodes using simple k-means clustering.

        This is called periodically to update pattern library.
        """
        if len(self.episodes) < self.min_pattern_samples:
            return

        # Simple k-means clustering
        # For Phase 0, use fixed k=5 clusters
        k = min(5, len(self.episodes) // self.min_pattern_samples)

        if k < 1:
            return

        # Extract state vectors
        states = np.array([ep.state for ep in self.episodes])

        # Initialize centroids randomly
        indices = np.random.choice(len(states), k, replace=False)
        centroids = states[indices]

        # K-means iterations (simple implementation)
        for _ in range(10):  # Fixed 10 iterations
            # Assign episodes to nearest centroid
            assignments = []
            for state in states:
                distances = [np.linalg.norm(state - c) for c in centroids]
                assignments.append(np.argmin(distances))

            # Update centroids
            new_centroids = []
            for i in range(k):
                cluster_states = states[np.array(assignments) == i]
                if len(cluster_states) > 0:
                    new_centroids.append(np.mean(cluster_states, axis=0))
                else:
                    new_centroids.append(centroids[i])
            centroids = np.array(new_centroids)

        # Create patterns from clusters
        self.patterns = {}
        for i in range(k):
            cluster_episodes = [ep for j, ep in enumerate(self.episodes) if assignments[j] == i]

            if len(cluster_episodes) >= self.min_pattern_samples:
                pattern = Pattern(
                    pattern_id=f"pattern_{i}_{datetime.now().timestamp()}",
                    centroid=centroids[i],
                    episodes=cluster_episodes
                )
                pattern.update_statistics()
                self.patterns[pattern.pattern_id] = pattern

        self.pattern_updates += 1
        logger.info(f"Updated patterns: {len(self.patterns)} patterns from {len(self.episodes)} episodes")

    def get_pattern_for_state(self, state: np.ndarray) -> Optional[Pattern]:
        """Find the pattern that best matches this state"""
        if not self.patterns:
            return None

        best_pattern = None
        best_similarity = -1

        for pattern in self.patterns.values():
            sim = self._cosine_similarity(state, pattern.centroid)
            if sim > best_similarity:
                best_similarity = sim
                best_pattern = pattern

        return best_pattern if best_similarity > 0.7 else None

    def get_statistics(self) -> Dict:
        """Get memory system statistics"""
        return {
            "total_episodes": len(self.episodes),
            "episodes_stored": self.total_episodes_stored,
            "episodes_evicted": self.episodes_evicted,
            "patterns_count": len(self.patterns),
            "pattern_updates": self.pattern_updates,
            "cache_utilization": len(self.episodes) / self.max_episodes,
            "patterns": [
                {
                    "pattern_id": p.pattern_id,
                    "n_samples": p.n_samples,
                    "mean_reward": p.mean_reward,
                    "sharpe_ratio": p.sharpe_ratio,
                    "win_rate": p.win_rate,
                    "best_action": p.get_best_action()[0]
                }
                for p in self.patterns.values()
            ]
        }

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors"""
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (norm_a * norm_b)

    def __repr__(self):
        return (
            f"SimpleMemory("
            f"episodes={len(self.episodes)}/{self.max_episodes}, "
            f"patterns={len(self.patterns)}, "
            f"win_rate={self._calculate_overall_win_rate():.2%})"
        )

    def _calculate_overall_win_rate(self) -> float:
        """Calculate overall win rate from all episodes"""
        if not self.episodes:
            return 0.0
        wins = sum(1 for ep in self.episodes if ep.reward > 0)
        return wins / len(self.episodes)
