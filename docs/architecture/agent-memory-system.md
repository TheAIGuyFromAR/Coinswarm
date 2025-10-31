# Agent Memory System Architecture

## Overview

Coinswarm implements a **Memory-Augmented Multi-Agent Reinforcement Learning (MARL)** framework where each agent maintains episodic and semantic memory to improve decision-making in dynamic market conditions. This document details the memory architecture, storage layer, retrieval mechanisms, and integration with the RL framework.

**Inspired by**: MacroHFT (Zong et al., 2024) - Memory-augmented context-aware RL for high-frequency trading.

---

## Why Memory-Augmented RL?

Traditional RL agents rely solely on:
- Current state observation
- Learned policy weights
- No explicit memory of past regimes or outcomes

**Problem**: Markets exhibit regime changes that aren't captured in model weights alone.

**Solution**: Augment agents with explicit memory that stores:
- Past market states and outcomes
- Successful/failed pattern executions
- Regime characteristics
- Agent interaction history

**Benefits**:
- Faster adaptation to regime shifts
- Better credit assignment across agents
- Reduced non-stationarity in MARL
- Improved sample efficiency

---

## Memory Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Agent Layer                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐     │
│  │ Trading      │  │ Pattern      │  │ Market Analysis      │     │
│  │ Agent        │  │ Agent        │  │ Agent                │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────────────┘     │
│         │ query            │                 │                      │
└─────────┼──────────────────┼─────────────────┼──────────────────────┘
          │                  │                 │
          ▼                  ▼                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Memory Retrieval Service                          │
│  • Vector similarity search                                          │
│  • Temporal filtering                                                │
│  • Regime-aware retrieval                                            │
│  • Concurrent query batching                                         │
└─────────┬───────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Redis Vector Database                             │
│  ┌────────────────────┐  ┌────────────────────┐                     │
│  │ Episodic Memory    │  │ Semantic Memory    │                     │
│  │ • State vectors    │  │ • Pattern vectors  │                     │
│  │ • Action outcomes  │  │ • Regime vectors   │                     │
│  │ • Rewards          │  │ • Agent policies   │                     │
│  └────────────────────┘  └────────────────────┘                     │
│                                                                       │
│  Performance: Sub-millisecond latency, 3.4× higher QPS than Qdrant  │
└───────────────────────────────────────────────────────────────────────┘
```

---

## Memory Types

### 1. Episodic Memory

**Purpose**: Store specific experiences (state-action-reward-next_state tuples)

**Schema**:
```python
@dataclass
class EpisodicMemory:
    """Single experience in agent's episodic memory"""

    # Identity
    memory_id: str
    agent_id: str
    timestamp: datetime

    # Experience tuple
    state_vector: np.ndarray      # 256-dim embedding of market state
    action: Action                # Action taken
    reward: float                 # Immediate reward
    next_state_vector: np.ndarray # Resulting state

    # Context
    product_id: str               # BTC-USD, ETH-USD, etc.
    regime: str                   # TRENDING, MEAN_REVERTING, VOLATILE, etc.
    market_phase: str             # OPEN, MIDDAY, CLOSE

    # Metadata
    pattern_ids: List[str]        # Patterns that triggered this action
    confidence: float             # Agent's confidence in action
    other_agent_actions: Dict[str, Action]  # What other agents did

    # Outcome
    terminal: bool                # Was this a terminal state?
    cumulative_return: float      # Total return from this action
```

**Storage in Redis**:
```python
# Redis key structure
key = f"episodic:{agent_id}:{product_id}:{timestamp_ms}"

# Store as hash with vector field
redis_client.hset(key, mapping={
    'agent_id': agent_id,
    'timestamp': timestamp,
    'action': action.to_json(),
    'reward': reward,
    'regime': regime,
    'terminal': terminal,
    # ... other fields
})

