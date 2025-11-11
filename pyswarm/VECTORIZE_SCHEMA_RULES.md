# Cloudflare Vectorize Schema Rules & Constraints

## Quick Reference Card

| Component | Limit | Notes |
|-----------|-------|-------|
| **Metadata per vector** | 10 KiB | Total JSON size |
| **Vector ID** | 64 bytes | String identifier |
| **Dimensions** | 1536 max | 32-bit precision |
| **Vectors per index** | 5,000,000 | Hard limit |
| **Metadata indexes** | 10 per index | Must create before inserting vectors |
| **Index name** | 64 bytes | Account-wide unique |
| **Filter JSON** | 2,048 bytes | Compact representation |
| **Property names** | 512 chars max | No dots, spaces, $, pipes |

---

## Index Configuration (One-Time Setup)

### Creating an Index

```bash
wrangler vectorize create INDEX_NAME \
  --dimensions=384 \
  --metric=cosine \
  --description="Optional description"
```

**Rules**:
- Index name: **64 bytes max**
- Dimensions: **Fixed at creation** (cannot change later)
  - Max: 1536 dimensions
  - Common: 384, 768, 1024
- Metric: `cosine`, `euclidean`, or `dot-product`
- **Cannot change dimensions or metric after creation!**

### Account Limits

- **Workers Paid**: 50,000 indexes
- **Workers Free**: 100 indexes
- **Namespaces**: 50,000 per index (Paid only)

---

## Vector Structure

### Vector Object Schema

```typescript
{
  id: string,              // Required, max 64 bytes
  values: number[],        // Required, must match index dimensions
  metadata?: object,       // Optional, max 10 KiB JSON
  namespace?: string       // Optional (Paid plan only)
}
```

### Vector ID Rules

- **Max length**: 64 bytes (UTF-8)
- **Type**: String
- **Uniqueness**: Must be unique within index/namespace
- **Examples**:
  ```typescript
  id: "2024-01-15T12:00:00Z"           // ISO timestamp ✓
  id: "snapshot_1705320000"            // Unix timestamp ✓
  id: "btc_daily_2024-01-15"          // Descriptive ✓
  id: "user123_doc456_chunk789"        // Composite ✓
  ```

### Vector Values Rules

- **Type**: Array of numbers (`number[]`)
- **Precision**: 32-bit floats (float32)
- **Dimensions**: Must **exactly match** index dimensions
  - 384-dim index → 384 numbers required
  - No more, no less
- **Range**: Typical embedding values are -1.0 to 1.0 (normalized)

---

## Metadata Rules

### Size & Structure

- **Max size**: 10 KiB per vector (total JSON size)
- **Format**: JSON object
- **Nesting**: Supported (use dot notation for filtering)

### Supported Data Types

| Type | Example | Notes |
|------|---------|-------|
| `string` | `"Bitcoin rally"` | Indexed to first 64 bytes |
| `number` | `45000` or `0.75` | Float64 precision |
| `boolean` | `true` or `false` | - |
| `null` | `null` | - |
| Arrays | `[1, 2, 3]` | Only for `$in`/`$nin` operators |
| Objects | `{price: 45000}` | Nestable |

### Property Name Rules

**CANNOT contain**:
- `.` (dot) - Reserved for nested access
- ` ` (space)
- `|` (pipe)
- `$` (dollar sign) at start
- Empty strings

**MUST**:
- Be ≤ 512 characters
- Be non-empty

**Examples**:
```typescript
// ✓ VALID
{
  "timestamp": 1705320000,
  "btc_price": 45000,
  "sentiment_score": 0.75,
  "market_phase": "bull_rally",
  "technical": {
    "rsi": 72,
    "macd": "bullish"
  }
}

// ✗ INVALID
{
  "price.btc": 45000,        // Contains dot ✗
  "market phase": "bull",    // Contains space ✗
  "$special": "value",       // Starts with $ ✗
  "": "empty key"            // Empty key ✗
}
```

### Nested Objects (Dot Notation)

```typescript
// Stored metadata
{
  "market": {
    "btc": {
      "price": 45000,
      "volume": 35000000000
    }
  }
}

// Filter using dot notation
filter: {
  "market.btc.price": { "$gte": 40000 }
}
```

---

## Metadata Indexes (For Filtering)

### Creating Metadata Indexes

**CRITICAL**: Must create metadata indexes **BEFORE** inserting vectors!

