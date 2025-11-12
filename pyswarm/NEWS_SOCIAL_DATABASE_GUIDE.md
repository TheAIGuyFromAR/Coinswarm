# News & Social Media Database Guide

## Overview

Comprehensive D1 database schema for collecting, deduplicating, categorizing, and analyzing news, social media, macro events, and on-chain data for the temporal embedding system.

**Design Philosophy**: Overzealous - capture everything an AI trading agent might need. We can always query selectively, but can't retroactively add missing data.

## Database Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA SOURCES                             │
├─────────────────────────────────────────────────────────────┤
│  News APIs  │  Twitter  │  Reddit  │  Blockchain  │  Macro  │
└──────────┬──────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│               INGESTION & PROCESSING                        │
│  - Deduplication (content hash)                             │
│  - Categorization (AI classification)                       │
│  - Sentiment analysis                                       │
│  - Entity extraction                                        │
│  - Importance scoring                                       │
│  - Keyword extraction                                       │
└──────────┬──────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│                    D1 STORAGE                               │
│                                                             │
│  Core Tables:                                               │
│  ├─ news_items (comprehensive metadata)                    │
│  ├─ social_posts (Twitter, Reddit, etc.)                   │
│  ├─ macro_events (Fed, CPI, GDP)                           │
│  └─ on_chain_events (whale moves, flows)                   │
│                                                             │
│  Enrichment Tables:                                         │
│  ├─ entities (companies, people, protocols)                │
│  ├─ narratives (ETF approval, regulation)                  │
│  ├─ news_sources (credibility tracking)                    │
│  └─ news_clusters (deduplication)                          │
│                                                             │
│  Integration Tables:                                        │
│  ├─ daily_snapshots (link to Vectorize)                    │
│  └─ snapshot_news_items (which news in each snapshot)      │
└──────────┬──────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│           TEMPORAL EMBEDDING SYSTEM                         │
│  - Query top headlines for date                             │
│  - Get historical context (important news from past N days) │
│  - Generate dual embeddings                                 │
│  - Store in Vectorize with metadata                         │
└─────────────────────────────────────────────────────────────┘
```

## Core Tables

### 1. news_items (Primary Table)

**Purpose**: Store all news headlines and articles with comprehensive metadata.

**Key Fields**:

#### Identity & Deduplication
```sql
id                TEXT PRIMARY KEY     -- UUID
content_hash      TEXT UNIQUE          -- SHA-256 of title+content
canonical_id      TEXT                 -- Points to original if duplicate
duplicate_count   INTEGER              -- How many dupes found
```

#### Content
```sql
title             TEXT NOT NULL
content           TEXT                 -- Full article
summary           TEXT                 -- AI-generated summary
excerpt           TEXT                 -- First 200 chars
```

#### Categorization
```sql
category          TEXT NOT NULL        -- Primary: 'regulatory_approval', 'major_hack', etc.
subcategory       TEXT
event_type        TEXT                 -- Specific: 'etf_approval', 'sec_lawsuit'
narrative_theme   TEXT                 -- Broader: 'etf_narrative', 'regulation_crackdown'
```

**Category Values**:
- `regulatory_approval` - SEC approvals, legal clarity (persists 14 days)
- `regulatory_crackdown` - Lawsuits, enforcement (persists 7 days)
- `major_hack` - Exchange hacks, exploits (persists 5 days)
- `institutional_adoption` - Companies buying, announcements (persists 10 days)
- `technical_breakout` - ATH, resistance breaks (persists 2 days)
- `macro_news` - Fed policy, CPI, GDP (persists 21 days)
- `protocol_upgrade` - Hard forks, Ethereum merge (persists 7 days)
- `social_trend` - Twitter/Reddit hype (persists 1 day)
- `exchange_listing` - New listings (persists 3 days)
- `defi_event`, `nft_event`, `mining_event`, `other`

#### Importance & Impact
```sql
importance_score      REAL (0-1)       -- How important? (AI-scored)
market_impact_score   REAL (0-1)       -- Expected market impact
urgency_score         REAL (0-1)       -- How time-sensitive?
surprise_score        REAL (0-1)       -- How unexpected?
```

**Importance Scoring Guide**:
- `0.9-1.0`: Major events (ETF approval, major hack, Fed pivot)
- `0.7-0.9`: Significant news (institutional announcements, regulatory clarity)
- `0.5-0.7`: Notable news (earnings, upgrades, listings)
- `0.3-0.5`: Minor news (price movements, minor partnerships)
- `0.0-0.3`: Noise (social media trends, minor updates)

#### Sentiment Analysis
```sql
sentiment_score       REAL (-1 to 1)   -- Bullish/bearish
sentiment_direction   TEXT             -- 'bullish', 'bearish', 'neutral'
sentiment_confidence  REAL (0-1)
emotional_tone        TEXT             -- 'fear', 'greed', 'euphoria', 'panic'
emotional_intensity   REAL (0-1)
```

**Emotional Tone Values**:
- `extreme_fear` - Capitulation, panic selling
- `fear` - Concern, risk-off
- `uncertainty` - Mixed signals, unclear direction
- `neutral` - Balanced, no strong emotion
- `cautious_optimism` - Hopeful but careful
- `optimism` - Positive outlook
- `greed` - FOMO, excessive risk-taking
- `euphoria` - Extreme optimism, bubble territory
- `panic` - Flash crashes, black swan events

#### Credibility
```sql
source_credibility_score  REAL (0-1)   -- Bloomberg=0.9, Random blog=0.3
author_credibility_score  REAL (0-1)
fact_check_status         TEXT         -- 'verified', 'disputed', 'false'
fake_news_score          REAL (0-1)    -- Probability it's fake
```

#### Social Metrics
```sql
engagement_count     INTEGER           -- Total: likes + shares + comments
like_count          INTEGER
share_count         INTEGER
comment_count       INTEGER
view_count          INTEGER
retweet_count       INTEGER
quote_count         INTEGER

