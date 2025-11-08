/**
 * News & Sentiment Agent for Multi-Agent Committee Weighting
 *
 * Pulls current sentiment and macro trends to weight committee decisions.
 *
 * Data Sources (in priority order):
 * 1. Fear & Greed Index (FREE, no API key, always available)
 * 2. CryptoCompare News API (FREE tier 50/day, API key optional)
 * 3. FRED Macro Data (FREE, API key optional)
 *
 * Architecture Integration:
 * - Layer 2 reasoning agents use sentiment to weight pattern combinations
 * - Committee decisions weighted by current market sentiment
 * - Sentiment stored in chaos trades for pattern discovery
 *
 * Examples:
 * - "RSI oversold + extreme fear = 78% win rate"
 * - "MACD crossover + bull market + rising rates = 65% win rate"
 * - "Volume spike + extreme greed = 45% win rate (avoid)"
 */

import { createLogger, LogLevel } from './structured-logger';

const logger = createLogger('NewsSentimentAgent', LogLevel.INFO);

// Environment bindings interface
interface Env {
  DB: D1Database;
  SENTIMENT_CACHE?: KVNamespace;
  CRYPTOCOMPARE_API_KEY?: string;
  FRED_API_KEY?: string;
}

// API Response interfaces
interface FearGreedAPIResponse {
  data: Array<{
    value: string;
    value_classification: string;
    timestamp: string;
    time_until_update?: string;
  }>;
}

interface NewsAPIItem {
  title: string;
  body: string;
  url: string;
  source: string;
  source_info?: { name: string };
  published_on: number;
  imageurl?: string;
  tags?: string;
}

interface NewsAPIResponse {
  Data: NewsAPIItem[];
}

// ============================================================================
// Data Structures
// ============================================================================

interface FearGreedData {
  value: number; // 0-100
  value_classification: string; // 'Extreme Fear', 'Fear', 'Neutral', 'Greed', 'Extreme Greed'
  timestamp: number;
  time_until_update?: number;
}

interface NewsArticle {
  title: string;
  body: string;
  url: string;
  source: string;
  published_on: number; // Unix timestamp
  imageurl?: string;
  tags?: string;
}

interface MacroIndicator {
  indicator_name: string;
  indicator_code: string; // FEDFUNDS, CPIAUCSL, etc.
  value: number;
  date: string; // YYYY-MM-DD
  unit: string;
}

interface SentimentSnapshot {
  timestamp: string;
  fear_greed_index: number; // 0-100
  fear_greed_classification: string;
  news_sentiment: number; // -1 to +1
  news_articles_analyzed: number;
  overall_sentiment: number; // -1 to +1 (normalized)
  market_regime: 'bull' | 'bear' | 'sideways' | 'volatile';
  macro_indicators?: MacroIndicator[];
}

interface CommitteeWeighting {
  sentiment_score: number; // -1 to +1
  regime: 'bull' | 'bear' | 'sideways' | 'volatile';
  risk_level: 'low' | 'medium' | 'high' | 'extreme';
  recommended_bias: 'aggressive' | 'neutral' | 'defensive';
  fear_greed: number;
  macro_summary?: string;
}

// ============================================================================
// Fear & Greed Index Client (Always Free)
// ============================================================================

class FearGreedClient {
  private baseUrl = 'https://api.alternative.me/fng/';

  async getCurrentIndex(): Promise<FearGreedData | null> {
    try {
      const response = await fetch(this.baseUrl, {
        headers: {
          'User-Agent': 'Coinswarm-Trading-Bot/1.0'
        }
      });

      if (!response.ok) {
        logger.error('Fear & Greed API error', { status: response.status });
        return null;
      }

      const data = await response.json() as FearGreedAPIResponse;

      if (data.data && data.data.length > 0) {
        const latest = data.data[0];
        return {
          value: parseInt(latest.value),
          value_classification: latest.value_classification,
          timestamp: parseInt(latest.timestamp),
          time_until_update: latest.time_until_update ? parseInt(latest.time_until_update) : undefined
        };
      }

      return null;
    } catch (error) {
      logger.error('Fear & Greed fetch error', error instanceof Error ? error : new Error(String(error)));
      return null;
    }
  }

