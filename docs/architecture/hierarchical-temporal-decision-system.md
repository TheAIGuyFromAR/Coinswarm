# Hierarchical Temporal Decision System

## Overview

Coinswarm implements a **three-layer cognitive hierarchy** with temporal division of labor: **Planners** (strategic alignment), **Committee** (tactical ensemble), and **Memory Optimizer** (execution adaptation). This architecture enables the system to operate coherently across multiple timescales—from macro sentiment shifts (weeks) to microstructure execution (seconds)—while maintaining quorum governance at all levels.

**Key Innovation**: Separates concerns by temporal horizon, allowing each layer to optimize within its domain without interfering with others, yet still maintaining global alignment through feedback loops.

**Status**: Production Specification (Integrated with Quorum System)

**Related Documents**:
- [Data Feeds Architecture](data-feeds-architecture.md) - Complete specification of data sources, cadences, and storage for each layer
- [Quorum Memory System](quorum-memory-system.md) - Production memory governance

---

## 1. Temporal Division of Labor

**Note**: Each layer consumes data at different cadences and from different sources. See [Data Feeds Architecture](data-feeds-architecture.md) for complete details on data ingestion, storage, and distribution.

### Three-Layer Hierarchy

| Layer | Horizon | Core Driver | Responsible For |
|-------|---------|-------------|-----------------|
| **Planners** | Weeks–Months | Macro themes, sentiment trends, liquidity regimes | Adjust committee weights, goals, thresholds |
| **Committee** | Hours–Days | News flow, funding rates, positioning shifts | Ensemble of domain agents with adaptive weighting |
| **Memory Optimizer** | Seconds–Minutes | Order-book microstructure, volatility bursts | Pattern recall and execution heuristics |

### Separation of Concerns

```
┌─────────────────────────────────────────────────────────────────┐
│                        PLANNERS                                  │
│  Strategic Alignment (Weeks–Months)                              │
│  • Monitor macro sentiment (Twitter, news, funding)             │
│  • Detect regime shifts (risk-on/off, range-bound)              │
│  • Adjust committee weights w_agent[t]                           │
│  • Update rule thresholds (vol limits, risk scaling)            │
│  Update: Hourly to Daily                                         │
└────────────────────────┬────────────────────────────────────────┘
                         │ Weights & Thresholds
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                        COMMITTEE                                 │
│  Tactical Ensemble (Hours–Days)                                  │
│  • Trend Agent × w_trend                                         │
│  • Mean-Reversion Agent × w_mean_rev                             │
│  • Execution Agent × w_exec                                      │
│  • Risk Agent × w_risk                                           │
│  • Arbitrage Agent × w_arb                                       │
│  Aggregate: action = Σ w_i * agent_i.action                      │
└────────────────────────┬────────────────────────────────────────┘
                         │ Trade Execution
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MEMORY OPTIMIZER                              │
│  Execution Adaptation (Seconds–Minutes)                          │
│  • Pattern recall (breakout probability, slippage models)       │
│  • Adjust cluster weights (recent pattern performance)           │
│  • Tune decay rates (episodic entry aging)                       │
│  • Immediate action biases (size up/down)                        │
│  Update: Continuous (after every trade)                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Planner Mechanics

### Purpose

**Strategic alignment** across multiple timescales. Planners observe macro trends and adjust the tactical blend of the committee to match current market regime.

### Inputs

**Aggregated Sentiment Signals**:
```python
class PlannerInputs:
    # Social sentiment
    twitter_sentiment: SentimentTimeSeries  # 7-day rolling
    reddit_sentiment: SentimentTimeSeries
    news_embeddings: np.ndarray  # Semantic clusters

    # Market positioning
    funding_rate_deltas: Dict[str, float]  # Change in funding rates
    open_interest_trends: Dict[str, float]  # OI growth/decline
    long_short_ratios: Dict[str, float]

    # Cross-asset correlations
    btc_eth_corr: float
    crypto_spx_corr: float
    crypto_dxy_corr: float  # Dollar index

    # Liquidity regimes
    bid_ask_spread_avg: float
    depth_at_top: float
    price_impact_curve: Callable

    # Macro indicators
    vix: float
    treasury_yields: Dict[str, float]
