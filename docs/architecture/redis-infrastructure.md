# Redis Infrastructure and Benchmarking

## Overview

Redis serves as the **primary vector database** for Coinswarm's agent memory system. It provides sub-millisecond latency for memory retrieval, which is critical for high-frequency trading applications where agents must quickly recall similar past experiences.

**Why Redis?**
- **3.4× higher QPS** than Qdrant (Redis benchmarks, 2024)
- **4× lower latency** than Milvus for recall ≥ 0.98
- **Sub-millisecond latency** for single-threaded queries
- **In-memory architecture** optimized for speed
- **Mature ecosystem** with strong community support

**Critical for**: Memory-augmented multi-agent reinforcement learning in HFT environment where latency = alpha.

---

## Benchmark Results Summary

### Source: Redis Vector Database Benchmarks (2024)

**Test Configuration**:
- Hardware: Consistent across all DBs
- Dataset: 1M vectors, 768 dimensions
- Query: Top-10 similarity search
- Metric: Recall @ 0.98

**Results**:

| Database | QPS (Queries/Sec) | Latency (ms) | Relative to Redis |
|----------|-------------------|--------------|-------------------|
| **Redis** | **12,000** | **0.8** | 1.0× (baseline) |
| Qdrant | 3,500 | 2.8 | 0.29× QPS, 3.5× latency |
| Milvus | 3,000 | 3.2 | 0.25× QPS, 4.0× latency |
| Pinecone | 4,500 | 2.2 | 0.38× QPS, 2.8× latency |
| Weaviate | 4,000 | 2.5 | 0.33× QPS, 3.1× latency |

**Implication**: For our multi-agent system where 10+ agents may query memory simultaneously, Redis's throughput advantage is critical.

### Concurrency Caveat

**Source**: Qdrant benchmarks comparing Redis under concurrent load

**Finding**: Redis latency increases with concurrent queries:
- 1 thread: 0.8ms
- 10 threads: 2.5ms
- 50 threads: 8.0ms
- 100 threads: 15ms

**Mitigation Strategy**:
1. Query batching (combine multiple requests)
2. Connection pooling (reuse connections)
3. Read replicas (distribute read load)
4. Strategic caching (reduce query frequency)

---

## Architecture

### Deployment Topology

```
┌─────────────────────────────────────────────────────────────────┐
│                        Agent Layer                               │
│  10-50 concurrent agents querying memory                         │
└────────────────────────┬────────────────────────────────────────┘
                         │ Queries
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Memory Retrieval Service                        │
│  • Query batching (10ms window)                                  │
│  • Connection pooling (50 connections)                           │
│  • Request deduplication                                         │
│  • Circuit breaker                                               │
└──────────┬────────────────────┬──────────────────────┬──────────┘
           │                    │                      │
           ▼                    ▼                      ▼
    ┌──────────┐         ┌──────────┐         ┌──────────┐
    │  Redis   │         │  Redis   │         │  Redis   │
    │  Master  │────────▶│ Replica 1│         │ Replica 2│
    │ (Write)  │         │  (Read)  │         │  (Read)  │
    └──────────┘         └──────────┘         └──────────┘
         │
         ▼
   ┌──────────────┐
   │ Redis AOF    │
   │ (Persistence)│
   └──────────────┘
```

### Configuration

#### redis.conf (Master)

```conf
# === Memory ===
maxmemory 16gb
maxmemory-policy allkeys-lru  # Evict LRU when full

# === Persistence ===
# For production: Enable AOF for durability
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec  # Balance between durability and performance

# For maximum performance (test/dev only):
# save ""  # Disable RDB
# appendonly no  # Disable AOF
# WARNING: Memory-only, data loss on crash!

# === Networking ===
bind 0.0.0.0
port 6379
tcp-backlog 511
timeout 0
tcp-keepalive 300

# === Performance ===
io-threads 4  # Multi-threaded I/O
io-threads-do-reads yes
lazyfree-lazy-eviction yes
lazyfree-lazy-expire yes

# === Modules ===
loadmodule /usr/lib/redis/modules/redisearch.so
loadmodule /usr/lib/redis/modules/redisai.so  # Optional, for inference

# === Limits ===
maxclients 10000
```

#### redis.conf (Replica)

```conf
# Same as master, plus:
replicaof redis-master 6379
replica-read-only yes
replica-serve-stale-data yes  # Continue serving during sync
```

---

## Vector Index Configuration

### Episodic Memory Index

