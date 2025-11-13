"""
Google-Based Sentiment Fetcher

Uses Google services for sentiment data:
1. Google News RSS (FREE, no API key needed)
2. Google Trends (FREE, shows search interest)
3. Google Custom Search API (FREE tier: 100 queries/day)

Advantages:
- Free and unlimited (RSS)
- No API key needed for basic usage
- Comprehensive news coverage
- Real-time trends data
"""

import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta

try:
    import httpx
except ImportError:
    import requests as httpx



logger = logging.getLogger(__name__)


@dataclass
class GoogleNewsArticle:
    """Single news article from Google News"""
    timestamp: datetime
    title: str
    url: str
    source: str
    snippet: str
    sentiment: float  # -1.0 to +1.0


class GoogleSentimentFetcher:
    """
    Fetch sentiment data using Google services.

    Sources:
    1. Google News RSS - FREE, unlimited
    2. Google Trends - FREE, shows search interest
    3. Google Custom Search API - FREE tier (100/day)
    """

    def __init__(self, google_api_key: str | None = None, search_engine_id: str | None = None):
        """
        Initialize Google sentiment fetcher.

        Args:
            google_api_key: Google Custom Search API key (optional)
            search_engine_id: Custom Search Engine ID (optional)

        Get API key (optional):
            https://developers.google.com/custom-search/v1/introduction
        """
        self.google_api_key = google_api_key
        self.search_engine_id = search_engine_id

        # Google News RSS feed URLs
        self.news_rss_urls = {
            "BTC": "https://news.google.com/rss/search?q=bitcoin&hl=en-US&gl=US&ceid=US:en",
            "ETH": "https://news.google.com/rss/search?q=ethereum&hl=en-US&gl=US&ceid=US:en",
            "SOL": "https://news.google.com/rss/search?q=solana&hl=en-US&gl=US&ceid=US:en",
            "crypto": "https://news.google.com/rss/search?q=cryptocurrency&hl=en-US&gl=US&ceid=US:en"
        }

        # Sentiment keywords
        self.bullish_keywords = [
            "surge", "rally", "bull", "moon", "pump", "breakout",
            "all-time high", "ath", "record", "soar", "jump",
            "adoption", "institutional", "breakthrough", "upgrade",
            "partnership", "integration", "growth", "bullish",
            "optimistic", "positive", "gain", "rise", "climb"
        ]

        self.bearish_keywords = [
            "crash", "plunge", "dump", "bear", "collapse", "tank",
            "decline", "drop", "fall", "plummet", "sink",
            "regulation", "ban", "lawsuit", "fraud", "hack",
            "scam", "ponzi", "bubble", "warning", "concern",
            "fear", "bearish", "pessimistic", "negative", "loss"
        ]

    async def fetch_google_news_sentiment(
        self,
        symbol: str,
        hours_back: int = 24
    ) -> list[GoogleNewsArticle]:
        """
        Fetch recent news from Google News RSS.

        Args:
            symbol: Crypto symbol (BTC, ETH, SOL)
            hours_back: How many hours of news to fetch

        Returns:
            List of articles with sentiment scores
        """

        logger.info(f"Fetching Google News for {symbol}...")

        rss_url = self.news_rss_urls.get(symbol)
        if not rss_url:
            logger.warning(f"No RSS feed configured for {symbol}")
            return []

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(rss_url, timeout=10.0)
                response.raise_for_status()

                # Parse RSS XML
                root = ET.fromstring(response.content)

                articles = []
                cutoff_time = datetime.now() - timedelta(hours=hours_back)

                # Parse RSS items
                for item in root.findall(".//item"):
                    try:
                        title_elem = item.find("title")
                        link_elem = item.find("link")
                        pub_date_elem = item.find("pubDate")
                        source_elem = item.find("source")
                        description_elem = item.find("description")

                        if title_elem is None or link_elem is None:
                            continue

                        title = title_elem.text
                        url = link_elem.text
                        source = source_elem.text if source_elem is not None else "Unknown"
                        snippet = description_elem.text if description_elem is not None else ""

                        # Parse date (RFC 822 format)
                        pub_date = None
                        if pub_date_elem is not None:
                            pub_date = self._parse_rfc822_date(pub_date_elem.text)

                        # Skip old articles
                        if pub_date and pub_date < cutoff_time:
                            continue

                        # Analyze sentiment
                        sentiment = self._analyze_sentiment(title + " " + snippet)

                        article = GoogleNewsArticle(
                            timestamp=pub_date or datetime.now(),
                            title=title,
                            url=url,
                            source=source,
                            snippet=snippet,
                            sentiment=sentiment
                        )

                        articles.append(article)

                    except Exception as e:
                        logger.debug(f"Error parsing article: {e}")
                        continue

                logger.info(f"✓ Fetched {len(articles)} articles for {symbol} from Google News")

                return articles

        except Exception as e:
            logger.error(f"Error fetching Google News: {e}")
            return []

    async def fetch_google_search_sentiment(
        self,
        symbol: str,
        days_back: int = 7
    ) -> list[GoogleNewsArticle]:
        """
        Fetch articles using Google Custom Search API.

        Requires API key (free tier: 100 queries/day).

        Args:
            symbol: Crypto symbol
            days_back: How many days back to search

        Returns:
            List of articles with sentiment
        """

        if not self.google_api_key or not self.search_engine_id:
            logger.debug("Google Custom Search API not configured (optional)")
            return []

        logger.info(f"Searching Google for {symbol} articles...")

        # Map symbols to search queries
        search_queries = {
            "BTC": "Bitcoin cryptocurrency news",
            "ETH": "Ethereum cryptocurrency news",
            "SOL": "Solana cryptocurrency news"
        }

        query = search_queries.get(symbol, f"{symbol} cryptocurrency")

        try:
            async with httpx.AsyncClient() as client:
                # Date range
                end_date = datetime.now()
                end_date - timedelta(days=days_back)

                response = await client.get(
                    "https://www.googleapis.com/customsearch/v1",
                    params={
                        "key": self.google_api_key,
                        "cx": self.search_engine_id,
                        "q": query,
                        "dateRestrict": f"d{days_back}",  # Last N days
                        "num": 10,  # Max results per query
                        "sort": "date"
                    },
                    timeout=10.0
                )

                response.raise_for_status()
                data = response.json()

                articles = []

                for item in data.get("items", []):
                    title = item.get("title", "")
                    url = item.get("link", "")
                    snippet = item.get("snippet", "")

                    # Extract source from domain
                    source = self._extract_domain(url)

                    # Analyze sentiment
                    sentiment = self._analyze_sentiment(title + " " + snippet)

                    article = GoogleNewsArticle(
                        timestamp=datetime.now(),  # Custom Search doesn't provide dates
                        title=title,
                        url=url,
                        source=source,
                        snippet=snippet,
                        sentiment=sentiment
                    )

                    articles.append(article)

                logger.info(f"✓ Found {len(articles)} articles via Google Search")

                return articles

        except Exception as e:
            logger.error(f"Error using Google Custom Search: {e}")
            return []

    async def fetch_google_trends_score(
        self,
        symbol: str,
        days_back: int = 30
    ) -> dict[str, float]:
        """
        Fetch Google Trends interest over time.

        Uses pytrends library (unofficial Google Trends API).
        FREE, no API key needed.

        Args:
            symbol: Crypto symbol
            days_back: Days of trend data

        Returns:
            Dict with trend scores
        """

        try:
            from pytrends.request import TrendReq

            # Map symbols to search terms
            search_terms = {
                "BTC": "Bitcoin",
                "ETH": "Ethereum",
                "SOL": "Solana"
            }

            term = search_terms.get(symbol, symbol)

            # Initialize pytrends
            pytrends = TrendReq(hl='en-US', tz=360)

            # Build payload (last N days)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            timeframe = f"{start_date.strftime('%Y-%m-%d')} {end_date.strftime('%Y-%m-%d')}"

            pytrends.build_payload([term], timeframe=timeframe)

            # Get interest over time
            interest_df = pytrends.interest_over_time()

            if interest_df.empty:
                logger.warning(f"No Google Trends data for {term}")
                return {"trend_score": 50, "trend_direction": "neutral"}

            # Calculate trend metrics
            values = interest_df[term].values
            recent_avg = values[-7:].mean()  # Last week average
            overall_avg = values.mean()

            # Trend direction
            if recent_avg > overall_avg * 1.2:
                direction = "rising"
                score = min(100, recent_avg)
            elif recent_avg < overall_avg * 0.8:
                direction = "falling"
                score = max(0, recent_avg)
            else:
                direction = "neutral"
                score = recent_avg

            logger.info(f"✓ Google Trends for {term}: {score:.0f}/100 ({direction})")

            return {
                "trend_score": score,
                "trend_direction": direction,
                "recent_avg": recent_avg,
                "overall_avg": overall_avg
            }

        except ImportError:
            logger.warning("pytrends not installed. Run: pip install pytrends")
            return {"trend_score": 50, "trend_direction": "neutral"}
        except Exception as e:
            logger.error(f"Error fetching Google Trends: {e}")
            return {"trend_score": 50, "trend_direction": "neutral"}

    async def fetch_sentiment_snapshot(
        self,
        symbol: str,
        hours_back: int = 24
    ) -> dict:
        """
        Fetch comprehensive sentiment from all Google sources.

        Args:
            symbol: Crypto symbol
            hours_back: How many hours of data

        Returns:
            Dict with aggregated sentiment
        """

        logger.info(f"Fetching Google sentiment for {symbol}...")

        # Fetch from all sources in parallel
        tasks = [
            self.fetch_google_news_sentiment(symbol, hours_back),
            self.fetch_google_trends_score(symbol, days_back=30)
        ]

        # Add Custom Search if API key available
        if self.google_api_key:
            tasks.append(self.fetch_google_search_sentiment(symbol, days_back=7))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Parse results
        news_articles = []
        trends = {"trend_score": 50, "trend_direction": "neutral"}
        search_articles = []

        for result in results:
            if isinstance(result, Exception):
                logger.debug(f"Source error: {result}")
            elif isinstance(result, list):
                if all(isinstance(x, GoogleNewsArticle) for x in result):
                    if not news_articles:
                        news_articles = result
                    else:
                        search_articles = result
            elif isinstance(result, dict):
                trends = result

        # Calculate aggregated sentiment
        all_articles = news_articles + search_articles

        if all_articles:
            avg_sentiment = sum(a.sentiment for a in all_articles) / len(all_articles)
            bullish_count = sum(1 for a in all_articles if a.sentiment > 0.2)
            bearish_count = sum(1 for a in all_articles if a.sentiment < -0.2)
        else:
            avg_sentiment = 0.0
            bullish_count = 0
            bearish_count = 0

        # Normalize trend score to -1 to +1
        trend_sentiment = (trends["trend_score"] - 50) / 50

        # Weighted average
        if all_articles:
            overall_sentiment = avg_sentiment * 0.7 + trend_sentiment * 0.3
        else:
            overall_sentiment = trend_sentiment

        return {
            "symbol": symbol,
            "overall_sentiment": overall_sentiment,
            "news_sentiment": avg_sentiment,
            "trend_sentiment": trend_sentiment,
            "article_count": len(all_articles),
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "trend_score": trends["trend_score"],
            "trend_direction": trends["trend_direction"],
            "articles": all_articles[:10]  # Top 10 most recent
        }

    def _analyze_sentiment(self, text: str) -> float:
        """
        Analyze sentiment using keyword matching.

        Args:
            text: Text to analyze

        Returns:
            Sentiment score from -1.0 to +1.0
        """

        if not text:
            return 0.0

        text_lower = text.lower()

        # Count keyword matches
        bullish_count = sum(1 for kw in self.bullish_keywords if kw in text_lower)
        bearish_count = sum(1 for kw in self.bearish_keywords if kw in text_lower)

        # Calculate sentiment
        total = bullish_count + bearish_count
        if total == 0:
            return 0.0

        sentiment = (bullish_count - bearish_count) / total

        # Clamp to [-1, 1]
        return max(-1.0, min(1.0, sentiment))

    def _parse_rfc822_date(self, date_str: str) -> datetime | None:
        """Parse RFC 822 date format (used in RSS)"""

        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except Exception as e:
            logger.debug(f"Error parsing date: {date_str} - {e}")
            return None

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""

        try:
            match = re.search(r'https?://([^/]+)', url)
            if match:
                domain = match.group(1)
                # Remove www.
                domain = domain.replace("www.", "")
                return domain
            return "Unknown"
        except:
            return "Unknown"


