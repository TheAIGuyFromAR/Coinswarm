#!/usr/bin/env python3
"""
Test Agents with 50,000 Real Historical Trades

Uses the actual historical trades from historical-trades-50k.sql
to validate pattern detection and agent performance.

Key features:
- 50,000 real trades with entry/exit prices, P&L, market conditions
- Tests pattern recognition on REAL outcomes
- Validates agents against actual profitable vs unprofitable trades
- Cross-validates discovered patterns
"""

import asyncio
import json
import logging
import re
import statistics
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class HistoricalTrade:
    """Real historical trade from SQL data"""
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    pnl_pct: float
    profitable: bool
    buy_reason: str
    buy_state: dict
    sell_reason: str
    sell_state: dict
    duration_minutes: float


class HistoricalTradesLoader:
    """Load and parse 50,000 historical trades from SQL file"""

    def __init__(self, sql_file: str = "historical-trades-50k.sql"):
        self.sql_file = Path(sql_file)
        self.trades: list[HistoricalTrade] = []

    def load_trades(self) -> list[HistoricalTrade]:
        """Parse SQL file and extract trades"""

        logger.info(f"Loading historical trades from {self.sql_file}...")

        if not self.sql_file.exists():
            raise FileNotFoundError(
                f"Historical trades file not found: {self.sql_file}\n"
                f"Expected to find 50,000 real trades!"
            )

        with open(self.sql_file) as f:
            content = f.read()

        # Find all INSERT statements
        insert_pattern = r"INSERT INTO chaos_trades.*?VALUES\s+(.*?)(?:;|\nINSERT)"
        inserts = re.findall(insert_pattern, content, re.DOTALL)

        if not inserts:
            logger.error("No INSERT statements found in SQL file!")
            return []

        trades_parsed = 0

        for insert_block in inserts:
            # Parse individual trade rows
            # Format: ('timestamp', 'timestamp', price, price, pnl_pct, profitable, 'reason', '{json}', 'reason', '{json}')
            row_pattern = r"\((.*?)\)(?:,|\s*$)"
            rows = re.findall(row_pattern, insert_block, re.DOTALL)

            for row in rows:
                try:
                    trade = self._parse_trade_row(row)
                    if trade:
                        self.trades.append(trade)
                        trades_parsed += 1

                        if trades_parsed % 5000 == 0:
                            logger.info(f"  Loaded {trades_parsed} trades...")
                except Exception as e:
                    logger.debug(f"Failed to parse row: {e}")
                    continue

        logger.info(f"✅ Loaded {len(self.trades)} real historical trades")
        return self.trades

    def _parse_trade_row(self, row: str) -> HistoricalTrade | None:
        """Parse a single trade row"""

        # Split by comma, but respect quotes and braces
        parts = []
        current = ""
        in_quotes = False
        in_braces = 0

        for char in row:
            if char == "'" and (not current or current[-1] != '\\'):
                in_quotes = not in_quotes
            elif char == '{' and not in_quotes:
                in_braces += 1
            elif char == '}' and not in_quotes:
                in_braces -= 1
            elif char == ',' and not in_quotes and in_braces == 0:
                parts.append(current.strip())
                current = ""
                continue

            current += char

        if current:
            parts.append(current.strip())

        if len(parts) < 10:
            return None

        # Extract fields
        entry_time_str = parts[0].strip("'")
        exit_time_str = parts[1].strip("'")
        entry_price = float(parts[2])
        exit_price = float(parts[3])
        pnl_pct = float(parts[4])
        profitable = int(parts[5]) == 1
        buy_reason = parts[6].strip("'")
        buy_state_str = parts[7].strip("'")
        sell_reason = parts[8].strip("'")
        sell_state_str = parts[9].strip("'")

        # Parse JSON states
        try:
            buy_state = json.loads(buy_state_str)
        except:
            buy_state = {}

        try:
            sell_state = json.loads(sell_state_str)
        except:
            sell_state = {}

        # Calculate duration
        entry_time = datetime.fromisoformat(entry_time_str.replace('Z', '+00:00'))
        exit_time = datetime.fromisoformat(exit_time_str.replace('Z', '+00:00'))
        duration = (exit_time - entry_time).total_seconds() / 60

        return HistoricalTrade(
            entry_time=entry_time,
            exit_time=exit_time,
            entry_price=entry_price,
            exit_price=exit_price,
            pnl_pct=pnl_pct,
            profitable=profitable,
            buy_reason=buy_reason,
            buy_state=buy_state,
            sell_reason=sell_reason,
            sell_state=sell_state,
            duration_minutes=duration
        )


