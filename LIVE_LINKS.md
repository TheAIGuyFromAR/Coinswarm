# 🔗 Coinswarm Evolution - Live Links

**Last Updated**: 2025-11-07

---

## 🌐 Production System

**Cloudflare Worker**: `coinswarm-evolution-agent.bamn86.workers.dev`
**Status**: ✅ Live and running 24/7
**Current Cycle**: 1026+
**Patterns Discovered**: 663+
**Winning Strategies**: 228+

---

## 📊 Interactive Dashboards

Click to view live dashboards with real-time data:

### 🏗️ [System Architecture](https://coinswarm-evolution-agent.bamn86.workers.dev/architecture)
Visual representation of the 3-layer multi-agent system:
- Layer 1: Pattern Discovery (Chaos, Academic, Technical)
- Layer 2: Reasoning Agents (Self-reflective, competitive)
- Layer 3: Meta-Learning (Model research)

### 📈 [Pattern Leaderboard](https://coinswarm-evolution-agent.bamn86.workers.dev/patterns)
Top trading patterns ranked by performance:
- Filter by origin (chaos/academic/technical)
- Filter by status (winning/testing)
- Win rates, H2H records, votes
- Real-time statistics

### 🐝 [Agent Swarm](https://coinswarm-evolution-agent.bamn86.workers.dev/swarm)
Live view of all trading agents:
- Agent personalities and generations
- Fitness scores and progress
- Active/Eliminated status
- Competition wins and stats

### 🏆 [Agent Leaderboard](https://coinswarm-evolution-agent.bamn86.workers.dev/agents)
Agent rankings and detailed stats:
- Sort by fitness, ROI, win rate, trades
- Competition records (W-L)
- Expandable detailed stats
- Generation tracking

---

## 🔌 API Endpoints

All endpoints return JSON data:

### System Information
```bash
# Current status and statistics
curl https://coinswarm-evolution-agent.bamn86.workers.dev/status

# System-wide stats
curl https://coinswarm-evolution-agent.bamn86.workers.dev/api/stats
```

### Pattern Data
```bash
# All patterns with filters
curl "https://coinswarm-evolution-agent.bamn86.workers.dev/api/patterns?origin=all&status=all&min_runs=3&limit=50"

# Academic patterns only
curl "https://coinswarm-evolution-agent.bamn86.workers.dev/api/patterns?origin=academic&limit=100"

# Winning patterns
curl "https://coinswarm-evolution-agent.bamn86.workers.dev/api/patterns?status=winning&min_runs=10"
```

### Agent Data
```bash
# All agents (active + eliminated)
curl https://coinswarm-evolution-agent.bamn86.workers.dev/api/agents/all

# Top 100 active agents by fitness
curl https://coinswarm-evolution-agent.bamn86.workers.dev/api/agents/leaderboard
```

### Management
```bash
# Trigger evolution cycle manually
curl -X POST https://coinswarm-evolution-agent.bamn86.workers.dev/trigger

# View recent logs
curl https://coinswarm-evolution-agent.bamn86.workers.dev/logs

# Debug information
curl https://coinswarm-evolution-agent.bamn86.workers.dev/debug
```

---

## 🎯 Quick Links

| Resource | URL |
|----------|-----|
| **Cloudflare Dashboard** | https://dash.cloudflare.com/8a330fc6c339f031a73905d4ca2f3e5d/workers/services/view/coinswarm-evolution-agent |
| **GitHub Repository** | https://github.com/TheAIGuyFromAR/Coinswarm |
| **GitHub Actions** | https://github.com/TheAIGuyFromAR/Coinswarm/actions |
| **D1 Database** | https://dash.cloudflare.com/8a330fc6c339f031a73905d4ca2f3e5d/d1 |

---

## 📚 Documentation

- [Multi-Agent Architecture](./MULTI_AGENT_ARCHITECTURE.md) - Complete system design
- [Dashboard Guide](./cloudflare-agents/dashboards/README.md) - Dashboard usage and customization
- [Reasoning Agents Schema](./cloudflare-agents/reasoning-agent-schema.sql) - Database schema

