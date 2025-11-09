/**
 * Historical Data Worker for Cloudflare
 *
 * Fetches real historical price data from Binance and stores in KV
 * Supports 5-minute candles for maximum granularity
 * Enables random time segment selection for backtesting
 *
 * Endpoints:
 * - POST /fetch - Fetch historical data from Binance
 * - GET /data/{pair}/{start}/{end} - Get cached historical data
 * - GET /random - Get random time segment for testing
 * - GET /pairs - List available pairs
 */

interface Env {
  HISTORICAL_PRICES?: KVNamespace;  // Optional until KV namespace is created
}

interface BinanceKline {
  openTime: number;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: string;
  closeTime: number;
  quoteAssetVolume: string;
  numberOfTrades: number;
  takerBuyBaseAssetVolume: string;
  takerBuyQuoteAssetVolume: string;
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
  interval: string;
  startTime: number;
  endTime: number;
  candles: OHLCVCandle[];
  fetchedAt: string;
}

// Multi-pair configuration
const PAIRS = [
  { symbol: 'BTCUSDT', pair: 'BTC-USDT' },
  { symbol: 'BTCUSDC', pair: 'BTC-USDC' },
  { symbol: 'BTCBUSD', pair: 'BTC-BUSD' },
  { symbol: 'SOLUSDT', pair: 'SOL-USDT' },
  { symbol: 'SOLUSDC', pair: 'SOL-USDC' },
  { symbol: 'SOLBUSD', pair: 'SOL-BUSD' },
  { symbol: 'ETHUSDT', pair: 'ETH-USDT' },
  { symbol: 'ETHUSDC', pair: 'ETH-USDC' },
  { symbol: 'ETHBUSD', pair: 'ETH-BUSD' },
  { symbol: 'BTCSOL', pair: 'BTC-SOL' },  // Cross pair if available
];

/**
 * Binance API Client
 * Fetches real historical klines (candlestick) data
 */
class BinanceClient {
  private baseUrl = 'https://data.binance.com';  // Public data API - not region restricted

