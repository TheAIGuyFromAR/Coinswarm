# Multi-Agent Architecture

## Overview

Coinswarm employs a **Memory-Augmented Multi-Agent Reinforcement Learning (MARL)** system where specialized agents collaborate to gather information, analyze markets, learn patterns, and execute trades. Each agent has a specific role, maintains episodic and semantic memory, and learns through reinforcement learning while sharing knowledge with other agents.

**Key Innovation**: Unlike traditional trading bots that rely solely on model weights, Coinswarm agents use explicit memory systems (stored in Redis vector database) to recall similar past experiences, adapt to regime changes, and learn from collective intelligence.

**References**:
- **[Agent Memory System](../architecture/agent-memory-system.md)** - Detailed memory architecture
- Wei et al. (2024): "Multi-Agent RL for High-Frequency Trading" (Sharpe 2.87)
- Zong et al. (2024): "MacroHFT: Memory Augmented Context-aware RL"

---

## Agent Hierarchy

```
                        ┌─────────────────────────┐
                        │  Master Orchestrator    │
                        │  (Strategic Coordinator)│
                        └───────────┬─────────────┘
                                    │
                    ┌───────────────┼────────────────┐
                    │               │                │
            ┌───────▼──────┐  ┌────▼──────────┐  ┌─▼──────────────┐
            │  Oversight   │  │  Memory       │  │  Pattern       │
            │  Manager     │  │  Managers     │  │  Learning      │
            │              │  │  (Quorum=3)   │  │  System        │
            └───────┬──────┘  └────┬──────────┘  └─┬──────────────┘
                    │              │               │
        ┌───────────┼──────────────┼───────────────┼──────────┐
        │           │              │               │           │
    ┌───▼────┐  ┌──▼────┐  ┌─────▼──┐  ┌────────▼──┐  ┌─────▼─────┐
    │ Info   │  │ Data  │  │ Market │  │ Sentiment │  │ Trading   │
    │ Gather │  │ Anal. │  │ Pattern│  │ Analysis  │  │ Agents    │
    │ Agents │  │ Agents│  │ Agents │  │ Agent     │  │ (per pair)│
    └────────┘  └───────┘  └────────┘  └───────────┘  └───────────┘
                                                             │
                                                             ▼
                                                    ┌────────────────┐
                                                    │  Message Bus   │
                                                    │  (NATS)        │
                                                    │  Proposals     │
                                                    │  Votes         │
                                                    │  Commits       │
                                                    └────────────────┘
```

**Key Addition**: **Memory Managers** form a consensus layer (minimum 3) that govern all memory mutations through quorum voting. See **[Quorum-Governed Memory System](../architecture/quorum-memory-system.md)** for complete specification.

---

## Core Agents

### 1. Master Orchestrator

**Role**: Strategic coordinator and decision arbiter

**Responsibilities**:
- Coordinate all agent activities
- Allocate resources across trading strategies
- Make final trading decisions based on agent recommendations
- Manage portfolio allocation and rebalancing
- Handle emergency shutdowns and circuit breakers

**Inputs**:
- Trading recommendations from Trading Agents
- Risk assessments from Oversight Manager
- Pattern insights from Pattern Learning System
- Market analysis from Market Pattern Agents
- Sentiment scores from Sentiment Agent

**Outputs**:
- Trading approvals/rejections
- Resource allocation decisions
- Strategy activation/deactivation
- Emergency stops

**Decision Framework**:
```python
class MasterOrchestrator:
    def evaluate_trade_proposal(self, proposal: TradeProposal) -> Decision:
        # Collect opinions
        risk_assessment = self.oversight_manager.assess_risk(proposal)
        pattern_match = self.pattern_system.match_patterns(proposal)
        sentiment = self.sentiment_agent.get_current_sentiment(proposal.product)

        # Weighted scoring
        score = (
            risk_assessment.score * 0.4 +
            pattern_match.confidence * 0.3 +
            sentiment.score * 0.2 +
            self.portfolio_fit_score(proposal) * 0.1
        )

        # Decision threshold
        if score > 0.75 and risk_assessment.acceptable:
            return Decision.APPROVE
        elif score > 0.5:
            return Decision.APPROVE_REDUCED_SIZE
        else:
            return Decision.REJECT

    def allocate_capital(self) -> Dict[str, float]:
        # Kelly Criterion with safety factor
        allocations = {}
        for strategy in self.active_strategies:
            edge = self.pattern_system.get_strategy_edge(strategy)
            kelly = edge / variance
            safe_kelly = kelly * 0.25  # Quarter Kelly
            allocations[strategy] = safe_kelly

        return self.normalize_allocations(allocations)
```

