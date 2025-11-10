# ⚠️ CRITICAL: PostgreSQL vs D1 Database Schema Separation

**Date:** November 8, 2025
**Status:** DOCUMENTATION REQUIRED
**Impact:** CRITICAL - Using wrong schema will cause complete deployment failure

---

## 🔴 DO NOT USE WITH CLOUDFLARE D1

The following schema files are **PostgreSQL-ONLY** and will **FAIL** on Cloudflare D1:

### 1. `/scripts/init-db.sql` ❌ INCOMPATIBLE WITH D1

**Size:** 6.5 KB
**Purpose:** Initial database setup for PostgreSQL
**Deployment Target:** Local development or PostgreSQL server ONLY

**Why it fails on D1:**
```sql
-- Line 7-8: PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- D1 ERROR: Extensions not supported
CREATE EXTENSION IF NOT EXISTS "pg_trgm";    -- D1 ERROR: Extensions not supported

-- Lines 14+: PostgreSQL-specific types
id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),  -- D1 ERROR: UUID type not supported
created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),  -- D1 ERROR: TIMESTAMPTZ not supported
conditions JSONB NOT NULL,                       -- D1 ERROR: JSONB not supported, use TEXT
pattern_ids TEXT[],                              -- D1 ERROR: Arrays not supported
history BYTEA,                                   -- D1 ERROR: BYTEA not supported

-- Lines 219-234: Triggers and functions
CREATE OR REPLACE FUNCTION update_updated_at_column()  -- D1 ERROR: Functions not supported
RETURNS TRIGGER AS $$...$$;                           -- D1 ERROR: Triggers not supported
```

**If you run this on D1, you will get:**
- `D1_ERROR: near "EXTENSION": syntax error`
- `D1_ERROR: unknown type: UUID`
- Complete deployment failure

---

### 2. `/scripts/add-historical-prices-table.sql` ❌ PARTIALLY INCOMPATIBLE

**Size:** 2.0 KB
**Purpose:** Add historical prices table with advanced PostgreSQL features
**Deployment Target:** PostgreSQL ONLY

**PostgreSQL-specific features:**
```sql
-- Line 2: PostgreSQL data types
id UUID DEFAULT uuid_generate_v4(),      -- D1 ERROR: UUID not supported
timestamp TIMESTAMPTZ NOT NULL,          -- D1 ERROR: TIMESTAMPTZ not supported

-- Line 51: PostgreSQL-specific query syntax
SELECT DISTINCT ON (symbol, interval)    -- D1 ERROR: DISTINCT ON not supported
  symbol, interval, timestamp, close
FROM historical_prices
ORDER BY symbol, interval, timestamp DESC;

-- Lines 69-70: PostgreSQL aggregate functions
SELECT array_agg(DISTINCT exchange)      -- D1 ERROR: array_agg not supported
FROM historical_prices;
```

---

## ✅ USE THESE SCHEMAS WITH CLOUDFLARE D1

The following schemas are **D1-COMPATIBLE** and safe to use:

### Core Schemas (D1-Compatible)

| File | Size | Purpose | Status |
|------|------|---------|--------|
| `cloudflare-d1-schema.sql` | 1.4 KB | Historical price data | ✅ Safe |
| `cloudflare-d1-evolution-schema.sql` | 1.5 KB | Evolution system core | ✅ Safe |
| `cloudflare-d1-competition-migration.sql` | 2.8 KB | Agent competition | ⚠️ ALTER heavy |
| `fix-state-persistence.sql` | 0.2 KB | System state table | ✅ Safe |

### Agent Schemas (D1-Compatible)

| File | Size | Purpose | Status |
|------|------|---------|--------|
| `cloudflare-agents/d1-schema-technical-indicators.sql` | 4.7 KB | Technical indicators | ✅ Safe |
| `cloudflare-agents/reasoning-agent-schema.sql` | 6.8 KB | Reasoning agents | ✅ Safe |
| `cloudflare-agents/sentiment-data-schema.sql` | 7.2 KB | Sentiment data | ⚠️ ALTER heavy |
| `cloudflare-agents/sentiment-advanced-schema.sql` | 8.2 KB | Advanced sentiment | ⚠️ ALTER heavy |
| `cloudflare-agents/cross-agent-learning-schema.sql` | 8.2 KB | Cross-agent learning | ✅ Safe |
| `cloudflare-agents/pattern-recency-weighting.sql` | 4.0 KB | Pattern weighting | ⚠️ ALTER heavy |

