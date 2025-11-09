#!/bin/bash
# Deploy the new workers using Cloudflare API
# This script will deploy workers that don't exist yet

set -e

echo "🚀 Deploying New Coinswarm Workers"
echo "===================================="

cd cloudflare-agents

# Array of new workers to deploy
declare -a NEW_WORKERS=(
    "wrangler-historical-collection-cron.toml"
    "wrangler-realtime-price-cron.toml"
    "wrangler-monitor.toml"
    "wrangler-technical-indicators.toml"
    "wrangler-collection-alerts.toml"
)

echo "Workers to deploy:"
for config in "${NEW_WORKERS[@]}"; do
    worker_name=$(grep "^name = " "$config" | cut -d'"' -f2)
    echo "  - $worker_name (from $config)"
done

echo ""
read -p "Deploy these workers? (y/n) " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled"
    exit 0
fi

echo ""
echo "Deploying workers..."
echo ""

for config in "${NEW_WORKERS[@]}"; do
    worker_name=$(grep "^name = " "$config" | cut -d'"' -f2)
    echo "📦 Deploying $worker_name..."

    if npx wrangler deploy --config "$config"; then
        echo "✅ $worker_name deployed successfully"
    else
        echo "❌ Failed to deploy $worker_name"
        echo "   Check logs above for errors"
    fi

    echo ""
done

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "Test the workers:"
echo "  ./test-workers.sh"
echo ""
echo "Or visit the dashboard:"
echo "  https://coinswarm-data-monitor.bamn86.workers.dev/"
