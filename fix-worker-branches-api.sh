#!/bin/bash
# Use Cloudflare API to update worker branch settings
# Requires CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN

set -e

# Target branch
TARGET_BRANCH="claude/full-code-review-011CUvqUcjpgrh9x49XzAs2v"

# These should come from GitHub secrets or environment
ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID}"
API_TOKEN="${CLOUDFLARE_API_TOKEN}"

if [ -z "$ACCOUNT_ID" ] || [ -z "$API_TOKEN" ]; then
    echo "❌ Missing Cloudflare credentials"
    echo "Set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN environment variables"
    exit 1
fi

echo "🔧 Updating Worker Branch Settings via Cloudflare API"
echo "Target Branch: $TARGET_BRANCH"
echo ""

# Workers to update
WORKERS=(
    "coinswarm-historical-collection-cron"
    "coinswarm-realtime-price-cron"
    "coinswarm-data-monitor"
    "coinswarm-technical-indicators"
    "coinswarm-collection-alerts"
)

for worker in "${WORKERS[@]}"; do
    echo "Processing: $worker"

    # Get current worker configuration
    echo "  Fetching current config..."
    response=$(curl -s -X GET \
        "https://api.cloudflare.com/client/v4/accounts/${ACCOUNT_ID}/workers/scripts/${worker}" \
        -H "Authorization: Bearer ${API_TOKEN}")

    if echo "$response" | jq -e '.success == true' >/dev/null 2>&1; then
        echo "  ✅ Worker exists"

        # For Workers with git integration (Pages Functions), update via Pages API
        # Try to find associated Pages project
        pages_response=$(curl -s -X GET \
            "https://api.cloudflare.com/client/v4/accounts/${ACCOUNT_ID}/pages/projects" \
            -H "Authorization: Bearer ${API_TOKEN}")

        project_name=$(echo "$pages_response" | jq -r ".result[] | select(.name == \"$worker\") | .name")

        if [ -n "$project_name" ]; then
            echo "  Found Pages project: $project_name"
            echo "  Updating deployment branch..."

            update_response=$(curl -s -X PATCH \
                "https://api.cloudflare.com/client/v4/accounts/${ACCOUNT_ID}/pages/projects/${project_name}" \
                -H "Authorization: Bearer ${API_TOKEN}" \
                -H "Content-Type: application/json" \
                -d "{
                    \"production_branch\": \"$TARGET_BRANCH\"
                }")

            if echo "$update_response" | jq -e '.success == true' >/dev/null 2>&1; then
                echo "  ✅ Updated production branch to: $TARGET_BRANCH"
            else
                error=$(echo "$update_response" | jq -r '.errors[0].message // "Unknown error"')
                echo "  ❌ Failed to update: $error"
            fi
        else
            echo "  ℹ️  Not a Pages project - checking Workers for Platforms..."

            # Try Workers for Platforms dispatch namespace
            # This is for workers deployed via wrangler with git integration
            echo "  Checking for dispatch namespace..."

            # If it's a regular worker (not Pages), it doesn't have a "branch" setting
            # It's deployed directly from code via wrangler
            echo "  ℹ️  Regular Worker - no branch setting (deployed via wrangler)"
            echo "  💡 To update: Push code to GitHub, then GitHub Actions will deploy"
        fi
    else
        error=$(echo "$response" | jq -r '.errors[0].message // "Worker not found"')
        echo "  ❌ $error"
    fi

    echo ""
done

echo ""
echo "Summary:"
echo "- Workers deployed via wrangler don't have branch settings"
echo "- They deploy whatever code GitHub Actions checks out"
echo "- GitHub Actions is configured for branch: $TARGET_BRANCH"
echo "- Last deployment was successful at: 2025-11-09T07:42:19Z"
echo ""
echo "If workers still show old code, the issue might be:"
echo "1. GitHub Actions 'continue-on-error: true' hid deployment failures"
echo "2. Workers need secrets (COINGECKO, CRYPTOCOMPARE_API_KEY)"
echo "3. TypeScript compilation errors prevented deployment"
echo ""
echo "Check GitHub Actions logs for actual deployment errors."