```

**Collection Frequency**: Every 1-6 hours (depends on signal)

### Outputs

**Committee Configuration**:
```python
class PlannerOutputs:
    # Committee weights (sum to 1.0)
    committee_weights: Dict[str, float] = {
        'trend_agent': 0.4,
        'mean_rev_agent': 0.2,
        'execution_agent': 0.15,
        'risk_agent': 0.15,
        'arb_agent': 0.10
    }

    # Rule thresholds
    thresholds: Dict[str, Any] = {
        'vol_bucket_limits': {
            'low': (0, 0.02),    # Allow larger size
            'med': (0.02, 0.05), # Normal size
            'high': (0.05, inf)  # Reduce size
        },
        'risk_scaling': 0.8,     # 0-1, scales position limits
        'stop_loss_mult': 1.2,   # Multiplier on standard stops
        'take_profit_mult': 0.9  # Loosen take-profit in trends
    }

    # Directional bias (meta-features)
    regime_tags: List[str] = ['risk-on', 'trending']
    # Options: risk-on, risk-off, range-bound, high-vol, low-vol

    # Validity period
    valid_until: datetime  # When these weights expire
```

**Example Scenario**:
```python
# When planners detect "risk-on" + "trending up" regime:
PlannerOutputs(
    committee_weights={
        'trend_agent': 0.50,      # Increased (from 0.40)
        'mean_rev_agent': 0.10,   # Decreased (from 0.20)
        'execution_agent': 0.15,
        'risk_agent': 0.15,
        'arb_agent': 0.10
    },
    thresholds={
        'risk_scaling': 1.0,       # Full risk
        'take_profit_mult': 1.5    # Looser take-profits (let winners run)
    },
    regime_tags=['risk-on', 'trending'],
    valid_until=datetime.now() + timedelta(hours=24)
)
```

### Update Cadence

**Frequency**: Hourly to daily (depending on signal volatility)

**Trigger Conditions**:
- Scheduled (e.g., every 6 hours)
- Event-driven (large funding rate flip, major news)
- Performance-driven (Sharpe drops below threshold)

### Evaluation Horizon

**Metrics** (rolling window):
- 3–14 day PnL slope
- Sharpe ratio
- Max drawdown
- Regime stability (how long in current regime)
- Prediction accuracy (did regime tags match reality?)

**Optimization Target**:
```python
def planner_objective(outputs: PlannerOutputs) -> float:
    """
    Evaluate planner proposal on historical data

    Simulate using proposed weights over last 14 days
    """
    # Backtest with proposed committee weights
    pnl_history = backtest_with_weights(
        weights=outputs.committee_weights,
        thresholds=outputs.thresholds,
        start=now() - timedelta(days=14),
        end=now()
    )

    # Compute metrics
    sharpe = compute_sharpe(pnl_history)
    drawdown = compute_max_drawdown(pnl_history)
    regime_match = measure_regime_stability(outputs.regime_tags)

    # Combined score
    return (
        sharpe * 1.0
        - drawdown * 2.0  # Penalize drawdown heavily
        + regime_match * 0.5
    )
```

### Governance: Quorum Voting

**Critical**: Planner proposals flow through the **same quorum voting** system as memory updates.

**Why**: Prevents rogue planner from destabilizing the entire system.

**Process**:
```python
# Planner generates proposal
proposal = PlannerProposal(
    change_type='committee_weights',
    new_weights=proposed_weights,
    new_thresholds=proposed_thresholds,
    regime_tags=['risk-on', 'trending'],
    justification={
        'twitter_sentiment': 0.75,  # Bullish
        'funding_rate': 0.05,       # Positive carry
        'btc_eth_corr': 0.92        # Strong correlation
    }
)

# Submit to quorum
nats_client.publish('planner.propose', proposal)

# Memory Managers evaluate
# (Use different criteria than memory updates)
for manager in memory_managers:
    vote = manager.evaluate_planner_proposal(proposal)
    # Checks:
    # - Weights sum to 1.0
    # - Thresholds within safe bounds
    # - Backtest shows improvement
    # - Regime tags consistent with current data
    nats_client.publish('mem.vote', vote)

# Coordinator counts votes
if quorum_reached(votes) and all_votes_agree:
    # Apply new committee configuration
    committee.update_weights(proposal.new_weights)
    committee.update_thresholds(proposal.new_thresholds)
    committee.set_regime_tags(proposal.regime_tags)

    # Broadcast commit
    nats_client.publish('mem.commit', {
        'type': 'planner_config',
        'proposal_id': proposal.id,
        'decision': 'ACCEPT'
    })
