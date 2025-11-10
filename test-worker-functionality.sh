#!/bin/bash
# Comprehensive Worker Functionality Test Script
# Tests actual outputs against expected values over time

set -e

echo "========================================="
echo "Historical Data Collection System Tests"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS_COUNT=0
FAIL_COUNT=0

function test_endpoint() {
    local test_name="$1"
    local url="$2"
    local expected_field="$3"
    local expected_value="$4"

    echo -n "Testing: $test_name... "

    response=$(curl -s "$url" 2>&1)

    if echo "$response" | jq -e ".$expected_field" >/dev/null 2>&1; then
        actual=$(echo "$response" | jq -r ".$expected_field")
        if [ "$actual" == "$expected_value" ]; then
            echo -e "${GREEN}PASS${NC}"
            ((PASS_COUNT++))
            return 0
        else
            echo -e "${RED}FAIL${NC} - Expected: $expected_value, Got: $actual"
            ((FAIL_COUNT++))
            return 1
        fi
    else
        echo -e "${RED}FAIL${NC} - Field '$expected_field' not found in response"
        echo "Response: $response"
        ((FAIL_COUNT++))
        return 1
    fi
}

function test_endpoint_structure() {
    local test_name="$1"
    local url="$2"
    local required_fields="$3"

    echo -n "Testing structure: $test_name... "

    response=$(curl -s "$url" 2>&1)

    all_present=true
    missing_fields=""

    IFS=',' read -ra FIELDS <<< "$required_fields"
    for field in "${FIELDS[@]}"; do
        if ! echo "$response" | jq -e ".$field" >/dev/null 2>&1; then
            all_present=false
            missing_fields="$missing_fields $field"
        fi
    done

    if $all_present; then
        echo -e "${GREEN}PASS${NC}"
        ((PASS_COUNT++))
        return 0
    else
        echo -e "${RED}FAIL${NC} - Missing fields:$missing_fields"
        echo "Response: $response"
        ((FAIL_COUNT++))
        return 1
    fi
}

function test_data_collection() {
    echo "========================================="
    echo "1. Testing Historical Data Worker"
    echo "========================================="

    test_endpoint \
        "Historical Data Worker - Status" \
        "https://coinswarm-historical-data.bamn86.workers.dev/" \
        "status" \
        "ok"

    test_endpoint_structure \
        "Historical Data Worker - API Info Structure" \
        "https://coinswarm-historical-data.bamn86.workers.dev/" \
        "status,name,endpoints,features,pairs"

    echo ""
    echo "Testing /fetch-fresh endpoint..."
    response=$(curl -s "https://coinswarm-historical-data.bamn86.workers.dev/fetch-fresh?symbol=BTCUSDT&interval=5m&limit=10")

    if echo "$response" | jq -e '.success' >/dev/null 2>&1; then
        success=$(echo "$response" | jq -r '.success')
        candle_count=$(echo "$response" | jq -r '.candleCount')
        source=$(echo "$response" | jq -r '.source')

        if [ "$success" == "true" ]; then
            echo -e "${GREEN}PASS${NC} - Fetched $candle_count candles from $source"
            ((PASS_COUNT++))

            # Verify candle structure
            if echo "$response" | jq -e '.candles[0] | .timestamp, .open, .high, .low, .close, .volume' >/dev/null 2>&1; then
                echo -e "${GREEN}PASS${NC} - Candle structure is correct"
                ((PASS_COUNT++))

                # Verify OHLCV data integrity
                high=$(echo "$response" | jq -r '.candles[0].high')
                low=$(echo "$response" | jq -r '.candles[0].low')
                open=$(echo "$response" | jq -r '.candles[0].open')
                close=$(echo "$response" | jq -r '.candles[0].close')

                if (( $(echo "$high >= $low" | bc -l) )) && \
                   (( $(echo "$high >= $open" | bc -l) )) && \
                   (( $(echo "$high >= $close" | bc -l) )); then
                    echo -e "${GREEN}PASS${NC} - OHLCV data integrity check (high >= low, open, close)"
                    ((PASS_COUNT++))
                else
                    echo -e "${RED}FAIL${NC} - OHLCV data integrity violated"
                    echo "High: $high, Low: $low, Open: $open, Close: $close"
                    ((FAIL_COUNT++))
                fi
            else
                echo -e "${RED}FAIL${NC} - Candle structure is incomplete"
                ((FAIL_COUNT++))
            fi
        else
            echo -e "${RED}FAIL${NC} - Success field is false"
            ((FAIL_COUNT++))
        fi
    else
        echo -e "${RED}FAIL${NC} - Invalid response from /fetch-fresh"
        echo "Response: $response"
        ((FAIL_COUNT++))
    fi

    echo ""
    echo "Testing /pairs endpoint (KV namespace test)..."
    response=$(curl -s "https://coinswarm-historical-data.bamn86.workers.dev/pairs")

    if echo "$response" | jq -e '.success' >/dev/null 2>&1; then
        success=$(echo "$response" | jq -r '.success')
        if [ "$success" == "false" ]; then
            error=$(echo "$response" | jq -r '.error')
            echo -e "${YELLOW}EXPECTED FAIL${NC} - KV namespace not configured: $error"
            echo "This confirms audit finding #7"
        else
            echo -e "${GREEN}PASS${NC} - /pairs endpoint working"
            ((PASS_COUNT++))
        fi
    fi
}

