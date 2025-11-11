"""
Time Period Search: Vector Similarity → Metadata Template → D1 Expansion

This demonstrates the actual workflow:
1. Vector search finds semantically similar periods (by news/sentiment)
2. Extract metadata patterns from those periods (RSI, MACD, etc.)
3. Use metadata as template to find MORE periods in D1
4. Analyze outcomes from expanded dataset

This gives you the best of both:
- Semantic understanding (via Vectorize)
- Large sample size (via D1 pattern matching)
"""

import asyncio
import aiohttp
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class MetadataPattern:
    """Extracted pattern from similar period"""
    rsi_min: float
    rsi_max: float
    macd_signal: str
    sentiment_velocity_min: float
    sentiment_velocity_max: float
    fear_greed_min: int
    fear_greed_max: int
    volatility: str
    trend: str


class HybridPeriodSearch:
    """
    Two-stage search:
    1. Vectorize: Find semantically similar periods
    2. D1: Expand search using extracted metadata patterns
    """

    def __init__(self, embedding_worker_url: str, d1_service):
        self.embedding_url = embedding_worker_url
        self.d1 = d1_service

    async def find_and_expand_similar_periods(
        self,
        current_news: str,
        current_sentiment: float,
        current_technical: str,
        tolerance: Dict[str, float] = None
    ) -> Dict[str, Any]:
        """
        Full workflow: Vector search → Extract patterns → D1 expansion

        Args:
            current_news: Current news summary
            current_sentiment: Current sentiment score
            current_technical: Current technical setup description
            tolerance: How much variance to allow in pattern matching
                       e.g., {"rsi": 5, "sentiment_velocity": 0.02}

        Returns:
            {
                "anchor_periods": [...],  # From Vectorize (semantic matches)
                "expanded_periods": [...],  # From D1 (technical matches)
                "patterns": [...],  # Extracted metadata patterns
                "total_matches": 150
            }
        """
        if tolerance is None:
            tolerance = {
                "rsi": 5,
                "sentiment_velocity": 0.02,
                "fear_greed": 10,
            }

        # STEP 1: Vector similarity search (semantic)
        print("Step 1: Finding semantically similar periods...")
        anchor_periods = await self._vector_search(
            current_news,
            current_sentiment,
            current_technical
        )

        print(f"Found {len(anchor_periods)} semantically similar periods")

        # STEP 2: Extract metadata patterns from anchor periods
        print("\nStep 2: Extracting metadata patterns...")
        patterns = self._extract_patterns(anchor_periods, tolerance)

        print(f"Extracted {len(patterns)} unique patterns")

        # STEP 3: Expand search using patterns in D1
        print("\nStep 3: Expanding search in D1...")
        expanded_periods = await self._expand_via_d1(patterns)

        print(f"Found {len(expanded_periods)} total matching periods in D1")

        return {
            "anchor_periods": anchor_periods,
            "expanded_periods": expanded_periods,
            "patterns": patterns,
            "total_matches": len(expanded_periods),
            "summary": self._generate_summary(anchor_periods, expanded_periods)
        }

    async def _vector_search(
        self,
        news: str,
        sentiment: float,
        technical: str
    ) -> List[Dict[str, Any]]:
        """
        Step 1: Query Vectorize for semantically similar periods
        """
        query = {
            "current_snapshot": {
                "timestamp": int(time.time()),
                "news_summary": news,
                "sentiment_score": sentiment,
                "technical_setup": technical
            },
            "top_k": 10,  # Get top 10 semantically similar
            "min_similarity": 0.65  # Lower threshold for more variety
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.embedding_url}/search/similar",
                json=query
            ) as resp:
                result = await resp.json()

        return result.get("similar_periods", [])

    def _extract_patterns(
        self,
        anchor_periods: List[Dict],
        tolerance: Dict[str, float]
    ) -> List[MetadataPattern]:
        """
        Step 2: Extract metadata patterns from anchor periods

        For each anchor period, create a pattern with tolerance ranges
        """
        patterns = []

        for period in anchor_periods:
            meta = period.get("metadata", {})

            pattern = MetadataPattern(
                rsi_min=meta.get("rsi", 50) - tolerance["rsi"],
                rsi_max=meta.get("rsi", 50) + tolerance["rsi"],
                macd_signal=meta.get("macd_signal", "bullish"),
                sentiment_velocity_min=meta.get("sentiment_velocity", 0) - tolerance["sentiment_velocity"],
                sentiment_velocity_max=meta.get("sentiment_velocity", 0) + tolerance["sentiment_velocity"],
                fear_greed_min=meta.get("fear_greed", 50) - tolerance["fear_greed"],
                fear_greed_max=meta.get("fear_greed", 50) + tolerance["fear_greed"],
                volatility=meta.get("volatility", "medium"),
                trend=meta.get("trend", "uptrend")
            )

            patterns.append(pattern)

            print(f"  Pattern: RSI {pattern.rsi_min:.1f}-{pattern.rsi_max:.1f}, "
                  f"MACD {pattern.macd_signal}, "
                  f"Sentiment velocity {pattern.sentiment_velocity_min:.3f}-{pattern.sentiment_velocity_max:.3f}")

        return patterns

    async def _expand_via_d1(
        self,
        patterns: List[MetadataPattern]
    ) -> List[Dict[str, Any]]:
        """
        Step 3: Use patterns to query D1 for ALL matching periods

        This finds periods with similar technical setups, even if
        the news narrative was completely different
        """
        all_matches = []

        for i, pattern in enumerate(patterns):
            print(f"  Searching D1 for pattern {i+1}/{len(patterns)}...")

            # Build SQL query from pattern
            sql = """
                SELECT
                    id,
                    entry_time,
                    exit_time,
                    entry_price,
                    exit_price,
                    pnl_pct,
                    profitable,
                    entry_rsi_14,
                    entry_macd_bullish_cross,
                    entry_macd_bearish_cross,
                    sentiment_velocity,
                    sentiment_fear_greed,
                    entry_volatility_regime,
                    entry_trend_regime,
                    entry_volume_vs_avg
                FROM chaos_trades
                WHERE entry_rsi_14 BETWEEN ? AND ?
                  AND sentiment_velocity BETWEEN ? AND ?
                  AND sentiment_fear_greed BETWEEN ? AND ?
                  AND entry_volatility_regime = ?
                  AND entry_trend_regime = ?
            """

            # Determine MACD condition
            if pattern.macd_signal == "bullish":
                sql += " AND entry_macd_bullish_cross = 1"
            elif pattern.macd_signal == "bearish":
                sql += " AND entry_macd_bearish_cross = 1"

            params = [
                pattern.rsi_min,
                pattern.rsi_max,
                pattern.sentiment_velocity_min,
                pattern.sentiment_velocity_max,
                pattern.fear_greed_min,
                pattern.fear_greed_max,
                pattern.volatility,
                pattern.trend
            ]

            # Query D1
            result = await self.d1.query(sql, params)
            matches = result.rows if hasattr(result, 'rows') else []

            print(f"    Found {len(matches)} matches for this pattern")

            all_matches.extend(matches)

        # Remove duplicates (if same period matches multiple patterns)
        unique_matches = self._deduplicate(all_matches)

        return unique_matches

    def _deduplicate(self, matches: List[Dict]) -> List[Dict]:
        """Remove duplicate periods"""
        seen_ids = set()
        unique = []

        for match in matches:
            match_id = match.get('id') or match.get('entry_time')
            if match_id not in seen_ids:
                seen_ids.add(match_id)
                unique.append(match)

        return unique

    def _generate_summary(
        self,
        anchor_periods: List[Dict],
        expanded_periods: List[Dict]
    ) -> Dict[str, Any]:
        """Generate summary statistics"""
        # Calculate win rates and returns
        profitable = [p for p in expanded_periods if p.get('profitable') == 1]
        win_rate = len(profitable) / len(expanded_periods) if expanded_periods else 0

        avg_pnl = sum(p.get('pnl_pct', 0) for p in expanded_periods) / len(expanded_periods) if expanded_periods else 0
        avg_winning_pnl = sum(p.get('pnl_pct', 0) for p in profitable) / len(profitable) if profitable else 0

        return {
            "semantic_matches": len(anchor_periods),
            "technical_matches": len(expanded_periods),
            "expansion_ratio": len(expanded_periods) / len(anchor_periods) if anchor_periods else 0,
            "win_rate": win_rate,
            "avg_pnl_pct": avg_pnl,
            "avg_winning_pnl_pct": avg_winning_pnl,
            "total_profitable": len(profitable)
        }


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

