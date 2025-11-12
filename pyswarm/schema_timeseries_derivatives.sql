-- ============================================================================
-- TIME SERIES DERIVATIVES TRACKING
-- Track first, second, third, and fourth order derivatives of key metrics
-- ============================================================================

-- ============================================================================
-- SENTIMENT TIME SERIES
-- ============================================================================

CREATE TABLE IF NOT EXISTS sentiment_timeseries (
    id TEXT PRIMARY KEY,

    -- Identity
    timestamp INTEGER NOT NULL,
    symbol TEXT NOT NULL,  -- 'BTC', 'ETH', 'crypto_market'
    granularity TEXT NOT NULL,  -- '1h', '4h', '1d'

    -- === SENTIMENT (0th order) ===
    sentiment_value REAL NOT NULL,  -- -1 to 1

    -- === VELOCITY (1st derivative) ===
    -- Rate of change of sentiment
    velocity REAL,  -- sentiment change per hour
    -- Interpretation: +0.1/hr = sentiment improving fast
    --                -0.1/hr = sentiment declining fast

    -- === ACCELERATION (2nd derivative) ===
    -- Rate of change of velocity
    acceleration REAL,  -- change in velocity per hour
    -- Interpretation: +0.05/hr² = sentiment improving AND speeding up
    --                -0.05/hr² = sentiment improving BUT slowing down

    -- === JERK (3rd derivative) ===
    -- Rate of change of acceleration
    jerk REAL,  -- change in acceleration per hour
    -- Interpretation: +0.01/hr³ = momentum is building (acceleration increasing)
    --                -0.01/hr³ = momentum is fading (acceleration decreasing)

    -- === SNAP/JOUNCE (4th derivative) ===
    -- Rate of change of jerk
    snap REAL,  -- change in jerk per hour
    -- Interpretation: +0.001/hr⁴ = momentum building is accelerating (bubble forming)
    --                -0.001/hr⁴ = momentum fade is accelerating (crash incoming)

    -- Regime classification based on derivatives
    regime TEXT,  -- 'stable', 'trending', 'accelerating', 'parabolic', 'reversal'
    momentum_score REAL,  -- Combined score: velocity + acceleration + jerk

    -- === FEAR & GREED INDEX ===
    fear_greed_value INTEGER,  -- 0-100
    fear_greed_velocity REAL,
    fear_greed_acceleration REAL,
    fear_greed_jerk REAL,

    -- === NEWS SENTIMENT (from news_items) ===
    news_sentiment_1hr REAL,  -- Avg sentiment of news in last hour
    news_sentiment_4hr REAL,
    news_sentiment_24hr REAL,
    news_volume_1hr INTEGER,  -- Count of news items
    news_importance_avg_1hr REAL,

    -- === SOCIAL SENTIMENT (from social_posts) ===
    social_sentiment_1hr REAL,
    social_sentiment_4hr REAL,
    social_mentions_1hr INTEGER,
    social_bot_ratio REAL,  -- % of posts that are bot-driven

    -- Metadata
    created_at INTEGER NOT NULL,

    UNIQUE(timestamp, symbol, granularity)
);

CREATE INDEX IF NOT EXISTS idx_sentiment_ts_timestamp ON sentiment_timeseries(timestamp);
CREATE INDEX IF NOT EXISTS idx_sentiment_ts_symbol ON sentiment_timeseries(symbol);
CREATE INDEX IF NOT EXISTS idx_sentiment_ts_regime ON sentiment_timeseries(regime);
CREATE INDEX IF NOT EXISTS idx_sentiment_ts_jerk ON sentiment_timeseries(jerk DESC);

-- ============================================================================
-- ENGAGEMENT TIME SERIES
-- ============================================================================

