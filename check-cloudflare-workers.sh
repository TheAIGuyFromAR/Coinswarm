#!/bin/bash
# Query Cloudflare API to see what workers are actually deployed

# Read from GitHub secrets or environment
ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID:-}"
API_TOKEN="${CLOUDFLARE_API_TOKEN:-}"

if [ -z "$ACCOUNT_ID" ] || [ -z "$API_TOKEN" ]; then
    echo "Error: CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN must be set"
    echo ""
    echo "Usage:"
    echo "  export CLOUDFLARE_ACCOUNT_ID='your-account-id'"
    echo "  export CLOUDFLARE_API_TOKEN='your-api-token'"
    echo "  ./check-cloudflare-workers.sh"
    echo ""
    echo "Or get them from GitHub secrets:"
    echo "  gh secret list"
    exit 1
fi

echo "🔍 Querying Cloudflare Workers API..."
echo "Account ID: ${ACCOUNT_ID:0:10}..."
echo ""

# List all workers
echo "📋 All Deployed Workers:"
echo "========================"

response=$(curl -s -X GET \
  "https://api.cloudflare.com/client/v4/accounts/${ACCOUNT_ID}/workers/scripts" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json")

if echo "$response" | jq -e '.success' >/dev/null 2>&1; then
    echo "$response" | jq -r '.result[] | "- \(.id)"' | sort

    total=$(echo "$response" | jq -r '.result | length')
    echo ""
    echo "Total workers deployed: $total"
    echo ""

    # Check for specific workers we created
    echo "🎯 Checking for New Workers:"
    echo "============================"

    workers=(
        "coinswarm-data-monitor"
        "coinswarm-realtime-price-cron"
        "coinswarm-technical-indicators"
        "coinswarm-collection-alerts"
        "coinswarm-historical-collection-cron"
    )

    for worker in "${workers[@]}"; do
        if echo "$response" | jq -r '.result[].id' | grep -q "^${worker}$"; then
            echo "✅ $worker - DEPLOYED"

            # Get worker details
            details=$(curl -s -X GET \
              "https://api.cloudflare.com/client/v4/accounts/${ACCOUNT_ID}/workers/scripts/${worker}" \
              -H "Authorization: Bearer ${API_TOKEN}")

            # Get latest deployment
            deployments=$(curl -s -X GET \
              "https://api.cloudflare.com/client/v4/accounts/${ACCOUNT_ID}/workers/scripts/${worker}/deployments" \
              -H "Authorization: Bearer ${API_TOKEN}")

            if echo "$deployments" | jq -e '.result[0]' >/dev/null 2>&1; then
                deployed_at=$(echo "$deployments" | jq -r '.result[0].created_on')
                echo "   Last deployed: $deployed_at"
            fi
        else
            echo "❌ $worker - NOT FOUND"
        fi
    done

else
    echo "❌ API Error:"
    echo "$response" | jq '.'
    exit 1
fi

echo ""
echo "🔗 Testing Worker Endpoints:"
echo "============================"

for worker in "${workers[@]}"; do
    if echo "$response" | jq -r '.result[].id' | grep -q "^${worker}$"; then
        url="https://${worker}.bamn86.workers.dev/"
        echo -n "Testing $worker... "

        test_response=$(curl -s -w "\n%{http_code}" "$url" 2>&1 | tail -1)

        if [ "$test_response" = "200" ]; then
            echo "✅ HTTP 200"
        else
            echo "❌ HTTP $test_response"
        fi
    fi
done
