#!/bin/bash
# Automated Data Pipeline Deployment Script
# Run this from your local machine (not in the Claude Code environment)

set -e  # Exit on error

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║     Coinswarm Automated Data Pipeline Deployment             ║"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
CRYPTOCOMPARE_API_KEY="da672b9999120841fbd4427fa4550b83b5f23e017c5c03ff33bafe09064abe83"
DB_NAME="coinswarm-historical-data"
WORKER_NAME="coinswarm-data-backfill"
WRANGLER_CONFIG="wrangler-data-ingestion.toml"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 1: Check Prerequisites"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if wrangler is installed
if ! command -v wrangler &> /dev/null; then
    echo -e "${RED}✗ Wrangler not found${NC}"
    echo ""
    echo "Please install wrangler:"
    echo "  npm install -g wrangler"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ Wrangler installed${NC}"

# Check if logged in
if ! wrangler whoami &> /dev/null; then
    echo -e "${YELLOW}! Not logged in to Cloudflare${NC}"
    echo ""
    echo "Logging in to Cloudflare..."
    wrangler login
    echo ""
fi

echo -e "${GREEN}✓ Logged in to Cloudflare${NC}"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 2: Create D1 Database"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if database already exists
if wrangler d1 list | grep -q "$DB_NAME"; then
    echo -e "${YELLOW}! Database '$DB_NAME' already exists${NC}"
    echo ""

    # Get database ID
    DB_ID=$(wrangler d1 list | grep "$DB_NAME" | awk '{print $2}')
    echo -e "${GREEN}✓ Using existing database: $DB_ID${NC}"
else
    echo "Creating D1 database: $DB_NAME"
    echo ""

    # Create database and capture output
    CREATE_OUTPUT=$(wrangler d1 create "$DB_NAME" 2>&1)

    # Extract database ID from output
    DB_ID=$(echo "$CREATE_OUTPUT" | grep "database_id" | sed 's/.*"\(.*\)".*/\1/')

    if [ -z "$DB_ID" ]; then
        echo -e "${RED}✗ Failed to create database${NC}"
        echo "$CREATE_OUTPUT"
        exit 1
    fi

    echo -e "${GREEN}✓ Created database: $DB_ID${NC}"
fi

echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 3: Apply Database Schema"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ ! -f "cloudflare-d1-schema.sql" ]; then
    echo -e "${RED}✗ Schema file not found: cloudflare-d1-schema.sql${NC}"
    exit 1
fi

echo "Applying schema to database..."
wrangler d1 execute "$DB_NAME" --file=cloudflare-d1-schema.sql

echo -e "${GREEN}✓ Schema applied${NC}"
echo ""

# Verify tables
echo "Verifying tables..."
wrangler d1 execute "$DB_NAME" --command="SELECT name FROM sqlite_master WHERE type='table'"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 4: Update Wrangler Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Update wrangler.toml with database ID
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/database_id = \".*\"/database_id = \"$DB_ID\"/" "$WRANGLER_CONFIG"
else
    # Linux
    sed -i "s/database_id = \".*\"/database_id = \"$DB_ID\"/" "$WRANGLER_CONFIG"
fi

echo -e "${GREEN}✓ Updated $WRANGLER_CONFIG with database_id: $DB_ID${NC}"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 5: Set API Key Secret"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "Setting CRYPTOCOMPARE_API_KEY secret..."
echo "$CRYPTOCOMPARE_API_KEY" | wrangler secret put CRYPTOCOMPARE_API_KEY --config "$WRANGLER_CONFIG"

echo -e "${GREEN}✓ API key secret configured${NC}"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 6: Deploy Worker"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "Deploying backfill worker..."
DEPLOY_OUTPUT=$(wrangler deploy --config "$WRANGLER_CONFIG" 2>&1)

# Extract worker URL
WORKER_URL=$(echo "$DEPLOY_OUTPUT" | grep -o 'https://[^ ]*workers.dev' | head -1)

if [ -z "$WORKER_URL" ]; then
    echo -e "${RED}✗ Failed to deploy worker${NC}"
    echo "$DEPLOY_OUTPUT"
    exit 1
fi

echo -e "${GREEN}✓ Worker deployed!${NC}"
echo ""
echo "Worker URL: ${GREEN}$WORKER_URL${NC}"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 7: Trigger Initial Backfill"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "Triggering first backfill run..."
echo ""

sleep 2  # Give worker a moment to be ready

curl -s "$WORKER_URL/backfill" | python3 -m json.tool 2>/dev/null || curl -s "$WORKER_URL/backfill"

echo ""
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ DEPLOYMENT COMPLETE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎯 Your data pipeline is now running!"
echo ""
echo "Backfill runs: Every minute (cron: * * * * *)"
echo "Worker URL:    $WORKER_URL"
echo "Database:      $DB_NAME ($DB_ID)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Monitor Progress:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Check progress:"
echo "  curl $WORKER_URL/progress | jq"
echo ""
echo "Watch in real-time:"
echo "  watch -n 10 'curl -s $WORKER_URL/progress | jq'"
echo ""
echo "View logs:"
echo "  wrangler tail --config $WRANGLER_CONFIG"
echo ""
echo "Query database:"
echo "  wrangler d1 execute $DB_NAME --command=\"SELECT symbol, timeframe, COUNT(*) FROM price_data GROUP BY symbol, timeframe\""
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⏱️  Expected Timeline:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  • ~3,600 candles per minute"
echo "  • ~24,000 candles total target"
echo "  • Estimated completion: 10-15 minutes"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🛑 Stop Backfilling:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "When backfill is complete (progress stops increasing), disable cron:"
echo ""
echo "  1. Edit $WRANGLER_CONFIG"
echo "  2. Comment out: # crons = [\"* * * * *\"]"
echo "  3. Redeploy: wrangler deploy --config $WRANGLER_CONFIG"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}🚀 Pipeline is filling up! Check progress in a few minutes.${NC}"
echo ""
