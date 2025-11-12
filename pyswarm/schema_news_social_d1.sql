-- ============================================================================
-- COINSWARM NEWS & SOCIAL MEDIA DATABASE SCHEMA
-- For temporal embedding system and AI trading agents
-- ============================================================================

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- News Headlines & Articles
CREATE TABLE IF NOT EXISTS news_items (
    -- Identity
    id TEXT PRIMARY KEY,  -- UUID or content hash
    content_hash TEXT NOT NULL UNIQUE,  -- For deduplication
    canonical_id TEXT,  -- If duplicate, points to canonical version
    duplicate_count INTEGER DEFAULT 1,

    -- Source
    source TEXT NOT NULL,  -- 'bloomberg', 'reuters', 'coindesk', 'twitter', etc.
    source_url TEXT,
    author TEXT,
    author_verified BOOLEAN DEFAULT FALSE,

    -- Content
    title TEXT NOT NULL,
    content TEXT,  -- Full article text (if available)
    summary TEXT,  -- AI-generated summary
    excerpt TEXT,  -- First 200 chars

    -- Temporal
    published_at INTEGER NOT NULL,  -- Unix timestamp
    first_seen_at INTEGER NOT NULL,  -- When we first detected it
    last_updated_at INTEGER,
    peak_engagement_at INTEGER,  -- When engagement peaked

    -- Categorization
    category TEXT NOT NULL,  -- Primary category (see category_enum)
    subcategory TEXT,
    event_type TEXT,  -- 'approval', 'hack', 'listing', 'upgrade', etc.
    narrative_theme TEXT,  -- 'etf_approval', 'regulation', 'adoption', etc.

    -- Importance & Impact
    importance_score REAL NOT NULL,  -- 0.0-1.0 (how important is this?)
    market_impact_score REAL,  -- 0.0-1.0 (expected market impact)
    urgency_score REAL,  -- 0.0-1.0 (how time-sensitive?)
    surprise_score REAL,  -- 0.0-1.0 (how unexpected?)

    -- Sentiment
    sentiment_score REAL,  -- -1.0 to 1.0
    sentiment_direction TEXT,  -- 'bullish', 'bearish', 'neutral'
    sentiment_confidence REAL,  -- 0.0-1.0
    emotional_tone TEXT,  -- 'fear', 'greed', 'uncertainty', 'euphoria', 'panic', 'calm'
    emotional_intensity REAL,  -- 0.0-1.0

    -- Credibility
    source_credibility_score REAL,  -- 0.0-1.0
    author_credibility_score REAL,
    fact_check_status TEXT,  -- 'verified', 'disputed', 'false', 'unknown'
    fake_news_score REAL,  -- 0.0-1.0 (probability it's fake)

    -- Social Metrics (if from social media)
    engagement_count INTEGER DEFAULT 0,  -- Likes + shares + comments
    like_count INTEGER DEFAULT 0,
    share_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    view_count INTEGER DEFAULT 0,
    retweet_count INTEGER DEFAULT 0,
    quote_count INTEGER DEFAULT 0,

    -- Social Dynamics
    engagement_velocity REAL,  -- Engagement per hour
    viral_score REAL,  -- 0.0-1.0 (is this going viral?)
    bot_amplification_score REAL,  -- 0.0-1.0 (is this bot-driven?)
    organic_reach_estimate INTEGER,

    -- Market Context (snapshot at time of news)
    btc_price_at_publication REAL,
    eth_price_at_publication REAL,
    market_cap_at_publication REAL,
    volume_24h_at_publication REAL,
    fear_greed_at_publication INTEGER,

    -- Price Impact (measured after publication)
    price_impact_1h REAL,  -- % change 1 hour after
    price_impact_4h REAL,
    price_impact_24h REAL,
    price_impact_7d REAL,
    volume_impact_24h REAL,  -- % change in volume
    volatility_impact_24h REAL,

    -- Keywords & Entities
    keywords TEXT,  -- JSON array: ["bitcoin", "etf", "sec"]
    entities TEXT,  -- JSON: {"companies": ["BlackRock"], "people": ["Gary Gensler"]}
    tickers TEXT,  -- JSON array: ["BTC", "ETH", "SOL"]
    asset_mentions TEXT,  -- JSON: {"BTC": 5, "ETH": 2}

    -- Narrative Tracking
    is_breaking_news BOOLEAN DEFAULT FALSE,
    is_major_event BOOLEAN DEFAULT FALSE,
    starts_new_narrative BOOLEAN DEFAULT FALSE,
    continues_narrative TEXT,  -- ID of narrative it continues
    contradicts_news_id TEXT,  -- ID of news it contradicts

    -- Temporal Persistence
    persistence_window_days INTEGER,  -- How many days should this persist in embeddings?
    decay_rate REAL,  -- Custom decay rate for this item
    should_persist BOOLEAN DEFAULT TRUE,  -- Should this be in historical context?

    -- Embedding Integration
    embedding_text TEXT,  -- Processed text fed to embedding model
    embedding_vector_id TEXT,  -- Reference to Vectorize
    included_in_snapshots TEXT,  -- JSON array of snapshot dates: ["2024-01-15", "2024-01-16"]
    last_embedded_at INTEGER,

    -- Clustering & Similarity
    similar_news_ids TEXT,  -- JSON array of similar headline IDs
    cluster_id TEXT,  -- Clustering for related stories
    topic_id TEXT,  -- Broader topic grouping

    -- Metadata
    language TEXT DEFAULT 'en',
    is_deleted BOOLEAN DEFAULT 0,
    deletion_reason TEXT,

    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,

    -- Indexes
    CHECK (importance_score BETWEEN 0 AND 1),
    CHECK (sentiment_score BETWEEN -1 AND 1)
);

-- Indexes for news_items
CREATE INDEX IF NOT EXISTS idx_news_published_at ON news_items(published_at);
CREATE INDEX IF NOT EXISTS idx_news_category ON news_items(category);
CREATE INDEX IF NOT EXISTS idx_news_importance ON news_items(importance_score DESC);
CREATE INDEX IF NOT EXISTS idx_news_source ON news_items(source);
CREATE INDEX IF NOT EXISTS idx_news_canonical ON news_items(canonical_id);
CREATE INDEX IF NOT EXISTS idx_news_content_hash ON news_items(content_hash);
CREATE INDEX IF NOT EXISTS idx_news_narrative ON news_items(narrative_theme);
CREATE INDEX IF NOT EXISTS idx_news_event_type ON news_items(event_type);
CREATE INDEX IF NOT EXISTS idx_news_cluster ON news_items(cluster_id);
CREATE INDEX IF NOT EXISTS idx_news_breaking ON news_items(is_breaking_news, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_persist ON news_items(should_persist, published_at DESC);

-- ============================================================================
-- SOCIAL MEDIA SPECIFIC
-- ============================================================================

CREATE TABLE IF NOT EXISTS social_posts (
    -- Identity
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,  -- 'twitter', 'reddit', 'telegram', 'discord'
    platform_post_id TEXT UNIQUE,
    post_url TEXT,

    -- Author
    username TEXT,
    user_id TEXT,
    user_follower_count INTEGER,
    user_verified BOOLEAN DEFAULT FALSE,
    user_influence_score REAL,  -- 0.0-1.0

    -- Content
    text TEXT NOT NULL,
    media_urls TEXT,  -- JSON array
    hashtags TEXT,  -- JSON array
    mentions TEXT,  -- JSON array

    -- Engagement
    engagement_metrics TEXT,  -- JSON: all platform-specific metrics
    engagement_rate REAL,  -- Engagement / followers

    -- Context
    is_reply BOOLEAN DEFAULT FALSE,
    reply_to_post_id TEXT,
    is_repost BOOLEAN DEFAULT FALSE,
    repost_of_post_id TEXT,
    thread_id TEXT,

    -- Sentiment & Analysis
    sentiment_score REAL,
    bot_probability REAL,  -- 0.0-1.0
    spam_probability REAL,
    sarcasm_probability REAL,

    -- Link to news item
    news_item_id TEXT,  -- If this is related to a news story

    -- Temporal
    posted_at INTEGER NOT NULL,
    scraped_at INTEGER NOT NULL,

    created_at INTEGER NOT NULL,

    FOREIGN KEY (news_item_id) REFERENCES news_items(id)
);

CREATE INDEX IF NOT EXISTS idx_social_platform ON social_posts(platform);
CREATE INDEX IF NOT EXISTS idx_social_posted_at ON social_posts(posted_at);
CREATE INDEX IF NOT EXISTS idx_social_influence ON social_posts(user_influence_score DESC);
CREATE INDEX IF NOT EXISTS idx_social_news ON social_posts(news_item_id);

-- ============================================================================
-- MACRO & ON-CHAIN DATA
-- ============================================================================

CREATE TABLE IF NOT EXISTS macro_events (
    id TEXT PRIMARY KEY,

    -- Event Details
    event_type TEXT NOT NULL,  -- 'fed_decision', 'cpi_release', 'gdp', 'employment'
    category TEXT,  -- 'monetary_policy', 'inflation', 'growth', 'employment'
    title TEXT NOT NULL,
    description TEXT,

    -- Data
    actual_value REAL,
    expected_value REAL,
    previous_value REAL,
    surprise_magnitude REAL,  -- abs(actual - expected) / expected

    -- Impact
    importance_score REAL,
    market_impact_score REAL,

    -- Temporal
    event_date INTEGER NOT NULL,
    release_date INTEGER NOT NULL,
    next_event_date INTEGER,  -- When is next occurrence?

    -- Related news
    news_item_ids TEXT,  -- JSON array

    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_macro_event_date ON macro_events(event_date);
CREATE INDEX IF NOT EXISTS idx_macro_type ON macro_events(event_type);

CREATE TABLE IF NOT EXISTS on_chain_events (
    id TEXT PRIMARY KEY,

    -- Event
    chain TEXT NOT NULL,  -- 'bitcoin', 'ethereum', 'solana'
    event_type TEXT NOT NULL,  -- 'whale_transfer', 'exchange_inflow', 'miner_sale', 'contract_deploy'

    -- Details
    transaction_hash TEXT,
    from_address TEXT,
    to_address TEXT,
    amount REAL,
    amount_usd REAL,

    -- Classification
    from_entity_type TEXT,  -- 'exchange', 'whale', 'miner', 'smart_contract', 'unknown'
    to_entity_type TEXT,
    from_entity_name TEXT,  -- 'Binance', 'Unknown Whale #123'
    to_entity_name TEXT,

    -- Impact
    significance_score REAL,
    market_impact_score REAL,

    -- Context
    is_unusual BOOLEAN DEFAULT FALSE,
    historical_percentile REAL,  -- Where does this rank historically?

    -- Temporal
    block_timestamp INTEGER NOT NULL,
    detected_at INTEGER NOT NULL,

    -- Related news
    news_item_id TEXT,

    created_at INTEGER NOT NULL,

    FOREIGN KEY (news_item_id) REFERENCES news_items(id)
);

CREATE INDEX IF NOT EXISTS idx_onchain_chain ON on_chain_events(chain);
CREATE INDEX IF NOT EXISTS idx_onchain_type ON on_chain_events(event_type);
CREATE INDEX IF NOT EXISTS idx_onchain_timestamp ON on_chain_events(block_timestamp);
CREATE INDEX IF NOT EXISTS idx_onchain_significance ON on_chain_events(significance_score DESC);

-- ============================================================================
-- ENTITY TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,

    -- Entity Details
    entity_type TEXT NOT NULL,  -- 'company', 'person', 'protocol', 'exchange', 'regulator'
    name TEXT NOT NULL,
    aliases TEXT,  -- JSON array: ["BTC", "Bitcoin", "bitcoin"]

    -- Attributes
    sector TEXT,  -- 'defi', 'cex', 'mining', 'custody', 'government'
    market_cap REAL,
    credibility_score REAL,
    influence_score REAL,

    -- Sentiment
    overall_sentiment REAL,  -- Average sentiment in news mentioning this entity
    sentiment_trend TEXT,  -- 'improving', 'declining', 'stable'

    -- Tracking
    mention_count INTEGER DEFAULT 0,
    first_mentioned_at INTEGER,
    last_mentioned_at INTEGER,

    -- Metadata
    metadata TEXT,  -- JSON: additional context

    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
CREATE INDEX IF NOT EXISTS idx_entities_influence ON entities(influence_score DESC);

-- Entity mentions (many-to-many)
CREATE TABLE IF NOT EXISTS news_entity_mentions (
    news_item_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    mention_type TEXT,  -- 'subject', 'mentioned', 'quoted'
    mention_count INTEGER DEFAULT 1,
    sentiment_in_context REAL,

    PRIMARY KEY (news_item_id, entity_id),
    FOREIGN KEY (news_item_id) REFERENCES news_items(id),
    FOREIGN KEY (entity_id) REFERENCES entities(id)
);

CREATE INDEX IF NOT EXISTS idx_mentions_news ON news_entity_mentions(news_item_id);
CREATE INDEX IF NOT EXISTS idx_mentions_entity ON news_entity_mentions(entity_id);

-- ============================================================================
-- NARRATIVE TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS narratives (
    id TEXT PRIMARY KEY,

    -- Narrative Details
    theme TEXT NOT NULL,  -- 'etf_approval', 'regulation_crackdown', 'institutional_adoption'
    title TEXT NOT NULL,
    description TEXT,

    -- Timeline
    started_at INTEGER NOT NULL,
    ended_at INTEGER,  -- NULL if ongoing
    peak_at INTEGER,  -- When was peak engagement?

    -- Metrics
    total_news_count INTEGER DEFAULT 0,
    total_engagement INTEGER DEFAULT 0,
    avg_sentiment REAL,
    importance_score REAL,

    -- Market Impact
    price_move_during_narrative REAL,  -- % change from start to end
    volume_increase REAL,
    volatility_increase REAL,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    lifecycle_stage TEXT,  -- 'emerging', 'peak', 'declining', 'ended'

    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_narratives_theme ON narratives(theme);
CREATE INDEX IF NOT EXISTS idx_narratives_active ON narratives(is_active);
CREATE INDEX IF NOT EXISTS idx_narratives_started ON narratives(started_at);

CREATE TABLE IF NOT EXISTS news_narratives (
    news_item_id TEXT NOT NULL,
    narrative_id TEXT NOT NULL,
    contribution_score REAL,  -- How much does this news contribute to narrative?
    is_key_event BOOLEAN DEFAULT FALSE,

    PRIMARY KEY (news_item_id, narrative_id),
    FOREIGN KEY (news_item_id) REFERENCES news_items(id),
    FOREIGN KEY (narrative_id) REFERENCES narratives(id)
);

-- ============================================================================
-- SOURCE MANAGEMENT
-- ============================================================================

CREATE TABLE IF NOT EXISTS news_sources (
    id TEXT PRIMARY KEY,

    -- Source Details
    name TEXT NOT NULL UNIQUE,
    domain TEXT,
    source_type TEXT,  -- 'news', 'social', 'blockchain', 'macro'

    -- Quality Metrics
    credibility_score REAL DEFAULT 0.5,
    accuracy_score REAL DEFAULT 0.5,
    timeliness_score REAL DEFAULT 0.5,
    bias_score REAL,  -- -1 (bearish bias) to 1 (bullish bias)

    -- Activity
    total_items_published INTEGER DEFAULT 0,
    avg_importance REAL,
    fake_news_rate REAL,  -- What % of their content is fake?

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_trusted BOOLEAN DEFAULT FALSE,
    is_blocked BOOLEAN DEFAULT FALSE,

    -- Scraping Config
    scrape_frequency_minutes INTEGER DEFAULT 60,
    last_scraped_at INTEGER,

    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sources_credibility ON news_sources(credibility_score DESC);
CREATE INDEX IF NOT EXISTS idx_sources_active ON news_sources(is_active);

-- ============================================================================
-- DEDUPLICATION & CLUSTERING
-- ============================================================================

CREATE TABLE IF NOT EXISTS news_duplicates (
    original_id TEXT NOT NULL,  -- Canonical version
    duplicate_id TEXT NOT NULL,  -- Duplicate
    similarity_score REAL NOT NULL,  -- 0.0-1.0
    detected_at INTEGER NOT NULL,

    PRIMARY KEY (original_id, duplicate_id),
    FOREIGN KEY (original_id) REFERENCES news_items(id),
    FOREIGN KEY (duplicate_id) REFERENCES news_items(id)
);

CREATE TABLE IF NOT EXISTS news_clusters (
    id TEXT PRIMARY KEY,

    -- Cluster Details
    cluster_type TEXT,  -- 'duplicate', 'related', 'follow_up'
    title TEXT,  -- Representative title
    summary TEXT,  -- Cluster summary

    -- Metrics
    item_count INTEGER DEFAULT 0,
    avg_importance REAL,
    total_engagement INTEGER DEFAULT 0,

    -- Timeline
    first_item_at INTEGER,
    last_item_at INTEGER,

    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS news_cluster_members (
    cluster_id TEXT NOT NULL,
    news_item_id TEXT NOT NULL,
    is_canonical BOOLEAN DEFAULT FALSE,  -- Is this the main story?

    PRIMARY KEY (cluster_id, news_item_id),
    FOREIGN KEY (cluster_id) REFERENCES news_clusters(id),
    FOREIGN KEY (news_item_id) REFERENCES news_items(id)
);

-- ============================================================================
-- TEMPORAL EMBEDDING INTEGRATION
-- ============================================================================

CREATE TABLE IF NOT EXISTS daily_snapshots (
    -- Identity
    id TEXT PRIMARY KEY,  -- Date in ISO format: "2024-01-15"
    date INTEGER NOT NULL UNIQUE,  -- Unix timestamp (midnight UTC)

    -- Embeddings (stored in Vectorize, referenced here)
    pure_embedding_id TEXT,  -- Vectorize ID for pure embedding
    smoothed_embedding_id TEXT,  -- Vectorize ID for smoothed embedding
    embedding_strategy TEXT,  -- 'dual', 'hybrid', 'pure', 'smoothed'
    alpha_used REAL,  -- Decay factor used

    -- Snapshot Metadata
    headline_count INTEGER DEFAULT 0,
    top_headline_ids TEXT,  -- JSON array of top 5 headline IDs
    important_headline_ids TEXT,  -- JSON array of important headlines (importance > 0.75)

    -- Narrative Summary
    primary_narrative TEXT,
    narrative_summary TEXT,  -- AI-generated summary
    dominant_sentiment REAL,
    sentiment_velocity REAL,

    -- Technical Context (from technical_indicators table)
    btc_price REAL,
    rsi REAL,
    macd_signal TEXT,
    volatility TEXT,
    volume_ratio REAL,
    fear_greed INTEGER,

    -- Market Outcomes (backfilled)
    outcome_1d REAL,
    outcome_5d REAL,
    outcome_7d REAL,
    outcome_30d REAL,

    -- Regime Classification
    regime TEXT,  -- 'bull_rally', 'bear_capitulation', 'consolidation', etc.
    regime_confidence REAL,

    -- Statistics
    total_engagement INTEGER DEFAULT 0,
    viral_news_count INTEGER DEFAULT 0,
    fake_news_count INTEGER DEFAULT 0,

    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_snapshots_date ON daily_snapshots(date);
CREATE INDEX IF NOT EXISTS idx_snapshots_regime ON daily_snapshots(regime);

-- Link news items to daily snapshots
CREATE TABLE IF NOT EXISTS snapshot_news_items (
    snapshot_id TEXT NOT NULL,
    news_item_id TEXT NOT NULL,
    inclusion_weight REAL,  -- How much weight in embedding? (importance * decay)
    is_primary BOOLEAN DEFAULT FALSE,  -- Is this a top headline?

    PRIMARY KEY (snapshot_id, news_item_id),
    FOREIGN KEY (snapshot_id) REFERENCES daily_snapshots(id),
    FOREIGN KEY (news_item_id) REFERENCES news_items(id)
);

-- ============================================================================
-- ANALYTICS & PERFORMANCE TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS prediction_performance (
    id TEXT PRIMARY KEY,

    -- Prediction Details
    snapshot_id TEXT NOT NULL,
    prediction_made_at INTEGER NOT NULL,
    lookahead_days INTEGER NOT NULL,

    -- Prediction
    predicted_return REAL,
    confidence REAL,
    similar_period_count INTEGER,

    -- Actual Outcome
    actual_return REAL,
    error REAL,
    absolute_error REAL,

    -- Analysis
    was_correct_direction BOOLEAN,
    beat_baseline BOOLEAN,  -- Did it beat simple moving average?

    created_at INTEGER NOT NULL,

    FOREIGN KEY (snapshot_id) REFERENCES daily_snapshots(id)
);

CREATE INDEX IF NOT EXISTS idx_performance_snapshot ON prediction_performance(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_performance_error ON prediction_performance(absolute_error);

-- ============================================================================
-- ENUMS & REFERENCE DATA
-- ============================================================================

-- Category enum (as reference)
-- We'll store these as TEXT but this documents valid values
/*
CATEGORY VALUES:
- regulatory_approval
- regulatory_crackdown
- major_hack
- institutional_adoption
- technical_breakout
- macro_news
- protocol_upgrade
- social_trend
- exchange_listing
- defi_event
- nft_event
- mining_event
- other
*/

-- Event type enum
/*
EVENT_TYPE VALUES:
- etf_approval
- etf_denial
- sec_lawsuit
- exchange_hack
- protocol_exploit
- major_purchase
- institutional_announcement
- protocol_upgrade
- hard_fork
- halving
- exchange_listing
- exchange_delisting
- regulatory_clarity
- regulatory_ban
- partnership_announcement
- acquisition
- bankruptcy
- ceo_change
- other
*/

-- Emotional tone enum
/*
EMOTIONAL_TONE VALUES:
- extreme_fear
- fear
- uncertainty
- neutral
- cautious_optimism
- optimism
- greed
- euphoria
- panic
*/

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Top breaking news (last 24 hours)
CREATE VIEW IF NOT EXISTS v_breaking_news AS
SELECT
    n.*,
    s.name as source_name,
    s.credibility_score as source_credibility
FROM news_items n
LEFT JOIN news_sources s ON n.source = s.name
WHERE n.is_breaking_news = TRUE
  AND n.published_at > (strftime('%s', 'now') - 86400)
  AND n.is_deleted = FALSE
ORDER BY n.importance_score DESC, n.published_at DESC;

-- Top headlines by day
CREATE VIEW IF NOT EXISTS v_daily_top_headlines AS
SELECT
    date(n.published_at, 'unixepoch') as date,
    n.*
FROM news_items n
WHERE n.importance_score >= 0.7
  AND n.is_deleted = FALSE
ORDER BY date DESC, n.importance_score DESC;

-- Active narratives
CREATE VIEW IF NOT EXISTS v_active_narratives AS
SELECT
    n.*,
    COUNT(nn.news_item_id) as current_news_count
FROM narratives n
LEFT JOIN news_narratives nn ON n.id = nn.narrative_id
WHERE n.is_active = TRUE
GROUP BY n.id
ORDER BY n.importance_score DESC;

-- Source performance
CREATE VIEW IF NOT EXISTS v_source_performance AS
SELECT
    s.*,
    COUNT(n.id) as total_items,
    AVG(n.importance_score) as avg_importance,
    AVG(n.sentiment_score) as avg_sentiment,
    SUM(CASE WHEN n.is_breaking_news THEN 1 ELSE 0 END) as breaking_news_count
FROM news_sources s
LEFT JOIN news_items n ON s.name = n.source
WHERE s.is_active = TRUE
GROUP BY s.id
ORDER BY s.credibility_score DESC;

-- ============================================================================
-- UTILITY FUNCTIONS
-- ============================================================================

-- Note: D1 doesn't support custom functions, but these are query patterns

-- Get news for embedding (for a specific date)
/*
SELECT
    n.id,
    n.title,
    n.category,
    n.importance_score,
    n.sentiment_score,
    n.persistence_window_days,
    date(n.published_at, 'unixepoch') as pub_date
FROM news_items n
WHERE n.should_persist = TRUE
  AND n.is_deleted = FALSE
  AND n.published_at BETWEEN :start_ts AND :end_ts
ORDER BY n.importance_score DESC
LIMIT 10;
*/

-- Get historical context (important news from past N days)
/*
SELECT
    n.id,
    n.title,
    n.category,
    n.importance_score,
    n.persistence_window_days,
    ((:current_ts - n.published_at) / 86400) as days_ago,
    (1.0 - ((:current_ts - n.published_at) / 86400.0 / n.persistence_window_days)) as decay_weight
FROM news_items n
WHERE n.should_persist = TRUE
  AND n.is_deleted = FALSE
  AND n.importance_score >= 0.75
  AND n.published_at < :current_ts
  AND n.published_at >= (:current_ts - (n.persistence_window_days * 86400))
ORDER BY (n.importance_score * decay_weight) DESC
LIMIT 5;
*/