---

## 🔄 Evolution Schedule

The system runs continuously with different agents activating at scheduled intervals:

| Interval | Agent | Description |
|----------|-------|-------------|
| Every 60s | Chaos Discovery | Generate 50 random trades |
| Every 3 min | Head-to-Head Pattern Testing | Patterns compete |
| Every 5 min | Pattern Analysis | AI discovers new patterns |
| Every 10 min | Strategy Testing | Test winning strategies |
| **Every 10 min** | **🧠 Reasoning Agent Competition** | **Agents compete head-to-head** |
| Every 15 min | Technical Patterns Research | Classic TA setups |
| Every 20 min | Academic Papers Research | Research-based strategies |
| **Every 50 min** | **🧬 Agent Evolution** | **Clone winners, eliminate losers** |
| **Every 50 min** | **🔬 Model Research** | **Search for better AI models** |

---

## ⚙️ System Requirements

**Next Step**: Apply database migrations to enable reasoning agents

### Option 1: GitHub Actions (Recommended)
1. Go to [Actions](https://github.com/TheAIGuyFromAR/Coinswarm/actions)
2. Select "Apply Reasoning Agent Schema Migration"
3. Click "Run workflow"

### Option 2: Manual via Wrangler
```bash
cd cloudflare-agents
npx wrangler d1 execute coinswarm-evolution --remote \
  --file=reasoning-agent-schema.sql
```

This creates tables for:
- `trading_agents` - Agent profiles and fitness scores
- `agent_memories` - Decision history with reflections
- `agent_knowledge` - Learned patterns and preferences
- `agent_competitions` - Competition results
- `agent_lineage` - Evolution family tree
- `model_test_results` - Model benchmarks
- `research_log` - Research findings

---

## 📊 Current Status

As of cycle 1026:
- ✅ **Pattern Discovery**: Active (663 patterns, 228 winning)
- ✅ **Head-to-Head Testing**: Active (patterns competing)
- ⏳ **Reasoning Agents**: Waiting for database migration
- ⏳ **Agent Competition**: Pending (needs migration)
- ⏳ **Model Research**: Pending (needs migration)

Once migrations are applied:
- **Cycle 1030**: First reasoning agent competition
- **Cycle 1050**: First agent evolution
- **Cycle 1075**: First model research

---

## 🎉 Features

### Real-Time Updates
- All dashboards auto-refresh every 30 seconds
- Live competition data
- Agent population dynamics
- Pattern performance tracking

### Interactive Exploration
- Filter patterns by origin and status
- Sort agents by different metrics
- Expand rows for detailed stats
- Visual progress indicators

### Comprehensive Data
- Full agent lineage tracking
- Decision history with reflections
- Competition records
- Model benchmarks

---

## 🛠️ Maintenance

### View Logs
```bash
# Recent system logs
curl https://coinswarm-evolution-agent.bamn86.workers.dev/logs

# Worker logs in Cloudflare Dashboard
# https://dash.cloudflare.com/.../workers/.../logs
```

### Monitor Performance
```bash
# Check if system is running
curl https://coinswarm-evolution-agent.bamn86.workers.dev/status

# Get statistics
curl https://coinswarm-evolution-agent.bamn86.workers.dev/api/stats
```

### Trigger Cycle
```bash
# Manually trigger evolution cycle
curl -X POST https://coinswarm-evolution-agent.bamn86.workers.dev/trigger
```

---

## 🔐 Security

- All dashboards are read-only (no write operations)
- API endpoints are public but read-only
- Database modifications only via Worker code
- Cloudflare Workers security built-in

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/TheAIGuyFromAR/Coinswarm/issues)
- **Discussions**: [GitHub Discussions](https://github.com/TheAIGuyFromAR/Coinswarm/discussions)
- **Documentation**: See [MULTI_AGENT_ARCHITECTURE.md](./MULTI_AGENT_ARCHITECTURE.md)

---

*System Status: 🟢 Live and operational*
*Auto-updated: Every deployment via GitHub Actions*
