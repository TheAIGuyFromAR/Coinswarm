# GitHub Copilot Instructions for Coinswarm

## Critical Documentation

**⚠️ BEFORE suggesting any deployment or worker changes, review:**

1. `/CLOUDFLARE_DEPLOYMENT_GUIDE.md` - Essential Cloudflare Workers deployment knowledge
2. `.claude/important-docs.md` - Quick reference for common issues

## Key Deployment Rules

### Always Follow These Principles

1. **Use `wrangler deploy` not `wrangler versions upload`**
   - `deploy` = creates + activates version ✅
   - `versions upload` = creates version only, doesn't activate ❌

2. **One Deployment Method Only**
   - Either GitHub Actions OR Cloudflare Git Integration
   - Using both causes version activation conflicts
   - Current standard: GitHub Actions only

3. **Check Git Integration Settings**
   - When users report "deployed but not active" issues
   - Problem: Git Integration enabled with wrong production branch
   - Solution: Disable Git Integration or update production branch

4. **Branch Pattern Support**
   - All `claude/**` branches supported in GitHub Actions
   - Git Integration production branch: often outdated
   - Don't assume Git Integration branch matches current work

## Code Completion Context

### When suggesting deployment code:

```yaml
# ✅ GOOD - Creates and activates
- uses: cloudflare/wrangler-action@v3
  with:
    command: deploy --config wrangler.toml

# ❌ BAD - Creates but doesn't activate
- uses: cloudflare/wrangler-action@v3
  with:
    command: versions upload --config wrangler.toml
```

### When suggesting wrangler.toml changes:

```toml
# ✅ GOOD - Account ID via environment
# account_id = "8a330fc6c339f031a73905d4ca2f3e5d"

# ❌ BAD - Hardcoded account ID
account_id = "8a330fc6c339f031a73905d4ca2f3e5d"
```

## Common Troubleshooting Patterns

### User says: "My deployment succeeded but code isn't live"

**Likely cause:** Git Integration enabled with wrong production branch

**Suggest:**
1. Check Cloudflare Dashboard → Workers & Pages → Settings → Production branch
2. Either disable Git Integration or update to current branch
3. Re-run deployment after fixing settings

### User says: "How do I add a new worker?"

**Steps to suggest:**
1. Create `cloudflare-agents/wrangler-[name].toml`
2. Create worker TypeScript file
3. Add to `.github/workflows/deploy-cloudflare-workers.yml`:
   - Add path filter for change detection
   - Add deployment step with conditional logic
4. Reference `dashboards` worker as example

### User says: "Which branch should I use for production?"

**Context:**
- Current setup uses unified GitHub Actions workflow
- Supports all `claude/**` branches
- If Git Integration is enabled, production branch controls activation
- Recommend: Deploy to `main`, test on `claude/*` branches

## Repository Structure

```
Coinswarm/
├── .github/workflows/
│   └── deploy-cloudflare-workers.yml  # Unified deployment (14 workers)
├── cloudflare-agents/
│   ├── wrangler-*.toml                # Per-worker configs
│   └── *-agent.ts                     # Worker source files
├── cloudflare-workers/
│   └── *.js                           # JavaScript workers (2)
├── CLOUDFLARE_DEPLOYMENT_GUIDE.md     # CRITICAL REFERENCE
└── .claude/important-docs.md          # Quick reference

Total workers: 14 (12 TypeScript + 2 JavaScript)
```

## Smart Conditional Deployment

The workflow uses `dorny/paths-filter@v3` to detect which files changed:

```yaml
# Only deploy workers whose files actually changed
- name: Deploy Dashboards
  if: steps.filter.outputs.dashboards == 'true' || steps.filter.outputs.workflow == 'true'
  uses: cloudflare/wrangler-action@v3
  with:
    command: deploy --config wrangler-dashboards.toml
```

**When adding new workers:**
- Add path filter in "Detect changed files" step
- Use same conditional pattern in deployment step
- Include `|| steps.filter.outputs.workflow == 'true'` for workflow changes

## Security Practices

1. **Never suggest hardcoding:**
   - Account IDs in wrangler.toml (use env vars)
   - API tokens anywhere (use GitHub Secrets)
   - API keys in toml files (use secrets)

2. **Always suggest:**
   - Using `${{ secrets.CLOUDFLARE_API_TOKEN }}`
   - Using `${{ secrets.CLOUDFLARE_ACCOUNT_ID }}`
   - Adding secrets via `wrangler secret put`

## Account Context

- **Account ID:** `8a330fc6c339f031a73905d4ca2f3e5d`
- **D1 Database:** `coinswarm-evolution` (ID: `ac4629b2-8240-4378-b3e3-e5262cd9b285`)
- **Primary Worker:** Evolution Agent (orchestrator)
- **Dashboard URL:** `https://dash.cloudflare.com/8a330fc6c339f031a73905d4ca2f3e5d/workers`

---

**For complex deployment issues, always refer to `/CLOUDFLARE_DEPLOYMENT_GUIDE.md`**