```python
import redis

r = redis.Redis(host='localhost', port=6379, decode_responses=False)

# Create index for episodic memories
r.execute_command(
    'FT.CREATE', 'episodic_memory_idx',
    'ON', 'HASH',
    'PREFIX', '1', 'episodic:',
    'SCHEMA',
    # Vector field for state embeddings
    'state_vector', 'VECTOR', 'HNSW', '10',
        'DIM', '256',                    # 256-dimensional embeddings
        'TYPE', 'FLOAT32',
        'DISTANCE_METRIC', 'COSINE',
        'INITIAL_CAP', '100000',         # Pre-allocate for 100k vectors
        'M', '16',                       # HNSW connections per node
        'EF_CONSTRUCTION', '200',        # Build-time quality (higher = better, slower)
        'EF_RUNTIME', '10',              # Query-time quality (lower = faster)
    # Filterable fields
    'agent_id', 'TAG', 'SORTABLE',
    'product_id', 'TAG', 'SORTABLE',
    'regime', 'TAG', 'SORTABLE',
    'reward', 'NUMERIC', 'SORTABLE',
    'timestamp', 'NUMERIC', 'SORTABLE',
    'terminal', 'TAG'
)
```

**Index Type: HNSW (Hierarchical Navigable Small World)**
- **Pros**: Logarithmic search time, scales to millions of vectors
- **Cons**: Approximate search (not exact)
- **When**: Use for > 100k vectors

**Alternative: FLAT index**
```python
# For smaller datasets (< 100k), use FLAT for exact search
'state_vector', 'VECTOR', 'FLAT', '6',
    'DIM', '256',
    'TYPE', 'FLOAT32',
    'DISTANCE_METRIC', 'COSINE'
```

### Semantic Memory Index

```python
# Create index for semantic memories (patterns, regimes, strategies)
r.execute_command(
    'FT.CREATE', 'semantic_memory_idx',
    'ON', 'HASH',
    'PREFIX', '1', 'semantic:',
    'SCHEMA',
    'concept_vector', 'VECTOR', 'HNSW', '10',
        'DIM', '256',
        'TYPE', 'FLOAT32',
        'DISTANCE_METRIC', 'COSINE',
        'INITIAL_CAP', '10000',
        'M', '32',                       # Higher M for better recall
        'EF_CONSTRUCTION', '400',        # Higher construction quality
        'EF_RUNTIME', '20',
    'memory_type', 'TAG',                # PATTERN, REGIME, STRATEGY
    'regime_name', 'TAG',
    'sharpe_ratio', 'NUMERIC', 'SORTABLE',
    'win_rate', 'NUMERIC', 'SORTABLE',
    'access_count', 'NUMERIC', 'SORTABLE',
    'last_accessed', 'NUMERIC', 'SORTABLE'
)
```

---

## Query Patterns

### Basic Vector Similarity Search

```python
import numpy as np

async def retrieve_similar_experiences(
    redis_client: redis.Redis,
    state_vector: np.ndarray,
    agent_id: str,
    top_k: int = 10
) -> list:
    """
    Find similar past experiences using vector similarity
    """

    # Convert vector to bytes
    query_vector = state_vector.astype(np.float32).tobytes()

    # Build query
    query = (
        f"(@agent_id:{{{agent_id}}}) "
        "=>[KNN $K @state_vector $BLOB AS score]"
    )

    # Execute search
    result = redis_client.ft('episodic_memory_idx').search(
        query,
        query_params={
            'K': top_k,
            'BLOB': query_vector
        }
    ).docs

    return result
```

### Hybrid Search (Vector + Filters)

```python
async def retrieve_regime_specific_experiences(
    redis_client: redis.Redis,
    state_vector: np.ndarray,
    agent_id: str,
    regime: str,
    product_id: str,
    min_reward: float = 0.0,
    top_k: int = 10
) -> list:
    """
    Vector search with multiple filters
    """

    query_vector = state_vector.astype(np.float32).tobytes()

    # Combine filters with vector search
    query = (
        f"(@agent_id:{{{agent_id}}}) "
        f"(@regime:{{{regime}}}) "
        f"(@product_id:{{{product_id}}}) "
        f"(@reward:[{min_reward} +inf]) "
        "=>[KNN $K @state_vector $BLOB AS score]"
    )

    result = redis_client.ft('episodic_memory_idx').search(
        query,
        query_params={'K': top_k, 'BLOB': query_vector}
    ).docs

    return result
```

### Range + Limit + Sort

