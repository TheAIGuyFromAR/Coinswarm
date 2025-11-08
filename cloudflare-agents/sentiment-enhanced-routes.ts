/**
 * Enhanced Sentiment Agent Routes
 *
 * Add these routes to news-sentiment-agent.ts to enable:
 * - Sentiment time-series storage
 * - Derivative calculations (velocity, acceleration, jerk)
 * - Keyword extraction and trending
 * - Historical context for any timestamp
 */

import {
  calculateSentimentDerivatives,
  calculateNewsContext,
  extractKeywords,
  classifyDerivatives,
  type SentimentSnapshot,
  type SentimentDerivatives,
  type NewsContext
} from './sentiment-timeseries-calculator';

/**
 * Route: Get sentiment with derivatives for a specific timestamp
 * GET /derivatives?timestamp=2025-11-08T12:00:00Z
 */
export async function getSentimentWithDerivatives(
  db: D1Database,
  timestamp: string
): Promise<SentimentDerivatives | null> {

  try {
    const targetTime = new Date(timestamp);
    const time_1hr_ago = new Date(targetTime.getTime() - 60 * 60 * 1000);
    const time_4hr_ago = new Date(targetTime.getTime() - 4 * 60 * 60 * 1000);
    const time_24hr_ago = new Date(targetTime.getTime() - 24 * 60 * 60 * 1000);

    // Get current snapshot
    const current = await db.prepare(`
      SELECT sentiment_value, fear_greed_value, timestamp
      FROM sentiment_timeseries
      WHERE timestamp <= ?
        AND symbol = 'MARKET'
      ORDER BY timestamp DESC
      LIMIT 1
    `).bind(targetTime.toISOString()).first() as any;

    if (!current) {
      return null;
    }

    // Get historical snapshots for derivative calculations
    const snapshots_1hr = await db.prepare(`
      SELECT sentiment_value as sentiment, fear_greed_value as fear_greed, timestamp
      FROM sentiment_timeseries
      WHERE timestamp BETWEEN ? AND ?
        AND symbol = 'MARKET'
      ORDER BY timestamp DESC
    `).bind(time_1hr_ago.toISOString(), targetTime.toISOString()).all() as any;

    const snapshots_4hr = await db.prepare(`
      SELECT sentiment_value as sentiment, fear_greed_value as fear_greed, timestamp
      FROM sentiment_timeseries
      WHERE timestamp BETWEEN ? AND ?
        AND symbol = 'MARKET'
      ORDER BY timestamp DESC
    `).bind(time_4hr_ago.toISOString(), time_1hr_ago.toISOString()).all() as any;

    const snapshots_24hr = await db.prepare(`
      SELECT sentiment_value as sentiment, fear_greed_value as fear_greed, timestamp
      FROM sentiment_timeseries
      WHERE timestamp BETWEEN ? AND ?
        AND symbol = 'MARKET'
      ORDER BY timestamp DESC
    `).bind(time_24hr_ago.toISOString(), time_4hr_ago.toISOString()).all() as any;

    const currentSnapshot: SentimentSnapshot = {
      timestamp: current.timestamp,
      sentiment: current.sentiment_value,
      fear_greed: current.fear_greed_value
    };

    const derivatives = calculateSentimentDerivatives(
      currentSnapshot,
      snapshots_1hr.results || [],
      snapshots_4hr.results || [],
      snapshots_24hr.results || []
    );

    return derivatives;

  } catch (error) {
    console.error('Failed to calculate sentiment derivatives:', error);
    return null;
  }
}

/**
 * Route: Get news context for a specific timestamp
 * GET /news-context?timestamp=2025-11-08T12:00:00Z
 */
export async function getNewsContext(
  db: D1Database,
  timestamp: string
): Promise<NewsContext | null> {

  try {
    const targetTime = new Date(timestamp);
    const time_1hr_ago = new Date(targetTime.getTime() - 60 * 60 * 1000);
    const time_24hr_ago = new Date(targetTime.getTime() - 24 * 60 * 60 * 1000);

    // Get articles from last 1 hour
    const articles_1hr_result = await db.prepare(`
      SELECT title, body, sentiment_score as sentiment, published_on
      FROM news_articles
      WHERE published_on BETWEEN ? AND ?
      ORDER BY published_on DESC
      LIMIT 50
    `).bind(
      Math.floor(time_1hr_ago.getTime() / 1000),
      Math.floor(targetTime.getTime() / 1000)
    ).all() as any;

    // Get articles from last 24 hours
    const articles_24hr_result = await db.prepare(`
      SELECT title, body, sentiment_score as sentiment, published_on
      FROM news_articles
      WHERE published_on BETWEEN ? AND ?
      ORDER BY published_on DESC
      LIMIT 200
    `).bind(
      Math.floor(time_24hr_ago.getTime() / 1000),
      Math.floor(targetTime.getTime() / 1000)
    ).all() as any;

    const articles_1hr = articles_1hr_result.results || [];
    const articles_24hr = articles_24hr_result.results || [];

    const context = calculateNewsContext(articles_1hr, articles_24hr);

    return context;

  } catch (error) {
    console.error('Failed to get news context:', error);
    return null;
  }
}