```

**Manager Evaluation (Deterministic)**:
```python
class MemoryManager:
    def evaluate_planner_proposal(self, proposal: PlannerProposal) -> Vote:
        """Evaluate planner configuration proposal"""

        checks = [
            self.check_weights_valid(proposal.new_weights),
            self.check_thresholds_safe(proposal.new_thresholds),
            self.check_backtest_improvement(proposal),
            self.check_regime_consistency(proposal.regime_tags)
        ]

        failures = [reason for ok, reason in checks if not ok]

        if failures:
            return Vote(decision='REJECT', reasons=failures)
        else:
            return Vote(decision='ACCEPT', reasons=[])

    def check_weights_valid(self, weights: Dict[str, float]) -> Tuple[bool, str]:
        """Ensure weights are valid"""
        # Check sum to 1.0
        if abs(sum(weights.values()) - 1.0) > 1e-6:
            return False, f"Weights sum to {sum(weights.values())}, not 1.0"

        # Check all non-negative
        if any(w < 0 for w in weights.values()):
            return False, "Negative weights detected"

        # Check no single agent dominates too much
        if any(w > 0.7 for w in weights.values()):
            return False, "Single agent weight > 0.7 (too concentrated)"

        return True, None

    def check_backtest_improvement(self, proposal: PlannerProposal) -> Tuple[bool, str]:
        """Backtest proposed weights on recent history"""

        # Simulate last 7 days with proposed weights
        proposed_pnl = backtest_with_weights(
            weights=proposal.new_weights,
            thresholds=proposal.new_thresholds,
            days=7
        )

        # Compare to current configuration
        current_pnl = backtest_with_weights(
            weights=committee.current_weights,
            thresholds=committee.current_thresholds,
            days=7
        )

        # Compute Sharpe improvement
        proposed_sharpe = compute_sharpe(proposed_pnl)
        current_sharpe = compute_sharpe(current_pnl)

        improvement = proposed_sharpe - current_sharpe

        if improvement < 0.1:  # Require at least 0.1 Sharpe improvement
            return False, f"Insufficient improvement: ΔSharpe={improvement:.3f}"

        return True, None
```

---

## 3. Committee (Tactical Ensemble)

### Purpose

**Aggregate decisions** from specialized domain agents, weighted by planner-determined importance.

### Agent Types

**1. Trend Agent**
- Detects and follows momentum
- Uses moving average crossovers, MACD, ADX
- High weight during trending regimes

**2. Mean-Reversion Agent**
- Identifies overbought/oversold conditions
- Uses RSI, Bollinger Bands, Z-scores
- High weight during range-bound regimes

**3. Execution Agent**
- Optimizes order placement and timing
- Monitors slippage, fill rates, time-to-fill
- Always active (base weight)

**4. Risk Agent**
- Monitors portfolio risk and suggests hedges
- Uses VaR, correlation matrices, tail risk
- Increased weight during high volatility

**5. Arbitrage Agent**
- Identifies cross-exchange or cross-asset opportunities
- Monitors funding rates, basis spreads
- Opportunistic (low base weight)

### Aggregation

**Weighted Vote**:
```python
class Committee:
    def decide_action(self, state: MarketState) -> Action:
        """Aggregate decisions from all agents"""

        # Get votes from each agent
        votes = {}
        for agent_name, agent in self.agents.items():
            votes[agent_name] = agent.vote(state)
            # Returns: (action, confidence)

        # Get current weights (from planner)
        weights = self.get_current_weights()

        # Weighted aggregation
        action_scores = defaultdict(float)
        for agent_name, (action, confidence) in votes.items():
            weight = weights[agent_name]
            action_scores[action] += weight * confidence

        # Select highest-scoring action
        best_action = max(action_scores.items(), key=lambda x: x[1])

        return Action(
            type=best_action[0],
            confidence=best_action[1],
            attribution={
                agent: votes[agent][1] * weights[agent]
                for agent in self.agents.keys()
            }
        )
```

**Example**:
```python
# State: BTC trending up, but RSI overbought
state = MarketState(
    price=45000,
    trend='up',
    rsi=72,  # Overbought
    macd_signal='buy',
    volatility=0.03
)