**Configuration**:
```yaml
orchestrator:
  max_concurrent_trades: 5
  max_portfolio_risk: 0.20  # 20% of capital at risk
  min_approval_score: 0.75
  emergency_stop_loss: -0.10  # 10% drawdown triggers stop
  rebalance_frequency: "4h"
```

---

### 2. Oversight Manager

**Role**: Risk management and compliance monitoring

**Responsibilities**:
- Monitor all trading activity in real-time
- Enforce position limits and risk parameters
- Detect anomalous behavior
- Trigger circuit breakers when needed
- Audit agent decisions
- Generate compliance reports

**Risk Checks**:
```python
class OversightManager:
    def assess_risk(self, proposal: TradeProposal) -> RiskAssessment:
        checks = [
            self.check_position_size(proposal),
            self.check_correlation_risk(proposal),
            self.check_liquidity(proposal),
            self.check_volatility(proposal),
            self.check_concentration(proposal),
            self.check_daily_loss_limit(),
            self.check_drawdown()
        ]

        failed_checks = [c for c in checks if not c.passed]

        return RiskAssessment(
            acceptable=len(failed_checks) == 0,
            score=sum(c.score for c in checks) / len(checks),
            failed_checks=failed_checks,
            warnings=[c.warning for c in checks if c.warning]
        )

    def check_position_size(self, proposal: TradeProposal) -> Check:
        current_position = self.get_position(proposal.product)
        new_position = current_position + proposal.size
        max_position = self.config.max_position_size

        if abs(new_position) > max_position:
            return Check(
                passed=False,
                score=0,
                warning=f"Position would exceed max size: {new_position} > {max_position}"
            )
        return Check(passed=True, score=1.0)

    def check_drawdown(self) -> Check:
        current_drawdown = self.calculate_drawdown()
        max_drawdown = self.config.max_drawdown

        if current_drawdown < -max_drawdown:
            self.trigger_circuit_breaker("Max drawdown exceeded")
            return Check(passed=False, score=0)

        return Check(passed=True, score=1.0)
```

**Circuit Breakers**:
- **Daily Loss Limit**: Stop all trading if daily loss > 5%
- **Drawdown Limit**: Halt if portfolio drawdown > 10%
- **Volatility Spike**: Pause if volatility > 3x average
- **API Errors**: Stop if error rate > 10%
- **Manual Override**: Human can trigger emergency stop

**Monitoring Dashboard**:
```python
class MonitoringDashboard:
    def get_real_time_metrics(self) -> Dict:
        return {
            'portfolio_value': self.calculate_portfolio_value(),
            'daily_pnl': self.calculate_daily_pnl(),
            'positions': self.get_all_positions(),
            'open_orders': self.get_open_orders(),
            'risk_utilization': self.calculate_risk_utilization(),
            'active_alerts': self.get_active_alerts(),
            'circuit_breaker_status': self.get_circuit_breaker_status()
        }
```

---

### 3. Memory Managers

**Role**: Consensus-based governance of memory mutations

**Count**: Minimum 3 (typically 3-5 for dev, up to 7 for production)

**Responsibilities**:
- Evaluate memory change proposals using deterministic decision function
- Cast votes on proposals (ACCEPT/REJECT with reasoning)
- Coordinate commits via rotating coordinator
- Maintain audit trail of all memory mutations
- Verify read-after-write consistency

**Key Principle**: **No memory mutation without 3 matching votes**