```python
async def get_recent_high_reward_memories(
    redis_client: redis.Redis,
    agent_id: str,
    hours: int = 24,
    min_reward: float = 0.01,
    limit: int = 100
) -> list:
    """
    Get recent profitable experiences (no vector search)
    """

    timestamp_cutoff = time.time() - (hours * 3600)

    query = (
        f"(@agent_id:{{{agent_id}}}) "
        f"(@timestamp:[{timestamp_cutoff} +inf]) "
        f"(@reward:[{min_reward} +inf])"
    )

    result = redis_client.ft('episodic_memory_idx').search(
        query
    ).sort_by('reward', asc=False).paging(0, limit).docs

    return result
```

---

## Performance Optimization

### 1. Query Batching

**Problem**: Each query has overhead; many small queries are inefficient.

**Solution**: Batch queries together.

```python
class QueryBatcher:
    def __init__(self, redis_client: redis.Redis, batch_window_ms: int = 10):
        self.redis = redis_client
        self.batch_window = batch_window_ms / 1000.0
        self.pending_queries = []
        self.pending_futures = []

    async def add_query(self, query_fn, *args, **kwargs):
        """Add query to batch"""
        future = asyncio.Future()
        self.pending_queries.append((query_fn, args, kwargs))
        self.pending_futures.append(future)

        # If this is first query, start timer
        if len(self.pending_queries) == 1:
            asyncio.create_task(self._flush_after_delay())

        return await future

    async def _flush_after_delay(self):
        """Flush batch after window expires"""
        await asyncio.sleep(self.batch_window)
        await self._flush_batch()

    async def _flush_batch(self):
        """Execute all pending queries in pipeline"""
        if not self.pending_queries:
            return

        # Use Redis pipeline for batching
        pipe = self.redis.pipeline()

        for query_fn, args, kwargs in self.pending_queries:
            query_fn(pipe, *args, **kwargs)

        # Execute all at once
        results = await pipe.execute()

        # Resolve futures
        for future, result in zip(self.pending_futures, results):
            future.set_result(result)

        # Clear batch
        self.pending_queries.clear()
        self.pending_futures.clear()
```

### 2. Connection Pooling

```python
from redis.asyncio import ConnectionPool, Redis

# Shared connection pool
pool = ConnectionPool(
    host='localhost',
    port=6379,
    max_connections=50,      # Support 50 concurrent agents
    decode_responses=False,  # Binary mode for vectors
    socket_keepalive=True,
    socket_connect_timeout=5,
    health_check_interval=30
)

# All agents share this pool
redis_client = Redis(connection_pool=pool)
```

### 3. Read Replicas with Load Balancing

```python
class ReplicaLoadBalancer:
    def __init__(self, master_host: str, replica_hosts: list):
        self.master = Redis(host=master_host, port=6379)
        self.replicas = [Redis(host=h, port=6379) for h in replica_hosts]
        self.replica_idx = 0

    async def read(self, query_fn, *args, **kwargs):
        """Read from replica (round-robin)"""
        replica = self.replicas[self.replica_idx % len(self.replicas)]
        self.replica_idx += 1
        return await query_fn(replica, *args, **kwargs)

    async def write(self, write_fn, *args, **kwargs):
        """Write to master only"""
        return await write_fn(self.master, *args, **kwargs)
```

### 4. Caching Layer

```python
from functools import lru_cache
import hashlib

class CachedMemoryRetrieval:
    def __init__(self, redis_client: redis.Redis, cache_ttl: int = 60):
        self.redis = redis_client
        self.cache = {}
        self.cache_ttl = cache_ttl

    async def retrieve_with_cache(
        self,
        state_vector: np.ndarray,
        agent_id: str,
        regime: str,
        top_k: int
    ):
        """Cache results for identical queries"""

        # Create cache key
        cache_key = self._cache_key(state_vector, agent_id, regime, top_k)

        # Check cache
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if time.time() - entry['timestamp'] < self.cache_ttl:
                return entry['result']

        # Cache miss - query Redis
        result = await self.retrieve_similar_experiences(
            state_vector, agent_id, regime, top_k
        )

        # Store in cache
        self.cache[cache_key] = {
            'result': result,
            'timestamp': time.time()
        }

        return result

    def _cache_key(self, vector, agent_id, regime, top_k):
        """Generate cache key from query parameters"""
        vector_hash = hashlib.md5(vector.tobytes()).hexdigest()
        return f"{agent_id}:{regime}:{vector_hash}:{top_k}"
```

---

## Monitoring and Observability

### Key Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Query latency
memory_query_latency = Histogram(
    'redis_memory_query_seconds',
    'Latency of memory retrieval queries',
    ['query_type', 'agent_id']
)

