#!/bin/bash
# Update Cloudflare Worker branch settings via API

set -e

# Get credentials from environment or GitHub secrets
ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID:-}"
API_TOKEN="${CLOUDFLARE_API_TOKEN:-}"

if [ -z "$ACCOUNT_ID" ] || [ -z "$API_TOKEN" ]; then
    echo "❌ Error: CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN must be set"
    echo ""
    echo "Get them from your GitHub secrets:"
    echo "  ACCOUNT_ID: In your Cloudflare dashboard or GitHub repo secrets"
    echo "  API_TOKEN: In your Cloudflare dashboard (API Tokens)"
    echo ""
    echo "Then run:"
    echo "  export CLOUDFLARE_ACCOUNT_ID='your-account-id'"
    echo "  export CLOUDFLARE_API_TOKEN='your-api-token'"
    echo "  $0"
    exit 1
fi

TARGET_BRANCH="claude/full-code-review-011CUvqUcjpgrh9x49XzAs2v"

echo "🔧 Updating Cloudflare Worker Branch Settings"
echo "=============================================="
echo "Target branch: $TARGET_BRANCH"
echo "Account ID: ${ACCOUNT_ID:0:10}..."
echo ""

# List of new workers
WORKERS=(
    "coinswarm-historical-collection-cron"
    "coinswarm-realtime-price-cron"
    "coinswarm-data-monitor"
    "coinswarm-technical-indicators"
    "coinswarm-collection-alerts"
)

echo "Checking worker settings..."
echo ""

for worker in "${WORKERS[@]}"; do
    echo "📋 Checking: $worker"

    # Get worker details
    response=$(curl -s -X GET \
        "https://api.cloudflare.com/client/v4/accounts/${ACCOUNT_ID}/workers/scripts/${worker}/settings" \
        -H "Authorization: Bearer ${API_TOKEN}" \
        -H "Content-Type: application/json")

    if echo "$response" | jq -e '.success' >/dev/null 2>&1; then
        echo "  ✅ Worker exists"

        # Check for deployment settings
        current_settings=$(echo "$response" | jq -r '.result')
        echo "  Current settings: $current_settings"

        # Check if there's a source/git configuration
        if echo "$response" | jq -e '.result.deployments' >/dev/null 2>&1; then
            echo "  Has deployment configuration"

            # Try to update deployment branch
            update_response=$(curl -s -X PUT \
                "https://api.cloudflare.com/client/v4/accounts/${ACCOUNT_ID}/workers/scripts/${worker}/settings" \
                -H "Authorization: Bearer ${API_TOKEN}" \
                -H "Content-Type: application/json" \
                -d "{
                    \"deployment\": {
                        \"branch\": \"$TARGET_BRANCH\"
                    }
                }")

            if echo "$update_response" | jq -e '.success' >/dev/null 2>&1; then
                echo "  ✅ Updated branch to: $TARGET_BRANCH"
            else
                echo "  ⚠️  Could not update branch:"
                echo "     $(echo "$update_response" | jq -r '.errors[0].message')"
            fi
        else
            echo "  ℹ️  No deployment configuration (deployed via wrangler)"
        fi
    else
        error_msg=$(echo "$response" | jq -r '.errors[0].message // "Unknown error"')

        if [[ "$error_msg" == *"not found"* ]] || [[ "$error_msg" == *"10007"* ]]; then
            echo "  ❌ Worker does not exist - needs to be deployed first"
            echo "     Run: cd cloudflare-agents && npx wrangler deploy --config wrangler-$(echo $worker | sed 's/coinswarm-//')*.toml"
        else
            echo "  ❌ Error: $error_msg"
        fi
    fi

    echo ""
done

echo ""
echo "💡 Note: Workers deployed via 'wrangler deploy' don't have branch settings."
echo "   They deploy whatever code is in your local directory."
echo ""
echo "   To deploy the new workers, either:"
echo "   1. Run './deploy-new-workers.sh'"
echo "   2. Or merge this branch to 'main' if your GitHub Actions deploys from main"
echo "   3. Or manually run: cd cloudflare-agents && npx wrangler deploy --config <config-file>"
