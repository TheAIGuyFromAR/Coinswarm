#!/bin/bash
# Cleanup script for old/broken workers
# This script deletes workers that should no longer exist

echo "🗑️  Cleaning up old workers..."

# Delete old cron worker (replaced by queue system)
echo "Deleting: coinswarm-historical-collection-cron"
wrangler delete coinswarm-historical-collection-cron --force || echo "Already deleted or doesn't exist"

# Delete broken KV worker (no KV namespace configured)
echo "Deleting: coinswarm-historical-data"
wrangler delete coinswarm-historical-data --force || echo "Already deleted or doesn't exist"

echo "✅ Cleanup complete"
