# Database Migration Guide

**Date:** November 8, 2025
**Version:** 2.0 (Phase 2 - Database Safety)
**Status:** Safe migration procedures implemented

---

## Quick Start

### Run a Safe Migration

```bash
# Dry-run first (test locally)
./scripts/safe-migrate.sh coinswarm-evolution cloudflare-agents/sentiment-data-schema-safe.sql dry-run

# Apply to remote database
./scripts/safe-migrate.sh coinswarm-evolution cloudflare-agents/sentiment-data-schema-safe.sql
```

---

## Migration Safety Features

### What the Safe Migration Runner Does

1. **Pre-migration Validation**
   - Checks if migration file exists
   - Validates basic SQL syntax
   - Checks if migration already applied

2. **Migration Tracking**
   - Creates `schema_migrations` table automatically
   - Records migration ID, timestamp, status
   - Prevents duplicate migrations

3. **Dry-run Mode**
   - Tests migration locally before remote execution
   - Identifies errors safely
   - No risk to production database

4. **Error Handling**
   - Captures and reports errors clearly
   - Marks failed migrations in database
   - Provides rollback guidance

5. **Verification**
   - Lists tables before and after migration
   - Confirms migration status
   - Provides verification commands

---

## Migration File Order

### For Fresh D1 Database (Recommended Order)

```bash
# 1. Core tables
./scripts/safe-migrate.sh coinswarm-evolution cloudflare-d1-schema.sql
./scripts/safe-migrate.sh coinswarm-evolution cloudflare-d1-evolution-schema.sql
./scripts/safe-migrate.sh coinswarm-evolution fix-state-persistence.sql

# 2. Technical indicators (adds 80+ columns to chaos_trades)
./scripts/safe-migrate.sh coinswarm-evolution cloudflare-agents/d1-schema-technical-indicators.sql

# 3. Agent schemas
./scripts/safe-migrate.sh coinswarm-evolution cloudflare-agents/reasoning-agent-schema.sql
./scripts/safe-migrate.sh coinswarm-evolution cloudflare-agents/cross-agent-learning-schema.sql

# 4. Sentiment data (SAFE versions with INT timestamps)
./scripts/safe-migrate.sh coinswarm-evolution cloudflare-agents/sentiment-data-schema-safe.sql
./scripts/safe-migrate.sh coinswarm-evolution cloudflare-agents/sentiment-advanced-schema-safe.sql

# 5. Competition features
./scripts/safe-migrate.sh coinswarm-evolution cloudflare-d1-competition-migration.sql

# 6. Pattern weighting
./scripts/safe-migrate.sh coinswarm-evolution cloudflare-agents/pattern-recency-weighting.sql
```

### For Existing Database (Incremental Updates)

```bash
# Only apply new migrations
./scripts/safe-migrate.sh coinswarm-evolution cloudflare-agents/sentiment-data-schema-safe.sql

# Check which migrations are applied
npx wrangler d1 execute coinswarm-evolution --remote \
  --command "SELECT * FROM schema_migrations ORDER BY applied_at DESC LIMIT 10"
```

---

## Checking Migration Status

### View Applied Migrations

```bash
# List all migrations
npx wrangler d1 execute coinswarm-evolution --remote \
  --command "SELECT migration_id, status, datetime(applied_at, 'unixepoch') as applied_date FROM schema_migrations ORDER BY applied_at DESC"

# Check specific migration
npx wrangler d1 execute coinswarm-evolution --remote \
  --command "SELECT * FROM schema_migrations WHERE migration_id = 'sentiment-data-schema-safe-2025-11-08'"

# Count successful migrations
npx wrangler d1 execute coinswarm-evolution --remote \
  --command "SELECT COUNT(*) as total_migrations FROM schema_migrations WHERE status = 'success'"
```

### Verify Tables Exist

```bash
# List all tables
npx wrangler d1 execute coinswarm-evolution --remote --command ".tables"

# Check if specific table exists
npx wrangler d1 execute coinswarm-evolution --remote \
  --command "SELECT name FROM sqlite_master WHERE type='table' AND name='chaos_trades'"

# Count rows in a table
npx wrangler d1 execute coinswarm-evolution --remote \
  --command "SELECT COUNT(*) as row_count FROM chaos_trades"
```

---

## Troubleshooting

### Error: "duplicate column name"

**Cause:** Column already exists from previous migration
**Solution:** This is expected if you're re-applying a migration. The error can be ignored, or use the safe schema versions which handle this gracefully.

```bash
# Check if column exists
npx wrangler d1 execute coinswarm-evolution --remote \
  --command "SELECT sql FROM sqlite_master WHERE type='table' AND name='chaos_trades'"
```

### Error: "no such table: schema_migrations"

**Cause:** First migration, table doesn't exist yet
**Solution:** The safe-migrate.sh script creates it automatically. This is normal on first run.

### Error: "syntax error near..."

**Cause:** SQL syntax incompatible with SQLite/D1
**Solution:** Check DATABASE_SCHEMA_WARNING.md for D1-compatible syntax

Common fixes:
- `TIMESTAMPTZ` → `INTEGER` (unix timestamp)
- `UUID` → `TEXT`
- `JSONB` → `TEXT`
- `NOW()` → `CURRENT_TIMESTAMP` or `datetime('now')`

### Migration Stuck "in_progress"

**Cause:** Migration failed partway through
**Solution:**

```bash
# Check status
npx wrangler d1 execute coinswarm-evolution --remote \
  --command "SELECT * FROM schema_migrations WHERE status = 'in_progress'"

# Manual fix: Mark as failed
npx wrangler d1 execute coinswarm-evolution --remote \
  --command "UPDATE schema_migrations SET status = 'failed' WHERE migration_id = 'your-migration-id'"

# Then re-run migration
./scripts/safe-migrate.sh coinswarm-evolution your-migration-file.sql
```