---

## 🔄 Data Type Compatibility Matrix

| PostgreSQL Type | D1/SQLite Equivalent | Migration Strategy |
|----------------|---------------------|-------------------|
| `UUID` | `TEXT` | Generate UUID in app code, store as TEXT |
| `TIMESTAMPTZ` | `INTEGER` or `TEXT` | Use unix timestamp (INT) or ISO 8601 (TEXT) |
| `JSONB` | `TEXT` | Store as JSON string, parse in app |
| `TEXT[]` | `TEXT` | Store JSON array: `'["a","b","c"]'` |
| `BYTEA` | `BLOB` or `TEXT` | Use BLOB or base64-encoded TEXT |
| `DECIMAL(10,2)` | `REAL` | ⚠️ May lose precision |
| `SERIAL` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Direct replacement |
| `NOW()` | `CURRENT_TIMESTAMP` or `datetime('now')` | Use SQLite functions |
| `ARRAY_AGG()` | `GROUP_CONCAT()` | Different syntax, same result |
| `DISTINCT ON` | `GROUP BY` + subquery | Rewrite query logic |

---

## 📋 Migration Strategy

### For New Deployments (Fresh D1 Database)

**Step 1:** Run D1-compatible schemas in this order:
```bash
# Core tables first
wrangler d1 execute coinswarm-evolution --remote --file=cloudflare-d1-schema.sql
wrangler d1 execute coinswarm-evolution --remote --file=cloudflare-d1-evolution-schema.sql
wrangler d1 execute coinswarm-evolution --remote --file=fix-state-persistence.sql

# Agent schemas
wrangler d1 execute coinswarm-evolution --remote --file=cloudflare-agents/d1-schema-technical-indicators.sql
wrangler d1 execute coinswarm-evolution --remote --file=cloudflare-agents/reasoning-agent-schema.sql
wrangler d1 execute coinswarm-evolution --remote --file=cloudflare-agents/cross-agent-learning-schema.sql

# Migrations (with ALTER TABLE - apply carefully)
wrangler d1 execute coinswarm-evolution --remote --file=cloudflare-d1-competition-migration.sql
wrangler d1 execute coinswarm-evolution --remote --file=cloudflare-agents/sentiment-data-schema.sql
wrangler d1 execute coinswarm-evolution --remote --file=cloudflare-agents/sentiment-advanced-schema.sql
wrangler d1 execute coinswarm-evolution --remote --file=cloudflare-agents/pattern-recency-weighting.sql
```

**Step 2:** Verify tables were created:
```bash
wrangler d1 execute coinswarm-evolution --remote --command ".tables"
```

### For Local Development (PostgreSQL)

**Step 1:** Run PostgreSQL schemas:
```bash
# Only for PostgreSQL!
psql -d coinswarm -f scripts/init-db.sql
psql -d coinswarm -f scripts/add-historical-prices-table.sql
```

**Step 2:** Keep PostgreSQL and D1 schemas synchronized manually

---

## 🚨 Common Errors and Solutions

### Error: `near "EXTENSION": syntax error`
**Cause:** Trying to run PostgreSQL schema on D1
**Solution:** Use D1-compatible schema instead

### Error: `no such column: uuid_generate_v4`
**Cause:** PostgreSQL UUID function called in D1
**Solution:** Generate UUIDs in application code:
```javascript
const id = crypto.randomUUID(); // Modern JavaScript
// or
const id = `${Date.now()}-${Math.random().toString(36)}`;
```

### Error: `unknown type: TIMESTAMPTZ`
**Cause:** PostgreSQL timestamp type not supported
**Solution:** Use INTEGER for unix timestamps:
```sql
-- Before (PostgreSQL):
created_at TIMESTAMPTZ DEFAULT NOW()

-- After (D1):
created_at INTEGER DEFAULT (cast(strftime('%s', 'now') as integer))
```

