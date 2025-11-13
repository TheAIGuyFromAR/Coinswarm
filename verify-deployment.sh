#!/bin/bash

# Automated Post-Deployment Verification Script
# Runs after GitHub Actions deployment to verify everything works

# Don't exit on error - we want to see all results
set +e

# Set timeouts for wrangler commands
export WRANGLER_TIMEOUT=10

echo "🔍 Post-Deployment Verification"
echo "========================================"
echo "Working directory: $(pwd)"
echo "Date: $(date)"
echo ""

# Exit codes
EXIT_SUCCESS=0
EXIT_WARNING=1
EXIT_FAILURE=2

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Functions
pass() {
    echo -e "${GREEN}✅ PASS:${NC} $1"
    ((PASSED++))
}

fail() {
    echo -e "${RED}❌ FAIL:${NC} $1"
    ((FAILED++))
}

warn() {
    echo -e "${YELLOW}⚠️  WARN:${NC} $1"
    ((WARNINGS++))
}

info() {
    echo -e "${BLUE}ℹ️  INFO:${NC} $1"
}

# Check if required env vars are set
echo "Checking environment variables..."
if [ -z "$CLOUDFLARE_API_TOKEN" ]; then
    fail "CLOUDFLARE_API_TOKEN not set"
    echo "This script requires CLOUDFLARE_API_TOKEN to be set"
    exit $EXIT_FAILURE
else
    pass "CLOUDFLARE_API_TOKEN is set"
fi

if [ -z "$CLOUDFLARE_ACCOUNT_ID" ]; then
    fail "CLOUDFLARE_ACCOUNT_ID not set"
    echo "This script requires CLOUDFLARE_ACCOUNT_ID to be set"
    exit $EXIT_FAILURE
else
    pass "CLOUDFLARE_ACCOUNT_ID is set"
fi

export CLOUDFLARE_API_TOKEN
export CLOUDFLARE_ACCOUNT_ID

info "Using Cloudflare Account: $CLOUDFLARE_ACCOUNT_ID"
echo ""

# Function to run commands with timeout
run_with_timeout() {
    timeout 30 "$@" 2>&1
    local exit_code=$?
    if [ $exit_code -eq 124 ]; then
        echo "TIMEOUT after 30 seconds"
    fi
    return $exit_code
}

# Test 1: Check if queues exist
echo "Test 1: Verifying queues exist..."
info "Running: wrangler queues list (max 30 sec timeout)"
QUEUE_LIST=$(run_with_timeout wrangler queues list || echo "FAILED")
echo "Queue list result: $(echo "$QUEUE_LIST" | head -3)"

if echo "$QUEUE_LIST" | grep -q "historical-data-queue"; then
    pass "historical-data-queue exists"
else
    fail "historical-data-queue not found"
fi

if echo "$QUEUE_LIST" | grep -q "historical-data-dlq"; then
    pass "historical-data-dlq (dead letter queue) exists"
else
    warn "historical-data-dlq not found (non-critical)"
fi

echo ""

# Test 2: Check if consumer is attached to queue
echo ""
echo "Test 2: Verifying queue consumer..."
info "Running: wrangler queues consumer historical-data-queue (max 30 sec timeout)"
CONSUMER_INFO=$(run_with_timeout wrangler queues consumer historical-data-queue || echo "FAILED")
echo "Consumer info result: $(echo "$CONSUMER_INFO" | head -3)"

if echo "$CONSUMER_INFO" | grep -q "historical-data-queue-consumer"; then
    pass "Consumer attached to queue"

    # Check consumer settings
    if echo "$CONSUMER_INFO" | grep -q "max_batch_size.*100"; then
        pass "Consumer batch size: 100"
    else
        warn "Consumer batch size may not be configured correctly"
    fi

    if echo "$CONSUMER_INFO" | grep -q "max_concurrency.*5"; then
        pass "Consumer concurrency: 5"
    else
        warn "Consumer concurrency may not be configured correctly"
    fi
else
    fail "Consumer not attached to queue"
fi

echo ""

# Test 3: Check if D1 database exists and is accessible
echo "Test 3: Verifying D1 database..."
DB_ID="ac4629b2-8240-4378-b3e3-e5262cd9b285"

DB_LIST=$(wrangler d1 list 2>&1 || echo "FAILED")
if echo "$DB_LIST" | grep -q "$DB_ID"; then
    pass "D1 database accessible"

    # Check if price_data table exists
    TABLE_CHECK=$(wrangler d1 execute $DB_ID \
        --command "SELECT name FROM sqlite_master WHERE type='table' AND name='price_data';" \
        --remote 2>&1 || echo "FAILED")

    if echo "$TABLE_CHECK" | grep -q "price_data"; then
        pass "price_data table exists"

        # Get initial row count (for later comparison)
        ROW_COUNT=$(wrangler d1 execute $DB_ID \
            --command "SELECT COUNT(*) as count FROM price_data;" \
            --remote 2>&1 | grep -o "[0-9]\+" | tail -1 || echo "0")
        info "Current row count: $ROW_COUNT"
        echo "$ROW_COUNT" > /tmp/initial_row_count.txt
    else
        fail "price_data table not found"
    fi
else
    fail "D1 database not accessible"
fi

echo ""

# Test 4: Check worker deployments
echo "Test 4: Verifying worker deployments..."

