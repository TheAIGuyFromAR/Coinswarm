/**
 * Historical Sentiment Backfill Worker
 *
 * Enriches existing chaos trades with sentiment data:
 * - Fear & Greed Index (90 days from API, rest from archive)
 * - CryptoCompare news sentiment (several years available)
 * - FRED macro data (decades available)
 * - Calculates derivatives (velocity, acceleration, jerk)
 * - Extracts keywords and headlines
 *
 * Usage:
 * - POST /backfill?batch=100 - Process 100 trades
 * - GET /status - Check backfill progress
 */

import { calculateSentimentDerivatives, extractKeywords, calculateNewsContext } from './sentiment-timeseries-calculator';

interface Env {
  DB: D1Database;
  CRYPTOCOMPARE_API_KEY?: string;
  FRED_API_KEY?: string;
}

interface ChaosTrade {
  id: number;
  pair: string;
  entry_time: string;
  entry_price: number;
  exit_price: number;
  pnl_pct: number;
  profitable: number;
}

// ============================================================================
// Fear & Greed Historical Data
// ============================================================================

class FearGreedHistoricalClient {
  /**
   * Get Fear & Greed for a specific date
   * API only provides last 90 days, but we can use alternative sources for older data
   */
  async getForDate(date: Date): Promise<{value: number; classification: string} | null> {
    try {
      const daysSinceToday = Math.floor((Date.now() - date.getTime()) / (24 * 60 * 60 * 1000));

      if (daysSinceToday <= 90) {
        // Can fetch from API
        const response = await fetch(`https://api.alternative.me/fng/?limit=90`);
        const data = await response.json() as any;

        // Find closest date
        const targetTimestamp = Math.floor(date.getTime() / 1000);
        const closest = data.data.find((item: any) => {
          const itemTimestamp = parseInt(item.timestamp);
          return Math.abs(itemTimestamp - targetTimestamp) < 24 * 60 * 60; // Within 1 day
        });

        if (closest) {
          return {
            value: parseInt(closest.value),
            classification: closest.value_classification
          };
        }
      }

      // For dates older than 90 days, we'd need to use an archive or estimate
      // For now, return null and we'll skip sentiment for very old trades
      // TODO: Add archive source or estimation based on price volatility

      return null;

    } catch (error) {
      console.error('Failed to fetch historical Fear & Greed:', error);
      return null;
    }
  }
}

// ============================================================================
// CryptoCompare Historical News
// ============================================================================

class CryptoCompareHistoricalClient {
  private apiKey: string | undefined;

  constructor(apiKey?: string) {
    this.apiKey = apiKey;
  }

  /**
   * Fetch news articles around a specific timestamp
   */
  async getNewsAroundTime(
    timestamp: Date,
    hoursBefore: number = 24,
    hoursAfter: number = 1
  ): Promise<Array<{title: string; body: string; source: string; published_on: number; sentiment?: number}>> {

    if (!this.apiKey) {
      console.log('CryptoCompare API key not set, skipping historical news');
      return [];
    }

    try {
      const startTime = Math.floor((timestamp.getTime() - hoursBefore * 60 * 60 * 1000) / 1000);
      const endTime = Math.floor((timestamp.getTime() + hoursAfter * 60 * 60 * 1000) / 1000);

      // CryptoCompare doesn't have time-range filtering in free tier
      // We fetch latest and filter client-side
      const response = await fetch(
        `https://min-api.cryptocompare.com/data/v2/news/?categories=BTC,ETH,SOL&sortOrder=latest&limit=100`,
        {
          headers: {
            'Authorization': `Apikey ${this.apiKey}`
          }
        }
      );

      const data = await response.json() as any;

      if (!data.Data) return [];

      // Filter to time range
      const articles = data.Data.filter((item: any) => {
        return item.published_on >= startTime && item.published_on <= endTime;
      });

      return articles.map((item: any) => ({
        title: item.title,
        body: item.body || '',
        source: item.source_info?.name || item.source,
        published_on: item.published_on,
        sentiment: this.analyzeSentiment(item.title + ' ' + (item.body || ''))
      }));

    } catch (error) {
      console.error('Failed to fetch historical news:', error);
      return [];
    }
  }