# Store vector separately for similarity search
redis_client.execute_command(
    'FT.ADD', 'episodic_memory_index',
    key,
    1.0,
    'FIELDS',
    'state_vector', state_vector.tobytes(),
    'agent_id', agent_id,
    'product_id', product_id,
    'regime', regime
)
```

---

### 2. Semantic Memory

**Purpose**: Store abstract knowledge (patterns, strategies, regime characteristics)

**Schema**:
```python
@dataclass
class SemanticMemory:
    """Abstract knowledge in agent's semantic memory"""

    # Identity
    memory_id: str
    memory_type: str  # PATTERN, REGIME, STRATEGY, CORRELATION
    created_at: datetime
    last_accessed: datetime
    access_count: int

    # Content
    concept_vector: np.ndarray    # 256-dim embedding of the concept
    description: str              # Human-readable description

    # Pattern-specific (if memory_type == PATTERN)
    pattern_id: Optional[str]
    conditions: Optional[Dict]
    expected_return: Optional[float]
    win_rate: Optional[float]

    # Regime-specific (if memory_type == REGIME)
    regime_name: Optional[str]
    regime_features: Optional[Dict]  # Volatility, volume, trend characteristics
    typical_duration: Optional[int]  # Seconds
    transition_probability: Optional[Dict[str, float]]  # Next regime probabilities

    # Strategy-specific (if memory_type == STRATEGY)
    strategy_name: Optional[str]
    applicable_regimes: Optional[List[str]]
    success_rate_by_regime: Optional[Dict[str, float]]

    # Performance
    historical_performance: PerformanceMetrics
    sharpe_ratio: float
    max_drawdown: float
```

**Storage in Redis**:
```python
# Redis key structure
key = f"semantic:{memory_type}:{memory_id}"

# Index for vector search
redis_client.execute_command(
    'FT.CREATE', 'semantic_memory_index',
    'ON', 'HASH',
    'PREFIX', '1', 'semantic:',
    'SCHEMA',
    'concept_vector', 'VECTOR', 'FLAT', '6', 'DIM', '256', 'TYPE', 'FLOAT32', 'DISTANCE_METRIC', 'COSINE',
    'memory_type', 'TAG',
    'regime_name', 'TAG',
    'sharpe_ratio', 'NUMERIC'
)
```

---

### 3. Working Memory

**Purpose**: Short-term context for current episode

**Schema**:
```python
@dataclass
class WorkingMemory:
    """Agent's current working context"""

    agent_id: str

    # Current episode
    episode_id: str
    episode_start: datetime
    episode_length: int  # Number of steps

    # Recent observations (sliding window)
    recent_states: deque  # Last N states (maxlen=100)
    recent_actions: deque  # Last N actions
    recent_rewards: deque  # Last N rewards

    # Current beliefs
    current_regime: str
    regime_confidence: float
    regime_start_time: datetime

    # Active patterns
    active_patterns: List[str]  # Pattern IDs currently matching
    pattern_confidences: Dict[str, float]

    # Other agents
    other_agent_states: Dict[str, AgentState]

    # Temporary variables (reset each episode)
    cumulative_reward: float
    episode_max_drawdown: float
```

**Storage**: In-process memory (Python objects), not persisted to Redis unless episode completes.

---

## Memory Retrieval

### Similarity Search

```python
class MemoryRetrievalService:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def retrieve_similar_experiences(
        self,
        current_state_vector: np.ndarray,
        agent_id: str,
        product_id: Optional[str] = None,
        regime: Optional[str] = None,
        top_k: int = 10
    ) -> List[EpisodicMemory]:
        """
        Retrieve most similar past experiences to current state

        Uses Redis vector similarity search with filtering
        """

        # Build query
        query_parts = [
            f"@state_vector:[VECTOR_RANGE {top_k} $state_blob]",
            f"@agent_id:{{{agent_id}}}"
        ]

        if product_id:
            query_parts.append(f"@product_id:{{{product_id}}}")

        if regime:
            query_parts.append(f"@regime:{{{regime}}}")

        query = " ".join(query_parts)

        # Execute search
        results = await self.redis.execute_command(
            'FT.SEARCH', 'episodic_memory_index',
            query,
            'PARAMS', '2', 'state_blob', current_state_vector.tobytes(),
            'SORTBY', '_score',
            'LIMIT', '0', str(top_k)
        )

        # Parse results
        memories = []
        for i in range(1, len(results), 2):
            key = results[i]
            fields = results[i+1]
            memory = self.parse_memory(key, fields)
            memories.append(memory)

        return memories
```

### Regime-Aware Retrieval

```python
async def retrieve_regime_knowledge(
    self,
    current_regime: str,
    previous_regimes: List[str],
    top_k: int = 5
) -> List[SemanticMemory]:
    """
    Retrieve knowledge about current regime and transitions
    """

    # Get regime characteristics
    regime_memories = await self.redis.ft('semantic_memory_index').search(
        f"@memory_type:{{REGIME}} @regime_name:{{{current_regime}}}"
    )

    # Get successful strategies for this regime
    strategy_memories = await self.redis.ft('semantic_memory_index').search(
        f"@memory_type:{{STRATEGY}} @applicable_regimes:{{{current_regime}}}"
        " @sharpe_ratio:[1.5 +inf]"  # Only high-performing strategies
    ).sort_by('sharpe_ratio', asc=False).paging(0, top_k)

    return regime_memories + strategy_memories
