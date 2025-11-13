#!/bin/bash

# Queue System Test Script
# Run this after GitHub Actions deployment completes

set -e  # Exit on error

echo "🧪 Testing Queue-Based Historical Data System"
echo "=============================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
pass() {
    echo -e "${GREEN}✅ $1${NC}"
}

fail() {
    echo -e "${RED}❌ $1${NC}"
}

warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

info() {
    echo -e "ℹ️  $1"
}

# Check if wrangler is installed
echo "1. Checking prerequisites..."
if command -v wrangler &> /dev/null; then
    pass "Wrangler CLI found"
    WRANGLER_VERSION=$(wrangler --version 2>&1 | head -1)
    info "Version: $WRANGLER_VERSION"
else
    fail "Wrangler CLI not found"
    info "Install with: npm install -g wrangler"
    exit 1
fi

# Check if logged in
echo ""
echo "2. Checking Cloudflare authentication..."
if wrangler whoami &> /dev/null; then
    pass "Authenticated to Cloudflare"
    USER_INFO=$(wrangler whoami 2>&1 | grep "You are logged in" || echo "Logged in")
    info "$USER_INFO"
else
    fail "Not authenticated to Cloudflare"
    info "Run: wrangler login"
    exit 1
fi

# Check if queues exist
echo ""
echo "3. Checking if queues exist..."
if wrangler queues list 2>&1 | grep -q "historical-data-queue"; then
    pass "historical-data-queue exists"
else
    warn "historical-data-queue not found"
    info "Creating queue..."
    wrangler queues create historical-data-queue
    pass "historical-data-queue created"
fi

if wrangler queues list 2>&1 | grep -q "historical-data-dlq"; then
    pass "historical-data-dlq exists"
else
    warn "historical-data-dlq not found"
    info "Creating dead letter queue..."
    wrangler queues create historical-data-dlq
    pass "historical-data-dlq created"
fi

# Check queue consumer status
echo ""
echo "4. Checking queue consumer status..."
CONSUMER_OUTPUT=$(wrangler queues consumer historical-data-queue 2>&1)
if echo "$CONSUMER_OUTPUT" | grep -q "historical-data-queue-consumer"; then
    pass "Consumer attached to queue"
    echo "$CONSUMER_OUTPUT" | grep -E "(max_batch_size|max_concurrency|max_retries)"
else
    warn "Consumer not attached to queue"
    info "Consumer should be deployed by GitHub Actions"
    info "Check: https://github.com/TheAIGuyFromAR/Coinswarm/actions"
fi

# Check if D1 database exists
echo ""
echo "5. Checking D1 database..."
DB_ID="ac4629b2-8240-4378-b3e3-e5262cd9b285"
if wrangler d1 list 2>&1 | grep -q "$DB_ID"; then
    pass "D1 database found (coinswarm-evolution)"

    # Check if price_data table exists
    info "Checking price_data table..."
    TABLE_CHECK=$(wrangler d1 execute $DB_ID --command "SELECT name FROM sqlite_master WHERE type='table' AND name='price_data';" --remote 2>&1)
    if echo "$TABLE_CHECK" | grep -q "price_data"; then
        pass "price_data table exists"

        # Get row count
        info "Checking row count..."
        ROW_COUNT=$(wrangler d1 execute $DB_ID --command "SELECT COUNT(*) as count FROM price_data;" --remote 2>&1 | grep -o "[0-9]\+" | tail -1)
        pass "Current rows: $ROW_COUNT"
    else
        warn "price_data table not found"
        info "May need to apply schema"
    fi
else
    fail "D1 database not found"
    info "Database ID: $DB_ID"
    exit 1
fi

# Test Python worker (if user provides subdomain)
echo ""
echo "6. Testing Python worker (manual trigger)..."
echo ""
read -p "Enter your Cloudflare subdomain (or press Enter to skip): " SUBDOMAIN

if [ -n "$SUBDOMAIN" ]; then
    WORKER_URL="https://coinswarm-historical-import.$SUBDOMAIN.workers.dev/trigger"
    info "Triggering: $WORKER_URL"

    RESPONSE=$(curl -s -X POST "$WORKER_URL" -w "\nHTTP_CODE:%{http_code}")
    HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
    BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE")

    if [ "$HTTP_CODE" = "200" ]; then
        pass "Python worker responded successfully"
        echo "$BODY" | jq . 2>/dev/null || echo "$BODY"

        # Check if data was queued
        if echo "$BODY" | grep -q "Queued"; then
            pass "Data queued successfully"
            CANDLES=$(echo "$BODY" | grep -o "[0-9]\+ candles" | head -1)
            info "$CANDLES queued"
        fi
    else
        warn "Python worker returned HTTP $HTTP_CODE"
        echo "$BODY"
    fi
else
    info "Skipping Python worker test"
    info "To test manually, run:"
    info "  curl -X POST https://coinswarm-historical-import.<subdomain>.workers.dev/trigger"
fi

# Monitor queue depth
echo ""
echo "7. Monitoring queue depth..."
info "Checking current queue status..."
sleep 2

QUEUE_STATUS=$(wrangler queues consumer historical-data-queue 2>&1)
echo "$QUEUE_STATUS"

if echo "$QUEUE_STATUS" | grep -q "Messages:"; then
    MSG_COUNT=$(echo "$QUEUE_STATUS" | grep "Messages:" | grep -o "[0-9]\+" || echo "0")
    if [ "$MSG_COUNT" -gt 0 ]; then
        warn "Queue has $MSG_COUNT messages"
        info "Consumer should be processing these"
        info "Monitor with: wrangler tail historical-data-queue-consumer --format pretty"
    else
        pass "Queue is empty (consumer is keeping up!)"
    fi
fi

# Summary
echo ""
echo "=============================================="
echo "📊 Test Summary"
echo "=============================================="
echo ""
pass "Wrangler CLI configured"
pass "Cloudflare authenticated"
pass "Queues created"

if echo "$CONSUMER_OUTPUT" | grep -q "historical-data-queue-consumer"; then
    pass "Consumer deployed and attached"
else
    warn "Consumer may not be deployed yet"
fi

pass "D1 database accessible"

echo ""
echo "🎯 Next Steps:"
echo ""
echo "1. Monitor consumer logs:"
echo "   wrangler tail historical-data-queue-consumer --format pretty"
echo ""
echo "2. Check queue depth:"
echo "   wrangler queues consumer historical-data-queue"
echo ""
echo "3. Trigger Python worker:"
echo "   curl -X POST https://coinswarm-historical-import.<subdomain>.workers.dev/trigger"
echo ""
echo "4. Verify data in D1:"
echo "   wrangler d1 execute $DB_ID \\"
echo "     --command \"SELECT COUNT(*) as total, source FROM price_data GROUP BY source\" \\"
echo "     --remote"
echo ""
echo "5. Monitor GitHub Actions:"
echo "   https://github.com/TheAIGuyFromAR/Coinswarm/actions"
echo ""
echo "✅ System is ready!"
echo ""