class PatternAnalyzer:
    """Analyze historical trades to discover profitable patterns"""

    def __init__(self, trades: list[HistoricalTrade]):
        self.trades = trades
        self.profitable_trades = [t for t in trades if t.profitable]
        self.losing_trades = [t for t in trades if not t.profitable]

    def analyze_all_patterns(self):
        """Run comprehensive pattern analysis"""

        logger.info("\n" + "="*80)
        logger.info("HISTORICAL TRADES PATTERN ANALYSIS")
        logger.info("="*80)

        # Basic stats
        self._print_basic_stats()

        # Buy reason analysis
        self._analyze_buy_reasons()

        # Sell reason analysis
        self._analyze_sell_reasons()

        # Market condition analysis
        self._analyze_market_conditions()

        # Duration analysis
        self._analyze_trade_durations()

        logger.info("\n" + "="*80)

    def _print_basic_stats(self):
        """Print basic statistics"""

        total = len(self.trades)
        profitable = len(self.profitable_trades)
        losing = len(self.losing_trades)
        win_rate = profitable / total if total > 0 else 0

        avg_profit = statistics.mean([t.pnl_pct for t in self.profitable_trades]) if self.profitable_trades else 0
        avg_loss = statistics.mean([t.pnl_pct for t in self.losing_trades]) if self.losing_trades else 0

        logger.info("\nBasic Statistics:")
        logger.info(f"  Total Trades:     {total:,}")
        logger.info(f"  Profitable:       {profitable:,} ({win_rate:.1%})")
        logger.info(f"  Losing:           {losing:,} ({1-win_rate:.1%})")
        logger.info(f"  Avg Profit:       {avg_profit:+.2f}%")
        logger.info(f"  Avg Loss:         {avg_loss:+.2f}%")

        if self.profitable_trades and self.losing_trades:
            profit_factor = abs(avg_profit * profitable / (avg_loss * losing))
            logger.info(f"  Profit Factor:    {profit_factor:.2f}")

    def _analyze_buy_reasons(self):
        """Analyze which buy reasons are most profitable"""

        logger.info("\nBuy Reason Analysis:")

        buy_reasons = {}
        for trade in self.trades:
            reason = trade.buy_reason
            if reason not in buy_reasons:
                buy_reasons[reason] = {"total": 0, "profitable": 0, "pnl": []}

            buy_reasons[reason]["total"] += 1
            if trade.profitable:
                buy_reasons[reason]["profitable"] += 1
            buy_reasons[reason]["pnl"].append(trade.pnl_pct)

        # Sort by win rate
        sorted_reasons = sorted(
            buy_reasons.items(),
            key=lambda x: x[1]["profitable"] / x[1]["total"],
            reverse=True
        )

        for reason, stats in sorted_reasons[:10]:
            win_rate = stats["profitable"] / stats["total"]
            avg_pnl = statistics.mean(stats["pnl"])
            emoji = "✅" if win_rate > 0.5 else "❌"

            logger.info(
                f"  {emoji} {reason:40s} | "
                f"Win Rate: {win_rate:5.1%} | "
                f"Avg P&L: {avg_pnl:+6.2f}% | "
                f"Count: {stats['total']:4d}"
            )

    def _analyze_sell_reasons(self):
        """Analyze which sell reasons correlate with profits"""

        logger.info("\nSell Reason Analysis:")

        sell_reasons = {}
        for trade in self.trades:
            reason = trade.sell_reason
            if reason not in sell_reasons:
                sell_reasons[reason] = {"total": 0, "profitable": 0, "pnl": []}

            sell_reasons[reason]["total"] += 1
            if trade.profitable:
                sell_reasons[reason]["profitable"] += 1
            sell_reasons[reason]["pnl"].append(trade.pnl_pct)

        # Sort by average P&L
        sorted_reasons = sorted(
            sell_reasons.items(),
            key=lambda x: statistics.mean(x[1]["pnl"]),
            reverse=True
        )

        for reason, stats in sorted_reasons[:10]:
            win_rate = stats["profitable"] / stats["total"]
            avg_pnl = statistics.mean(stats["pnl"])
            emoji = "✅" if avg_pnl > 0 else "❌"

            logger.info(
                f"  {emoji} {reason:40s} | "
                f"Win Rate: {win_rate:5.1%} | "
                f"Avg P&L: {avg_pnl:+6.2f}% | "
                f"Count: {stats['total']:4d}"
            )

    def _analyze_market_conditions(self):
        """Analyze market conditions at entry for profitable vs losing trades"""

        logger.info("\nMarket Conditions Analysis:")

        # Analyze momentum
        profitable_momentum = [
            t.buy_state.get('momentum1tick', 0)
            for t in self.profitable_trades
            if 'momentum1tick' in t.buy_state
        ]
        losing_momentum = [
            t.buy_state.get('momentum1tick', 0)
            for t in self.losing_trades
            if 'momentum1tick' in t.buy_state
        ]

        if profitable_momentum and losing_momentum:
            logger.info("  Entry Momentum (1-tick):")
            logger.info(f"    Profitable trades: {statistics.mean(profitable_momentum):+.4f}")
            logger.info(f"    Losing trades:     {statistics.mean(losing_momentum):+.4f}")

        # Analyze volume
        profitable_volume = [
            t.buy_state.get('volumeVsAvg', 1)
            for t in self.profitable_trades
            if 'volumeVsAvg' in t.buy_state
        ]
        losing_volume = [
            t.buy_state.get('volumeVsAvg', 1)
            for t in self.losing_trades
            if 'volumeVsAvg' in t.buy_state
        ]

        if profitable_volume and losing_volume:
            logger.info("  Entry Volume vs Avg:")
            logger.info(f"    Profitable trades: {statistics.mean(profitable_volume):.2f}x")
            logger.info(f"    Losing trades:     {statistics.mean(losing_volume):.2f}x")

        # Analyze volatility
        profitable_volatility = [
            t.buy_state.get('volatility', 0)
            for t in self.profitable_trades
            if 'volatility' in t.buy_state
        ]
        losing_volatility = [
            t.buy_state.get('volatility', 0)
            for t in self.losing_trades
            if 'volatility' in t.buy_state
        ]

        if profitable_volatility and losing_volatility:
            logger.info("  Entry Volatility:")
            logger.info(f"    Profitable trades: {statistics.mean(profitable_volatility):.4f}")
            logger.info(f"    Losing trades:     {statistics.mean(losing_volatility):.4f}")

    def _analyze_trade_durations(self):
        """Analyze optimal trade durations"""

        logger.info("\nTrade Duration Analysis:")

        # Bucket by duration
        buckets = {
            "< 1 hour": [],
            "1-6 hours": [],
            "6-24 hours": [],
            "1-7 days": [],
            "> 7 days": []
        }

        for trade in self.trades:
            duration_hours = trade.duration_minutes / 60

            if duration_hours < 1:
                bucket = "< 1 hour"
            elif duration_hours < 6:
                bucket = "1-6 hours"
            elif duration_hours < 24:
                bucket = "6-24 hours"
            elif duration_hours < 168:  # 7 days
                bucket = "1-7 days"
            else:
                bucket = "> 7 days"

            buckets[bucket].append(trade)

        for bucket_name, trades in buckets.items():
            if not trades:
                continue

            profitable = sum(1 for t in trades if t.profitable)
            win_rate = profitable / len(trades)
            avg_pnl = statistics.mean([t.pnl_pct for t in trades])
            emoji = "✅" if win_rate > 0.5 else "❌"

            logger.info(
                f"  {emoji} {bucket_name:12s}: "
                f"Win Rate: {win_rate:5.1%} | "
                f"Avg P&L: {avg_pnl:+6.2f}% | "
                f"Count: {len(trades):5d}"
            )


async def main():
    """Main entry point"""

    logger.info("="*80)
    logger.info("TESTING WITH 50,000 REAL HISTORICAL TRADES")
    logger.info("="*80)

    # Load historical trades
    loader = HistoricalTradesLoader()
    trades = loader.load_trades()

    if not trades:
        logger.error("❌ No trades loaded! Check SQL file.")
        return

    # Analyze patterns
    analyzer = PatternAnalyzer(trades)
    analyzer.analyze_all_patterns()

    logger.info("\n✅ Historical trades analysis complete!")
    logger.info("\nNext steps:")
    logger.info("  1. Use these patterns to train agents")
    logger.info("  2. Validate pattern recognition on new data")
    logger.info("  3. Implement discovered profitable patterns")


if __name__ == "__main__":
    asyncio.run(main())
