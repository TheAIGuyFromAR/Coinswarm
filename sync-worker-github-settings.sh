#!/bin/bash
# Sync all workers to use GitHub Actions with correct branch settings
# Based on subdomain: bamn86

set -e

ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID:-}"
API_TOKEN="${CLOUDFLARE_API_TOKEN:-}"
TARGET_BRANCH="claude/audit-historical-data-system-011CUx7r66ZDX5rTp6bRDQYE"
GITHUB_REPO="TheAIGuyFromAR/Coinswarm"

if [ -z "$ACCOUNT_ID" ] || [ -z "$API_TOKEN" ]; then
    echo "❌ Error: CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN must be set"
    exit 1
fi

echo "🔧 Syncing Worker GitHub Settings"
echo "Target Branch: $TARGET_BRANCH"
echo "Subdomain: bamn86"
echo ""

# Workers that should be deployed via GitHub Actions
WORKERS=(
    "coinswarm-historical-collection-cron"
    "coinswarm-realtime-price-cron"
    "coinswarm-data-monitor"
    "coinswarm-technical-indicators"
    "coinswarm-collection-alerts"
    "coinswarm-historical-data"
    "coinswarm-evolution-agent"
    "coinswarm-news-sentiment"
    "coinswarm-multi-exchange"
    "coinswarm-solana-dex"
    "coinswarm-sentiment-backfill"
)

for worker in "${WORKERS[@]}"; do
    echo "📦 Checking: $worker"

    # Get current worker settings
    current=$(curl -s -X GET \
        "https://api.cloudflare.com/client/v4/accounts/${ACCOUNT_ID}/workers/scripts/${worker}/settings" \
        -H "Authorization: Bearer ${API_TOKEN}" \
        -H "Content-Type: application/json")

    if echo "$current" | jq -e '.success == true' >/dev/null 2>&1; then
        echo "   ✅ Worker exists"

        # Check deployment source
        source=$(echo "$current" | jq -r '.result.deployment_source // "manual"')
        echo "   Current source: $source"

        # Update to use GitHub Actions if not already
        if [ "$source" != "github" ]; then
            echo "   🔄 Updating to GitHub Actions deployment..."

            update=$(curl -s -X PATCH \
                "https://api.cloudflare.com/client/v4/accounts/${ACCOUNT_ID}/workers/scripts/${worker}/settings" \
                -H "Authorization: Bearer ${API_TOKEN}" \
                -H "Content-Type: application/json" \
                -d "{
                    \"deployment_source\": \"github\",
                    \"github_repo\": \"${GITHUB_REPO}\",
                    \"github_branch\": \"${TARGET_BRANCH}\",
                    \"auto_deploy\": true
                }")

            if echo "$update" | jq -e '.success == true' >/dev/null 2>&1; then
                echo "   ✅ Updated to GitHub Actions"
            else
                error=$(echo "$update" | jq -r '.errors[0].message // "Unknown error"')
                echo "   ⚠️  Update response: $error"
                echo "   Note: Workers deployed via wrangler may not support this API"
            fi
        else
            # Check if branch is correct
            current_branch=$(echo "$current" | jq -r '.result.github_branch // "unknown"')
            if [ "$current_branch" != "$TARGET_BRANCH" ]; then
                echo "   🔄 Updating branch from $current_branch to $TARGET_BRANCH..."

                update=$(curl -s -X PATCH \
                    "https://api.cloudflare.com/client/v4/accounts/${ACCOUNT_ID}/workers/scripts/${worker}/settings" \
                    -H "Authorization: Bearer ${API_TOKEN}" \
                    -H "Content-Type: application/json" \
                    -d "{
                        \"github_branch\": \"${TARGET_BRANCH}\"
                    }")

                if echo "$update" | jq -e '.success == true' >/dev/null 2>&1; then
                    echo "   ✅ Branch updated"
                else
                    echo "   ⚠️  Could not update branch (may be wrangler-deployed)"
                fi
            else
                echo "   ✅ Branch already correct"
            fi
        fi

        # Trigger redeployment
        echo "   🚀 Triggering redeployment..."
        redeploy=$(curl -s -X POST \
            "https://api.cloudflare.com/client/v4/accounts/${ACCOUNT_ID}/workers/scripts/${worker}/deployments" \
            -H "Authorization: Bearer ${API_TOKEN}" \
            -H "Content-Type: application/json" \
            -d '{"force": true}')

        if echo "$redeploy" | jq -e '.success == true' >/dev/null 2>&1; then
            echo "   ✅ Redeployment triggered"
        else
            echo "   ℹ️  Redeployment will happen via GitHub Actions"
        fi

    else
        echo "   ❌ Worker not found or error accessing it"
    fi

    echo ""
done

echo "✅ Sync complete!"
echo ""
echo "Next steps:"
echo "1. Wait 2-3 minutes for deployments to complete"
echo "2. Test Historical Cron: curl -X POST https://coinswarm-historical-collection-cron.bamn86.workers.dev/init"
echo "3. Check if /init endpoint is active"
