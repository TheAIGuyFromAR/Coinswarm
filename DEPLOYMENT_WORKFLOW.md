# Complete Deployment Workflow

## 🔄 THE CORRECT DEPLOYMENT SEQUENCE:

### Phase 1: PRE-DEPLOYMENT CHECK ✅ (Before pushing)
### Phase 2: DEPLOY 🚀 (Push to trigger GitHub Actions)
### Phase 3: VERIFY 🔍 (Check what actually deployed)
### Phase 4: POST-DEPLOYMENT REPORT 📊 (Document results)
### Phase 5: POST-DEPLOYMENT FIXES 🔧 (Fix any issues)

---

## Phase 1: PRE-DEPLOYMENT CHECK ✅

**BEFORE pushing to GitHub, verify locally:**

### Rule 1: Trust but Verify
**Never assume files are correct. Always check actual contents.**

### Rule 2: Read the Source
**Always read the actual files that will be deployed.**

### Rule 3: Test the Flow
**Trace through the code logic: Does it make sense?**

### Rule 6: Don't Say "Should"
**Say "I verified..." not "It should work..."**

### Rule 8: Old Workers Haunt
**Check configs to ensure old workers are disabled/deleted.**

### And always remember:
**I can do this! I can fix it! Do I really need to ask the user or does that make me less of an agent?!**

---

### PRE-DEPLOYMENT CHECKLIST:

#### 1. Read Python Worker Source
```bash
cat pyswarm/Data_Import/historical_worker.py
```

**Verify:**
- [ ] Uses `HISTORICAL_QUEUE` (not direct D1 writes)
- [ ] Has `sendBatch()` method
- [ ] Batches data properly (10 per message)
- [ ] Has POST /trigger endpoint
- [ ] Comment says "Queue candles for batch processing"

#### 2. Read Python Worker Config
```bash
cat pyswarm/wrangler_historical_import.toml
```

**Verify:**
- [ ] Database ID: `ac4629b2-8240-4378-b3e3-e5262cd9b285` (not placeholder)
- [ ] Queue binding: `HISTORICAL_QUEUE` present
- [ ] Observability enabled: `true`
- [ ] Worker name: `coinswarm-historical-import`

#### 3. Read Consumer Source
```bash
cat cloudflare-agents/historical-data-queue-consumer.ts
```

**Verify:**
- [ ] Writes to `price_data` table (NOT `historical_prices`)
- [ ] Uses `INSERT OR IGNORE`
- [ ] Has `timeframe`, `volumeFrom`, `volumeTo` columns
- [ ] Handles array messages

#### 4. Read Consumer Config
```bash
cat cloudflare-agents/wrangler-historical-queue-consumer.toml
```

**Verify:**
- [ ] Database ID: correct
- [ ] max_batch_size: 100
- [ ] max_concurrency: 5
- [ ] Observability enabled

#### 5. Read Producer Config
```bash
cat cloudflare-agents/wrangler-historical-queue-producer.toml
```

**Verify:**
- [ ] Cron: `*/30 * * * *` (every 30 minutes)
- [ ] Queue binding: `HISTORICAL_DATA_QUEUE`
- [ ] Observability enabled

#### 6. Read Old Cron Worker Config
```bash
cat cloudflare-agents/wrangler-historical-collection-cron.toml
```

**Verify:**
- [ ] Cron trigger: COMMENTED OUT
- [ ] Deprecation notice: PRESENT

#### 7. Read GitHub Actions Workflow
```bash
grep -A20 "Deploy Python Historical Worker" .github/workflows/deploy-cloudflare-workers.yml
```

**Verify:**
- [ ] Python worker deployment step exists
- [ ] Triggers on queue worker changes
- [ ] continue-on-error: false (will fail if deployment fails)
- [ ] Delete old cron worker step exists

#### 8. Run Pre-Deployment Script
```bash
./verify-logs-config.sh
```

**Verify:**
- [ ] All configs have observability sections
- [ ] All configs have correct database IDs
- [ ] All configs have queue bindings

---

### PRE-DEPLOYMENT REPORT:

**Say this BEFORE pushing:**

```
PRE-DEPLOYMENT CHECK COMPLETE:

✅ Python worker source: Uses HISTORICAL_QUEUE, batches data
✅ Python worker config: Database ID correct, queue binding present
✅ Consumer source: Writes to price_data, handles arrays
✅ Consumer config: Batch size 100, concurrency 5
✅ Producer config: 30-min cron, observability enabled
✅ Old cron config: Disabled (cron commented out)
✅ GitHub Actions: Python deployment and delete steps present

All pre-deployment checks passed. Ready to deploy.
```