engagement_velocity  REAL              -- Engagement per hour
viral_score         REAL (0-1)        -- Is this going viral?
bot_amplification   REAL (0-1)        -- Bot-driven amplification?
organic_reach       INTEGER           -- Estimated organic reach
```

#### Market Context
```sql
btc_price_at_publication     REAL
eth_price_at_publication     REAL
market_cap_at_publication    REAL
volume_24h_at_publication    REAL
fear_greed_at_publication    INTEGER

-- Measured impact
price_impact_1h              REAL (%)
price_impact_4h              REAL (%)
price_impact_24h             REAL (%)
price_impact_7d              REAL (%)
volume_impact_24h            REAL (%)
volatility_impact_24h        REAL (%)
```

#### Keywords & Entities
```sql
keywords         TEXT    -- JSON: ["bitcoin", "etf", "sec", "blackrock"]
entities         TEXT    -- JSON: {"companies": ["BlackRock"], "people": ["Gary Gensler"]}
tickers          TEXT    -- JSON: ["BTC", "ETH"]
asset_mentions   TEXT    -- JSON: {"BTC": 5, "ETH": 2, "SOL": 1}
```

#### Narrative Tracking
```sql
is_breaking_news        BOOLEAN
is_major_event         BOOLEAN
starts_new_narrative   BOOLEAN
continues_narrative    TEXT     -- ID of narrative
contradicts_news_id    TEXT     -- ID of contradicting news
```

#### Temporal Persistence
```sql
persistence_window_days  INTEGER   -- How many days to persist in embeddings
decay_rate              REAL      -- Custom decay rate (overrides category default)
should_persist          BOOLEAN   -- Should be in historical context?
```

#### Embedding Integration
```sql
embedding_text           TEXT     -- Processed text for embedding
embedding_vector_id      TEXT     -- Vectorize ID
included_in_snapshots    TEXT     -- JSON: ["2024-01-15", "2024-01-16"]
last_embedded_at         INTEGER
```

#### Clustering & Similarity
```sql
similar_news_ids  TEXT     -- JSON: IDs of similar headlines
cluster_id        TEXT     -- Clustering for related stories
topic_id          TEXT     -- Broader topic grouping
```

### 2. social_posts

**Purpose**: Track social media posts (Twitter, Reddit, Telegram, Discord)

**Key Fields**:
```sql
platform                 TEXT     -- 'twitter', 'reddit', 'telegram'
platform_post_id         TEXT UNIQUE
username                 TEXT
user_follower_count     INTEGER
user_verified           BOOLEAN
user_influence_score    REAL (0-1)

