#!/bin/bash
#
# Quick deployment script for multi-source Cloudflare Worker
# Fixes the 30-day historical data limitation
#

set -e  # Exit on error

echo "=========================================="
echo "Cloudflare Worker Deployment Script"
echo "=========================================="
echo ""

# Check if wrangler is installed
if ! command -v wrangler &> /dev/null; then
    echo "❌ Wrangler CLI not found"
    echo "Installing wrangler..."
    npm install -g wrangler
fi

echo "✅ Wrangler CLI found"
echo ""

# Check authentication
echo "Checking Cloudflare authentication..."
if ! wrangler whoami &> /dev/null; then
    echo "⚠️  Not authenticated with Cloudflare"
    echo ""
    echo "Please choose authentication method:"
    echo "  1. Interactive login (opens browser)"
    echo "  2. Use API token"
    echo ""
    read -p "Choice (1 or 2): " auth_choice

    if [ "$auth_choice" == "1" ]; then
        wrangler login
    elif [ "$auth_choice" == "2" ]; then
        read -p "Enter your Cloudflare API token: " api_token
        export CLOUDFLARE_API_TOKEN="$api_token"
    else
        echo "❌ Invalid choice"
        exit 1
    fi
fi

echo "✅ Authenticated with Cloudflare"
wrangler whoami
echo ""

# Change to worker directory
cd /home/user/Coinswarm/cloudflare-workers

echo "=========================================="
echo "Deploying Multi-Source Worker"
echo "=========================================="
echo ""
echo "This worker will support:"
echo "  • 2+ years of historical data"
echo "  • CryptoCompare + CoinGecko sources"
echo "  • /multi-price endpoint"
echo ""

# Deploy
echo "Deploying..."
wrangler deploy --config wrangler-multi-source.toml

echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""

# Get the deployed URL
echo "Testing deployment..."
WORKER_URL=$(wrangler deployments list --config wrangler-multi-source.toml 2>/dev/null | grep -oP 'https://[^ ]+' | head -1)

if [ -z "$WORKER_URL" ]; then
    echo "⚠️  Could not automatically detect worker URL"
    echo "Please check: wrangler deployments list"
else
    echo "Worker URL: $WORKER_URL"
    echo ""

    # Test basic endpoint
    echo "Testing root endpoint..."
    curl -s "$WORKER_URL/" | jq '.' || echo "Could not parse JSON response"

    echo ""
    echo "Testing /multi-price endpoint with 6 months (P0 requirement)..."

    # Test P0 requirement
    RESPONSE=$(curl -s "${WORKER_URL}/multi-price?symbol=BTC&days=180")
    DATA_POINTS=$(echo "$RESPONSE" | jq -r '.dataPoints // 0')

    if [ "$DATA_POINTS" -gt 4000 ]; then
        echo "✅ P0 REQUIREMENT MET!"
        echo "   Fetched: $DATA_POINTS candles"
        echo "$RESPONSE" | jq '{dataPoints, first, last, priceChange, sources: .providersUsed}'
    else
        echo "⚠️  Unexpected result:"
        echo "   Data points: $DATA_POINTS (expected 4320+)"
        echo "$RESPONSE" | jq '.'
    fi
fi

echo ""
echo "=========================================="
echo "Next Steps"
echo "=========================================="
echo ""
echo "1. Update Python client with new worker URL:"
echo "   File: src/coinswarm/data_ingest/coinswarm_worker_client.py"
echo "   URL: $WORKER_URL"
echo ""
echo "2. Test with Python:"
echo "   python -m src.coinswarm.data_ingest.coinswarm_worker_client"
echo ""
echo "3. Run backtest with 6+ months data:"
echo "   python your_backtest_script.py"
echo ""
echo "=========================================="
