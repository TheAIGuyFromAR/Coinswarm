# Pattern Learning and Optimization System

## Overview

The Pattern Learning System is the intelligence core of Coinswarm. It observes all trades, market conditions, and outcomes to build a library of successful trading patterns. Over time, the system identifies what works, what doesn't, and continuously optimizes strategies through combination, augmentation, and evolutionary algorithms.

**Integration with Memory System**: All patterns are stored as semantic memories in Redis vector database, enabling ultra-fast pattern matching during live trading. Agents use memory retrieval to find similar past situations and apply learned patterns.

**Integration with MARL**: Pattern learning works alongside reinforcement learning - patterns represent explicit knowledge while RL policies capture implicit decision-making. Both are enhanced by the agent memory system.

**See Also**:
- **[Agent Memory System](../architecture/agent-memory-system.md)** - How patterns are stored and retrieved
- **[Multi-Agent Architecture](../agents/multi-agent-architecture.md)** - How agents use patterns

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Trading Execution Layer                       │
│  • Places trades • Records outcomes • Tags with conditions      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Trade Recording System                         │
│  • Captures entry/exit conditions                               │
│  • Stores market state snapshot                                 │
│  • Records sentiment and external factors                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Pattern Extraction Engine                      │
│  • Analyzes winning/losing trades                               │
│  • Extracts common features                                     │
│  • Generates pattern candidates                                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Pattern Library                             │
│  • Stores validated patterns                                    │
│  • Tracks performance metrics                                   │
│  • Maintains version history                                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Pattern Optimization Agent                     │
│  • Combines patterns • Mutates parameters • A/B tests           │
│  • Genetic algorithms • Backtests candidates                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Enhanced Pattern Library                       │
│  • Optimized patterns • Ensemble strategies • Live deployment   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Trade Recording System

**Purpose**: Capture complete context for every trade

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

@dataclass
class TradeRecord:
    """Complete record of a trade and its context"""

    # Trade details
    trade_id: str
    product_id: str
    side: str  # BUY | SELL
    entry_price: float
    entry_time: datetime
    exit_price: Optional[float]
    exit_time: Optional[datetime]
    size: float
    commission: float

    # Outcome
    realized_pnl: Optional[float]
    return_pct: Optional[float]
    hold_duration_seconds: Optional[int]

    # Market conditions at entry
    market_state: MarketState
    technical_indicators: Dict[str, float]
    sentiment_score: float
    volatility: float
    volume_profile: Dict[str, float]
    order_book_imbalance: float

    # External factors
    news_sentiment: Optional[float]
    on_chain_metrics: Optional[Dict[str, float]]
    macro_conditions: Optional[Dict[str, float]]

    # Strategy metadata
    strategy_name: str
    pattern_ids: List[str]  # Patterns that triggered this trade
    confidence_score: float
    agent_reasoning: str

@dataclass
class MarketState:
    """Market snapshot at trade time"""
    price: float
    bid: float
    ask: float
    spread: float
    volume_24h: float
    volatility_24h: float
    trend: str  # UPTREND | DOWNTREND | SIDEWAYS
    support_levels: List[float]
    resistance_levels: List[float]
    recent_high: float
    recent_low: float


