# 🚨 CRITICAL: Cloudflare Workers Deployment Guide

**⚠️ READ THIS BEFORE DEPLOYING WORKERS ⚠️**

This document explains how Cloudflare Workers deployments work and how to avoid common pitfalls that cause versions to be created but not activated.

---

## Table of Contents

1. [Understanding Versions vs Deployments](#understanding-versions-vs-deployments)
2. [Git Integration vs GitHub Actions](#git-integration-vs-github-actions)
3. [Common Problems & Solutions](#common-problems--solutions)
4. [Deployment Configuration](#deployment-configuration)
5. [Best Practices](#best-practices)
6. [Troubleshooting](#troubleshooting)

---

## Understanding Versions vs Deployments

### 🔑 KEY CONCEPT

Cloudflare Workers separates **versions** (code uploads) from **deployments** (what's serving traffic).

```
Version = Code uploaded to Cloudflare
Deployment = Which version is actively serving traffic
```

### The Two Commands

#### `wrangler deploy`
- ✅ Creates a new version
- ✅ **Automatically activates it** (makes it serve 100% of traffic)
- ✅ **This is what you want for CI/CD**

#### `wrangler versions upload` (or `wrangler versions deploy`)
- ✅ Creates a new version
- ❌ **Does NOT activate it**
- ⚠️ Requires separate activation via dashboard or API
- 📝 Used for gradual rollouts or manual approval workflows

### Real-World Problem

```
Symptom: "My code deployed but the worker is still running old code"
Cause: You're creating versions but not activating them
Solution: Use `wrangler deploy` not `wrangler versions upload`
```

---

## Git Integration vs GitHub Actions

### 🚨 CRITICAL: These Can Conflict!

Cloudflare offers **TWO** deployment mechanisms that can work against each other:

### 1. Cloudflare Git Integration (Dashboard-Based)

**Location**: Cloudflare Dashboard → Workers & Pages → [Your Worker] → Settings

**Configuration Example:**
```
Build command: None
Deploy command: npx wrangler deploy
Version command: npx wrangler versions upload  ⚠️ DANGER
Root directory: /cloudflare-agents/dashboards
Production branch: main  ⚠️ CONTROLS ACTIVATION
```

**How It Works:**
- Cloudflare monitors your GitHub repo
- When code is pushed to the **Production branch**, it auto-deploys
- Only deployments from the production branch are **activated**
- Deployments from other branches create versions but don't activate them

**The Problem:**
```
Production branch: claude/audit-historical-data-system-011CUx7r66ZDX5rTp6bRDQYE

Your current branch: claude/fix-deployment-issues-011CUyVUGjyMbF9mBiM4WYuf

Result: Your GitHub Actions deploys create versions but Cloudflare
        only activates versions from the old branch!

Effect: Worker stays 6+ versions behind your actual code!
```

### 2. GitHub Actions Deployment (Workflow-Based)

**Location**: `.github/workflows/deploy-cloudflare-workers.yml`

**How It Works:**
- GitHub Actions runs on push to specified branches
- Uses `wrangler deploy` command
- Should activate versions immediately

**The Problem:**
- If Git Integration is ALSO enabled in Cloudflare dashboard
- Git Integration settings **override** GitHub Actions deployments
- Your versions get created but not activated

### 🎯 The Solution

**Choose ONE deployment method:**

#### Option A: Disable Cloudflare Git Integration (RECOMMENDED)
1. Go to Cloudflare Dashboard → Workers & Pages → [Your Worker] → Settings
2. Disconnect or disable Git integration
3. Let GitHub Actions be the sole deployment controller
4. Ensures `wrangler deploy` from Actions actually activates versions

#### Option B: Update Production Branch Setting
1. Go to Cloudflare Dashboard → Workers & Pages → [Your Worker] → Settings
2. Change "Production branch" to match your actual deployment branch:
   - `main` for production
   - `claude/**` if Cloudflare supports wildcards (it doesn't)
   - Your current active branch for testing
3. **Downside**: Need to update this for every new branch

#### Option C: Use Branch-Specific Workers
1. Deploy different workers for different branches
2. Use environment-specific worker names
3. Overly complex for most use cases

---

## Common Problems & Solutions

### Problem 1: "Deployed but still showing old code"

**Symptoms:**
- GitHub Actions shows successful deployment
- Cloudflare shows new version created
- Worker still serves old code
- Dashboard shows version 6+ behind

**Root Cause:**
```
Cloudflare Git Integration is enabled with wrong production branch
→ New versions created but not activated
→ Old version still serving traffic
```

**Solution:**
1. Check Cloudflare Dashboard Settings
2. Either disable Git Integration OR update production branch
3. Re-run deployment to activate latest version

### Problem 2: "Works on main, not on feature branches"

**Symptoms:**
- Deploys from `main` activate correctly
- Deploys from `claude/*` branches don't activate
- GitHub Actions shows success

**Root Cause:**
```
Production branch: main
Your branch: claude/fix-something

→ Cloudflare only auto-activates from main branch
→ Feature branch deploys create versions but don't activate
```

**Solution:**
- Disable Git Integration entirely
- Let GitHub Actions control activation via `wrangler deploy`

### Problem 3: "Version command vs Deploy command confusion"

**Configuration in Dashboard:**
```
Deploy command: npx wrangler deploy           ✅ Good
Version command: npx wrangler versions upload ⚠️ Creates confusion
```

**What Happens:**
- Deploy command creates + activates versions
- Version command only creates versions
- If Git Integration uses version command, activation breaks

**Solution:**
- Remove or comment out version command
- Only use deploy command
- Or disable Git Integration entirely

---

## Deployment Configuration

### Our Current Setup

#### GitHub Actions Workflow
**File**: `.github/workflows/deploy-cloudflare-workers.yml`

**Key Features:**
- Unified workflow managing 14 workers
- Smart conditional deployment (only changed workers)
- Uses `wrangler deploy` for all deployments
- Supports `claude/**` branch pattern

**Deployment Logic:**
```yaml
- name: Deploy Dashboards
  if: steps.filter.outputs.dashboards == 'true' || steps.filter.outputs.workflow == 'true'
  uses: cloudflare/wrangler-action@v3
  with:
    apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
    accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
    workingDirectory: 'cloudflare-agents'
    wranglerVersion: "4.45.4"
    command: deploy --config wrangler-dashboards.toml  # ✅ Uses deploy, not versions
```

#### Wrangler Configuration
**File**: `cloudflare-agents/wrangler-dashboards.toml`

```toml
name = "dashboards"
compatibility_date = "2024-01-01"

# Account ID set via GitHub Secrets, not hardcoded
# account_id = "8a330fc6c339f031a73905d4ca2f3e5d"

[assets]
directory = "dashboards"
```

### Required Cloudflare Settings

#### For Git-Integration-Free Deployment (RECOMMENDED)

1. **Disconnect Git Integration:**
   - Dashboard → Workers & Pages → Settings
   - Remove GitHub connection
   - Or disable automatic deployments

2. **Use API Token:**
   - Create API token with Workers deploy permissions
   - Store in GitHub Secrets as `CLOUDFLARE_API_TOKEN`
   - Store account ID in GitHub Secrets as `CLOUDFLARE_ACCOUNT_ID`

3. **Let GitHub Actions Control Everything:**
   - All deployments via `wrangler deploy` in Actions
   - Full control over when and what activates
   - Consistent across all workers

#### For Git-Integration-Based Deployment (NOT RECOMMENDED)

1. **Update Production Branch:**
   - Dashboard → Workers & Pages → Settings → Production branch
   - Set to `main` or your primary deployment branch

2. **Configure Deploy Command:**
   ```
   Deploy command: npx wrangler deploy
   Version command: [Leave empty or remove]
   ```

3. **Accept Limitations:**
   - Only production branch auto-activates
   - Feature branches create versions but need manual activation
   - Two deployment systems create confusion

---

## Best Practices

### ✅ DO

1. **Use `wrangler deploy` for all automated deployments**
   - Creates AND activates versions
   - Consistent behavior
   - No manual intervention needed

2. **Choose ONE deployment method**
   - Either GitHub Actions OR Git Integration
   - Not both
   - Prevents conflicts

3. **Use GitHub Actions for multi-branch workflows**
   - Better control over branch patterns
   - Conditional deployment logic
   - Unified workflow for all workers

4. **Document your deployment strategy**
   - Which method you're using
   - Where to find settings
   - How to troubleshoot

5. **Monitor version activation**
   - Check that deployed versions are actually serving traffic
   - Don't assume success from GitHub Actions green checkmark
   - Verify in Cloudflare dashboard

### ❌ DON'T

1. **Don't use both Git Integration AND GitHub Actions**
   - They will conflict
   - Git Integration settings override Actions
   - Creates version activation issues

2. **Don't use `wrangler versions upload` in CI/CD**
   - Creates versions without activating them
   - Requires manual activation
   - Defeats purpose of automation

3. **Don't rely on old production branch settings**
   - Update or disable them
   - Old branch names break activation
   - Check settings when switching branches

4. **Don't assume deployment = activation**
   - Always verify version is active
   - Check worker behavior after deploy
   - Monitor Cloudflare dashboard

5. **Don't hardcode account IDs in wrangler.toml**
   - Use environment variables
   - Use GitHub Secrets
   - Keeps credentials secure

---

## Troubleshooting

### Step 1: Verify Deployment Method

**Check which system deployed the current version:**

1. Go to Cloudflare Dashboard
2. Navigate to Workers & Pages → [Your Worker] → Versions
3. Look at the most recent version:
   - Source: "GitHub" = Git Integration deployed it
   - Source: "API" = GitHub Actions/wrangler CLI deployed it

### Step 2: Check Version Activation

**Verify which version is serving traffic:**

1. Go to Cloudflare Dashboard
2. Navigate to Workers & Pages → [Your Worker]
3. Look for "Active Deployment" or "Production"
4. Compare version number to your latest deployment

**If versions don't match:**
- Your latest code is uploaded but not activated
- Check Git Integration settings (production branch)
- Or manually activate the version in dashboard

### Step 3: Review Git Integration Settings

**Dashboard → Workers & Pages → [Your Worker] → Settings**

Look for:
```
Production branch: [BRANCH NAME]
```

**Fix:**
- If using GitHub Actions: Disable Git Integration
- If using Git Integration: Update to correct branch

### Step 4: Test Deployment

**Quick test to verify activation:**

1. Make a small change (e.g., add a comment)
2. Commit and push
3. Wait for GitHub Actions to complete
4. Check Cloudflare dashboard for new version
5. **Verify version is marked as "Active"**
6. Test worker URL to confirm code change is live

### Step 5: Manual Activation (Emergency Fix)

**If you need to activate a version immediately:**

1. Go to Cloudflare Dashboard
2. Navigate to Workers & Pages → [Your Worker] → Versions
3. Find the version you want to activate
4. Click "Manage Deployment" or similar
5. Set deployment percentage to 100%
6. Confirm activation

**Note:** This is a temporary fix. Fix the underlying configuration issue.

---

## Account Information

**Cloudflare Account ID:** `8a330fc6c339f031a73905d4ca2f3e5d`

**Workers Deployed:**
- Evolution Agent
- News & Sentiment Agent
- Multi-Exchange Data Worker
- Solana DEX Worker
- Sentiment Backfill Worker
- Historical Data Worker
- Historical Data Collection Cron
- Real-Time Price Collection Cron
- Data Collection Monitor
- Technical Indicators Agent
- Collection Alerts Agent
- **Dashboards** (Static HTML assets)
- Comprehensive Data Worker
- Data Backfill Worker

**Deployment Workflow:** `.github/workflows/deploy-cloudflare-workers.yml`

**Branch Pattern:** `claude/**` (all Claude Code session branches)

---

## Quick Reference Commands

### Deploy from CLI
```bash
# Deploy specific worker (creates + activates)
cd cloudflare-agents
npx wrangler deploy --config wrangler-dashboards.toml

# Deploy with specific account
CLOUDFLARE_ACCOUNT_ID=8a330fc6c339f031a73905d4ca2f3e5d npx wrangler deploy
```

### Check Current Deployment
```bash
# List versions
npx wrangler versions list --name dashboards

# View deployment status
npx wrangler deployments list --name dashboards
```

### Test Worker
```bash
# Replace with your worker URL
curl https://dashboards.your-subdomain.workers.dev/

# Check specific version
curl -H "CF-Workers-Version: v123" https://dashboards.your-subdomain.workers.dev/
```

---

## For Future AI Assistants (Claude Code / GitHub Copilot)

### 🤖 Important Context

When helping with Cloudflare Workers deployments:

1. **Always ask about Git Integration first**
   - Is it enabled?
   - What's the production branch setting?
   - This is the #1 cause of "deployed but not active" issues

2. **Verify deployment method**
   - GitHub Actions OR Git Integration, not both
   - Check which one is actually controlling activation

3. **Use `wrangler deploy` in all automation**
   - Never suggest `wrangler versions upload` for CI/CD
   - Deployment should activate versions automatically

4. **Check version activation, not just deployment success**
   - Green checkmark in GitHub Actions ≠ version is active
   - Always verify in Cloudflare dashboard

5. **Recommend disabling Git Integration for multi-branch workflows**
   - GitHub Actions gives better control
   - Supports `claude/**` pattern natively
   - Prevents activation conflicts

### Common User Reports & Solutions

**"It deployed but my code isn't live"**
→ Check Git Integration production branch setting

**"Works on main but not my feature branch"**
→ Disable Git Integration, use GitHub Actions exclusively

**"GitHub Actions succeeds but nothing changes"**
→ Git Integration is overriding; disable it

**"Which version is actually running?"**
→ Check Cloudflare Dashboard → Versions → Active Deployment

---

## Related Documentation

- [Cloudflare Workers Versioning Docs](https://developers.cloudflare.com/workers/configuration/versions-and-deployments/)
- [Wrangler Deploy Command](https://developers.cloudflare.com/workers/wrangler/commands/#deploy)
- [GitHub Actions Workflow](.github/workflows/deploy-cloudflare-workers.yml)
- [Workers Configuration](cloudflare-agents/wrangler-dashboards.toml)

---

**Last Updated:** 2025-11-10
**Author:** Claude Code
**Status:** CRITICAL REFERENCE - DO NOT DELETE

---