function test_collection_cron() {
    echo ""
    echo "========================================="
    echo "2. Testing Historical Collection Cron"
    echo "========================================="

    test_endpoint \
        "Collection Cron - Status" \
        "https://coinswarm-historical-collection-cron.bamn86.workers.dev/" \
        "status" \
        "ok"

    echo ""
    echo "Testing collection progress..."
    response=$(curl -s "https://coinswarm-historical-collection-cron.bamn86.workers.dev/status")

    total_tokens=$(echo "$response" | jq -r '.totalTokens')
    tokens_array_length=$(echo "$response" | jq -r '.tokens | length')

    echo "Total tokens configured: $total_tokens"
    echo "Tokens in database: $tokens_array_length"

    if [ "$tokens_array_length" == "0" ]; then
        echo -e "${RED}CRITICAL ISSUE${NC} - No tokens in database!"
        echo "This means data collection has NOT started."
        echo "Expected: 15 tokens (BTCUSDT, ETHUSDT, SOLUSDT, etc.)"
        echo "Actual: 0 tokens"
        ((FAIL_COUNT++))
    elif [ "$tokens_array_length" == "$total_tokens" ]; then
        echo -e "${GREEN}PASS${NC} - All tokens initialized in database"
        ((PASS_COUNT++))

        # Check collection progress
        minutes_collected=$(echo "$response" | jq -r '.tokens[0].minutes_collected // 0')
        days_collected=$(echo "$response" | jq -r '.tokens[0].days_collected // 0')
        hours_collected=$(echo "$response" | jq -r '.tokens[0].hours_collected // 0')

        echo "Sample token progress:"
        echo "  Minutes: $minutes_collected"
        echo "  Hours: $hours_collected"
        echo "  Days: $days_collected"

        if [ "$minutes_collected" -gt "0" ] || [ "$hours_collected" -gt "0" ] || [ "$days_collected" -gt "0" ]; then
            echo -e "${GREEN}PASS${NC} - Data collection is active"
            ((PASS_COUNT++))
        else
            echo -e "${YELLOW}WARNING${NC} - Tokens initialized but no data collected yet"
            echo "Collection cron may not have run yet (runs hourly)"
        fi
    else
        echo -e "${YELLOW}WARNING${NC} - Partial initialization ($tokens_array_length / $total_tokens)"
        ((FAIL_COUNT++))
    fi
}

function test_technical_indicators() {
    echo ""
    echo "========================================="
    echo "3. Testing Technical Indicators Worker"
    echo "========================================="

    test_endpoint \
        "Technical Indicators - Status" \
        "https://coinswarm-technical-indicators.bamn86.workers.dev/" \
        "status" \
        "ok"

    test_endpoint_structure \
        "Technical Indicators - API Structure" \
        "https://coinswarm-technical-indicators.bamn86.workers.dev/" \
        "status,name,endpoints,indicators"
}

