# Quorum-Governed Memory System Specification

## Overview

This document specifies Coinswarm's **quorum-governed, self-improving memory system** for multi-agent trading. The system enables **online learning without weight retrains** where memory improves with every trade, and all memory mutations require **3-vote consensus** from independent memory manager agents.

**Key Innovation**: Combines Neural Episodic Control (NEC), regime-gated retrieval, pattern semantics, and Byzantine fault-tolerant quorum consensus for safe, auditable, real-time learning.

**Status**: Implementation Specification (Ready to Build)

---

## 0. Objective

**Primary Goal**: Online learning without weight retrains. Memory improves on every trade.

**Safety Constraint**: All memory mutations require `quorum=3` agent votes.

**Performance Target**: Sub-2ms end-to-end latency from retrieval to commit.

---

## 1. System Roles

### Trading Bots
**Responsibilities**:
- Compute state embeddings φ ∈ R^d
- Request actions from memory-augmented policy
- Execute trades
- Submit memory-change proposals after trade completion

**Count**: Variable (2-50 bots per deployment)

### Memory Managers
**Responsibilities**:
- Independent evaluators of memory change proposals
- Majority vote on proposals (deterministic decision function)
- Rotating coordinator commits accepted changes
- Audit trail maintenance

**Count**: M ≥ 3 (typically 3-5 for Phase A/B, up to 7 for production)

**Critical**: Each manager runs identical decision function but independently

### Memory Store (Hot)
**Technology**: Redis + RediSearch
**Purpose**: In-RAM vector storage for sub-millisecond retrieval
**Scope**: Episodic memories (per-bot), patterns (shared), regime state (global)

### Memory Store (Cold) [Optional]
**Technology**: Qdrant or Milvus
**Purpose**: Archive and pattern backfills
**Scope**: Historical data > 30 days

### Message Bus
**Technology**: NATS or Redis Streams
**Purpose**: Proposals, votes, commits, audit log
**Guarantee**: At-least-once delivery, ordered per symbol

---

## 2. Memory Tiers

### Episodic Memory (Hot, Per-Bot)

**Structure**: Tuples `(φ, a, r, o, meta)`

**Fields**:
- `φ`: State embedding vector ∈ R^384
- `a`: Action taken (BUY/SELL/HOLD/SIZE_±)
- `r`: Realized reward (PnL)
- `o`: Outcome metrics (slippage, fill time, fill ratio)
- `meta`: Symbol, regime, timestamp, agent ID

**Storage**: Redis hash per entry
**Index**: HNSW vector index for kNN retrieval
**Retention**: 30 days (configurable)

### Pattern Memory (Shared, Global)

**Structure**: Clusters of episodic entries with statistics

**Fields**:
- `n`: Sample size
- `μ_pnl`: Mean PnL
- `σ`: Standard deviation
- `win_rate`: Win rate
- `SR`: Sharpe ratio
- `tail_q05`: 5th percentile (downside tail)
- `tail_q95`: 95th percentile (upside tail)
- `slip_mu`: Mean slippage (bps)
- `regime`: Associated regime tag
- `last_updated`: Timestamp

**Maintenance**: Refreshed every 5-10 minutes via mini-batch k-means

**Promotion Rules**:
- Enable influence when: `n ≥ N_promote`, `SR ≥ S_min`, `DD ≤ DD_max`
- Deprecate when: Live SR underperforms backtest by Δ for L windows

### Regime Memory (Shared, Global)

**Structure**: Discrete state R_t from microstructure and session features

**Dimensions**:
- `vol`: Volatility (low | med | high)
- `spr`: Spread (tight | wide)
- `trend`: Direction (up | down | flat)
- `sess`: Session (US | EU | APAC)
- `ver`: Version counter

**Update Frequency**: Real-time (sub-second)

---

## 3. Data Schema (Redis)

### Hash Keys and Types

```redis
# Episodic memory entry
hash:epi:{bot_id}:{entry_id}
  v        BLOB          # float32[384] embedding
  ts       NUMERIC       # epoch seconds
  sym      TAG           # symbol (BTC-USD, etc.)
  reg      TAG           # regime (R1, R2, R3, ...)
  a        TAG           # action (BUY/SELL/HOLD/SIZE_+/SIZE_-)
  pnl      NUMERIC       # realized PnL (float)
  rr       NUMERIC       # reward ratio
  slip     NUMERIC       # slippage in bps
  ttf      NUMERIC       # time-to-fill milliseconds
  fillr    NUMERIC       # fill ratio (0-1)
  w        NUMERIC       # episodic weight

# Pattern statistics
hash:pattern:{pattern_id}
  n        NUMERIC       # sample size
  mu       NUMERIC       # mean PnL
  sig      NUMERIC       # std dev
  sr       NUMERIC       # Sharpe ratio
  t05      NUMERIC       # 5th percentile
  t95      NUMERIC       # 95th percentile
  slip_mu  NUMERIC       # mean slippage
  reg      TAG           # regime
  last     NUMERIC       # last updated timestamp

# Current regime state
hash:regime:current
  vol      TAG           # low|med|high
  spr      TAG           # tight|wide
  trend    TAG           # up|down|flat
  sess     TAG           # US|EU|APAC
  ver      NUMERIC       # version

# Prioritized replay/refresh queue per bot
zset:elig:{bot_id}
  score: priority
  member: entry_id
```

### Vector Index Configuration

