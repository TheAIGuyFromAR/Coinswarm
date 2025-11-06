#!/bin/bash
# Monitor evolution system progress
# Run: ./monitor-evolution.sh

echo "🔬 Monitoring Coinswarm Evolution System"
echo "========================================"
echo ""

while true; do
  timestamp=$(date "+%H:%M:%S")

  # Fetch stats
  response=$(curl -s https://coinswarm-evolution-agent.bamn86.workers.dev/stats)

  # Parse JSON
  cycles=$(echo $response | jq -r '.agentState.totalCycles')
  stateTrades=$(echo $response | jq -r '.agentState.totalTrades')
  dbTrades=$(echo $response | jq -r '.database.totalTrades')
  patterns=$(echo $response | jq -r '.database.totalPatterns')
  winners=$(echo $response | jq -r '.database.winningStrategies')
  lastCycle=$(echo $response | jq -r '.agentState.lastCycleAt')

  # Calculate actual cycles from database
  actualCycles=$((dbTrades / 50))

  # Clear previous line and print update
  echo -ne "\r[$timestamp] Cycles: $cycles/$actualCycles | Trades: $stateTrades/$dbTrades | Patterns: $patterns | Winners: $winners | Last: $lastCycle"

  # Check for pattern analysis (should happen at cycle 5, 10, 15, etc)
  if [ $actualCycles -ge 5 ] && [ $patterns -eq 0 ]; then
    echo ""
    echo "⚠️  WARNING: $actualCycles cycles completed but no patterns discovered yet!"
    echo "   Pattern analysis should trigger at cycles 5, 10, 15..."
  fi

  # Show top patterns if any exist
  if [ $patterns -gt 0 ]; then
    echo ""
    echo ""
    echo "📊 TOP PATTERNS:"
    echo $response | jq -r '.topPatterns[] | "  \(.name): ROI \(.annualized_roi_pct)%, Runs: \(.number_of_runs), Max: $\(.max_ending_value)"'
  fi

  sleep 10
done