text                    TEXT NOT NULL
hashtags                TEXT     -- JSON array
mentions                TEXT     -- JSON array

engagement_rate         REAL     -- engagement / followers
bot_probability         REAL (0-1)
spam_probability        REAL (0-1)
sarcasm_probability     REAL (0-1)

news_item_id           TEXT     -- Link to related news story
```

**Use Cases**:
- Track social sentiment separate from news sentiment
- Identify organic vs bot-driven trends
- Find influential voices
- Detect early signals before mainstream news

### 3. macro_events

**Purpose**: Track macroeconomic events (Fed, CPI, GDP, employment)

**Key Fields**:
```sql
event_type           TEXT     -- 'fed_decision', 'cpi_release', 'gdp', 'employment'
category             TEXT     -- 'monetary_policy', 'inflation', 'growth'

actual_value         REAL
expected_value       REAL
previous_value       REAL
surprise_magnitude   REAL     -- abs(actual - expected) / expected

importance_score     REAL (0-1)
market_impact_score  REAL (0-1)

event_date           INTEGER
next_event_date      INTEGER  -- When's the next release?
```

**Use Cases**:
- Track macro context for crypto markets
- Identify surprise events (actual >> expected)
- Correlate crypto moves with macro releases
- Build "risk-on / risk-off" indicators

### 4. on_chain_events

**Purpose**: Track significant on-chain events

**Key Fields**:
```sql
chain                TEXT     -- 'bitcoin', 'ethereum', 'solana'
event_type           TEXT     -- 'whale_transfer', 'exchange_inflow', 'miner_sale'

transaction_hash     TEXT
from_address         TEXT
to_address           TEXT
amount              REAL
amount_usd          REAL

from_entity_type    TEXT     -- 'exchange', 'whale', 'miner', 'unknown'
to_entity_type      TEXT
from_entity_name    TEXT     -- 'Binance', 'Unknown Whale #123'
to_entity_name      TEXT

significance_score  REAL (0-1)
is_unusual          BOOLEAN
historical_percentile REAL   -- Where does this rank historically?
```

**Use Cases**:
- Track whale movements
- Monitor exchange flows (inflow = bearish, outflow = bullish)
- Identify miner selling pressure
- Detect unusual on-chain activity

## Enrichment Tables

### 5. entities

**Purpose**: Track companies, people, protocols, exchanges, regulators

**Key Fields**:
```sql
entity_type          TEXT     -- 'company', 'person', 'protocol', 'exchange'
name                 TEXT NOT NULL
aliases              TEXT     -- JSON: ["BTC", "Bitcoin", "bitcoin"]

sector               TEXT     -- 'defi', 'cex', 'mining', 'custody'
credibility_score    REAL (0-1)
influence_score      REAL (0-1)

overall_sentiment    REAL     -- Average sentiment in news
sentiment_trend      TEXT     -- 'improving', 'declining', 'stable'

mention_count        INTEGER
```

**Examples**:
```json
{
  "id": "entity_blackrock",
  "entity_type": "company",
  "name": "BlackRock",
  "aliases": ["BlackRock", "BLK"],
  "sector": "asset_management",
  "influence_score": 0.95,
  "overall_sentiment": 0.7
}

{
  "id": "entity_gensler",
  "entity_type": "person",
  "name": "Gary Gensler",
  "aliases": ["Gary Gensler", "Gensler", "SEC Chair"],
  "sector": "regulator",
  "influence_score": 0.9,
  "overall_sentiment": -0.3
}
```

### 6. narratives

**Purpose**: Track multi-day market narratives

**Key Fields**:
```sql
theme                TEXT     -- 'etf_approval', 'regulation_crackdown'
title                TEXT
description          TEXT

started_at           INTEGER
ended_at             INTEGER   -- NULL if ongoing
peak_at              INTEGER   -- Peak engagement

total_news_count     INTEGER
avg_sentiment        REAL
importance_score     REAL (0-1)

