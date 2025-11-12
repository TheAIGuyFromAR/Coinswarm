"""
Backfill Vectorize with Historical Time Period Snapshots

This script processes 6+ years of historical data from D1 and creates
complete snapshots with both indicators AND outcomes in Vectorize.

Since we have historical data, we can "look forward" from each date
to calculate what actually happened 7/30 days later.

Result: Fully labeled dataset for pattern matching!
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Any
import json


class HistoricalVectorizeBackfill:
    """
    Backfill Vectorize from historical D1 data
    """

    def __init__(self, d1_service, embedding_worker_url: str):
        self.d1 = d1_service
        self.embedding_url = embedding_worker_url
        self.batch_size = 100  # Process 100 days at a time

    async def backfill_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ):
        """
        Backfill all dates in range with complete snapshots
        """
        current_date = start_date
        total_processed = 0

        while current_date <= end_date:
            batch_end = min(current_date + timedelta(days=self.batch_size), end_date)

            print(f"\n{'='*80}")
            print(f"Processing: {current_date.date()} to {batch_end.date()}")
            print(f"{'='*80}\n")

            # Process batch
            snapshots = await self._process_batch(current_date, batch_end)

            # Store in Vectorize
            if snapshots:
                await self._store_snapshots(snapshots)
                total_processed += len(snapshots)

            print(f"✓ Processed {len(snapshots)} snapshots")
            print(f"Total so far: {total_processed}")

            current_date = batch_end + timedelta(days=1)

        print(f"\n{'='*80}")
        print(f"BACKFILL COMPLETE")
        print(f"Total snapshots created: {total_processed}")
        print(f"{'='*80}\n")

    async def _process_batch(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """
        Process a batch of dates and create complete snapshots
        """
        snapshots = []

        current = start_date
        while current <= end_date:
            timestamp = int(current.timestamp())

            # Get all data for this date
            indicators = await self._get_indicators(timestamp)

            if not indicators:
                print(f"⚠ No data for {current.date()}, skipping")
                current += timedelta(days=1)
                continue

            # Calculate outcomes (we have historical data!)
            outcomes_7d = await self._calculate_outcomes(timestamp, days=7)
            outcomes_30d = await self._calculate_outcomes(timestamp, days=30)

            # Build complete snapshot
            snapshot = {
                **indicators,
                **outcomes_7d,
                **outcomes_30d
            }

            # Generate embedding for news/sentiment text
            embedding_text = self._build_embedding_text(snapshot)
            embedding = await self._generate_embedding(embedding_text)

            # Format for Vectorize
            vectorize_record = {
                "id": current.isoformat(),
                "values": embedding,
                "metadata": snapshot
            }

            snapshots.append(vectorize_record)
            current += timedelta(days=1)

        return snapshots

    async def _get_indicators(self, timestamp: int) -> Dict[str, Any]:
        """
        Get all indicators for a specific timestamp from D1
        """
        # Query technical indicators
        tech_sql = """
            SELECT
                timestamp,
                symbol,
                sma_20, sma_50, sma_200,
                ema_12, ema_26,
                bb_upper, bb_middle, bb_lower,
                macd, macd_signal, macd_histogram,
                rsi_14,
                fear_greed_index,
                volume_sma_20, volume_ratio
            FROM technical_indicators
            WHERE timestamp = ?
              AND symbol = 'BTC'
              AND timeframe = '1d'
        """

        tech_result = await self.d1.query(tech_sql, [timestamp])
        if not tech_result.rows:
            return None

        tech = tech_result.rows[0]

        # Query price data
        price_sql = """
            SELECT open, high, low, close, volume
            FROM price_data
            WHERE timestamp = ?
              AND symbol = 'BTC'
              AND timeframe = '1d'
        """

        price_result = await self.d1.query(price_sql, [timestamp])
        if not price_result.rows:
            return None

        price = price_result.rows[0]

        # Query sentiment data
        sentiment_sql = """
            SELECT
                sentiment_value,
                fear_greed_value,
                velocity,
                acceleration,
                jerk,
                direction,
                news_volume
            FROM sentiment_timeseries
            WHERE timestamp = ?
              AND symbol = 'BTC'
        """

        sentiment_result = await self.d1.query(sentiment_sql, [timestamp])
        sentiment = sentiment_result.rows[0] if sentiment_result.rows else {}

        # Calculate derived indicators
        indicators = self._calculate_derived_indicators(tech, price, sentiment)

        return indicators

    def _calculate_derived_indicators(
        self,
        tech: Dict,
        price: Dict,
        sentiment: Dict
    ) -> Dict[str, Any]:
        """
        Calculate all derived indicators
        """
        btc_price = price['close']

        # RSI classification
        rsi = tech['rsi_14']
        if rsi < 30:
            rsi_range = "oversold"
        elif rsi > 70:
            rsi_range = "overbought"
        else:
            rsi_range = "neutral"

        # MACD signal
        macd_hist = tech['macd_histogram']
        if macd_hist > 50:
            macd_signal = "bullish"
        elif macd_hist < -50:
            macd_signal = "bearish"
        else:
            macd_signal = "neutral"

        # Price vs MAs
        price_vs_sma20 = btc_price / tech['sma_20'] if tech['sma_20'] else 1
        price_vs_sma50 = btc_price / tech['sma_50'] if tech['sma_50'] else 1
        price_vs_sma200 = btc_price / tech['sma_200'] if tech['sma_200'] else 1

        # SMA alignment
        if tech['sma_20'] > tech['sma_50'] > tech['sma_200']:
            sma_alignment = "golden_cross"
        elif tech['sma_20'] < tech['sma_50'] < tech['sma_200']:
            sma_alignment = "death_cross"
        else:
            sma_alignment = "mixed"

        # Volatility classification
        bb_width = (tech['bb_upper'] - tech['bb_lower']) / tech['bb_middle'] if tech['bb_middle'] else 0
        if bb_width < 0.03:
            volatility = "low"
        elif bb_width > 0.06:
            volatility = "high"
        else:
            volatility = "medium"

        # Fear & Greed classification
        fear_greed = tech['fear_greed_index']
        if fear_greed < 25:
            fear_greed_class = "fear"
        elif fear_greed > 75:
            fear_greed_class = "greed"
        else:
            fear_greed_class = "neutral"

        return {
            # Temporal
            "timestamp": tech['timestamp'],
            "day_of_week": datetime.fromtimestamp(tech['timestamp']).weekday(),
            "month": datetime.fromtimestamp(tech['timestamp']).month,

            # Technical
            "rsi": rsi,
            "rsi_range": rsi_range,

            "macd_histogram": macd_hist,
            "macd_signal": macd_signal,

            "sma_20": tech['sma_20'],
            "sma_50": tech['sma_50'],
            "sma_200": tech['sma_200'],
            "price_vs_sma20": price_vs_sma20,
            "price_vs_sma50": price_vs_sma50,
            "price_vs_sma200": price_vs_sma200,
            "sma_alignment": sma_alignment,

            "bb_upper": tech['bb_upper'],
            "bb_middle": tech['bb_middle'],
            "bb_lower": tech['bb_lower'],
            "bb_width": bb_width,
            "volatility": volatility,

            "volume_ratio": tech['volume_ratio'],
            "volume_spike": 1 if tech['volume_ratio'] > 2.0 else 0,

            # Sentiment
            "sentiment_score": sentiment.get('sentiment_value', 0),
            "sentiment_velocity": sentiment.get('velocity', 0),
            "sentiment_acceleration": sentiment.get('acceleration', 0),
            "sentiment_jerk": sentiment.get('jerk', 0),
            "sentiment_direction": sentiment.get('direction', 'stable'),

            "fear_greed": fear_greed,
            "fear_greed_class": fear_greed_class,

            "news_volume": sentiment.get('news_volume', 0),

            # Price
            "btc_price": btc_price,
            "volume": price['volume']
        }

    async def _calculate_outcomes(
        self,
        entry_timestamp: int,
        days: int
    ) -> Dict[str, Any]:
        """
        Calculate outcomes N days forward
        (We have historical data, so we can look forward!)
        """
        # Get price at entry
        entry_price_sql = """
            SELECT close FROM price_data
            WHERE timestamp = ?
              AND symbol = 'BTC'
              AND timeframe = '1d'
        """
        entry_result = await self.d1.query(entry_price_sql, [entry_timestamp])
        if not entry_result.rows:
            return {}

        entry_price = entry_result.rows[0]['close']

        # Get all prices for the period
        end_timestamp = entry_timestamp + (days * 86400)
        period_sql = """
            SELECT timestamp, close, high, low
            FROM price_data
            WHERE timestamp BETWEEN ? AND ?
              AND symbol = 'BTC'
              AND timeframe = '1d'
            ORDER BY timestamp ASC
        """

        period_result = await self.d1.query(period_sql, [entry_timestamp, end_timestamp])
        if not period_result.rows or len(period_result.rows) < days:
            return {}  # Not enough data

        period_prices = period_result.rows

        # Calculate metrics
        exit_price = period_prices[-1]['close']
        outcome = (exit_price - entry_price) / entry_price

        # Max drawdown
        lowest_price = min(p['low'] for p in period_prices)
        max_drawdown = (lowest_price - entry_price) / entry_price

        # Peak return
        highest_price = max(p['high'] for p in period_prices)
        peak_return = (highest_price - entry_price) / entry_price

        # Days to peak
        days_to_peak = next(
            (i for i, p in enumerate(period_prices) if p['high'] == highest_price),
            len(period_prices) - 1
        )

        # Volatility
        returns = [(period_prices[i]['close'] - period_prices[i-1]['close']) / period_prices[i-1]['close']
                   for i in range(1, len(period_prices))]
        volatility = (sum(r**2 for r in returns) / len(returns)) ** 0.5 if returns else 0

        # Outcome classification
        if outcome > 0.10:
            outcome_class = "strong_win"
        elif outcome > 0.03:
            outcome_class = "weak_win"
        elif outcome > -0.03:
            outcome_class = "weak_loss"
        else:
            outcome_class = "strong_loss"

        prefix = f"outcome_{days}d" if days == 7 else f"outcome_{days}d"

        return {
            f"{prefix}": outcome,
            f"profitable_{days}d": 1 if outcome > 0 else 0,
            f"max_drawdown_{days}d": max_drawdown,
            f"peak_return_{days}d": peak_return,
            f"days_to_peak_{days}d": days_to_peak,
            f"volatility_{days}d": volatility,
            f"outcome_class_{days}d": outcome_class
        }

    def _build_embedding_text(self, snapshot: Dict) -> str:
        """
        Build text representation for embedding
        """
        rsi = snapshot['rsi']
        macd = snapshot['macd_signal']
        sentiment = snapshot['sentiment_score']
        sentiment_vel = snapshot.get('sentiment_velocity', 0)
        trend = snapshot.get('sma_alignment', 'mixed')

        text = f"""
        RSI {rsi:.0f} ({snapshot['rsi_range']}),
        MACD {macd},
        Sentiment {sentiment:.2f} (velocity {sentiment_vel:.3f}),
        Trend {trend},
        Fear & Greed {snapshot['fear_greed']},
        Volume ratio {snapshot['volume_ratio']:.2f}
        """.strip()

        return text

    async def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding via embedding worker
        """
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.embedding_url}/embed",
                json={"text": text, "model": "bge-large-en"}
            ) as resp:
                result = await resp.json()
                return result["embeddings"][0]

    async def _store_snapshots(self, snapshots: List[Dict]):
        """
        Batch upsert snapshots to Vectorize
        """
        # Split into batches of 1000 (Vectorize limit)
        for i in range(0, len(snapshots), 1000):
            batch = snapshots[i:i+1000]

            async with aiohttp.ClientSession() as session:
                # You'd need an upsert endpoint on your embedding worker
                # Or use Vectorize binding directly
                async with session.post(
                    f"{self.embedding_url}/batch/upsert",
                    json={"vectors": batch}
                ) as resp:
                    result = await resp.json()

            print(f"  Stored batch {i//1000 + 1}: {len(batch)} vectors")


# ============================================================================
# USAGE
# ============================================================================

async def main():
    """
    Backfill 6 years of historical data
    """
    from cloudflare_d1_service import CloudflareD1Service

    # Initialize services
    d1 = CloudflareD1Service(bindings["DB"])
    backfill = HistoricalVectorizeBackfill(
        d1_service=d1,
        embedding_worker_url="https://pyswarm-embeddings.YOUR_SUBDOMAIN.workers.dev"
    )

    # Backfill 6 years
    start_date = datetime(2018, 1, 1)
    end_date = datetime(2024, 12, 31)

    print(f"Starting backfill: {start_date.date()} to {end_date.date()}")
    print(f"Total days: {(end_date - start_date).days}")
    print(f"{'='*80}\n")

    await backfill.backfill_date_range(start_date, end_date)

    print("\n✅ Backfill complete!")
    print("Vectorize now contains complete snapshots with outcomes")
    print("Ready for pattern matching and predictions!")


if __name__ == "__main__":
    asyncio.run(main())