**Decision Function** (deterministic):
```python
class MemoryManager:
    def evaluate_proposal(self, proposal: MemoryProposal) -> Vote:
        """
        Deterministic evaluation of memory change proposal

        Same input → same vote (enables audit and replay)
        """

        checks = [
            self.check_regime_consistency(proposal),
            self.check_support(proposal),  # Cluster validity
            self.check_bounds(proposal),   # Delta and weight limits
            self.check_impact(proposal),   # Sharpe and drawdown proxy
            self.check_cooldown(proposal)  # Rate limiting
        ]

        failures = [reason for ok, reason in checks if not ok]

        if failures:
            decision = "REJECT"
            reasons = failures
        else:
            decision = "ACCEPT"
            reasons = []

        # Compute deterministic vote hash
        payload_norm = normalize_proposal(proposal)
        vote_hash = hashlib.sha256(
            f"{decision}||{json.dumps(payload_norm, sort_keys=True)}".encode()
        ).hexdigest()

        return Vote(
            manager_id=self.id,
            change_id=proposal.change_id,
            decision=decision,
            reasons=reasons,
            vote_hash=vote_hash
        )
```

**Quorum Protocol**:
```python
class QuorumCoordinator:
    """
    Accumulate votes and commit on 3 matching votes

    Roles rotate every M commits or time-boxed
    """

    def __init__(self, quorum_size=3):
        self.quorum_size = quorum_size
        self.pending_votes = defaultdict(list)

    def on_vote(self, vote: Vote):
        change_id = vote.change_id
        self.pending_votes[change_id].append(vote)

        if len(self.pending_votes[change_id]) >= self.quorum_size:
            votes = self.pending_votes[change_id][:self.quorum_size]

            # Check consensus
            vote_hashes = [v.vote_hash for v in votes]
            decisions = [v.decision for v in votes]

            if len(set(vote_hashes)) == 1 and len(set(decisions)) == 1:
                # Quorum reached
                if decisions[0] == 'ACCEPT':
                    self.apply_change(get_proposal(change_id))
                    state_hash = compute_state_hash()
                else:
                    state_hash = None

                # Broadcast commit
                self.publish_commit(change_id, decisions[0], votes, state_hash)
                self.append_audit(change_id, votes)
            else:
                # No consensus - reject
                self.publish_commit(change_id, 'REJECT', votes, None)

            del self.pending_votes[change_id]
```

**Communication**:
- **Message Bus**: NATS or Redis Streams
- **Topics**:
  - `mem.propose`: Bots → Managers
  - `mem.vote`: Managers → Coordinator
  - `mem.commit`: Coordinator → All
  - `mem.audit`: Append-only log

**Safety Guarantees**:
1. Read-only mode if < 3 managers online
2. All commits logged with proposal hash, vote hashes, and state hash
3. Deterministic decisions enable replay and audit
4. Byzantine fault-tolerant (handles 1 malicious manager with 3 total)

**Configuration**:
```yaml
memory_managers:
  count: 3
  quorum_size: 3
  vote_timeout_ms: 5
  coordinator_rotation_commits: 100
  audit_log_retention_days: 365
```

**See**: **[Quorum-Governed Memory System](../architecture/quorum-memory-system.md)** for complete specification including:
- Detailed decision function with checks
- Credit assignment algorithm (kernel-weighted)
- Pattern maintenance and promotion rules
- Deployment phases
- Benchmarking and CI gates

---

### 4. Information Gathering Agents

**Role**: Collect and preprocess raw data from external sources

**Agent Types**:

#### 3.1 Market Data Agent
```python
class MarketDataAgent:
    def __init__(self):
        self.sources = [
            CoinbaseMarketData(),
            AlpacaMarketData(),
            CoinGeckoMarketData()
        ]

    async def gather_market_data(self, products: List[str]) -> MarketSnapshot:
        tasks = [
            self.fetch_ticker(product),
            self.fetch_orderbook(product),
            self.fetch_recent_trades(product),
            self.fetch_candles(product, '1h', 24)
        ]
        results = await asyncio.gather(*tasks)

        return MarketSnapshot(
            products=products,
            tickers=results[0],
            orderbooks=results[1],
            trades=results[2],
            candles=results[3],
            timestamp=datetime.utcnow()
        )
```

#### 3.2 News Gathering Agent
```python
class NewsGatheringAgent:
    def __init__(self):
        self.sources = [
            NewsAPISource(),
            RedditSource(),
            TwitterSource()
        ]

    async def gather_news(self, keywords: List[str]) -> NewsSnapshot:
        articles = []
        for source in self.sources:
            data = await source.fetch({'keywords': keywords})
            articles.extend(data['articles'])

        # Deduplicate
        articles = self.deduplicate(articles)

        return NewsSnapshot(
            articles=articles,
            keywords=keywords,
            timestamp=datetime.utcnow()
        )
```