price_move_during    REAL (%)  -- % change start to end
is_active            BOOLEAN
lifecycle_stage      TEXT     -- 'emerging', 'peak', 'declining', 'ended'
```

**Example Narratives**:
- "Bitcoin ETF Approval Rally" (Jan 10-24, 2024)
- "FTX Collapse & Contagion" (Nov 8-30, 2022)
- "DeFi Summer 2020" (Jun-Sep 2020)
- "China Mining Ban" (May-Jul 2021)

### 7. news_sources

**Purpose**: Track and score news sources

**Key Fields**:
```sql
name                  TEXT UNIQUE
source_type           TEXT     -- 'news', 'social', 'blockchain'

credibility_score     REAL (0-1)
accuracy_score        REAL (0-1)
timeliness_score      REAL (0-1)
bias_score            REAL (-1 to 1)  -- Bearish to bullish bias

total_items_published INTEGER
avg_importance        REAL
fake_news_rate        REAL (0-1)

is_trusted            BOOLEAN
is_blocked            BOOLEAN
```

**Credibility Tiers**:
- **Tier 1** (0.9-1.0): Bloomberg, Reuters, WSJ, Financial Times
- **Tier 2** (0.7-0.9): CoinDesk, The Block, Decrypt, CoinTelegraph
- **Tier 3** (0.5-0.7): Crypto Twitter influencers, smaller blogs
- **Tier 4** (0.3-0.5): Random blogs, unverified sources
- **Tier 5** (0.0-0.3): Known fake news, spam sites

## Integration Tables

### 8. daily_snapshots

**Purpose**: Link D1 news data to Vectorize embeddings

**Key Fields**:
```sql
id                        TEXT PRIMARY KEY  -- "2024-01-15"
date                      INTEGER UNIQUE

-- Vectorize references
pure_embedding_id         TEXT
smoothed_embedding_id     TEXT
embedding_strategy        TEXT             -- 'dual', 'hybrid'
alpha_used                REAL

-- Snapshot metadata
headline_count            INTEGER
top_headline_ids          TEXT (JSON)      -- Top 5
important_headline_ids    TEXT (JSON)      -- importance > 0.75

-- Narrative
primary_narrative         TEXT
narrative_summary         TEXT
dominant_sentiment        REAL
sentiment_velocity        REAL

-- Technical context
btc_price, rsi, macd_signal, volatility, volume_ratio, fear_greed

-- Outcomes (backfilled)
outcome_1d, outcome_5d, outcome_7d, outcome_30d

