# Post-Deployment Verification Checklist

## 📋 MUST DO AFTER EVERY DEPLOYMENT

### 1. ✅ Read the GitHub Actions Logs
**Before saying "deployment complete", ALWAYS:**

```bash
# Check the actual deployment logs
# Look for these specific sections:
```

- [ ] "Deploy Python Historical Worker" - Did it succeed or fail?
- [ ] "Deploy Historical Data Queue Consumer" - Did it succeed?
- [ ] "Deploy Historical Data Queue Producer" - Did it succeed?
- [ ] "Delete Old Historical Cron Worker" - Did it run?
- [ ] "Verify Queue System Deployment" - What were the results?

**RED FLAGS:**
- ❌ "Error: Python workers not enabled"
- ❌ "Error: Queue not found"
- ❌ "Error: Database not found"
- ❌ "Skip: No changes detected" (when there should be changes)

---

### 2. ✅ Verify Which Workers Are ACTUALLY Deployed

**Ask user to check Cloudflare Dashboard OR check GitHub Actions output:**

```
Dashboard: https://dash.cloudflare.com → Workers & Pages
```

**Expected workers:**
- [ ] `coinswarm-historical-import` (Python) - **MUST BE THERE**
- [ ] `historical-data-queue-consumer` (TypeScript)
- [ ] `historical-data-queue-producer` (TypeScript)

**Should NOT see:**
- [ ] `coinswarm-historical-collection-cron` (should be deleted)

**VERIFY BY READING:**
- [ ] Read the worker SOURCE in dashboard to confirm it's the right code
- [ ] Python worker should have `HISTORICAL_QUEUE` in code
- [ ] TypeScript consumer should write to `price_data` table
- [ ] Old cron worker should NOT exist

---

### 3. ✅ Read the Actual Deployed Worker Code

**CRITICAL: Don't assume - VERIFY:**

For Python worker `coinswarm-historical-import`:
- [ ] Open in dashboard → View source
- [ ] Search for `HISTORICAL_QUEUE` - MUST be present
- [ ] Search for `sendBatch` - MUST be present
- [ ] Should say "Queue candles for batch processing"

For TypeScript consumer:
- [ ] Open in dashboard → View source
- [ ] Search for `price_data` - MUST write to this table
- [ ] Search for `historical_prices` - MUST NOT be present
- [ ] Should say `INSERT OR IGNORE INTO price_data`

For TypeScript producer:
- [ ] Has cron trigger configured (30 minutes)
- [ ] Sends to `HISTORICAL_DATA_QUEUE`

---

### 4. ✅ Verify Logs Are Enabled

**In Cloudflare Dashboard for EACH worker:**

- [ ] Consumer: Logs tab → Toggle should be ON (and stay on)
- [ ] Producer: Logs tab → Toggle should be ON (and stay on)
- [ ] Python worker: Logs tab → Toggle should be ON (and stay on)

**If toggle turns OFF after deployment:**
- Config is missing `[observability]` section
- Need to add `head_sampling_rate = 1`
- Need to redeploy

---

### 5. ✅ Verify Queue Configuration

**Check GitHub Actions logs or wrangler output:**

```bash
wrangler queues consumer historical-data-queue
```

Expected:
- [ ] Queue exists: `historical-data-queue`
- [ ] Consumer attached: `historical-data-queue-consumer`
- [ ] max_batch_size: 100
- [ ] max_concurrency: 5
- [ ] dead_letter_queue: `historical-data-dlq`

---

### 6. ✅ Test the Python Worker

**After deployment, ALWAYS test:**

```bash
# Trigger Python worker
curl -X POST https://coinswarm-historical-import.<subdomain>.workers.dev/trigger
```

Expected response:
```json
{
  "inserted": 2000,
  "message": "Inserted 2000 BTC-USDC daily candles",
  "next_trigger": "POST /trigger with toTs=..."
}
```

- [ ] Response is 200 OK
- [ ] Message says "Inserted X candles"
- [ ] No error in response
- [ ] Check logs immediately after (should see activity)

---

### 7. ✅ Verify Data Flow End-to-End

**After triggering Python worker:**

1. [ ] **Queue receives messages:**
   ```bash
   wrangler queues consumer historical-data-queue
   # Should show: Messages: 200 (or declining number)
   ```

2. [ ] **Consumer processes messages:**
   ```bash
   wrangler tail historical-data-queue-consumer --format pretty
   # Should see: "Processing batch of X data points"
   # Should see: "Inserted X rows in Xms"
   ```

3. [ ] **Data reaches D1:**
   ```bash
   wrangler d1 execute <db-id> \
     --command "SELECT COUNT(*) FROM price_data WHERE source='cryptocompare'" \
     --remote
   # Should see increasing count
   ```

---

### 8. ✅ Check for Common Issues

**BEFORE saying "everything is deployed":**

- [ ] Python worker is NOT just the TypeScript one renamed
- [ ] Consumer is NOT writing to `historical_prices` table
- [ ] Old cron worker is NOT still running (check cron triggers)
- [ ] Logs are NOT disabled in dashboard
- [ ] Queue is NOT at 0 messages if you just triggered worker
- [ ] Error rate is NOT 100% in dashboard

---

## 🚨 RED FLAGS TO WATCH FOR

### If User Says:
- "I only see TypeScript workers" → Python deployment failed
- "Logs turn off after deployment" → Missing observability config
- "Old cron worker still there" → Delete step failed or didn't run
- "No data in D1" → Check queue depth, consumer logs, end-to-end flow
- "Worker has 'var var var'" → That's the OLD cron worker, should be deleted

