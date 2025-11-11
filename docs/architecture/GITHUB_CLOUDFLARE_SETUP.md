# GitHub to Cloudflare Workers - Automated Deployment Setup

## 🎯 What This Does

Automatically deploys your Cloudflare Worker whenever you push code to GitHub.

## ✅ Files Created

- `wrangler.toml` - Worker configuration
- `.github/workflows/deploy-worker.yml` - GitHub Actions deployment workflow

## 📋 Setup Instructions (5 minutes)

### Step 1: Add Cloudflare API Token to GitHub Secrets

1. **Get your Cloudflare API Token:**
   - Go to: https://dash.cloudflare.com/profile/api-tokens
   - Click "Create Token"
   - Use template: "Edit Cloudflare Workers"
   - Or use your existing token: `rvXIkCIXf778QSR1tVlHHjjPqh3x3xRLJ73zmikf`

2. **Add to GitHub Secrets:**
   - Go to your GitHub repo: https://github.com/TheAIGuyFromAR/Coinswarm
   - Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `CLOUDFLARE_API_TOKEN`
   - Value: `rvXIkCIXf778QSR1tVlHHjjPqh3x3xRLJ73zmikf` (or your new token)
   - Click "Add secret"

### Step 2: (Optional) Add CryptoCompare API Key for Comprehensive Worker

If you want to use the comprehensive multi-source worker:

1. **Add API Key Secret:**
   - Same location: Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `CRYPTOCOMPARE_API_KEY`
   - Value: `da672b9999120841fbd4427fa4550b83b5f23e017c5c03ff33bafe09064abe83`
   - Click "Add secret"

2. **Update wrangler.toml:**
   - Change `main = "cloudflare-workers/simple-coingecko-worker.js"`
   - To: `main = "cloudflare-workers/comprehensive-data-worker.js"`

3. **Uncomment environment variables in workflow:**
   - Edit `.github/workflows/deploy-worker.yml`
   - Uncomment the `secrets:` and `env:` sections

### Step 3: Push Changes to Trigger Deployment

All the necessary files are already committed to your branch. The workflow will automatically run when you push changes to:
- Worker files in `cloudflare-workers/`
- `wrangler.toml`
- The workflow file itself

### Step 4: Verify Deployment

1. **Check GitHub Actions:**
   - Go to: https://github.com/TheAIGuyFromAR/Coinswarm/actions
   - You should see "Deploy to Cloudflare Workers" workflow running
   - Wait for green checkmark ✅

2. **Test the deployed worker:**
   ```bash
   # For simple CoinGecko worker:
   curl "https://swarm.bamn86.workers.dev/data?symbol=BTC&days=180"

   # Should return JSON with 180 days of data
   ```

## 🔧 Configuration Options

### Which Worker to Deploy

Edit `wrangler.toml` and change the `main` field:

**Option 1: Simple CoinGecko (No API Key)**
```toml
main = "cloudflare-workers/simple-coingecko-worker.js"
```
- 365 days max
- Hourly/daily data
- No authentication

**Option 2: Comprehensive Multi-Source (Requires API Key)**
```toml
main = "cloudflare-workers/comprehensive-data-worker.js"
```
- 2+ years of data
- Minute/hour/day intervals
- Multiple source fallbacks
- Requires `CRYPTOCOMPARE_API_KEY` environment variable

**Option 3: Minute-Level Data**
```toml
main = "cloudflare-workers/minute-data-worker.js"
```
- 5/15/30/60 minute intervals
- Kraken-based
- Recent data focus

### Branch Configuration

The workflow is currently set to deploy from:
- `claude/debug-cloudflare-historical-data-011CUqugUynEoovcsiVnoaPB` (current branch)
- `main` (if you create it later)
- `master` (if you create it later)

Edit `.github/workflows/deploy-worker.yml` to change which branches trigger deployment.

## 📊 GitHub Settings for Cloudflare Integration

If you're using the Cloudflare GitHub App integration (via Cloudflare Dashboard):

### For Cloudflare Pages (Static Sites)
**NOT applicable** - This repo contains Workers, not static pages.

### For Cloudflare Workers (via GitHub Actions)
**Settings:**
- **Repository:** TheAIGuyFromAR/Coinswarm
- **Branch:** claude/debug-cloudflare-historical-data-011CUqugUynEoovcsiVnoaPB
- **Build command:** *(leave empty)*
- **Build output directory:** *(leave empty)*

**Secrets Required:**
- `CLOUDFLARE_API_TOKEN` - Your Cloudflare API token
- `CRYPTOCOMPARE_API_KEY` - (optional) For comprehensive worker

## 🎯 Quick Summary

**For the GitHub-Cloudflare connection you're setting up:**

```
Repository: TheAIGuyFromAR/Coinswarm
Branch:     claude/debug-cloudflare-historical-data-011CUqugUynEoovcsiVnoaPB
            (or create 'main' branch later)

Build Command:  (empty - no build needed)
Output Dir:     (empty - workers don't have output)

Secrets to add in GitHub:
  - CLOUDFLARE_API_TOKEN = rvXIkCIXf778QSR1tVlHHjjPqh3x3xRLJ73zmikf
  - CRYPTOCOMPARE_API_KEY = da672b9999120841fbd4427fa4550b83b5f23e017c5c03ff33bafe09064abe83
```

## ✅ Next Steps

1. **Add secrets to GitHub** (Step 1 above)
2. **Commit these new files** (wrangler.toml and workflow)
3. **Push to GitHub** - deployment will happen automatically
4. **Check GitHub Actions** tab to see deployment status
5. **Test your worker** with the curl commands above

## 🔍 Troubleshooting

**Workflow not running?**
- Check that secrets are added correctly
- Verify workflow file is in `.github/workflows/` directory
- Make sure you pushed changes to a branch listed in the workflow

**Deployment fails?**
- Check Cloudflare API token has "Edit Cloudflare Workers" permission
- Verify worker name "swarm" doesn't conflict with existing workers
- Check GitHub Actions logs for specific error messages

**Worker returns 404?**
- Wait 30 seconds after deployment for changes to propagate
- Verify worker name matches in wrangler.toml
- Check Cloudflare Dashboard → Workers to see if it deployed

---

**Current Status:** All files ready, just need to add secrets to GitHub and deployment will be automatic! 🚀
