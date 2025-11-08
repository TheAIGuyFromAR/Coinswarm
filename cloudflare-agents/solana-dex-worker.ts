/**
 * Solana DEX Data Worker
 *
 * Fetches real-time and historical data from Solana DEXes:
 * - Jupiter (aggregator - best prices)
 * - Raydium (AMM)
 * - Orca (concentrated liquidity)
 * - Meteora (dynamic AMM)
 * - Phoenix (order book)
 *
 * Data sources:
 * - Jupiter API (aggregated prices)
 * - Birdeye API (DEX trades, OHLCV)
 * - DeFi Llama API (TVL, volumes)
 * - Solana RPC (on-chain queries)
 *
 * Endpoints:
 * - GET /price/{mint} - Current price from Jupiter
 * - GET /price-all - All tracked tokens
 * - GET /trades/{pair} - Recent trades from Birdeye
 * - GET /ohlcv/{pair} - Historical candles (1m, 5m, 15m, 1h, 1d)
 * - GET /pools - Active liquidity pools
 * - GET /arb-opportunities - CEX-DEX arbitrage opportunities
 */

import { createLogger, LogLevel } from './structured-logger';

const logger = createLogger('SolanaDEXWorker', LogLevel.INFO);

// API Response Interfaces
interface JupiterAPIResponse {
  data: Record<string, {price: number}>;
}

interface BirdeyeOHLCVResponse {
  data?: {
    items: Array<{
      address: string;
      type: string;
      unixTime: number;
      open: number;
      high: number;
      low: number;
      close: number;
      volume: number;
    }>;
  };
}

interface BirdeyeTradesResponse {
  data?: {
    items: Array<{
      blockUnixTime: number;
      price: number;
      amount: number;
      side: string;
      source?: string;
      txHash: string;
    }>;
  };
}

interface BinancePriceResponse {
  price: string;
}

interface TokenInfo {
  name?: string;
  symbol?: string;
  decimals?: number;
  liquidity?: number;
}

interface Env {
  SOLANA_DEX_KV: KVNamespace;
}

interface JupiterPrice {
  id: string;  // Mint address
  mintSymbol: string;
  vsToken: string;  // USDC mint
  vsTokenSymbol: string;
  price: number;
  timestamp: number;
}

interface BirdeyeOHLCV {
  address: string;
  type: string;
  unixTime: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface Trade {
  timestamp: number;
  price: number;
  amount: number;
  side: 'buy' | 'sell';
  source: string;  // 'raydium', 'orca', etc.
  signature: string;
}

interface ArbitrageOpportunity {
  token: string;
  cexPrice: number;  // Binance
  dexPrice: number;  // Jupiter best price
  spread: number;    // Percentage
  profitPct: number; // After fees
  source: string;    // Which DEX
  liquidity: number;
}

/**
 * Solana Token Mints
 */
const TOKENS = {
  // Stablecoins
  USDC: 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
  USDT: 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB',

  // Major tokens
  SOL: 'So11111111111111111111111111111111111111112',  // Wrapped SOL
  BTC: '9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E',  // Wrapped BTC (Portal)
  ETH: '7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs',  // Wrapped ETH (Wormhole)

  // Solana ecosystem
  JUP: 'JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN',
  RAY: '4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R',
  ORCA: 'orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE',
  BONK: 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',
};

/**
 * Jupiter Price API Client
 */
class JupiterClient {
  private baseUrl = 'https://price.jup.ag/v4';

  /**
   * Get current price for a token
   */
  async getPrice(mint: string, vsMint: string = TOKENS.USDC): Promise<number | null> {
    try {
      const url = `${this.baseUrl}/price?ids=${mint}&vsToken=${vsMint}`;
      const response = await fetch(url);
      const data = await response.json() as JupiterAPIResponse;

      if (data.data && data.data[mint]) {
        return data.data[mint].price;
      }

      return null;
    } catch (error) {
      logger.error('Jupiter API error', error instanceof Error ? error : new Error(String(error)));
      return null;
    }
  }

  /**
   * Get prices for multiple tokens
   */
  async getPrices(mints: string[], vsMint: string = TOKENS.USDC): Promise<Record<string, number>> {
    try {
      const ids = mints.join(',');
      const url = `${this.baseUrl}/price?ids=${ids}&vsToken=${vsMint}`;
      const response = await fetch(url);
      const data = await response.json() as JupiterAPIResponse;

      const prices: Record<string, number> = {};
      for (const [mint, priceData] of Object.entries(data.data || {})) {
        prices[mint] = priceData.price;
      }

      return prices;
    } catch (error) {
      logger.error('Jupiter API error', error instanceof Error ? error : new Error(String(error)));
      return {};
    }
  }
}

/**
 * Birdeye API Client (for OHLCV and trades)
 */
class BirdeyeClient {
  private baseUrl = 'https://public-api.birdeye.so';
  private apiKey: string | null = null;