---

## 📢 WHAT TO SAY AFTER DEPLOYMENT

### ❌ DON'T SAY:
- "Deployment complete!" (without checking)
- "Everything should be working!" (without verifying)
- "The Python worker is deployed!" (without confirming)
- "Logs are enabled!" (without checking dashboard)

### ✅ DO SAY:
- "Let me check the GitHub Actions logs to verify deployment..."
- "Can you confirm you see these 3 workers in your dashboard: [list]"
- "Let me verify the Python worker source in the dashboard..."
- "Let's test the Python worker endpoint to confirm it works..."
- "Can you check if logs stay enabled in the dashboard?"

---

## 🎯 DEPLOYMENT SUCCESS CRITERIA

**ALL must be true:**
- [x] GitHub Actions workflow passed (green checkmark)
- [x] Python worker `coinswarm-historical-import` exists in dashboard
- [x] Python worker source contains `HISTORICAL_QUEUE` (not direct D1 writes)
- [x] Consumer source writes to `price_data` table (not `historical_prices`)
- [x] Old cron worker `coinswarm-historical-collection-cron` is gone
- [x] Logs toggle stays ON in dashboard after deployment
- [x] Python worker responds to POST /trigger with 200 OK
- [x] Queue receives messages after trigger
- [x] Consumer processes messages (check logs)
- [x] Data appears in D1 (check row count)

**If ANY is false → Deployment is NOT complete!**

---

## 📝 CHANT AFTER DEPLOYMENT

**ALWAYS say this after deployment:**

```
✅ Deployment Verification:

1. GitHub Actions Status: [CHECK LOGS]
2. Workers in Dashboard: [ASK USER TO CONFIRM]
   - coinswarm-historical-import (Python) - [PRESENT/MISSING]
   - historical-data-queue-consumer (TS) - [PRESENT/MISSING]
   - historical-data-queue-producer (TS) - [PRESENT/MISSING]
   - coinswarm-historical-collection-cron - [DELETED/STILL THERE]

3. Worker Source Code: [VERIFY IN DASHBOARD]
   - Python worker uses HISTORICAL_QUEUE - [YES/NO]
   - Consumer writes to price_data table - [YES/NO]

4. Logs Status: [CHECK DASHBOARD]
   - Toggle stays ON after deployment - [YES/NO]

5. Test Results:
   - POST /trigger response: [200 OK / ERROR]
   - Queue depth after trigger: [X messages]
   - Consumer processing: [YES/NO - check logs]
   - Data in D1: [YES/NO - check count]

6. Overall Status: [VERIFIED WORKING / NEEDS FIXES]
```

**DO NOT skip any of these checks!**

---

## 💡 SUGGESTIONS FOR RULES

### Rule 1: "Trust but Verify"
**Never assume deployment worked. Always check actual results.**

### Rule 2: "Read the Source"
**Always view the deployed worker source in dashboard to confirm it's correct.**

### Rule 3: "Test the Flow"
**Always test end-to-end: Trigger → Queue → Consumer → D1.**

### Rule 4: "Check the Logs"
**Always verify GitHub Actions logs, worker logs, and dashboard logs.**

### Rule 5: "Ask the User"
**Always ask user to confirm what they see in dashboard - don't guess.**

### Rule 6: "Don't Say 'Should'"
**Say "Let me verify..." not "It should work..."**

### Rule 7: "Python is Special"
**Python workers often fail silently - ALWAYS verify deployment.**

### Rule 8: "Old Workers Haunt"
**Always confirm old workers are deleted, not just disabled.**

### Rule 9: "Logs Lie"
**Logs turning off means config is wrong, even if deployment "succeeded".**

### Rule 10: "One Source of Truth"
**The dashboard shows what's ACTUALLY deployed, not what SHOULD be deployed.**

---

## 🎬 EXAMPLE GOOD DEPLOYMENT VERIFICATION

```
Claude: "I see the GitHub Actions workflow completed. Let me verify what was actually deployed.

Looking at the logs:
- ✅ Python worker deployment step passed
- ✅ Queue consumer deployment passed
- ✅ Queue producer deployment passed
- ✅ Delete old worker step ran

However, I cannot verify what's actually in your Cloudflare dashboard from here.

Can you please check your dashboard and confirm:
1. Do you see 'coinswarm-historical-import' (Python worker)?
2. Is 'coinswarm-historical-collection-cron' gone?
3. Do the logs toggles stay ON?

Then let's test by running:
curl -X POST https://coinswarm-historical-import.<your>.workers.dev/trigger

And share the response so we can verify it's actually working."
```

**This is GOOD because:**
- ✅ Checks logs
- ✅ Acknowledges limitations (can't see dashboard)
- ✅ Asks user to verify
- ✅ Provides test command
- ✅ Wants to see results before declaring success

---

## 🔴 EXAMPLE BAD DEPLOYMENT VERIFICATION

```
Claude: "✅ Deployment complete! Your Python worker is now deployed and logs are enabled. The queue system should be working!"
```

**This is BAD because:**
- ❌ Didn't check logs
- ❌ Didn't verify dashboard
- ❌ Didn't test anything
- ❌ Used "should" instead of "verified"
- ❌ Made assumptions

---

## 🎯 FINAL RULE

**"If I can't verify it directly, I must ask the user to verify and share results."**

Never declare success without evidence!
