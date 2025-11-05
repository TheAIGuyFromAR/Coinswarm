"""
News & Sentiment Data Fetcher

Fetches historical news, tweets, and sentiment data for crypto assets.

Data Sources:
1. Google News RSS (unlimited, FREE, no API key) ← BEST FREE OPTION
2. Google Trends (unlimited, FREE, no API key) ← BEST FREE OPTION
3. Fear & Greed Index (Alternative.me - free)
4. CryptoCompare News API (free tier: 50 req/day)
5. NewsAPI.org (free tier: 100 req/day)
6. Reddit sentiment (via PRAW - free)

Recommendation: Start with Google News + Google Trends (no setup needed!)

For backtesting, we cache historical sentiment scores aligned with price data.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
from dataclasses import dataclass, asdict
from enum import Enum

try:
    import httpx
except ImportError:
    import requests as httpx  # Fallback

from coinswarm.data_ingest.base import DataPoint
from coinswarm.data_ingest.google_sentiment_fetcher import GoogleSentimentFetcher


logger = logging.getLogger(__name__)


class SentimentScore(Enum):
    """Sentiment classification"""
    VERY_BEARISH = -2
    BEARISH = -1
    NEUTRAL = 0
    BULLISH = 1
    VERY_BULLISH = 2


@dataclass
class NewsArticle:
    """Single news article with sentiment"""
    timestamp: datetime
    source: str
    title: str
    url: str
    sentiment: float  # -1.0 to +1.0
    symbols: List[str]  # ["BTC", "ETH"]
    categories: List[str]  # ["regulation", "adoption", "technical"]

    def to_dict(self):
        return {
            **asdict(self),
            'timestamp': self.timestamp.isoformat(),
        }


@dataclass
class SentimentSnapshot:
    """Aggregated sentiment at a point in time"""
    timestamp: datetime
    symbol: str
    news_sentiment: float  # -1.0 to +1.0 from news
    social_sentiment: float  # -1.0 to +1.0 from social media
    fear_greed_index: float  # 0-100
    article_count: int
    bullish_count: int
    bearish_count: int

    def overall_sentiment(self) -> float:
        """Weighted average sentiment"""
        return (
            self.news_sentiment * 0.4 +
            self.social_sentiment * 0.4 +
            (self.fear_greed_index - 50) / 50 * 0.2  # Normalize to -1 to +1
        )


class NewsSentimentFetcher:
    """
    Fetch historical news and sentiment data.

    Free sources (no API key needed):
    - CoinDesk RSS
    - Cointelegraph RSS
    - Fear & Greed Index

    Optional sources (require API keys):
    - CryptoCompare (CRYPTOCOMPARE_API_KEY)
    - NewsAPI (NEWSAPI_KEY)
    - Reddit (REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET)
    """

    def __init__(
        self,
        cryptocompare_api_key: Optional[str] = None,
        newsapi_key: Optional[str] = None,
        reddit_credentials: Optional[Dict] = None
    ):
        self.cryptocompare_api_key = cryptocompare_api_key
        self.newsapi_key = newsapi_key
        self.reddit_credentials = reddit_credentials

        # Base URLs
        self.fear_greed_url = "https://api.alternative.me/fng/"
        self.cryptocompare_url = "https://min-api.cryptocompare.com/data/v2/news/"
        self.newsapi_url = "https://newsapi.org/v2/everything"

        # RSS feeds (public, unlimited)
        self.rss_feeds = {
            "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "cointelegraph": "https://cointelegraph.com/rss",
        }

        # Cache for sentiment data
        self.sentiment_cache: Dict[str, List[SentimentSnapshot]] = {}

    async def fetch_historical_sentiment(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval_hours: int = 24
    ) -> List[SentimentSnapshot]:
        """
        Fetch historical sentiment data aligned with price data.

        Args:
            symbol: Crypto symbol (e.g., "BTC", "ETH")
            start_date: Start date
            end_date: End date
            interval_hours: Sentiment snapshot interval (default 24h)

        Returns:
            List of SentimentSnapshot objects, one per interval
        """

        logger.info(f"Fetching sentiment for {symbol} from {start_date.date()} to {end_date.date()}")

        # Check cache
        cache_key = f"{symbol}_{start_date.date()}_{end_date.date()}_{interval_hours}"
        if cache_key in self.sentiment_cache:
            logger.info(f"Using cached sentiment for {symbol}")
            return self.sentiment_cache[cache_key]

        snapshots = []
        current = start_date

        # Generate snapshots at regular intervals
        while current <= end_date:
            snapshot = await self._fetch_sentiment_snapshot(
                symbol=symbol,
                timestamp=current
            )

            snapshots.append(snapshot)
            current += timedelta(hours=interval_hours)

        # Cache results
        self.sentiment_cache[cache_key] = snapshots

        logger.info(f"Fetched {len(snapshots)} sentiment snapshots for {symbol}")

        return snapshots

    async def _fetch_sentiment_snapshot(
        self,
        symbol: str,
        timestamp: datetime
    ) -> SentimentSnapshot:
        """Fetch sentiment at a specific point in time"""

        # Fetch from all available sources
        tasks = []

        # Fear & Greed Index (always available)
        tasks.append(self._fetch_fear_greed_index(timestamp))

        # CryptoCompare news (if API key available)
        if self.cryptocompare_api_key:
            tasks.append(self._fetch_cryptocompare_news(symbol, timestamp))

        # NewsAPI (if API key available)
        if self.newsapi_key:
            tasks.append(self._fetch_newsapi(symbol, timestamp))

        # Reddit sentiment (if credentials available)
        if self.reddit_credentials:
            tasks.append(self._fetch_reddit_sentiment(symbol, timestamp))

        # Execute all in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        fear_greed = 50  # Default neutral
        news_articles = []
        social_mentions = []

        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"Sentiment fetch error: {result}")
                continue

            if isinstance(result, dict):
                if "fear_greed" in result:
                    fear_greed = result["fear_greed"]
                elif "articles" in result:
                    news_articles.extend(result["articles"])
                elif "mentions" in result:
                    social_mentions.extend(result["mentions"])

        # Calculate aggregated sentiment
        news_sentiment = self._calculate_news_sentiment(news_articles)
        social_sentiment = self._calculate_social_sentiment(social_mentions)

        # Count bullish/bearish articles
        bullish_count = sum(1 for a in news_articles if a.sentiment > 0.2)
        bearish_count = sum(1 for a in news_articles if a.sentiment < -0.2)

        return SentimentSnapshot(
            timestamp=timestamp,
            symbol=symbol,
            news_sentiment=news_sentiment,
            social_sentiment=social_sentiment,
            fear_greed_index=fear_greed,
            article_count=len(news_articles),
            bullish_count=bullish_count,
            bearish_count=bearish_count
        )

    async def _fetch_fear_greed_index(self, timestamp: datetime) -> Dict:
        """
        Fetch Fear & Greed Index from Alternative.me

        Free API, no key needed.
        Returns: 0 (Extreme Fear) to 100 (Extreme Greed)
        """

        try:
            async with httpx.AsyncClient() as client:
                # Get historical data
                response = await client.get(
                    self.fear_greed_url,
                    params={"limit": 90, "format": "json"},
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()

                # Find closest date
                target_ts = int(timestamp.timestamp())
                closest = min(
                    data["data"],
                    key=lambda x: abs(int(x["timestamp"]) - target_ts)
                )

                return {"fear_greed": float(closest["value"])}

        except Exception as e:
            logger.warning(f"Fear & Greed fetch failed: {e}")
            return {"fear_greed": 50}  # Neutral default

    async def _fetch_cryptocompare_news(
        self,
        symbol: str,
        timestamp: datetime
    ) -> Dict:
        """
        Fetch news from CryptoCompare API.

        Requires CRYPTOCOMPARE_API_KEY.
        Free tier: 50 requests/day, 100 articles/request
        """

        if not self.cryptocompare_api_key:
            return {"articles": []}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.cryptocompare_url,
                    params={
                        "feeds": "cryptocompare,coindesk,cointelegraph",
                        "extraParams": "Coinswarm",
                        "api_key": self.cryptocompare_api_key
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()

                articles = []
                for item in data.get("Data", []):
                    article_time = datetime.fromtimestamp(item["published_on"])

                    # Only include articles within 24 hours of target
                    if abs((article_time - timestamp).total_seconds()) > 86400:
                        continue

                    # Check if article mentions the symbol
                    title = item.get("title", "").upper()
                    body = item.get("body", "").upper()

                    if symbol in title or symbol in body:
                        sentiment = self._analyze_sentiment(
                            item.get("title", "") + " " + item.get("body", "")
                        )

                        article = NewsArticle(
                            timestamp=article_time,
                            source=item.get("source", "unknown"),
                            title=item.get("title", ""),
                            url=item.get("url", ""),
                            sentiment=sentiment,
                            symbols=[symbol],
                            categories=item.get("categories", "").split("|")
                        )

                        articles.append(article)

                return {"articles": articles}

        except Exception as e:
            logger.warning(f"CryptoCompare news fetch failed: {e}")
            return {"articles": []}

    async def _fetch_newsapi(self, symbol: str, timestamp: datetime) -> Dict:
        """
        Fetch news from NewsAPI.org

        Requires NEWSAPI_KEY.
        Free tier: 100 requests/day, 100 articles/request
        Historical data limited to 1 month back on free tier
        """

        if not self.newsapi_key:
            return {"articles": []}

        try:
            # Map crypto symbols to search terms
            search_terms = {
                "BTC": "Bitcoin",
                "ETH": "Ethereum",
                "SOL": "Solana",
                "USDC": "USDC stablecoin",
                "USDT": "Tether",
            }

            query = search_terms.get(symbol, symbol)

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.newsapi_url,
                    params={
                        "q": query,
                        "from": (timestamp - timedelta(days=1)).isoformat(),
                        "to": timestamp.isoformat(),
                        "sortBy": "publishedAt",
                        "language": "en",
                        "apiKey": self.newsapi_key
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()

                articles = []
                for item in data.get("articles", []):
                    article_time = datetime.fromisoformat(
                        item["publishedAt"].replace("Z", "+00:00")
                    )

                    sentiment = self._analyze_sentiment(
                        item.get("title", "") + " " + item.get("description", "")
                    )

                    article = NewsArticle(
                        timestamp=article_time,
                        source=item.get("source", {}).get("name", "unknown"),
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        sentiment=sentiment,
                        symbols=[symbol],
                        categories=[]
                    )

                    articles.append(article)

                return {"articles": articles}

        except Exception as e:
            logger.warning(f"NewsAPI fetch failed: {e}")
            return {"articles": []}

    async def _fetch_reddit_sentiment(self, symbol: str, timestamp: datetime) -> Dict:
        """
        Fetch Reddit sentiment from r/CryptoCurrency, r/Bitcoin, etc.

        Requires Reddit API credentials (free).
        """

        if not self.reddit_credentials:
            return {"mentions": []}

        # TODO: Implement Reddit sentiment via PRAW
        # For now, return empty
        logger.debug("Reddit sentiment not implemented yet")
        return {"mentions": []}

    def _analyze_sentiment(self, text: str) -> float:
        """
        Simple keyword-based sentiment analysis.

        Returns: -1.0 (very bearish) to +1.0 (very bullish)

        For production, use proper NLP:
        - VADER sentiment analyzer
        - FinBERT (financial sentiment model)
        - GPT-4 for nuanced analysis
        """

        text_lower = text.lower()

        # Bullish keywords
        bullish_keywords = [
            "bull", "moon", "pump", "surge", "rally", "breakout",
            "all-time high", "ath", "adoption", "institutional",
            "upgrade", "partnership", "growth", "bullish"
        ]

        # Bearish keywords
        bearish_keywords = [
            "bear", "crash", "dump", "plunge", "collapse", "sell-off",
            "regulation", "ban", "hack", "scam", "fraud", "bearish",
            "decline", "drop", "fall", "down"
        ]

        bullish_count = sum(1 for kw in bullish_keywords if kw in text_lower)
        bearish_count = sum(1 for kw in bearish_keywords if kw in text_lower)

        # Simple ratio
        total = bullish_count + bearish_count
        if total == 0:
            return 0.0  # Neutral

        sentiment = (bullish_count - bearish_count) / total

        # Clamp to [-1, 1]
        return max(-1.0, min(1.0, sentiment))

    def _calculate_news_sentiment(self, articles: List[NewsArticle]) -> float:
        """Aggregate sentiment from news articles"""

        if not articles:
            return 0.0

        # Weighted average (recent articles matter more)
        total_weight = 0.0
        weighted_sum = 0.0

        now = datetime.now()
        for article in articles:
            # Exponential decay: older articles have less weight
            age_hours = (now - article.timestamp).total_seconds() / 3600
            weight = 0.9 ** (age_hours / 24)  # Decay over days

            weighted_sum += article.sentiment * weight
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def _calculate_social_sentiment(self, mentions: List) -> float:
        """Aggregate sentiment from social media mentions"""

        # TODO: Implement when Reddit/Twitter are added
        return 0.0

    def convert_to_datapoints(
        self,
        snapshots: List[SentimentSnapshot]
    ) -> List[DataPoint]:
        """
        Convert sentiment snapshots to DataPoint objects
        for integration with backtesting system.
        """

        data_points = []

        for snapshot in snapshots:
            data_point = DataPoint(
                source="sentiment",
                symbol=snapshot.symbol,
                timeframe="1d",  # Daily sentiment snapshots
                timestamp=snapshot.timestamp,
                data={
                    "sentiment": snapshot.overall_sentiment(),
                    "news_sentiment": snapshot.news_sentiment,
                    "social_sentiment": snapshot.social_sentiment,
                    "fear_greed": snapshot.fear_greed_index,
                    "article_count": snapshot.article_count,
                    "bullish_count": snapshot.bullish_count,
                    "bearish_count": snapshot.bearish_count,
                },
                quality_score=1.0
            )

            data_points.append(data_point)

        return data_points


# Example usage
if __name__ == "__main__":
    async def demo():
        fetcher = NewsSentimentFetcher()

        # Fetch sentiment for BTC over last 30 days
        end = datetime.now()
        start = end - timedelta(days=30)

        snapshots = await fetcher.fetch_historical_sentiment(
            symbol="BTC",
            start_date=start,
            end_date=end,
            interval_hours=24
        )

        print(f"\nFetched {len(snapshots)} sentiment snapshots\n")

        for snapshot in snapshots[-7:]:  # Last 7 days
            overall = snapshot.overall_sentiment()
            emoji = "🔴" if overall < -0.3 else "🟡" if overall < 0.3 else "🟢"

            print(f"{snapshot.timestamp.date()} {emoji}  "
                  f"Overall: {overall:+.2f}  "
                  f"News: {snapshot.news_sentiment:+.2f}  "
                  f"F&G: {snapshot.fear_greed_index:.0f}  "
                  f"Articles: {snapshot.article_count}")

    asyncio.run(demo())