# Agent votes
votes = {
    'trend_agent': (Action.BUY, confidence=0.8),
    'mean_rev_agent': (Action.SELL, confidence=0.6),  # RSI high
    'execution_agent': (Action.HOLD, confidence=0.3),
    'risk_agent': (Action.HOLD, confidence=0.4),
    'arb_agent': (Action.HOLD, confidence=0.1)
}

# Current weights (trending regime)
weights = {
    'trend_agent': 0.50,
    'mean_rev_agent': 0.10,
    'execution_agent': 0.15,
    'risk_agent': 0.15,
    'arb_agent': 0.10
}

# Aggregated scores
action_scores = {
    Action.BUY:  0.50*0.8 = 0.40,           # From trend agent
    Action.SELL: 0.10*0.6 = 0.06,           # From mean-rev agent
    Action.HOLD: 0.15*0.3 + 0.15*0.4 + 0.10*0.1 = 0.115
}

# Result: BUY wins (trend dominates in trending regime)
final_action = Action.BUY
confidence = 0.40
attribution = {
    'trend_agent': 0.40,    # Dominant
    'mean_rev_agent': 0.06, # Minor dissent
    'risk_agent': 0.06,
    'execution_agent': 0.045,
    'arb_agent': 0.01
}
```

### Dynamic Weight Adjustment

**Planners update weights based on regime**:

| Regime | Trend | Mean-Rev | Exec | Risk | Arb |
|--------|-------|----------|------|------|-----|
| Trending Up | 0.50 | 0.10 | 0.15 | 0.15 | 0.10 |
| Range-Bound | 0.15 | 0.45 | 0.15 | 0.15 | 0.10 |
| High Volatility | 0.20 | 0.15 | 0.15 | 0.40 | 0.10 |
| Low Liquidity | 0.20 | 0.20 | 0.30 | 0.25 | 0.05 |

---

## 4. Memory Optimizer (Execution-Level Adaptation)

### Purpose

**Real-time execution tuning** based on transient microstructure patterns.

### Operates Continuously

Unlike Planners (hourly) and Committee (per tick), the Memory Optimizer runs **after every trade** to refine execution.

### What It Learns

**Transient Relationships**:
1. **Breakout Probability** after funding rate flips
2. **Slippage Models** vs spread width and order size
3. **Micro-Trend Exhaustion** (5-min reversals)
4. **Fill Quality** (partial fills, queue position)
5. **Volatility Clustering** (GARCH-like effects)

### What It Adjusts

**Local Parameters** (no global impact):
```python
class MemoryOptimizer:
    def optimize_after_trade(self, trade: TradeOutcome):
        """Refine execution heuristics after observing outcome"""

        # 1. Adjust pattern cluster weights
        if trade.pnl > 0:
            # Increase weight of patterns that led to this trade
            for pattern_id in trade.pattern_ids:
                self.increase_pattern_weight(pattern_id, delta=0.05)
        else:
            # Decrease weight
            for pattern_id in trade.pattern_ids:
                self.decrease_pattern_weight(pattern_id, delta=0.03)

        # 2. Adjust episodic decay rates
        if trade.regime_changed_during_hold:
            # Faster decay for cross-regime memories
            self.set_decay_rate(trade.entry_regime, faster=True)

        # 3. Immediate action biases
        if trade.slippage_bps > expected_slippage * 1.5:
            # Size down next time in similar conditions
            self.set_size_bias(trade.conditions, bias=0.8)

        # 4. Update slippage model
        self.slippage_model.update(
            spread=trade.spread,
            size=trade.size,
            observed_slip=trade.slippage_bps
        )
```

**Example: Slippage Model**:
```python
class SlippageModel:
    """Learn relationship between spread, size, and slippage"""

    def __init__(self):
        self.observations = []

    def update(self, spread: float, size: float, observed_slip: float):
        self.observations.append({
            'spread': spread,
            'size': size,
            'slip': observed_slip,
            'timestamp': time.time()
        })

        # Keep last 1000 observations
        if len(self.observations) > 1000:
            self.observations = self.observations[-1000:]

    def predict(self, spread: float, size: float) -> float:
        """Predict slippage for given spread and size"""

        # Find similar past observations (kNN)
        similar = sorted(
            self.observations,
            key=lambda x: abs(x['spread'] - spread) + abs(x['size'] - size)
        )[:10]

        # Average their slippage
        return np.mean([obs['slip'] for obs in similar])