function test_collection_alerts() {
    echo ""
    echo "========================================="
    echo "4. Testing Collection Alerts Worker"
    echo "========================================="

    test_endpoint \
        "Collection Alerts - Status" \
        "https://coinswarm-collection-alerts.bamn86.workers.dev/" \
        "status" \
        "ok"

    echo ""
    echo "Testing alerts endpoint..."
    response=$(curl -s "https://coinswarm-collection-alerts.bamn86.workers.dev/alerts")

    if echo "$response" | jq -e '.success' >/dev/null 2>&1; then
        success=$(echo "$response" | jq -r '.success')
        if [ "$success" == "true" ]; then
            alerts_count=$(echo "$response" | jq -r '.alerts | length')
            echo -e "${GREEN}PASS${NC} - Alerts endpoint working ($alerts_count alerts)"
            ((PASS_COUNT++))
        else
            echo -e "${RED}FAIL${NC} - Alerts endpoint returned success=false"
            ((FAIL_COUNT++))
        fi
    else
        echo -e "${RED}FAIL${NC} - Invalid alerts response"
        ((FAIL_COUNT++))
    fi
}

function test_data_monitor() {
    echo ""
    echo "========================================="
    echo "5. Testing Data Monitor Dashboard"
    echo "========================================="

    echo -n "Testing dashboard accessibility... "
    response=$(curl -s "https://coinswarm-data-monitor.bamn86.workers.dev/" 2>&1)

    if echo "$response" | grep -q "error code: 1101"; then
        echo -e "${RED}FAIL${NC} - Dashboard returns error 1101"
        echo "This confirms audit finding - dashboard not properly deployed"
        ((FAIL_COUNT++))
    elif echo "$response" | grep -q "<html\|<!DOCTYPE"; then
        echo -e "${GREEN}PASS${NC} - Dashboard HTML returned"
        ((PASS_COUNT++))
    else
        echo -e "${YELLOW}UNKNOWN${NC} - Unexpected response"
        echo "Response: $response"
    fi
}

function test_over_time() {
    echo ""
    echo "========================================="
    echo "6. Time-Series Testing (3 samples)"
    echo "========================================="

    for i in 1 2 3; do
        echo ""
        echo "Sample $i ($(date)):"

        response=$(curl -s "https://coinswarm-historical-data.bamn86.workers.dev/fetch-fresh?symbol=BTCUSDT&interval=5m&limit=1")

        if echo "$response" | jq -e '.success' >/dev/null 2>&1; then
            timestamp=$(echo "$response" | jq -r '.candles[0].timestamp')
            close=$(echo "$response" | jq -r '.candles[0].close')
            source=$(echo "$response" | jq -r '.source')

            echo "  Timestamp: $timestamp"
            echo "  BTC Close: \$$close"
            echo "  Source: $source"

            # Verify timestamp is reasonable (not in future, not too old)
            current_time=$(date +%s)000  # milliseconds
            if (( timestamp <= current_time )) && (( timestamp > current_time - 86400000 )); then
                echo -e "  ${GREEN}✓${NC} Timestamp is reasonable"
            else
                echo -e "  ${RED}✗${NC} Timestamp seems invalid (current: $current_time, data: $timestamp)"
            fi

            # Verify price is reasonable for BTC
            if (( $(echo "$close > 10000" | bc -l) )) && (( $(echo "$close < 200000" | bc -l) )); then
                echo -e "  ${GREEN}✓${NC} Price is in reasonable range"
                ((PASS_COUNT++))
            else
                echo -e "  ${RED}✗${NC} Price seems unrealistic: \$$close"
                ((FAIL_COUNT++))
            fi
        else
            echo -e "  ${RED}✗${NC} Failed to fetch data"
            ((FAIL_COUNT++))
        fi

        if [ $i -lt 3 ]; then
            echo "  Waiting 5 seconds..."
            sleep 5
        fi
    done
}

# Run all tests
test_data_collection
test_collection_cron
test_technical_indicators
test_collection_alerts
test_data_monitor
test_over_time

# Summary
echo ""
echo "========================================="
echo "Test Summary"
echo "========================================="
echo -e "${GREEN}Passed: $PASS_COUNT${NC}"
echo -e "${RED}Failed: $FAIL_COUNT${NC}"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. See details above.${NC}"
    exit 1
fi
