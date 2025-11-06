"""
Research Agent - Spawns Parallel News Crawlers

This agent doesn't analyze markets directly. Instead, it:
- Spawns dozens of crawler sub-agents in parallel
- Each crawler targets a different news source
- Aggregates sentiment from all sources
- Votes based on overall sentiment

Example: BTC news research spawns 20 crawlers:
- CoinDesk, CoinTelegraph, Bloomberg, Reuters, etc.
- All run in parallel (concurrent HTTP requests)
- Results aggregated in ~2-3 seconds
- Vote weighted by source credibility
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
class NewsSource:
    """News source configuration"""
    name: str
    url_template: str  # e.g., "https://api.coindesk.com/v1/search?q={symbol}"
    credibility: float  # 0.0-1.0 (higher = more trusted)
    enabled: bool = True


@dataclass
class NewsSentiment:
    """Sentiment from a news source"""
    source: str
    sentiment: float  # -1.0 (very negative) to +1.0 (very positive)
    confidence: float  # 0.0-1.0
    headline: str
    url: str
    timestamp: datetime


class ResearchAgent(BaseAgent):
    """
    Research agent that spawns parallel news crawlers.

    Architecture:
    1. Receives market tick
    2. Spawns crawler for each news source (in parallel)
    3. Each crawler fetches and analyzes sentiment
    4. Aggregates sentiment across all sources
    5. Votes BUY/SELL/HOLD based on sentiment

    This is the "dozens of crawlers with different targets" approach.
    """

    def __init__(
        self,
        name: str = "ResearchAgent",
        weight: float = 1.5,
        sources: Optional[List[NewsSource]] = None
    ):
        super().__init__(name, weight)

        # News sources (in production, load from config)
        self.sources = sources or self._default_sources()

        # Cache sentiment (avoid re-crawling same news)
        self.sentiment_cache: Dict[str, List[NewsSentiment]] = {}
        self.cache_ttl = timedelta(minutes=5)  # Cache for 5 minutes

    def _default_sources(self) -> List[NewsSource]:
        """Default news sources for crypto"""
        return [
            # Major crypto news
            NewsSource("CoinDesk", "https://api.coindesk.com/search?q={symbol}", 0.9),
            NewsSource("CoinTelegraph", "https://cointelegraph.com/api/search?q={symbol}", 0.8),
            NewsSource("CryptoSlate", "https://cryptoslate.com/api/search?q={symbol}", 0.8),
            NewsSource("Decrypt", "https://decrypt.co/api/search?q={symbol}", 0.8),

            # Traditional finance (for BTC/ETH)
            NewsSource("Bloomberg", "https://bloomberg.com/api/search?q={symbol}", 0.95),
            NewsSource("Reuters", "https://reuters.com/api/search?q={symbol}", 0.95),
            NewsSource("CNBC", "https://cnbc.com/api/search?q={symbol}", 0.85),
            NewsSource("WSJ", "https://wsj.com/api/search?q={symbol}", 0.9),

            # Social sentiment
            NewsSource("Reddit", "https://reddit.com/r/cryptocurrency/search?q={symbol}", 0.6),
            NewsSource("Twitter", "https://api.twitter.com/search?q={symbol}", 0.7),

            # Blockchain data
            NewsSource("CoinMetrics", "https://coinmetrics.io/api/v1/{symbol}", 0.85),
            NewsSource("Glassnode", "https://glassnode.com/api/{symbol}", 0.85),

            # Add more sources as needed...
        ]

    async def analyze(
        self,
        tick: DataPoint,
        position: Optional[Dict],
        market_context: Dict
    ) -> AgentVote:
        """
        Spawn parallel news crawlers and aggregate sentiment.

        Process:
        1. Check cache for recent sentiment
        2. If cache miss, spawn crawlers in parallel
        3. Aggregate sentiment across all sources
        4. Return vote based on sentiment
        """

        symbol = tick.symbol

        # Check cache first
        cached_sentiment = self._get_cached_sentiment(symbol)
        if cached_sentiment:
            logger.debug(f"Using cached sentiment for {symbol}")
            sentiments = cached_sentiment
        else:
            # Cache miss - spawn parallel crawlers
            logger.info(f"Spawning {len(self.sources)} news crawlers for {symbol}...")
            start_time = datetime.now()

            # Spawn all crawlers in parallel
            sentiments = await self._spawn_crawlers(symbol)

            # Cache results
            self.sentiment_cache[symbol] = sentiments

            duration = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"Crawled {len(sentiments)} sources in {duration:.1f}s "
                f"({len(sentiments)/duration:.1f} sources/sec)"
            )

        # Aggregate sentiment
        vote = self._aggregate_sentiment(symbol, sentiments, tick)

        return vote

    async def _spawn_crawlers(self, symbol: str) -> List[NewsSentiment]:
        """
        Spawn all news crawlers in parallel.

        This is the key to fast research:
        - 20 sources × 2s each = 40s sequential
        - 20 sources in parallel = 2s total ✅
        """

        # Create crawler tasks (one per source)
        tasks = [
            self._crawl_source(source, symbol)
            for source in self.sources
            if source.enabled
        ]

        # Run all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out errors and None values
        sentiments = [
            r for r in results
            if isinstance(r, NewsSentiment)
        ]

        return sentiments

    async def _crawl_source(
        self,
        source: NewsSource,
        symbol: str
    ) -> Optional[NewsSentiment]:
        """
        Crawl a single news source.

        In production, this would:
        1. Make HTTP request to news API
        2. Parse response
        3. Analyze sentiment (using NLP or simple keyword matching)
        4. Return NewsSentiment

        For now, this is a placeholder.
        """

        try:
            # Placeholder: In production, use httpx or aiohttp
            # import httpx
            # async with httpx.AsyncClient() as client:
            #     url = source.url_template.format(symbol=symbol)
            #     response = await client.get(url, timeout=5)
            #     data = response.json()
            #     sentiment = self._analyze_sentiment(data)

            # For now, return mock sentiment
            await asyncio.sleep(0.1)  # Simulate HTTP request

            # Mock sentiment (in production, analyze actual news)
            sentiment = NewsSentiment(
                source=source.name,
                sentiment=0.0,  # Neutral (placeholder)
                confidence=0.5,
                headline=f"Mock headline for {symbol}",
                url=source.url_template.format(symbol=symbol),
                timestamp=datetime.now()
            )

            return sentiment

        except Exception as e:
            logger.error(f"Error crawling {source.name}: {e}")
            return None

    def _aggregate_sentiment(
        self,
        symbol: str,
        sentiments: List[NewsSentiment],
        tick: DataPoint
    ) -> AgentVote:
        """
        Aggregate sentiment from all sources into a vote.

        Algorithm:
        - Weight each source by credibility
        - Calculate weighted average sentiment
        - Map sentiment to BUY/SELL/HOLD
        """

        if not sentiments:
            return AgentVote(
                agent_name=self.name,
                action="HOLD",
                confidence=0.5,
                size=0.0,
                reason="No news data available"
            )

        # Calculate weighted sentiment
        weighted_sum = 0.0
        total_weight = 0.0

        for sentiment in sentiments:
            # Get source credibility
            source = next((s for s in self.sources if s.name == sentiment.source), None)
            credibility = source.credibility if source else 0.5

            # Weight = credibility × confidence
            weight = credibility * sentiment.confidence

            weighted_sum += sentiment.sentiment * weight
            total_weight += weight

        # Aggregate sentiment (-1.0 to +1.0)
        avg_sentiment = weighted_sum / total_weight if total_weight > 0 else 0.0

        # Map sentiment to action
        if avg_sentiment > 0.3:
            # Positive sentiment → BUY
            action = "BUY"
            confidence = min(0.9, avg_sentiment)
            size = 0.01 * confidence  # Scale size by confidence
            reason = f"Positive news sentiment: {avg_sentiment:.2f} from {len(sentiments)} sources"

        elif avg_sentiment < -0.3:
            # Negative sentiment → SELL
            action = "SELL"
            confidence = min(0.9, abs(avg_sentiment))
            size = 0.01 * confidence
            reason = f"Negative news sentiment: {avg_sentiment:.2f} from {len(sentiments)} sources"

        else:
            # Neutral sentiment → HOLD
            action = "HOLD"
            confidence = 0.6
            size = 0.0
            reason = f"Neutral news sentiment: {avg_sentiment:.2f} from {len(sentiments)} sources"

        return AgentVote(
            agent_name=self.name,
            action=action,
            confidence=confidence,
            size=size,
            reason=reason
        )

    def _get_cached_sentiment(self, symbol: str) -> Optional[List[NewsSentiment]]:
        """Get cached sentiment if available and fresh"""

        if symbol not in self.sentiment_cache:
            return None

        sentiments = self.sentiment_cache[symbol]

        # Check if cache is still fresh
        if sentiments and (datetime.now() - sentiments[0].timestamp) < self.cache_ttl:
            return sentiments

        # Cache expired
        return None

    def _analyze_sentiment(self, news_data: dict) -> float:
        """
        Analyze sentiment from news data.

        In production, this would use:
        - NLP sentiment analysis (VADER, TextBlob, etc.)
        - Fine-tuned transformer models (FinBERT, etc.)
        - Keyword matching
        - Social media engagement metrics

        Returns:
            Sentiment score (-1.0 to +1.0)
        """

        # Placeholder: Simple keyword matching
        text = news_data.get("text", "").lower()

        positive_keywords = ["bullish", "surge", "rally", "breakout", "gains", "positive"]
        negative_keywords = ["bearish", "crash", "decline", "drop", "losses", "negative"]

        positive_count = sum(1 for word in positive_keywords if word in text)
        negative_count = sum(1 for word in negative_keywords if word in text)

        if positive_count + negative_count == 0:
            return 0.0  # Neutral

        sentiment = (positive_count - negative_count) / (positive_count + negative_count)

        return sentiment
