#!/bin/bash
# Monitor Cloudflare Worker Deployment Status

echo "========================================="
echo "Cloudflare Worker Deployment Monitor"
echo "========================================="
echo ""
echo "Push triggered at: $(date)"
echo "Expected deployment time: 5-10 minutes"
echo ""

check_deployment() {
    echo "[$1] Checking /init endpoint..."
    response=$(curl -s -X POST "https://coinswarm-historical-collection-cron.bamn86.workers.dev/init" 2>&1)

    if echo "$response" | grep -q "success"; then
        echo "✅ SUCCESS! /init endpoint is deployed!"
        echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
        return 0
    elif echo "$response" | grep -q "Multi-Timeframe"; then
        echo "⏳ Old version still running (returns default response)"
        return 1
    else
        echo "❌ Unexpected response:"
        echo "$response"
        return 2
    fi
}

# Check immediately
check_deployment "Initial check"
initial_result=$?

if [ $initial_result -eq 0 ]; then
    echo ""
    echo "✅ Deployment already complete!"
    exit 0
fi

echo ""
echo "Waiting for deployment to complete..."
echo "Will check every 30 seconds for 10 minutes"
echo ""

# Monitor for 10 minutes
for i in {1..20}; do
    sleep 30
    echo ""
    check_deployment "Check $i/20"

    if [ $? -eq 0 ]; then
        echo ""
        echo "========================================="
        echo "✅ DEPLOYMENT SUCCESSFUL!"
        echo "========================================="
        echo ""
        echo "Next step: Initialize database"
        echo "Run: curl -X POST https://coinswarm-historical-collection-cron.bamn86.workers.dev/init"
        exit 0
    fi

    remaining=$((20 - i))
    echo "Remaining checks: $remaining"
done

echo ""
echo "========================================="
echo "⚠️  Deployment did not complete in 10 minutes"
echo "========================================="
echo ""
echo "Possible issues:"
echo "1. GitHub Actions workflow failed"
echo "2. Cloudflare API issues"
echo "3. Branch controls preventing deployment"
echo ""
echo "Check GitHub Actions: https://github.com/TheAIGuyFromAR/Coinswarm/actions"
echo "Check Cloudflare Dashboard: https://dash.cloudflare.com"
exit 1