CREATE TABLE IF NOT EXISTS engagement_timeseries (
    id TEXT PRIMARY KEY,

    -- Identity
    timestamp INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    granularity TEXT NOT NULL,

    -- === ENGAGEMENT (0th order) ===
    total_engagement INTEGER NOT NULL,  -- Sum of likes + shares + comments

    -- === VELOCITY (1st derivative) ===
    engagement_velocity REAL,  -- Engagement per hour
    -- Interpretation: 1000/hr = getting 1000 engagements per hour

    -- === ACCELERATION (2nd derivative) ===
    engagement_acceleration REAL,  -- Change in velocity per hour
    -- Interpretation: +500/hr² = viral growth speeding up

    -- === JERK (3rd derivative) ===
    engagement_jerk REAL,
    -- Interpretation: +100/hr³ = going viral faster and faster

    -- === SNAP (4th derivative) ===
    engagement_snap REAL,
    -- Interpretation: +50/hr⁴ = viral explosion (parabolic growth)

    -- Virality classification
    viral_stage TEXT,  -- 'dormant', 'emerging', 'viral', 'parabolic', 'peak', 'fading'
    viral_coefficient REAL,  -- Measure of virality (>1 = exponential growth)

    -- Breakdown by type
    likes_velocity REAL,
    shares_velocity REAL,
    comments_velocity REAL,

    -- Platform breakdown
    twitter_engagement INTEGER,
    reddit_engagement INTEGER,
    telegram_engagement INTEGER,

    -- Bot detection
    bot_engagement_ratio REAL,  -- % of engagement from bots
    organic_velocity REAL,  -- Velocity after filtering bots

    created_at INTEGER NOT NULL,

    UNIQUE(timestamp, symbol, granularity)
);

CREATE INDEX IF NOT EXISTS idx_engagement_ts_timestamp ON engagement_timeseries(timestamp);
CREATE INDEX IF NOT EXISTS idx_engagement_ts_viral ON engagement_timeseries(viral_stage);
CREATE INDEX IF NOT EXISTS idx_engagement_ts_jerk ON engagement_timeseries(engagement_jerk DESC);

-- ============================================================================
-- NARRATIVE STRENGTH TIME SERIES
-- ============================================================================

CREATE TABLE IF NOT EXISTS narrative_strength_timeseries (
    id TEXT PRIMARY KEY,

    -- Identity
    timestamp INTEGER NOT NULL,
    narrative_id TEXT NOT NULL,
    granularity TEXT NOT NULL,

    -- === NARRATIVE STRENGTH (0th order) ===
    news_count INTEGER NOT NULL,  -- Number of news items about this narrative
    total_engagement INTEGER,
    avg_importance REAL,
    strength_score REAL,  -- Composite: news_count * avg_importance * engagement

    -- === VELOCITY (1st derivative) ===
    news_velocity REAL,  -- News items per hour
    engagement_velocity REAL,
    strength_velocity REAL,
    -- Interpretation: +10/hr = 10 new articles per hour (narrative growing)

    -- === ACCELERATION (2nd derivative) ===
    news_acceleration REAL,
    engagement_acceleration REAL,
    strength_acceleration REAL,
    -- Interpretation: +5/hr² = not just growing, but growth is speeding up

    -- === JERK (3rd derivative) ===
    news_jerk REAL,
    strength_jerk REAL,
    -- Interpretation: +2/hr³ = narrative explosion (media feeding frenzy)

    -- Lifecycle indicators
    lifecycle_stage TEXT,  -- 'emerging', 'growing', 'peak', 'mature', 'declining', 'dead'
    time_to_peak_estimate INTEGER,  -- Hours until estimated peak
    saturation_score REAL,  -- 0-1 (is media saturated with this story?)

    -- Sentiment within narrative
    narrative_sentiment REAL,  -- Avg sentiment of news in narrative
    sentiment_velocity REAL,
    sentiment_coherence REAL,  -- 0-1 (are all sources saying the same thing?)

    created_at INTEGER NOT NULL,

    FOREIGN KEY (narrative_id) REFERENCES narratives(id),
    UNIQUE(timestamp, narrative_id, granularity)
);

CREATE INDEX IF NOT EXISTS idx_narrative_strength_ts ON narrative_strength_timeseries(timestamp);
CREATE INDEX IF NOT EXISTS idx_narrative_strength_narrative ON narrative_strength_timeseries(narrative_id);
CREATE INDEX IF NOT EXISTS idx_narrative_strength_stage ON narrative_strength_timeseries(lifecycle_stage);

-- ============================================================================
-- SOURCE CREDIBILITY TIME SERIES
-- ============================================================================

