#!/bin/bash

# Deploy Free Agents SDK Evolution System to Cloudflare
# Run this script to deploy: chmod +x deploy-agent.sh && ./deploy-agent.sh

set -e

echo "🚀 Deploying Coinswarm Evolution Agent (Free Tier)"
echo ""

# Check if wrangler is installed
if ! command -v wrangler &> /dev/null; then
    echo "❌ wrangler not found. Installing..."
    npm install -g wrangler
fi

# Check if logged in
echo "📋 Checking Cloudflare authentication..."
if ! wrangler whoami &> /dev/null; then
    echo "❌ Not logged in to Cloudflare"
    echo "Please run: wrangler login"
    exit 1
fi

echo "✅ Authenticated"
echo ""

# Change to cloudflare-agents directory
cd "$(dirname "$0")/cloudflare-agents"

# Check if D1 database exists
echo "🔍 Checking for D1 database..."
DB_EXISTS=$(wrangler d1 list | grep -c "coinswarm-evolution" || true)

if [ "$DB_EXISTS" -eq 0 ]; then
    echo "📦 Creating D1 database..."
    DB_OUTPUT=$(wrangler d1 create coinswarm-evolution)
    echo "$DB_OUTPUT"

    # Extract database_id from output
    DB_ID=$(echo "$DB_OUTPUT" | grep "database_id" | sed 's/.*= "\(.*\)"/\1/')

    if [ -z "$DB_ID" ]; then
        echo "❌ Failed to create database. Please create manually:"
        echo "   wrangler d1 create coinswarm-evolution"
        exit 1
    fi

    echo "✅ Database created: $DB_ID"

    # Update wrangler.toml with database_id
    echo "📝 Updating wrangler.toml..."
    sed -i.bak "s/YOUR_DATABASE_ID_HERE/$DB_ID/" wrangler.toml
    rm wrangler.toml.bak

    # Initialize schema
    echo "📊 Initializing database schema..."
    wrangler d1 execute coinswarm-evolution --file=../cloudflare-d1-evolution-schema.sql
    echo "✅ Schema initialized"
else
    echo "✅ Database already exists"

    # Check if wrangler.toml has placeholder
    if grep -q "YOUR_DATABASE_ID_HERE" wrangler.toml; then
        echo "⚠️  wrangler.toml still has placeholder database_id"
        echo "Please run: wrangler d1 list"
        echo "And update database_id in wrangler.toml"
        exit 1
    fi
fi

echo ""

# Install dependencies
echo "📦 Installing dependencies..."
npm install
echo "✅ Dependencies installed"
echo ""

# Deploy
echo "🚀 Deploying agent to Cloudflare..."
npm run deploy

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📍 Your agent is now running at:"
echo "   https://coinswarm-evolution-agent.YOUR-ACCOUNT.workers.dev"
echo ""
echo "🎯 Trigger the first cycle:"
echo "   curl -X POST https://coinswarm-evolution-agent.YOUR-ACCOUNT.workers.dev/trigger"
echo ""
echo "📊 Check status:"
echo "   curl https://coinswarm-evolution-agent.YOUR-ACCOUNT.workers.dev/status"
echo ""
echo "🎉 Evolution system is now running!"