#### 3.3 On-Chain Data Agent
```python
class OnChainAgent:
    def __init__(self):
        self.sources = [
            EtherscanSource(),
            CryptoQuantSource(),
            GlassnodeSource()
        ]

    async def gather_onchain_data(self, assets: List[str]) -> OnChainSnapshot:
        metrics = {}
        for asset in assets:
            metrics[asset] = {
                'exchange_flows': await self.get_exchange_flows(asset),
                'whale_movements': await self.get_whale_activity(asset),
                'network_activity': await self.get_network_metrics(asset)
            }

        return OnChainSnapshot(
            metrics=metrics,
            timestamp=datetime.utcnow()
        )
```

---

### 4. Data Analysis Agents

**Role**: Process and analyze gathered data to extract insights

#### 4.1 Technical Analysis Agent
```python
class TechnicalAnalysisAgent:
    def analyze(self, candles: List[Candle]) -> TechnicalAnalysis:
        return TechnicalAnalysis(
            trend=self.calculate_trend(candles),
            support_resistance=self.find_support_resistance(candles),
            indicators={
                'rsi': self.calculate_rsi(candles),
                'macd': self.calculate_macd(candles),
                'bollinger': self.calculate_bollinger(candles)
            },
            signals=self.generate_signals(candles)
        )

    def calculate_trend(self, candles: List[Candle]) -> Trend:
        # Simple moving average crossover
        sma_20 = self.sma(candles, 20)
        sma_50 = self.sma(candles, 50)

        if sma_20 > sma_50:
            return Trend.UPTREND
        elif sma_20 < sma_50:
            return Trend.DOWNTREND
        else:
            return Trend.SIDEWAYS
```

#### 4.2 Fundamental Analysis Agent (Crypto)
```python
class CryptoFundamentalAgent:
    def analyze(self, asset: str) -> FundamentalAnalysis:
        return FundamentalAnalysis(
            valuation=self.calculate_valuation(asset),
            network_health=self.assess_network_health(asset),
            development_activity=self.measure_dev_activity(asset),
            community_strength=self.assess_community(asset)
        )

    def calculate_valuation(self, asset: str) -> Valuation:
        # NVT Ratio, Metcalfe's Law, etc.
        market_cap = self.get_market_cap(asset)
        transaction_volume = self.get_transaction_volume(asset)

        nvt = market_cap / transaction_volume

        return Valuation(
            nvt_ratio=nvt,
            fair_value_estimate=self.estimate_fair_value(asset),
            overvalued=nvt > 90
        )
```

---

### 5. Market Pattern Recognition Agents

**Role**: Identify recurring market patterns and conditions

```python
class MarketPatternAgent:
    def __init__(self):
        self.pattern_library = PatternLibrary()

    def identify_patterns(self, market_data: MarketSnapshot) -> List[Pattern]:
        patterns = []

        # Chart patterns
        patterns.extend(self.find_chart_patterns(market_data.candles))

        # Volume patterns
        patterns.extend(self.find_volume_patterns(market_data.volume))

        # Order book patterns
        patterns.extend(self.analyze_order_book(market_data.orderbook))

        return patterns

    def find_chart_patterns(self, candles: List[Candle]) -> List[Pattern]:
        patterns = []

        # Head and shoulders
        if self.is_head_and_shoulders(candles):
            patterns.append(Pattern(
                type='head_and_shoulders',
                confidence=0.85,
                signal='bearish',
                expected_move=-0.05
            ))

        # Double bottom
        if self.is_double_bottom(candles):
            patterns.append(Pattern(
                type='double_bottom',
                confidence=0.80,
                signal='bullish',
                expected_move=0.07
            ))

        return patterns
```

---

### 6. Sentiment Analysis Agent

**Role**: Analyze news, social media, and alternative data for sentiment