  async getHistorical(limit: number = 30): Promise<FearGreedData[]> {
    try {
      const response = await fetch(`${this.baseUrl}?limit=${limit}`, {
        headers: {
          'User-Agent': 'Coinswarm-Trading-Bot/1.0'
        }
      });

      if (!response.ok) {
        logger.error('Fear & Greed API error', { status: response.status });
        return [];
      }

      const data = await response.json() as FearGreedAPIResponse;

      if (data.data) {
        return data.data.map((item) => ({
          value: parseInt(item.value),
          value_classification: item.value_classification,
          timestamp: parseInt(item.timestamp)
        }));
      }

      return [];
    } catch (error) {
      logger.error('Fear & Greed historical fetch error', error instanceof Error ? error : new Error(String(error)));
      return [];
    }
  }
}

// ============================================================================
// CryptoCompare News Client (Optional, API Key)
// ============================================================================

class CryptoCompareClient {
  private baseUrl = 'https://min-api.cryptocompare.com/data/v2/news/';
  private apiKey: string | undefined;

  constructor(apiKey?: string) {
    this.apiKey = apiKey;
  }

  async getLatestNews(categories: string[] = ['BTC', 'ETH', 'SOL'], limit: number = 50): Promise<NewsArticle[]> {
    if (!this.apiKey) {
      logger.info('CryptoCompare API key not set, skipping news fetch');
      return [];
    }

    try {
      const params = new URLSearchParams({
        categories: categories.join(','),
        sortOrder: 'latest',
        limit: limit.toString()
      });

      const response = await fetch(`${this.baseUrl}?${params}`, {
        headers: {
          'Authorization': `Apikey ${this.apiKey}`,
          'User-Agent': 'Coinswarm-Trading-Bot/1.0'
        }
      });

      if (!response.ok) {
        logger.error('CryptoCompare API error', { status: response.status });
        return [];
      }

      const data = await response.json() as NewsAPIResponse;

      if (data.Data) {
        return data.Data.map((item) => ({
          title: item.title,
          body: item.body,
          url: item.url,
          source: item.source_info?.name || item.source,
          published_on: item.published_on,
          imageurl: item.imageurl,
          tags: item.tags
        }));
      }

      return [];
    } catch (error) {
      logger.error('CryptoCompare news fetch error', error instanceof Error ? error : new Error(String(error)));
      return [];
    }
  }
}

// ============================================================================
// FRED Macro Data Client (Optional, API Key)
// ============================================================================

class FREDClient {
  private baseUrl = 'https://api.stlouisfed.org/fred/series/observations';
  private apiKey: string | undefined;

  constructor(apiKey?: string) {
    this.apiKey = apiKey;
  }

  async getIndicator(seriesId: string, limit: number = 1): Promise<MacroIndicator | null> {
    if (!this.apiKey) {
      logger.info('FRED API key not set, skipping macro data fetch');
      return null;
    }

    try {
      const params = new URLSearchParams({
        series_id: seriesId,
        api_key: this.apiKey,
        file_type: 'json',
        sort_order: 'desc',
        limit: limit.toString()
      });

      const response = await fetch(`${this.baseUrl}?${params}`, {
        headers: {
          'User-Agent': 'Coinswarm-Trading-Bot/1.0'
        }
      });

      if (!response.ok) {
        logger.error('FRED API error', { series_id: seriesId, status: response.status });
        return null;
      }

      const data = await response.json() as any;

      if (data.observations && data.observations.length > 0) {
        const obs = data.observations[0];
        return {
          indicator_name: this.getIndicatorName(seriesId),
          indicator_code: seriesId,
          value: parseFloat(obs.value),
          date: obs.date,
          unit: data.units || ''
        };
      }

      return null;
    } catch (error) {
      logger.error('FRED fetch error', {
        series_id: seriesId,
        error: error instanceof Error ? error.message : String(error)
      });
      return null;
    }
  }