```redis
FT.CREATE idx:epi
  ON HASH
  PREFIX 1 "hash:epi:"
  SCHEMA
    v VECTOR HNSW 384
      TYPE FLOAT32
      DIM 384
      M 16
      EF_CONSTRUCTION 200
      EF_RUNTIME 64
      DISTANCE_METRIC COSINE
    sym TAG
    reg TAG
    a TAG
    ts NUMERIC SORTABLE
    pnl NUMERIC SORTABLE
    w NUMERIC SORTABLE
```

**Embedding Dimension**: `d = 384`
- Cache-friendly (fits in L1/L2 cache)
- Fast dot products on modern CPUs
- Good balance between expressiveness and speed

---

## 4. Retrieval (Read Path)

### Algorithm

Given current state `s_t`:

**Step 1: Embed State**
```python
φ_t = embed(s_t)  # deterministic embedding function
```

**Step 2: Get Current Regime**
```python
R_t = regime_now()  # from hash:regime:current
```

**Step 3: kNN Query**
```python
neighbors = knn_query(
    index='idx:epi',
    vector=φ_t,
    k=16,
    filters={
        'sym': product_id,
        'reg': R_t,
        'ts': f'[-inf {current_timestamp}]'  # no future leakage
    }
)
```

**Step 4: Aggregate Neighbor Statistics**
```python
for action in [BUY, SELL, HOLD]:
    action_neighbors = [n for n in neighbors if n.a == action]

    stats[action] = {
        'expected_pnl': weighted_mean([n.pnl for n in action_neighbors],
                                       weights=[kernel(φ_t, n.v) for n in action_neighbors]),
        'variance': weighted_var([n.pnl for n in action_neighbors]),
        'stop_out_prob': mean([n.pnl < -threshold for n in action_neighbors]),
        'expected_slip': mean([n.slip for n in action_neighbors])
    }
```

**Step 5: Pattern Lookup**
```python
# Assign pattern via nearest centroid
pattern_id = nearest_pattern_centroid(φ_t, R_t)

pattern_stats = redis.hgetall(f'hash:pattern:{pattern_id}')
# Returns: {n, mu, sig, sr, t05, t95, slip_mu}
```

**Step 6: Action Scoring**
```python
for action in [BUY, SELL, HOLD]:
    score[action] = (
        w_model * model_logit[action]                    # NN policy output
        + w_mem * stats[action]['expected_pnl']          # memory-based expectation
        + β * UCB(action, stats[action])                 # exploration bonus
        - λ * risk(action, neighbors, pattern, inventory) # risk penalty
    )

best_action = argmax(score)
```

**UCB (Upper Confidence Bound)**:
```python
def UCB(action, stats):
    if stats['n'] == 0:
        return float('inf')  # encourage exploration
    return stats['expected_pnl'] + β * sqrt(log(total_queries) / stats['n'])
```

**Risk Penalty**:
```python
def risk(action, neighbors, pattern, inventory):
    penalties = []

    # Tail risk
    if pattern['t05'] < -tail_threshold:
        penalties.append(tail_penalty)

    # Slippage risk
    if pattern['slip_mu'] > slip_threshold:
        penalties.append(slip_penalty)

    # Inventory risk
    if (action == BUY and inventory > max_long) or \
       (action == SELL and inventory < -max_short):
        penalties.append(inventory_penalty)

    return sum(penalties)
```

**Hard Caps** (applied after scoring):
- Position size limits
- Daily loss limits
- Exposure caps per symbol

---

## 5. Update (Write Path) via Quorum

### After Trade Exit

**Step 1: Compute Reward and Advantage**
```python
r_t = realized_pnl  # from trade execution
δ_t = r_t - E[r | φ_t, a_t]  # advantage = actual - expected
```

**Step 2: Form Credit Assignment Proposal**
```python
proposal = {
    'type': 'credit_update',
    'change_id': uuid4(),
    'proposer': bot_id,
    'timestamp': time.time(),

    # Affected entries
    'ids': [n.id for n in neighbors],

    # Updates (kernel-weighted credit assignment)
    'deltas': {
        n.id: α * kernel(φ_t, n.v) * δ_t
        for n in neighbors
    },

    # Safety guards
    'guards': {
        'regime': R_t,
        'symbol': product_id,
        'bounds': {
            'delta_max': 0.05,
            'w_min': 0.1,
            'w_max': 10.0
        }
    }
}
```

**Kernel Function** (RBF kernel):
```python
def kernel(φ_i, φ_j, σ=1.0):
    """Radial basis function kernel for credit assignment"""
    distance = np.linalg.norm(φ_i - φ_j)
    return np.exp(-(distance ** 2) / (2 * σ ** 2))
```

**Step 3: Publish Proposal**
```python
nats_client.publish('mem.propose', json.dumps(proposal))
```

---

## 6. Memory Manager Decision Function

### Deterministic Evaluation

**Inputs**:
- Proposal (change request)
- Snapshot of store indices
- Safety parameters (config)

**Checks**:

#### 1. Regime Consistency
```python
def check_regime(proposal):
    current_regime = redis.hget('hash:regime:current', 'ver')
    if proposal['guards']['regime'] != current_regime:
        return False, "STALE_REGIME"
    return True, None
```

#### 2. Support (Cluster Validity)
```python
def check_support(proposal):
    for entry_id in proposal['ids']:
        # Get pattern assignment
        pattern_id = get_pattern_assignment(entry_id)
        pattern = redis.hgetall(f'hash:pattern:{pattern_id}')

        if int(pattern['n']) < config.n_min_cluster:
            return False, f"INSUFFICIENT_SUPPORT:{entry_id}"

        if float(pattern['sr']) < config.SR_min_cluster:
            return False, f"LOW_SHARPE_CLUSTER:{entry_id}"

    return True, None
```