```

---

## Multi-Agent Memory Sharing

### Shared Memory Pool

**Purpose**: Allow agents to learn from each other's experiences

```python
class SharedMemoryPool:
    """Centralized memory pool accessible to all agents"""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def add_shared_experience(
        self,
        experience: EpisodicMemory,
        quality_score: float
    ):
        """
        Add high-quality experience to shared pool

        Only experiences with quality_score > threshold are shared
        """

        if quality_score < 0.7:  # Threshold
            return

        key = f"shared_episodic:{experience.product_id}:{experience.timestamp}"

        # Store with TTL (expire after 30 days)
        await self.redis.hset(key, mapping=experience.to_dict())
        await self.redis.expire(key, 30 * 24 * 3600)

        # Add to vector index
        await self.add_to_vector_index(key, experience)

    async def retrieve_shared_experiences(
        self,
        state_vector: np.ndarray,
        product_id: str,
        exclude_agent_id: str,
        top_k: int = 5
    ) -> List[EpisodicMemory]:
        """
        Retrieve experiences from other agents

        Useful for learning from collective intelligence
        """

        query = (
            f"@state_vector:[VECTOR_RANGE {top_k} $state_blob] "
            f"@product_id:{{{product_id}}} "
            f"-@agent_id:{{{exclude_agent_id}}}"  # Exclude own experiences
        )

        results = await self.redis.ft('shared_episodic_index').search(
            query,
            query_params={'state_blob': state_vector.tobytes()}
        )

        return [self.parse_experience(r) for r in results]
```

### Communication Protocol

```python
@dataclass
class AgentMemoryMessage:
    """Message for sharing memory insights between agents"""

    sender_agent_id: str
    recipient_agent_ids: List[str]  # Or "all" for broadcast
    message_type: str  # EXPERIENCE, PATTERN, REGIME_CHANGE, WARNING

    # Content
    memory_id: Optional[str]  # Reference to shared memory
    insight: str  # Human-readable insight
    data: Dict  # Structured data

    # Metadata
    importance: float  # 0-1 score
    timestamp: datetime

# Example: Agent broadcasts regime change
message = AgentMemoryMessage(
    sender_agent_id="trading_agent_btc",
    recipient_agent_ids=["all"],
    message_type="REGIME_CHANGE",
    memory_id=None,
    insight="Detected regime shift from TRENDING to VOLATILE",
    data={
        'old_regime': 'TRENDING',
        'new_regime': 'VOLATILE',
        'confidence': 0.92,
        'typical_duration': 3600  # 1 hour
    },
    importance=0.9,
    timestamp=datetime.utcnow()
)
```

---

## Memory-Augmented Decision Making

### Integration with RL Policy

```python
class MemoryAugmentedPolicy:
    """
    RL policy that uses memory retrieval to augment decisions

    Based on MacroHFT architecture (Zong et al., 2024)
    """

    def __init__(
        self,
        base_policy: nn.Module,
        memory_retrieval: MemoryRetrievalService,
        memory_encoder: nn.Module
    ):
        self.base_policy = base_policy
        self.memory_retrieval = memory_retrieval
        self.memory_encoder = memory_encoder

    async def select_action(
        self,
        state: np.ndarray,
        agent_id: str,
        product_id: str,
        regime: str
    ) -> Tuple[Action, float]:
        """
        Select action using both policy network and memory
        """

        # Encode current state
        state_vector = self.encode_state(state)

        # Retrieve similar past experiences
        similar_memories = await self.memory_retrieval.retrieve_similar_experiences(
            state_vector,
            agent_id,
            product_id,
            regime,
            top_k=10
        )

        # Retrieve regime knowledge
        regime_knowledge = await self.memory_retrieval.retrieve_regime_knowledge(
            regime,
            previous_regimes=[],  # TODO: track regime history
            top_k=5
        )

        # Encode retrieved memories
        if similar_memories:
            memory_embedding = self.memory_encoder(
                [m.to_tensor() for m in similar_memories]
            )
        else:
            memory_embedding = torch.zeros(256)

        # Encode regime knowledge
        if regime_knowledge:
            regime_embedding = self.memory_encoder(
                [k.concept_vector for k in regime_knowledge]
            )
        else:
            regime_embedding = torch.zeros(256)

        # Concatenate state + memory + regime
        augmented_state = torch.cat([
            torch.tensor(state_vector),
            memory_embedding,
            regime_embedding
        ])

        # Forward through policy network
        action_logits = self.base_policy(augmented_state)
        action_probs = F.softmax(action_logits, dim=-1)

        # Sample action
        action_idx = torch.multinomial(action_probs, 1).item()
        action = Action.from_index(action_idx)

        # Confidence = max probability
        confidence = action_probs.max().item()

        return action, confidence
