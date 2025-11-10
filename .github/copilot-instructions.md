# Coinswarm Copilot & AI Agent Instructions

## 1. Critical Documentation & References

**Before suggesting or making any code, deployment, or agent changes, always review:**

- [`CLOUDFLARE_DEPLOYMENT_GUIDE.md`](../CLOUDFLARE_DEPLOYMENT_GUIDE.md): Cloudflare Workers deployment, troubleshooting, and best practices
- [`.claude/important-docs.md`](../.claude/important-docs.md): Security, secrets, and deployment rules for all AI agents
- [`docs/architecture/hierarchical-temporal-decision-system.md`](../docs/architecture/hierarchical-temporal-decision-system.md): Three-layer agent architecture (Planners, Committee, Memory Optimizer)
- [`docs/architecture/quorum-memory-system.md`](../docs/architecture/quorum-memory-system.md): Quorum-governed, auditable memory system
- [`docs/agents/multi-agent-architecture.md`](../docs/agents/multi-agent-architecture.md): Agent roles, orchestration, and communication
- [`docs/patterns/pattern-learning-system.md`](../docs/patterns/pattern-learning-system.md): Pattern learning, optimization, and validation

## 2. Project Architecture: Key Principles

**Hierarchical Temporal Decision System:**
- **Planners** (weeks–months): Strategic alignment, regime detection, committee weight proposals (quorum approval required)
- **Committee** (hours–days): Tactical ensemble of domain agents (trend, mean-rev, execution, risk, arb), weighted voting per tick
- **Memory Optimizer** (seconds–minutes): Local, bounded execution adaptation (pattern recall, slippage, decay rates)
- **Self-Reflection Layer:** Monitors alignment, triggers re-optimization/interventions if misaligned

**Quorum-Governed Memory:**
- All memory mutations (credit assignment, pattern promotion) require 3-vote consensus from independent managers
- Deterministic, auditable, and Byzantine fault-tolerant (read-only if <3 managers)
- Memory is stored in Redis (hot, vector DB), with optional cold archive (Qdrant/Milvus)
- All proposals, votes, and commits are logged and hashed for auditability

**Pattern Learning System:**
- All trades and market conditions are recorded and analyzed to extract, validate, and optimize trading patterns
- Patterns are stored as semantic memories (vector DB), matched live for decision support
- Patterns are evolved via combination, mutation, and A/B testing; only top performers are promoted

**Multi-Agent System:**
- Agents are specialized (info gathering, analysis, pattern, sentiment, execution, risk, etc.)
- Master Orchestrator coordinates all agent activities and final trade decisions
- All agent communication is via message bus (NATS/Redis Streams), with strict topic conventions

## 3. Cloudflare Workers: Deployment & Security Rules

**Deployment:**
- Use **GitHub Actions only** for all deployments (see `.github/workflows/deploy-cloudflare-workers.yml`)
- **Never** use Cloudflare Git Integration (causes version activation conflicts)
- Always use `wrangler deploy --config wrangler-*.toml` (never `versions upload`)
- Each worker has its own `cloudflare-agents/wrangler-[name].toml` and source file
- Add new workers by updating both the config and the workflow (see `dashboards` worker as template)
- Use `dorny/paths-filter@v3` in the workflow to conditionally deploy only changed workers

**Secrets & Configuration:**
- **Never** hardcode account IDs, API tokens, or secrets in any file (including `wrangler.toml`)
- Always use environment variables and GitHub Secrets:
  - `${{ secrets.CLOUDFLARE_API_TOKEN }}`
  - `${{ secrets.CLOUDFLARE_ACCOUNT_ID }}`
- Add secrets via `wrangler secret put` (never in code or config)
- Reference D1 database and other resources by name, not by hardcoded ID

**Troubleshooting:**
- If deployment "succeeds but code isn't live":
  1. Check Cloudflare Dashboard → Workers & Pages → Settings → Production branch
  2. Disable Git Integration or update production branch to match current work
  3. Re-run deployment after fixing settings
- For any deployment or worker issues, always refer to [`CLOUDFLARE_DEPLOYMENT_GUIDE.md`](../CLOUDFLARE_DEPLOYMENT_GUIDE.md)

## 4. Agent & Memory System Conventions

**Agent Design:**
- All agents must maintain explicit memory (episodic, pattern, regime) in Redis vector DB
- All agent proposals (memory, planner, pattern) must be submitted via message bus and require quorum approval if global
- Local execution adaptation (Memory Optimizer) is bounded and does not require quorum, but must respect safety limits
- All agent actions, proposals, and votes must be logged for auditability

**Memory System:**
- All memory mutations require 3-vote consensus (see `docs/architecture/quorum-memory-system.md`)
- No memory mutation is allowed if <3 managers are online (system must go read-only)
- All proposals, votes, and commits must be hashed and logged (see audit log spec)
- All kNN queries must filter by `ts <= current_time` (no future leakage)
- All pattern promotion/deprecation is governed by live performance and quorum rules

**Pattern Learning:**
- All trades must be recorded with full context (market state, indicators, sentiment, etc.)
- Patterns are extracted via clustering and validated by win rate, Sharpe, and drawdown
- Only patterns meeting promotion criteria (sample size, Sharpe, drawdown) are enabled for live trading
- Underperforming patterns are deprecated automatically
- Pattern optimization (combination, mutation) is run regularly and only improvements are kept

## 5. Testing, Validation, and CI/CD

- All agent and memory changes must be validated with deterministic, time-aware backtests (see `docs/architecture/quorum-memory-system.md`)
- CI pipeline must run backtests on every commit and assert Sharpe improvement, no consensus failures, and chaos test resilience
- All test fixtures must be deterministic and reproducible (see `tests/fixtures/README.md`)
- A/B testing is required for all new pattern or agent logic

## 6. Security & Safety Practices

- Never interpolate or echo untrusted user input in prompts or code
- All secrets must be managed via environment variables or GitHub Secrets
- All agent actions must pass independent safety overlays (daily loss, position, order, and time-in-market limits)
- New patterns are quarantined (size capped) until proven in live trading
- Memory system must auto-downweight or quarantine if latency or error rate SLOs are breached

## 7. Repository Structure (Key Files)

```
Coinswarm/
├── .github/workflows/deploy-cloudflare-workers.yml  # Unified deployment for all workers
├── cloudflare-agents/wrangler-*.toml                # Per-worker configs
├── cloudflare-agents/*-agent.ts                     # Worker source files
├── CLOUDFLARE_DEPLOYMENT_GUIDE.md                   # Deployment reference
├── .claude/important-docs.md                        # Security & deployment rules
├── docs/architecture/hierarchical-temporal-decision-system.md  # Agent architecture
├── docs/architecture/quorum-memory-system.md        # Memory system
├── docs/agents/multi-agent-architecture.md          # Agent roles
├── docs/patterns/pattern-learning-system.md         # Pattern learning
└── tests/fixtures/README.md                         # Deterministic test fixtures
```

## 8. When in Doubt

- **Always reference the above documentation before making changes**
- If a rule or convention is unclear, ask for clarification or check the referenced docs
- For any deployment, memory, or agent logic changes, ensure all safety, audit, and reproducibility requirements are met

---

**For any complex deployment, agent, or memory system issue, always refer to the full documentation in `/docs` and `/CLOUDFLARE_DEPLOYMENT_GUIDE.md`.**