#### 3. Bounds Check
```python
def check_bounds(proposal):
    for entry_id, delta in proposal['deltas'].items():
        # Check delta magnitude
        if abs(delta) > proposal['guards']['bounds']['delta_max']:
            return False, f"DELTA_TOO_LARGE:{entry_id}"

        # Check resulting weight
        current_w = float(redis.hget(f'hash:epi:*:{entry_id}', 'w'))
        new_w = current_w + delta

        w_min = proposal['guards']['bounds']['w_min']
        w_max = proposal['guards']['bounds']['w_max']

        if not (w_min <= new_w <= w_max):
            return False, f"WEIGHT_OUT_OF_BOUNDS:{entry_id}"

    return True, None
```

#### 4. Impact Estimate (Fast Proxy)
```python
def check_impact(proposal):
    """Estimate impact on Sharpe and drawdown"""

    # Get affected neighbors
    neighbor_pnls = []
    neighbor_weights = []

    for entry_id in proposal['ids']:
        key = find_redis_key(entry_id)  # hash:epi:{bot}:{id}
        pnl = float(redis.hget(key, 'pnl'))
        w = float(redis.hget(key, 'w'))
        delta = proposal['deltas'][entry_id]

        neighbor_pnls.append(pnl)
        neighbor_weights.append(w + delta)

    # Estimate new Sharpe
    weighted_returns = np.array(neighbor_pnls) * np.array(neighbor_weights)
    new_sharpe = np.mean(weighted_returns) / (np.std(weighted_returns) + 1e-9)

    # Compare to current
    old_sharpe = get_current_sharpe(proposal['guards']['symbol'])

    delta_sharpe = new_sharpe - old_sharpe

    if delta_sharpe < config.epsilon_gain:
        return False, f"INSUFFICIENT_GAIN:{delta_sharpe:.4f}"

    # Estimate drawdown (simple proxy)
    cumulative = np.cumsum(weighted_returns)
    running_max = np.maximum.accumulate(cumulative)
    drawdown = np.min(cumulative - running_max)

    if abs(drawdown) > config.max_drawdown_pct / 100:
        return False, f"DRAWDOWN_RISK:{drawdown:.4f}"

    return True, None
```

#### 5. Cooldown (Rate Limiting)
```python
def check_cooldown(proposal):
    """Prevent too-frequent updates per symbol"""

    symbol = proposal['guards']['symbol']
    last_update_key = f'cooldown:{symbol}'

    last_update = redis.get(last_update_key)

    if last_update:
        elapsed_ms = (time.time() - float(last_update)) * 1000

        if elapsed_ms < config.commit_cooldown_ms_per_symbol:
            return False, f"COOLDOWN:{elapsed_ms:.0f}ms"

    return True, None
```

### Execution

```python
def on_propose(proposal):
    """Manager's vote handler"""

    # Run all checks
    checks = [
        check_regime(proposal),
        check_support(proposal),
        check_bounds(proposal),
        check_impact(proposal),
        check_cooldown(proposal)
    ]

    # Aggregate results
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

    # Publish vote
    vote = {
        'manager_id': MANAGER_ID,
        'change_id': proposal['change_id'],
        'decision': decision,
        'reasons': reasons,
        'vote_hash': vote_hash,
        'timestamp': time.time()
    }

    nats_client.publish('mem.vote', json.dumps(vote))
```

---

## 7. Quorum Protocol (Q=3, M Managers)

### Message Topics

```
mem.propose     # bots → managers
mem.vote        # managers → coordinator
mem.commit      # coordinator → all (bots + managers)
mem.audit       # append-only audit log
```

### Flow

```
┌──────────┐                                      ┌──────────┐
│ Bot      │                                      │ Manager 1│
│          │──1. Propose────────────────────────▶ │          │
│          │                                      │          │
│          │                                      │ Evaluate │
│          │                                      │ Vote     │
│          │                                      └─────┬────┘
│          │                                            │
│          │                                      ┌─────▼────┐
│          │                                      │ Manager 2│
│          │                                      │          │
│          │                                      │ Evaluate │
│          │                                      │ Vote     │
│          │                                      └─────┬────┘
│          │                                            │
│          │                                      ┌─────▼────┐
│          │                                      │ Manager 3│
│          │                                      │          │
│          │                                      │ Evaluate │
│          │                                      │ Vote     │
│          │                                      └─────┬────┘
│          │                                            │
│          │                                      ┌─────▼────┐
│          │                                      │Coordinator│
│          │                                      │          │
│          │                                      │ Count    │
│          │                                      │ Votes    │
│          │                                      │          │
│          │                                      │ Q=3?     │
│          │                                      │ ┌──────┐ │
│          │                                      │ │ Yes  │ │
│          │                                      │ └──┬───┘ │
│          │                                      │    │     │
│          │                                      │ Commit   │
│          │◀──2. Commit broadcast───────────────┤ to Redis │
│          │                                      │          │
│          │                                      │ Publish  │
└──────────┘                                      └──────────┘
```

**Coordinator Algorithm**:

