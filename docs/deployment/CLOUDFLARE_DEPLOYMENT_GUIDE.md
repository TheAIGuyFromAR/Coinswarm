# Cloudflare Deployment Guide

**CRITICAL: Read before making any changes to deployment configuration!**

## 1. Overview
- Use GitHub Actions for all deployments
- Never use Cloudflare Git Integration (causes version conflicts)
- Each worker has its own wrangler config and source file

## 2. Deployment Steps
1. Update worker code and config
2. Commit changes to GitHub
3. GitHub Actions triggers deployment
4. Verify deployment in Cloudflare dashboard

## 3. Troubleshooting
- If deployment "succeeds but code isn't live":
	- Check Cloudflare dashboard settings
	- Disable Git Integration if enabled
	- Re-run deployment

## 4. Security
- Never commit secrets to git
- Use `wrangler secret put` for all secrets
- Reference D1 and other resources by name, not ID

## 5. References
- See `.github/workflows/deploy-cloudflare-workers.yml`
- See `cloudflare-agents/wrangler-*.toml`
- See `docs/deployment/DEPLOYMENT_INSTRUCTIONS.md`