```bash
wrangler vectorize create-metadata-index INDEX_NAME \
  --property-name=timestamp \
  --type=number

wrangler vectorize create-metadata-index INDEX_NAME \
  --property-name=sentiment_score \
  --type=number

wrangler vectorize create-metadata-index INDEX_NAME \
  --property-name=market_phase \
  --type=string
```

### Metadata Index Rules

- **Limit**: 10 indexes per Vectorize index
- **Types**: `string`, `number`, `boolean`
- **Must create before inserting vectors** (cannot filter on un-indexed fields)
- **Cannot change after creation** (must recreate index)

### Type-Specific Indexing

**String Indexes**:
- Indexed to **first 64 bytes** only
- Truncated on UTF-8 character boundaries
- Only first 64B is searchable

**Number Indexes**:
- Precision: **float64**
- Full precision indexed

**Boolean Indexes**:
- `true` or `false` values

---

## Query Filters

### Filter Object Rules

- **Max size**: 2,048 bytes (compact JSON)
- **Must be**: Non-empty object
- **Keys**: Same rules as property names (no dots, $, spaces, pipes)
- **Values**: Depends on operator

### Supported Operators

| Operator | Description | Value Type | Example |
|----------|-------------|------------|---------|
| `$eq` | Equals | string, number, boolean, null | `{"sentiment_score": {"$eq": 0.75}}` |
| `$ne` | Not equals | string, number, boolean, null | `{"market_phase": {"$ne": "bear"}}` |
| `$in` | In array | Array of same type | `{"phase": {"$in": ["bull", "neutral"]}}` |
| `$nin` | Not in array | Array of same type | `{"phase": {"$nin": ["bear"]}}` |
| `$gt` | Greater than | number or string | `{"timestamp": {"$gt": 1705320000}}` |
| `$gte` | Greater than or equal | number or string | `{"sentiment": {"$gte": 0.5}}` |
| `$lt` | Less than | number or string | `{"timestamp": {"$lt": 1705400000}}` |
| `$lte` | Less than or equal | number or string | `{"sentiment": {"$lte": 0.8}}` |

### Filter Examples

```typescript
// Simple equality
filter: {
  "market_phase": { "$eq": "bull_rally" }
}

// Range query
filter: {
  "sentiment_score": { "$gte": 0.5, "$lte": 0.9 }
}

// Multiple conditions (AND logic)
filter: {
  "timestamp": { "$gte": 1705320000, "$lt": 1705406400 },
  "sentiment_score": { "$gte": 0.5 }
}

// Array membership
filter: {
  "market_phase": { "$in": ["bull_rally", "accumulation"] }
}

// Nested properties
filter: {
  "technical.rsi": { "$gte": 60, "$lte": 80 }
}
```

### Filter Constraints

**Allowed**:
- Multiple properties (AND logic)
- Range queries (combining `$gte` and `$lte` on same field)
- Nested property access

**NOT Allowed**:
- OR logic between properties (use multiple queries instead)
- Mixing operators beyond range queries
- Filtering on non-indexed properties (will be ignored)

---

## Query Limits

### topK Limits

| Returns Metadata/Values | Max topK |
|-------------------------|----------|
| **Yes** (returnMetadata: true) | 20 |
| **No** (returnMetadata: false) | 100 |

### Batch Operations

| Operation | Workers API | HTTP API |
|-----------|-------------|----------|
| **Upsert batch** | 1,000 vectors | 5,000 vectors |
| **Delete batch** | 1,000 IDs | 1,000 IDs |
| **List vectors** | 1,000 per page | 1,000 per page |

### Upload Size

- **Max upload**: 100 MB per request

---

## Best Practices for Your Use Case

### Time Period Snapshots

```typescript
// ✓ RECOMMENDED STRUCTURE
{
  id: "2024-01-15T12:00:00Z",           // ISO timestamp as ID
  values: [...],                         // 384-dim embedding
  metadata: {
    // Searchable fields (CREATE INDEXES FOR THESE!)
    timestamp: 1705320000,               // number index ✓
    sentiment_score: 0.75,               // number index ✓
    market_phase: "bull_rally",          // string index ✓

    // Text content (no indexes needed)
    news_summary: "Bitcoin ETF approved...",
    technical_setup: "RSI 72, breaking resistance...",
    social_summary: "Extremely bullish...",

    // Additional data (no indexes needed)
    btc_price: 45000,
    volume_24h: 35000000000,
    embedding_model: "@cf/baai/bge-small-en-v1.5",

    // Nested technical indicators (create index if filtering)
    technical: {
      rsi: 72,
      macd: "bullish",
      sma_20: 43500
    }
  }
}
```