### Error: `DISTINCT ON not supported`
**Cause:** PostgreSQL-specific syntax
**Solution:** Rewrite with GROUP BY:
```sql
-- Before (PostgreSQL):
SELECT DISTINCT ON (symbol, interval)
  symbol, interval, timestamp, close
FROM historical_prices
ORDER BY symbol, interval, timestamp DESC;

-- After (D1):
SELECT symbol, interval, timestamp, close
FROM historical_prices
WHERE (symbol, interval, timestamp) IN (
  SELECT symbol, interval, MAX(timestamp)
  FROM historical_prices
  GROUP BY symbol, interval
);
```

---

## 📊 Schema File Decision Tree

```
Are you deploying to Cloudflare Workers?
│
├─ YES → Use cloudflare-d1-*.sql files
│   ├─ New database? → Run all D1 schemas in order
│   └─ Existing database? → Run only new migrations
│
└─ NO (Local development)
    ├─ Using PostgreSQL? → Use scripts/init-db.sql
    ├─ Using SQLite locally? → Use cloudflare-d1-*.sql files
    └─ Using MySQL? → ❌ Not supported, convert to PostgreSQL or SQLite
```

---

## 🔧 Creating D1-Compatible Schemas from PostgreSQL

**Step 1:** Identify PostgreSQL-specific features
- Extensions (`CREATE EXTENSION`)
- Data types (`UUID`, `TIMESTAMPTZ`, `JSONB`, `TEXT[]`, `BYTEA`)
- Functions (`NOW()`, `uuid_generate_v4()`, `array_agg()`)
- Triggers and stored procedures
- Advanced query syntax (`DISTINCT ON`, `RETURNING *`)

**Step 2:** Replace with SQLite equivalents
```sql
-- PostgreSQL version:
CREATE TABLE trades (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  conditions JSONB NOT NULL,
  pattern_ids TEXT[]
);

-- D1/SQLite version:
CREATE TABLE trades (
  id TEXT PRIMARY KEY,  -- Generate in app: crypto.randomUUID()
  created_at INTEGER NOT NULL DEFAULT (cast(strftime('%s', 'now') as integer)),
  conditions TEXT NOT NULL,  -- JSON as string
  pattern_ids TEXT  -- JSON array as string: '["id1","id2"]'
);
```

**Step 3:** Test on D1
```bash
wrangler d1 execute coinswarm-evolution --local --file=new-schema.sql
```

---

## 📝 Best Practices

### DO ✅
- Use `cloudflare-d1-*.sql` files for Cloudflare Workers deployments
- Test migrations on D1 local (`--local`) before deploying remotely
- Use `CREATE TABLE IF NOT EXISTS` for idempotent migrations
- Document which schemas are for which database
- Keep PostgreSQL and D1 schemas in separate directories

### DON'T ❌
- Run `scripts/init-db.sql` on Cloudflare D1
- Use PostgreSQL data types in D1 schemas
- Rely on triggers or stored procedures in D1
- Use `ALTER TABLE` heavily (D1 has limited support)
- Store sensitive data without encryption

---

## 📞 Support

**If you accidentally ran PostgreSQL schema on D1:**
1. Database is likely corrupted - recreate it:
   ```bash
   wrangler d1 create coinswarm-evolution-new
   ```
2. Update `database_id` in all wrangler.toml files
3. Run D1-compatible schemas only

**If D1 migration fails:**
1. Check error message for unsupported feature
2. Rewrite using D1-compatible syntax
3. Test locally first: `wrangler d1 execute DB --local --file=migration.sql`

---

## 🎯 Quick Reference

**PostgreSQL Schemas (DO NOT USE WITH D1):**
- ❌ `scripts/init-db.sql`
- ❌ `scripts/add-historical-prices-table.sql`

**D1-Compatible Schemas (USE WITH CLOUDFLARE):**
- ✅ `cloudflare-d1-*.sql` (all files in root)
- ✅ `cloudflare-agents/d1-*.sql` (all D1 schemas)
- ✅ `cloudflare-agents/*-schema.sql` (agent-specific schemas)

**When in doubt:**
- If filename contains "d1" → Safe for Cloudflare
- If in `scripts/` directory → Assume PostgreSQL-only
- Always test with `--local` flag first

---

**Last Updated:** November 8, 2025
**Maintained By:** Claude Code Review System
**Related Docs:** CODE_REVIEW_REPORT_2025_11_08.md (Database section)
