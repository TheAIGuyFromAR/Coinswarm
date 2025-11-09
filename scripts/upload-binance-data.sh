#!/bin/bash
# Upload Binance Historical Data to Cloudflare D1
#
# This script fetches historical candles from Binance API (runs locally, not blocked)
# and uploads them to the Cloudflare Worker's price_data table
#
# Usage:
#   ./upload-binance-data.sh BTCUSDT 5m 1000
#   ./upload-binance-data.sh ETHUSDT 5m 1000
#   ./upload-binance-data.sh SOLUSDT 5m 1000

SYMBOL=${1:-BTCUSDT}
INTERVAL=${2:-5m}
LIMIT=${3:-1000}

WORKER_URL="https://coinswarm-evolution-agent.bamn86.workers.dev/upload-candles"

echo "📊 Fetching $LIMIT candles for $SYMBOL ($INTERVAL interval)..."

# Fetch from Binance (your local IP won't be blocked)
CANDLES=$(curl -s "https://api.binance.com/api/v3/klines?symbol=$SYMBOL&interval=$INTERVAL&limit=$LIMIT")

if [ $? -ne 0 ] || [ -z "$CANDLES" ]; then
  echo "❌ Failed to fetch from Binance"
  exit 1
fi

# Check if response is valid JSON
if ! echo "$CANDLES" | jq empty 2>/dev/null; then
  echo "❌ Invalid JSON response from Binance:"
  echo "$CANDLES"
  exit 1
fi

# Transform Binance format to our format
TRANSFORMED=$(echo "$CANDLES" | jq '[.[] | {
  timestamp: .[0],
  open: (.[1] | tonumber),
  high: (.[2] | tonumber),
  low: (.[3] | tonumber),
  close: (.[4] | tonumber),
  volume: (.[5] | tonumber)
}]')

CANDLE_COUNT=$(echo "$TRANSFORMED" | jq 'length')
echo "✓ Fetched $CANDLE_COUNT candles from Binance"

# Upload to worker
echo "📤 Uploading to Cloudflare D1..."

PAYLOAD=$(jq -n \
  --arg symbol "$SYMBOL" \
  --arg interval "$INTERVAL" \
  --argjson candles "$TRANSFORMED" \
  '{symbol: $symbol, interval: $interval, candles: $candles}')

RESPONSE=$(curl -s -X POST "$WORKER_URL" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

echo "$RESPONSE" | jq .

if echo "$RESPONSE" | jq -e '.success' > /dev/null 2>&1; then
  INSERTED=$(echo "$RESPONSE" | jq -r '.candlesInserted')
  echo "✅ Successfully uploaded $INSERTED candles for $SYMBOL"
else
  echo "❌ Upload failed:"
  echo "$RESPONSE" | jq .
  exit 1
fi
