"""
Agent Swarm for Trading

Multiple specialized agents working together:
- Each agent has a specific strategy
- Agents vote independently in parallel
- Committee aggregates votes using weighted confidence
- Risk agent can veto dangerous trades
- Research agent spawns dozens of parallel news crawlers

Inspired by 17000% return swarm in tradfi.
"""

from coinswarm.agents.base_agent import BaseAgent, AgentVote
from coinswarm.agents.committee import AgentCommittee, CommitteeDecision
from coinswarm.agents.trend_agent import TrendFollowingAgent
from coinswarm.agents.risk_agent import RiskManagementAgent
from coinswarm.agents.research_agent import ResearchAgent, NewsSource, NewsSentiment

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
]