  /**
   * Fetch historical klines from Binance
   *
   * @param symbol - Binance symbol (e.g., 'BTCUSDT')
   * @param interval - Timeframe ('1m', '5m', '15m', '1h', '1d')
   * @param startTime - Start timestamp (ms)
   * @param endTime - End timestamp (ms)
   * @param limit - Max candles per request (default 1000, max 1000)
   */
  async fetchKlines(
    symbol: string,
    interval: string,
    startTime: number,
    endTime: number,
    limit: number = 1000
  ): Promise<BinanceKline[]> {
    const url = `${this.baseUrl}/api/v3/klines?symbol=${symbol}&interval=${interval}&startTime=${startTime}&endTime=${endTime}&limit=${limit}`;

    const response = await fetch(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json'
      }
    });
    if (!response.ok) {
      throw new Error(`Binance API error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json() as Array<[number, string, string, string, string, string, number, string, number, string, string]>;

    // Parse Binance kline format
    return data.map(k => ({
      openTime: k[0],
      open: k[1],
      high: k[2],
      low: k[3],
      close: k[4],
      volume: k[5],
      closeTime: k[6],
      quoteAssetVolume: k[7],
      numberOfTrades: k[8],
      takerBuyBaseAssetVolume: k[9],
      takerBuyQuoteAssetVolume: k[10]
    }));
  }

  /**
   * Fetch large historical datasets by batching requests
   * Binance limits to 1000 candles per request
   */
  async fetchLargeDataset(
    symbol: string,
    interval: string,
    startTime: number,
    endTime: number
  ): Promise<OHLCVCandle[]> {
    const allCandles: OHLCVCandle[] = [];
    let currentStart = startTime;

    // Calculate interval duration in ms
    const intervalMs = this.intervalToMs(interval);

    // Fetch in batches of 1000 candles
    while (currentStart < endTime) {
      const batchEnd = Math.min(currentStart + (1000 * intervalMs), endTime);

      const klines = await this.fetchKlines(symbol, interval, currentStart, batchEnd, 1000);

      const candles = klines.map(k => ({
        timestamp: k.openTime,
        open: parseFloat(k.open),
        high: parseFloat(k.high),
        low: parseFloat(k.low),
        close: parseFloat(k.close),
        volume: parseFloat(k.volume)
      }));

      allCandles.push(...candles);

      if (klines.length < 1000) {
        // No more data available
        break;
      }

      // Move to next batch
      currentStart = klines[klines.length - 1].closeTime + 1;

      // Rate limiting: wait 200ms between requests
      await this.sleep(200);
    }

    return allCandles;
  }

  /**
   * Convert interval string to milliseconds
   */
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
 * Historical Data Manager
 * Manages storage and retrieval of historical data in KV
 */
class HistoricalDataManager {
  constructor(private kv: KVNamespace) {}

  /**
   * Store historical dataset in KV
   */
  async storeDataset(dataset: HistoricalDataset): Promise<void> {
    const key = this.buildKey(dataset.pair, dataset.interval, dataset.startTime, dataset.endTime);
    await this.kv.put(key, JSON.stringify(dataset), {
      expirationTtl: 60 * 60 * 24 * 30 // 30 days
    });

    // Also store in index for listing
    await this.addToIndex(dataset);
  }

  /**
   * Get historical dataset from KV
   */
  async getDataset(pair: string, interval: string, startTime: number, endTime: number): Promise<HistoricalDataset | null> {
    const key = this.buildKey(pair, interval, startTime, endTime);
    const data = await this.kv.get(key, 'json');
    return data as HistoricalDataset | null;
  }

  /**
   * Get random time segment for testing
   * Returns 30+ day segment from available historical data
   */
  async getRandomSegment(pair: string, interval: string, minDays: number = 30): Promise<HistoricalDataset | null> {
    // Get index of available datasets
    const index = await this.getIndex(pair, interval);
    if (!index || index.length === 0) {
      return null;
    }

    // Find datasets with sufficient length
    const minDuration = minDays * 24 * 60 * 60 * 1000;
    const validDatasets = index.filter(ds => (ds.endTime - ds.startTime) >= minDuration);

    if (validDatasets.length === 0) {
      return null;
    }

    // Pick random dataset
    const randomIndex = Math.floor(Math.random() * validDatasets.length);
    const dataset = validDatasets[randomIndex];

    // Return full dataset or random sub-segment
    return await this.getDataset(pair, interval, dataset.startTime, dataset.endTime);
  }

  /**
   * List all available pairs
   */
  async listPairs(): Promise<string[]> {
    const pairsJson = await this.kv.get('index:pairs', 'json');
    return (pairsJson as string[]) || [];
  }

  private buildKey(pair: string, interval: string, startTime: number, endTime: number): string {
    return `historical:${pair}:${interval}:${startTime}:${endTime}`;
  }

  private async addToIndex(dataset: HistoricalDataset): Promise<void> {
    const indexKey = `index:${dataset.pair}:${dataset.interval}`;
    const existing = await this.kv.get(indexKey, 'json') as any[] || [];

    existing.push({
      startTime: dataset.startTime,
      endTime: dataset.endTime,
      candleCount: dataset.candles.length
    });

    await this.kv.put(indexKey, JSON.stringify(existing));

    // Update pairs index
    const pairs = await this.listPairs();
    if (!pairs.includes(dataset.pair)) {
      pairs.push(dataset.pair);
      await this.kv.put('index:pairs', JSON.stringify(pairs));
    }
  }

  private async getIndex(pair: string, interval: string): Promise<any[]> {
    const indexKey = `index:${pair}:${interval}`;
    const data = await this.kv.get(indexKey, 'json');
    return (data as any[]) || [];
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
      const dataManager = env.HISTORICAL_PRICES ? new HistoricalDataManager(env.HISTORICAL_PRICES) : null;

      // Route: Fetch fresh data from Binance (no caching)
      if (path === '/fetch-fresh' && request.method === 'GET') {
        const symbol = url.searchParams.get('symbol') || 'BTCUSDT';
        const interval = url.searchParams.get('interval') || '5m';
        const limit = parseInt(url.searchParams.get('limit') || '500');

        const endTime = Date.now();
        const startTime = endTime - (limit * 5 * 60 * 1000); // 5 minutes per candle

        const candles = await binanceClient.fetchLargeDataset(symbol, interval, startTime, endTime);

        return new Response(JSON.stringify({
          success: true,
          symbol,
          interval,
          candles,
          candleCount: candles.length,
          startTime,
          endTime,
          cached: false
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      // Route: Fetch historical data from Binance
      if (path === '/fetch' && request.method === 'POST') {
        if (!dataManager) {
          return new Response(JSON.stringify({
            success: false,
            error: 'KV storage not configured. Use /fetch-fresh endpoint instead.'
          }), { status: 503, headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
        }

        const body = await request.json() as any;
        const { symbol, pair, interval, startTime, endTime } = body;

        // Validate
        if (!symbol || !pair || !interval || !startTime || !endTime) {
          return new Response(JSON.stringify({
            success: false,
            error: 'Missing required fields: symbol, pair, interval, startTime, endTime'
          }), { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
        }

        // Fetch from Binance
        const candles = await binanceClient.fetchLargeDataset(symbol, interval, startTime, endTime);

        // Store in KV
        const dataset: HistoricalDataset = {
          pair,
          interval,
          startTime,
          endTime,
          candles,
          fetchedAt: new Date().toISOString()
        };

        await dataManager.storeDataset(dataset);

        return new Response(JSON.stringify({
          success: true,
          pair,
          interval,
          candleCount: candles.length,
          startTime,
          endTime,
          durationDays: (endTime - startTime) / (1000 * 60 * 60 * 24)
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      // Route: Fetch all pairs (multi-pair)
      if (path === '/fetch-all' && request.method === 'POST') {
        const body = await request.json() as any;
        const { interval, durationDays } = body;

        const endTime = Date.now();
        const startTime = endTime - (durationDays * 24 * 60 * 60 * 1000);

        const results = [];

        for (const { symbol, pair } of PAIRS) {
          try {
            const candles = await binanceClient.fetchLargeDataset(symbol, interval, startTime, endTime);

            const dataset: HistoricalDataset = {
              pair,
              interval,
              startTime,
              endTime,
              candles,
              fetchedAt: new Date().toISOString()
            };

            await dataManager.storeDataset(dataset);

            results.push({
              pair,
              success: true,
              candleCount: candles.length
            });
          } catch (error) {
            const err = error instanceof Error ? error : new Error(String(error));
            results.push({
              pair,
              success: false,
              error: err.message
            });
          }

          // Rate limiting between pairs
          await new Promise(resolve => setTimeout(resolve, 500));
        }

        return new Response(JSON.stringify({
          success: true,
          interval,
          durationDays,
          results
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      // Route: Get cached data
      if (path.startsWith('/data/')) {
        const parts = path.split('/').filter(p => p);
        // Format: /data/{pair}/{interval}/{startTime}/{endTime}
        if (parts.length === 5) {
          const [_, pair, interval, startStr, endStr] = parts;
          const startTime = parseInt(startStr);
          const endTime = parseInt(endStr);

          const dataset = await dataManager.getDataset(pair, interval, startTime, endTime);

          if (!dataset) {
            return new Response(JSON.stringify({
              success: false,
              error: 'Dataset not found'
            }), { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
          }

          return new Response(JSON.stringify({
            success: true,
            dataset
          }), {
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          });
        }
      }

      // Route: Get random time segment
      if (path === '/random') {
        const pair = url.searchParams.get('pair') || 'BTC-USDT';
        const interval = url.searchParams.get('interval') || '5m';
        const minDays = parseInt(url.searchParams.get('minDays') || '30');

        const dataset = await dataManager.getRandomSegment(pair, interval, minDays);

        if (!dataset) {
          return new Response(JSON.stringify({
            success: false,
            error: 'No datasets available for random selection'
          }), { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
        }

        return new Response(JSON.stringify({
          success: true,
          dataset
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      // Route: List available pairs
      if (path === '/pairs') {
        const pairs = await dataManager.listPairs();

        return new Response(JSON.stringify({
          success: true,
          pairs,
          configured: PAIRS.map(p => p.pair)
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      // Default: API info
      return new Response(JSON.stringify({
        status: 'ok',
        name: 'Coinswarm Historical Data Worker',
        endpoints: {
          'POST /fetch': 'Fetch historical data from Binance for single pair {symbol, pair, interval, startTime, endTime}',
          'POST /fetch-all': 'Fetch historical data for all configured pairs {interval, durationDays}',
          'GET /data/{pair}/{interval}/{start}/{end}': 'Get cached historical data',
          'GET /random': 'Get random time segment for testing ?pair=BTC-USDT&interval=5m&minDays=30',
          'GET /pairs': 'List available pairs'
        },
        features: [
          'Real historical data from Binance',
          '5-minute candles for maximum granularity',
          'Multi-pair support (BTC, SOL, ETH × USDT, USDC, BUSD)',
          'Cross pairs (BTC-SOL)',
          'Random time segment selection for unbiased testing',
          'Automatic batching for large datasets (>1000 candles)',
          'KV storage with 30-day expiration'
        ],
        pairs: PAIRS.map(p => p.pair)
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });

    } catch (error) {
      const err = error instanceof Error ? error : new Error(String(error));
      return new Response(JSON.stringify({
        success: false,
        error: err.message,
        stack: err.stack
      }), {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }
  }
};
