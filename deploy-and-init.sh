#!/bin/bash
# Manual Deployment and Initialization Script
# Use this if GitHub Actions deployment is slow

set -e

echo "========================================="
echo "Historical Data Collection - Manual Setup"
echo "========================================="
echo ""

# Check if wrangler is available
if ! command -v wrangler &> /dev/null; then
    echo "❌ Wrangler CLI not found. Installing..."
    npm install -g wrangler
fi

echo "✅ Wrangler CLI available"
echo ""

# Navigate to cloudflare-agents directory
cd /home/user/Coinswarm/cloudflare-agents || exit 1

echo "Step 1: Deploying Historical Collection Cron Worker..."
wrangler deploy --config wrangler-historical-collection-cron.toml

echo ""
echo "✅ Deployment complete"
echo ""

# Wait for deployment to propagate
echo "Waiting 10 seconds for deployment to propagate..."
sleep 10

echo ""
echo "Step 2: Initializing database..."
response=$(curl -s -X POST "https://coinswarm-historical-collection-cron.bamn86.workers.dev/init")

echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"

echo ""
echo "Step 3: Verifying initialization..."
sleep 3

status=$(curl -s "https://coinswarm-historical-collection-cron.bamn86.workers.dev/status")
tokens_count=$(echo "$status" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d['tokens']))" 2>/dev/null || echo "0")

echo "Tokens in database: $tokens_count / 15"

if [ "$tokens_count" = "15" ]; then
    echo ""
    echo "========================================="
    echo "✅ SUCCESS! Database initialized"
    echo "========================================="
    echo ""
    echo "Next steps:"
    echo "1. Wait for next hourly cron trigger (runs at :00)"
    echo "2. Data collection will start automatically"
    echo "3. Check progress: curl https://coinswarm-historical-collection-cron.bamn86.workers.dev/status"
    echo ""
    echo "Expected timeline:"
    echo "- Hourly/Daily data: 24-48 hours"
    echo "- Minute data: ~97 days"
    echo ""
else
    echo ""
    echo "========================================="
    echo "⚠️  Initialization may not be complete"
    echo "========================================="
    echo ""
    echo "Tokens found: $tokens_count"
    echo "Expected: 15"
    echo ""
    echo "Try running the init command manually:"
    echo "curl -X POST https://coinswarm-historical-collection-cron.bamn86.workers.dev/init"
fi
