"""
Agent Swarm for Trading

Self-learning evolutionary agent swarm with:
- Multiple specialized agents working in parallel
- Committee aggregates votes using weighted confidence
- Trade analysis agent tracks win/loss outcomes
- Strategy learning agent evolves new strategies (genetic algorithm)
- Academic research agent discovers proven strategies from papers
- Hedge agent manages stop losses, take profits, risk/reward ratios
- Research agent spawns dozens of parallel news crawlers

Evolutionary approach:
- Successful strategies get + weight
- Unsuccessful strategies get BIGGER - weight (die faster)
- Only best strategies survive
- New strategies bred from successful parents
- All strategies tested in sandbox first

Inspired by 17000% return swarm in tradfi.
"""

from coinswarm.agents.base_agent import BaseAgent, AgentVote
from coinswarm.agents.committee import AgentCommittee, CommitteeDecision
from coinswarm.agents.trend_agent import TrendFollowingAgent
from coinswarm.agents.risk_agent import RiskManagementAgent
from coinswarm.agents.research_agent import ResearchAgent, NewsSource, NewsSentiment
from coinswarm.agents.trade_analysis_agent import TradeAnalysisAgent, TradeOutcome
from coinswarm.agents.strategy_learning_agent import StrategyLearningAgent, Strategy
from coinswarm.agents.academic_research_agent import AcademicResearchAgent, ResearchStrategy
from coinswarm.agents.hedge_agent import HedgeAgent, RiskParameters, HedgeRecommendation

__all__ = [
    "BaseAgent",
    "AgentVote",
    "AgentCommittee",
    "CommitteeDecision",
    "TrendFollowingAgent",
    "RiskManagementAgent",
    "ResearchAgent",
    "NewsSource",
    "NewsSentiment",
    "TradeAnalysisAgent",
    "TradeOutcome",
    "StrategyLearningAgent",
    "Strategy",
    "AcademicResearchAgent",
    "ResearchStrategy",
    "HedgeAgent",
    "RiskParameters",
    "HedgeRecommendation",
]
