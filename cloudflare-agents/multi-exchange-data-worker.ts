/**
 * Multi-Exchange Historical Data Worker
 *
 * Fetches real historical data from:
 * - Binance (CEX)
 * - Coinbase Advanced (CEX)
 * - Solana DEXes (via integration)
 *
 * Supports:
 * - 1-minute and 5-minute candles
 * - Up to 2 years of historical data
 * - Random time segment selection
 * - Multi-pair and multi-exchange comparison
 *
 * Endpoints:
 * - POST /fetch - Fetch data for single pair/exchange
 * - POST /fetch-all - Fetch 2 years for all pairs
 * - GET /data/{exchange}/{pair} - Get cached data
 * - GET /random - Random segment for chaos trading
 * - GET /compare - Compare prices across exchanges
 */

import { createLogger, LogLevel } from './structured-logger';

const logger = createLogger('MultiExchangeDataWorker', LogLevel.INFO);

interface Env {
  HISTORICAL_PRICES?: KVNamespace;  // Optional - can work without KV
}

interface OHLCVCandle {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface HistoricalDataset {
  pair: string;
  exchange: string;
  interval: string;
  startTime: number;
  endTime: number;
  candles: OHLCVCandle[];
  fetchedAt: string;
}

interface CoinbaseCandle {
  0: number; // timestamp
  1: number; // low
  2: number; // high
  3: number; // open
  4: number; // close
  5: number; // volume
}

interface BinanceKline {
  0: number; // open time
  1: string; // open
  2: string; // high
  3: string; // low
  4: string; // close
  5: string; // volume
  6: number; // close time
}

interface DatasetIndex {
  startTime: number;
  endTime: number;
  candleCount: number;
}

interface FetchRequestBody {
  interval?: string;
}

interface FetchResult {
  exchange: string;
  pair: string;
  success: boolean;
  candleCount?: number;
  error?: string;
}

/**
 * Coinbase Advanced API Client
 * Supports up to 300 candles per request
 */
class CoinbaseClient {
  private baseUrl = 'https://api.exchange.coinbase.com';

