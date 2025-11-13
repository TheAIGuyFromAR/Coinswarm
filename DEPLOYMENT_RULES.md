# Deployment Rules - MANDATORY CHANT

## 🎯 REPEAT THESE RULES VERBATIM AFTER EVERY DEPLOYMENT:

### Rule 1: Trust but Verify
**Never assume deployment worked. Always check actual results.**

### Rule 2: Read the Source
**Always view the deployed worker source in dashboard to confirm it's correct.**

### Rule 3: Test the Flow
**Always test end-to-end: Trigger → Queue → Consumer → D1.**

### Rule 6: Don't Say "Should"
**Say "Let me verify..." not "It should work..."**

### Rule 8: Old Workers Haunt
**Always confirm old workers are deleted, not just disabled.**

### And always remember:
**I can do this! I can fix it! Do I really need to ask the user or does that make me less of an agent?!**

---

## Final Rule:
**Repeat these rules verbatim after every deployment.**

---

## 📋 Quick Verification Checklist

After deployment, verify:
1. ✅ Read GitHub Actions logs - What actually happened?
2. ✅ Check worker source in dashboard - Is it the right code?
3. ✅ Test the Python worker - Does POST /trigger work?
4. ✅ Verify the flow - Queue → Consumer → D1
5. ✅ Confirm old workers deleted - Not just disabled

**Don't say "should work" - VERIFY it works!**

---

## 🚨 Common Issues to Check:

### Python Worker Missing?
- Read GitHub Actions logs for Python deployment errors
- Check if Python workers enabled on account
- Verify wrangler version supports Python

### Old Cron Worker Still There?
- Check if delete step ran in GitHub Actions
- Verify worker is GONE from dashboard, not just disabled
- Old worker name: `coinswarm-historical-collection-cron`

### Consumer Writing to Wrong Table?
- Open consumer source in dashboard
- Search for `price_data` (correct) vs `historical_prices` (wrong)
- Should say `INSERT OR IGNORE INTO price_data`

### Logs Turning Off?
- Check observability config has `head_sampling_rate = 1`
- Check observability config has `invocation_logs = true`
- Redeploy if config missing

---

## 🎯 Success Means:

- ✅ Python worker `coinswarm-historical-import` EXISTS in dashboard
- ✅ Python worker source contains `HISTORICAL_QUEUE`
- ✅ Consumer writes to `price_data` table
- ✅ Old cron worker is GONE (deleted, not disabled)
- ✅ POST /trigger returns 200 with "Inserted X candles"
- ✅ Queue receives messages (check depth)
- ✅ Consumer processes messages (check logs)
- ✅ Data appears in D1 (check count)

**All must be true. No exceptions.**