CREATE TABLE IF NOT EXISTS source_credibility_timeseries (
    id TEXT PRIMARY KEY,

    -- Identity
    timestamp INTEGER NOT NULL,
    source_id TEXT NOT NULL,
    granularity TEXT NOT NULL,  -- '1d', '7d', '30d'

    -- === CREDIBILITY (0th order) ===
    credibility_score REAL NOT NULL,
    accuracy_score REAL,
    timeliness_score REAL,
    fake_news_rate REAL,

    -- === VELOCITY (1st derivative) ===
    credibility_velocity REAL,
    accuracy_velocity REAL,
    fake_news_velocity REAL,
    -- Interpretation: -0.1/day = credibility declining by 0.1 per day

    -- === ACCELERATION (2nd derivative) ===
    credibility_acceleration REAL,
    -- Interpretation: -0.05/day² = credibility decline is speeding up

    -- === JERK (3rd derivative) ===
    credibility_jerk REAL,
    -- Interpretation: -0.01/day³ = credibility collapse accelerating

    -- Source behavior
    article_count INTEGER,
    article_velocity REAL,  -- Articles per day
    breaking_news_ratio REAL,  -- % of articles that are breaking news
    sensationalism_score REAL,  -- 0-1 (clickbait tendency)

    -- Relative ranking
    rank_among_sources INTEGER,  -- Where does this rank vs other sources?
    rank_change INTEGER,  -- Change in rank from previous period

    created_at INTEGER NOT NULL,

    FOREIGN KEY (source_id) REFERENCES news_sources(id),
    UNIQUE(timestamp, source_id, granularity)
);

CREATE INDEX IF NOT EXISTS idx_source_cred_ts ON source_credibility_timeseries(timestamp);
CREATE INDEX IF NOT EXISTS idx_source_cred_source ON source_credibility_timeseries(source_id);

-- ============================================================================
-- ENTITY SENTIMENT TIME SERIES
-- ============================================================================

CREATE TABLE IF NOT EXISTS entity_sentiment_timeseries (
    id TEXT PRIMARY KEY,

    -- Identity
    timestamp INTEGER NOT NULL,
    entity_id TEXT NOT NULL,
    granularity TEXT NOT NULL,

    -- === SENTIMENT ABOUT ENTITY (0th order) ===
    sentiment_score REAL NOT NULL,  -- How positive/negative is news about this entity?
    mention_count INTEGER,
    avg_importance REAL,  -- Avg importance of news mentioning this entity

    -- === VELOCITY (1st derivative) ===
    sentiment_velocity REAL,
    mention_velocity REAL,
    -- Interpretation: +0.2/day = sentiment about BlackRock improving rapidly

    -- === ACCELERATION (2nd derivative) ===
    sentiment_acceleration REAL,
    mention_acceleration REAL,
    -- Interpretation: +0.1/day² = positive sentiment accelerating

    -- === JERK (3rd derivative) ===
    sentiment_jerk REAL,
    -- Interpretation: +0.05/day³ = rapid reputation improvement

    -- Context
    sentiment_trend TEXT,  -- 'improving', 'stable', 'declining', 'volatile'
    controversy_score REAL,  -- 0-1 (how controversial is this entity?)
    polarization_score REAL,  -- 0-1 (is sentiment split or unified?)

    -- Breakdown by sentiment
    positive_mention_count INTEGER,
    negative_mention_count INTEGER,
    neutral_mention_count INTEGER,

    created_at INTEGER NOT NULL,

    FOREIGN KEY (entity_id) REFERENCES entities(id),
    UNIQUE(timestamp, entity_id, granularity)
);

CREATE INDEX IF NOT EXISTS idx_entity_sentiment_ts ON entity_sentiment_timeseries(timestamp);
CREATE INDEX IF NOT EXISTS idx_entity_sentiment_entity ON entity_sentiment_timeseries(entity_id);

-- ============================================================================
-- MARKET CORRELATION TIME SERIES
-- ============================================================================

CREATE TABLE IF NOT EXISTS market_correlation_timeseries (
    id TEXT PRIMARY KEY,

    -- Identity
    timestamp INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    granularity TEXT NOT NULL,

    -- === NEWS-PRICE CORRELATION (0th order) ===
    -- How correlated is news sentiment with price movement?
    correlation_1h REAL,  -- Correlation over 1 hour
    correlation_4h REAL,
    correlation_24h REAL,
    correlation_7d REAL,

    -- === VELOCITY (1st derivative) ===
    correlation_velocity REAL,
    -- Interpretation: +0.1/day = news becoming MORE predictive of price

    -- === ACCELERATION (2nd derivative) ===
    correlation_acceleration REAL,
    -- Interpretation: +0.05/day² = news-price link strengthening rapidly

    -- Lead/lag analysis
    optimal_lag_hours REAL,  -- At what lag is correlation highest?
    -- e.g., 2 hours = news predicts price 2 hours ahead

    -- Causality
    granger_causality_score REAL,  -- Does news Granger-cause price?
    reverse_causality_score REAL,  -- Does price cause news? (pump then FUD)

    -- Efficiency
    market_efficiency_score REAL,  -- 0-1 (how fast does price react to news?)
    -- 1.0 = instant reaction (efficient)
    -- 0.0 = slow reaction (inefficient, opportunity)

    created_at INTEGER NOT NULL,

    UNIQUE(timestamp, symbol, granularity)
);

