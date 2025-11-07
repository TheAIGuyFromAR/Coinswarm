# Fix for "/memberships" API Error - Missing Permission

## The Problem
Error: `A request to the Cloudflare API (/memberships) failed`

This specific endpoint requires: **Account Settings: Read**

## Check Your Current Token

Go to: https://dash.cloudflare.com/profile/api-tokens

Find your token and click **Edit**. Check if you have:

### Required Permissions Checklist:

**Account Permissions:**
- [ ] **Account Settings** → **Read** ⚠️ **THIS IS WHAT'S MISSING**
- [ ] Workers Scripts → Edit (you probably have this)
- [ ] D1 → Edit (you probably have this)

### The Fix

1. Click **Edit** on your existing token
2. Scroll to **Account Permissions**
3. Click **+ Add more**
4. Find: **Account Settings**
5. Set to: **Read**
6. Click **Continue to summary**
7. Click **Save**

## Still Not Working?

If you added Account Settings: Read and it still fails, check:

### Is the Account Scope Correct?

In your token settings, under **Account Resources**:
- ❌ If it says "All accounts" → Change to your specific account
- ✅ Should say your account name/ID

### Verify Token Works

Test locally:
```bash
export CLOUDFLARE_API_TOKEN="your-token"
cd cloudflare-agents
npx wrangler whoami
```

Should show:
```
Getting User settings...
👋 You are logged in with an API Token, associated with the email 'your-email@example.com'!
┌──────────────────────┬──────────────────────────────────┐
│ Account Name         │ Account ID                        │
├──────────────────────┼──────────────────────────────────┤
│ Your Account Name    │ abc123...                        │
└──────────────────────┴──────────────────────────────────┘
```

If `wrangler whoami` fails → token is wrong
If `wrangler whoami` works but deploy fails → different issue

## Quick Test: Update GitHub Secret

After adding Account Settings: Read:

1. Go to: https://github.com/TheAIGuyFromAR/Coinswarm/settings/secrets/actions
2. Find **CLOUDFLARE_API_TOKEN**
3. Click **Update**
4. Paste the SAME token (to refresh it)
5. Click **Update secret**

Then retry the deployment:
```bash
git commit --allow-empty -m "Retry deployment"
git push
```

## Nuclear Option: Recreate Token

If editing doesn't work, create fresh:

1. Delete old token
2. Create new with these EXACT permissions:

**Template:** Edit Cloudflare Workers

**Account Resources:** [Your Account Name] (not "All accounts")

**Account Permissions:**
- Account Settings → **Read**
- Workers Scripts → **Edit**
- D1 → **Edit**

**Zone Resources:** All zones (or specific zone)

**Zone Permissions:**
- Workers Routes → **Edit**

That's it - nothing more needed!

## Alternative: Just Use API Key

Fastest solution to get unblocked:

1. Go to: https://dash.cloudflare.com/profile/api-tokens
2. Scroll to **"API Keys"**
3. Click **View** next to **Global API Key**
4. Copy it
5. Update GitHub Secret with this

API Key has all permissions - guaranteed to work.

---

**TL;DR:** Add **"Account Settings: Read"** to your existing token. That's the permission for the `/memberships` endpoint.
