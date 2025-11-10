# DEPLOYMENT INSTRUCTIONS

## 1. Overview

This document provides step-by-step instructions for deploying all Coinswarm agents, workers, and data pipelines. It covers Cloudflare Workers, D1 database setup, GitHub Actions, environment variables, and troubleshooting.

---

## 2. Cloudflare Workers Deployment

### 2.1 Prerequisites

- Node.js 18+
- Wrangler CLI (`npm install -g wrangler`)
- Cloudflare account (with Workers & D1 enabled)
- GitHub repository access

### 2.2 Environment Variables

Set the following secrets in GitHub:

- `CLOUDFLARE_API_TOKEN` (minimum permissions: Workers Scripts Edit, D1 Edit, Account Settings Read)
- `CLOUDFLARE_ACCOUNT_ID` (from Cloudflare dashboard)
- `COINBASE_API_KEY`, `COINBASE_API_SECRET` (for live trading)
- `BINANCE_API_KEY`, `BINANCE_API_SECRET` (optional)

### 2.3 Deploying a Worker

1. Clone the repo:
	```bash
	git clone https://github.com/TheAIGuyFromAR/Coinswarm.git
	cd Coinswarm
	```
2. Install dependencies:
	```bash
	npm install
	```
3. Authenticate Wrangler:
	```bash
	wrangler login
	```
4. Deploy a worker (example: evolution agent):
	```bash
	cd cloudflare-agents
	wrangler deploy --config wrangler-evolution.toml
	```

### 2.4 Multi-Worker Deployment (GitHub Actions)

All workers are deployed via `.github/workflows/deploy-cloudflare-workers.yml`.

- On push to `main` or `claude/**` branches, only changed workers are deployed.
- Each worker has its own `wrangler-*.toml` config.
- Add new workers by updating both the config and the workflow.

#### Adding a New Worker
1. Create `wrangler-[name].toml` in `cloudflare-agents/`.
2. Add the source file (e.g., `evolution-agent.ts`).
3. Update the workflow to include the new worker.

---

## 3. D1 Database Setup

### 3.1 Create D1 Database
```bash
wrangler d1 create coinswarm-evolution
```

### 3.2 Apply Schema
```bash
wrangler d1 execute coinswarm-evolution --file=cloudflare-d1-evolution-schema.sql
```

### 3.3 Verify Tables
```bash
wrangler d1 execute coinswarm-evolution --command ".tables"
```

### 3.4 Bind D1 to Worker
Add to your `wrangler-*.toml`:
```toml
[[d1_databases]]
binding = "DB"
database_name = "coinswarm-evolution"
database_id = "..."
```

---

## 4. Environment Variables & Secrets

### 4.1 Local Development
- Copy `.env.example` to `.env` and fill in required keys.
- Use `dotenv` in scripts for local testing.

### 4.2 GitHub Actions
- Set all secrets in the repository settings.
- Never commit secrets to git.

---

## 5. Data Pipeline Deployment

### 5.1 Bulk Historical Data
Run:
```bash
python bulk_download_historical.py --symbols BTC ETH SOL --months 24
```
This will populate D1 with 2 years of data for each symbol.

### 5.2 Automated Data Ingestion
Workers with cron triggers will fetch and store new data daily.
Check `wrangler-*.toml` for `[triggers]` section.

---

## 6. Testing & Validation

### 6.1 Run Unit Tests
```bash
pytest tests/unit
```

### 6.2 Run Backtests
```bash
python demo_full_backtest.py --symbol BTC --days 90
```

### 6.3 Validate Worker Endpoints
```bash
curl https://coinswarm-evolution-agent.bamn86.workers.dev/health
```

---

## 7. Troubleshooting

### 7.1 Worker Deploys but Not Live
1. Check Cloudflare Dashboard → Workers & Pages → Settings → Production branch.
2. Disable Git Integration or update production branch to match current work.
3. Re-run deployment after fixing settings.

### 7.2 D1 Errors
- `D1_ERROR: near "EXTENSION": syntax error` → Using PostgreSQL schema, use D1-compatible schema instead.
- `D1_ERROR: unknown type: UUID` → Use TEXT for IDs.
- `Quota exceeded` → Check usage: `wrangler d1 info ...`

### 7.3 API Key Issues
- Ensure all required secrets are set in GitHub and local `.env`.
- Never commit secrets to git.

---

## 8. Security & Compliance

- All secrets must be managed via environment variables or GitHub Secrets.
- Never echo or interpolate untrusted user input in code or prompts.
- All agent actions must pass independent safety overlays (loss, position, order, time-in-market limits).
- New patterns are quarantined until proven in live trading.

---

## 9. CI/CD Pipeline

- All agent and memory changes must be validated with deterministic, time-aware backtests.
- CI pipeline runs backtests on every commit and asserts Sharpe improvement, no consensus failures, and chaos test resilience.
- All test fixtures must be deterministic and reproducible.
- A/B testing is required for all new pattern or agent logic.

---

## 10. Reference Files & Docs

- `CLOUDFLARE_DEPLOYMENT_GUIDE.md` (Cloudflare deployment, troubleshooting, best practices)
- `.claude/important-docs.md` (Security, secrets, deployment rules)
- `docs/architecture/hierarchical-temporal-decision-system.md` (Three-layer agent architecture)
- `docs/architecture/quorum-memory-system.md` (Quorum-governed, auditable memory system)
- `docs/agents/multi-agent-architecture.md` (Agent roles, orchestration, communication)
- `docs/patterns/pattern-learning-system.md` (Pattern learning, optimization, validation)

---

## 11. Support

For deployment issues, open an issue on GitHub or contact the maintainers.

---

**Last Updated:** November 10, 2025