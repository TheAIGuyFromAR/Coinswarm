# Cloudflare Workers Platform: API & Wrangler Capabilities

## 1. Overview
This document provides a comprehensive summary of what you can access and control in the Cloudflare Workers platform using the REST API and Wrangler CLI, including deployment, configuration, storage, monitoring, and automation. It also includes a Python class for scripting these operations and usage documentation.

---

## 2. Platform Capabilities

### A. Worker Lifecycle Management
- Deploy new code (wrangler deploy, API)
- List, activate, rollback, and delete Worker scripts
- List and activate deployments/versions

### B. Configuration & Settings
- Edit environment variables and secrets (wrangler secret, API)
- Manage bindings: D1, KV, R2, Durable Objects, etc.
- Edit compatibility date, usage model, routes, triggers
- View and update scheduled events, HTTP routes, custom domains

### C. Database & Storage
- D1: Create, bind, migrate schema, run SQL, inspect data
- KV, R2, Durable Objects: Create, bind, interact

### D. Monitoring & Logs
- Fetch logs (wrangler tail, API)
- View metrics: usage, errors, invocations, CPU time

### E. Secrets & Security
- Manage API tokens
- Set per-Worker secrets

### F. Account & Project Management
- List accounts, zones, Workers
- Manage custom domains

---

## 3. Wrangler CLI vs REST API
- Wrangler CLI: High-level, user-friendly, covers most use cases
- REST API: Full control, advanced automation, integration

References:
- https://developers.cloudflare.com/workers/wrangler/commands/
- https://api.cloudflare.com/

---

## 4. Python Automation Class

Below is a Python class for automating Cloudflare Workers operations via Wrangler CLI and REST API. Requires `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` in environment.

```python
import os
import subprocess
import requests

class CloudflareWorkersManager:
    """
    Automates Cloudflare Workers operations via Wrangler CLI and REST API.
    Requires CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID in environment.
    """
    def __init__(self, account_id=None, api_token=None):
        self.account_id = account_id or os.environ.get("CLOUDFLARE_ACCOUNT_ID")
        self.api_token = api_token or os.environ.get("CLOUDFLARE_API_TOKEN")
        self.api_base = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}"

    # --- Wrangler CLI Wrappers ---

    def deploy_worker(self, wrangler_toml_path):
        """Deploys a Worker using wrangler CLI."""
        return subprocess.run([
            "npx", "wrangler", "deploy", "--config", wrangler_toml_path
        ], capture_output=True, text=True)

    def tail_logs(self, worker_name):
        """Tails logs for a Worker."""
        return subprocess.run([
            "npx", "wrangler", "tail", "--name", worker_name
        ], capture_output=True, text=True)

    def put_secret(self, worker_name, secret_name, secret_value):
        """Sets a secret for a Worker."""
        proc = subprocess.Popen([
            "npx", "wrangler", "secret", "put", secret_name, "--name", worker_name
        ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = proc.communicate(input=secret_value)
        return stdout, stderr

    # --- REST API Wrappers ---

    def list_workers(self):
        """Lists all Workers in the account."""
        url = f"{self.api_base}/workers/scripts"
        return requests.get(url, headers=self._headers()).json()

    def get_worker_details(self, worker_name):
        """Gets details for a specific Worker."""
        url = f"{self.api_base}/workers/scripts/{worker_name}"
        return requests.get(url, headers=self._headers()).json()

    def list_deployments(self, worker_name):
        """Lists deployments/versions for a Worker."""
        url = f"{self.api_base}/workers/scripts/{worker_name}/deployments"
        return requests.get(url, headers=self._headers()).json()

    def activate_deployment(self, worker_name, deployment_id):
        """Activates a specific deployment/version."""
        url = f"{self.api_base}/workers/scripts/{worker_name}/deployments/{deployment_id}/activate"
        return requests.post(url, headers=self._headers()).json()

    def delete_worker(self, worker_name):
        """Deletes a Worker."""
        url = f"{self.api_base}/workers/scripts/{worker_name}"
        return requests.delete(url, headers=self._headers()).json()

    def list_d1_databases(self):
        """Lists D1 databases in the account."""
        url = f"{self.api_base}/d1/database"
        return requests.get(url, headers=self._headers()).json()

    def run_d1_query(self, database_id, sql):
        """Runs a SQL query on a D1 database."""
        url = f"{self.api_base}/d1/database/{database_id}/query"
        return requests.post(url, headers=self._headers(), json={"sql": sql}).json()

    # --- Helpers ---

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
```

---

## 5. Usage Example

```python
cf = CloudflareWorkersManager()

# Deploy a worker
deploy_result = cf.deploy_worker("cloudflare-agents/wrangler-historical.toml")
print(deploy_result.stdout)

# List all workers
workers = cf.list_workers()
print(workers)

# Set a secret
cf.put_secret("historical-data-worker", "API_KEY", "supersecret")

# Run a D1 query
dbs = cf.list_d1_databases()
db_id = dbs['result'][0]['uuid']
cf.run_d1_query(db_id, "SELECT * FROM sqlite_master")
```

---

## 6. Best Practices
- Use API tokens with least privilege
- Never hardcode secrets; use environment variables
- Use Wrangler for most day-to-day tasks; REST API for automation
- Check Cloudflare’s API docs for new endpoints
- For CI/CD, prefer Wrangler CLI in GitHub Actions

---

## 7. References
- https://developers.cloudflare.com/workers/
- https://developers.cloudflare.com/workers/wrangler/commands/
- https://api.cloudflare.com/
<!-- Cleared: Content moved to Development_strategies.md -->
