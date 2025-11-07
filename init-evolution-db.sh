#!/bin/bash
# Initialize D1 database with evolution schema

echo "🗄️  Initializing D1 database for evolution system..."

# Execute the schema
wrangler d1 execute coinswarm-evolution --file=cloudflare-d1-evolution-schema.sql

echo "✅ Database initialized!"
echo ""
echo "Now trigger the evolution cycle:"
echo "curl -X POST https://coinswarm-evolution-agent.bamn86.workers.dev/trigger"
