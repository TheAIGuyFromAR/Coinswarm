#!/bin/bash
# Test suite for Coinswarm data collection workers
# Documents expected behavior and validates live deployments

set -e

SUBDOMAIN="bamn86"
BASE_URL="https://coinswarm"

echo "🧪 Testing Coinswarm Workers..."
echo "================================"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

# Test helper function
test_endpoint() {
    local name="$1"
    local url="$2"
    local expected_field="$3"
    local expected_value="$4"

    echo -n "Testing $name... "

    response=$(curl -s "$url" 2>&1)

    if echo "$response" | grep -q "DNS resolution failure\|Could not resolve\|Connection refused"; then
        echo -e "${RED}FAIL${NC} - Worker not deployed or DNS issue"
        ((FAILED++))
        return 1
    fi

    if [ -n "$expected_field" ]; then
        if echo "$response" | jq -e ".$expected_field" >/dev/null 2>&1; then
            actual=$(echo "$response" | jq -r ".$expected_field")
            if [ "$actual" = "$expected_value" ]; then
                echo -e "${GREEN}PASS${NC}"
                ((PASSED++))
                return 0
            else
                echo -e "${RED}FAIL${NC} - Expected '$expected_value', got '$actual'"
                ((FAILED++))
                return 1
            fi
        else
            echo -e "${RED}FAIL${NC} - Field '$expected_field' not found in response"
            echo "Response: $response" | head -3
            ((FAILED++))
            return 1
        fi
    else
        # Just check if we got a valid response
        if [ -n "$response" ] && [ "$response" != "DNS resolution failure" ]; then
            echo -e "${GREEN}PASS${NC}"
            ((PASSED++))
            return 0
        else
            echo -e "${RED}FAIL${NC} - No response"
            ((FAILED++))
            return 1
        fi
    fi
}

echo "📊 1. Historical Data Collection Cron Worker"
echo "---------------------------------------------"
# Expected: { "status": "ok", "name": "Multi-Timeframe Historical Data Collection Worker", ... }
test_endpoint \
    "Root endpoint" \
    "${BASE_URL}-historical-collection-cron.${SUBDOMAIN}.workers.dev/" \
    "status" \
    "ok"

test_endpoint \
    "Worker name" \
    "${BASE_URL}-historical-collection-cron.${SUBDOMAIN}.workers.dev/" \
    "name" \
    "Multi-Timeframe Historical Data Collection Worker"

test_endpoint \
    "Parallel strategy" \
    "${BASE_URL}-historical-collection-cron.${SUBDOMAIN}.workers.dev/" \
    "parallel" \
    "All three collectors run simultaneously"

echo ""
echo "🔴 2. Real-Time Price Collection Worker"
echo "----------------------------------------"
# Expected: { "status": "ok", "name": "Real-Time Price Collection Worker", ... }
test_endpoint \
    "Root endpoint" \
    "${BASE_URL}-realtime-price-cron.${SUBDOMAIN}.workers.dev/" \
    "status" \
    "ok"

test_endpoint \
    "Worker name" \
    "${BASE_URL}-realtime-price-cron.${SUBDOMAIN}.workers.dev/" \
    "name" \
    "Real-Time Price Collection Worker"

test_endpoint \
    "Schedule" \
    "${BASE_URL}-realtime-price-cron.${SUBDOMAIN}.workers.dev/" \
    "schedule" \
    "Every minute"

echo ""
echo "📈 3. Technical Indicators Agent"
echo "---------------------------------"
# Expected: { "status": "ok", "name": "Technical Indicators Agent", ... }
test_endpoint \
    "Root endpoint" \
    "${BASE_URL}-technical-indicators.${SUBDOMAIN}.workers.dev/" \
    "status" \
    "ok"

test_endpoint \
    "Worker name" \
    "${BASE_URL}-technical-indicators.${SUBDOMAIN}.workers.dev/" \
    "name" \
    "Technical Indicators Agent"

echo ""
echo "🔔 4. Collection Alerts Agent"
echo "------------------------------"
# Expected: { "status": "ok", "name": "Collection Alerts Agent", ... }
test_endpoint \
    "Root endpoint" \
    "${BASE_URL}-collection-alerts.${SUBDOMAIN}.workers.dev/" \
    "status" \
    "ok"

test_endpoint \
    "Worker name" \
    "${BASE_URL}-collection-alerts.${SUBDOMAIN}.workers.dev/" \
    "name" \
    "Collection Alerts Agent"

echo ""
echo "📊 5. Data Collection Monitor Dashboard"
echo "----------------------------------------"
# Expected: HTML page with "Coinswarm Data Collection Monitor"
echo -n "Testing dashboard HTML... "
response=$(curl -s "${BASE_URL}-data-monitor.${SUBDOMAIN}.workers.dev/" 2>&1)

if echo "$response" | grep -q "Coinswarm Data Collection Monitor"; then
    echo -e "${GREEN}PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}FAIL${NC} - Expected HTML with dashboard title"
    ((FAILED++))
fi

echo -n "Testing dashboard API endpoint... "
response=$(curl -s "${BASE_URL}-data-monitor.${SUBDOMAIN}.workers.dev/api/stats" 2>&1)

if echo "$response" | jq -e ".totalTokens" >/dev/null 2>&1; then
    echo -e "${GREEN}PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}FAIL${NC} - Expected JSON with totalTokens field"
    ((FAILED++))
fi

echo ""
echo "================================"
echo "Test Results:"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All workers are deployed and responding correctly!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some workers are not deployed or not responding as expected${NC}"
    echo ""
    echo "To deploy missing workers:"
    echo "  git push origin claude/full-code-review-011CUvqUcjpgrh9x49XzAs2v"
    echo ""
    echo "Or manually deploy:"
    echo "  cd cloudflare-agents"
    echo "  wrangler deploy --config wrangler-<worker-name>.toml"
    exit 1
fi