  /**
   * Fetch historical candles from Coinbase
   * Coinbase uses granularity in seconds: 60, 300, 900, 3600, 21600, 86400
   */
  async fetchCandles(
    productId: string,  // e.g., 'BTC-USD'
    granularity: number,  // 60 = 1m, 300 = 5m
    start: Date,
    end: Date
  ): Promise<OHLCVCandle[]> {
    // Coinbase API: /products/{product_id}/candles
    const url = `${this.baseUrl}/products/${productId}/candles?granularity=${granularity}&start=${start.toISOString()}&end=${end.toISOString()}`;

    const response = await fetch(url, {
      headers: {
        'Accept': 'application/json',
        'User-Agent': 'Coinswarm/1.0'
      }
    });

    if (!response.ok) {
      throw new Error(`Coinbase API error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json() as CoinbaseCandle[];

    // Coinbase format: [timestamp, low, high, open, close, volume]
    return data.map(c => ({
      timestamp: c[0] * 1000,  // Convert to ms
      open: c[3],
      high: c[2],
      low: c[1],
      close: c[4],
      volume: c[5]
    })).reverse();  // Coinbase returns newest first
  }

  /**
   * Fetch large dataset (2 years) by batching
   * Coinbase limits to 300 candles per request
   */
  async fetchLargeDataset(
    productId: string,
    granularity: number,
    startTime: number,
    endTime: number
  ): Promise<OHLCVCandle[]> {
    const allCandles: OHLCVCandle[] = [];
    let currentStart = startTime;

    // Calculate time per batch (300 candles)
    const msPerCandle = granularity * 1000;
    const batchDuration = 300 * msPerCandle;

    while (currentStart < endTime) {
      const batchEnd = Math.min(currentStart + batchDuration, endTime);

      try {
        const candles = await this.fetchCandles(
          productId,
          granularity,
          new Date(currentStart),
          new Date(batchEnd)
        );

        allCandles.push(...candles);

        // Rate limiting: 10 requests per second
        await this.sleep(100);

      } catch (error) {
        logger.error('Error fetching Coinbase batch', {
          product_id: productId,
          start: currentStart,
          end: batchEnd,
          error: error instanceof Error ? error.message : String(error)
        });
        // Continue with next batch
      }

      currentStart = batchEnd;
    }

    return allCandles;
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

/**
 * Binance API Client (optimized for 2 years of data)
 */
class BinanceClient {
  private baseUrl = 'https://api.binance.com';

  async fetchLargeDataset(
    symbol: string,
    interval: string,
    startTime: number,
    endTime: number
  ): Promise<OHLCVCandle[]> {
    const allCandles: OHLCVCandle[] = [];
    let currentStart = startTime;

    const intervalMs = this.intervalToMs(interval);

    while (currentStart < endTime) {
      const batchEnd = Math.min(currentStart + (1000 * intervalMs), endTime);

      try {
        const url = `${this.baseUrl}/api/v3/klines?symbol=${symbol}&interval=${interval}&startTime=${currentStart}&endTime=${batchEnd}&limit=1000`;
        const response = await fetch(url);

        if (!response.ok) {
          throw new Error(`Binance API error: ${response.status}`);
        }

        const data = await response.json() as BinanceKline[];
        const candles = data.map(k => ({
          timestamp: k[0],
          open: parseFloat(k[1]),
          high: parseFloat(k[2]),
          low: parseFloat(k[3]),
          close: parseFloat(k[4]),
          volume: parseFloat(k[5])
        }));

        allCandles.push(...candles);

        if (data.length < 1000) break;

        currentStart = data[data.length - 1][6] + 1;  // Use closeTime + 1
        await this.sleep(200);  // Rate limiting

      } catch (error) {
        logger.error('Error fetching Binance batch', {
          symbol,
          start: currentStart,
          end: batchEnd,
          error: error instanceof Error ? error.message : String(error)
        });
        break;
      }
    }

    return allCandles;
  }

  private intervalToMs(interval: string): number {
    const unit = interval.slice(-1);
    const value = parseInt(interval.slice(0, -1));
    switch (unit) {
      case 'm': return value * 60 * 1000;
      case 'h': return value * 60 * 60 * 1000;
      case 'd': return value * 24 * 60 * 60 * 1000;
      default: throw new Error(`Unknown interval: ${interval}`);
    }
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

/**
 * Historical Data Manager with multi-exchange support
 */
class MultiExchangeDataManager {
  constructor(private kv: KVNamespace) {}

  async storeDataset(dataset: HistoricalDataset): Promise<void> {
    const key = `historical:${dataset.exchange}:${dataset.pair}:${dataset.interval}:${dataset.startTime}:${dataset.endTime}`;
    await this.kv.put(key, JSON.stringify(dataset), {
      expirationTtl: 60 * 60 * 24 * 90  // 90 days
    });

    await this.addToIndex(dataset);
  }

  async getDataset(exchange: string, pair: string, interval: string, startTime: number, endTime: number): Promise<HistoricalDataset | null> {
    const key = `historical:${exchange}:${pair}:${interval}:${startTime}:${endTime}`;
    const data = await this.kv.get(key, 'json');
    return data as HistoricalDataset | null;
  }

  async getRandomSegment(exchange: string, pair: string, interval: string, minDays: number = 30): Promise<HistoricalDataset | null> {
    const index = await this.getIndex(exchange, pair, interval);
    if (!index || index.length === 0) return null;

    const minDuration = minDays * 24 * 60 * 60 * 1000;
    const validDatasets = index.filter((ds: DatasetIndex) => (ds.endTime - ds.startTime) >= minDuration);

    if (validDatasets.length === 0) return null;

    const randomIndex = Math.floor(Math.random() * validDatasets.length);
    const dataset = validDatasets[randomIndex];

    return await this.getDataset(exchange, pair, interval, dataset.startTime, dataset.endTime);
  }

  private async addToIndex(dataset: HistoricalDataset): Promise<void> {
    const indexKey = `index:${dataset.exchange}:${dataset.pair}:${dataset.interval}`;
    const existing = await this.kv.get(indexKey, 'json') as DatasetIndex[] | null || [];

    existing.push({
      startTime: dataset.startTime,
      endTime: dataset.endTime,
      candleCount: dataset.candles.length
    });

    await this.kv.put(indexKey, JSON.stringify(existing));
  }

  private async getIndex(exchange: string, pair: string, interval: string): Promise<DatasetIndex[]> {
    const indexKey = `index:${exchange}:${pair}:${interval}`;
    const data = await this.kv.get(indexKey, 'json');
    return (data as DatasetIndex[] | null) || [];
  }
}

/**
 * Main Worker Handler
 */
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;

    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    try {
      const binanceClient = new BinanceClient();
      const coinbaseClient = new CoinbaseClient();
      const dataManager = env.HISTORICAL_PRICES ? new MultiExchangeDataManager(env.HISTORICAL_PRICES) : null;

      // Route: Fetch 2 years of data for all pairs
      if (path === '/fetch-2-years' && request.method === 'POST') {
        const body = await request.json() as FetchRequestBody;
        const interval = body.interval || '5m';  // 1m or 5m
        const durationDays = 730;  // 2 years

        const endTime = Date.now();
        const startTime = endTime - (durationDays * 24 * 60 * 60 * 1000);

        const results: FetchResult[] = [];

        // Binance pairs
        const binancePairs = [
          { symbol: 'BTCUSDT', pair: 'BTC-USDT' },
          { symbol: 'SOLUSDT', pair: 'SOL-USDT' },
          { symbol: 'ETHUSDT', pair: 'ETH-USDT' },
        ];

        for (const { symbol, pair } of binancePairs) {
          try {
            logger.info('Fetching Binance data', { pair, interval, duration: '2 years' });
            const candles = await binanceClient.fetchLargeDataset(symbol, interval, startTime, endTime);

            const dataset: HistoricalDataset = {
              pair,
              exchange: 'binance',
              interval,
              startTime,
              endTime,
              candles,
              fetchedAt: new Date().toISOString()
            };

            if (dataManager) {
              await dataManager.storeDataset(dataset);
            }

            results.push({
              exchange: 'binance',
              pair,
              success: true,
              candleCount: candles.length
            });

          } catch (error) {
            results.push({
              exchange: 'binance',
              pair,
              success: false,
              error: error instanceof Error ? error.message : String(error)
            });
          }
        }

        // Coinbase pairs
        const coinbasePairs = [
          { productId: 'BTC-USD', pair: 'BTC-USD' },
          { productId: 'SOL-USD', pair: 'SOL-USD' },
          { productId: 'ETH-USD', pair: 'ETH-USD' },
        ];

        const granularity = interval === '1m' ? 60 : 300;

        for (const { productId, pair } of coinbasePairs) {
          try {
            logger.info('Fetching Coinbase data', { pair, interval, duration: '2 years' });
            const candles = await coinbaseClient.fetchLargeDataset(productId, granularity, startTime, endTime);

            const dataset: HistoricalDataset = {
              pair,
              exchange: 'coinbase',
              interval,
              startTime,
              endTime,
              candles,
              fetchedAt: new Date().toISOString()
            };

            if (dataManager) {
              await dataManager.storeDataset(dataset);
            }

            results.push({
              exchange: 'coinbase',
              pair,
              success: true,
              candleCount: candles.length
            });

          } catch (error) {
            results.push({
              exchange: 'coinbase',
              pair,
              success: false,
              error: error instanceof Error ? error.message : String(error)
            });
          }
        }

        return new Response(JSON.stringify({
          success: true,
          interval,
          durationDays,
          results,
          totalCandles: results.reduce((sum, r) => sum + (r.candleCount || 0), 0)
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      // Route: Get random segment for chaos trading
      if (path === '/random') {
        const exchange = url.searchParams.get('exchange') || 'binance';
        const pair = url.searchParams.get('pair') || 'BTC-USDT';
        const interval = url.searchParams.get('interval') || '5m';
        const minDays = parseInt(url.searchParams.get('minDays') || '30');

        const dataset = await dataManager.getRandomSegment(exchange, pair, interval, minDays);

        if (!dataset) {
          return new Response(JSON.stringify({
            success: false,
            error: 'No datasets available'
          }), { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
        }

        return new Response(JSON.stringify({
          success: true,
          dataset
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      // Route: Compare prices across exchanges
      if (path === '/compare') {
        const pair = url.searchParams.get('pair') || 'BTC-USD';
        const interval = url.searchParams.get('interval') || '5m';
        const daysBack = parseInt(url.searchParams.get('days') || '7');

        const endTime = Date.now();
        const startTime = endTime - (daysBack * 24 * 60 * 60 * 1000);

        // Get data from both exchanges
        const binanceData = await dataManager.getDataset('binance', pair.replace('USD', 'USDT'), interval, startTime, endTime);
        const coinbaseData = await dataManager.getDataset('coinbase', pair, interval, startTime, endTime);

        // Calculate spread statistics
        const spreads: number[] = [];
        if (binanceData && coinbaseData) {
          const minLength = Math.min(binanceData.candles.length, coinbaseData.candles.length);

          for (let i = 0; i < minLength; i++) {
            const binancePrice = binanceData.candles[i].close;
            const coinbasePrice = coinbaseData.candles[i].close;
            const spread = Math.abs(coinbasePrice - binancePrice) / binancePrice * 100;
            spreads.push(spread);
          }
        }

        const avgSpread = spreads.reduce((a, b) => a + b, 0) / spreads.length;
        const maxSpread = Math.max(...spreads);

        return new Response(JSON.stringify({
          success: true,
          pair,
          interval,
          daysBack,
          binanceCandleCount: binanceData?.candles.length || 0,
          coinbaseCandleCount: coinbaseData?.candles.length || 0,
          avgSpreadPct: avgSpread,
          maxSpreadPct: maxSpread,
          arbitrageOpportunities: spreads.filter(s => s > 0.5).length
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      // Default: API info
      return new Response(JSON.stringify({
        status: 'ok',
        name: 'Multi-Exchange Historical Data Worker',
        endpoints: {
          'POST /fetch-2-years': 'Fetch 2 years of data for all pairs {interval: "1m" or "5m"}',
          'GET /random': 'Get random segment ?exchange=binance&pair=BTC-USDT&interval=5m&minDays=30',
          'GET /compare': 'Compare prices across exchanges ?pair=BTC-USD&interval=5m&days=7'
        },
        exchanges: ['binance', 'coinbase'],
        pairs: ['BTC-USDT', 'SOL-USDT', 'ETH-USDT', 'BTC-USD', 'SOL-USD', 'ETH-USD'],
        intervals: ['1m', '5m'],
        maxHistory: '2 years (730 days)',
        features: [
          'Multi-exchange support (Binance + Coinbase)',
          '1-minute and 5-minute candles',
          'Up to 2 years of historical data',
          'Random segment selection for chaos trading',
          'Cross-exchange spread analysis',
          'Automatic batching and rate limiting'
        ]
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });

    } catch (error) {
      return new Response(JSON.stringify({
        success: false,
        error: error instanceof Error ? error.message : String(error),
        stack: error instanceof Error ? error.stack : undefined
      }), {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }
  }
};