CREATE INDEX IF NOT EXISTS idx_market_corr_ts ON market_correlation_timeseries(timestamp);
CREATE INDEX IF NOT EXISTS idx_market_corr_symbol ON market_correlation_timeseries(symbol);

-- ============================================================================
-- VOLATILITY REGIME TIME SERIES
-- ============================================================================

CREATE TABLE IF NOT EXISTS volatility_regime_timeseries (
    id TEXT PRIMARY KEY,

    -- Identity
    timestamp INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    granularity TEXT NOT NULL,

    -- === VOLATILITY (0th order) ===
    realized_volatility REAL NOT NULL,  -- Historical volatility
    implied_volatility REAL,  -- From options (if available)
    news_driven_volatility REAL,  -- Volatility correlated with news events

    -- === VELOCITY (1st derivative) ===
    volatility_velocity REAL,
    -- Interpretation: +5%/day = volatility increasing 5% per day

    -- === ACCELERATION (2nd derivative) ===
    volatility_acceleration REAL,
    -- Interpretation: +2%/day² = volatility surge accelerating

    -- === JERK (3rd derivative) ===
    volatility_jerk REAL,
    -- Interpretation: +1%/day³ = rapid transition to high volatility regime

    -- Regime classification
    regime TEXT,  -- 'low', 'medium', 'high', 'extreme'
    regime_probability REAL,  -- 0-1 confidence in classification
    regime_transition_probability REAL,  -- Probability of switching regimes

    -- Event-driven analysis
    news_spike_volatility REAL,  -- Avg volatility spike after major news
    social_spike_volatility REAL,  -- Avg volatility spike after viral posts

    created_at INTEGER NOT NULL,

    UNIQUE(timestamp, symbol, granularity)
);

CREATE INDEX IF NOT EXISTS idx_volatility_regime_ts ON volatility_regime_timeseries(timestamp);
CREATE INDEX IF NOT EXISTS idx_volatility_regime_symbol ON volatility_regime_timeseries(symbol);

-- ============================================================================
-- COMPOSITE MOMENTUM SCORE
-- ============================================================================

CREATE TABLE IF NOT EXISTS momentum_timeseries (
    id TEXT PRIMARY KEY,

    -- Identity
    timestamp INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    granularity TEXT NOT NULL,

    -- === COMPOSITE MOMENTUM (0th order) ===
    -- Weighted combination of all momentum indicators
    momentum_score REAL NOT NULL,  -- -1 to 1

    -- === VELOCITY (1st derivative) ===
    momentum_velocity REAL,
    -- Interpretation: +0.1/day = momentum building

    -- === ACCELERATION (2nd derivative) ===
    momentum_acceleration REAL,
    -- Interpretation: +0.05/day² = momentum building faster

    -- === JERK (3rd derivative) ===
    momentum_jerk REAL,
    -- Interpretation: +0.01/day³ = explosive momentum building

    -- === SNAP (4th derivative) ===
    momentum_snap REAL,
    -- Interpretation: +0.005/day⁴ = parabolic momentum (bubble warning)

    -- Component scores
    sentiment_momentum REAL,
    engagement_momentum REAL,
    news_momentum REAL,
    social_momentum REAL,
    price_momentum REAL,

    -- Regime classification based on derivatives
    regime TEXT,  -- 'accumulation', 'markup', 'distribution', 'markdown'
    -- Accumulation: momentum_jerk > 0, momentum < 0 (building from bottom)
    -- Markup: momentum > 0, momentum_acceleration > 0 (bull run)
    -- Distribution: momentum > 0, momentum_acceleration < 0 (topping)
    -- Markdown: momentum < 0, momentum_acceleration < 0 (bear market)

    -- Warning signals
    bubble_risk_score REAL,  -- 0-1 (based on snap/jerk)
    crash_risk_score REAL,  -- 0-1 (based on negative snap/jerk)
    regime_shift_probability REAL,  -- Probability of regime change

    created_at INTEGER NOT NULL,

    UNIQUE(timestamp, symbol, granularity)
);

