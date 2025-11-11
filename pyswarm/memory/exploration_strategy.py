"""
Exploration Strategy - Random RL + Academic Patterns

Hybrid approach combining:
1. Random exploration (epsilon-greedy RL) - discover novel patterns
2. Established patterns (academic research) - bootstrap from proven strategies
3. Evolved patterns (genetic algorithm) - combine successful strategies

This balances:
- Exploitation: Use what works (established + learned patterns)
- Exploration: Try random things (might discover unique inefficiencies)

Example discoveries from random exploration:
- "BTC pumps every Tuesday 3pm" (day-of-week effect)
- "ETH follows BTC with 15min lag" (cross-asset correlation)
- "Funding rate > 0.1% predicts reversal" (market microstructure)
- "Low volume + tight spread = breakout soon" (liquidity pattern)

These patterns might never appear in academic research but could be real!
"""

import logging
import random
import numpy as np
from typing import Dict, Optional, Tuple, List
from datetime import datetime

from coinswarm.agents.base_agent import AgentVote

logger = logging.getLogger(__name__)


class ExplorationStrategy:
    """
    Manages exploration vs exploitation tradeoff.

    Three sources of strategies:
    1. Random exploration (epsilon% of time)
    2. Academic patterns (from research papers)
    3. Learned patterns (from experience)

    Epsilon-greedy algorithm:
    - With probability epsilon: Take RANDOM action (explore)
    - With probability 1-epsilon: Take BEST action (exploit)

    Epsilon decays over time as system learns:
    - Start: epsilon = 0.3 (30% random exploration)
    - After 1000 trades: epsilon = 0.1 (10% exploration)
    - After 10000 trades: epsilon = 0.05 (5% exploration)

    This ensures:
    - Early: Lots of exploration to discover patterns
    - Late: Mostly exploitation of learned patterns, but still some exploration
    """

    def __init__(
        self,
        epsilon_start: float = 0.3,  # Start with 30% random
        epsilon_end: float = 0.05,    # Decay to 5% random
        epsilon_decay: float = 0.9995, # Decay rate per trade
        random_seed: Optional[int] = None
    ):
        """
        Initialize exploration strategy.

        Args:
            epsilon_start: Initial exploration rate (0-1)
            epsilon_end: Minimum exploration rate (0-1)
            epsilon_decay: Decay multiplier per trade
            random_seed: Random seed for reproducibility
        """
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay

        if random_seed is not None:
            random.seed(random_seed)
            np.random.seed(random_seed)

        # Statistics
        self.stats = {
            "total_decisions": 0,
            "random_explorations": 0,
            "learned_exploitations": 0,
            "academic_exploitations": 0,
            "evolved_exploitations": 0,
            "novel_patterns_discovered": 0
        }

        logger.info(
            f"ExplorationStrategy initialized: "
            f"epsilon={epsilon_start:.2%} → {epsilon_end:.2%}"
        )

    def should_explore(self) -> bool:
        """
        Decide whether to explore (random) or exploit (best strategy).

        Returns:
            True if should explore randomly, False if should exploit
        """
        self.stats["total_decisions"] += 1

        # Epsilon-greedy decision
        if random.random() < self.epsilon:
            self.stats["random_explorations"] += 1
            logger.debug(f"EXPLORING (epsilon={self.epsilon:.3f})")
            return True
        else:
            logger.debug(f"EXPLOITING (epsilon={self.epsilon:.3f})")
            return False

    def get_random_action(
        self,
        market_context: Dict
    ) -> AgentVote:
        """
        Generate completely random action for exploration.

        This might discover patterns like:
        - Time-of-day effects
        - Day-of-week seasonality
        - Moon phase correlations (yes, really!)
        - Cross-asset lead-lag relationships
        - Orderbook imbalance signals
        - Funding rate extremes
        - Etc.

        Args:
            market_context: Current market data

        Returns:
            Random AgentVote
        """
        # Random action
        action = random.choice(["BUY", "SELL", "HOLD"])

        # Random confidence (but not too extreme)
        confidence = random.uniform(0.5, 0.9)

        # Random size (but reasonable)
        size = random.uniform(0.001, 0.02)

        # Log interesting market conditions for later pattern analysis
        timestamp = datetime.now()
        hour = timestamp.hour
        dow = timestamp.weekday()
        moon_phase = self._get_moon_phase(timestamp)  # Yes, people actually trade on this!

        reason = (
            f"RANDOM EXPLORATION: {action} at {hour:02d}:00 on "
            f"{['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][dow]}, "
            f"moon={moon_phase:.2f}"
        )

        return AgentVote(
            agent_name="RandomExplorer",
            action=action,
            confidence=confidence,
            size=size,
            reason=reason,
            veto=False  # Never veto (let risk agent handle that)
        )

    def get_best_action(
        self,
        learned_patterns: List[Dict],
        academic_patterns: List[Dict],
        evolved_patterns: List[Dict],
        current_state: np.ndarray
    ) -> Tuple[AgentVote, str]:
        """
        Get best action by comparing all pattern types.

        Ranks patterns by:
        1. Sharpe ratio (risk-adjusted return)
        2. Win rate
        3. Sample size (confidence)

        Args:
            learned_patterns: Patterns from experience (memory)
            academic_patterns: Patterns from research papers
            evolved_patterns: Patterns from genetic algorithm
            current_state: Current market state

        Returns:
            (best_vote, pattern_source)
            pattern_source: "learned", "academic", or "evolved"
        """
        # Combine all patterns with their source
        all_patterns = []

        for p in learned_patterns:
            all_patterns.append({**p, "source": "learned"})

        for p in academic_patterns:
            all_patterns.append({**p, "source": "academic"})

        for p in evolved_patterns:
            all_patterns.append({**p, "source": "evolved"})

        if not all_patterns:
            # No patterns yet, return neutral
            return AgentVote(
                agent_name="BestExploiter",
                action="HOLD",
                confidence=0.5,
                size=0.0,
                reason="No patterns available yet",
                veto=False
            ), "none"

        # Rank patterns by quality
        # Score = sharpe * win_rate * log(sample_size)
        for pattern in all_patterns:
            sharpe = pattern.get("sharpe_ratio", 0.0)
            win_rate = pattern.get("win_rate", 0.5)
            n_samples = max(pattern.get("sample_size", 1), 1)

            pattern["score"] = sharpe * win_rate * np.log(n_samples)

        # Select best pattern
        best_pattern = max(all_patterns, key=lambda p: p["score"])
        source = best_pattern["source"]

        # Update stats
        if source == "learned":
            self.stats["learned_exploitations"] += 1
        elif source == "academic":
            self.stats["academic_exploitations"] += 1
        elif source == "evolved":
            self.stats["evolved_exploitations"] += 1

        # Generate vote from best pattern
        vote = AgentVote(
            agent_name=f"BestExploiter[{source}]",
            action=best_pattern.get("action", "HOLD"),
            confidence=best_pattern.get("confidence", 0.7),
            size=best_pattern.get("size", 0.01),
            reason=f"Best {source} pattern: {best_pattern.get('name', 'unknown')} "
                   f"(sharpe={best_pattern.get('sharpe_ratio', 0):.2f}, "
                   f"win_rate={best_pattern.get('win_rate', 0):.1%})",
            veto=False
        )

        return vote, source

    def update_epsilon(self):
        """
        Decay epsilon after each trade.

        Gradually reduces exploration as system learns.
        """
        old_epsilon = self.epsilon
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)

        if old_epsilon != self.epsilon:
            logger.debug(f"Epsilon decayed: {old_epsilon:.4f} → {self.epsilon:.4f}")

    def mark_novel_pattern_discovered(self, pattern_description: str):
        """
        Mark that a novel pattern was discovered through random exploration.

        These are the gems we're looking for!
        """
        self.stats["novel_patterns_discovered"] += 1
        logger.info(
            f"🎉 NOVEL PATTERN DISCOVERED #{self.stats['novel_patterns_discovered']}: "
            f"{pattern_description}"
        )

    def get_statistics(self) -> Dict:
        """Get exploration statistics"""
        total = max(self.stats["total_decisions"], 1)

        return {
            **self.stats,
            "current_epsilon": self.epsilon,
            "exploration_rate": self.stats["random_explorations"] / total,
            "exploitation_rate": (total - self.stats["random_explorations"]) / total,
            "learned_ratio": self.stats["learned_exploitations"] / total,
            "academic_ratio": self.stats["academic_exploitations"] / total,
            "evolved_ratio": self.stats["evolved_exploitations"] / total
        }

    @staticmethod
    def _get_moon_phase(timestamp: datetime) -> float:
        """
        Calculate moon phase (0=new moon, 0.5=full moon, 1=new moon).

        Yes, some traders actually use this! There's research showing
        weak correlations between lunar cycles and market behavior.

        Source: Dichev & Janes (2003) "Lunar Cycle Effects in Stock Returns"
        """
        # Synodic month (new moon to new moon): 29.53059 days
        # Known new moon: 2000-01-06 18:14 UTC
        known_new_moon = datetime(2000, 1, 6, 18, 14)

        days_since = (timestamp - known_new_moon).total_seconds() / 86400
        phase = (days_since % 29.53059) / 29.53059

        return phase

    def __repr__(self):
        return (
            f"ExplorationStrategy("
            f"epsilon={self.epsilon:.3f}, "
            f"explorations={self.stats['random_explorations']}, "
            f"novel_patterns={self.stats['novel_patterns_discovered']})"
        )