  async getAllMacroIndicators(): Promise<MacroIndicator[]> {
    const indicators = [
      'FEDFUNDS',    // Federal Funds Rate
      'CPIAUCSL',    // CPI (Inflation)
      'UNRATE',      // Unemployment Rate
      'DGS10',       // 10-Year Treasury Yield
      'DEXUSEU',     // USD/EUR Exchange Rate (Dollar strength)
    ];

    const results = await Promise.all(
      indicators.map(id => this.getIndicator(id))
    );

    return results.filter(r => r !== null) as MacroIndicator[];
  }

  private getIndicatorName(code: string): string {
    const names: Record<string, string> = {
      'FEDFUNDS': 'Federal Funds Rate',
      'CPIAUCSL': 'Consumer Price Index (Inflation)',
      'UNRATE': 'Unemployment Rate',
      'DGS10': '10-Year Treasury Yield',
      'DEXUSEU': 'USD/EUR Exchange Rate'
    };
    return names[code] || code;
  }
}

// ============================================================================
// Sentiment Analyzer
// ============================================================================

class SentimentAnalyzer {
  private bullishKeywords = [
    'moon', 'pump', 'surge', 'rally', 'breakout', 'bullish', 'bull',
    'all-time high', 'ath', 'adoption', 'institutional', 'upgrade',
    'partnership', 'growth', 'soar', 'skyrocket', 'record high',
    'momentum', 'breakthrough', 'accumulation', 'buying', 'buy'
  ];

  private bearishKeywords = [
    'crash', 'dump', 'plunge', 'collapse', 'bearish', 'bear',
    'regulation', 'ban', 'hack', 'scam', 'decline', 'drop', 'fall',
    'plummet', 'sell-off', 'selloff', 'fear', 'panic', 'liquidation',
    'downturn', 'correction', 'weakness', 'selling', 'sell'
  ];

  analyzeText(text: string): number {
    const lowerText = text.toLowerCase();

    let bullishCount = 0;
    let bearishCount = 0;

    for (const keyword of this.bullishKeywords) {
      const regex = new RegExp(`\\b${keyword}\\b`, 'g');
      const matches = lowerText.match(regex);
      if (matches) {
        bullishCount += matches.length;
      }
    }

    for (const keyword of this.bearishKeywords) {
      const regex = new RegExp(`\\b${keyword}\\b`, 'g');
      const matches = lowerText.match(regex);
      if (matches) {
        bearishCount += matches.length;
      }
    }

    const total = bullishCount + bearishCount;
    if (total === 0) return 0;

    // Return -1 to +1 score
    return (bullishCount - bearishCount) / total;
  }

  analyzeArticles(articles: NewsArticle[]): { score: number; analyzed: number } {
    if (articles.length === 0) {
      return { score: 0, analyzed: 0 };
    }

    let totalScore = 0;
    let validArticles = 0;

    for (const article of articles) {
      const titleScore = this.analyzeText(article.title) * 2; // Title weighted more
      const bodyScore = this.analyzeText(article.body || '');

      const articleScore = (titleScore + bodyScore) / 3;
      totalScore += articleScore;
      validArticles++;
    }

    return {
      score: validArticles > 0 ? totalScore / validArticles : 0,
      analyzed: validArticles
    };
  }
}

// ============================================================================
// Market Regime Detector
// ============================================================================

