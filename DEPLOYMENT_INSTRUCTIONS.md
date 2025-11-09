# DEPLOYMENT INSTRUCTIONS - Historical Data Collection

**Critical Issue:** Cloudflare Workers only deploy from `main` branch, not feature branches.

## Current Situation

✅ **Code complete** on `claude/audit-historical-data-system-011CUx7r66ZDX5rTp6bRDQYE`
❌ **Not deployed** - Changes on feature branch, Cloudflare not deploying
❌ **Main protected** - Cannot push directly (HTTP 403)

**Root cause:** Cloudflare Workers configured to deploy from `main` only.

## Solution: Create Pull Request

**PR URL:**
https://github.com/TheAIGuyFromAR/Coinswarm/compare/main...claude/audit-historical-data-system-011CUx7r66ZDX5rTp6bRDQYE

**After PR is merged:**
1. Cloudflare deploys from main (~5 min)
2. Call `/init` endpoint to seed database
3. Wait for next cron (:00) to start collection
4. Historical data collection begins

**Total time to first data:** ~40 minutes after merge