class TradeRecorder:
    def __init__(self, storage: TradeStorage):
        self.storage = storage

    async def record_trade_entry(
        self,
        order: Order,
        market_data: MarketSnapshot,
        sentiment: SentimentScore,
        indicators: Dict[str, float],
        strategy: str,
        agent_reasoning: str
    ) -> str:
        """Record a new trade at entry"""

        trade_record = TradeRecord(
            trade_id=str(uuid.uuid4()),
            product_id=order.product_id,
            side=order.side,
            entry_price=order.fill_price,
            entry_time=datetime.utcnow(),
            exit_price=None,
            exit_time=None,
            size=order.filled_size,
            commission=order.commission,
            realized_pnl=None,
            return_pct=None,
            hold_duration_seconds=None,
            market_state=self.extract_market_state(market_data),
            technical_indicators=indicators,
            sentiment_score=sentiment.overall_score,
            volatility=market_data.volatility,
            volume_profile=market_data.volume_profile,
            order_book_imbalance=self.calculate_imbalance(market_data.orderbook),
            news_sentiment=sentiment.news_score,
            on_chain_metrics=None,  # TODO: integrate
            macro_conditions=None,  # TODO: integrate
            strategy_name=strategy,
            pattern_ids=[],  # Set when pattern matches
            confidence_score=0.0,
            agent_reasoning=agent_reasoning
        )

        await self.storage.save(trade_record)
        return trade_record.trade_id

    async def record_trade_exit(
        self,
        trade_id: str,
        exit_order: Order
    ):
        """Update trade record on exit"""

        trade = await self.storage.get(trade_id)

        trade.exit_price = exit_order.fill_price
        trade.exit_time = datetime.utcnow()

        # Calculate outcome
        if trade.side == 'BUY':
            pnl = (trade.exit_price - trade.entry_price) * trade.size
        else:
            pnl = (trade.entry_price - trade.exit_price) * trade.size

        pnl -= (trade.commission + exit_order.commission)

        trade.realized_pnl = pnl
        trade.return_pct = pnl / (trade.entry_price * trade.size)
        trade.hold_duration_seconds = (
            trade.exit_time - trade.entry_time
        ).total_seconds()

        await self.storage.update(trade)