/**
 * Route: Store sentiment snapshot for time-series analysis
 * POST /store-snapshot
 */
export async function storeSentimentSnapshot(
  db: D1Database,
  snapshot: {
    timestamp: string;
    symbol: string;
    sentiment: number;
    fear_greed: number;
    regime: string;
    news_volume?: number;
    news_sentiment?: number;
  }
): Promise<boolean> {

  try {
    // Calculate derivatives if we have historical data
    const derivatives = await getSentimentDerivatives(db, snapshot.timestamp);

    await db.prepare(`
      INSERT INTO sentiment_timeseries (
        timestamp, symbol, sentiment_value, fear_greed_value,
        velocity, acceleration, jerk,
        direction, regime, news_volume, news_sentiment
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(timestamp, symbol) DO UPDATE SET
        sentiment_value = excluded.sentiment_value,
        fear_greed_value = excluded.fear_greed_value,
        velocity = excluded.velocity,
        acceleration = excluded.acceleration,
        jerk = excluded.jerk,
        direction = excluded.direction,
        regime = excluded.regime,
        news_volume = excluded.news_volume,
        news_sentiment = excluded.news_sentiment
    `).bind(
      snapshot.timestamp,
      snapshot.symbol,
      snapshot.sentiment,
      snapshot.fear_greed,
      derivatives?.velocity ?? null,
      derivatives?.acceleration ?? null,
      derivatives?.jerk ?? null,
      derivatives?.direction ?? 'stable',
      snapshot.regime,
      snapshot.news_volume ?? null,
      snapshot.news_sentiment ?? null
    ).run();

    return true;

  } catch (error) {
    console.error('Failed to store sentiment snapshot:', error);
    return false;
  }
}

async function getSentimentDerivatives(
  db: D1Database,
  timestamp: string
): Promise<Pick<SentimentDerivatives, 'velocity' | 'acceleration' | 'jerk' | 'direction'> | null> {
  const derivatives = await getSentimentWithDerivatives(db, timestamp);
  if (!derivatives) return null;

  return {
    velocity: derivatives.velocity,
    acceleration: derivatives.acceleration,
    jerk: derivatives.jerk,
    direction: derivatives.direction
  };
}

/**
 * Route: Get trending keywords
 * GET /keywords/trending?hours=24
 */
export async function getTrendingKeywords(
  db: D1Database,
  hoursAgo: number = 24
): Promise<Array<{keyword: string; frequency: number; sentiment: number}>> {

  try {
    const cutoffTime = new Date(Date.now() - hoursAgo * 60 * 60 * 1000).toISOString();

    const results = await db.prepare(`
      SELECT keyword, SUM(frequency) as total_frequency, AVG(sentiment_score) as avg_sentiment
      FROM sentiment_keywords
      WHERE timestamp >= ?
      GROUP BY keyword
      ORDER BY total_frequency DESC
      LIMIT 50
    `).bind(cutoffTime).all() as any;

    return results.results || [];

  } catch (error) {
    console.error('Failed to get trending keywords:', error);
    return [];
  }
}

/**
 * Route: Store news article with keywords
 * POST /store-article
 */
export async function storeNewsArticle(
  db: D1Database,
  article: {
    title: string;
    body?: string;
    url: string;
    source: string;
    published_on: number;
    sentiment_score?: number;
  }
): Promise<boolean> {

  try {
    // Extract keywords
    const keywords = extractKeywords([article]);

    await db.prepare(`
      INSERT INTO news_articles (
        title, body, url, source, published_on,
        sentiment_score, keywords
      ) VALUES (?, ?, ?, ?, ?, ?, ?)
    `).bind(
      article.title,
      article.body ?? null,
      article.url,
      article.source,
      article.published_on,
      article.sentiment_score ?? null,
      JSON.stringify(keywords)
    ).run();

    // Store keywords in trending table
    const timestamp = new Date(article.published_on * 1000).toISOString();
    for (const keyword of keywords) {
      await db.prepare(`
        INSERT INTO sentiment_keywords (
          timestamp, keyword, frequency, sentiment_score, sources
        ) VALUES (?, ?, 1, ?, ?)
        ON CONFLICT(keyword, timestamp) DO UPDATE SET
          frequency = frequency + 1
      `).bind(
        timestamp,
        keyword,
        article.sentiment_score ?? null,
        JSON.stringify([article.source])
      ).run();
    }

    return true;

  } catch (error) {
    console.error('Failed to store news article:', error);
    return false;
  }
}