# Query rate
memory_query_total = Counter(
    'redis_memory_queries_total',
    'Total memory queries',
    ['query_type', 'status']
)

# Cache hit rate
memory_cache_hits = Counter(
    'redis_memory_cache_hits_total',
    'Cache hits'
)

memory_cache_misses = Counter(
    'redis_memory_cache_misses_total',
    'Cache misses'
)

# Redis memory usage
redis_memory_bytes = Gauge(
    'redis_memory_usage_bytes',
    'Redis memory usage'
)

# Connection pool
redis_connections_active = Gauge(
    'redis_connections_active',
    'Active Redis connections'
)
```

### Instrumentation Example

```python
async def retrieve_with_metrics(
    redis_client: redis.Redis,
    state_vector: np.ndarray,
    agent_id: str,
    top_k: int
):
    """Retrieve with Prometheus metrics"""

    start = time.time()

    try:
        result = await retrieve_similar_experiences(
            redis_client, state_vector, agent_id, top_k
        )

        # Record success
        memory_query_total.labels(
            query_type='vector_similarity',
            status='success'
        ).inc()

        return result

    except Exception as e:
        # Record failure
        memory_query_total.labels(
            query_type='vector_similarity',
            status='error'
        ).inc()
        raise

    finally:
        # Record latency
        duration = time.time() - start
        memory_query_latency.labels(
            query_type='vector_similarity',
            agent_id=agent_id
        ).observe(duration)
```

---

## Benchmarking Plan

### Phase 1: Single-Agent Baseline

**Objective**: Establish baseline latency and QPS without concurrency.

```python
async def benchmark_single_agent():
    """Benchmark single-threaded query performance"""

    redis_client = Redis(host='localhost', port=6379)

    # Load test data (10k memories)
    await load_test_memories(redis_client, count=10000)

    latencies = []

    # Run 1000 queries
    for i in range(1000):
        state_vector = np.random.randn(256).astype(np.float32)

        start = time.perf_counter()
        result = await retrieve_similar_experiences(
            redis_client,
            state_vector,
            agent_id='test_agent',
            top_k=10
        )
        duration = (time.perf_counter() - start) * 1000  # ms

        latencies.append(duration)

    # Report
    print(f"Single-agent baseline:")
    print(f"  Mean latency: {np.mean(latencies):.2f}ms")
    print(f"  P50 latency: {np.percentile(latencies, 50):.2f}ms")
    print(f"  P95 latency: {np.percentile(latencies, 95):.2f}ms")
    print(f"  P99 latency: {np.percentile(latencies, 99):.2f}ms")
    print(f"  Max latency: {max(latencies):.2f}ms")
```

**Expected Results**:
- P50: < 1ms
- P95: < 2ms
- P99: < 5ms

### Phase 2: Concurrent Agents

**Objective**: Measure latency degradation under concurrent load.

```python
async def benchmark_concurrent_agents(num_agents: int):
    """Benchmark with multiple concurrent agents"""

    redis_client = Redis(host='localhost', port=6379)

    async def agent_workload(agent_id: str, num_queries: int = 100):
        latencies = []
        for _ in range(num_queries):
            state_vector = np.random.randn(256).astype(np.float32)

            start = time.perf_counter()
            await retrieve_similar_experiences(
                redis_client, state_vector, agent_id, top_k=10
            )
            duration = (time.perf_counter() - start) * 1000

            latencies.append(duration)

        return latencies

    # Run workloads concurrently
    tasks = [
        agent_workload(f'agent_{i}', 100)
        for i in range(num_agents)
    ]

    results = await asyncio.gather(*tasks)

    # Flatten all latencies
    all_latencies = [lat for agent_lats in results for lat in agent_lats]

    print(f"\nConcurrent {num_agents} agents:")
    print(f"  P50: {np.percentile(all_latencies, 50):.2f}ms")
    print(f"  P95: {np.percentile(all_latencies, 95):.2f}ms")
    print(f"  P99: {np.percentile(all_latencies, 99):.2f}ms")
    print(f"  Max: {max(all_latencies):.2f}ms")

# Test at different concurrency levels
for num_agents in [1, 5, 10, 20, 50]:
    await benchmark_concurrent_agents(num_agents)