```python
def coordinator_loop():
    """Accumulate votes and commit on quorum"""

    pending_votes = defaultdict(list)  # change_id -> [votes]

    for msg in nats_client.subscribe('mem.vote'):
        vote = json.loads(msg.data)
        change_id = vote['change_id']

        # Add to pending
        pending_votes[change_id].append(vote)

        # Check for quorum
        if len(pending_votes[change_id]) >= QUORUM_SIZE:
            votes = pending_votes[change_id][:QUORUM_SIZE]

            # Check if all votes match
            vote_hashes = [v['vote_hash'] for v in votes]
            decisions = [v['decision'] for v in votes]

            if len(set(vote_hashes)) == 1 and len(set(decisions)) == 1:
                # Quorum reached with consensus
                decision = decisions[0]

                if decision == 'ACCEPT':
                    # Apply change (single writer)
                    proposal = get_proposal(change_id)
                    apply_to_redis(proposal)

                    # Compute state hash
                    state_hash = compute_state_hash(proposal['guards']['symbol'])

                else:
                    state_hash = None

                # Broadcast commit
                commit = {
                    'change_id': change_id,
                    'decision': decision,
                    'votes': votes,
                    'state_hash': state_hash,
                    'timestamp': time.time()
                }

                nats_client.publish('mem.commit', json.dumps(commit))

                # Append to audit log
                append_audit(commit)

                # Clean up
                del pending_votes[change_id]

            else:
                # No consensus - reject
                commit = {
                    'change_id': change_id,
                    'decision': 'REJECT',
                    'reason': 'NO_CONSENSUS',
                    'votes': votes,
                    'timestamp': time.time()
                }

                nats_client.publish('mem.commit', json.dumps(commit))
                append_audit(commit)
                del pending_votes[change_id]

        # Timeout check (separate coroutine)
        check_timeouts(pending_votes)


def check_timeouts(pending_votes):
    """Reject proposals that don't reach quorum in time"""

    now = time.time()

    for change_id, votes in list(pending_votes.items()):
        if votes:
            oldest_vote_time = min(v['timestamp'] for v in votes)

            if (now - oldest_vote_time) * 1000 > VOTE_TIMEOUT_MS:
                # Timeout - reject
                commit = {
                    'change_id': change_id,
                    'decision': 'REJECT',
                    'reason': 'TIMEOUT',
                    'votes': votes,
                    'timestamp': now
                }

                nats_client.publish('mem.commit', json.dumps(commit))
                append_audit(commit)
                del pending_votes[change_id]
```

### Leader Rotation

```python
# Round-robin every M commits or time-boxed
current_coordinator_idx = commit_count % len(managers)
coordinator = managers[current_coordinator_idx]

# Alternative: Time-boxed
if time.time() - coordinator_start_time > COORDINATOR_WINDOW_SEC:
    rotate_coordinator()
```

### Read-After-Write Verification

```python
def verify_commit(commit):
    """All managers verify commit was applied correctly"""

    if commit['decision'] != 'ACCEPT':
        return  # Nothing to verify

    # Read back from Redis
    proposal = get_proposal(commit['change_id'])

    for entry_id, expected_delta in proposal['deltas'].items():
        key = find_redis_key(entry_id)
        actual_w = float(redis.hget(key, 'w'))

        # Verify weight matches expected
        original_w = get_original_weight(entry_id)  # from cache
        expected_w = original_w + expected_delta

        if abs(actual_w - expected_w) > 1e-6:
            log_error(f"VERIFY_FAILED:{entry_id}:{actual_w}!={expected_w}")
            trigger_alert()

    # Verify state hash
    computed_hash = compute_state_hash(proposal['guards']['symbol'])

    if computed_hash != commit['state_hash']:
        log_error(f"STATE_HASH_MISMATCH:{computed_hash}!={commit['state_hash']}")
        trigger_alert()
```

---

## 8. Pattern Maintenance

### Refresh Schedule

**Frequency**: Every 5-10 minutes

**Algorithm**:

```python
def refresh_patterns():
    """Cluster episodic memories into patterns"""

    for symbol in ACTIVE_SYMBOLS:
        for regime in ACTIVE_REGIMES:
            # Reservoir sample recent episodes
            episodes = redis_sample(
                index='idx:epi',
                filters={'sym': symbol, 'reg': regime},
                sample_size=min(1000, total_count * 0.1)
            )

            if len(episodes) < MIN_PATTERN_SIZE:
                continue

            # Extract vectors
            vectors = np.array([e['v'] for e in episodes])

            # Mini-batch k-means
            n_clusters = estimate_n_clusters(len(episodes))
            kmeans = MiniBatchKMeans(n_clusters=n_clusters, batch_size=100)
            labels = kmeans.fit_predict(vectors)

            # Update pattern statistics
            for cluster_id in range(n_clusters):
                cluster_episodes = [e for e, l in zip(episodes, labels) if l == cluster_id]

                if len(cluster_episodes) < MIN_PATTERN_SIZE:
                    continue

                pattern_id = f"{symbol}:{regime}:P{cluster_id}"

                stats = compute_pattern_stats(cluster_episodes)

                # Write to Redis
                redis.hset(f'hash:pattern:{pattern_id}', mapping={
                    'n': stats['n'],
                    'mu': stats['mu'],
                    'sig': stats['sig'],
                    'sr': stats['sr'],
                    't05': stats['t05'],
                    't95': stats['t95'],
                    'slip_mu': stats['slip_mu'],
                    'reg': regime,
                    'last': time.time()
                })


def compute_pattern_stats(episodes):
    """Compute aggregate statistics for pattern"""

    pnls = np.array([e['pnl'] for e in episodes])
    slips = np.array([e['slip'] for e in episodes])

    returns = pnls / np.mean(np.abs(pnls))  # normalize

    return {
        'n': len(episodes),
        'mu': np.mean(pnls),
        'sig': np.std(pnls),
        'sr': np.mean(returns) / (np.std(returns) + 1e-9) * np.sqrt(252),
        't05': np.percentile(pnls, 5),
        't95': np.percentile(pnls, 95),
        'slip_mu': np.mean(slips)
    }
```