**If ANY check fails, FIX IT before pushing!**

---

## Phase 2: DEPLOY 🚀

**Push to GitHub to trigger deployment:**

```bash
git push
```

**Monitor deployment:**
- Watch GitHub Actions: https://github.com/TheAIGuyFromAR/Coinswarm/actions
- Wait for workflow to complete
- Check for green checkmark ✅ or red X ❌

---

## Phase 3: VERIFY 🔍

**AFTER deployment completes, verify what actually happened:**

### Rule 1: Trust but Verify
**GitHub Actions says "success" - but did it REALLY deploy correctly?**

### Rule 2: Read the Source
**Check the actual deployed worker code in Cloudflare dashboard.**

### Rule 3: Test the Flow
**Trigger → Queue → Consumer → D1 - does it work end-to-end?**

### Rule 6: Don't Say "Should"
**Don't assume - TEST and VERIFY.**

### Rule 8: Old Workers Haunt
**Is the old worker actually GONE (not just disabled)?**

### And always remember:
**I can do this! I can fix it! Do I really need to ask the user or does that make me less of an agent?!**

---

### VERIFICATION CHECKLIST:

#### 1. Read GitHub Actions Logs

**Check these specific sections:**

```
Look for:
- "Deploy Python Historical Worker" - Success or Fail?
- "Deploy Historical Data Queue Consumer" - Success?
- "Deploy Historical Data Queue Producer" - Success?
- "Delete Old Historical Cron Worker" - Did it run?
- "Verify Queue System Deployment" - What were results?
```

**Red flags:**
- ❌ "Error: Python workers not enabled"
- ❌ "Error: Queue not found"
- ❌ "Skip: No changes detected" (when there should be changes)

#### 2. Check Cloudflare Dashboard

**Go to:** https://dash.cloudflare.com → Workers & Pages

**Workers that SHOULD exist:**
- [ ] `coinswarm-historical-import` (Python)
- [ ] `historical-data-queue-consumer` (TypeScript)
- [ ] `historical-data-queue-producer` (TypeScript)

**Workers that should NOT exist:**
- [ ] `coinswarm-historical-collection-cron` (should be deleted)

#### 3. Read Deployed Worker Source in Dashboard

**For Python worker:**
- [ ] Click `coinswarm-historical-import` → View Source
- [ ] Search for `HISTORICAL_QUEUE` - must be present
- [ ] Search for `sendBatch` - must be present
- [ ] Should NOT have direct D1 INSERT in main flow

**For Consumer:**
- [ ] Click `historical-data-queue-consumer` → View Source
- [ ] Search for `price_data` - must write to this table
- [ ] Search for `historical_prices` - must NOT be present
- [ ] Should say `INSERT OR IGNORE INTO price_data`

#### 4. Check Logs Status

**For each worker:**
- [ ] Consumer: Logs tab → Toggle ON and STAYS ON after refresh
- [ ] Producer: Logs tab → Toggle ON and STAYS ON after refresh
- [ ] Python: Logs tab → Toggle ON and STAYS ON after refresh

#### 5. Test Python Worker

```bash
curl -X POST https://coinswarm-historical-import.<subdomain>.workers.dev/trigger
```

**Expected:**
```json
{
  "inserted": 2000,
  "message": "Inserted 2000 BTC-USDC daily candles"
}
```