```

---

## Regime Detection and Memory

### Regime Detection Agent

```python
class RegimeDetectionAgent:
    """
    Detects market regime changes and manages regime memory

    Regimes: TRENDING, MEAN_REVERTING, VOLATILE, QUIET, CRISIS
    """

    def __init__(self, memory_service: MemoryRetrievalService):
        self.memory_service = memory_service
        self.current_regime = None
        self.regime_start_time = None

    async def detect_regime(
        self,
        market_data: MarketSnapshot,
        lookback_periods: int = 100
    ) -> Tuple[str, float]:
        """
        Detect current market regime

        Returns: (regime_name, confidence)
        """

        # Calculate regime features
        features = self.calculate_regime_features(market_data, lookback_periods)

        # Encode features as vector
        feature_vector = self.encode_features(features)

        # Retrieve similar regime states from memory
        similar_regimes = await self.memory_service.retrieve_similar_regimes(
            feature_vector,
            top_k=5
        )

        if similar_regimes:
            # Vote based on similar historical regimes
            regime_votes = defaultdict(float)
            for mem in similar_regimes:
                regime_votes[mem.regime_name] += mem.confidence

            regime = max(regime_votes.items(), key=lambda x: x[1])
            regime_name, confidence = regime[0], regime[1] / len(similar_regimes)
        else:
            # Fallback: rule-based classification
            regime_name, confidence = self.classify_regime_rule_based(features)

        # Detect regime change
        if regime_name != self.current_regime:
            await self.on_regime_change(regime_name, confidence)

        return regime_name, confidence

    def calculate_regime_features(
        self,
        market_data: MarketSnapshot,
        lookback: int
    ) -> Dict[str, float]:
        """Calculate features for regime classification"""

        prices = market_data.get_price_history(lookback)
        volumes = market_data.get_volume_history(lookback)

        return {
            'volatility': np.std(np.diff(np.log(prices))),
            'trend_strength': self.calculate_trend_strength(prices),
            'mean_reversion': self.calculate_mean_reversion(prices),
            'volume_trend': np.mean(np.diff(volumes)) / np.mean(volumes),
            'autocorrelation': self.calculate_autocorr(prices, lag=10),
            'hurst_exponent': self.calculate_hurst(prices),
            'orderbook_imbalance': market_data.orderbook_imbalance,
            'bid_ask_spread': market_data.spread / market_data.price
        }

    async def on_regime_change(self, new_regime: str, confidence: float):
        """Handle regime transition"""

        if self.current_regime:
            # Calculate regime duration
            duration = (datetime.utcnow() - self.regime_start_time).total_seconds()

            # Update regime memory with actual duration
            await self.memory_service.update_regime_duration(
                self.current_regime,
                duration
            )

            # Update transition probabilities
            await self.memory_service.update_transition_probability(
                from_regime=self.current_regime,
                to_regime=new_regime
            )

        # Broadcast regime change to all agents
        await self.broadcast_regime_change(new_regime, confidence)

        # Update current regime
        self.current_regime = new_regime
        self.regime_start_time = datetime.utcnow()
```

---

## Redis Configuration for Memory

### Redis Setup

```yaml
# redis.conf optimizations for vector search

# Memory
maxmemory 16gb
maxmemory-policy allkeys-lru  # Evict least recently used when full

# Persistence
save ""  # Disable RDB snapshots for max performance
appendonly no  # Disable AOF for max performance
# Trade-off: Memory-only, no persistence

# Performance
io-threads 4
io-threads-do-reads yes

# RedisSearch module
loadmodule /usr/lib/redis/modules/redisearch.so

