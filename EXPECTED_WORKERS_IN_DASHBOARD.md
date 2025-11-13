# Expected Workers in Cloudflare Dashboard

## ✅ SHOULD BE DEPLOYED (Queue System):

### 1. `historical-data-queue-consumer`
- **Source:** TypeScript (`cloudflare-agents/historical-data-queue-consumer.ts`)
- **Purpose:** Processes queue messages → Writes to D1 `price_data` table
- **Trigger:** Queue messages (automatic)
- **Status:** ✅ Active

### 2. `historical-data-queue-producer`
- **Source:** TypeScript (`cloudflare-agents/historical-data-queue-producer.ts`)
- **Purpose:** Fetches from 3 APIs → Sends to queue
- **Trigger:** Cron (every 30 minutes)
- **Status:** ✅ Active

### 3. `coinswarm-historical-import`
- **Source:** Python (`pyswarm/Data_Import/historical_worker.py`)
- **Purpose:** Fetches from CryptoCompare → Sends to queue
- **Trigger:** Manual POST /trigger
- **Status:** ⚠️ Should be deployed (may be missing)

---

## ❌ SHOULD BE DELETED:

### 4. `coinswarm-historical-collection-cron`
- **Source:** TypeScript (`cloudflare-agents/historical-data-collection-cron.ts`)
- **Purpose:** OLD direct D1 writes (replaced by queue system)
- **Trigger:** Cron (DISABLED in config)
- **Status:** ❌ Should be deleted
- **Note:** Cron trigger disabled, but worker still deployed

**Why you see "var var var":** This is TypeScript source, but when deployed to Cloudflare, it gets transpiled to JavaScript. The transpiler outputs old-style `var` declarations, which is what you see in the dashboard code viewer.

---

## 🔧 How to Fix Dashboard:

The next GitHub Actions deployment will automatically:

1. ✅ Deploy Python worker `coinswarm-historical-import`
2. ✅ Deploy/update queue workers (consumer + producer)
3. ✅ **DELETE** `coinswarm-historical-collection-cron`

**After deployment, your dashboard should show:**
- `historical-data-queue-consumer` (TypeScript)
- `historical-data-queue-producer` (TypeScript)
- `coinswarm-historical-import` (Python)
- ~~`coinswarm-historical-collection-cron`~~ (deleted)

---

## Manual Fix (If Needed):

If GitHub Actions fails to delete the old worker, run manually:

```bash
# Login to Cloudflare
wrangler login

# Delete old cron worker
wrangler delete coinswarm-historical-collection-cron --force

# Deploy Python worker
cd pyswarm
wrangler deploy --config wrangler_historical_import.toml
```

---

## Other Historical Workers (Different Purposes):

### `historical-data-worker`
- **Purpose:** KV caching (NOT D1 writes)
- **Status:** Different use case, keep this one

---

## Summary:

**You currently see:** 4 workers (2 queue + 1 old cron + maybe 1 other)
**You should see:** 3 workers (2 queue + 1 Python)

**The old cron worker (`coinswarm-historical-collection-cron`) is the one you want to get rid of!**

Next deployment will clean this up automatically. ✅