async def main():
    """
    Example: Find similar periods and expand search
    """
    from cloudflare_d1_service import CloudflareD1Service

    # Initialize services
    d1 = CloudflareD1Service(bindings["DB"])
    searcher = HybridPeriodSearch(
        embedding_worker_url="https://pyswarm-embeddings.YOUR_SUBDOMAIN.workers.dev",
        d1_service=d1
    )

    # Current market conditions
    current_state = {
        "news": "Bitcoin ETF approval drives institutional buying surge. "
                "Major banks announce crypto custody services.",
        "sentiment": 0.72,
        "technical": "Strong bullish momentum with RSI at 68. "
                     "MACD showing bullish crossover. Breaking key resistance."
    }

    # Run hybrid search
    results = await searcher.find_and_expand_similar_periods(
        current_news=current_state["news"],
        current_sentiment=current_state["sentiment"],
        current_technical=current_state["technical"],
        tolerance={
            "rsi": 5,                # ±5 RSI points
            "sentiment_velocity": 0.02,  # ±0.02 sentiment change
            "fear_greed": 10         # ±10 fear/greed points
        }
    )

    # Results breakdown
    print("\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80)

    print(f"\nSemanically similar periods (Vectorize): {len(results['anchor_periods'])}")
    for i, period in enumerate(results['anchor_periods'][:3], 1):
        print(f"  {i}. {period['id']} - Similarity: {period['similarity_score']:.3f}")
        print(f"     News: {period.get('news_summary', 'N/A')[:60]}...")

    print(f"\nTechnically similar periods (D1): {len(results['expanded_periods'])}")
    print(f"Expansion ratio: {results['summary']['expansion_ratio']:.1f}x")

    print(f"\nPerformance of similar periods:")
    print(f"  Win rate: {results['summary']['win_rate']:.1%}")
    print(f"  Avg PnL: {results['summary']['avg_pnl_pct']:.2%}")
    print(f"  Avg winning PnL: {results['summary']['avg_winning_pnl_pct']:.2%}")

    # Analyze what happened after these periods
    print("\n" + "="*80)
    print("OUTCOME ANALYSIS")
    print("="*80)

    for period in results['expanded_periods'][:10]:
        # You can now look up what happened AFTER this period
        future_price = await get_price_after(period['entry_time'], days=7)
        entry_price = period['entry_price']
        return_7d = (future_price - entry_price) / entry_price

        print(f"{period['entry_time']}: "
              f"RSI {period['entry_rsi_14']:.1f}, "
              f"7-day return: {return_7d:.1%}")


# ============================================================================
# KEY INSIGHT
# ============================================================================
"""
Why this two-stage approach is powerful:

STAGE 1 - Vectorize (Semantic):
- Finds 5-10 periods with similar NEWS NARRATIVES
- "ETF approval" ≈ "Institutional adoption" ≈ "Regulatory clarity"
- Extracts their TECHNICAL METADATA

STAGE 2 - D1 (Technical):
- Uses metadata as TEMPLATE
- Finds 50-200 periods with SIMILAR TECHNICAL SETUPS
- Even if news was completely different
- Much larger sample size for statistical analysis

Example:
- Vectorize finds: 8 periods with "ETF approval" type news
- Those 8 had: RSI 65-75, bullish MACD, improving sentiment
- D1 finds: 156 periods with RSI 65-75, bullish MACD, improving sentiment
  (even if news was about "mining profitability" or "exchange listings")
- Now you have 156 examples to analyze outcomes!

This combines:
✓ Semantic understanding (what does this feel like?)
✓ Technical precision (what are the exact conditions?)
✓ Large sample size (statistical significance)
"""

if __name__ == "__main__":
    asyncio.run(main())