# Vector index settings
# In application code, set:
# FLAT index for < 100k vectors (exact search, fast)
# HNSW index for > 100k vectors (approximate, scalable)
```

### Vector Index Configuration

```python
# Create episodic memory index
redis_client.execute_command(
    'FT.CREATE', 'episodic_memory_index',
    'ON', 'HASH',
    'PREFIX', '1', 'episodic:',
    'SCHEMA',
    'state_vector', 'VECTOR', 'HNSW', '10',
        'DIM', '256',
        'TYPE', 'FLOAT32',
        'DISTANCE_METRIC', 'COSINE',
        'INITIAL_CAP', '100000',
        'M', '16',              # HNSW connections per layer
        'EF_CONSTRUCTION', '200',  # Build quality
        'EF_RUNTIME', '10',     # Query quality
    'agent_id', 'TAG',
    'product_id', 'TAG',
    'regime', 'TAG',
    'reward', 'NUMERIC',
    'timestamp', 'NUMERIC', 'SORTABLE'
)
```

---

## Performance Optimization

### Concurrency Handling

**Problem**: Redis latency increases with concurrent queries (Source 10: Qdrant benchmarks)

**Solutions**:

1. **Query Batching**
```python
class BatchedMemoryRetrieval:
    def __init__(self, redis_client: Redis, batch_size: int = 10):
        self.redis = redis_client
        self.batch_size = batch_size
        self.query_queue = asyncio.Queue()

    async def start_batch_processor(self):
        """Background task to batch queries"""
        while True:
            batch = []
            # Collect up to batch_size queries
            for _ in range(self.batch_size):
                try:
                    query = await asyncio.wait_for(
                        self.query_queue.get(),
                        timeout=0.01  # 10ms timeout
                    )
                    batch.append(query)
                except asyncio.TimeoutError:
                    break

            if batch:
                # Execute batch with pipelining
                results = await self.execute_batch(batch)
                # Return results to waiting coroutines
                for query, result in zip(batch, results):
                    query['future'].set_result(result)

    async def retrieve_async(self, query_params):
        """Add query to batch queue"""
        future = asyncio.Future()
        await self.query_queue.put({
            'params': query_params,
            'future': future
        })
        return await future
```

2. **Redis Connection Pooling**
```python
from redis.asyncio import ConnectionPool, Redis

# Create connection pool (shared across agents)
pool = ConnectionPool(
    host='localhost',
    port=6379,
    max_connections=50,  # Allow concurrent connections
    decode_responses=False  # Binary for vectors
)

redis_client = Redis(connection_pool=pool)
```

3. **Read Replicas** (if concurrency exceeds single instance)
```python
# Master for writes, replicas for reads
master = Redis(host='redis-master', port=6379)
replicas = [
    Redis(host='redis-replica-1', port=6379),
    Redis(host='redis-replica-2', port=6379),
    Redis(host='redis-replica-3', port=6379)
]

class LoadBalancedMemoryRetrieval:
    def __init__(self, master, replicas):
        self.master = master
        self.replicas = replicas
        self.replica_idx = 0

    async def read(self, query):
        # Round-robin across replicas
        replica = self.replicas[self.replica_idx % len(self.replicas)]
        self.replica_idx += 1
        return await replica.execute_command(query)

    async def write(self, data):
        # All writes go to master
        return await self.master.execute_command(data)
```

---

## Memory Lifecycle

### Memory Creation

1. **Experience Recording**: After each action, create episodic memory
2. **Quality Filtering**: Only store if meets quality threshold
3. **Vector Encoding**: Encode state into 256-dim vector
4. **Storage**: Write to Redis with appropriate TTL

### Memory Retrieval

1. **Query Construction**: Build query with filters (regime, product, agent)
2. **Vector Search**: Execute similarity search in Redis
3. **Post-filtering**: Apply business logic filters
4. **Ranking**: Sort by relevance (distance + recency + reward)

### Memory Consolidation

**Nightly Process**:
```python
async def consolidate_memories():
    """
    Consolidate episodic memories into semantic knowledge

    Run nightly during low-trading hours
    """

    # Get all episodic memories from last 24h
    recent_memories = await memory_service.get_recent_episodic(hours=24)

    # Cluster similar experiences
    clusters = cluster_experiences(recent_memories)

    # For each cluster, create/update semantic memory
    for cluster in clusters:
        if len(cluster) >= 10:  # Minimum sample size
            # Extract pattern
            pattern = extract_pattern_from_cluster(cluster)

            # Check if pattern already exists
            existing = await memory_service.find_similar_pattern(pattern)

            if existing:
                # Update existing pattern with new data
                await memory_service.update_pattern(existing.id, cluster)
            else:
                # Create new semantic memory
                semantic_mem = SemanticMemory(
                    memory_type='PATTERN',
                    concept_vector=pattern.vector,
                    pattern_id=pattern.id,
                    conditions=pattern.conditions,
                    # ...
                )
                await memory_service.add_semantic(semantic_mem)
