# API Keys to Set in Cloudflare Workers

## CoinGecko API Key
**Key:** `CG-rLjqR8jToo9ELnAAsWnvyGQL`

**Set this key in the following workers:**
1. `coinswarm-historical-collection-cron`
2. `coinswarm-realtime-price-cron`

**Secret name:** `COINGECKO`

## CryptoCompare API Key
**Key:** [WAITING - please provide]

**Set this key in the following workers:**
1. `coinswarm-historical-collection-cron`
2. `coinswarm-realtime-price-cron`

**Secret name:** `CRYPTOCOMPARE_API_KEY`

---

## How to Set Secrets via Cloudflare Dashboard

1. Go to: https://dash.cloudflare.com/8a330fc6c339f031a73905d4ca2f3e5d/workers
2. Click on worker name (e.g., `coinswarm-historical-collection-cron`)
3. Go to **Settings** → **Variables and Secrets**
4. Click **Add variable** → Choose **Encrypt**
5. Enter variable name and value
6. Click **Deploy** to apply changes
7. Repeat for the second worker

## Alternative: Set via CLI

```bash
# Historical collection worker
echo "CG-rLjqR8jToo9ELnAAsWnvyGQL" | wrangler secret put COINGECKO --name coinswarm-historical-collection-cron
echo "[CRYPTOCOMPARE_KEY_HERE]" | wrangler secret put CRYPTOCOMPARE_API_KEY --name coinswarm-historical-collection-cron

# Realtime collection worker
echo "CG-rLjqR8jToo9ELnAAsWnvyGQL" | wrangler secret put COINGECKO --name coinswarm-realtime-price-cron
echo "[CRYPTOCOMPARE_KEY_HERE]" | wrangler secret put CRYPTOCOMPARE_API_KEY --name coinswarm-realtime-price-cron
```

---

**Status:** Once both keys are set in both workers, data collection will start automatically on the next cron run.