### Promotion Rules

```python
def check_promotion(pattern_id):
    """Determine if pattern should influence decisions"""

    pattern = redis.hgetall(f'hash:pattern:{pattern_id}')

    n = int(pattern['n'])
    sr = float(pattern['sr'])

    # Compute current drawdown
    dd = compute_pattern_drawdown(pattern_id)

    # Promotion criteria
    if n >= config.N_promote and sr >= config.S_min and dd <= config.DD_max:
        redis.hset(f'hash:pattern:{pattern_id}', 'enabled', 1)
        return True
    else:
        redis.hset(f'hash:pattern:{pattern_id}', 'enabled', 0)
        return False
```

### Deprecation Rules

```python
def check_deprecation(pattern_id):
    """Deprecate underperforming patterns"""

    pattern = redis.hgetall(f'hash:pattern:{pattern_id}')

    # Get backtest SR (from initial evaluation)
    backtest_sr = float(redis.hget(f'hash:pattern:{pattern_id}:backtest', 'sr'))

    # Get live SR (from recent trades using this pattern)
    live_sr = compute_live_sr(pattern_id, window_days=7)

    # Check degradation
    if live_sr < backtest_sr - config.deprecation_delta:
        deprecation_count = int(redis.hincrby(f'hash:pattern:{pattern_id}', 'deprecation_count', 1))

        if deprecation_count >= config.deprecation_windows:
            # Disable pattern
            redis.hset(f'hash:pattern:{pattern_id}', 'enabled', 0)
            log_warning(f"Pattern deprecated: {pattern_id}")
            return True

    else:
        # Reset deprecation counter
        redis.hset(f'hash:pattern:{pattern_id}', 'deprecation_count', 0)

    return False
```

---

## 9. Safety Overlays

### Independent Safety Checks

**These run regardless of memory system**:

```python
class SafetyOverlay:
    def __init__(self, config):
        self.config = config
        self.daily_pnl = 0
        self.daily_trades = 0
        self.open_positions = {}

    def check_daily_loss_limit(self):
        if self.daily_pnl < -self.config.max_daily_loss:
            return False, "DAILY_LOSS_LIMIT_BREACHED"
        return True, None

    def check_position_limits(self, symbol, size):
        current = self.open_positions.get(symbol, 0)
        new_position = current + size

        if abs(new_position) > self.config.max_position_size:
            return False, f"POSITION_LIMIT:{symbol}"
        return True, None

    def check_max_open_orders(self):
        if len(self.open_positions) >= self.config.max_open_orders:
            return False, "MAX_OPEN_ORDERS"
        return True, None

    def check_max_time_in_market(self, symbol):
        if symbol in self.position_entry_times:
            elapsed = time.time() - self.position_entry_times[symbol]
            if elapsed > self.config.max_time_in_market:
                return False, f"MAX_TIME_IN_MARKET:{symbol}"
        return True, None

    def approve_trade(self, symbol, action, size):
        """Must pass ALL safety checks"""

        checks = [
            self.check_daily_loss_limit(),
            self.check_position_limits(symbol, size),
            self.check_max_open_orders(),
            self.check_max_time_in_market(symbol)
        ]

        failures = [reason for ok, reason in checks if not ok]

        if failures:
            return False, failures
        return True, []
```

### Memory Quarantine

**New patterns capped until proven**:

```python
def apply_quarantine_multiplier(pattern_id, size):
    """Limit size for new patterns"""

    pattern = redis.hgetall(f'hash:pattern:{pattern_id}')
    n = int(pattern['n'])

    if n < config.quarantine_threshold:
        # Apply cap
        multiplier = min(config.s_max_new, n / config.quarantine_threshold)
        return size * multiplier

    return size
```

### Auto-Downweight on Degradation

```python
def check_memory_health():
    """Downgrade memory influence if system degraded"""

    # Check latency
    p99_latency = get_p99_latency(window_seconds=60)

    if p99_latency > config.latency_slo_ms:
        adjust_memory_weight(factor=0.5)
        log_warning(f"Memory downweighted: latency {p99_latency}ms > SLO")

    # Check error rate
    error_rate = get_error_rate(window_seconds=60)

    if error_rate > config.error_rate_slo:
        adjust_memory_weight(factor=0.5)
        log_warning(f"Memory downweighted: error rate {error_rate} > SLO")
```

---

## 10. Latency Budgets

**End-to-End Target**: < 2ms from state to action

### Breakdown

| Operation | Target (P99) | Notes |
|-----------|--------------|-------|
| kNN + aggregate | ≤ 1 ms | Local shard, Redis HNSW |
| Voting round trip | ≤ 2 ms | Intra-DC, Q=3, NATS |
| Commit cost | ≤ 1 ms | Single write + tag update |
| **Total** | **≤ 4 ms** | **Including buffer** |

### Degradation Handling

```python
if bus_congestion_detected():
    # Buffer proposals
    buffer_queue.append(proposal)

    # Temporarily downgrade memory weight
    current_w_mem = get_memory_weight()
    set_memory_weight(current_w_mem * 0.5)

    log_warning("Memory weight reduced due to bus congestion")
```

---

## 11. Metrics and Dashboards

### Memory Health

```python
# Prometheus metrics

memory_hit_rate = Gauge('memory_hit_rate', 'Fraction of queries with k≥K neighbors')
neighbor_age_histogram = Histogram('neighbor_age_seconds', 'Age of retrieved neighbors')
effective_sample_size = Gauge('memory_effective_n', 'Effective sample size by symbol/regime')
```

