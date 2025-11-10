# Cloudflare Workers: Enumerating All Live Workers

## Problem
The Wrangler CLI does not provide a direct command to list all Workers in your Cloudflare account. Only deployments for a specific Worker (via its config) can be listed. However, your environment contains many more Workers than are currently documented or managed via local configs.

## Solution: Use the Cloudflare REST API

You can enumerate all Workers in your account using the Cloudflare REST API:

- **Endpoint:** `GET /accounts/:account_id/workers/scripts`
- **Docs:** https://api.cloudflare.com/#worker-scripts-list-worker-scripts

### Example: Python Script to List All Workers

```python
import os
import requests

ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN")

url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/workers/scripts"
headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

resp = requests.get(url, headers=headers)
for script in resp.json().get('result', []):
    print(f"Name: {script['id']}, Last Modified: {script['modified_on']}, Size: {script['size']} bytes")
```

- This will print all live Workers, regardless of local config.
- You can then use `wrangler deployments list --name <worker>` for each to inspect deployments.

## Why This Matters
- **Architecture Alignment:** Many Workers may be live but not tracked in your repo or deployment workflow.
- **Security:** Orphaned or legacy Workers may have access to secrets or data.
- **Governance:** Full inventory is required for compliance and operational safety.

## Next Steps
1. Run the above script to enumerate all Workers.
2. For each Worker:
   - Document its purpose, config, and deployment state.
   - Compare to the intended architecture in `docs/architecture`.
   - Remove or update any legacy/orphaned Workers.
3. Update `docs/development/workers-deployment-vs-architecture.md` with the full inventory and status.

## References
- https://api.cloudflare.com/#worker-scripts-list-worker-scripts
- https://developers.cloudflare.com/workers/wrangler/commands/

_Last updated: 2025-11-10_