```

**Expected Results** (with optimizations):
- 10 agents: P99 < 10ms
- 20 agents: P99 < 15ms
- 50 agents: P99 < 30ms

### Phase 3: Production Workload Simulation

**Objective**: Simulate realistic trading workload.

```python
async def benchmark_production_workload():
    """Simulate realistic trading scenario"""

    # 10 trading agents (1 per product)
    # Each agent queries memory:
    # - Every 5s for pattern matching
    # - On every trade (variable)

    redis_client = Redis(host='localhost', port=6379)

    # Simulate 1 hour of trading
    duration_seconds = 3600
    query_interval = 5  # seconds
    num_agents = 10

    async def trading_agent_simulation(agent_id: str):
        queries = 0
        latencies = []

        for _ in range(duration_seconds // query_interval):
            state_vector = np.random.randn(256).astype(np.float32)

            start = time.perf_counter()
            await retrieve_similar_experiences(
                redis_client, state_vector, agent_id, top_k=10
            )
            duration = (time.perf_counter() - start) * 1000

            latencies.append(duration)
            queries += 1

            await asyncio.sleep(query_interval)

        return queries, latencies

    # Run all agents concurrently
    tasks = [
        trading_agent_simulation(f'agent_{i}')
        for i in range(num_agents)
    ]

    results = await asyncio.gather(*tasks)

    total_queries = sum(r[0] for r in results)
    all_latencies = [lat for _, lats in results for lat in lats]

    print(f"\nProduction workload (1 hour):")
    print(f"  Total queries: {total_queries}")
    print(f"  QPS: {total_queries / duration_seconds:.2f}")
    print(f"  P50 latency: {np.percentile(all_latencies, 50):.2f}ms")
    print(f"  P99 latency: {np.percentile(all_latencies, 99):.2f}ms")
```

---

## Deployment

### Docker Compose

```yaml
version: '3.8'

services:
  redis-master:
    image: redis/redis-stack-server:latest
    container_name: redis-master
    ports:
      - "6379:6379"
    volumes:
      - redis-master-data:/data
      - ./redis.conf:/redis-stack.conf
    command: redis-server /redis-stack.conf
    restart: unless-stopped

  redis-replica-1:
    image: redis/redis-stack-server:latest
    container_name: redis-replica-1
    ports:
      - "6380:6379"
    volumes:
      - redis-replica-1-data:/data
    command: redis-server --replicaof redis-master 6379
    depends_on:
      - redis-master
    restart: unless-stopped

  redis-replica-2:
    image: redis/redis-stack-server:latest
    container_name: redis-replica-2
    ports:
      - "6381:6379"
    volumes:
      - redis-replica-2-data:/data
    command: redis-server --replicaof redis-master 6379
    depends_on:
      - redis-master
    restart: unless-stopped

volumes:
  redis-master-data:
  redis-replica-1-data:
  redis-replica-2-data:
```

---

## Failure Scenarios and Recovery

### Scenario 1: Master Failure

**Detection**: Replica promotion monitoring

**Recovery**:
```bash
# Promote replica-1 to master
redis-cli -h redis-replica-1 -p 6379 REPLICAOF NO ONE

# Point application to new master
# Update DNS or use Redis Sentinel for automatic failover
```

### Scenario 2: Out of Memory

**Detection**: Monitor `redis_memory_usage_bytes` metric

**Recovery**:
```bash
# Option 1: Increase maxmemory
CONFIG SET maxmemory 32gb

# Option 2: More aggressive eviction
CONFIG SET maxmemory-policy allkeys-lru

# Option 3: Manual pruning
# Delete old episodic memories
FT.SEARCH episodic_memory_idx "@timestamp:[-inf $(date -d '90 days ago' +%s)]" LIMIT 0 0
# Then delete via script
```

### Scenario 3: Slow Queries

**Detection**: P99 latency > 50ms

**Diagnosis**:
```bash
# Enable slow log
CONFIG SET slowlog-log-slower-than 10000  # 10ms

# View slow queries
SLOWLOG GET 10
```

**Remediation**:
- Check EF_RUNTIME setting (lower = faster)
- Add replicas to distribute load
- Enable query batching
- Review index configuration

---

## References

1. **Redis Benchmarking results for vector databases** (2024)
   - 3.4× higher QPS than Qdrant, 4× lower latency than Milvus

2. **Redis for vector database** (solutions page)
   - Sub-millisecond latency, in-memory architecture

3. **Announcing faster Redis Query Engine** (2024)
   - 16× throughput improvement, leads top 7 vector DBs

4. **Vector Database Benchmark – Overview** (Pixion, 2025)
   - Comparison across Redis, Milvus, Chroma, Qdrant

5. **Vector Database Benchmarks – Qdrant** (Qdrant website)
   - Concurrency effects on Redis latency

---

**Last Updated**: 2025-10-31
**Status**: Planning Phase - Ready for implementation
**Next**: Deploy test Redis cluster and run benchmarks