```

### Memory Pruning

```python
async def prune_old_memories():
    """Remove low-value memories to manage storage"""

    # Prune episodic memories older than 90 days
    await memory_service.delete_episodic_older_than(days=90)

    # Prune low-quality semantic memories
    # Keep only patterns with:
    # - Sharpe > 1.0 OR
    # - Access count > 100 in last 30 days
    await memory_service.prune_semantic(
        min_sharpe=1.0,
        min_access_count=100,
        access_window_days=30
    )
```

---

## Integration with MARL

### Centralized Training, Decentralized Execution (CTDE)

```python
class CentralizedTrainer:
    """
    Train agents centrally using shared memory pool

    Each agent executes independently but training uses global knowledge
    """

    def __init__(self, agents: List[TradingAgent], shared_memory: SharedMemoryPool):
        self.agents = agents
        self.shared_memory = shared_memory

    async def train_step(self):
        """Single training iteration"""

        # Collect experiences from all agents
        all_experiences = []
        for agent in self.agents:
            experiences = await agent.get_recent_experiences(batch_size=32)
            all_experiences.extend(experiences)

        # Shuffle for i.i.d. assumption
        random.shuffle(all_experiences)

        # Train each agent on mixed batch
        for agent in self.agents:
            loss = await agent.train_on_batch(all_experiences)

        # Update shared memory with high-quality experiences
        for exp in all_experiences:
            quality = self.calculate_quality(exp)
            if quality > 0.7:
                await self.shared_memory.add_shared_experience(exp, quality)
```

---

## Benchmarking Plan

### Latency Testing

```python
async def benchmark_memory_retrieval():
    """
    Test Redis vector search latency under load

    Target: < 1ms p50, < 5ms p99
    """

    latencies = []

    # Generate test queries
    for _ in range(10000):
        state_vector = np.random.randn(256).astype(np.float32)

        start = time.perf_counter()
        results = await memory_service.retrieve_similar_experiences(
            state_vector,
            agent_id='test_agent',
            top_k=10
        )
        end = time.perf_counter()

        latencies.append((end - start) * 1000)  # Convert to ms

    print(f"P50 latency: {np.percentile(latencies, 50):.2f}ms")
    print(f"P95 latency: {np.percentile(latencies, 95):.2f}ms")
    print(f"P99 latency: {np.percentile(latencies, 99):.2f}ms")
    print(f"Max latency: {max(latencies):.2f}ms")
```

### Concurrency Testing

```python
async def benchmark_concurrent_queries(num_agents: int = 10):
    """
    Test Redis under concurrent load from multiple agents
    """

    async def agent_workload(agent_id: str):
        latencies = []
        for _ in range(100):
            state_vector = np.random.randn(256).astype(np.float32)
            start = time.perf_counter()
            await memory_service.retrieve_similar_experiences(
                state_vector,
                agent_id=agent_id,
                top_k=10
            )
            end = time.perf_counter()
            latencies.append((end - start) * 1000)
        return latencies

    # Run workloads concurrently
    tasks = [agent_workload(f'agent_{i}') for i in range(num_agents)]
    results = await asyncio.gather(*tasks)

    all_latencies = [lat for agent_lats in results for lat in agent_lats]

    print(f"Concurrent {num_agents} agents:")
    print(f"  P50: {np.percentile(all_latencies, 50):.2f}ms")
    print(f"  P99: {np.percentile(all_latencies, 99):.2f}ms")
```

---

## References

1. **Zong et al. (2024)**: "MacroHFT: Memory Augmented Context-aware Reinforcement Learning On High Frequency Trading"
   - Introduced memory mechanism for regime adaptation in HFT

2. **Wei et al. (2024)**: "Multi-Agent Reinforcement Learning for High-Frequency Trading Strategy Optimization"
   - Applied MARL to HFT with strong results (Sharpe 2.87)

3. **Ning et al. (2024)**: "A survey on multi-agent reinforcement learning and its applications"
   - Comprehensive overview of MARL challenges and solutions

4. **Redis Benchmarks (2024)**: Vector database performance comparisons
   - Redis: 3.4× QPS vs Qdrant, 4× lower latency vs Milvus

---

**Last Updated**: 2025-10-31
**Status**: Planning Phase - Integrated from research
**Next**: Implement memory service and benchmark
