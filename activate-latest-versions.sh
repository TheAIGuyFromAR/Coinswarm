#!/bin/bash
# Activate the latest deployed versions of Cloudflare Workers
# This forces workers to serve the newest uploaded code

ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID:-}"
API_TOKEN="${CLOUDFLARE_API_TOKEN:-}"

if [ -z "$ACCOUNT_ID" ] || [ -z "$API_TOKEN" ]; then
    echo "Error: CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN must be set"
    echo ""
    echo "Usage:"
    echo "  export CLOUDFLARE_ACCOUNT_ID='your-account-id'"
    echo "  export CLOUDFLARE_API_TOKEN='your-api-token'"
    echo "  ./activate-latest-versions.sh"
    exit 1
fi

echo "🚀 Activating Latest Worker Versions..."
echo "========================================"
echo ""

workers=(
    "coinswarm-historical-collection-cron"
    "coinswarm-realtime-price-cron"
    "coinswarm-data-monitor"
    "coinswarm-technical-indicators"
    "coinswarm-collection-alerts"
    "coinswarm-historical-data"
)

for worker in "${workers[@]}"; do
    echo "📦 Processing: $worker"

    # Get all versions/deployments
    versions_response=$(curl -s -X GET \
        "https://api.cloudflare.com/client/v4/accounts/${ACCOUNT_ID}/workers/scripts/${worker}/versions" \
        -H "Authorization: Bearer ${API_TOKEN}" \
        -H "Content-Type: application/json")

    if echo "$versions_response" | jq -e '.success' >/dev/null 2>&1; then
        latest_version=$(echo "$versions_response" | jq -r '.result.items[0].id' 2>/dev/null)

        if [ -n "$latest_version" ] && [ "$latest_version" != "null" ]; then
            echo "   Latest version: $latest_version"

            # Deploy this version to 100% of traffic
            deploy_response=$(curl -s -X POST \
                "https://api.cloudflare.com/client/v4/accounts/${ACCOUNT_ID}/workers/scripts/${worker}/deployments" \
                -H "Authorization: Bearer ${API_TOKEN}" \
                -H "Content-Type: application/json" \
                -d "{\"version_id\": \"${latest_version}\", \"percentage\": 100}")

            if echo "$deploy_response" | jq -e '.success' >/dev/null 2>&1; then
                echo "   ✅ Activated to 100% traffic"
            else
                echo "   ⚠️  Deployment response:"
                echo "$deploy_response" | jq '.'
            fi
        else
            echo "   ℹ️  No versions found (worker might use legacy deployment)"

            # For workers without versions, try gradual deployments API
            current_deployment=$(curl -s -X GET \
                "https://api.cloudflare.com/client/v4/accounts/${ACCOUNT_ID}/workers/scripts/${worker}/deployments" \
                -H "Authorization: Bearer ${API_TOKEN}")

            echo "   Current deployment info:"
            echo "$current_deployment" | jq '.result[0] | {created_on, author_email}' 2>/dev/null || echo "   No deployment data"
        fi
    else
        echo "   ❌ Failed to get versions:"
        echo "$versions_response" | jq '.errors' 2>/dev/null || echo "$versions_response"
    fi

    echo ""
done

echo "✅ Version activation complete!"
echo ""
echo "🔍 Testing endpoints to verify activation..."
echo ""

for worker in "${workers[@]}"; do
    url="https://${worker}.bamn86.workers.dev/"
    echo -n "Testing $worker... "

    http_code=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>&1)

    if [ "$http_code" = "200" ]; then
        echo "✅ HTTP 200"
    else
        echo "⚠️  HTTP $http_code"
    fi
done

echo ""
echo "🎯 Special check: /init endpoint on historical-collection-cron"
init_response=$(curl -s -X POST "https://coinswarm-historical-collection-cron.bamn86.workers.dev/init")

if echo "$init_response" | jq -e '.success' >/dev/null 2>&1; then
    echo "✅ /init endpoint is ACTIVE (new version deployed!)"
    echo "$init_response" | jq '.'
elif echo "$init_response" | jq -e '.tokens' >/dev/null 2>&1; then
    echo "⚠️  Still showing old version (no /init endpoint)"
    echo "$init_response" | jq '{status, name, tokens}'
else
    echo "❓ Unexpected response:"
    echo "$init_response"
fi
