# Fix for /memberships Error - Account ID Required

## The Problem

When using an **account-scoped API token** (not user-scoped), wrangler can't call the `/memberships` endpoint to figure out which account to deploy to.

## Solution: Add Account ID

You need to tell wrangler which account to use. There are two ways:

### Option 1: Add to GitHub Secret (Recommended for CI/CD)

1. **Get your Account ID:**
   - Go to: https://dash.cloudflare.com
   - Click on any domain or Workers & Pages
   - Look at the URL: `https://dash.cloudflare.com/YOUR_ACCOUNT_ID/...`
   - Copy that account ID (looks like: `abc123def456...`)

2. **Add as GitHub Secret:**
   - Go to: https://github.com/TheAIGuyFromAR/Coinswarm/settings/secrets/actions
   - Click **"New repository secret"**
   - Name: `CLOUDFLARE_ACCOUNT_ID`
   - Value: `your-account-id-here`
   - Click **"Add secret"**

3. **Done!** The workflow is already updated to use it.

### Option 2: Add to wrangler.toml (Alternative)

Add this line at the top of `cloudflare-agents/wrangler.toml`:

```toml
name = "coinswarm-evolution-agent"
account_id = "your-account-id-here"  # Add this line
main = "evolution-agent.ts"
```

## How to Get Your Account ID

**Method 1: From Dashboard URL**
1. Go to https://dash.cloudflare.com
2. Click on Workers & Pages
3. Look at URL: `https://dash.cloudflare.com/YOUR_ACCOUNT_ID/workers`
4. Copy the account ID

**Method 2: From Existing Worker**
1. Go to https://dash.cloudflare.com
2. Click Workers & Pages
3. Click any existing worker
4. Click Settings
5. Account ID is shown there

**Method 3: From API Token Page**
When you created the API token, you selected an account - that's your account ID.

## Why This Happens

- **User-scoped token**: Can call `/memberships` to find all accounts
- **Account-scoped token**: Can't call `/memberships` (security feature)
- **Solution**: Explicitly tell wrangler the account ID

---

**Next Step:** Get your account ID and add it as a GitHub Secret named `CLOUDFLARE_ACCOUNT_ID`, then retry the deployment!