```python
class SentimentAnalysisAgent:
    def __init__(self):
        self.nlp_model = SentimentModel()
        self.sources = {
            'news': NewsSource(),
            'twitter': TwitterSource(),
            'reddit': RedditSource()
        }

    async def analyze_sentiment(self, asset: str) -> SentimentScore:
        # Gather data
        news = await self.sources['news'].fetch({'query': asset})
        tweets = await self.sources['twitter'].fetch({'query': asset})
        reddit = await self.sources['reddit'].fetch({'query': asset})

        # Analyze each source
        news_sentiment = self.analyze_news(news)
        twitter_sentiment = self.analyze_tweets(tweets)
        reddit_sentiment = self.analyze_reddit(reddit)

        # Weighted aggregate
        overall = (
            news_sentiment * 0.5 +
            twitter_sentiment * 0.3 +
            reddit_sentiment * 0.2
        )

        return SentimentScore(
            asset=asset,
            overall_score=overall,
            news_score=news_sentiment,
            social_score=(twitter_sentiment + reddit_sentiment) / 2,
            confidence=self.calculate_confidence([news, tweets, reddit]),
            timestamp=datetime.utcnow()
        )

    def analyze_news(self, articles: List[dict]) -> float:
        scores = []
        for article in articles:
            text = f"{article['title']} {article['description']}"
            sentiment = self.nlp_model.predict(text)
            scores.append(sentiment)

        return sum(scores) / len(scores) if scores else 0.0
```

---

### 7. Pattern Learning System

**Role**: Learn from historical trades and market conditions

**See**: `pattern-learning-system.md` for detailed documentation

**Summary**:
- Stores successful and failed trades
- Identifies conditions that lead to profitable patterns
- Builds a pattern library
- Provides pattern matching for new opportunities

---

### 8. Pattern Optimization Agent

**Role**: Combine, augment, and optimize learned patterns

```python
class PatternOptimizationAgent:
    def __init__(self):
        self.pattern_storage = PatternStorage()
        self.genetic_algorithm = GeneticOptimizer()

    async def optimize_patterns(self):
        """Runs periodically to improve pattern library"""

        # Get all patterns
        patterns = await self.pattern_storage.get_all_patterns()

        # Find correlated patterns
        correlations = self.find_correlations(patterns)

        # Combine high-correlation patterns
        combined = self.combine_patterns(correlations)

        # Run genetic algorithm for parameter optimization
        optimized = self.genetic_algorithm.optimize(combined)

        # Test on historical data
        backtested = self.backtest_patterns(optimized)

        # Keep only improvements
        improvements = [p for p in backtested if p.sharpe > 1.5]

        # Store in pattern library
        await self.pattern_storage.add_patterns(improvements)

    def combine_patterns(self, correlations: List[Correlation]) -> List[Pattern]:
        """Merge correlated patterns into ensemble patterns"""
        combined = []

        for corr in correlations:
            if corr.strength > 0.8:
                ensemble = EnsemblePattern(
                    patterns=[corr.pattern_a, corr.pattern_b],
                    weights=self.optimize_weights(corr),
                    conditions=self.merge_conditions(corr)
                )
                combined.append(ensemble)

        return combined
```

---

### 9. Trading Execution Agents

**Role**: Execute trades for specific products/strategies

**One agent per trading pair** to allow parallel execution and independent state management.

```python
class TradingAgent:
    def __init__(self, product_id: str, strategy: Strategy):
        self.product_id = product_id
        self.strategy = strategy
        self.state = TradingState()

    async def run(self):
        """Main trading loop"""
        while self.state.active:
            # Get market data
            market_data = await self.get_market_data()

            # Get sentiment
            sentiment = await self.get_sentiment()

            # Check for pattern matches
            patterns = await self.match_patterns(market_data)

            # Generate trade signal
            signal = self.strategy.generate_signal(
                market_data, sentiment, patterns
            )

            if signal:
                # Create proposal
                proposal = TradeProposal(
                    product_id=self.product_id,
                    side=signal.side,
                    size=signal.size,
                    strategy=self.strategy.name,
                    confidence=signal.confidence,
                    reasoning=signal.reasoning
                )

                # Submit to orchestrator
                decision = await self.orchestrator.evaluate_trade(proposal)

                if decision == Decision.APPROVE:
                    await self.execute_trade(proposal)

            await asyncio.sleep(self.strategy.interval)

    async def execute_trade(self, proposal: TradeProposal):
        """Execute approved trade"""
        order = await self.mcp_server.place_order({
            'product_id': proposal.product_id,
            'side': proposal.side,
            'size': str(proposal.size),
            'order_type': 'LIMIT',
            'limit_price': str(proposal.limit_price)
        })

        # Track order
        self.state.open_orders[order['order_id']] = order

        # Update pattern system
        await self.pattern_system.record_trade(proposal, order)
```

