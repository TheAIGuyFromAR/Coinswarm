#!/bin/bash

# Script to manually deploy Python worker and remove old cron worker

set -e

echo "🔧 Manual Deployment Fix Script"
echo "================================"
echo ""

# Check if authenticated
if ! wrangler whoami &> /dev/null; then
    echo "❌ Not authenticated to Cloudflare"
    echo "Run: wrangler login"
    exit 1
fi

echo "✅ Authenticated to Cloudflare"
echo ""

# Deploy Python worker
echo "1. Deploying Python Historical Worker..."
echo "   Working directory: pyswarm"
echo "   Config: wrangler_historical_import.toml"
echo ""

cd pyswarm
wrangler deploy --config wrangler_historical_import.toml
cd ..

echo ""
echo "✅ Python worker deployed!"
echo ""

# Delete old cron worker
echo "2. Deleting old cron worker (historical-collection-cron)..."
echo ""

read -p "Delete coinswarm-historical-collection-cron? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    wrangler delete coinswarm-historical-collection-cron --force || echo "Worker may not exist"
    echo "✅ Old cron worker deleted (or didn't exist)"
else
    echo "⏭️  Skipped deletion of old cron worker"
fi

echo ""
echo "================================"
echo "✅ Manual fixes complete!"
echo ""
echo "Check dashboard:"
echo "  https://dash.cloudflare.com"
echo ""
echo "You should now see:"
echo "  ✅ coinswarm-historical-import (Python)"
echo "  ✅ historical-data-queue-consumer (TS)"
echo "  ✅ historical-data-queue-producer (TS)"
echo "  ❌ coinswarm-historical-collection-cron (deleted)"
echo ""
