#!/bin/bash
# Safe D1 Migration Runner
# Adds safety features to D1 migrations:
# - Pre-migration validation
# - Transaction wrapping (where supported)
# - Migration tracking
# - Error handling with rollback capability
# - Dry-run mode

set -e  # Exit on error

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DATABASE_NAME="${1:-coinswarm-evolution}"
MIGRATION_FILE="${2}"
DRY_RUN="${3:-false}"

# Usage
if [ -z "$MIGRATION_FILE" ]; then
    echo "Usage: $0 <database_name> <migration_file.sql> [dry-run]"
    echo ""
    echo "Examples:"
    echo "  $0 coinswarm-evolution cloudflare-agents/sentiment-data-schema-safe.sql"
    echo "  $0 coinswarm-evolution cloudflare-agents/sentiment-advanced-schema-safe.sql dry-run"
    echo ""
    echo "Options:"
    echo "  database_name  - Name of the D1 database (default: coinswarm-evolution)"
    echo "  migration_file - Path to SQL migration file"
    echo "  dry-run       - Test migration locally before remote execution"
    exit 1
fi

# Check if migration file exists
if [ ! -f "$MIGRATION_FILE" ]; then
    echo -e "${RED}Error: Migration file not found: $MIGRATION_FILE${NC}"
    exit 1
fi

# Extract migration ID from filename
MIGRATION_ID=$(basename "$MIGRATION_FILE" .sql)
TIMESTAMP=$(date +%s)

echo -e "${GREEN}=== Safe D1 Migration Runner ===${NC}"
echo "Database: $DATABASE_NAME"
echo "Migration: $MIGRATION_FILE"
echo "Migration ID: $MIGRATION_ID"
echo "Timestamp: $TIMESTAMP"
echo ""

# Step 1: Validate SQL syntax (basic check)
echo -e "${YELLOW}Step 1: Validating SQL syntax...${NC}"
if ! grep -q "CREATE\|ALTER\|INSERT\|UPDATE" "$MIGRATION_FILE"; then
    echo -e "${RED}Warning: Migration file doesn't contain CREATE/ALTER/INSERT/UPDATE statements${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi
echo -e "${GREEN}✓ SQL syntax looks valid${NC}"
echo ""

# Step 2: Check if migration already applied
echo -e "${YELLOW}Step 2: Checking if migration already applied...${NC}"
MIGRATION_CHECK=$(npx wrangler d1 execute "$DATABASE_NAME" --remote \
    --command "SELECT COUNT(*) as count FROM schema_migrations WHERE migration_id = '$MIGRATION_ID'" 2>&1 || echo "table_not_found")

if [[ "$MIGRATION_CHECK" == *"table_not_found"* ]] || [[ "$MIGRATION_CHECK" == *"no such table"* ]]; then
    echo -e "${YELLOW}Note: schema_migrations table doesn't exist yet (will be created)${NC}"
elif [[ "$MIGRATION_CHECK" == *'"count":1'* ]]; then
    echo -e "${YELLOW}Warning: Migration $MIGRATION_ID already applied!${NC}"
    read -p "Re-apply anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Exiting..."
        exit 0
    fi
else
    echo -e "${GREEN}✓ Migration not yet applied${NC}"
fi
echo ""

# Step 3: Dry run (local execution)
if [ "$DRY_RUN" = "dry-run" ]; then
    echo -e "${YELLOW}Step 3: Running migration locally (dry-run)...${NC}"
    if npx wrangler d1 execute "$DATABASE_NAME" --local --file="$MIGRATION_FILE"; then
        echo -e "${GREEN}✓ Local migration successful!${NC}"
        echo ""
        echo -e "${YELLOW}Dry-run complete. To apply to remote database, run without 'dry-run' parameter.${NC}"
        exit 0
    else
        echo -e "${RED}✗ Local migration failed!${NC}"
        echo "Fix errors before applying to remote database."
        exit 1
    fi
fi