class RegimeDetector {
  detectRegime(fearGreed: number, sentiment: number, volatility?: number): 'bull' | 'bear' | 'sideways' | 'volatile' {
    // If we have volatility data, check for volatile regime first
    if (volatility !== undefined && volatility > 0.6) {
      return 'volatile';
    }

    // Fear & Greed based regime detection
    // 0-25: Extreme Fear → Bear
    // 25-45: Fear → Bear or Sideways
    // 45-55: Neutral → Sideways
    // 55-75: Greed → Bull or Sideways
    // 75-100: Extreme Greed → Bull

    if (fearGreed < 25) {
      return 'bear';
    } else if (fearGreed > 75) {
      return 'bull';
    } else if (fearGreed >= 45 && fearGreed <= 55) {
      return 'sideways';
    } else if (fearGreed > 55) {
      // Greed zone - check sentiment
      return sentiment > 0.2 ? 'bull' : 'sideways';
    } else {
      // Fear zone - check sentiment
      return sentiment < -0.2 ? 'bear' : 'sideways';
    }
  }

  getRiskLevel(fearGreed: number, regime: string): 'low' | 'medium' | 'high' | 'extreme' {
    if (fearGreed < 15 || fearGreed > 85) {
      return 'extreme'; // Extreme fear or extreme greed
    } else if (regime === 'volatile') {
      return 'high';
    } else if (regime === 'sideways') {
      return 'low';
    } else if (regime === 'bull' && fearGreed > 70) {
      return 'high'; // Bull + greed = bubble risk
    } else if (regime === 'bear' && fearGreed < 30) {
      return 'high'; // Bear + fear = capitulation risk
    } else {
      return 'medium';
    }
  }

  getRecommendedBias(regime: string, riskLevel: string): 'aggressive' | 'neutral' | 'defensive' {
    if (riskLevel === 'extreme') {
      return 'defensive';
    } else if (regime === 'bull' && riskLevel !== 'high') {
      return 'aggressive';
    } else if (regime === 'bear') {
      return 'defensive';
    } else if (regime === 'volatile') {
      return 'defensive';
    } else {
      return 'neutral';
    }
  }
}

