"""
Trade Analysis Agent

Analyzes completed trades to determine success and extract insights.

Key responsibilities:
- Track trade outcomes (profitable vs losing)
- Calculate metrics (P&L, Sharpe ratio, win rate, etc.)
- Identify which agents contributed to successful trades
- Update agent weights based on performance
- Store trade patterns for strategy learning
"""

import logging
from dataclasses import dataclass
from datetime import datetime

from coinswarm.agents.base_agent import AgentVote, BaseAgent
from coinswarm.data_ingest.base import DataPoint

logger = logging.getLogger(__name__)


@dataclass
class TradeOutcome:
    """Outcome of a completed trade"""
    trade_id: str
    symbol: str
    entry_price: float
    exit_price: float
    size: float
    pnl: float  # Profit/loss in USD
    pnl_pct: float  # Profit/loss as percentage
    duration_seconds: float
    winning: bool
    contributing_agents: list[str]  # Agents that voted for this trade
    strategy_tags: list[str]  # Strategy patterns (e.g., "trend_uptrend", "news_positive")


class TradeAnalysisAgent(BaseAgent):
    """
    Post-trade analysis agent.

    Runs AFTER trades complete to:
    1. Calculate actual P&L
    2. Determine which agents contributed
    3. Update agent weights (reward winners, penalize losers)
    4. Extract strategy patterns for learning
    """

    def __init__(
        self,
        name: str = "TradeAnalyzer",
        weight: float = 0.0,  # Doesn't vote on trades
        lookback_period: int = 100  # Analyze last N trades
    ):
        super().__init__(name, weight)
        self.lookback_period = lookback_period

        # Trade history
        self.trade_outcomes: list[TradeOutcome] = []

        # Performance metrics
        self.metrics = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "total_pnl_pct": 0.0,
            "best_trade_pnl": 0.0,
            "worst_trade_pnl": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,  # Total wins / total losses
            "sharpe_ratio": 0.0,
        }

    async def analyze(
        self,
        tick: DataPoint,
        position: dict | None,
        market_context: dict
    ) -> AgentVote:
        """
        Trade analyzer doesn't vote on new trades.
        Returns neutral HOLD vote.
        """
        return AgentVote(
            agent_name=self.name,
            action="HOLD",
            confidence=0.5,
            size=0.0,
            reason="Trade analyzer does not vote on new trades"
        )

    def analyze_completed_trade(
        self,
        trade: dict,
        entry_price: float,
        exit_price: float,
        committee_votes: list[dict]
    ) -> TradeOutcome:
        """
        Analyze a completed trade.

        Args:
            trade: Trade data (from database)
            entry_price: Entry price
            exit_price: Exit price (current market price)
            committee_votes: Votes from agents when trade was placed

        Returns:
            TradeOutcome with P&L and insights
        """

        symbol = trade["symbol"]
        size = trade["size"]
        action = trade["action"]

        # Calculate P&L
        if action == "BUY":
            pnl = (exit_price - entry_price) * size
            pnl_pct = (exit_price - entry_price) / entry_price
        else:  # SELL
            pnl = (entry_price - exit_price) * size
            pnl_pct = (entry_price - exit_price) / entry_price

        # Duration
        entry_time = datetime.fromisoformat(trade["timestamp"])
        exit_time = datetime.now()
        duration_seconds = (exit_time - entry_time).total_seconds()

        # Extract contributing agents (those who voted for winning action)
        contributing_agents = [
            vote["agent_name"]
            for vote in committee_votes
            if vote["action"] == action
        ]

        # Extract strategy tags from reasons
        strategy_tags = self._extract_strategy_tags(committee_votes)

        # Create outcome
        outcome = TradeOutcome(
            trade_id=trade["id"],
            symbol=symbol,
            entry_price=entry_price,
            exit_price=exit_price,
            size=size,
            pnl=pnl,
            pnl_pct=pnl_pct,
            duration_seconds=duration_seconds,
            winning=pnl > 0,
            contributing_agents=contributing_agents,
            strategy_tags=strategy_tags
        )

        # Store outcome
        self.trade_outcomes.append(outcome)
        if len(self.trade_outcomes) > self.lookback_period:
            self.trade_outcomes.pop(0)

        # Update metrics
        self._update_metrics()

        # Log outcome
        logger.info(
            f"Trade {outcome.trade_id}: "
            f"{'WIN' if outcome.winning else 'LOSS'} "
            f"${outcome.pnl:.2f} ({outcome.pnl_pct:+.2%}) "
            f"in {outcome.duration_seconds:.0f}s"
        )

        return outcome

    def _extract_strategy_tags(self, committee_votes: list[dict]) -> list[str]:
        """
        Extract strategy tags from agent vote reasons.

        Examples:
        - "Uptrend: momentum=2.5%" → "trend_uptrend"
        - "Positive news sentiment" → "news_positive"
        - "RSI oversold" → "rsi_oversold"
        """

        tags = []

        for vote in committee_votes:
            reason = vote.get("reason", "").lower()

            # Trend patterns
            if "uptrend" in reason or "momentum" in reason:
                tags.append("trend_uptrend")
            if "downtrend" in reason:
                tags.append("trend_downtrend")
            if "rsi" in reason and "oversold" in reason:
                tags.append("rsi_oversold")
            if "rsi" in reason and "overbought" in reason:
                tags.append("rsi_overbought")

            # News patterns
            if "positive" in reason and "news" in reason:
                tags.append("news_positive")
            if "negative" in reason and "news" in reason:
                tags.append("news_negative")

            # Mean reversion
            if "mean reversion" in reason:
                tags.append("mean_reversion")

            # Breakout
            if "breakout" in reason:
                tags.append("breakout")

            # Arbitrage
            if "arbitrage" in reason:
                tags.append("arbitrage")

        return list(set(tags))  # Deduplicate

    def _update_metrics(self):
        """Update performance metrics from trade history"""

        if not self.trade_outcomes:
            return

        # Basic counts
        self.metrics["total_trades"] = len(self.trade_outcomes)
        self.metrics["winning_trades"] = sum(1 for t in self.trade_outcomes if t.winning)
        self.metrics["losing_trades"] = sum(1 for t in self.trade_outcomes if not t.winning)

        # P&L
        self.metrics["total_pnl"] = sum(t.pnl for t in self.trade_outcomes)
        self.metrics["total_pnl_pct"] = sum(t.pnl_pct for t in self.trade_outcomes)

        # Best/worst
        self.metrics["best_trade_pnl"] = max(t.pnl for t in self.trade_outcomes)
        self.metrics["worst_trade_pnl"] = min(t.pnl for t in self.trade_outcomes)

        # Win/loss averages
        winning_trades = [t for t in self.trade_outcomes if t.winning]
        losing_trades = [t for t in self.trade_outcomes if not t.winning]

        if winning_trades:
            self.metrics["avg_win"] = sum(t.pnl for t in winning_trades) / len(winning_trades)

        if losing_trades:
            self.metrics["avg_loss"] = sum(t.pnl for t in losing_trades) / len(losing_trades)

        # Win rate
        self.metrics["win_rate"] = self.metrics["winning_trades"] / self.metrics["total_trades"]

        # Profit factor
        total_wins = sum(t.pnl for t in winning_trades)
        total_losses = abs(sum(t.pnl for t in losing_trades))

        if total_losses > 0:
            self.metrics["profit_factor"] = total_wins / total_losses

        # Sharpe ratio (simplified)
        returns = [t.pnl_pct for t in self.trade_outcomes]
        if len(returns) > 1:
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            std_dev = variance ** 0.5

            if std_dev > 0:
                self.metrics["sharpe_ratio"] = mean_return / std_dev

    def get_agent_performance(self, agent_name: str) -> dict:
        """
        Get performance metrics for a specific agent.

        Returns:
            Dict with win_rate, avg_pnl, trade_count for this agent
        """

        # Find trades where this agent contributed
        agent_trades = [
            t for t in self.trade_outcomes
            if agent_name in t.contributing_agents
        ]

        if not agent_trades:
            return {
                "agent_name": agent_name,
                "trade_count": 0,
                "win_rate": 0.5,
                "avg_pnl": 0.0,
                "total_pnl": 0.0
            }

        winning_trades = [t for t in agent_trades if t.winning]

        return {
            "agent_name": agent_name,
            "trade_count": len(agent_trades),
            "win_rate": len(winning_trades) / len(agent_trades),
            "avg_pnl": sum(t.pnl for t in agent_trades) / len(agent_trades),
            "total_pnl": sum(t.pnl for t in agent_trades)
        }

    def get_strategy_performance(self, strategy_tag: str) -> dict:
        """
        Get performance metrics for a specific strategy pattern.

        Returns:
            Dict with win_rate, avg_pnl, trade_count for this strategy
        """

        # Find trades using this strategy
        strategy_trades = [
            t for t in self.trade_outcomes
            if strategy_tag in t.strategy_tags
        ]

        if not strategy_trades:
            return {
                "strategy_tag": strategy_tag,
                "trade_count": 0,
                "win_rate": 0.5,
                "avg_pnl": 0.0,
                "total_pnl": 0.0,
                "weight": 0.0
            }

        winning_trades = [t for t in strategy_trades if t.winning]

        win_rate = len(winning_trades) / len(strategy_trades)
        avg_pnl = sum(t.pnl for t in strategy_trades) / len(strategy_trades)

        # Calculate weight for strategy
        # Win rate > 50% → positive weight
        # Win rate < 50% → negative weight
        # Scaled by avg P&L
        weight = (win_rate - 0.5) * 2 * abs(avg_pnl)

        return {
            "strategy_tag": strategy_tag,
            "trade_count": len(strategy_trades),
            "win_rate": win_rate,
            "avg_pnl": avg_pnl,
            "total_pnl": sum(t.pnl for t in strategy_trades),
            "weight": weight
        }

    def get_all_strategy_weights(self) -> dict[str, float]:
        """
        Get weights for all discovered strategies.

        Positive weight → successful strategy (use more)
        Negative weight → unsuccessful strategy (avoid)

        Returns:
            Dict mapping strategy_tag → weight
        """

        # Find all unique strategy tags
        all_tags = set()
        for outcome in self.trade_outcomes:
            all_tags.update(outcome.strategy_tags)

        # Calculate weight for each
        weights = {}
        for tag in all_tags:
            perf = self.get_strategy_performance(tag)
            weights[tag] = perf["weight"]

        # Sort by weight (best first)
        weights = dict(sorted(weights.items(), key=lambda x: x[1], reverse=True))

        return weights

    def get_metrics(self) -> dict:
        """Get all performance metrics"""
        return self.metrics
