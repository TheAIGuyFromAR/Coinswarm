"""
Pattern Analysis Agent

Analyzes chaos trading results to discover patterns that correlate with profitable trades.

Process:
1. Load chaos trading results (thousands of trades)
2. Separate winning trades from losing trades
3. Analyze market conditions at entry/exit
4. Find patterns that differentiate winners from losers
5. Generate candidate strategies
6. Store patterns for testing
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import statistics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Pattern:
    """A discovered pattern/strategy"""
    id: str
    name: str
    description: str
    conditions: Dict  # Entry conditions
    exit_rules: Dict  # Exit conditions
    confidence: float  # How confident are we in this pattern
    win_rate: float  # Win rate in training data
    avg_return: float  # Average return per trade
    sample_size: int  # Number of trades that match this pattern
    discovered_at: str  # Timestamp


class PatternAnalysisAgent:
    """
    Agent that discovers profitable patterns from chaos trading data.

    Uses statistical analysis to find market conditions that correlate
    with profitable vs unprofitable trades.
    """

    def __init__(self):
        self.patterns = []
        self.all_trades = []
        self.winning_trades = []
        self.losing_trades = []

    def load_trades(self, filepath: str):
        """Load chaos trading results"""
        logger.info(f"Loading trades from {filepath}...")

        with open(filepath, "r") as f:
            self.all_trades = json.load(f)

        self.winning_trades = [t for t in self.all_trades if t.get("profitable", False)]
        self.losing_trades = [t for t in self.all_trades if not t.get("profitable", False)]

        logger.info(f"  Loaded {len(self.all_trades)} trades")
        logger.info(f"  Winners: {len(self.winning_trades)} ({len(self.winning_trades)/len(self.all_trades)*100:.1f}%)")
        logger.info(f"  Losers: {len(self.losing_trades)} ({len(self.losing_trades)/len(self.all_trades)*100:.1f}%)")

    def analyze_entry_conditions(self) -> Dict:
        """
        Analyze what entry conditions correlate with winners vs losers.

        Returns dict of features and their statistics for winners vs losers.
        """

        logger.info("\n" + "=" * 80)
        logger.info("ANALYZING ENTRY CONDITIONS")
        logger.info("=" * 80)

        features = {}

        # Extract features from buy states
        def extract_features(trades):
            feature_values = defaultdict(list)

            for trade in trades:
                buy_state = trade.get("buy_state", {})
                buy_confidence = trade.get("buy_confidence", 0)

                # Momentum
                if "price_change_1" in buy_state:
                    feature_values["momentum_1tick"].append(buy_state["price_change_1"])

                # Position vs moving averages
                if "price_vs_sma10" in buy_state:
                    feature_values["vs_sma10"].append(buy_state["price_vs_sma10"])

                if "price_vs_sma20" in buy_state:
                    feature_values["vs_sma20"].append(buy_state["price_vs_sma20"])

                # Volume
                if "volume_vs_avg" in buy_state:
                    feature_values["volume_vs_avg"].append(buy_state["volume_vs_avg"])

                # Volatility
                if "volatility_10" in buy_state:
                    feature_values["volatility"].append(buy_state["volatility_10"])

                # Confidence
                feature_values["buy_confidence"].append(buy_confidence)

            return feature_values

        winner_features = extract_features(self.winning_trades)
        loser_features = extract_features(self.losing_trades)

        # Compare features
        for feature_name in winner_features.keys():
            if feature_name in loser_features:
                winner_values = winner_features[feature_name]
                loser_values = loser_features[feature_name]

                if winner_values and loser_values:
                    winner_avg = statistics.mean(winner_values)
                    loser_avg = statistics.mean(loser_values)
                    winner_median = statistics.median(winner_values)
                    loser_median = statistics.median(loser_values)

                    # Calculate difference
                    diff = winner_avg - loser_avg
                    pct_diff = (diff / abs(loser_avg) * 100) if loser_avg != 0 else 0

                    features[feature_name] = {
                        "winner_avg": winner_avg,
                        "loser_avg": loser_avg,
                        "winner_median": winner_median,
                        "loser_median": loser_median,
                        "difference": diff,
                        "pct_difference": pct_diff
                    }

                    logger.info(f"\n📊 {feature_name}:")
                    logger.info(f"   Winners: avg={winner_avg:.4f}, median={winner_median:.4f}")
                    logger.info(f"   Losers:  avg={loser_avg:.4f}, median={loser_median:.4f}")
                    logger.info(f"   Diff:    {diff:+.4f} ({pct_diff:+.1f}%)")

        return features

    def analyze_exit_conditions(self) -> Dict:
        """
        Analyze what exit conditions correlate with winners vs losers.
        """

        logger.info("\n" + "=" * 80)
        logger.info("ANALYZING EXIT CONDITIONS")
        logger.info("=" * 80)

        features = {}

        def extract_features(trades):
            feature_values = defaultdict(list)

            for trade in trades:
                sell_state = trade.get("sell_state", {})
                profit_pct = trade.get("pnl_pct", 0)

                # Profit at exit
                feature_values["profit_pct"].append(profit_pct)

                # Distance from high
                if "distance_from_recent_high" in sell_state:
                    feature_values["distance_from_high"].append(sell_state["distance_from_recent_high"])

                # Momentum at exit
                if "momentum_5" in sell_state:
                    feature_values["exit_momentum"].append(sell_state["momentum_5"])

                # Confidence at exit
                sell_confidence = trade.get("sell_confidence", 0)
                feature_values["sell_confidence"].append(sell_confidence)

                # Duration
                duration = trade.get("duration_ticks", 0)
                feature_values["duration_ticks"].append(duration)

            return feature_values

        winner_features = extract_features(self.winning_trades)
        loser_features = extract_features(self.losing_trades)

        # Compare
        for feature_name in winner_features.keys():
            if feature_name in loser_features:
                winner_values = winner_features[feature_name]
                loser_values = loser_features[feature_name]

                if winner_values and loser_values:
                    winner_avg = statistics.mean(winner_values)
                    loser_avg = statistics.mean(loser_values)

                    diff = winner_avg - loser_avg

                    features[feature_name] = {
                        "winner_avg": winner_avg,
                        "loser_avg": loser_avg,
                        "difference": diff
                    }

                    logger.info(f"\n📊 {feature_name}:")
                    logger.info(f"   Winners: {winner_avg:.4f}")
                    logger.info(f"   Losers:  {loser_avg:.4f}")
                    logger.info(f"   Diff:    {diff:+.4f}")

        return features

    def generate_candidate_strategies(self, entry_features: Dict, exit_features: Dict) -> List[Pattern]:
        """
        Generate candidate strategies based on discovered patterns.

        Strategy: Find the biggest differences between winners and losers,
        and create rules around those conditions.
        """

        logger.info("\n" + "=" * 80)
        logger.info("GENERATING CANDIDATE STRATEGIES")
        logger.info("=" * 80)

        patterns = []

        # Pattern 1: Momentum-based
        if "momentum_1tick" in entry_features:
            feat = entry_features["momentum_1tick"]
            if abs(feat["pct_difference"]) > 5:  # Significant difference
                pattern = Pattern(
                    id="momentum_entry_1",
                    name="Momentum Entry",
                    description=f"Buy when momentum is {'positive' if feat['winner_avg'] > 0 else 'negative'}",
                    conditions={
                        "momentum_1tick": {
                            "min": feat["winner_median"] - 0.01,
                            "max": feat["winner_median"] + 0.01
                        }
                    },
                    exit_rules={
                        "profit_target": exit_features.get("profit_pct", {}).get("winner_avg", 0.02),
                        "stop_loss": exit_features.get("profit_pct", {}).get("loser_avg", -0.02)
                    },
                    confidence=min(abs(feat["pct_difference"]) / 100, 0.9),
                    win_rate=len(self.winning_trades) / len(self.all_trades),
                    avg_return=statistics.mean([t["pnl_pct"] for t in self.winning_trades]),
                    sample_size=len(self.winning_trades),
                    discovered_at=Path("data/chaos_trading").stat().st_mtime if Path("data/chaos_trading").exists() else 0
                )
                patterns.append(pattern)
                logger.info(f"\n✓ Generated: {pattern.name}")
                logger.info(f"  Conditions: {pattern.conditions}")
                logger.info(f"  Confidence: {pattern.confidence:.2%}")

        # Pattern 2: Moving average crossover
        if "vs_sma10" in entry_features:
            feat = entry_features["vs_sma10"]
            if abs(feat["pct_difference"]) > 5:
                pattern = Pattern(
                    id="sma_crossover_1",
                    name="SMA Crossover",
                    description=f"Buy when price is {'above' if feat['winner_avg'] > 0 else 'below'} 10-SMA",
                    conditions={
                        "vs_sma10": {
                            "min": feat["winner_median"] - 0.01,
                            "max": feat["winner_median"] + 0.01
                        }
                    },
                    exit_rules={
                        "profit_target": 0.03,  # 3%
                        "stop_loss": -0.015  # -1.5%
                    },
                    confidence=min(abs(feat["pct_difference"]) / 100, 0.9),
                    win_rate=len(self.winning_trades) / len(self.all_trades),
                    avg_return=statistics.mean([t["pnl_pct"] for t in self.winning_trades]),
                    sample_size=len(self.winning_trades),
                    discovered_at=""
                )
                patterns.append(pattern)
                logger.info(f"\n✓ Generated: {pattern.name}")

        # Pattern 3: Volume-based
        if "volume_vs_avg" in entry_features:
            feat = entry_features["volume_vs_avg"]
            if abs(feat["pct_difference"]) > 10:
                pattern = Pattern(
                    id="volume_surge_1",
                    name="Volume Surge",
                    description=f"Buy on {'high' if feat['winner_avg'] > 0 else 'low'} volume",
                    conditions={
                        "volume_vs_avg": {
                            "min": feat["winner_median"] - 0.2,
                            "max": feat["winner_median"] + 0.2
                        }
                    },
                    exit_rules={
                        "profit_target": 0.025,
                        "stop_loss": -0.01
                    },
                    confidence=min(abs(feat["pct_difference"]) / 100, 0.9),
                    win_rate=len(self.winning_trades) / len(self.all_trades),
                    avg_return=statistics.mean([t["pnl_pct"] for t in self.winning_trades]),
                    sample_size=len(self.winning_trades),
                    discovered_at=""
                )
                patterns.append(pattern)
                logger.info(f"\n✓ Generated: {pattern.name}")

        return patterns

    def save_patterns(self, patterns: List[Pattern]):
        """Save discovered patterns to JSON"""
        output_dir = Path("data/discovered_patterns")
        output_dir.mkdir(parents=True, exist_ok=True)

        patterns_file = output_dir / "patterns.json"

        # Load existing patterns if any
        existing_patterns = []
        if patterns_file.exists():
            with open(patterns_file, "r") as f:
                existing_patterns = json.load(f)

        # Add new patterns
        new_pattern_dicts = [asdict(p) for p in patterns]
        all_patterns = existing_patterns + new_pattern_dicts

        # Save
        with open(patterns_file, "w") as f:
            json.dump(all_patterns, f, indent=2)

        logger.info(f"\n💾 Saved {len(patterns)} patterns to {patterns_file}")
        logger.info(f"   Total patterns in database: {len(all_patterns)}")

    def analyze(self, trades_file: str):
        """Run full analysis pipeline"""
        self.load_trades(trades_file)
        entry_features = self.analyze_entry_conditions()
        exit_features = self.analyze_exit_conditions()
        patterns = self.generate_candidate_strategies(entry_features, exit_features)

        self.save_patterns(patterns)

        logger.info("\n" + "=" * 80)
        logger.info(f"ANALYSIS COMPLETE - Discovered {len(patterns)} candidate strategies")
        logger.info("=" * 80)

        return patterns


def main():
    """Analyze chaos trading results to find patterns"""

    # Find the most recent chaos trading results
    chaos_dir = Path("data/chaos_trading")
    trade_files = sorted(chaos_dir.glob("chaos_trades_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not trade_files:
        logger.error("No chaos trading results found!")
        return

    latest_file = trade_files[0]
    logger.info(f"Analyzing: {latest_file}")

    agent = PatternAnalysisAgent()
    patterns = agent.analyze(str(latest_file))

    return patterns


if __name__ == "__main__":
    main()
