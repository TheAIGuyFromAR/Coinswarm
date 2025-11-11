"""
Academic Research Agent

Researches documented trading strategies from academic sources:
- Academic papers (arXiv, SSRN, journals)
- Trading books and textbooks
- Quantitative finance research
- Crypto-specific research

Extracts proven strategies and converts them into testable patterns.
"""

import asyncio
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta

from coinswarm.data_ingest.base import DataPoint
from coinswarm.agents.base_agent import BaseAgent, AgentVote


logger = logging.getLogger(__name__)


@dataclass
class AcademicSource:
    """Academic source configuration"""
    name: str
    url_template: str
    query_type: str  # "api", "scrape", "database"
    credibility: float  # 0.0-1.0
    enabled: bool = True


@dataclass
class ResearchStrategy:
    """Strategy discovered from academic research"""
    source: str  # Paper title or source
    author: str
    year: int
    strategy_name: str
    description: str
    pattern: Dict  # Strategy parameters
    backtested_sharpe: Optional[float]  # Sharpe ratio from paper
    backtested_return: Optional[float]  # Annual return from paper
    asset_classes: List[str]  # ["crypto", "equities", "forex", etc.]
    url: str


class AcademicResearchAgent(BaseAgent):
    """
    Academic research agent for discovering proven strategies.

    Process:
    1. Query academic databases for trading strategies
    2. Parse papers to extract strategy descriptions
    3. Convert to testable patterns
    4. Mark for sandbox testing
    5. If successful, add to production strategy pool

    Sources:
    - arXiv (quantitative finance section)
    - SSRN (Social Science Research Network)
    - Google Scholar
    - Academic journals (Journal of Finance, etc.)
    - Crypto research (Messari, CoinMetrics research)
    """

    def __init__(
        self,
        name: str = "AcademicResearcher",
        weight: float = 0.0,  # Doesn't vote on trades
        sources: Optional[List[AcademicSource]] = None
    ):
        super().__init__(name, weight)

        # Academic sources
        self.sources = sources or self._default_sources()

        # Discovered strategies (not yet tested)
        self.discovered_strategies: List[ResearchStrategy] = []

        # Cache
        self.cache: Dict[str, List[ResearchStrategy]] = {}
        self.cache_ttl = timedelta(days=7)  # Cache for 1 week
        self.last_research_time = datetime.now()

    def _default_sources(self) -> List[AcademicSource]:
        """Default academic sources"""
        return [
            # Quantitative finance papers
            AcademicSource(
                "arXiv Quant Finance",
                "https://arxiv.org/search/?query={query}&searchtype=all&source=header&in_q-fin.TR=1",
                "api",
                0.9
            ),

            # Social science research
            AcademicSource(
                "SSRN",
                "https://papers.ssrn.com/sol3/results.cfm?txtWords={query}",
                "scrape",
                0.85
            ),

            # Google Scholar
            AcademicSource(
                "Google Scholar",
                "https://scholar.google.com/scholar?q={query}+trading+strategy",
                "scrape",
                0.8
            ),

            # Crypto-specific research
            AcademicSource(
                "Messari Research",
                "https://messari.io/research?search={query}",
                "api",
                0.85
            ),

            AcademicSource(
                "CoinMetrics Research",
                "https://coinmetrics.io/research/?search={query}",
                "api",
                0.85
            ),

            # Trading strategy databases
            AcademicSource(
                "QuantConnect Strategies",
                "https://www.quantconnect.com/forum/search?term={query}",
                "scrape",
                0.7
            ),

            AcademicSource(
                "Quantpedia",
                "https://quantpedia.com/strategies/?s={query}",
                "scrape",
                0.8
            ),
        ]

    async def analyze(
        self,
        tick: DataPoint,
        position: Optional[Dict],
        market_context: Dict
    ) -> AgentVote:
        """
        Academic researcher doesn't vote on new trades.
        Returns neutral HOLD vote.
        """
        return AgentVote(
            agent_name=self.name,
            action="HOLD",
            confidence=0.5,
            size=0.0,
            reason="Academic researcher does not vote on new trades"
        )

    async def research_strategies(self, query: str = "cryptocurrency trading") -> List[ResearchStrategy]:
        """
        Research academic strategies.

        Args:
            query: Research query (e.g., "momentum trading", "mean reversion")

        Returns:
            List of discovered strategies
        """

        # Check cache
        if query in self.cache:
            cached_time, cached_strategies = self.cache[query]
            if datetime.now() - cached_time < self.cache_ttl:
                logger.debug(f"Using cached academic research for '{query}'")
                return cached_strategies

        logger.info(f"Researching academic strategies for '{query}'...")
        start_time = datetime.now()

        # Query all sources in parallel
        tasks = [
            self._query_source(source, query)
            for source in self.sources
            if source.enabled
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results
        strategies = []
        for result in results:
            if isinstance(result, list):
                strategies.extend(result)

        # Store in cache
        self.cache[query] = (datetime.now(), strategies)

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Discovered {len(strategies)} strategies from "
            f"{len(self.sources)} sources in {duration:.1f}s"
        )

        # Store discovered strategies
        self.discovered_strategies.extend(strategies)

        return strategies

    async def _query_source(
        self,
        source: AcademicSource,
        query: str
    ) -> List[ResearchStrategy]:
        """
        Query a single academic source.

        In production, this would:
        1. Make HTTP request to source
        2. Parse results (JSON, HTML, etc.)
        3. Extract strategy descriptions
        4. Convert to ResearchStrategy objects

        For now, returns mock data.
        """

        try:
            # Placeholder: In production, use httpx or aiohttp
            await asyncio.sleep(0.2)  # Simulate HTTP request

            # Mock strategies (in production, parse actual papers)
            if "momentum" in query.lower():
                return [
                    ResearchStrategy(
                        source=f"Mock paper from {source.name}",
                        author="Jegadeesh & Titman",
                        year=1993,
                        strategy_name="Momentum Trading",
                        description="Buy past winners, sell past losers",
                        pattern={
                            "type": "momentum",
                            "lookback_period": 12,
                            "holding_period": 3,
                            "top_percentile": 10
                        },
                        backtested_sharpe=1.2,
                        backtested_return=0.18,
                        asset_classes=["equities", "crypto"],
                        url=source.url_template.format(query=query)
                    )
                ]

            elif "mean reversion" in query.lower():
                return [
                    ResearchStrategy(
                        source=f"Mock paper from {source.name}",
                        author="DeBondt & Thaler",
                        year=1985,
                        strategy_name="Mean Reversion",
                        description="Contrarian strategy: buy losers, sell winners",
                        pattern={
                            "type": "mean_reversion",
                            "lookback_period": 36,
                            "holding_period": 36,
                            "extreme_threshold": 2.0
                        },
                        backtested_sharpe=0.8,
                        backtested_return=0.25,
                        asset_classes=["equities", "crypto"],
                        url=source.url_template.format(query=query)
                    )
                ]

            else:
                # Generic strategy
                return [
                    ResearchStrategy(
                        source=f"Mock paper from {source.name}",
                        author="Mock Author",
                        year=2023,
                        strategy_name="Generic Strategy",
                        description="Placeholder strategy from academic research",
                        pattern={
                            "type": "generic",
                            "parameter_1": 1.0,
                            "parameter_2": 2.0
                        },
                        backtested_sharpe=None,
                        backtested_return=None,
                        asset_classes=["crypto"],
                        url=source.url_template.format(query=query)
                    )
                ]

        except Exception as e:
            logger.error(f"Error querying {source.name}: {e}")
            return []

    def get_top_strategies(self, n: int = 10) -> List[ResearchStrategy]:
        """
        Get top N strategies by Sharpe ratio.

        Returns:
            List of strategies sorted by Sharpe ratio
        """

        # Filter strategies with Sharpe ratio
        with_sharpe = [
            s for s in self.discovered_strategies
            if s.backtested_sharpe is not None
        ]

        # Sort by Sharpe ratio
        sorted_strategies = sorted(
            with_sharpe,
            key=lambda s: s.backtested_sharpe,
            reverse=True
        )

        return sorted_strategies[:n]

    def convert_to_testable_pattern(self, strategy: ResearchStrategy) -> Dict:
        """
        Convert academic strategy to testable pattern.

        This adapts the strategy description to our trading system.
        """

        # Base pattern from research
        pattern = strategy.pattern.copy()

        # Add metadata
        pattern["source"] = "academic"
        pattern["paper_title"] = strategy.source
        pattern["author"] = strategy.author
        pattern["year"] = strategy.year
        pattern["original_sharpe"] = strategy.backtested_sharpe
        pattern["original_return"] = strategy.backtested_return

        # Adapt to crypto timeframes (academic papers often use monthly data)
        if "lookback_period" in pattern:
            # Convert months to minutes for crypto (assume 1 month = ~43,200 minutes)
            pattern["lookback_minutes"] = pattern["lookback_period"] * 43200
            pattern["lookback_candles"] = pattern["lookback_period"] * 30  # 30 days/month

        return pattern

    def get_research_summary(self) -> Dict:
        """Get summary of academic research"""

        return {
            "total_strategies": len(self.discovered_strategies),
            "sources_queried": len(self.sources),
            "strategies_with_sharpe": len([
                s for s in self.discovered_strategies
                if s.backtested_sharpe is not None
            ]),
            "avg_sharpe": sum(
                s.backtested_sharpe for s in self.discovered_strategies
                if s.backtested_sharpe is not None
            ) / len([
                s for s in self.discovered_strategies
                if s.backtested_sharpe is not None
            ]) if self.discovered_strategies else 0.0,
            "last_research_time": self.last_research_time.isoformat()
        }