```

### No Quorum Approval Needed

**Key**: Memory Optimizer adjustments are **local and bounded**.

They don't change global parameters like committee weights or safety thresholds, so they don't require quorum approval.

**Governance Boundary**:
```python
# These DO require quorum (global impact):
- committee_weights
- risk_thresholds
- pattern promotion/deprecation

# These DON'T require quorum (local tuning):
- episodic entry decay rates
- pattern cluster weights (within bounds)
- immediate size biases (within safety limits)
- slippage model parameters
```

**Safety Constraint**:
```python
# Even without quorum, Memory Optimizer is bounded
MAX_SIZE_BIAS = 0.5  # Can't reduce size below 50%
MAX_WEIGHT_DELTA = 0.1  # Can't change weight by more than 10%
MAX_DECAY_MULT = 2.0  # Can't decay faster than 2x normal
```

---

## 5. Feedback Loop

### Complete System Flow

```
1. PLANNERS observe macro environment
   ↓
   Generate committee weight proposal
   ↓
   Submit to quorum voting
   ↓
   If approved: Update committee configuration

2. COMMITTEE receives new weights and thresholds
   ↓
   For each market tick:
     - Each agent votes (action, confidence)
     - Aggregate with current weights
     - Select best action
   ↓
   Execute trade

3. MEMORY OPTIMIZER observes trade outcome
   ↓
   Update execution heuristics:
     - Pattern weights
     - Decay rates
     - Size biases
     - Slippage model
   ↓
   No approval needed (local adjustments)

4. SELF-REFLECTION LAYER monitors all three
   ↓
   If alignment poor:
     - Trigger planner re-optimization
     - Adjust committee coordination
     - Reset memory biases
```

### Self-Reflection Layer

**Purpose**: Monitor alignment across all three layers

**Metrics**:
```python
class SelfReflectionMetrics:
    # Planner effectiveness
    regime_prediction_accuracy: float  # Did regime tags match?
    weight_stability: float  # How often do weights change?
    backtest_vs_live_gap: float  # Backtest Sharpe - Live Sharpe

    # Committee coordination
    vote_entropy: float  # How much agents disagree
    attribution_concentration: float  # Is one agent dominating?
    action_flip_rate: float  # Frequency of reversals

    # Memory-committee alignment
    memory_hit_rate: float  # Are patterns matching?
    execution_quality: float  # Actual vs expected slippage
    pattern_win_rate: float  # Are memory patterns profitable?
```

**Intervention Triggers**:
```python
class SelfReflectionLayer:
    def check_alignment(self) -> List[str]:
        """Detect misalignment and trigger interventions"""

        issues = []

        # Planner issues
        if self.metrics.backtest_vs_live_gap > 0.5:
            issues.append('planner_overfit')
            self.trigger_planner_reoptimization()

        if self.metrics.regime_prediction_accuracy < 0.6:
            issues.append('regime_mismatch')
            self.update_regime_detector()

        # Committee issues
        if self.metrics.vote_entropy > 2.0:
            issues.append('committee_disagreement')
            self.increase_coordination()

        if self.metrics.attribution_concentration > 0.8:
            issues.append('single_agent_dominance')
            self.diversify_weights()

        # Memory issues
        if self.metrics.memory_hit_rate < 0.3:
            issues.append('memory_mismatch')
            self.refresh_patterns()

        if self.metrics.pattern_win_rate < 0.5:
            issues.append('bad_patterns')
            self.deprecate_underperformers()

        return issues
```

**Interventions**:
```python
def trigger_planner_reoptimization(self):
    """Force planners to generate new proposal"""
    planner_proposal = planners.generate_emergency_proposal(
        reason='backtest_live_gap',
        constraints={'conservative': True}
    )
    # Submit to quorum as usual

def refresh_patterns(self):
    """Force pattern maintenance cycle"""
    pattern_maintenance.run_now()
    # Re-cluster episodic memories
    # Update pattern statistics