// ============================================================================
// Main News & Sentiment Agent
// ============================================================================

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;

    const fearGreedClient = new FearGreedClient();
    const cryptoCompareClient = new CryptoCompareClient(env.CRYPTOCOMPARE_API_KEY);
    const fredClient = new FREDClient(env.FRED_API_KEY);
    const sentimentAnalyzer = new SentimentAnalyzer();
    const regimeDetector = new RegimeDetector();

    // ========================================================================
    // Route: Get Current Sentiment Snapshot
    // ========================================================================
    if (path === '/current' || path === '/') {
      try {
        // Always fetch Fear & Greed (free, no key)
        const fearGreed = await fearGreedClient.getCurrentIndex();

        if (!fearGreed) {
          return new Response(JSON.stringify({
            error: 'Failed to fetch Fear & Greed Index'
          }), { status: 500, headers: { 'Content-Type': 'application/json' } });
        }

        // Optionally fetch news (if API key available)
        const articles = await cryptoCompareClient.getLatestNews(['BTC', 'ETH', 'SOL'], 30);
        const newsAnalysis = sentimentAnalyzer.analyzeArticles(articles);

        // Normalize Fear & Greed to -1 to +1
        const fearGreedNormalized = (fearGreed.value - 50) / 50;

        // Calculate overall sentiment (weighted average)
        // If we have news, weight it 60%, fear/greed 40%
        // If no news, use fear/greed only
        let overallSentiment: number;
        if (newsAnalysis.analyzed > 0) {
          overallSentiment = (newsAnalysis.score * 0.6) + (fearGreedNormalized * 0.4);
        } else {
          overallSentiment = fearGreedNormalized;
        }

        // Detect market regime
        const regime = regimeDetector.detectRegime(fearGreed.value, overallSentiment);
        const riskLevel = regimeDetector.getRiskLevel(fearGreed.value, regime);
        const recommendedBias = regimeDetector.getRecommendedBias(regime, riskLevel);

        // Optionally fetch macro data (if API key available)
        const macroIndicators = await fredClient.getAllMacroIndicators();

        const snapshot: SentimentSnapshot = {
          timestamp: new Date().toISOString(),
          fear_greed_index: fearGreed.value,
          fear_greed_classification: fearGreed.value_classification,
          news_sentiment: newsAnalysis.score,
          news_articles_analyzed: newsAnalysis.analyzed,
          overall_sentiment: overallSentiment,
          market_regime: regime,
          macro_indicators: macroIndicators.length > 0 ? macroIndicators : undefined
        };

        // Store in D1 for historical analysis
        if (env.DB) {
          try {
            await env.DB.prepare(`
              INSERT INTO sentiment_snapshots (
                timestamp, fear_greed_index, fear_greed_classification,
                news_sentiment, news_articles_analyzed, overall_sentiment,
                market_regime, macro_indicators_json
              ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            `).bind(
              snapshot.timestamp,
              snapshot.fear_greed_index,
              snapshot.fear_greed_classification,
              snapshot.news_sentiment,
              snapshot.news_articles_analyzed,
              snapshot.overall_sentiment,
              snapshot.market_regime,
              macroIndicators.length > 0 ? JSON.stringify(macroIndicators) : null
            ).run();
          } catch (dbError) {
            logger.error('Failed to store sentiment snapshot', {
              error: dbError instanceof Error ? dbError.message : String(dbError)
            });
            // Continue anyway - not critical
          }
        }

        return new Response(JSON.stringify(snapshot, null, 2), {
          headers: { 'Content-Type': 'application/json' }
        });
      } catch (error) {
        logger.error('Error fetching current sentiment', error instanceof Error ? error : new Error(String(error)));
        return new Response(JSON.stringify({
          error: 'Failed to fetch current sentiment',
          details: error instanceof Error ? error.message : 'Unknown error'
        }), { status: 500, headers: { 'Content-Type': 'application/json' } });
      }
    }

    // ========================================================================
    // Route: Get Committee Weighting
    // ========================================================================
    if (path === '/committee-weighting') {
      try {
        const fearGreed = await fearGreedClient.getCurrentIndex();

        if (!fearGreed) {
          return new Response(JSON.stringify({
            error: 'Failed to fetch Fear & Greed Index'
          }), { status: 500, headers: { 'Content-Type': 'application/json' } });
        }

        const articles = await cryptoCompareClient.getLatestNews(['BTC', 'ETH', 'SOL'], 30);
        const newsAnalysis = sentimentAnalyzer.analyzeArticles(articles);

        const fearGreedNormalized = (fearGreed.value - 50) / 50;
        const overallSentiment = newsAnalysis.analyzed > 0
          ? (newsAnalysis.score * 0.6) + (fearGreedNormalized * 0.4)
          : fearGreedNormalized;

        const regime = regimeDetector.detectRegime(fearGreed.value, overallSentiment);
        const riskLevel = regimeDetector.getRiskLevel(fearGreed.value, regime);
        const recommendedBias = regimeDetector.getRecommendedBias(regime, riskLevel);

        // Get latest macro snapshot if available
        const macroIndicators = await fredClient.getAllMacroIndicators();
        let macroSummary: string | undefined;

        if (macroIndicators.length > 0) {
          const fedRate = macroIndicators.find(i => i.indicator_code === 'FEDFUNDS');
          const cpi = macroIndicators.find(i => i.indicator_code === 'CPIAUCSL');
          const unemployment = macroIndicators.find(i => i.indicator_code === 'UNRATE');

          macroSummary = [
            fedRate ? `Fed Rate: ${fedRate.value}%` : null,
            cpi ? `CPI: ${cpi.value}` : null,
            unemployment ? `Unemployment: ${unemployment.value}%` : null
          ].filter(Boolean).join(' | ');
        }

        const weighting: CommitteeWeighting = {
          sentiment_score: overallSentiment,
          regime: regime,
          risk_level: riskLevel,
          recommended_bias: recommendedBias,
          fear_greed: fearGreed.value,
          macro_summary: macroSummary
        };

        return new Response(JSON.stringify(weighting, null, 2), {
          headers: { 'Content-Type': 'application/json' }
        });
      } catch (error) {
        logger.error('Error generating committee weighting', error instanceof Error ? error : new Error(String(error)));
        return new Response(JSON.stringify({
          error: 'Failed to generate committee weighting',
          details: error instanceof Error ? error.message : 'Unknown error'
        }), { status: 500, headers: { 'Content-Type': 'application/json' } });
      }
    }

    // ========================================================================
    // Route: Get Historical Sentiment
    // ========================================================================
    if (path === '/historical') {
      try {
        const limitParam = url.searchParams.get('limit');
        const limit = limitParam ? parseInt(limitParam) : 30;

        const historical = await fearGreedClient.getHistorical(limit);

        return new Response(JSON.stringify({
          count: historical.length,
          data: historical
        }, null, 2), {
          headers: { 'Content-Type': 'application/json' }
        });
      } catch (error) {
        logger.error('Error fetching historical sentiment', error instanceof Error ? error : new Error(String(error)));
        return new Response(JSON.stringify({
          error: 'Failed to fetch historical sentiment',
          details: error instanceof Error ? error.message : 'Unknown error'
        }), { status: 500, headers: { 'Content-Type': 'application/json' } });
      }
    }

    // ========================================================================
    // Route: Get Latest News
    // ========================================================================
    if (path === '/news') {
      try {
        const limitParam = url.searchParams.get('limit');
        const limit = limitParam ? parseInt(limitParam) : 50;

        const articles = await cryptoCompareClient.getLatestNews(['BTC', 'ETH', 'SOL'], limit);
        const analysis = sentimentAnalyzer.analyzeArticles(articles);

        return new Response(JSON.stringify({
          count: articles.length,
          sentiment_score: analysis.score,
          articles: articles.slice(0, 20) // Return first 20 for brevity
        }, null, 2), {
          headers: { 'Content-Type': 'application/json' }
        });
      } catch (error) {
        logger.error('Error fetching news', error instanceof Error ? error : new Error(String(error)));
        return new Response(JSON.stringify({
          error: 'Failed to fetch news',
          details: error instanceof Error ? error.message : 'Unknown error'
        }), { status: 500, headers: { 'Content-Type': 'application/json' } });
      }
    }

    // ========================================================================
    // Route: Get Macro Indicators
    // ========================================================================
    if (path === '/macro') {
      try {
        const indicators = await fredClient.getAllMacroIndicators();

        return new Response(JSON.stringify({
          count: indicators.length,
          indicators: indicators
        }, null, 2), {
          headers: { 'Content-Type': 'application/json' }
        });
      } catch (error) {
        logger.error('Error fetching macro indicators', error instanceof Error ? error : new Error(String(error)));
        return new Response(JSON.stringify({
          error: 'Failed to fetch macro indicators',
          details: error instanceof Error ? error.message : 'Unknown error'
        }), { status: 500, headers: { 'Content-Type': 'application/json' } });
      }
    }

    // ========================================================================
    // Route: Version Information
    // ========================================================================
    if (path === '/version') {
      return new Response(JSON.stringify({
        worker: 'news-sentiment-agent',
        version: '2.1.0',
        branch: 'claude/incomplete-description-011CUutLehm75rEefmt5WYQj',
        deployed_at: '2025-11-08T11:52:00Z',
        phase: 'Phase 3 - Code Quality Improvements',
        changes: [
          'Added version endpoint for deployment tracking',
          'Ready for structured logging migration'
        ]
      }, null, 2), {
        headers: { 'Content-Type': 'application/json' }
      });
    }

    return new Response('News & Sentiment Agent\n\nRoutes:\n- GET / or /current - Current sentiment snapshot\n- GET /committee-weighting - Committee weighting recommendation\n- GET /historical?limit=30 - Historical Fear & Greed data\n- GET /news?limit=50 - Latest news articles with sentiment\n- GET /macro - Current macro indicators\n- GET /version - Version and deployment info', {
      headers: { 'Content-Type': 'text/plain' }
    });
  }
};