  constructor(apiKey?: string) {
    this.apiKey = apiKey || null;
  }

  /**
   * Get OHLCV data for a token pair
   */
  async getOHLCV(
    address: string,
    type: '1m' | '5m' | '15m' | '1H' | '1D' = '5m',
    timeFrom?: number,
    timeTo?: number
  ): Promise<BirdeyeOHLCV[]> {
    try {
      const headers: HeadersInit = {
        'Accept': 'application/json'
      };
      if (this.apiKey) {
        headers['X-API-KEY'] = this.apiKey;
      }

      let url = `${this.baseUrl}/defi/ohlcv?address=${address}&type=${type}`;
      if (timeFrom) url += `&time_from=${timeFrom}`;
      if (timeTo) url += `&time_to=${timeTo}`;

      const response = await fetch(url, { headers });
      const data = await response.json() as BirdeyeOHLCVResponse;

      return data.data?.items || [];
    } catch (error) {
      logger.error('Birdeye API error', error instanceof Error ? error : new Error(String(error)));
      return [];
    }
  }

  /**
   * Get recent trades for a token
   */
  async getTrades(address: string, limit: number = 100): Promise<Trade[]> {
    try {
      const headers: HeadersInit = {
        'Accept': 'application/json'
      };
      if (this.apiKey) {
        headers['X-API-KEY'] = this.apiKey;
      }

      const url = `${this.baseUrl}/defi/txs/token?address=${address}&tx_type=swap&limit=${limit}`;
      const response = await fetch(url, { headers });
      const data = await response.json() as BirdeyeTradesResponse;

      const trades: Trade[] = [];
      for (const tx of data.data?.items || []) {
        trades.push({
          timestamp: tx.blockUnixTime * 1000,
          price: tx.price,
          amount: tx.amount,
          side: tx.side as 'buy' | 'sell',
          source: tx.source || 'unknown',
          signature: tx.txHash
        });
      }

      return trades;
    } catch (error) {
      logger.error('Birdeye API error', error instanceof Error ? error : new Error(String(error)));
      return [];
    }
  }

  /**
   * Get token info
   */
  async getTokenInfo(address: string): Promise<TokenInfo | null> {
    try {
      const headers: HeadersInit = {
        'Accept': 'application/json'
      };
      if (this.apiKey) {
        headers['X-API-KEY'] = this.apiKey;
      }

      const url = `${this.baseUrl}/defi/token_overview?address=${address}`;
      const response = await fetch(url, { headers });
      const data = await response.json() as {data?: TokenInfo};

      return data.data || null;
    } catch (error) {
      logger.error('Birdeye API error', error instanceof Error ? error : new Error(String(error)));
      return null;
    }
  }
}

/**
 * Arbitrage Detector (CEX-DEX)
 */
class SolanaArbitrageDetector {
  private jupiterClient: JupiterClient;
  private binanceApiUrl = 'https://api.binance.com';

  constructor() {
    this.jupiterClient = new JupiterClient();
  }

  /**
   * Find arbitrage opportunities between Binance and Solana DEXes
   */
  async findArbitrageOpportunities(): Promise<ArbitrageOpportunity[]> {
    const opportunities: ArbitrageOpportunity[] = [];

    // Check SOL/USDC
    const [binanceSolPrice, jupiterSolPrice] = await Promise.all([
      this.getBinancePrice('SOLUSDC'),
      this.jupiterClient.getPrice(TOKENS.SOL, TOKENS.USDC)
    ]);

    if (binanceSolPrice && jupiterSolPrice) {
      const spread = Math.abs(jupiterSolPrice - binanceSolPrice) / binanceSolPrice;
      const profitPct = spread - 0.003; // 0.3% total fees (0.1% Binance, 0.2% Solana)

      if (profitPct > 0.001) { // 0.1% minimum
        opportunities.push({
          token: 'SOL',
          cexPrice: binanceSolPrice,
          dexPrice: jupiterSolPrice,
          spread: spread * 100,
          profitPct: profitPct * 100,
          source: 'Jupiter',
          liquidity: 0 // TODO: Get actual liquidity
        });
      }
    }

    // Check BTC (Portal wrapped BTC)
    const [binanceBtcPrice, jupiterBtcPrice] = await Promise.all([
      this.getBinancePrice('BTCUSDC'),
      this.jupiterClient.getPrice(TOKENS.BTC, TOKENS.USDC)
    ]);

    if (binanceBtcPrice && jupiterBtcPrice) {
      const spread = Math.abs(jupiterBtcPrice - binanceBtcPrice) / binanceBtcPrice;
      const profitPct = spread - 0.003;

      if (profitPct > 0.001) {
        opportunities.push({
          token: 'BTC',
          cexPrice: binanceBtcPrice,
          dexPrice: jupiterBtcPrice,
          spread: spread * 100,
          profitPct: profitPct * 100,
          source: 'Jupiter',
          liquidity: 0
        });
      }
    }

    return opportunities;
  }