**NOT expected:**
- ❌ 404 Not Found (worker doesn't exist)
- ❌ 500 Error (worker crashed)
- ❌ Timeout (worker hanging)

#### 6. Check Queue Flow

```bash
# Immediately after triggering Python worker
wrangler queues consumer historical-data-queue
```

**Expected:**
- Messages: 200 (or declining as consumer processes)
- Consumer: historical-data-queue-consumer attached

#### 7. Watch Consumer Logs

```bash
wrangler tail historical-data-queue-consumer --format pretty
```

**Expected:**
- "Processing batch of X data points"
- "Inserted X rows in Xms"
- NO errors

#### 8. Verify Data in D1

```bash
wrangler d1 execute ac4629b2-8240-4378-b3e3-e5262cd9b285 \
  --command "SELECT COUNT(*) FROM price_data WHERE source='cryptocompare'" \
  --remote
```

**Expected:** Count increases after test

---

## Phase 4: POST-DEPLOYMENT REPORT 📊

**Document what actually happened:**

```
POST-DEPLOYMENT REPORT:

Date: [date]
Commit: [commit hash]
GitHub Actions: [SUCCESS/FAILED]

Workers Deployed:
✅/❌ coinswarm-historical-import (Python) - [PRESENT/MISSING]
✅/❌ historical-data-queue-consumer (TS) - [PRESENT/MISSING]
✅/❌ historical-data-queue-producer (TS) - [PRESENT/MISSING]

Old Workers:
✅/❌ coinswarm-historical-collection-cron - [DELETED/STILL PRESENT]

Worker Source Verification:
✅/❌ Python worker uses HISTORICAL_QUEUE - [YES/NO]
✅/❌ Consumer writes to price_data - [YES/NO]

Logs Status:
✅/❌ Toggles stay ON after refresh - [YES/NO]

Testing:
✅/❌ POST /trigger response - [200 OK / ERROR]
✅/❌ Queue received messages - [YES/NO - count]
✅/❌ Consumer processed messages - [YES/NO]
✅/❌ Data reached D1 - [YES/NO - count]

OVERALL STATUS: [VERIFIED WORKING / NEEDS FIXES]

Issues Found:
[List any issues discovered]
```

---

## Phase 5: POST-DEPLOYMENT FIXES 🔧

**If ANY verification failed, fix it immediately:**

### Issue: Python Worker Missing

**Cause:** Python workers not enabled OR deployment failed

**Fix:**
```bash
# Check GitHub Actions logs for error
# If Python not enabled, contact Cloudflare support
# If deployment error, check the specific error message
```

### Issue: Old Cron Worker Still Present

**Cause:** Delete step failed OR didn't run

**Fix:**
```bash
wrangler delete coinswarm-historical-collection-cron --force
```

### Issue: Consumer Writing to Wrong Table

**Cause:** Wrong version deployed OR edit didn't save

**Fix:**
```bash
# Verify local file is correct
cat cloudflare-agents/historical-data-queue-consumer.ts | grep "price_data"

# If local is correct, redeploy
cd cloudflare-agents
wrangler deploy --config wrangler-historical-queue-consumer.toml
```

### Issue: Logs Turn Off After Deployment

**Cause:** Observability config missing OR not applied

**Fix:**
```bash
# Verify configs have observability
grep -A5 "\[observability\]" cloudflare-agents/wrangler-historical-queue-consumer.toml

# If missing, add and redeploy
# If present, check if head_sampling_rate = 1 is there
```

### Issue: No Data in D1

**Cause:** Queue not processing OR consumer not writing

**Fix:**
```bash
# Check queue depth
wrangler queues consumer historical-data-queue

# If messages stuck, check consumer logs for errors
wrangler tail historical-data-queue-consumer --format pretty

# If consumer erroring, check the error message
# Common: "table not found" = schema not applied
# Common: "database locked" = too many concurrent writes
```

---

## 🎯 SUCCESS CRITERIA:

**Deployment is ONLY successful when ALL are true:**

- [x] GitHub Actions passed (green checkmark)
- [x] Python worker exists in dashboard
- [x] Python worker source uses HISTORICAL_QUEUE
- [x] Consumer source writes to price_data
- [x] Old cron worker is GONE (not just disabled)
- [x] Logs toggles stay ON in dashboard
- [x] POST /trigger returns 200 with "Inserted X candles"
- [x] Queue receives messages (check depth)
- [x] Consumer processes messages (check logs)
- [x] Data appears in D1 (check count)

**If ANY is false, deployment is NOT complete. Go to Phase 5: Fixes.**

---

## 📢 FINAL DEPLOYMENT CHANT:

**Recite after EVERY deployment:**

**Rule 1: Trust but Verify**
Never assume deployment worked. Always check actual results.

**Rule 2: Read the Source**
Always view the deployed worker source in dashboard to confirm it's correct.

**Rule 3: Test the Flow**
Always test end-to-end: Trigger → Queue → Consumer → D1.

**Rule 6: Don't Say "Should"**
Say "Let me verify..." not "It should work..."

**Rule 8: Old Workers Haunt**
Always confirm old workers are deleted, not just disabled.

**And always remember:**
I can do this! I can fix it! Do I really need to ask the user or does that make me less of an agent?!

**Final Rule:**
Repeat these rules verbatim after every deployment.