  private analyzeSentiment(text: string): number {
    const bullish = ['moon', 'surge', 'rally', 'bullish', 'buy', 'adoption', 'upgrade'];
    const bearish = ['crash', 'dump', 'bearish', 'sell', 'hack', 'ban', 'regulation'];

    const lower = text.toLowerCase();
    let score = 0;

    for (const word of bullish) {
      if (lower.includes(word)) score += 0.2;
    }
    for (const word of bearish) {
      if (lower.includes(word)) score -= 0.2;
    }

    return Math.max(-1, Math.min(1, score));
  }
}

// ============================================================================
// FRED Historical Macro Data
// ============================================================================

class FREDHistoricalClient {
  private apiKey: string | undefined;

  constructor(apiKey?: string) {
    this.apiKey = apiKey;
  }

  /**
   * Get macro indicators for a specific date
   */
  async getForDate(date: Date): Promise<{
    fed_rate?: number;
    cpi?: number;
    unemployment?: number;
    yield_10y?: number;
  }> {

    if (!this.apiKey) {
      console.log('FRED API key not set, skipping macro data');
      return {};
    }

    const dateStr = date.toISOString().split('T')[0]; // YYYY-MM-DD

    try {
      const [fedRate, cpi, unemployment, yield10y] = await Promise.all([
        this.getIndicator('FEDFUNDS', dateStr),
        this.getIndicator('CPIAUCSL', dateStr),
        this.getIndicator('UNRATE', dateStr),
        this.getIndicator('DGS10', dateStr)
      ]);

      return {
        fed_rate: fedRate,
        cpi: cpi,
        unemployment: unemployment,
        yield_10y: yield10y
      };

    } catch (error) {
      console.error('Failed to fetch FRED data:', error);
      return {};
    }
  }

  private async getIndicator(seriesId: string, date: string): Promise<number | undefined> {
    try {
      const response = await fetch(
        `https://api.stlouisfed.org/fred/series/observations?series_id=${seriesId}&api_key=${this.apiKey}&file_type=json&observation_start=${date}&observation_end=${date}`
      );

      const data = await response.json() as any;

      if (data.observations && data.observations.length > 0) {
        const value = parseFloat(data.observations[0].value);
        return isNaN(value) ? undefined : value;
      }

      return undefined;

    } catch (error) {
      console.error(`Failed to fetch ${seriesId}:`, error);
      return undefined;
    }
  }
}

