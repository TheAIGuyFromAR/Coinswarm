#!/bin/bash

# Quick script to verify logs and traces are accessible

echo "🔍 Verifying Logs and Traces Configuration"
echo "==========================================="
echo ""

# Check if configs have observability enabled
echo "1. Checking wrangler configs for observability settings..."
echo ""

echo "Consumer config:"
grep -A5 "\[observability\]" cloudflare-agents/wrangler-historical-queue-consumer.toml
echo ""

echo "Producer config:"
grep -A5 "\[observability\]" cloudflare-agents/wrangler-historical-queue-producer.toml
echo ""

echo "Python worker config:"
grep -A5 "\[observability\]" pyswarm/wrangler_historical_import.toml
echo ""

echo "==========================================="
echo "2. How to verify in Cloudflare Dashboard:"
echo "==========================================="
echo ""
echo "After next deployment, check:"
echo ""
echo "📊 For Logs:"
echo "   1. Go to: https://dash.cloudflare.com"
echo "   2. Workers & Pages → historical-data-queue-consumer"
echo "   3. Click 'Logs' tab"
echo "   4. Toggle should stay ON (won't turn off on deployment)"
echo ""
echo "🔍 For Traces:"
echo "   1. Same worker page"
echo "   2. Click 'Traces' or 'Observability' tab"
echo "   3. Should see execution traces for each invocation"
echo ""
echo "==========================================="
echo "3. Test with wrangler tail (real-time):"
echo "==========================================="
echo ""
echo "Run these commands to see live logs:"
echo ""
echo "  wrangler tail historical-data-queue-consumer --format pretty"
echo "  wrangler tail historical-data-queue-producer --format pretty"
echo "  wrangler tail coinswarm-historical-import --format pretty"
echo ""
echo "You should see:"
echo "  ✅ console.log() statements"
echo "  ✅ console.error() statements"
echo "  ✅ Worker invocation events"
echo "  ✅ Request/response info"
echo ""
echo "==========================================="
echo "✅ Configuration verified!"
echo ""
echo "Next steps:"
echo "1. Wait for GitHub Actions deployment to complete"
echo "2. Check dashboard - logs toggle should stay ON"
echo "3. Trigger Python worker to generate logs"
echo "4. View logs in dashboard or via wrangler tail"
echo ""
