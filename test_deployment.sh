#!/bin/bash
# Quick deployment verification script

echo "=============================================="
echo "Testing Cloudflare Worker Deployment"
echo "=============================================="
echo ""

echo "1. Testing worker root endpoint..."
curl -s "https://swarm.bamn86.workers.dev/" | head -20
echo ""
echo ""

echo "2. Testing with BTC data (7 days)..."
curl -s "https://swarm.bamn86.workers.dev/data?symbol=BTC&days=7" | head -100
echo ""
echo ""

echo "3. Testing with 180 days (P0 requirement)..."
curl -s "https://swarm.bamn86.workers.dev/data?symbol=BTC&days=180" | head -50
echo ""
echo ""

echo "=============================================="
echo "If you see JSON data above, deployment worked!"
echo "If you see errors, check GitHub Actions logs"
echo "=============================================="