  private async getBinancePrice(symbol: string): Promise<number | null> {
    try {
      const url = `${this.binanceApiUrl}/api/v3/ticker/price?symbol=${symbol}`;
      const response = await fetch(url);
      const data = await response.json() as BinancePriceResponse;
      return parseFloat(data.price);
    } catch (error) {
      logger.error('Binance API error', error instanceof Error ? error : new Error(String(error)));
      return null;
    }
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
      const jupiterClient = new JupiterClient();
      const birdeyeClient = new BirdeyeClient();
      const arbDetector = new SolanaArbitrageDetector();

      // Route: Get price for specific token
      if (path.startsWith('/price/')) {
        const mint = path.split('/')[2];
        const price = await jupiterClient.getPrice(mint);

        return new Response(JSON.stringify({
          success: true,
          mint,
          price,
          timestamp: Date.now()
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      // Route: Get all prices
      if (path === '/price-all') {
        const mints = Object.values(TOKENS);
        const prices = await jupiterClient.getPrices(mints);

        // Add symbols
        const pricesWithSymbols: Record<string, {mint: string; price: number}> = {};
        for (const [symbol, mint] of Object.entries(TOKENS)) {
          if (prices[mint]) {
            pricesWithSymbols[symbol] = {
              mint,
              price: prices[mint]
            };
          }
        }

        return new Response(JSON.stringify({
          success: true,
          prices: pricesWithSymbols,
          timestamp: Date.now()
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      // Route: Get OHLCV data
      if (path.startsWith('/ohlcv/')) {
        const parts = path.split('/');
        const tokenSymbol = parts[2];
        const interval = (url.searchParams.get('interval') || '5m') as ('1m' | '5m' | '15m' | '1H' | '1D');

        const mint = (TOKENS as Record<string, string>)[tokenSymbol.toUpperCase()];
        if (!mint) {
          return new Response(JSON.stringify({
            success: false,
            error: 'Unknown token'
          }), { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
        }

        const timeFrom = url.searchParams.get('from') ? parseInt(url.searchParams.get('from')!) : undefined;
        const timeTo = url.searchParams.get('to') ? parseInt(url.searchParams.get('to')!) : undefined;

        const candles = await birdeyeClient.getOHLCV(mint, interval, timeFrom, timeTo);

        // Store in KV for caching
        const cacheKey = `ohlcv:${mint}:${interval}:${Date.now()}`;
        await env.SOLANA_DEX_KV.put(cacheKey, JSON.stringify(candles), {
          expirationTtl: 3600 // 1 hour
        });

        return new Response(JSON.stringify({
          success: true,
          token: tokenSymbol,
          interval,
          candles,
          count: candles.length
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      // Route: Get recent trades
      if (path.startsWith('/trades/')) {
        const tokenSymbol = path.split('/')[2];
        const limit = parseInt(url.searchParams.get('limit') || '100');

        const mint = (TOKENS as Record<string, string>)[tokenSymbol.toUpperCase()];
        if (!mint) {
          return new Response(JSON.stringify({
            success: false,
            error: 'Unknown token'
          }), { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
        }

        const trades = await birdeyeClient.getTrades(mint, limit);

        return new Response(JSON.stringify({
          success: true,
          token: tokenSymbol,
          trades,
          count: trades.length
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      // Route: Find arbitrage opportunities
      if (path === '/arb-opportunities') {
        const opportunities = await arbDetector.findArbitrageOpportunities();

        return new Response(JSON.stringify({
          success: true,
          opportunities,
          count: opportunities.length,
          timestamp: Date.now()
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      // Default: API info
      return new Response(JSON.stringify({
        status: 'ok',
        name: 'Solana DEX Data Worker',
        endpoints: {
          '/price/{mint}': 'Get current price from Jupiter',
          '/price-all': 'Get all token prices',
          '/ohlcv/{token}?interval=5m': 'Get OHLCV candles (1m, 5m, 15m, 1H, 1D)',
          '/trades/{token}?limit=100': 'Get recent trades',
          '/arb-opportunities': 'Find CEX-DEX arbitrage opportunities'
        },
        tokens: Object.keys(TOKENS),
        dexes: ['Jupiter', 'Raydium', 'Orca', 'Meteora', 'Phoenix'],
        features: [
          'Real-time prices from Jupiter',
          'Historical OHLCV from Birdeye',
          'Trade history',
          'CEX-DEX arbitrage detection',
          'Sub-second Solana data',
          'Near-zero gas costs'
        ]
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });

    } catch (error) {
      const err = error instanceof Error ? error : new Error(String(error));
      logger.error('Worker fetch failed', err);
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