# Check consumer
CONSUMER_DEPLOY=$(wrangler deployments list --name historical-data-queue-consumer 2>&1 | head -5 || echo "FAILED")
if echo "$CONSUMER_DEPLOY" | grep -E "(Active|Success|Deployed)" > /dev/null; then
    pass "Queue consumer deployed"
else
    fail "Queue consumer deployment not found"
fi

# Check producer
PRODUCER_DEPLOY=$(wrangler deployments list --name historical-data-queue-producer 2>&1 | head -5 || echo "FAILED")
if echo "$PRODUCER_DEPLOY" | grep -E "(Active|Success|Deployed)" > /dev/null; then
    pass "Queue producer deployed"
else
    fail "Queue producer deployment not found"
fi

# Check Python worker
PYTHON_DEPLOY=$(wrangler deployments list --name coinswarm-historical-import 2>&1 | head -5 || echo "FAILED")
if echo "$PYTHON_DEPLOY" | grep -E "(Active|Success|Deployed)" > /dev/null; then
    pass "Python historical worker deployed"
else
    warn "Python historical worker deployment not found (may need manual deployment)"
fi

echo ""

# Test 5: Check queue depth (should be low initially)
echo "Test 5: Checking initial queue depth..."
QUEUE_DEPTH=$(echo "$CONSUMER_INFO" | grep -E "Messages:|Queued:" | grep -o "[0-9]\+" | head -1 || echo "0")

if [ "$QUEUE_DEPTH" -eq 0 ]; then
    pass "Queue is empty (consumer is keeping up)"
elif [ "$QUEUE_DEPTH" -lt 1000 ]; then
    pass "Queue depth is low ($QUEUE_DEPTH messages)"
else
    warn "Queue has $QUEUE_DEPTH messages (may be backlog)"
fi

echo ""

# Test 6: Check cron trigger is configured
echo "Test 6: Verifying cron trigger..."
PRODUCER_CONFIG=$(cat cloudflare-agents/wrangler-historical-queue-producer.toml 2>/dev/null || echo "FAILED")

if echo "$PRODUCER_CONFIG" | grep -q 'crons.*=.*\[".*30.*\*.*\*.*\*.*\*.*"\]'; then
    pass "Producer has 30-minute cron trigger"
elif echo "$PRODUCER_CONFIG" | grep -q 'crons'; then
    warn "Producer has cron trigger but may not be 30-minute interval"
else
    fail "Producer missing cron trigger"
fi

echo ""

# Test 7: Verify consumer writes to correct table
echo "Test 7: Verifying consumer configuration..."
CONSUMER_CODE=$(cat cloudflare-agents/historical-data-queue-consumer.ts 2>/dev/null || echo "FAILED")

if echo "$CONSUMER_CODE" | grep -q "INSERT.*INTO price_data"; then
    pass "Consumer writes to price_data table (correct!)"
elif echo "$CONSUMER_CODE" | grep -q "INSERT.*INTO historical_prices"; then
    fail "Consumer writes to historical_prices table (wrong!)"
else
    warn "Could not verify consumer table target"
fi

# Check for INSERT OR IGNORE
if echo "$CONSUMER_CODE" | grep -q "INSERT OR IGNORE"; then
    pass "Consumer uses INSERT OR IGNORE (protects existing data)"
else
    fail "Consumer missing INSERT OR IGNORE"
fi

echo ""

# Test 8: Verify Python worker uses queues
echo "Test 8: Verifying Python worker configuration..."
PYTHON_CODE=$(cat pyswarm/Data_Import/historical_worker.py 2>/dev/null || echo "FAILED")
PYTHON_CONFIG=$(cat pyswarm/wrangler_historical_import.toml 2>/dev/null || echo "FAILED")

if echo "$PYTHON_CODE" | grep -q "HISTORICAL_QUEUE"; then
    pass "Python worker uses queue"
else
    fail "Python worker missing queue usage"
fi

if echo "$PYTHON_CONFIG" | grep -q "HISTORICAL_QUEUE"; then
    pass "Python worker has queue binding"
else
    fail "Python worker missing queue binding"
fi

if echo "$PYTHON_CODE" | grep -q "sendBatch"; then
    pass "Python worker uses batch sending"
else
    warn "Python worker may not use batch sending"
fi

echo ""

# Summary
echo "========================================"
echo "📊 Verification Summary"
echo "========================================"
echo ""
echo -e "${GREEN}✅ Passed:${NC} $PASSED"
echo -e "${YELLOW}⚠️  Warnings:${NC} $WARNINGS"
echo -e "${RED}❌ Failed:${NC} $FAILED"
echo ""

# Determine exit code
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}❌ DEPLOYMENT VERIFICATION FAILED${NC}"
    echo "   Please review failures above and redeploy if necessary."
    exit $EXIT_FAILURE
elif [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}⚠️  DEPLOYMENT VERIFIED WITH WARNINGS${NC}"
    echo "   System is functional but some issues were detected."
    exit $EXIT_WARNING
else
    echo -e "${GREEN}✅ DEPLOYMENT VERIFIED SUCCESSFULLY!${NC}"
    echo "   All checks passed. System is ready for use."
    echo ""
    echo "🎯 Next steps:"
    echo "   1. Monitor queue: wrangler queues consumer historical-data-queue"
    echo "   2. Watch consumer logs: wrangler tail historical-data-queue-consumer --format pretty"
    echo "   3. Trigger Python worker: curl -X POST https://coinswarm-historical-import.<subdomain>.workers.dev/trigger"
    exit $EXIT_SUCCESS
fi