```

---

### 2. Pattern Extraction Engine

**Purpose**: Analyze trades to discover profitable patterns

```python
class PatternExtractionEngine:
    def __init__(self, min_occurrences: int = 10, min_win_rate: float = 0.6):
        self.min_occurrences = min_occurrences
        self.min_win_rate = min_win_rate

    async def extract_patterns(
        self,
        trades: List[TradeRecord],
        lookback_days: int = 30
    ) -> List[Pattern]:
        """Extract patterns from recent trades"""

        # Filter to recent successful trades
        winning_trades = [
            t for t in trades
            if t.realized_pnl and t.realized_pnl > 0
            and self.is_recent(t, lookback_days)
        ]

        # Group by similar conditions
        clusters = self.cluster_trades(winning_trades)

        # Extract pattern from each cluster
        patterns = []
        for cluster in clusters:
            if len(cluster) >= self.min_occurrences:
                pattern = self.create_pattern_from_cluster(cluster)
                if pattern and pattern.win_rate >= self.min_win_rate:
                    patterns.append(pattern)

        return patterns

    def cluster_trades(
        self,
        trades: List[TradeRecord]
    ) -> List[List[TradeRecord]]:
        """Group trades with similar characteristics"""

        # Feature extraction
        features = []
        for trade in trades:
            features.append([
                trade.market_state.trend_encoded,
                trade.technical_indicators['rsi'],
                trade.technical_indicators['macd'],
                trade.sentiment_score,
                trade.volatility,
                trade.order_book_imbalance
            ])

        # K-means clustering
        from sklearn.cluster import KMeans

        n_clusters = min(10, len(trades) // 5)
        kmeans = KMeans(n_clusters=n_clusters)
        labels = kmeans.fit_predict(features)

        # Group by cluster
        clusters = defaultdict(list)
        for trade, label in zip(trades, labels):
            clusters[label].append(trade)

        return list(clusters.values())

    def create_pattern_from_cluster(
        self,
        cluster: List[TradeRecord]
    ) -> Optional[Pattern]:
        """Create a pattern from a cluster of similar trades"""

        # Calculate statistics
        avg_return = np.mean([t.return_pct for t in cluster])
        avg_hold_time = np.mean([t.hold_duration_seconds for t in cluster])
        win_rate = sum(1 for t in cluster if t.realized_pnl > 0) / len(cluster)

        # Extract conditions (ranges)
        conditions = self.extract_conditions(cluster)

        return Pattern(
            pattern_id=str(uuid.uuid4()),
            name=f"Pattern_{conditions['trend']}_{conditions['rsi_range']}",
            conditions=conditions,
            expected_return=avg_return,
            expected_hold_time=avg_hold_time,
            win_rate=win_rate,
            sample_size=len(cluster),
            created_at=datetime.utcnow(),
            last_updated=datetime.utcnow(),
            version=1
        )

    def extract_conditions(
        self,
        cluster: List[TradeRecord]
    ) -> Dict[str, Any]:
        """Extract condition ranges from cluster"""

        rsi_values = [t.technical_indicators['rsi'] for t in cluster]
        macd_values = [t.technical_indicators['macd'] for t in cluster]
        sentiment_values = [t.sentiment_score for t in cluster]

        return {
            'trend': self.most_common([t.market_state.trend for t in cluster]),
            'rsi_range': (np.percentile(rsi_values, 10), np.percentile(rsi_values, 90)),
            'macd_range': (np.percentile(macd_values, 10), np.percentile(macd_values, 90)),
            'sentiment_range': (np.percentile(sentiment_values, 10), np.percentile(sentiment_values, 90)),
            'min_volume_24h': np.percentile([t.market_state.volume_24h for t in cluster], 25),
            'side': self.most_common([t.side for t in cluster])
        }
```

---

### 3. Pattern Library

**Purpose**: Store and manage validated patterns

```python
@dataclass
class Pattern:
    """A trading pattern"""
    pattern_id: str
    name: str
    conditions: Dict[str, Any]
    expected_return: float
    expected_hold_time: float
    win_rate: float
    sample_size: int
    sharpe_ratio: Optional[float]
    max_drawdown: Optional[float]

    # Versioning
    created_at: datetime
    last_updated: datetime
    version: int
    parent_pattern_id: Optional[str]  # For evolved patterns

    # Performance tracking
    live_trades: int = 0
    live_wins: int = 0
    live_losses: int = 0
    live_pnl: float = 0.0

    # Metadata
    tags: List[str] = None
    description: str = ""

    def matches(self, market_state: MarketState, indicators: Dict) -> float:
        """Check if current conditions match pattern, return confidence"""

        confidence_scores = []

        # Check trend
        if market_state.trend == self.conditions['trend']:
            confidence_scores.append(1.0)
        else:
            confidence_scores.append(0.0)

        # Check RSI
        rsi = indicators['rsi']
        rsi_min, rsi_max = self.conditions['rsi_range']
        if rsi_min <= rsi <= rsi_max:
            confidence_scores.append(1.0)
        else:
            # Partial credit based on distance
            distance = min(abs(rsi - rsi_min), abs(rsi - rsi_max))
            confidence_scores.append(max(0, 1 - distance / 10))

        # Check MACD
        macd = indicators['macd']
        macd_min, macd_max = self.conditions['macd_range']
        if macd_min <= macd <= macd_max:
            confidence_scores.append(1.0)
        else:
            distance = min(abs(macd - macd_min), abs(macd - macd_max))
            confidence_scores.append(max(0, 1 - distance / 0.001))

        # Check sentiment
        # ... similar logic

        # Overall confidence
        return np.mean(confidence_scores)


class PatternLibrary:
    def __init__(self, storage: PatternStorage):
        self.storage = storage
        self.patterns: Dict[str, Pattern] = {}

    async def load_patterns(self):
        """Load all patterns from storage"""
        self.patterns = await self.storage.load_all()

    async def add_pattern(self, pattern: Pattern):
        """Add a new pattern to library"""
        self.patterns[pattern.pattern_id] = pattern
        await self.storage.save(pattern)

    async def update_pattern_performance(
        self,
        pattern_id: str,
        trade_outcome: TradeRecord
    ):
        """Update pattern's live performance"""

        pattern = self.patterns[pattern_id]
        pattern.live_trades += 1

        if trade_outcome.realized_pnl > 0:
            pattern.live_wins += 1
        else:
            pattern.live_losses += 1

        pattern.live_pnl += trade_outcome.realized_pnl

        await self.storage.update(pattern)

    async def get_best_patterns(
        self,
        min_sample_size: int = 20,
        min_win_rate: float = 0.6,
        min_sharpe: float = 1.0
    ) -> List[Pattern]:
        """Get top performing patterns"""

        return sorted(
            [
                p for p in self.patterns.values()
                if (p.sample_size >= min_sample_size
                    and p.win_rate >= min_win_rate
                    and (p.sharpe_ratio or 0) >= min_sharpe)
            ],
            key=lambda p: p.sharpe_ratio or 0,
            reverse=True
        )

    def match_patterns(
        self,
        market_state: MarketState,
        indicators: Dict[str, float],
        min_confidence: float = 0.7
    ) -> List[Tuple[Pattern, float]]:
        """Find patterns matching current conditions"""

        matches = []
        for pattern in self.patterns.values():
            confidence = pattern.matches(market_state, indicators)
            if confidence >= min_confidence:
                matches.append((pattern, confidence))

        return sorted(matches, key=lambda x: x[1], reverse=True)
```

---

### 4. Pattern Optimization Agent

**Purpose**: Evolve patterns through combination and genetic algorithms

```python
class PatternOptimizationAgent:
    def __init__(
        self,
        pattern_library: PatternLibrary,
        trade_storage: TradeStorage
    ):
        self.pattern_library = pattern_library
        self.trade_storage = trade_storage

    async def run_optimization_cycle(self):
        """Run one optimization cycle"""

        print("Starting pattern optimization cycle...")

        # Step 1: Prune underperforming patterns
        await self.prune_patterns()

        # Step 2: Combine correlated patterns
        await self.combine_patterns()

        # Step 3: Mutate parameters
        await self.mutate_patterns()

        # Step 4: Backtest new candidates
        await self.backtest_candidates()

        print("Optimization cycle complete")

    async def prune_patterns(self):
        """Remove patterns that perform poorly in live trading"""

        patterns = self.pattern_library.patterns.values()

        for pattern in patterns:
            # Require minimum live trades before pruning
            if pattern.live_trades < 20:
                continue

            # Calculate live win rate
            live_win_rate = pattern.live_wins / pattern.live_trades

            # Prune if significantly worse than expected
            if live_win_rate < pattern.win_rate * 0.7:
                print(f"Pruning pattern {pattern.name}: "
                      f"Expected {pattern.win_rate}, got {live_win_rate}")
                await self.pattern_library.archive_pattern(pattern.pattern_id)

    async def combine_patterns(self):
        """Create ensemble patterns from correlated patterns"""

        patterns = await self.pattern_library.get_best_patterns()

        # Find correlated patterns
        correlations = self.find_correlations(patterns)

        for corr in correlations:
            if corr.strength > 0.8:
                # Create ensemble
                ensemble = self.create_ensemble(
                    corr.pattern_a,
                    corr.pattern_b
                )

                # Backtest
                performance = await self.backtest_pattern(ensemble)

                # Add if better than components
                if performance.sharpe > max(
                    corr.pattern_a.sharpe_ratio,
                    corr.pattern_b.sharpe_ratio
                ):
                    print(f"Created ensemble pattern: {ensemble.name}")
                    await self.pattern_library.add_pattern(ensemble)

    def find_correlations(
        self,
        patterns: List[Pattern]
    ) -> List[Correlation]:
        """Find patterns that often trigger together"""

        # Get trades for each pattern
        pattern_trades = {}
        for pattern in patterns:
            trades = self.trade_storage.get_by_pattern(pattern.pattern_id)
            pattern_trades[pattern.pattern_id] = set(t.trade_id for t in trades)

        # Calculate correlations
        correlations = []
        for i, pattern_a in enumerate(patterns):
            for pattern_b in patterns[i+1:]:
                # Jaccard similarity
                trades_a = pattern_trades[pattern_a.pattern_id]
                trades_b = pattern_trades[pattern_b.pattern_id]

                intersection = len(trades_a & trades_b)
                union = len(trades_a | trades_b)

                if union > 0:
                    similarity = intersection / union

                    if similarity > 0.5:
                        correlations.append(Correlation(
                            pattern_a=pattern_a,
                            pattern_b=pattern_b,
                            strength=similarity
                        ))

        return correlations

    def create_ensemble(
        self,
        pattern_a: Pattern,
        pattern_b: Pattern
    ) -> Pattern:
        """Combine two patterns into an ensemble"""

        # Weight by Sharpe ratio
        weight_a = pattern_a.sharpe_ratio / (
            pattern_a.sharpe_ratio + pattern_b.sharpe_ratio
        )
        weight_b = 1 - weight_a

        # Combine conditions (intersection - must satisfy both)
        combined_conditions = {
            'pattern_a_id': pattern_a.pattern_id,
            'pattern_b_id': pattern_b.pattern_id,
            'pattern_a_weight': weight_a,
            'pattern_b_weight': weight_b,
            'require_both': True
        }

        return Pattern(
            pattern_id=str(uuid.uuid4()),
            name=f"Ensemble_{pattern_a.name}_{pattern_b.name}",
            conditions=combined_conditions,
            expected_return=weight_a * pattern_a.expected_return +
                          weight_b * pattern_b.expected_return,
            expected_hold_time=weight_a * pattern_a.expected_hold_time +
                             weight_b * pattern_b.expected_hold_time,
            win_rate=min(pattern_a.win_rate, pattern_b.win_rate),  # Conservative
            sample_size=0,  # Will be tested
            sharpe_ratio=None,
            max_drawdown=None,
            created_at=datetime.utcnow(),
            last_updated=datetime.utcnow(),
            version=1,
            parent_pattern_id=None,
            tags=['ensemble']
        )

    async def mutate_patterns(self):
        """Generate pattern variations through parameter mutation"""

        patterns = await self.pattern_library.get_best_patterns()

        for pattern in patterns[:10]:  # Top 10
            # Generate mutations
            mutations = [
                self.mutate_rsi_range(pattern),
                self.mutate_sentiment_threshold(pattern),
                self.mutate_hold_time(pattern)
            ]

            for mutated in mutations:
                # Backtest
                performance = await self.backtest_pattern(mutated)

                # Keep if better
                if performance.sharpe > (pattern.sharpe_ratio or 0):
                    print(f"Improved pattern through mutation: {mutated.name}")
                    await self.pattern_library.add_pattern(mutated)

    def mutate_rsi_range(self, pattern: Pattern) -> Pattern:
        """Widen or narrow RSI range"""
        mutated = copy.deepcopy(pattern)
        mutated.pattern_id = str(uuid.uuid4())
        mutated.version = pattern.version + 1
        mutated.parent_pattern_id = pattern.pattern_id

        rsi_min, rsi_max = pattern.conditions['rsi_range']
        # Widen by 10%
        new_min = max(0, rsi_min - 5)
        new_max = min(100, rsi_max + 5)
        mutated.conditions['rsi_range'] = (new_min, new_max)

        return mutated

    async def backtest_pattern(self, pattern: Pattern) -> Performance:
        """Backtest pattern on historical data"""

        # Get historical trades
        all_trades = await self.trade_storage.get_all(days=90)

        # Simulate pattern matching
        matched_trades = []
        for trade in all_trades:
            confidence = pattern.matches(
                trade.market_state,
                trade.technical_indicators
            )
            if confidence >= 0.7:
                matched_trades.append(trade)

        if not matched_trades:
            return Performance(sharpe=0, returns=[], max_drawdown=1)

        # Calculate performance
        returns = [t.return_pct for t in matched_trades]
        sharpe = self.calculate_sharpe(returns)
        max_drawdown = self.calculate_max_drawdown(returns)

        return Performance(
            sharpe=sharpe,
            returns=returns,
            max_drawdown=max_drawdown,
            win_rate=sum(1 for r in returns if r > 0) / len(returns)
        )

    def calculate_sharpe(self, returns: List[float]) -> float:
        """Calculate Sharpe ratio"""
        if not returns:
            return 0
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        return (mean_return / std_return) * np.sqrt(252) if std_return > 0 else 0
```

---

## Pattern Types

### 1. Technical Patterns
- Trend-following (moving average crossovers)
- Mean reversion (RSI oversold/overbought)
- Breakout (support/resistance breaks)
- Momentum (MACD divergences)

### 2. Sentiment Patterns
- News-driven (positive sentiment spikes)
- Social momentum (Twitter/Reddit buzz)
- Contrarian (extreme fear/greed)

### 3. Temporal Patterns
- Time-of-day effects
- Day-of-week patterns
- Seasonal trends

### 4. Cross-Asset Patterns
- Correlation trades (BTC leads ETH)
- Pairs trading
- Risk-on/risk-off rotations

### 5. Ensemble Patterns
- Multiple signal confirmation
- Weighted combinations
- Hierarchical strategies

---

## Performance Metrics

```python
class PatternMetrics:
    @staticmethod
    def calculate_all(trades: List[TradeRecord]) -> Dict[str, float]:
        returns = [t.return_pct for t in trades]

        return {
            'total_trades': len(trades),
            'win_rate': sum(1 for r in returns if r > 0) / len(returns),
            'avg_return': np.mean(returns),
            'median_return': np.median(returns),
            'total_return': sum(returns),
            'sharpe_ratio': PatternMetrics.sharpe(returns),
            'sortino_ratio': PatternMetrics.sortino(returns),
            'max_drawdown': PatternMetrics.max_drawdown(returns),
            'profit_factor': PatternMetrics.profit_factor(trades),
            'avg_hold_time': np.mean([t.hold_duration_seconds for t in trades])
        }

    @staticmethod
    def sharpe(returns: List[float]) -> float:
        return (np.mean(returns) / np.std(returns)) * np.sqrt(252)

    @staticmethod
    def sortino(returns: List[float]) -> float:
        downside = [r for r in returns if r < 0]
        downside_std = np.std(downside) if downside else 0.0001
        return (np.mean(returns) / downside_std) * np.sqrt(252)

    @staticmethod
    def max_drawdown(returns: List[float]) -> float:
        cumulative = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = cumulative - running_max
        return abs(np.min(drawdowns))
```

---

## Storage Schema

```sql
-- Trades table
CREATE TABLE trades (
    trade_id UUID PRIMARY KEY,
    product_id VARCHAR(20),
    side VARCHAR(4),
    entry_price DECIMAL(20, 8),
    entry_time TIMESTAMP,
    exit_price DECIMAL(20, 8),
    exit_time TIMESTAMP,
    size DECIMAL(20, 8),
    realized_pnl DECIMAL(20, 8),
    return_pct DECIMAL(10, 6),

    -- Market conditions (JSONB for flexibility)
    market_state JSONB,
    technical_indicators JSONB,
    sentiment_data JSONB,

    -- Strategy info
    strategy_name VARCHAR(100),
    pattern_ids TEXT[],
    confidence_score DECIMAL(5, 4),
    agent_reasoning TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);

-- Patterns table
CREATE TABLE patterns (
    pattern_id UUID PRIMARY KEY,
    name VARCHAR(200),
    conditions JSONB,
    expected_return DECIMAL(10, 6),
    expected_hold_time INTEGER,
    win_rate DECIMAL(5, 4),
    sample_size INTEGER,
    sharpe_ratio DECIMAL(10, 4),

    -- Live performance
    live_trades INTEGER DEFAULT 0,
    live_wins INTEGER DEFAULT 0,
    live_pnl DECIMAL(20, 8) DEFAULT 0,

    -- Versioning
    version INTEGER,
    parent_pattern_id UUID,

    created_at TIMESTAMP,
    last_updated TIMESTAMP
);

-- Pattern performance (time series)
CREATE TABLE pattern_performance (
    id SERIAL PRIMARY KEY,
    pattern_id UUID,
    date DATE,
    trades_count INTEGER,
    wins INTEGER,
    losses INTEGER,
    total_pnl DECIMAL(20, 8),
    sharpe DECIMAL(10, 4),

    FOREIGN KEY (pattern_id) REFERENCES patterns(pattern_id)
);
```

---

## Deployment Strategy

### Phase 1: Learning (Weeks 1-4)
- Record all trades with full context
- Build initial pattern library (100+ patterns)
- No optimization yet, just observation

### Phase 2: Validation (Weeks 5-8)
- Backtest discovered patterns
- Paper trade top patterns
- Measure live vs backtest performance

### Phase 3: Optimization (Weeks 9-12)
- Enable pattern combination
- Enable parameter mutation
- Run nightly optimization cycles

### Phase 4: Production (Week 13+)
- Deploy best patterns to live trading
- Continuous learning and optimization
- A/B testing new patterns

---

**Last Updated**: 2025-10-31
**Status**: Planning Phase
**Next**: Architecture Overview Document
