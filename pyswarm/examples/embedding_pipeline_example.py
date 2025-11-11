"""
Example: Time Period Embedding Pipeline

This demonstrates how to:
1. Create time period snapshots from your data
2. Generate embeddings and store in Vectorize
3. Query for similar historical periods in <10ms
4. Get timestamps and full metadata instantly

The key insight: Vectorize returns timestamps + metadata directly in the query result!
No additional KV lookup needed - it's all in one fast operation.
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict, Any


class EmbeddingPipeline:
    """
    Pipeline for creating and querying time period embeddings.

    This uses the TypeScript embedding worker via HTTP for fast AI/Vectorize operations.
    All timestamp lookups happen in <10ms via Vectorize metadata.
    """

    def __init__(self, embedding_worker_url: str):
        """
        Initialize pipeline with the embedding worker URL.

        Args:
            embedding_worker_url: URL of deployed embedding worker
                                 e.g., "https://pyswarm-embeddings.YOUR_SUBDOMAIN.workers.dev"
        """
        self.worker_url = embedding_worker_url.rstrip('/')

    async def create_time_snapshot(self,
                                   timestamp: int,
                                   news_summary: str,
                                   sentiment_score: float,
                                   technical_setup: str,
                                   social_summary: str = None,
                                   market_conditions: str = None,
                                   additional_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create and store a time period snapshot embedding.

        This generates an embedding and stores it in Vectorize with the timestamp as ID.
        The timestamp and ALL metadata are stored together for instant retrieval.

        Args:
            timestamp: Unix timestamp in seconds
            news_summary: Summary of key news from this period
            sentiment_score: Overall sentiment (-1 to 1)
            technical_setup: Description of technical indicators/patterns
            social_summary: Social media sentiment summary
            market_conditions: Overall market state
            additional_metadata: Any extra data you want to attach

        Returns:
            dict: Response with embedding ID, success status
        """
        # Build snapshot payload
        snapshot = {
            "timestamp": timestamp,
            "news_summary": news_summary,
            "sentiment_score": sentiment_score,
            "technical_setup": technical_setup,
            "store_in_vectorize": True
        }

        if social_summary:
            snapshot["social_summary"] = social_summary

        if market_conditions:
            snapshot["market_conditions"] = market_conditions

        if additional_metadata:
            snapshot["metadata"] = additional_metadata

        # Call embedding worker
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.worker_url}/embed/snapshot",
                json=snapshot
            ) as response:
                result = await response.json()

        return result

    async def find_similar_periods(self,
                                  current_timestamp: int,
                                  current_news: str,
                                  current_sentiment: float,
                                  current_technical: str,
                                  top_k: int = 10,
                                  min_similarity: float = 0.75,
                                  exclude_recent_days: int = 30) -> List[Dict[str, Any]]:
        """
        Find historical time periods similar to current conditions.

        This is a SINGLE QUERY to Vectorize that returns:
        - Similar period timestamps
        - Similarity scores
        - ALL metadata (news, sentiment, technical setup, etc.)

        Typical query time: 5-15 milliseconds

        Args:
            current_timestamp: Current time
            current_news: Current news summary
            current_sentiment: Current sentiment score
            current_technical: Current technical setup
            top_k: Number of similar periods to return
            min_similarity: Minimum similarity threshold (0-1)
            exclude_recent_days: Exclude periods within this many days

        Returns:
            list: Similar periods with timestamps and full context
        """
        # Build query payload
        query = {
            "current_snapshot": {
                "timestamp": current_timestamp,
                "news_summary": current_news,
                "sentiment_score": current_sentiment,
                "technical_setup": current_technical
            },
            "top_k": top_k,
            "min_similarity": min_similarity,
            "exclude_recent_days": exclude_recent_days
        }

        # Query for similar periods - ONE REQUEST, ALL DATA RETURNED
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.worker_url}/search/similar",
                json=query
            ) as response:
                result = await response.json()

        return result.get("similar_periods", [])

    async def batch_create_historical_snapshots(self,
                                               snapshots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create multiple historical snapshots in parallel.

        Use this to backfill historical data efficiently.

        Args:
            snapshots: List of snapshot dictionaries (see create_time_snapshot)

        Returns:
            list: Results for each snapshot
        """
        tasks = []
        for snapshot in snapshots:
            task = self.create_time_snapshot(
                timestamp=snapshot["timestamp"],
                news_summary=snapshot["news_summary"],
                sentiment_score=snapshot["sentiment_score"],
                technical_setup=snapshot["technical_setup"],
                social_summary=snapshot.get("social_summary"),
                market_conditions=snapshot.get("market_conditions"),
                additional_metadata=snapshot.get("metadata")
            )
            tasks.append(task)

        return await asyncio.gather(*tasks)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

async def main():
    """
    Example: Create historical snapshots and find similar periods
    """
    # Initialize pipeline (replace with your worker URL)
    pipeline = EmbeddingPipeline("https://pyswarm-embeddings.YOUR_SUBDOMAIN.workers.dev")

    # Example 1: Create a historical snapshot
    print("Creating historical snapshot...")

    past_snapshot = await pipeline.create_time_snapshot(
        timestamp=int(datetime(2024, 1, 15, 12, 0).timestamp()),
        news_summary="Bitcoin ETF approval drives major rally. Institutional inflows surge.",
        sentiment_score=0.82,
        technical_setup="Strong bullish momentum. RSI at 72, MACD crossover. Breaking resistance at $45k.",
        social_summary="Extremely bullish social sentiment across Twitter and Reddit",
        market_conditions="Bull market confirmed. High volume accumulation.",
        additional_metadata={
            "btc_price": 45000,
            "volume_24h": 35000000000,
            "market_phase": "bull_rally"
        }
    )

    print(f"✓ Stored snapshot: {past_snapshot['id']}")

    # Example 2: Create current snapshot and find similar periods
    print("\nFinding similar historical periods...")

    current_time = int(datetime.now().timestamp())

    similar_periods = await pipeline.find_similar_periods(
        current_timestamp=current_time,
        current_news="Market consolidating after recent gains. ETF volumes remain strong.",
        current_sentiment=0.65,
        current_technical="Bullish divergence forming on daily chart. Support holding at $42k.",
        top_k=5,
        min_similarity=0.75,
        exclude_recent_days=30
    )

    # Display results - ALL DATA RETURNED IN ONE QUERY (< 10ms typical)
    print(f"\nFound {len(similar_periods)} similar periods:")
    for i, period in enumerate(similar_periods, 1):
        timestamp = period['timestamp']
        date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M')
        similarity = period['similarity_score']

        print(f"\n{i}. {date} (similarity: {similarity:.3f})")
        print(f"   News: {period['news_summary'][:80]}...")
        print(f"   Sentiment: {period['sentiment_score']:.2f}")
        print(f"   Technical: {period['technical_setup'][:80]}...")

        # Access additional metadata if stored
        if 'metadata' in period:
            metadata = period['metadata']
            if 'btc_price' in metadata:
                print(f"   BTC Price: ${metadata['btc_price']:,}")

    # Example 3: Backfill multiple historical snapshots
    print("\n\nBackfilling historical data...")

    historical_snapshots = [
        {
            "timestamp": int(datetime(2024, 2, 1).timestamp()),
            "news_summary": "Regulatory clarity improves market sentiment",
            "sentiment_score": 0.55,
            "technical_setup": "Consolidation pattern forming",
            "metadata": {"market_phase": "accumulation"}
        },
        {
            "timestamp": int(datetime(2024, 3, 1).timestamp()),
            "news_summary": "Major exchange launches new features",
            "sentiment_score": 0.45,
            "technical_setup": "Testing previous resistance levels",
            "metadata": {"market_phase": "recovery"}
        },
        # Add more...
    ]

    results = await pipeline.batch_create_historical_snapshots(historical_snapshots)
    print(f"✓ Backfilled {len(results)} historical snapshots")


# ============================================================================
# PERFORMANCE NOTES
# ============================================================================
"""
Vectorize Query Performance:
- Typical query time: 5-15ms
- Returns: IDs (timestamps) + full metadata + similarity scores
- No additional lookups needed!

Why it's fast:
1. Vectorize indexes are in-memory globally distributed
2. Metadata is stored WITH the vector (no joins needed)
3. Cosine similarity is computed on Cloudflare's edge

Scaling:
- Free tier: 5M queried dimensions/month (~4,800 queries with 1024-dim vectors)
- Paid: $0.040 per 1M queried dimensions (~$0.04 per 1,000 queries)
- Storage: 10M stored dimensions free (~9,700 vectors with 1024-dim)

For your use case (finding similar time periods):
- Store 1 snapshot per day = 365 snapshots/year
- Query 100 times/day = 3,000 queries/month
- Cost: ~$0.12/month for queries + free storage

This is MUCH faster and cheaper than:
- D1 queries (50-100ms, SQL complexity)
- KV lookups (need vector search first, then KV lookup = 2 operations)
- Durable Objects (overkill for read-heavy workloads)
"""


if __name__ == "__main__":
    asyncio.run(main())
