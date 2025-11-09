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
 * Binance.US API Client
 * Fetches real historical klines (candlestick) data from Binance.US
 *
 * Rate Limits:
 * - Weight-based: 6000 weight per minute for API keys, 1200 for IP
 * - Hard limit: 20 orders per second, 160,000 orders per day
 * - Klines endpoint: 1 weight per request, max 1000 candles per request
 *
 * Documentation: https://docs.binance.us/
 */
class BinanceClient {
  private baseUrl = 'https://api.binance.us';  // Binance.US API endpoint

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

    const data = await response.json() as Array<[number, string, string, string, string, string, number, string, number, string, number, string]>;

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
 * CoinGecko API Client
 * Free API with OHLC data - no API key required
 *
 * Rate Limits (Free/Demo Plan):
 * - 30 calls per minute (with free Demo account registration)
 * - 10,000 calls per month
 * - Public API (no registration): 5-15 calls per minute
 *
 * Paid plans: 500-1000 calls/min
 * Documentation: https://www.coingecko.com/en/api/pricing
 */
class CoinGeckoClient {
  private baseUrl = 'https://api.coingecko.com/api/v3';

  /**
   * Fetch OHLC data from CoinGecko
   * Note: CoinGecko uses different intervals (days back)
   */
  async fetchOHLC(coinId: string, days: number = 30): Promise<OHLCVCandle[]> {
    // CoinGecko OHLC endpoint: /coins/{id}/ohlc?vs_currency=usd&days={days}
    const url = `${this.baseUrl}/coins/${coinId}/ohlc?vs_currency=usd&days=${days}`;

    const response = await fetch(url, {
      headers: {
        'Accept': 'application/json'
      }
    });

    if (!response.ok) {
      throw new Error(`CoinGecko API error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json() as Array<[number, number, number, number, number]>;

    // CoinGecko format: [timestamp, open, high, low, close]
    // No volume in OHLC endpoint
    return data.map(candle => ({
      timestamp: candle[0],
      open: candle[1],
      high: candle[2],
      low: candle[3],
      close: candle[4],
      volume: 0 // CoinGecko OHLC doesn't include volume
    }));
  }

  /**
   * Map common symbols to CoinGecko IDs
   */
  private getCoinId(symbol: string): string {
    const mapping: { [key: string]: string } = {
      'BTCUSDT': 'bitcoin',
      'ETHUSDT': 'ethereum',
      'SOLUSDT': 'solana',
      'BNBUSDT': 'binancecoin',
      'ADAUSDT': 'cardano',
      'DOTUSDT': 'polkadot'
    };
    return mapping[symbol] || 'bitcoin';
  }

  async fetchForSymbol(symbol: string, days: number = 30): Promise<OHLCVCandle[]> {
    const coinId = this.getCoinId(symbol);
    return await this.fetchOHLC(coinId, days);
  }
}

/**
 * CryptoCompare API Client
 * Free tier with good limits - supports minute-level data
 *
 * Rate Limits (Free Tier):
 * - ~30 calls per minute (with free API key registration)
 * - Few thousand calls per day
 * - Requires API key for stable limits
 *
 * Paid plans: Start at $80/month for ~100k calls/month
 * Documentation: https://min-api.cryptocompare.com/pricing
 */
class CryptoCompareClient {
  private baseUrl = 'https://min-api.cryptocompare.com/data';

  /**
   * Fetch historical minute data from CryptoCompare
   * histominute endpoint gives minute-level OHLCV
   */
  async fetchHistoMinute(symbol: string, limit: number = 500): Promise<OHLCVCandle[]> {
    // Extract base symbol (BTC from BTCUSDT)
    const fsym = symbol.replace(/USDT|USDC|BUSD/g, '');
    const tsym = 'USD';

    // CryptoCompare histominute endpoint
    const url = `${this.baseUrl}/v2/histominute?fsym=${fsym}&tsym=${tsym}&limit=${limit}`;

    const response = await fetch(url, {
      headers: {
        'Accept': 'application/json'
      }
    });

    if (!response.ok) {
      throw new Error(`CryptoCompare API error: ${response.status} ${response.statusText}`);
    }

    const result = await response.json() as any;

    if (result.Response !== 'Success') {
      throw new Error(`CryptoCompare error: ${result.Message || 'Unknown error'}`);
    }

    // CryptoCompare format: {time, open, high, low, close, volumefrom, volumeto}
    return result.Data.Data.map((candle: any) => ({
      timestamp: candle.time * 1000, // Convert to ms
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
      volume: candle.volumefrom
    }));
  }
}

/**
 * DexScreener API Client
 * FREE - Covers ALL chains and DEXes (50+ chains)
 * Supports: Ethereum, BSC, Solana, Arbitrum, Optimism, Polygon, Avalanche, Base, etc.
 *
 * Rate Limits (Free API):
 * - DEX/Pairs endpoints: 300 requests per minute
 * - Token Profile/Boost endpoints: 60 requests per minute
 * - Returns 429 error when limit exceeded
 *
 * Paid plans available for higher limits
 * Documentation: https://docs.dexscreener.com/api/reference
 */
class DexScreenerClient {
  private baseUrl = 'https://api.dexscreener.com/latest/dex';

  /**
   * Search for token across all chains
   */
  async searchToken(symbol: string): Promise<any> {
    const url = `${this.baseUrl}/search?q=${symbol}`;
    const response = await fetch(url, {
      headers: { 'Accept': 'application/json' }
    });
    if (!response.ok) {
      throw new Error(`DexScreener API error: ${response.status} ${response.statusText}`);
    }
    return await response.json();
  }

  /**
   * Get price data for specific token pairs
   */
  async getTokenPairs(chainId: string, tokenAddress: string): Promise<any> {
    const url = `${this.baseUrl}/tokens/${chainId}/${tokenAddress}`;
    const response = await fetch(url, {
      headers: { 'Accept': 'application/json' }
    });
    if (!response.ok) {
      throw new Error(`DexScreener API error: ${response.status} ${response.statusText}`);
    }
    return await response.json();
  }

  /**
   * Fetch OHLCV candles from DexScreener search results
   * Returns best match for symbol with price data
   */
  async fetchForSymbol(symbol: string): Promise<OHLCVCandle[]> {
    const baseSymbol = symbol.replace(/USDT|USDC|BUSD/g, '');
    const searchResult = await this.searchToken(baseSymbol);

    if (!searchResult.pairs || searchResult.pairs.length === 0) {
      throw new Error(`No pairs found for ${symbol}`);
    }

    // Get the first pair with highest liquidity
    const pair = searchResult.pairs.sort((a: any, b: any) =>
      (b.liquidity?.usd || 0) - (a.liquidity?.usd || 0)
    )[0];

    // DexScreener doesn't provide historical candles, just current price
    // Return a single data point representing current state
    return [{
      timestamp: Date.now(),
      open: parseFloat(pair.priceUsd || '0'),
      high: parseFloat(pair.priceUsd || '0'),
      low: parseFloat(pair.priceUsd || '0'),
      close: parseFloat(pair.priceUsd || '0'),
      volume: parseFloat(pair.volume?.h24 || '0')
    }];
  }
}

/**
 * GeckoTerminal API Client
 * FREE - CoinGecko's DEX aggregator for 100+ networks
 * Supports: All major DEXes on Ethereum, BSC, Solana, Arbitrum, Optimism, Polygon, Avalanche, etc.
 *
 * Rate Limits (Free API):
 * - 30 calls per minute (increased from 10/min in 2024)
 * - No API key required
 * - Returns OHLCV data for DEX pools
 *
 * Paid plans: 500 calls/min (16x increase)
 * Documentation: https://apiguide.geckoterminal.com/
 */
class GeckoTerminalClient {
  private baseUrl = 'https://api.geckoterminal.com/api/v2';

  /**
   * Get OHLCV data for a specific pool
   */
  async getPoolOHLCV(network: string, poolAddress: string, timeframe: string = '5m'): Promise<OHLCVCandle[]> {
    // Timeframe options: '1m', '5m', '15m', '1h', '4h', '12h', '1d'
    const url = `${this.baseUrl}/networks/${network}/pools/${poolAddress}/ohlcv/${timeframe}`;
    const response = await fetch(url, {
      headers: { 'Accept': 'application/json' }
    });
    if (!response.ok) {
      throw new Error(`GeckoTerminal API error: ${response.status} ${response.statusText}`);
    }
    const result = await response.json() as any;

    // GeckoTerminal format: {data: {attributes: {ohlcv_list: [[timestamp, open, high, low, close, volume]]}}}
    const ohlcvList = result.data?.attributes?.ohlcv_list || [];
    return ohlcvList.map((candle: any[]) => ({
      timestamp: candle[0] * 1000, // Convert to ms
      open: candle[1],
      high: candle[2],
      low: candle[3],
      close: candle[4],
      volume: candle[5]
    }));
  }

  /**
   * Search for token pools across all networks
   */
  async searchTokens(query: string): Promise<any> {
    const url = `${this.baseUrl}/search/pools?query=${query}`;
    const response = await fetch(url, {
      headers: { 'Accept': 'application/json' }
    });
    if (!response.ok) {
      throw new Error(`GeckoTerminal API error: ${response.status} ${response.statusText}`);
    }
    return await response.json();
  }

  /**
   * Fetch OHLCV for a symbol by searching and getting best pool
   */
  async fetchForSymbol(symbol: string, timeframe: string = '5m'): Promise<OHLCVCandle[]> {
    const baseSymbol = symbol.replace(/USDT|USDC|BUSD/g, '');
    const searchResult = await this.searchTokens(baseSymbol);

    if (!searchResult.data || searchResult.data.length === 0) {
      throw new Error(`No pools found for ${symbol}`);
    }

    // Get the first pool (highest relevance)
    const pool = searchResult.data[0];
    const network = pool.relationships?.base_token?.data?.id?.split('_')[0];
    const poolAddress = pool.attributes?.address;

    if (!network || !poolAddress) {
      throw new Error(`Invalid pool data for ${symbol}`);
    }

    return await this.getPoolOHLCV(network, poolAddress, timeframe);
  }

  /**
   * Get network mapping for common symbols
   */
  private getNetwork(symbol: string): string {
    const baseSymbol = symbol.replace(/USDT|USDC|BUSD/g, '');

    // Common network mappings
    const mapping: { [key: string]: string } = {
      'BTC': 'eth', // Wrapped BTC on Ethereum
      'ETH': 'eth',
      'SOL': 'solana',
      'BNB': 'bsc',
      'AVAX': 'avax',
      'MATIC': 'polygon',
      'ARB': 'arbitrum',
      'OP': 'optimism'
    };

    return mapping[baseSymbol] || 'eth'; // Default to Ethereum
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
      const coinGeckoClient = new CoinGeckoClient();
      const cryptoCompareClient = new CryptoCompareClient();
      const dexScreenerClient = new DexScreenerClient();
      const geckoTerminalClient = new GeckoTerminalClient();
      const dataManager = env.HISTORICAL_PRICES ? new HistoricalDataManager(env.HISTORICAL_PRICES) : null;

      // Route: Fetch fresh data with multi-source fallback
      if (path === '/fetch-fresh' && request.method === 'GET') {
        const symbol = url.searchParams.get('symbol') || 'BTCUSDT';
        const interval = url.searchParams.get('interval') || '5m';
        const limit = parseInt(url.searchParams.get('limit') || '500');

        let candles: OHLCVCandle[] = [];
        let source = '';
        const errors: string[] = [];

        // Try CryptoCompare first (minute-level data, has volume)
        try {
          candles = await cryptoCompareClient.fetchHistoMinute(symbol, limit);
          source = 'cryptocompare';
        } catch (e) {
          errors.push(`CryptoCompare: ${e instanceof Error ? e.message : String(e)}`);

          // Fallback to CoinGecko
          try {
            const days = Math.ceil(limit * 5 / (60 * 24));
            candles = await coinGeckoClient.fetchForSymbol(symbol, Math.max(days, 30));
            source = 'coingecko';
          } catch (e2) {
            errors.push(`CoinGecko: ${e2 instanceof Error ? e2.message : String(e2)}`);

            // Fallback to GeckoTerminal (DEX aggregator with OHLCV)
            try {
              candles = await geckoTerminalClient.fetchForSymbol(symbol, interval);
              source = 'geckoterminal';
            } catch (e3) {
              errors.push(`GeckoTerminal: ${e3 instanceof Error ? e3.message : String(e3)}`);

              // Fallback to Binance
              try {
                const endTime = Date.now();
                const startTime = endTime - (limit * 5 * 60 * 1000);
                candles = await binanceClient.fetchLargeDataset(symbol, interval, startTime, endTime);
                source = 'binance';
              } catch (e4) {
                errors.push(`Binance: ${e4 instanceof Error ? e4.message : String(e4)}`);

                // Final fallback to DexScreener (current price only)
                try {
                  candles = await dexScreenerClient.fetchForSymbol(symbol);
                  source = 'dexscreener';
                } catch (e5) {
                  errors.push(`DexScreener: ${e5 instanceof Error ? e5.message : String(e5)}`);
                  throw new Error(`All sources failed: ${errors.join('; ')}`);
                }
              }
            }
          }
        }

        return new Response(JSON.stringify({
          success: true,
          symbol,
          interval,
          candles,
          candleCount: candles.length,
          source,
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