CREATE INDEX IF NOT EXISTS idx_momentum_ts_timestamp ON momentum_timeseries(timestamp);
CREATE INDEX IF NOT EXISTS idx_momentum_ts_symbol ON momentum_timeseries(symbol);
CREATE INDEX IF NOT EXISTS idx_momentum_ts_regime ON momentum_timeseries(regime);
CREATE INDEX IF NOT EXISTS idx_momentum_ts_bubble_risk ON momentum_timeseries(bubble_risk_score DESC);

-- ============================================================================
-- DERIVATIVE CALCULATION FUNCTIONS (Query Patterns)
-- ============================================================================

-- Calculate derivatives for sentiment
-- Note: D1 doesn't support stored procedures, but these are query patterns

/*
-- Calculate velocity (1st derivative)
WITH current AS (
    SELECT sentiment_value, timestamp
    FROM sentiment_timeseries
    WHERE symbol = 'BTC' AND timestamp = :current_ts
),
previous AS (
    SELECT sentiment_value, timestamp
    FROM sentiment_timeseries
    WHERE symbol = 'BTC' AND timestamp = :previous_ts
)
SELECT
    (c.sentiment_value - p.sentiment_value) / ((c.timestamp - p.timestamp) / 3600.0) as velocity
FROM current c, previous p;

-- Calculate acceleration (2nd derivative)
WITH t0 AS (SELECT sentiment_value, timestamp FROM sentiment_timeseries WHERE symbol = 'BTC' AND timestamp = :t0),
     t1 AS (SELECT sentiment_value, timestamp FROM sentiment_timeseries WHERE symbol = 'BTC' AND timestamp = :t1),
     t2 AS (SELECT sentiment_value, timestamp FROM sentiment_timeseries WHERE symbol = 'BTC' AND timestamp = :t2)
SELECT
    -- v1 = (s1 - s0) / dt
    -- v2 = (s2 - s1) / dt
    -- a = (v2 - v1) / dt = ((s2 - s1) - (s1 - s0)) / (dt^2)
    ((t2.sentiment_value - t1.sentiment_value) - (t1.sentiment_value - t0.sentiment_value)) /
    POWER((t1.timestamp - t0.timestamp) / 3600.0, 2) as acceleration
FROM t0, t1, t2;

-- Calculate jerk (3rd derivative)
-- Similar pattern but need 4 time points

-- Calculate snap (4th derivative)
-- Need 5 time points
*/

-- ============================================================================
-- VIEWS FOR MOMENTUM ANALYSIS
-- ============================================================================

-- Current momentum state
CREATE VIEW IF NOT EXISTS v_current_momentum AS
SELECT
    m.symbol,
    m.momentum_score,
    m.momentum_velocity,
    m.momentum_acceleration,
    m.momentum_jerk,
    m.momentum_snap,
    m.regime,
    m.bubble_risk_score,
    m.crash_risk_score,
    s.sentiment_value,
    s.velocity as sentiment_velocity,
    s.jerk as sentiment_jerk,
    e.engagement_velocity,
    e.viral_stage
FROM momentum_timeseries m
LEFT JOIN sentiment_timeseries s ON m.timestamp = s.timestamp AND m.symbol = s.symbol
LEFT JOIN engagement_timeseries e ON m.timestamp = e.timestamp AND m.symbol = e.symbol
WHERE m.granularity = '1h'
ORDER BY m.timestamp DESC
LIMIT 100;

-- High jerk periods (momentum building/fading rapidly)
CREATE VIEW IF NOT EXISTS v_high_jerk_periods AS
SELECT
    timestamp,
    symbol,
    momentum_jerk,
    momentum_snap,
    regime,
    bubble_risk_score,
    crash_risk_score
FROM momentum_timeseries
WHERE ABS(momentum_jerk) > 0.05  -- Significant jerk
ORDER BY ABS(momentum_jerk) DESC;

-- Regime transitions
CREATE VIEW IF NOT EXISTS v_regime_transitions AS
SELECT
    m1.timestamp as transition_timestamp,
    m1.symbol,
    m1.regime as old_regime,
    m2.regime as new_regime,
    m2.momentum_jerk,
    m2.momentum_snap
FROM momentum_timeseries m1
JOIN momentum_timeseries m2 ON m1.symbol = m2.symbol
    AND m2.timestamp = (
        SELECT MIN(timestamp)
        FROM momentum_timeseries
        WHERE symbol = m1.symbol AND timestamp > m1.timestamp
    )
WHERE m1.regime != m2.regime
ORDER BY m1.timestamp DESC;