### Metadata Indexes to Create

```bash
# For time-based filtering (CRITICAL)
wrangler vectorize create-metadata-index pyswarm-time-periods \
  --property-name=timestamp \
  --type=number

# For sentiment-based filtering
wrangler vectorize create-metadata-index pyswarm-time-periods \
  --property-name=sentiment_score \
  --type=number

# For market phase filtering
wrangler vectorize create-metadata-index pyswarm-time-periods \
  --property-name=market_phase \
  --type=string

# For nested technical indicators (if needed)
wrangler vectorize create-metadata-index pyswarm-time-periods \
  --property-name=technical.rsi \
  --type=number
```

### Common Query Patterns

```typescript
// Find similar periods in specific time range
filter: {
  "timestamp": {
    "$gte": 1704067200,  // Jan 1, 2024
    "$lt": 1735689600    // Jan 1, 2025
  }
}

// Find similar bullish periods only
filter: {
  "sentiment_score": { "$gte": 0.5 },
  "market_phase": { "$in": ["bull_rally", "accumulation"] }
}

// Exclude recent periods (last 30 days)
filter: {
  "timestamp": {
    "$lt": Date.now()/1000 - (30 * 24 * 60 * 60)
  }
}
```

---

## Common Pitfalls to Avoid

### ✗ Don't Do This

```typescript
// ✗ Metadata too large (>10 KiB)
metadata: {
  full_article_text: "..." // 50 KB article ✗
}

// ✗ Property name with dot
metadata: {
  "btc.price": 45000  // Use btc_price or nested object ✗
}

// ✗ Filtering without index
// (Creates metadata index for sentiment_score first!)
filter: {
  "sentiment_score": { "$gte": 0.5 }  // Won't work without index! ✗
}

// ✗ Wrong dimension count
// 384-dim index, but providing 768 values
values: new Array(768).fill(0)  // Dimension mismatch! ✗

// ✗ Trying to change dimensions after creation
// Cannot change - must create new index! ✗

// ✗ Using OR logic
filter: {
  "$or": [  // OR not supported! ✗
    {"phase": "bull"},
    {"phase": "accumulation"}
  ]
}
// Use: {"phase": {"$in": ["bull", "accumulation"]}} ✓
```

### ✓ Do This Instead

```typescript
// ✓ Store summary, link to full text elsewhere
metadata: {
  news_summary: "Bitcoin ETF approved...",  // <1 KB
  article_id: "abc123"  // Look up full text in D1/KV
}

// ✓ Use underscore or nested object
metadata: {
  btc_price: 45000,  // ✓
  market: {          // ✓
    btc: {
      price: 45000
    }
  }
}

// ✓ Create index FIRST, then insert vectors
// wrangler vectorize create-metadata-index ... (first!)
// Then insert vectors with that metadata

// ✓ Match index dimensions exactly
// 384-dim index needs exactly 384 values
values: embeddingArray  // Must be length 384 ✓

// ✓ Plan dimensions before creating index
// Once created, dimensions are FIXED

// ✓ Use $in for OR logic
filter: {
  "phase": {"$in": ["bull", "accumulation"]}  // ✓
}
```

---

## Summary Checklist

Before deploying:

- [ ] Decided on dimensions (384, 768, or 1024) - **cannot change later!**
- [ ] Identified which metadata fields need filtering
- [ ] Created metadata indexes BEFORE inserting vectors
- [ ] Property names avoid dots, spaces, $, pipes
- [ ] Metadata size <10 KiB per vector
- [ ] Vector IDs <64 bytes
- [ ] Filter JSON <2,048 bytes
- [ ] Batch operations ≤1,000 vectors (Workers API)
- [ ] topK ≤20 when returning metadata

---

## Reference Commands

```bash
# Create index (one-time, dimensions FIXED)
wrangler vectorize create INDEX_NAME \
  --dimensions=384 \
  --metric=cosine

# Create metadata index (BEFORE inserting vectors!)
wrangler vectorize create-metadata-index INDEX_NAME \
  --property-name=PROPERTY \
  --type=TYPE  # string, number, or boolean

# List indexes
wrangler vectorize list

# Get index info
wrangler vectorize get INDEX_NAME

# Delete index (careful!)
wrangler vectorize delete INDEX_NAME
```

---

For complete documentation: https://developers.cloudflare.com/vectorize/
