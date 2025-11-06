"""
Learning Loop - Memory-Driven Strategy Evolution

Connects:
1. SimpleMemory - Stores complete trade context
2. TradeAnalysisAgent - Analyzes outcomes
3. StrategyLearningAgent - Evolves new strategies

Flow:
1. Committee votes → Execute trade
2. Store EVERYTHING in memory
3. Analyze trade outcome
4. Update agent/strategy weights
5. Evolve new strategies from successful patterns
6. Test new strategies in sandbox
7. Promote winners, cull losers
8. Repeat

Result: Self-improving system that gets better over time.
"""

import logging
import numpy as np
from typing import Dict, Optional, List
from datetime import datetime

from coinswarm.memory.simple_memory import SimpleMemory, Episode
from coinswarm.memory.state_builder import StateBuilder
from coinswarm.agents.trade_analysis_agent import TradeAnalysisAgent
from coinswarm.agents.strategy_learning_agent import StrategyLearningAgent
from coinswarm.agents.committee import AgentCommittee

logger = logging.getLogger(__name__)


class LearningLoop:
    """
    Orchestrates the learning cycle: Trade → Store → Analyze → Evolve → Repeat

    This is what makes the system LEARN and IMPROVE over time.
    """

    def __init__(
        self,
        memory: SimpleMemory,
        state_builder: StateBuilder,
        trade_analyzer: TradeAnalysisAgent,
        strategy_learner: StrategyLearningAgent,
        committee: AgentCommittee
    ):
        """
        Initialize learning loop.

        Args:
            memory: Memory system for episode storage
            state_builder: Builds state vectors from market data
            trade_analyzer: Analyzes trade outcomes
            strategy_learner: Evolves new strategies
            committee: Agent committee for voting
        """
        self.memory = memory
        self.state_builder = state_builder
        self.trade_analyzer = trade_analyzer
        self.strategy_learner = strategy_learner
        self.committee = committee

        # Open positions (track for outcome analysis)
        self.open_positions: Dict[str, Dict] = {}

        # Statistics
        self.stats = {
            "trades_opened": 0,
            "trades_closed": 0,
            "trades_stored": 0,
            "strategies_evolved": 0,
            "strategies_culled": 0
        }

        logger.info("LearningLoop initialized")

    async def on_trade_opened(
        self,
        symbol: str,
        action: str,
        price: float,
        size: float,
        decision: "CommitteeDecision",
        market_data: Dict,
        portfolio_state: Dict
    ) -> str:
        """
        Called when a trade is opened.

        Stores the trade context for later analysis when position closes.

        Args:
            symbol: Trading pair (e.g., "BTC-USD")
            action: "BUY" or "SELL"
            price: Entry price
            size: Position size
            decision: Committee decision with votes
            market_data: Market context at decision time
            portfolio_state: Portfolio state at decision time

        Returns:
            trade_id: Unique identifier for this trade
        """
        trade_id = f"{symbol}_{datetime.now().timestamp()}"

        # Build state vector for similarity matching
        state = self.state_builder.build_state(
            symbol=symbol,
            price=price,
            market_context=market_data.get("market_context"),
            technical_indicators=market_data.get("technical_indicators"),
            sentiment_data=market_data.get("sentiment_data"),
            portfolio_state=portfolio_state
        )

        # Store open position
        self.open_positions[trade_id] = {
            "symbol": symbol,
            "action": action,
            "entry_price": price,
            "size": size,
            "entry_time": datetime.now(),
            "decision": decision,
            "state": state,
            "market_data": market_data,
            "portfolio_state": portfolio_state
        }

        self.stats["trades_opened"] += 1

        logger.info(
            f"Trade opened: {trade_id} - {action} {size} {symbol} @ {price}"
        )

        return trade_id

    async def on_trade_closed(
        self,
        trade_id: str,
        exit_price: float,
        exit_reason: str = "manual"
    ) -> Optional[str]:
        """
        Called when a position is closed.

        This is where the LEARNING happens:
        1. Calculate P&L
        2. Store complete episode in memory
        3. Analyze trade outcome
        4. Update agent/strategy weights
        5. Evolve new strategies

        Args:
            trade_id: Trade identifier
            exit_price: Exit price
            exit_reason: Why position was closed

        Returns:
            episode_id: Memory episode ID (or None if trade not found)
        """
        if trade_id not in self.open_positions:
            logger.error(f"Trade {trade_id} not found in open positions")
            return None

        trade = self.open_positions[trade_id]

        # Calculate outcome
        entry_price = trade["entry_price"]
        size = trade["size"]
        action = trade["action"]

        if action == "BUY":
            pnl = (exit_price - entry_price) * size
            pnl_pct = (exit_price - entry_price) / entry_price
        else:  # SELL
            pnl = (entry_price - exit_price) * size
            pnl_pct = (entry_price - exit_price) / entry_price

        # Holding period
        entry_time = trade["entry_time"]
        exit_time = datetime.now()
        holding_period = (exit_time - entry_time).total_seconds() / 3600  # hours

        logger.info(
            f"Trade closed: {trade_id} - "
            f"{'WIN' if pnl > 0 else 'LOSS'} "
            f"${pnl:.2f} ({pnl_pct:+.2%}) "
            f"in {holding_period:.1f}h"
        )

        # === STEP 1: STORE IN MEMORY ===

        decision = trade["decision"]
        agent_votes = {}
        if hasattr(decision, 'votes') and decision.votes:
            agent_votes = {
                vote.agent_name: {
                    "action": vote.action,
                    "confidence": vote.confidence,
                    "reason": vote.reason
                }
                for vote in decision.votes
            }

        episode_id = await self.memory.store_episode(
            # Core trade
            action=action,
            symbol=trade["symbol"],
            price=entry_price,
            size=size,
            # Decision context
            confidence=decision.confidence,
            reason=decision.reason,
            agent_votes=agent_votes,
            # Market context
            state=trade["state"],
            market_context=trade["market_data"].get("market_context"),
            technical_indicators=trade["market_data"].get("technical_indicators"),
            sentiment_data=trade["market_data"].get("sentiment_data"),
            # Portfolio state
            portfolio_state=trade["portfolio_state"],
            # Outcome
            reward=pnl,
            holding_period=holding_period,
            exit_reason=exit_reason,
            # Metadata
            regime=self._detect_regime(trade["market_data"]),
            trade_type=self._classify_trade_type(agent_votes)
        )

        self.stats["trades_stored"] += 1

        # === STEP 2: ANALYZE TRADE ===

        # Use TradeAnalysisAgent to analyze outcome
        outcome = self.trade_analyzer.analyze_completed_trade(
            trade={
                "id": trade_id,
                "symbol": trade["symbol"],
                "size": size,
                "action": action,
                "timestamp": entry_time.isoformat()
            },
            entry_price=entry_price,
            exit_price=exit_price,
            committee_votes=[
                {"agent_name": name, "action": vote["action"], "reason": vote["reason"]}
                for name, vote in agent_votes.items()
            ]
        )

        # === STEP 3: UPDATE AGENT WEIGHTS ===

        # Update committee agents based on outcome
        self.committee.update_trade_result(
            trade={"id": trade_id},
            profitable=(pnl > 0)
        )

        # === STEP 4: UPDATE STRATEGY WEIGHTS ===

        # Get all strategy weights from trade analyzer
        strategy_weights = self.trade_analyzer.get_all_strategy_weights()

        # Update strategy learner
        self.strategy_learner.update_strategy_weights(strategy_weights)

        # === STEP 5: EVOLVE NEW STRATEGIES ===

        # Strategy learner automatically evolves in update_strategy_weights()
        # Track how many strategies exist
        old_count = len(self.strategy_learner.strategies)

        # Check if new strategies were created
        new_count = len(self.strategy_learner.strategies)
        if new_count > old_count:
            self.stats["strategies_evolved"] += (new_count - old_count)

        # Track culled strategies
        if new_count < old_count:
            self.stats["strategies_culled"] += (old_count - new_count)

        # === STEP 6: LOG LEARNING PROGRESS ===

        logger.info(
            f"Learning update: "
            f"memory={len(self.memory.episodes)}, "
            f"patterns={len(self.memory.patterns)}, "
            f"strategies={len(self.strategy_learner.strategies)}, "
            f"committee_win_rate={self.committee.win_rate:.2%}"
        )

        # Remove from open positions
        del self.open_positions[trade_id]
        self.stats["trades_closed"] += 1

        return episode_id

    def _detect_regime(self, market_data: Dict) -> str:
        """
        Detect market regime from market data.

        Regimes:
        - trending_up: Strong upward momentum
        - trending_down: Strong downward momentum
        - ranging: Sideways, low volatility
        - volatile: High volatility, no clear trend
        """
        indicators = market_data.get("technical_indicators", {})

        # Simple regime detection
        momentum = indicators.get("momentum_1d", 0.0)
        volatility = indicators.get("volatility_1d", 0.0)
        adx = indicators.get("adx", 0.0)

        # Trending if ADX > 25 (strong trend)
        if adx > 25:
            if momentum > 0.02:  # +2%
                return "trending_up"
            elif momentum < -0.02:  # -2%
                return "trending_down"

        # Volatile if volatility > 5%
        if volatility > 0.05:
            return "volatile"

        # Default: ranging
        return "ranging"

    def _classify_trade_type(self, agent_votes: Dict[str, Dict]) -> str:
        """
        Classify trade type based on which agents voted for it.

        Types:
        - momentum: TrendFollower voted
        - mean_reversion: MeanReversionAgent voted
        - news_driven: NewsAnalyst voted
        - sentiment: SentimentAgent voted
        - combined: Multiple different agents
        """
        agent_names = set(agent_votes.keys())

        # Check for specific agents
        if "TrendFollower" in agent_names or "TrendFollowingAgent" in agent_names:
            return "momentum"
        elif "MeanReversionAgent" in agent_names:
            return "mean_reversion"
        elif "NewsAnalyst" in agent_names or "ResearchAgent" in agent_names:
            return "news_driven"
        elif "SentimentAgent" in agent_names or "SentimentAnalysisAgent" in agent_names:
            return "sentiment"
        elif len(agent_names) > 2:
            return "combined"
        else:
            return "other"

    async def suggest_next_action(
        self,
        symbol: str,
        current_state: np.ndarray
    ) -> Dict:
        """
        Use memory to suggest best action for current state.

        This is how memory informs future decisions!

        Args:
            symbol: Trading pair
            current_state: Current state vector

        Returns:
            Dict with suggested action, confidence, and reasoning
        """
        # Get memory suggestion
        suggested_action, memory_confidence = self.memory.suggest_action(
            state=current_state,
            k=10  # Consider 10 most similar past situations
        )

        # Find similar episodes
        similar = await self.memory.recall_similar(
            state=current_state,
            k=5,
            min_similarity=0.7
        )

        # Build reasoning from similar episodes
        if similar:
            avg_reward = np.mean([ep.reward for ep, sim in similar])
            win_rate = np.mean([1 if ep.reward > 0 else 0 for ep, sim in similar])

            reasoning = (
                f"Memory suggests {suggested_action} based on {len(similar)} similar past trades. "
                f"Historical avg reward: ${avg_reward:.2f}, win rate: {win_rate:.1%}"
            )
        else:
            reasoning = "No similar past situations found. Using default strategy."

        return {
            "action": suggested_action,
            "confidence": memory_confidence,
            "reasoning": reasoning,
            "similar_episodes": len(similar)
        }

    def get_statistics(self) -> Dict:
        """Get learning loop statistics"""
        return {
            **self.stats,
            "open_positions": len(self.open_positions),
            "memory_stats": self.memory.get_statistics(),
            "analyzer_metrics": self.trade_analyzer.get_metrics(),
            "strategy_summary": self.strategy_learner.get_strategy_summary(),
            "committee_stats": self.committee.get_stats()
        }

    def __repr__(self):
        return (
            f"LearningLoop("
            f"trades={self.stats['trades_closed']}, "
            f"memory={len(self.memory.episodes)}, "
            f"strategies={len(self.strategy_learner.strategies)})"
        )