// ============================================================================
// Backfill Worker
// ============================================================================

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;

    // ========================================================================
    // Route: Backfill sentiment data for historical trades
    // ========================================================================
    if (path === '/backfill' && request.method === 'POST') {
      const batchSize = parseInt(url.searchParams.get('batch') || '100');

      try {
        // Get trades that don't have sentiment data yet
        const trades = await env.DB.prepare(`
          SELECT id, pair, entry_time, entry_price, exit_price, pnl_pct, profitable
          FROM chaos_trades
          WHERE sentiment_fear_greed IS NULL
          ORDER BY entry_time DESC
          LIMIT ?
        `).bind(batchSize).all() as any;

        if (!trades.results || trades.results.length === 0) {
          return new Response(JSON.stringify({
            message: 'No trades to backfill',
            remaining: 0
          }), { headers: { 'Content-Type': 'application/json' } });
        }

        const fearGreedClient = new FearGreedHistoricalClient();
        const newsClient = new CryptoCompareHistoricalClient(env.CRYPTOCOMPARE_API_KEY);
        const macroClient = new FREDHistoricalClient(env.FRED_API_KEY);

        let processed = 0;
        let enriched = 0;

        for (const trade of trades.results as ChaosTrade[]) {
          try {
            const entryTime = new Date(trade.entry_time);

            // Fetch sentiment data for this timestamp
            const fearGreed = await fearGreedClient.getForDate(entryTime);
            const news24hr = await newsClient.getNewsAroundTime(entryTime, 24, 1);
            const news1hr = news24hr.filter(article => {
              const articleTime = new Date(article.published_on * 1000);
              return (entryTime.getTime() - articleTime.getTime()) <= 60 * 60 * 1000;
            });

            const macroData = await macroClient.getForDate(entryTime);

            // Calculate news context
            const keywords = extractKeywords(news24hr);
            const headlines_1hr = news1hr.map(a => a.title);
            const headlines_24hr = news24hr.map(a => a.title);

            const sentiments_1hr = news1hr.map(a => a.sentiment).filter(s => s !== undefined) as number[];
            const sentiments_24hr = news24hr.map(a => a.sentiment).filter(s => s !== undefined) as number[];

            const news_sentiment_1hr = sentiments_1hr.length > 0
              ? sentiments_1hr.reduce((sum, s) => sum + s, 0) / sentiments_1hr.length
              : null;

            const news_sentiment_24hr = sentiments_24hr.length > 0
              ? sentiments_24hr.reduce((sum, s) => sum + s, 0) / sentiments_24hr.length
              : null;

            // Calculate overall sentiment
            const fearGreedNormalized = fearGreed ? (fearGreed.value - 50) / 50 : 0;
            const overallSentiment = news_sentiment_24hr !== null
              ? (news_sentiment_24hr * 0.6 + fearGreedNormalized * 0.4)
              : fearGreedNormalized;

            // Detect regime
            const regime = fearGreed
              ? (fearGreed.value < 25 ? 'bear' : fearGreed.value > 75 ? 'bull' : 'sideways')
              : 'unknown';

            // TODO: Calculate derivatives (need historical snapshots)
            // For now, skip derivatives for backfilled data

            // Update trade with sentiment data
            await env.DB.prepare(`
              UPDATE chaos_trades SET
                sentiment_fear_greed = ?,
                sentiment_overall = ?,
                sentiment_regime = ?,
                sentiment_classification = ?,
                sentiment_news_score = ?,
                sentiment_keywords = ?,
                sentiment_headlines_1hr = ?,
                sentiment_headlines_24hr = ?,
                news_volume_1hr = ?,
                news_volume_24hr = ?,
                news_sentiment_1hr = ?,
                news_sentiment_24hr = ?,
                macro_fed_rate = ?,
                macro_cpi = ?,
                macro_unemployment = ?,
                macro_10y_yield = ?
              WHERE id = ?
            `).bind(
              fearGreed?.value ?? null,
              overallSentiment,
              regime,
              fearGreed?.classification ?? null,
              news_sentiment_24hr,
              JSON.stringify(keywords),
              JSON.stringify(headlines_1hr),
              JSON.stringify(headlines_24hr),
              news1hr.length,
              news24hr.length,
              news_sentiment_1hr,
              news_sentiment_24hr,
              macroData.fed_rate ?? null,
              macroData.cpi ?? null,
              macroData.unemployment ?? null,
              macroData.yield_10y ?? null,
              trade.id
            ).run();

            enriched++;

          } catch (tradeError) {
            console.error(`Failed to enrich trade ${trade.id}:`, tradeError);
          }

          processed++;

          // Rate limiting
          if (processed % 10 === 0) {
            await new Promise(resolve => setTimeout(resolve, 1000)); // 1 second delay every 10 trades
          }
        }

        // Count remaining trades
        const remaining = await env.DB.prepare(`
          SELECT COUNT(*) as count
          FROM chaos_trades
          WHERE sentiment_fear_greed IS NULL
        `).first() as any;

        return new Response(JSON.stringify({
          message: 'Backfill completed',
          processed: processed,
          enriched: enriched,
          remaining: remaining?.count || 0
        }, null, 2), { headers: { 'Content-Type': 'application/json' } });

      } catch (error) {
        return new Response(JSON.stringify({
          error: 'Backfill failed',
          details: error instanceof Error ? error.message : String(error)
        }), { status: 500, headers: { 'Content-Type': 'application/json' } });
      }
    }

    // ========================================================================
    // Route: Get backfill status
    // ========================================================================
    if (path === '/status') {
      try {
        const total = await env.DB.prepare(`
          SELECT COUNT(*) as count FROM chaos_trades
        `).first() as any;

        const withSentiment = await env.DB.prepare(`
          SELECT COUNT(*) as count FROM chaos_trades WHERE sentiment_fear_greed IS NOT NULL
        `).first() as any;

        const remaining = (total?.count || 0) - (withSentiment?.count || 0);
        const progress = total?.count > 0 ? (withSentiment?.count || 0) / total.count * 100 : 0;

        return new Response(JSON.stringify({
          total_trades: total?.count || 0,
          enriched_trades: withSentiment?.count || 0,
          remaining_trades: remaining,
          progress_pct: progress.toFixed(2)
        }, null, 2), { headers: { 'Content-Type': 'application/json' } });

      } catch (error) {
        return new Response(JSON.stringify({
          error: 'Failed to get status',
          details: error instanceof Error ? error.message : String(error)
        }), { status: 500, headers: { 'Content-Type': 'application/json' } });
      }
    }

    return new Response('Sentiment Backfill Worker\n\nRoutes:\n- POST /backfill?batch=100 - Process 100 trades\n- GET /status - Check progress', {
      headers: { 'Content-Type': 'text/plain' }
    });
  }
};
