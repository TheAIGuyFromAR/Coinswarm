# Cloudflare API Token - Correct Permissions for Agents SDK

## Issue: Can't Find "Durable Objects" in Permissions List

Durable Objects permissions are often bundled under different names or automatically included.

## Solution: Use the Workers Template + Account Access

### Method 1: Use "Edit Cloudflare Workers" Template (Easiest)

1. Go to: https://dash.cloudflare.com/profile/api-tokens
2. Click **"Create Token"**
3. Select **"Edit Cloudflare Workers"** template
4. **Under "Account Resources"** section, make sure it says:
   - Include → **All accounts** (or your specific account)
5. **Add these additional permissions:**
   - Account → **D1** → **Edit**
   - Account → **Workers AI** → **Edit** (if available)
6. Create token

The "Edit Cloudflare Workers" template should automatically include Durable Objects access.

### Method 2: Custom Token with Full Workers Access

If the template doesn't work, create a custom token:

**Account Permissions:**
- ✅ Account → **Workers Scripts** → **Edit**
- ✅ Account → **Workers KV Storage** → **Edit**
- ✅ Account → **Workers R2 Storage** → **Edit** (includes Durable Objects)
- ✅ Account → **D1** → **Edit**
- ✅ Account → **Account Settings** → **Read**

**Zone Permissions (if asked):**
- All zones (or select specific zone)

### Method 3: Use API Key Instead (Quick Fix)

If token permissions are confusing, use your Global API Key temporarily:

1. Go to: https://dash.cloudflare.com/profile/api-tokens
2. Scroll to **"API Keys"** section
3. Click **"View"** next to **"Global API Key"**
4. Copy this key
5. In GitHub Secrets, update CLOUDFLARE_API_TOKEN with this key

⚠️ **Note:** API Keys have full access - less secure but guaranteed to work.

## Common Permission Names

Durable Objects might be listed as:
- ✅ **Workers Scripts** (includes Durable Objects)
- ✅ **Workers R2 Storage** (sometimes bundles DO)
- ✅ **Account Resources: All** (gives everything)
- Not listed separately (auto-included with Workers)

## Verify Your Token Has Correct Access

After creating the token, test it:

```bash
curl -X GET "https://api.cloudflare.com/client/v4/accounts" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

Should return your account info. If it returns an error, the token doesn't have account-level access.

## What GitHub Actions Actually Needs

Looking at the error `(/memberships)`, the token needs:
1. **Account-level access** (not just zone-level)
2. **Workers Scripts: Edit**
3. **Account Settings: Read** (for /memberships endpoint)

## Recommended Token Configuration

**Token Name:** `GitHub Actions - Workers Deploy`

**Permissions:**
```
Account Resources: [Your Account Name]
  ├─ Account Settings: Read
  ├─ Workers Scripts: Edit
  ├─ Workers KV Storage: Edit
  └─ D1: Edit

Zone Resources: All zones
  └─ Workers Routes: Edit
```

**Account Resources** section is critical - make sure it's set to your account, not "All accounts".

## Alternative: Simplify Deployment

If tokens keep failing, we can modify the deployment to use simpler Workers without Durable Objects:

### Option A: Use Traditional Worker (Already Working)
The traditional Worker approach (wrangler-evolution.toml) should already work with your current token since it doesn't use Durable Objects.

### Option B: Deploy Agents SDK Locally
```bash
export CLOUDFLARE_API_TOKEN="your-token"
cd cloudflare-agents
npx wrangler deploy
```

This gives better error messages about what's missing.

## Debug: Check What's Actually Wrong

Run this locally to see the exact error:

```bash
cd cloudflare-agents
npx wrangler whoami
```

This will show:
- ✅ If authentication works
- ✅ Your account ID
- ✅ What permissions are available

If `wrangler whoami` fails with same error, the token definitely needs account-level permissions.

## Quick Checklist

Before creating the token:
- [ ] Choose "Edit Cloudflare Workers" template
- [ ] Set Account Resources to YOUR account (not "All accounts")
- [ ] Verify "Workers Scripts: Edit" is included
- [ ] Add "D1: Edit" permission
- [ ] Add "Account Settings: Read" permission

After creating:
- [ ] Copy token immediately (shown only once)
- [ ] Update GitHub Secret: CLOUDFLARE_API_TOKEN
- [ ] Test with `wrangler whoami` locally

---

**Most Likely Solution:** Use "Edit Cloudflare Workers" template and make sure "Account Resources" is set to your specific account. Durable Objects will be included automatically.
