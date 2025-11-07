# Cloudflare API Token Troubleshooting

## Error: Unable to authenticate request [code: 10001]

This usually means the API token doesn't have the right permissions for the new features we're using (Durable Objects, Agents SDK).

## Quick Fixes

### Option 1: Update Token Permissions (Recommended)

Go to Cloudflare Dashboard and add these permissions to your existing token:

**Required Permissions for Agents SDK:**
1. **Account** → **Workers Scripts** → **Edit**
2. **Account** → **Workers KV Storage** → **Edit**
3. **Account** → **Workers Tail** → **Read**
4. **Account** → **Account Settings** → **Read** (for /memberships)
5. **Account** → **D1** → **Edit**
6. **Account** → **Durable Objects** → **Edit** ⚠️ **CRITICAL**
7. **Account** → **Workers AI** → **Edit** (for AI features)

### Option 2: Create New Token with Template

1. Go to: https://dash.cloudflare.com/profile/api-tokens
2. Click **"Create Token"**
3. Use the **"Edit Cloudflare Workers"** template
4. **Add these additional permissions:**
   - Account → D1 → Edit
   - Account → Durable Objects → Edit
   - Account → Workers AI → Edit
5. Click **"Continue to summary"**
6. Click **"Create Token"**
7. **Copy the new token** (you can only see it once!)

### Option 3: Use API Key (Less Secure, but Works)

Instead of API Token, use your Global API Key:
1. Go to: https://dash.cloudflare.com/profile/api-tokens
2. Scroll down to **"API Keys"**
3. Click **"View"** next to Global API Key
4. Use this in GitHub Secrets instead

⚠️ **Note:** API Keys have full account access - less secure than scoped tokens.

## Update GitHub Secret

Once you have the new token:

1. Go to: https://github.com/TheAIGuyFromAR/Coinswarm/settings/secrets/actions
2. Click on **CLOUDFLARE_API_TOKEN**
3. Click **"Update"**
4. Paste your new token
5. Click **"Update secret"**

## Why This Happens

**Durable Objects** and **Agents SDK** require special permissions that weren't needed for basic Workers:

- Basic Worker: Only needs `Workers Scripts:Edit`
- **Agents SDK**: Also needs `Durable Objects:Edit`, `D1:Edit`, `Workers AI:Edit`

Your old token probably only had basic Workers permissions.

## Test the New Token

After updating the token in GitHub Secrets:

1. Re-run the failed GitHub Action
2. Or push a small change to trigger deployment:

```bash
# Make a small change to trigger redeployment
git commit --allow-empty -m "Trigger deployment with new API token"
git push
```

## Alternative: Deploy from Local Machine

If GitHub Actions keeps failing, you can deploy locally:

```bash
# Set your token
export CLOUDFLARE_API_TOKEN="your-new-token-here"

# Deploy
cd cloudflare-agents
npm install
npx wrangler deploy
```

## Verify Token Permissions

You can test your token permissions:

```bash
# Test basic auth
curl -X GET "https://api.cloudflare.com/client/v4/user/tokens/verify" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"

# Should return: "status": "active"
```

## Quick Checklist

- [ ] Token has `Durable Objects:Edit` permission
- [ ] Token has `D1:Edit` permission
- [ ] Token has `Workers AI:Edit` permission
- [ ] Token has `Account Settings:Read` permission
- [ ] GitHub Secret is updated with new token
- [ ] Token is not expired
- [ ] Using the correct token (not an old one)

---

**Most likely issue:** Your token doesn't have `Durable Objects:Edit` permission, which is required for the Agents SDK deployment.

**Quickest fix:** Create a new token using the "Edit Cloudflare Workers" template + add Durable Objects, D1, and Workers AI permissions.