-- Regime
regime                    TEXT             -- 'bull_rally', 'consolidation'
regime_confidence         REAL (0-1)
```

### 9. snapshot_news_items

**Purpose**: Many-to-many link between snapshots and news

**Key Fields**:
```sql
snapshot_id          TEXT
news_item_id         TEXT
inclusion_weight     REAL     -- importance * decay
is_primary           BOOLEAN  -- Top headline?
```

## Common Workflows

### Workflow 1: Daily News Collection

```python
async def collect_daily_news(date: datetime):
    """Collect news for a specific day"""

    # 1. Scrape from sources
    raw_items = await scrape_all_sources(date)

    # 2. Process each item
    for raw in raw_items:
        # Compute content hash for deduplication
        content_hash = hashlib.sha256(
            f"{raw['title']}{raw['content']}".encode()
        ).hexdigest()

        # Check if duplicate
        existing = await d1.query(
            "SELECT id FROM news_items WHERE content_hash = ?",
            [content_hash]
        )

        if existing:
            # Update duplicate count on canonical
            await d1.execute(
                "UPDATE news_items SET duplicate_count = duplicate_count + 1 WHERE id = ?",
                [existing[0]['id']]
            )
            continue

        # 3. AI Processing
        processed = await process_news_item(raw)
        # Returns: {
        #   'summary': AI-generated summary,
        #   'category': classified category,
        #   'importance_score': 0.0-1.0,
        #   'sentiment_score': -1.0 to 1.0,
        #   'entities': extracted entities,
        #   'keywords': extracted keywords,
        #   'emotional_tone': classified emotion
        # }

        # 4. Store in D1
        await d1.execute(
            """
            INSERT INTO news_items (
                id, content_hash, source, title, content, summary,
                published_at, category, importance_score, sentiment_score,
                keywords, entities, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                generate_uuid(),
                content_hash,
                raw['source'],
                raw['title'],
                raw['content'],
                processed['summary'],
                int(date.timestamp()),
                processed['category'],
                processed['importance_score'],
                processed['sentiment_score'],
                json.dumps(processed['keywords']),
                json.dumps(processed['entities']),
                int(datetime.now().timestamp()),
                int(datetime.now().timestamp())
            ]
        )
```

### Workflow 2: Generate Daily Embedding

```python
async def generate_daily_embedding(date: datetime):
    """Generate embedding for a specific day"""

    # 1. Get top headlines for this day
    top_headlines = await d1.query(
        """
        SELECT id, title, category, importance_score, sentiment_score
        FROM news_items
        WHERE date(published_at, 'unixepoch') = date(?, 'unixepoch')
          AND is_deleted = FALSE
        ORDER BY importance_score DESC
        LIMIT 5
        """,
        [int(date.timestamp())]
    )

    # 2. Get important historical context (past 7 days)
    historical_context = await d1.query(
        """
        SELECT
            n.id,
            n.title,
            n.category,
            n.importance_score,
            n.persistence_window_days,
            (? - n.published_at) / 86400 as days_ago
        FROM news_items n
        WHERE n.should_persist = TRUE
          AND n.is_deleted = FALSE
          AND n.importance_score >= 0.75
          AND n.published_at < ?
          AND n.published_at >= (? - (n.persistence_window_days * 86400))
        ORDER BY (n.importance_score * (1 - days_ago / n.persistence_window_days)) DESC
        LIMIT 3
        """,
        [int(date.timestamp()), int(date.timestamp()), int(date.timestamp())]
    )

    # 3. Build embedding text
    embedding_text = build_embedding_text(top_headlines, historical_context)

    # 4. Generate dual embeddings
    pure_embedding = await embed(embedding_text)
    smoothed_embedding = await blend_with_yesterday(pure_embedding, date)

    # 5. Store in Vectorize
    await vectorize.upsert([{
        'id': date.isoformat(),
        'values': smoothed_embedding,
        'metadata': {
            'pure_embedding': pure_embedding,
            'headline_ids': [h['id'] for h in top_headlines],
            'historical_ids': [h['id'] for h in historical_context],
            # ... technical indicators, sentiment, etc.
        }
    }])

    # 6. Create daily snapshot in D1
    await d1.execute(
        """
        INSERT INTO daily_snapshots (
            id, date, pure_embedding_id, smoothed_embedding_id,
            headline_count, top_headline_ids, important_headline_ids,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            date.isoformat(),
            int(date.timestamp()),
            date.isoformat(),
            date.isoformat(),
            len(top_headlines),
            json.dumps([h['id'] for h in top_headlines]),
            json.dumps([h['id'] for h in historical_context]),
            int(datetime.now().timestamp()),
            int(datetime.now().timestamp())
        ]
    )

    # 7. Link news items to snapshot
    for headline in top_headlines:
        await d1.execute(
            """
            INSERT INTO snapshot_news_items (snapshot_id, news_item_id, is_primary)
            VALUES (?, ?, TRUE)
            """,
            [date.isoformat(), headline['id']]
        )

    for context in historical_context:
        await d1.execute(
            """
            INSERT INTO snapshot_news_items (snapshot_id, news_item_id, is_primary)
            VALUES (?, ?, FALSE)
            """,
            [date.isoformat(), context['id']]
        )
