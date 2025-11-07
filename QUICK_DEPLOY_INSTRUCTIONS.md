# Quick Deploy Instructions - 2 Minutes

## Step 1: Copy the Worker Code

**File to copy:** `COPY_THIS_WORKER_CODE.js` (in this repo)

Or view it directly on GitHub:
https://github.com/TheAIGuyFromAR/Coinswarm/blob/claude/debug-cloudflare-historical-data-011CUqugUynEoovcsiVnoaPB/COPY_THIS_WORKER_CODE.js

## Step 2: Deploy to Cloudflare

1. Go to: https://dash.cloudflare.com/
2. Navigate to: **Workers & Pages** (left sidebar)
3. Click on your existing `coinswarm` worker
4. Click: **Quick Edit** button (top right)
5. **Select All** (Ctrl+A) and **Delete**
6. **Paste** the code from `COPY_THIS_WORKER_CODE.js`
7. Click: **Save and Deploy**

## Step 3: Test It

```bash
curl "https://coinswarm.bamn86.workers.dev/multi-price?symbol=BTC&days=180" | jq '.dataPoints'
```

**Expected:** `4320` (or more)

**Success:** ✅ P0 requirement met (6+ months of data)!

---

## What This Fixes

**Before:**
- Max 30 days (721 candles)
- Only Kraken + Coinbase

**After:**
- Up to 2+ years (17,520 candles)
- CryptoCompare + CoinGecko + Kraken + Coinbase
- New `/multi-price` endpoint

---

## Alternative: Create New Worker

If you want a separate worker:

1. Workers & Pages → **Create Application** → **Create Worker**
2. Name: `coinswarm-multi-source`
3. Deploy → Quick Edit
4. Delete template → Paste code from `COPY_THIS_WORKER_CODE.js`
5. Save and Deploy
6. Note the new URL

---

**Total Time:** 2-3 minutes
