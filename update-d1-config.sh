#!/bin/bash
# Quick script to update wrangler config with your existing D1 database ID

set -e

echo "🔍 Finding your D1 database..."
echo ""

# List D1 databases and find coinswarm
DB_LIST=$(wrangler d1 list 2>&1)

# Check if coinswarm-historical-data exists
if echo "$DB_LIST" | grep -q "coinswarm-historical-data"; then
    echo "✅ Found existing D1 database: coinswarm-historical-data"
    echo ""

    # Extract database ID
    # Format: database_id: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    DB_ID=$(echo "$DB_LIST" | grep -A 1 "coinswarm-historical-data" | grep -o '[0-9a-f]\{8\}-[0-9a-f]\{4\}-[0-9a-f]\{4\}-[0-9a-f]\{4\}-[0-9a-f]\{12\}' | head -1)

    if [ -z "$DB_ID" ]; then
        echo "❌ Could not extract database ID"
        echo ""
        echo "Please run manually:"
        echo "  wrangler d1 list"
        echo ""
        echo "And update wrangler-data-ingestion.toml with your database_id"
        exit 1
    fi

    echo "Database ID: $DB_ID"
    echo ""

    # Update wrangler config
    echo "📝 Updating wrangler-data-ingestion.toml..."

    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/database_id = \".*\"/database_id = \"$DB_ID\"/" wrangler-data-ingestion.toml
    else
        # Linux
        sed -i "s/database_id = \".*\"/database_id = \"$DB_ID\"/" wrangler-data-ingestion.toml
    fi

    echo "✅ Updated wrangler-data-ingestion.toml"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✨ Ready to deploy!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Run:"
    echo "  git add wrangler-data-ingestion.toml"
    echo "  git commit -m 'Configure D1 database for backfill worker'"
    echo "  git push"
    echo ""
    echo "GitHub Actions will automatically deploy!"
    echo ""

else
    echo "❌ No D1 database named 'coinswarm-historical-data' found"
    echo ""
    echo "Your databases:"
    wrangler d1 list
    echo ""
    echo "Create one with:"
    echo "  wrangler d1 create coinswarm-historical-data"
    echo ""
    echo "Then apply schema:"
    echo "  wrangler d1 execute coinswarm-historical-data --file=cloudflare-d1-schema.sql"
    echo ""
    exit 1
fi