def deprecate_underperformers(self):
    """Remove patterns with poor live performance"""
    for pattern in pattern_library.get_all():
        if pattern.live_win_rate < 0.45:  # Below random
            pattern.disable()
            log_warning(f"Pattern {pattern.id} deprecated by self-reflection")
```

---

## 6. Example Scenarios

### Scenario A: Bullish Sentiment Shift

**Context**: Twitter sentiment goes bullish, funding rates positive, BTC/ETH correlation high

**Planner Response**:
```python
# Day 1: Planner detects bullish shift
planner_proposal = PlannerProposal(
    committee_weights={
        'trend_agent': 0.55,      # Increase trend following
        'mean_rev_agent': 0.05,   # Reduce mean reversion
        'execution_agent': 0.15,
        'risk_agent': 0.15,
        'arb_agent': 0.10
    },
    thresholds={
        'take_profit_mult': 1.8,  # Looser take-profits
        'stop_loss_mult': 1.0     # Standard stops
    },
    regime_tags=['risk-on', 'trending', 'bullish']
)

# Submit to quorum → Approved
```

**Committee Behavior**:
```python
# Next 3-7 days: Committee follows trends aggressively
# Trend agent has 55% influence
# Most trades are BUY with longer hold times

example_tick = {
    'trend_vote': (BUY, 0.9),
    'mean_rev_vote': (HOLD, 0.3),  # Quiet
    'risk_vote': (HOLD, 0.2)
}

# Aggregated action: BUY (trend dominates)
```

**Memory Optimizer**:
```python
# Observes that breakouts after funding flips are profitable
# Increases weight of "breakout" pattern cluster
# Reduces slippage estimate (liquidity is good in uptrend)
# Biases size up when trend patterns match
```

**Outcome**: System captures uptrend efficiently

---

### Scenario B: Volatility Spike

**Context**: VIX spikes, spreads widen, sudden drawdown

**Planner Response**:
```python
# Immediate: Planner detects high-vol regime
planner_proposal = PlannerProposal(
    committee_weights={
        'trend_agent': 0.20,      # Reduce trend (whipsaws likely)
        'mean_rev_agent': 0.15,
        'execution_agent': 0.20,  # Increase execution focus
        'risk_agent': 0.40,       # Increase risk management
        'arb_agent': 0.05
    },
    thresholds={
        'risk_scaling': 0.5,      # Half normal size
        'stop_loss_mult': 0.8     # Tighter stops
    },
    regime_tags=['high-vol', 'defensive']
)
```

**Committee Behavior**:
```python
# Risk agent now has 40% influence
# Most decisions are HOLD or size-reduction

example_tick = {
    'trend_vote': (BUY, 0.7),   # Still sees uptrend
    'risk_vote': (SELL, 0.9),   # But risk too high
    'exec_vote': (HOLD, 0.5)
}

# Aggregated action: SELL or HOLD (risk dominates)
```

**Memory Optimizer**:
```python
# Observes high slippage during volatility
# Updates slippage model with wider spreads
# Increases decay rate for old patterns (regime changed)
# Biases size down in similar conditions
```

**Outcome**: System reduces risk exposure, avoids whipsaws

---

### Scenario C: Range-Bound Market

**Context**: Low volatility, tight ranges, no clear trend

**Planner Response**:
```python
planner_proposal = PlannerProposal(
    committee_weights={
        'trend_agent': 0.10,      # Reduce trend (no trend to follow)
        'mean_rev_agent': 0.50,   # Increase mean reversion
        'execution_agent': 0.15,
        'risk_agent': 0.15,
        'arb_agent': 0.10
    },
    thresholds={
        'take_profit_mult': 0.6,  # Take profits quickly
        'stop_loss_mult': 1.0
    },
    regime_tags=['range-bound', 'low-vol']
)
```

**Committee Behavior**:
```python
# Mean-reversion agent has 50% influence
# Trades at support/resistance levels

example_tick = {
    'mean_rev_vote': (BUY, 0.8),   # Oversold
    'trend_vote': (HOLD, 0.2),     # No trend
    'risk_vote': (HOLD, 0.3)
}