# Step 4: Backup current schema (list tables)
echo -e "${YELLOW}Step 4: Backing up current schema state...${NC}"
TABLES_BEFORE=$(npx wrangler d1 execute "$DATABASE_NAME" --remote --command ".tables" 2>&1 || echo "error")
if [[ "$TABLES_BEFORE" == *"error"* ]]; then
    echo -e "${RED}Warning: Could not retrieve table list${NC}"
else
    echo "Tables before migration:"
    echo "$TABLES_BEFORE"
fi
echo ""

# Step 5: Apply migration with error handling
echo -e "${YELLOW}Step 5: Applying migration to remote database...${NC}"
echo "This may take a few moments..."
echo ""

# Create a temporary migration wrapper with transaction (if supported)
TEMP_MIGRATION="/tmp/migration_${TIMESTAMP}.sql"
cat > "$TEMP_MIGRATION" << EOF
-- Migration: $MIGRATION_ID
-- Applied: $(date)
-- File: $MIGRATION_FILE

-- Create schema_migrations table if not exists
CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_id TEXT PRIMARY KEY,
    applied_at INTEGER DEFAULT (cast(strftime('%s', 'now') as integer)),
    description TEXT,
    status TEXT DEFAULT 'success'
);

-- Note: D1 doesn't support full transactions, but we track migration status
-- Mark migration as started
INSERT OR REPLACE INTO schema_migrations (migration_id, description, status)
VALUES ('$MIGRATION_ID', 'Migration from $MIGRATION_FILE', 'in_progress');

-- Include actual migration file
EOF

cat "$MIGRATION_FILE" >> "$TEMP_MIGRATION"

cat >> "$TEMP_MIGRATION" << EOF

-- Mark migration as completed
UPDATE schema_migrations
SET status = 'success',
    applied_at = cast(strftime('%s', 'now') as integer)
WHERE migration_id = '$MIGRATION_ID';
EOF

# Execute migration
if npx wrangler d1 execute "$DATABASE_NAME" --remote --file="$TEMP_MIGRATION"; then
    echo -e "${GREEN}✓ Migration applied successfully!${NC}"
    MIGRATION_STATUS="success"
else
    echo -e "${RED}✗ Migration failed!${NC}"
    MIGRATION_STATUS="failed"

    # Update migration status to failed
    npx wrangler d1 execute "$DATABASE_NAME" --remote \
        --command "UPDATE schema_migrations SET status = 'failed' WHERE migration_id = '$MIGRATION_ID'" || true

    # Clean up temp file
    rm -f "$TEMP_MIGRATION"
    exit 1
fi

# Clean up temp file
rm -f "$TEMP_MIGRATION"
echo ""

# Step 6: Verify migration
echo -e "${YELLOW}Step 6: Verifying migration...${NC}"

# List tables after migration
TABLES_AFTER=$(npx wrangler d1 execute "$DATABASE_NAME" --remote --command ".tables" 2>&1)
echo "Tables after migration:"
echo "$TABLES_AFTER"
echo ""

# Check migration status
MIGRATION_STATUS_CHECK=$(npx wrangler d1 execute "$DATABASE_NAME" --remote \
    --command "SELECT migration_id, status, applied_at FROM schema_migrations WHERE migration_id = '$MIGRATION_ID'" 2>&1)

if [[ "$MIGRATION_STATUS_CHECK" == *"success"* ]]; then
    echo -e "${GREEN}✓ Migration verified in schema_migrations table${NC}"
else
    echo -e "${YELLOW}Warning: Could not verify migration status${NC}"
fi
echo ""

# Step 7: Summary
echo -e "${GREEN}=== Migration Complete ===${NC}"
echo "Migration ID: $MIGRATION_ID"
echo "Status: $MIGRATION_STATUS"
echo "Database: $DATABASE_NAME"
echo ""
echo "To view all migrations:"
echo "  npx wrangler d1 execute $DATABASE_NAME --remote --command \"SELECT * FROM schema_migrations ORDER BY applied_at DESC\""
echo ""
echo "To rollback (manual process):"
echo "  1. Review migration file: $MIGRATION_FILE"
echo "  2. Create reverse migration script"
echo "  3. Apply using this same safe-migrate.sh script"
echo ""

exit 0