### Pattern Health

```python
pattern_sharpe_live = Gauge('pattern_sharpe_live', 'Live Sharpe by pattern', ['pattern_id'])
pattern_sharpe_backtest = Gauge('pattern_sharpe_backtest', 'Backtest Sharpe by pattern', ['pattern_id'])
pattern_drawdown = Gauge('pattern_drawdown', 'Current drawdown by pattern', ['pattern_id'])
pattern_tail_risk = Gauge('pattern_tail_risk', '5th percentile PnL', ['pattern_id'])
```

### Quorum Stats

```python
proposals_per_second = Counter('memory_proposals_total', 'Proposals submitted')
vote_convergence_time = Histogram('memory_vote_duration_ms', 'Time to reach quorum')
rejection_reasons = Counter('memory_rejections_total', 'Rejections by reason', ['reason'])
```

### Latency

```python
knn_latency = Histogram('memory_knn_latency_ms', 'kNN query latency')
vote_latency = Histogram('memory_vote_latency_ms', 'Vote round-trip latency')
commit_latency = Histogram('memory_commit_latency_ms', 'Commit write latency')
```

### Attribution

```python
decision_weight_memory = Gauge('decision_weight_memory_pct', 'Memory contribution to action score')
decision_weight_model = Gauge('decision_weight_model_pct', 'Model contribution to action score')
```

### Grafana Dashboard Example

```json
{
  "dashboard": {
    "title": "Coinswarm Memory System",
    "panels": [
      {
        "title": "Memory Hit Rate",
        "targets": [{"expr": "memory_hit_rate"}],
        "type": "graph"
      },
      {
        "title": "Quorum Convergence (P99)",
        "targets": [{"expr": "histogram_quantile(0.99, memory_vote_duration_ms)"}],
        "type": "stat"
      },
      {
        "title": "Pattern Health (Top 10)",
        "targets": [
          {"expr": "topk(10, pattern_sharpe_live)"},
          {"expr": "topk(10, pattern_sharpe_backtest)"}
        ],
        "type": "table"
      },
      {
        "title": "Rejection Reasons",
        "targets": [{"expr": "sum by (reason) (memory_rejections_total)"}],
        "type": "piechart"
      }
    ]
  }
}
```

---

## 12. CI and Simulation Gates

### Time-Aware Backtest

```python
def backtest_with_memory_replay():
    """Simulate memory system with historical data"""

    # Initialize empty memory
    memory = MemoryStore()

    # Replay historical ticks
    for timestamp, tick in sorted(historical_data.items()):
        # Get state at this time
        state = construct_state(tick)
        φ = embed(state)

        # Query memory (no future leakage)
        neighbors = memory.knn(φ, timestamp=timestamp)

        # Make decision
        action = policy(state, neighbors)

        # Execute (simulated)
        outcome = simulate_execution(action, tick)

        # Propose memory update
        proposal = create_proposal(φ, action, outcome, timestamp)

        # Simulate quorum vote
        votes = [manager.evaluate(proposal) for manager in managers]

        if quorum_reached(votes):
            memory.apply(proposal)

        # Record results
        results.append(outcome)

    # Assert determinism
    assert hash(memory.state) == expected_hash
```

### Stylized Facts Validation

```python
def test_stylized_facts():
    """Ensure memory system preserves market microstructure"""

    sim_returns = run_simulation_with_memory()

    # Check fat tails
    kurtosis = scipy.stats.kurtosis(sim_returns)
    assert kurtosis > 3, "Returns should have fat tails"

    # Check volatility clustering
    acf_abs = autocorr(np.abs(sim_returns), lag=10)
    assert acf_abs > 0.2, "Volatility should cluster"

    # Check spread dynamics
    spreads = get_simulated_spreads()
    assert np.mean(spreads) < historical_mean_spread * 1.1, "Spreads reasonable"
```

### A/B Testing

```python
def ab_test_memory():
    """Compare model-only vs model+memory"""

    # Group A: Model only
    results_model_only = backtest(use_memory=False)

    # Group B: Model + Memory
    results_with_memory = backtest(use_memory=True)

    # Metrics
    sharpe_a = compute_sharpe(results_model_only)
    sharpe_b = compute_sharpe(results_with_memory)

    dd_a = compute_max_drawdown(results_model_only)
    dd_b = compute_max_drawdown(results_with_memory)

    slip_a = compute_mean_slippage(results_model_only)
    slip_b = compute_mean_slippage(results_with_memory)

    print(f"ΔSharpe: {sharpe_b - sharpe_a:.2f}")
    print(f"ΔDD: {dd_b - dd_a:.2f}%")
    print(f"ΔSlip: {slip_b - slip_a:.2f} bps")

    # Statistical significance
    t_stat, p_value = scipy.stats.ttest_ind(
        results_model_only['returns'],
        results_with_memory['returns']
    )

    assert p_value < 0.05, "Improvement must be statistically significant"
```

### Chaos Testing

```python
def chaos_test_manager_failure():
    """Test resilience to manager failures"""

    # Start with 5 managers
    managers = [MemoryManager(i) for i in range(5)]

    # Kill 2 managers
    managers[2].kill()
    managers[4].kill()

    # Quorum should still work (3 remaining)
    proposal = create_test_proposal()

    votes = [m.evaluate(proposal) for m in managers if m.alive]
    assert len(votes) >= 3, "Should have quorum with 3 managers"

    # Kill 1 more (only 2 left)
    managers[1].kill()

    # Now should go read-only
    assert memory_store.is_read_only(), "Should be read-only with <3 managers"
```