# Aggregated action: BUY (mean-reversion dominates)
```

**Memory Optimizer**:
```python
# Observes that micro-trends exhaust quickly
# Increases weight on "reversal" pattern cluster
# Tunes take-profit levels tighter
```

**Outcome**: System scalps range effectively

---

## 7. Implementation Details

### Planner Class

```python
class Planner:
    def __init__(self, config):
        self.config = config
        self.sentiment_aggregator = SentimentAggregator()
        self.regime_detector = RegimeDetector()
        self.backtest_engine = BacktestEngine()

    async def generate_proposal(self) -> PlannerProposal:
        """Generate new committee configuration proposal"""

        # Collect inputs
        inputs = await self.collect_inputs()

        # Detect current regime
        regime = self.regime_detector.detect(inputs)

        # Propose weights for this regime
        weights = self.propose_weights(regime)

        # Propose thresholds
        thresholds = self.propose_thresholds(regime)

        # Backtest proposal
        backtest_result = self.backtest_engine.evaluate(
            weights, thresholds, days=14
        )

        if backtest_result.sharpe < self.config.min_sharpe:
            # Reject own proposal
            return None

        # Create proposal
        return PlannerProposal(
            committee_weights=weights,
            thresholds=thresholds,
            regime_tags=regime.tags,
            justification={
                'sentiment': inputs.twitter_sentiment,
                'funding': inputs.funding_rate_deltas,
                'backtest_sharpe': backtest_result.sharpe
            }
        )

    async def collect_inputs(self) -> PlannerInputs:
        """Gather all input signals"""

        return PlannerInputs(
            twitter_sentiment=await self.sentiment_aggregator.get_twitter(),
            reddit_sentiment=await self.sentiment_aggregator.get_reddit(),
            funding_rate_deltas=await self.get_funding_deltas(),
            open_interest_trends=await self.get_oi_trends(),
            # ... etc
        )

    def propose_weights(self, regime: Regime) -> Dict[str, float]:
        """Propose committee weights based on regime"""

        if 'trending' in regime.tags:
            return {
                'trend_agent': 0.50,
                'mean_rev_agent': 0.10,
                'execution_agent': 0.15,
                'risk_agent': 0.15,
                'arb_agent': 0.10
            }
        elif 'range-bound' in regime.tags:
            return {
                'trend_agent': 0.10,
                'mean_rev_agent': 0.50,
                'execution_agent': 0.15,
                'risk_agent': 0.15,
                'arb_agent': 0.10
            }
        elif 'high-vol' in regime.tags:
            return {
                'trend_agent': 0.20,
                'mean_rev_agent': 0.15,
                'execution_agent': 0.20,
                'risk_agent': 0.40,
                'arb_agent': 0.05
            }
        else:
            # Default
            return {
                'trend_agent': 0.30,
                'mean_rev_agent': 0.25,
                'execution_agent': 0.15,
                'risk_agent': 0.20,
                'arb_agent': 0.10
            }
```

### Committee Class

```python
class Committee:
    def __init__(self):
        self.agents = {
            'trend_agent': TrendAgent(),
            'mean_rev_agent': MeanReversionAgent(),
            'execution_agent': ExecutionAgent(),
            'risk_agent': RiskAgent(),
            'arb_agent': ArbitrageAgent()
        }

        # Default weights (will be updated by planner)
        self.current_weights = {
            'trend_agent': 0.30,
            'mean_rev_agent': 0.25,
            'execution_agent': 0.15,
            'risk_agent': 0.20,
            'arb_agent': 0.10
        }

        self.current_thresholds = {}
        self.regime_tags = []

    def update_configuration(self, proposal: PlannerProposal):
        """Apply approved planner configuration"""
        self.current_weights = proposal.committee_weights
        self.current_thresholds = proposal.thresholds
        self.regime_tags = proposal.regime_tags

        log_info(f"Committee reconfigured: {self.regime_tags}")

    def decide_action(self, state: MarketState) -> Action:
        """Aggregate agent votes weighted by current configuration"""

        votes = {}
        for agent_name, agent in self.agents.items():
            votes[agent_name] = agent.vote(state)

        # Weighted aggregation
        action_scores = defaultdict(float)
        for agent_name, (action, confidence) in votes.items():
            weight = self.current_weights[agent_name]
            action_scores[action] += weight * confidence

        best_action = max(action_scores.items(), key=lambda x: x[1])

        return Action(
            type=best_action[0],
            confidence=best_action[1],
            attribution={
                agent: votes[agent][1] * self.current_weights[agent]
                for agent in self.agents.keys()
            },
            regime_tags=self.regime_tags
        )