```

### Workflow 3: Find Similar Periods

```python
async def find_similar_periods_with_context(current_date: datetime):
    """Find similar historical periods with full context"""

    # 1. Query Vectorize for similar embeddings
    similar_vectors = await vectorize.query(
        vector=current_embedding,
        topK=10,
        returnMetadata=True
    )

    # 2. For each similar period, get full news context from D1
    results = []
    for match in similar_vectors.matches:
        # Get snapshot
        snapshot = await d1.query(
            "SELECT * FROM daily_snapshots WHERE id = ?",
            [match.id]
        )

        # Get news items for this snapshot
        news_items = await d1.query(
            """
            SELECT n.*
            FROM news_items n
            JOIN snapshot_news_items sni ON n.id = sni.news_item_id
            WHERE sni.snapshot_id = ?
            ORDER BY sni.is_primary DESC, n.importance_score DESC
            """,
            [match.id]
        )

        # Get active narratives at that time
        narratives = await d1.query(
            """
            SELECT DISTINCT nar.*
            FROM narratives nar
            JOIN news_narratives nn ON nar.id = nn.narrative_id
            JOIN snapshot_news_items sni ON nn.news_item_id = sni.news_item_id
            WHERE sni.snapshot_id = ?
            """,
            [match.id]
        )

        results.append({
            'date': match.id,
            'similarity_score': match.score,
            'snapshot': snapshot[0],
            'top_headlines': news_items[:5],
            'active_narratives': narratives,
            'outcome_7d': snapshot[0]['outcome_7d']
        })

    return results
```

## Indexes & Performance

**Critical Indexes** (already in schema):
```sql
-- News items
CREATE INDEX idx_news_published_at ON news_items(published_at);
CREATE INDEX idx_news_importance ON news_items(importance_score DESC);
CREATE INDEX idx_news_persist ON news_items(should_persist, published_at DESC);

-- Daily snapshots
CREATE INDEX idx_snapshots_date ON daily_snapshots(date);

-- Social posts
CREATE INDEX idx_social_posted_at ON social_posts(posted_at);
```

**Query Performance Tips**:
1. Always filter by date range first
2. Use `should_persist = TRUE` for embedding queries
3. Limit results with `LIMIT` clause
4. Use views for common queries

## Deployment

### 1. Create D1 Database
```bash
wrangler d1 create coinswarm-news-social

# Output: database_id = "abc123..."
```

### 2. Run Schema
```bash
wrangler d1 execute coinswarm-news-social --file=pyswarm/schema_news_social_d1.sql
```

### 3. Bind to Workers
```toml
# wrangler.toml
[[d1_databases]]
binding = "NEWS_DB"
database_name = "coinswarm-news-social"
database_id = "abc123..."
```

### 4. Initial Data Population
```python
# Populate news sources
await d1.batch([
    """INSERT INTO news_sources (id, name, source_type, credibility_score)
       VALUES ('src_bloomberg', 'Bloomberg', 'news', 0.95)""",
    """INSERT INTO news_sources (id, name, source_type, credibility_score)
       VALUES ('src_reuters', 'Reuters', 'news', 0.95)""",
    """INSERT INTO news_sources (id, name, source_type, credibility_score)
       VALUES ('src_coindesk', 'CoinDesk', 'news', 0.80)""",
    # ... more sources
])
```

## Cost Estimates

**D1 Pricing** (as of 2024):
- Reads: First 25M/month free, then $0.001 per million
- Writes: First 50K/month free, then $1 per million
- Storage: First 5 GB free, then $0.75/GB-month

**Estimated Usage** (6 years, ~100 news items/day):
- Total news items: 100/day × 365 × 6 = 219,000 rows
- Total storage: ~500 MB (well within free tier)
- Daily writes: ~100-200 (free tier)
- Daily reads: ~1,000-5,000 (free tier)

**Total cost**: **$0/month** (within free tier)

## Migration Path

If starting fresh:
1. Deploy schema
2. Backfill last 30 days (for testing)
3. Start daily collection going forward
4. Backfill historical (6 years) in batches

If you have existing news data:
```python
# Migrate from old schema
async def migrate_old_to_new():
    old_items = await old_db.query("SELECT * FROM old_news_table")

    for item in old_items:
        # Transform to new schema
        new_item = transform_to_new_schema(item)

        # Insert
        await d1.execute(
            "INSERT INTO news_items (...) VALUES (...)",
            new_item
        )
```

## Next Steps

1. **Deploy schema** to D1
2. **Build ingestion workers** for each source (Bloomberg, Twitter, etc.)
3. **Implement AI processing pipeline** (categorization, sentiment, entity extraction)
4. **Connect to temporal embedding system** (use this data to generate embeddings)
5. **Monitor source quality** (track fake news rate, credibility)
6. **Iterate on categorization** (tune importance scores based on outcomes)

## Example Queries

See `schema_news_social_d1.sql` for more query examples at the bottom!