class PatternDiscovery:
    """
    Analyzes random exploration results to discover novel patterns.

    Process:
    1. Random exploration generates diverse trades
    2. After enough samples, cluster by outcome
    3. Look for statistically significant patterns
    4. Extract pattern conditions (e.g., "time=Tuesday 3pm → +2% avg return")
    5. Test pattern on validation set
    6. If validated, promote to learned patterns

    This is how we discover things like:
    - "BTC pumps every Tuesday" (if real)
    - "Funding rate > 0.1% predicts reversal" (if real)
    - "Low volume + tight spread = breakout" (if real)

    Many will be noise, but some might be real!
    """

    def __init__(
        self,
        min_samples: int = 50,  # Need 50+ samples to detect pattern
        significance_threshold: float = 0.05,  # p-value < 0.05
        min_sharpe: float = 1.0  # Pattern must have Sharpe > 1.0
    ):
        self.min_samples = min_samples
        self.significance_threshold = significance_threshold
        self.min_sharpe = min_sharpe

        # Random exploration results
        self.random_episodes: List[Dict] = []

        logger.info(
            f"PatternDiscovery initialized: "
            f"min_samples={min_samples}, p_threshold={significance_threshold}"
        )

    def add_random_episode(
        self,
        episode: Dict,
        reward: float
    ):
        """Add random exploration result"""
        self.random_episodes.append({
            **episode,
            "reward": reward
        })

        # Try to discover patterns periodically
        if len(self.random_episodes) % 50 == 0:
            self.discover_patterns()

    def discover_patterns(self) -> List[Dict]:
        """
        Attempt to discover statistically significant patterns.

        Returns:
            List of discovered patterns (may be empty)
        """
        if len(self.random_episodes) < self.min_samples:
            return []

        logger.info(
            f"Attempting pattern discovery from "
            f"{len(self.random_episodes)} random episodes"
        )

        discovered = []

        # Check various pattern hypotheses:
        # 1. Time-of-day effects
        # 2. Day-of-week effects
        # 3. Moon phase effects (yes, really)
        # 4. Market condition effects
        # Etc.

        # TODO: Implement statistical tests (t-test, chi-square, etc.)
        # For now, just log that we're looking

        logger.info(f"Pattern discovery: {len(discovered)} patterns found")

        return discovered

    def __repr__(self):
        return f"PatternDiscovery(episodes={len(self.random_episodes)})"