```

---

## 8. Configuration

```yaml
planners:
  count: 2  # Redundant planners for robustness
  update_cadence_hours: 6
  evaluation_horizon_days: 14
  min_sharpe_threshold: 1.0
  backtest_lookback_days: 90

  # Regime detection
  regime_detector:
    sentiment_window_days: 7
    volatility_window_hours: 24
    correlation_window_days: 30

committee:
  agents:
    - trend_agent
    - mean_rev_agent
    - execution_agent
    - risk_agent
    - arb_agent

  # Default weights (overridden by planner)
  default_weights:
    trend_agent: 0.30
    mean_rev_agent: 0.25
    execution_agent: 0.15
    risk_agent: 0.20
    arb_agent: 0.10

memory_optimizer:
  update_frequency: after_every_trade
  max_size_bias: 0.5
  max_weight_delta: 0.1
  max_decay_multiplier: 2.0
  slippage_model_window: 1000

self_reflection:
  check_frequency_hours: 1
  intervention_thresholds:
    backtest_live_gap: 0.5
    regime_accuracy: 0.6
    vote_entropy: 2.0
    attribution_concentration: 0.8
    memory_hit_rate: 0.3
    pattern_win_rate: 0.5
```

---

## 9. Metrics and Dashboards

### Planner Metrics

```python
planner_proposals_total = Counter('planner_proposals_total', 'Proposals generated')
planner_approvals_total = Counter('planner_approvals_total', 'Proposals approved by quorum')
planner_backtest_sharpe = Gauge('planner_backtest_sharpe', 'Backtest Sharpe of proposal')
planner_live_sharpe = Gauge('planner_live_sharpe', 'Live Sharpe with current weights')
```

### Committee Metrics

```python
committee_vote_entropy = Gauge('committee_vote_entropy', 'Entropy of agent votes')
committee_attribution = Gauge('committee_attribution_pct', 'Attribution by agent', ['agent'])
committee_action_distribution = Counter('committee_actions_total', 'Actions taken', ['action'])
```

### Memory Optimizer Metrics

```python
memory_pattern_weight = Gauge('memory_pattern_weight', 'Pattern cluster weight', ['pattern_id'])
memory_slippage_predicted = Histogram('memory_slippage_predicted_bps', 'Predicted slippage')
memory_slippage_actual = Histogram('memory_slippage_actual_bps', 'Actual slippage')
```

### Self-Reflection Metrics

```python
self_reflection_issues = Counter('self_reflection_issues_total', 'Issues detected', ['issue_type'])
self_reflection_interventions = Counter('self_reflection_interventions_total', 'Interventions triggered', ['intervention'])
```

---

## 10. Summary

**Three-Layer Architecture**:

| Layer | Horizon | Governs | Approval |
|-------|---------|---------|----------|
| Planners | Weeks–Months | Committee weights, thresholds, regime tags | Quorum (3 votes) |
| Committee | Hours–Days | Trade decisions (weighted ensemble) | N/A (executes) |
| Memory Optimizer | Seconds–Minutes | Execution heuristics (local tuning) | N/A (bounded) |

**Key Benefits**:
1. ✅ **Temporal Coherence**: Each layer optimizes its own timescale
2. ✅ **Strategic Alignment**: Planners keep system aligned with macro
3. ✅ **Tactical Flexibility**: Committee adapts to intraday conditions
4. ✅ **Execution Efficiency**: Memory refines microstructure tuning
5. ✅ **Governance**: Quorum protects against rogue planners
6. ✅ **Self-Correction**: Reflection layer detects misalignment

**Resulting Behavior**:
- When sentiment shifts bullish → Planners increase trend-agent weight
- As volatility spikes → Memory patterns tighten stops automatically
- Committee aggregates all votes per tick → Planners steer the blend
- System achieves **both macro alignment and micro adaptability** without model retraining

---

**Last Updated**: 2025-10-31
**Status**: Production Specification
**Next**: Integrate with quorum system and implement planner proposals

**See Also**:
- **[Quorum-Governed Memory System](quorum-memory-system.md)** - Governance for all proposals
- **[Multi-Agent Architecture](../agents/multi-agent-architecture.md)** - Complete agent roles
- **[Agent Memory System](agent-memory-system.md)** - Memory foundations