---

## Inter-Agent Communication

### Message Passing Protocol

```python
class AgentMessage:
    sender: str
    recipient: str
    message_type: MessageType
    payload: Dict[str, Any]
    timestamp: datetime
    correlation_id: str  # For tracking request/response chains

class MessageBus:
    def __init__(self):
        self.subscribers = defaultdict(list)
        self.message_queue = asyncio.Queue()

    def subscribe(self, topic: str, handler: Callable):
        self.subscribers[topic].append(handler)

    async def publish(self, topic: str, message: AgentMessage):
        for handler in self.subscribers[topic]:
            await handler(message)

    async def request_response(self, topic: str, message: AgentMessage,
                                timeout: int = 5) -> AgentMessage:
        correlation_id = str(uuid.uuid4())
        message.correlation_id = correlation_id

        # Set up response listener
        response_future = asyncio.Future()
        def response_handler(msg: AgentMessage):
            if msg.correlation_id == correlation_id:
                response_future.set_result(msg)

        self.subscribe(f"{topic}.response", response_handler)

        # Publish request
        await self.publish(topic, message)

        # Wait for response
        return await asyncio.wait_for(response_future, timeout)
```

### Topics

- `market.data.update` - Market data updates
- `sentiment.score.update` - New sentiment scores
- `pattern.matched` - Pattern recognition results
- `trade.proposal` - Trading proposals
- `trade.decision` - Orchestrator decisions
- `risk.alert` - Risk warnings
- `system.health` - Health checks

---

## Agent Lifecycle

### Initialization
```python
async def initialize_agents():
    # Start infrastructure
    message_bus = MessageBus()
    mcp_server = await start_mcp_server()
    pattern_storage = await PatternStorage.connect()

    # Initialize core agents
    orchestrator = MasterOrchestrator(message_bus)
    oversight = OversightManager(message_bus)
    pattern_system = PatternLearningSystem(pattern_storage)

    # Initialize worker agents
    agents = []

    # Info gathering
    agents.append(MarketDataAgent(message_bus))
    agents.append(NewsGatheringAgent(message_bus))
    agents.append(OnChainAgent(message_bus))

    # Analysis
    agents.append(TechnicalAnalysisAgent(message_bus))
    agents.append(SentimentAnalysisAgent(message_bus))
    agents.append(MarketPatternAgent(message_bus))

    # Pattern optimization
    agents.append(PatternOptimizationAgent(message_bus, pattern_system))

    # Trading execution (one per product)
    for product in TRADING_PRODUCTS:
        strategy = load_strategy(product)
        agents.append(TradingAgent(product, strategy, message_bus))

    # Start all agents
    tasks = [agent.run() for agent in agents]
    await asyncio.gather(*tasks)
```

---

## Configuration

```yaml
# config/agents.yaml

orchestrator:
  max_concurrent_trades: 5
  capital_allocation:
    mode: "dynamic"  # dynamic | fixed
    max_per_trade: 0.05  # 5% of capital

oversight:
  risk_limits:
    max_position_size: 0.25
    max_drawdown: 0.10
    max_daily_loss: 0.05
  circuit_breakers:
    enabled: true
    volatility_threshold: 3.0
    error_rate_threshold: 0.10

information_gathering:
  market_data:
    update_frequency: "1s"
    products: ["BTC-USD", "ETH-USD", "SOL-USD"]
  news:
    update_frequency: "5m"
    sources: ["newsapi", "reddit"]
  sentiment:
    update_frequency: "1m"

trading_agents:
  BTC-USD:
    strategy: "trend_following"
    interval: "5m"
    max_position: 0.10
  ETH-USD:
    strategy: "mean_reversion"
    interval: "5m"
    max_position: 0.10
  SOL-USD:
    strategy: "breakout"
    interval: "1m"
    max_position: 0.05
```

---

**Last Updated**: 2025-10-31
**Status**: Planning Phase
**Next**: Pattern Learning System Documentation