# Example usage
if __name__ == "__main__":
    async def demo():
        print("\n" + "="*70)
        print("GOOGLE SENTIMENT DEMO")
        print("="*70 + "\n")

        print("Data Sources:")
        print("  ✅ Google News RSS (free, unlimited)")
        print("  ✅ Google Trends (free, unlimited)")
        print("  ⚠️  Google Custom Search (optional, 100 queries/day)")
        print()

        fetcher = GoogleSentimentFetcher()

        # Fetch sentiment for BTC
        print("Fetching sentiment for BTC from Google...\n")

        snapshot = await fetcher.fetch_sentiment_snapshot("BTC", hours_back=24)

        print("="*70)
        print(f"SENTIMENT SNAPSHOT: {snapshot['symbol']}")
        print("="*70)
        print(f"Overall Sentiment:  {snapshot['overall_sentiment']:+.2f}")
        print(f"News Sentiment:     {snapshot['news_sentiment']:+.2f}")
        print(f"Trend Sentiment:    {snapshot['trend_sentiment']:+.2f}")
        print(f"Article Count:      {snapshot['article_count']}")
        print(f"Bullish Articles:   {snapshot['bullish_count']}")
        print(f"Bearish Articles:   {snapshot['bearish_count']}")
        print(f"Google Trends:      {snapshot['trend_score']:.0f}/100 ({snapshot['trend_direction']})")
        print()

        # Show sample articles
        if snapshot['articles']:
            print("Recent Articles:")
            print("-"*70)
            for i, article in enumerate(snapshot['articles'][:5], 1):
                emoji = "🔴" if article.sentiment < -0.3 else "🟡" if article.sentiment < 0.3 else "🟢"
                print(f"{i}. {emoji} [{article.source}]")
                print(f"   {article.title}")
                print(f"   Sentiment: {article.sentiment:+.2f}")
                print()

        print("="*70)
        print("✅ DEMO COMPLETE")
        print("="*70)
        print()
        print("Advantages of Google:")
        print("  - Free and unlimited (RSS + Trends)")
        print("  - No API key needed for basic usage")
        print("  - Comprehensive news coverage")
        print("  - Real-time search interest data")
        print()
        print("Optional: Get Custom Search API key for more sources")
        print("  https://developers.google.com/custom-search/v1/introduction")
        print()

    asyncio.run(demo())