---

## Manual Migration (Without Script)

If you need to run migrations manually without the safety script:

```bash
# Basic execution
npx wrangler d1 execute coinswarm-evolution --remote --file=migration.sql

# With local testing first
npx wrangler d1 execute coinswarm-evolution --local --file=migration.sql

# Direct SQL command
npx wrangler d1 execute coinswarm-evolution --remote --command "SELECT * FROM chaos_trades LIMIT 5"
```

**⚠️ Warning:** Manual migrations don't include:
- Pre-validation
- Migration tracking
- Error handling
- Rollback capability

Use the safe-migrate.sh script whenever possible.

---

## Rollback Procedure

D1 doesn't support automatic rollback. Manual process:

### Step 1: Identify What Changed

```bash
# View migration file
cat cloudflare-agents/sentiment-data-schema-safe.sql

# Check what columns were added
npx wrangler d1 execute coinswarm-evolution --remote \
  --command "PRAGMA table_info(chaos_trades)"
```

### Step 2: Create Reverse Migration

```sql
-- reverse-migration.sql
-- Removes columns added by sentiment-data-schema-safe.sql

-- SQLite doesn't support DROP COLUMN directly
-- Two options:

-- Option A: Leave columns (safe, recommended)
-- Do nothing, columns with NULL values don't hurt

-- Option B: Recreate table without columns (risky)
-- 1. Create new table with desired schema
-- 2. Copy data from old table
-- 3. Drop old table
-- 4. Rename new table

-- For most cases, Option A is safer
-- Just mark migration as rolled back
UPDATE schema_migrations
SET status = 'rolled_back', description = description || ' [ROLLED BACK]'
WHERE migration_id = 'sentiment-data-schema-safe-2025-11-08';
```

### Step 3: Apply Reverse Migration

```bash
./scripts/safe-migrate.sh coinswarm-evolution reverse-migration.sql
```

---

## Best Practices

### DO ✅

- **Always dry-run first** - Test locally before remote
- **Use safe-migrate.sh** - Built-in safety features
- **Track migrations** - Use schema_migrations table
- **Test incrementally** - One migration at a time
- **Backup data** - Export critical data before major migrations
- **Use INTEGER timestamps** - Better performance than TEXT
- **Add CHECK constraints** - Validate data at database level
- **Create indexes** - Add indexes on foreign keys and common queries
- **Version your schemas** - Include date/version in migration_id

### DON'T ❌

- **Run untested migrations** - Always dry-run first
- **Skip validation** - Check migration status before applying
- **Use PostgreSQL syntax** - Only D1/SQLite compatible SQL
- **Run migrations in parallel** - One at a time, in order
- **Ignore errors** - Fix errors before proceeding
- **Use TEXT timestamps** - Use INTEGER for better performance
- **Skip indexes** - Performance will suffer
- **Forget to track** - Always record in schema_migrations

---

## Migration Checklist

Before applying a migration:

- [ ] Read migration file and understand changes
- [ ] Check if migration already applied
- [ ] Test with dry-run mode locally
- [ ] Verify no syntax errors
- [ ] Ensure database has space for new data
- [ ] Have rollback plan ready
- [ ] Notify team (if applicable)

After applying a migration:

- [ ] Verify migration in schema_migrations table
- [ ] Check tables were created/modified
- [ ] Test queries against new schema
- [ ] Monitor for errors in logs
- [ ] Update documentation
- [ ] Verify application still works

---

## Viewing Schema Information

### Table Structure

```bash
# View table schema
npx wrangler d1 execute coinswarm-evolution --remote \
  --command "SELECT sql FROM sqlite_master WHERE type='table' AND name='chaos_trades'"

# List all columns in a table
npx wrangler d1 execute coinswarm-evolution --remote \
  --command "PRAGMA table_info(chaos_trades)"

# View indexes on a table
npx wrangler d1 execute coinswarm-evolution --remote \
  --command "SELECT * FROM sqlite_master WHERE type='index' AND tbl_name='chaos_trades'"
```

### Database Statistics

```bash
# Count all tables
npx wrangler d1 execute coinswarm-evolution --remote \
  --command "SELECT COUNT(*) as table_count FROM sqlite_master WHERE type='table'"

# Get row counts for all tables
npx wrangler d1 execute coinswarm-evolution --remote \
  --command "
    SELECT
      name as table_name,
      (SELECT COUNT(*) FROM \` || name || '\`) as row_count
    FROM sqlite_master
    WHERE type='table'
    ORDER BY row_count DESC"
```

---

## Emergency Procedures

### Database Corrupted

If migrations cause critical errors:

1. **Create new database**
   ```bash
   npx wrangler d1 create coinswarm-evolution-backup
   ```

2. **Update wrangler configs** with new database_id

3. **Apply clean migrations** to new database

4. **Migrate data** from old database (if possible)

### Can't Access Database

1. **Check database exists**
   ```bash
   npx wrangler d1 list
   ```

2. **Check wrangler auth**
   ```bash
   npx wrangler whoami
   ```

3. **Verify database_id** in wrangler.toml matches

---

## Support

**For migration issues:**
1. Check DATABASE_SCHEMA_WARNING.md for D1 compatibility
2. Review migration file for syntax errors
3. Test locally with --local flag
4. Check schema_migrations table for status

**For schema design:**
1. See CODE_REVIEW_REPORT_2025_11_08.md (Database section)
2. Review existing schemas as examples
3. Test with sample data locally

---

**Last Updated:** November 8, 2025
**Migration Script:** scripts/safe-migrate.sh
**Schema Versions:** See schema_migrations table in database