---

## 13. Configuration Defaults

```yaml
# Embedding
embedding_dim: 384

# Retrieval
K_neighbors: 16
kernel_sigma: 1.0

# Credit assignment
alpha_credit: 0.1

# Action scoring
beta_ucb: 1.0
lambda_risk: 1.0
w_model: 0.5
w_mem: 0.5

# Bounds
delta_max: 0.05
w_bounds: [0.1, 10.0]

# Pattern requirements
n_min_cluster: 50
SR_min_cluster: 0.6
N_promote: 100
S_min: 1.0
DD_max: 10.0  # percent

# Maintenance
memory_ttl_days: 30
pattern_refresh_min: 5

# Quorum
vote_timeout_ms: 5
commit_cooldown_ms_per_symbol: 20

# Safety
max_daily_loss: 0.05  # 5% of portfolio
max_position_size: 0.25  # 25% of portfolio
max_open_orders: 10
max_time_in_market: 3600  # seconds

# Performance SLOs
latency_slo_ms: 5
error_rate_slo: 0.01

# Quarantine
quarantine_threshold: 100
s_max_new: 0.3  # 30% size for new patterns
```

---

## 14. Minimal APIs

### Bot → Memory Layer

```http
POST /act
Content-Type: application/json

{
  "state": {...},
  "symbol": "BTC-USD"
}

Response:
{
  "action": "BUY",
  "size": 0.001,
  "confidence": 0.87,
  "attribution": {
    "model": 0.52,
    "memory": 0.35,
    "ucb": 0.08,
    "risk": -0.08
  },
  "neighbors": 16,
  "pattern": "BTC-USD:R3:P7"
}
```

```http
POST /mem/propose
Content-Type: application/json

{
  "change_type": "credit_update",
  "payload": {
    "ids": ["entry1", "entry2", ...],
    "deltas": {"entry1": 0.03, "entry2": 0.01, ...},
    "guards": {...}
  }
}

Response:
{
  "proposal_id": "uuid",
  "status": "pending"
}
```

### Manager Internal (NATS)

```
SUB mem.propose
  → Evaluate proposal
  → PUB mem.vote

SUB mem.commit
  → Verify commit
  → Update local cache

APPEND mem.audit
  → Write-ahead log
```

---

## 15. Pseudocode: Quorum-NEC Update

```python
# ============================================================
# BOT SIDE: Action selection and proposal submission
# ============================================================

φ_t = embed(state_t)
R_t = regime_now()

# kNN retrieval
neighbors = knn(
    sym=symbol,
    reg=R_t,
    vec=φ_t,
    k=16,
    time_limit=time_t
)

# Aggregate stats
stats = aggregate(neighbors)

# Action scoring
scores = {}
for action in [BUY, SELL, HOLD]:
    scores[action] = (
        w_model * model_logits[action]
        + w_mem * stats[action]['E_pnl']
        + β * ucb(action, stats)
        - λ * risk(action, stats)
    )

a_t = argmax(scores)

# Execute
execute(a_t)

# Observe reward
r_t = realized_pnl()

# Compute advantage
δ_t = r_t - stats[a_t]['E_pnl']

# Credit assignment proposal
payload = {
    'ids': [n.id for n in neighbors],
    'deltas': {n.id: α * kernel(φ_t, n.v) * δ_t for n in neighbors},
    'guards': {'sym': symbol, 'reg': R_t}
}

publish('mem.propose', payload)


# ============================================================
# MANAGER SIDE: Evaluate and vote
# ============================================================

def on_propose(payload):
    # Deterministic checks
    regime_ok = check_regime(payload)
    support_ok = check_support(payload)
    bounds_ok = check_bounds(payload)
    impact_ok = check_impact(payload)
    cooldown_ok = check_cooldown(payload)

    if all([regime_ok, support_ok, bounds_ok, impact_ok, cooldown_ok]):
        decision = "ACCEPT"
    else:
        decision = "REJECT"

    # Compute vote hash
    vote_hash = hash(decision + normalize(payload))

    publish('mem.vote', {
        'manager_id': ME,
        'change_id': payload.id,
        'decision': decision,
        'vote_hash': vote_hash
    })


# ============================================================
# COORDINATOR: Quorum counting and commit
# ============================================================

def coordinator():
    votes_by_change = {}

    for vote in subscribe('mem.vote'):
        change_id = vote['change_id']
        votes_by_change[change_id].append(vote)

        if len(votes_by_change[change_id]) >= 3:
            votes = votes_by_change[change_id][:3]

            # Check consensus
            if len(set(v['vote_hash'] for v in votes)) == 1:
                decision = votes[0]['decision']

                if decision == 'ACCEPT':
                    apply_change_to_redis(get_proposal(change_id))
                    state_hash = snapshot_hash()
                else:
                    state_hash = None

                publish('mem.commit', {
                    'change_id': change_id,
                    'decision': decision,
                    'state_hash': state_hash
                })

                append_audit(change_id, votes, decision)

            del votes_by_change[change_id]
```

---

## 16. Deployment Plan

### Phase A: Single-Host Validation

**Infrastructure**:
- 1 host (32 GB RAM, 8 cores)
- Redis + RediSearch (16 GB allocated)
- NATS server
- 3 Memory Manager containers
- 2 Trading Bot containers

**Objectives**:
- Validate quorum latency (target < 2ms)
- Validate memory uplift vs model-only
- Deterministic backtest with live-like timings

**Duration**: 2 weeks

**Success Criteria**:
- ΔSharpe > 0.3 vs model-only
- P99 vote latency < 5ms
- Zero consensus failures

### Phase B: Sharded Multi-Host

**Infrastructure**:
- 3 hosts (shard episodic per bot)
- Shared pattern table (Redis Cluster)
- 5 Memory Managers (across hosts)
- 10 Trading Bots (across hosts)
- NATS cluster

**Objectives**:
- Scale to 10+ concurrent bots
- Test cross-host quorum
- Pattern refresh at scale

**Duration**: 4 weeks

**Success Criteria**:
- Handle 100+ proposals/second
- P99 end-to-end latency < 10ms
- Pattern convergence within 15 minutes

### Phase C: Paper Trading

**Infrastructure**:
- Same as Phase B
- Connect to Coinbase/Alpaca sandbox
- Live market data feeds

**Objectives**:
- Test with real market dynamics
- Ramp memory influence (w_mem: 0.2 → 0.6)
- Validate promotion/deprecation gates

**Duration**: 8 weeks

**Success Criteria**:
- Live Sharpe > 1.5
- Max drawdown < 10%
- Pattern library > 50 active patterns

### Phase D: Live (Tiny Notional)

**Infrastructure**:
- Same as Phase C
- Real accounts (max $1000 per symbol)

**Objectives**:
- Real slippage and execution
- Kill switch validation
- Auto-downweight on anomalies

**Duration**: Ongoing

**Success Criteria**:
- Zero loss-of-capital incidents
- Kill switch triggers < 1/week
- Pattern degradation detected within 1 day

---

## 17. Hard Guarantees

1. **No memory mutation without 3 matching votes**
   - Enforced by coordinator quorum logic
   - Read-only mode if < 3 managers online

2. **All commits logged with hashes**
   - Proposal hash
   - 3 vote hashes
   - Post-commit state hash
   - Append-only audit log (immutable)

3. **Deterministic manager decisions**
   - Same input → same vote
   - Enables audit and replay

4. **No future leakage**
   - kNN queries filtered by `ts ≤ current_time`
   - Backtest replay enforces time order

5. **Bounded memory impact**
   - δ_max caps single update
   - w_bounds caps cumulative weight
   - Safety overlays independent of memory

---

## 18. What to Build Next

### Immediate (Week 1-2)

1. **`docker-compose.yml`**
   - Redis + RediSearch container
   - NATS server container
   - 3 Memory Manager containers
   - 2 Trading Bot containers
   - Prometheus + Grafana

2. **Python libraries**:
   - `memory_client.py`: kNN, propose, pattern assignment
   - `manager.py`: Evaluate, vote, commit, audit
   - `coordinator.py`: Quorum loop
   - `safety_overlay.py`: Independent safety checks

3. **Redis schema initialization**:
   - Create vector index (`idx:epi`)
   - Initialize regime state
   - Set up audit log stream

### Next (Week 3-4)

4. **Backtesting framework**:
   - Time-aware replay
   - Deterministic memory state
   - A/B comparison (model vs model+memory)

5. **Grafana dashboards**:
   - Memory health (hit rate, neighbor age)
   - Pattern health (Sharpe, drawdown, tail risk)
   - Quorum stats (proposals, votes, latency)
   - Attribution (model vs memory contribution)

6. **CI pipeline**:
   - Backtest on every commit
   - Assert Sharpe improvement
   - Assert no consensus failures
   - Chaos tests (kill managers)

---

## Appendix A: Example Proposal JSON

```json
{
  "change_id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "credit_update",
  "proposer": "bot_btc_001",
  "timestamp": 1704067200.123,
  "ids": [
    "entry_001",
    "entry_002",
    "entry_003"
  ],
  "deltas": {
    "entry_001": 0.0234,
    "entry_002": 0.0189,
    "entry_003": 0.0156
  },
  "guards": {
    "regime": "R3",
    "symbol": "BTC-USD",
    "bounds": {
      "delta_max": 0.05,
      "w_min": 0.1,
      "w_max": 10.0
    }
  }
}
```

## Appendix B: Example Vote JSON

```json
{
  "manager_id": "manager_002",
  "change_id": "550e8400-e29b-41d4-a716-446655440000",
  "decision": "ACCEPT",
  "reasons": [],
  "vote_hash": "a7f3c1b2e4d5f6g7h8i9j0k1l2m3n4o5",
  "timestamp": 1704067200.125
}
```

## Appendix C: Example Commit JSON

```json
{
  "change_id": "550e8400-e29b-41d4-a716-446655440000",
  "decision": "ACCEPT",
  "votes": [
    {
      "manager_id": "manager_001",
      "vote_hash": "a7f3c1b2e4d5f6g7h8i9j0k1l2m3n4o5",
      "decision": "ACCEPT"
    },
    {
      "manager_id": "manager_002",
      "vote_hash": "a7f3c1b2e4d5f6g7h8i9j0k1l2m3n4o5",
      "decision": "ACCEPT"
    },
    {
      "manager_id": "manager_003",
      "vote_hash": "a7f3c1b2e4d5f6g7h8i9j0k1l2m3n4o5",
      "decision": "ACCEPT"
    }
  ],
  "state_hash": "b8g4d2c3f5e6h7i8j9k0l1m2n3o4p5q6",
  "timestamp": 1704067200.127
}
```

---

**Last Updated**: 2025-10-31
**Status**: Implementation Specification (Ready to Build)
**Next**: Implement Phase A deployment and run first backtest

---

**This specification is implementation-complete. Proceed to build.**
