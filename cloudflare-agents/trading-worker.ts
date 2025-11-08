/**
 * Trading Worker for Cloudflare
 *
 * Real-time multi-pair trading agent that:
 * 1. Monitors multiple pairs (BTC, SOL, ETH across stablecoins)
 * 2. Detects patterns in real-time
 * 3. Executes arbitrage opportunities
 * 4. Manages portfolio across all pairs
 *
 * Endpoints:
 * - GET /scan - Scan for current opportunities
 * - GET /prices - Get current prices for all pairs
 * - POST /trade - Execute a trade
 * - GET /portfolio - Get current portfolio state
 */

import { MultiPatternDetector } from './pattern-detector';
import { createLogger, LogLevel } from './structured-logger';

const logger = createLogger('TradingWorker', LogLevel.INFO);

interface Env {
  TRADING_KV: KVNamespace;
  HISTORICAL_PRICES: KVNamespace;
}

interface BinancePriceResponse {
  symbol: string;
  price: string;
}

interface HistoricalDataResponse {
  success: boolean;
  dataset?: {
    pair: string;
    candles: Array<{
      timestamp: number;
      open: number;
      high: number;
      low: number;
      close: number;
      volume: number;
    }>;
  };
}

interface TradeRequest {
  action: 'BUY' | 'SELL';
  pair: string;
  size: number;
}

interface PortfolioPosition {
  pair: string;
  size: number;
  entryPrice: number;
  entryTime: string;
  currentValue: number;
  pnl: number;
  pnlPct: number;
}

interface PortfolioState {
  cash: number;
  positions: Record<string, PortfolioPosition>;
  totalEquity: number;
  totalPnL: number;
  totalPnLPct: number;
}

/**
 * Portfolio Manager
 * Tracks positions across all pairs
 */
class PortfolioManager {
  private kv: KVNamespace;

  constructor(kv: KVNamespace) {
    this.kv = kv;
  }

  async getState(): Promise<PortfolioState> {
    const stateJson = await this.kv.get('portfolio_state');
    if (!stateJson) {
      // Initialize with default state
      return {
        cash: 100000, // Start with $100k
        positions: {},
        totalEquity: 100000,
        totalPnL: 0,
        totalPnLPct: 0
      };
    }
    return JSON.parse(stateJson);
  }

  async saveState(state: PortfolioState): Promise<void> {
    await this.kv.put('portfolio_state', JSON.stringify(state));
  }

  async updatePositions(currentPrices: Record<string, number>): Promise<PortfolioState> {
    const state = await this.getState();

    let positionsValue = 0;
    let totalPnL = 0;

    // Update each position with current price
    for (const [pair, position] of Object.entries(state.positions)) {
      const currentPrice = currentPrices[pair];
      if (currentPrice) {
        position.currentValue = position.size * currentPrice;
        position.pnl = position.currentValue - (position.size * position.entryPrice);
        position.pnlPct = (position.pnl / (position.size * position.entryPrice)) * 100;

        positionsValue += position.currentValue;
        totalPnL += position.pnl;
      }
    }

    state.totalEquity = state.cash + positionsValue;
    state.totalPnL = totalPnL;
    state.totalPnLPct = (totalPnL / (state.totalEquity - totalPnL)) * 100;

    await this.saveState(state);
    return state;
  }

  async canOpenPosition(pair: string, size: number, price: number, maxPerPair: number = 0.3): Promise<boolean> {
    // Check if we can open a position given risk limits
    const state = await this.getState();

    // 1. Check if position already exists for this pair
    if (state.positions[pair]) {
      logger.warn('Risk check failed: Position already exists', { pair });
      return false;
    }

    // 2. Check if we have enough cash
    const positionValue = size * price;
    if (positionValue > state.cash) {
      logger.warn('Risk check failed: Insufficient cash', {
        pair,
        required: positionValue,
        available: state.cash,
      });
      return false;
    }

    // 3. Check maximum exposure per pair (default 30% of total equity)
    const maxPositionSize = state.totalEquity * maxPerPair;
    if (positionValue > maxPositionSize) {
      logger.warn('Risk check failed: Position size exceeds maximum', {
        pair,
        positionValue,
        maxPositionSize,
        maxPercentage: maxPerPair * 100,
      });
      return false;
    }

    // 4. Check total number of positions (max 5 positions to avoid over-diversification)
    const positionCount = Object.keys(state.positions).length;
    if (positionCount >= 5) {
      logger.warn('Risk check failed: Maximum positions reached', {
        pair,
        currentPositions: positionCount,
        maxPositions: 5,
      });
      return false;
    }

    // 5. Basic sanity checks
    if (size <= 0 || price <= 0) {
      logger.warn('Risk check failed: Invalid size or price', { pair, size, price });
      return false;
    }

    return true;
  }

  async openPosition(pair: string, size: number, price: number): Promise<void> {
    const state = await this.getState();

    state.positions[pair] = {
      pair,
      size,
      entryPrice: price,
      entryTime: new Date().toISOString(),
      currentValue: size * price,
      pnl: 0,
      pnlPct: 0
    };

    state.cash -= size * price;

    await this.saveState(state);
  }

  async closePosition(pair: string, price: number): Promise<number> {
    const state = await this.getState();
    const position = state.positions[pair];

    if (!position) {
      return 0;
    }

    const proceeds = position.size * price;
    const pnl = proceeds - (position.size * position.entryPrice);

    state.cash += proceeds;
    delete state.positions[pair];

    await this.saveState(state);
    return pnl;
  }
}

/**
 * Price Fetcher
 * Fetches current prices from Binance or cached historical data
 */
class PriceFetcher {
  private binanceApiUrl = 'https://api.binance.com';
  private historicalDataUrl: string | null = null;
  private useHistorical: boolean = false;

  constructor(historicalDataUrl?: string) {
    if (historicalDataUrl) {
      this.historicalDataUrl = historicalDataUrl;
      this.useHistorical = true;
    }
  }

  /**
   * Fetch current prices from Binance API
   */
  async fetchAllPrices(): Promise<Record<string, number>> {
    if (this.useHistorical && this.historicalDataUrl) {
      return await this.fetchFromHistorical();
    }

    return await this.fetchFromBinance();
  }

  /**
   * Fetch live prices from Binance
   */
  private async fetchFromBinance(): Promise<Record<string, number>> {
    const pairs = [
      'BTCUSDT', 'BTCUSDC', 'BTCBUSD',
      'SOLUSDT', 'SOLUSDC', 'SOLBUSD',
      'ETHUSDT', 'ETHUSDC', 'ETHBUSD'
    ];

    const prices: Record<string, number> = {};

    try {
      // Fetch all prices in parallel
      const pricePromises = pairs.map(async (symbol) => {
        const url = `${this.binanceApiUrl}/api/v3/ticker/price?symbol=${symbol}`;
        const response = await fetch(url);
        const data = (await response.json()) as BinancePriceResponse;
        return { symbol, price: parseFloat(data.price) };
      });

      const results = await Promise.all(pricePromises);

      for (const { symbol, price } of results) {
        const pair = this.symbolToPair(symbol);
        prices[pair] = price;
      }

      // Calculate cross pairs
      if (prices['BTC-USDT'] && prices['SOL-USDT']) {
        prices['BTC-SOL'] = prices['BTC-USDT'] / prices['SOL-USDT'];
      }
      if (prices['BTC-USDT'] && prices['ETH-USDT']) {
        prices['BTC-ETH'] = prices['BTC-USDT'] / prices['ETH-USDT'];
      }

    } catch (error) {
      logger.error('Error fetching Binance prices', error as Error);
      // Fallback to mock data if Binance fails
      return this.mockPrices();
    }

    return prices;
  }

  /**
   * Fetch latest prices from historical data worker
   */
  private async fetchFromHistorical(): Promise<Record<string, number>> {
    try {
      const response = await fetch(`${this.historicalDataUrl}/random?interval=5m&minDays=1`);
      const data = (await response.json()) as HistoricalDataResponse;

      if (data.success && data.dataset && data.dataset.candles.length > 0) {
        // Get latest candle
        const latestCandle = data.dataset.candles[data.dataset.candles.length - 1];
        return {
          [data.dataset.pair]: latestCandle.close
        };
      }
    } catch (error) {
      logger.error('Error fetching historical data', error as Error);
    }

    // Fallback
    return this.mockPrices();
  }

  /**
   * Mock prices for development/fallback
   */
  private mockPrices(): Record<string, number> {
    const basePrice = {
      BTC: 50000 + Math.random() * 1000,
      SOL: 100 + Math.random() * 5,
      ETH: 3000 + Math.random() * 100
    };

    return {
      'BTC-USDT': basePrice.BTC,
      'BTC-USDC': basePrice.BTC + (Math.random() - 0.5) * 20,
      'BTC-BUSD': basePrice.BTC + (Math.random() - 0.5) * 15,
      'SOL-USDT': basePrice.SOL,
      'SOL-USDC': basePrice.SOL + (Math.random() - 0.5) * 0.5,
      'SOL-BUSD': basePrice.SOL + (Math.random() - 0.5) * 0.3,
      'ETH-USDT': basePrice.ETH,
      'ETH-USDC': basePrice.ETH + (Math.random() - 0.5) * 5,
      'BTC-SOL': basePrice.BTC / basePrice.SOL,
      'BTC-ETH': basePrice.BTC / basePrice.ETH,
    };
  }

  private symbolToPair(symbol: string): string {
    // Convert BTCUSDT -> BTC-USDT
    const match = symbol.match(/^([A-Z]+)(USDT|USDC|BUSD)$/);
    if (match) {
      return `${match[1]}-${match[2]}`;
    }
    return symbol;
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
      // Initialize components
      const patternDetector = new MultiPatternDetector();
      const portfolioManager = new PortfolioManager(env.TRADING_KV);
      const priceFetcher = new PriceFetcher();

      // Route: Get current prices
      if (path === '/prices') {
        const prices = await priceFetcher.fetchAllPrices();
        return new Response(JSON.stringify({
          success: true,
          timestamp: new Date().toISOString(),
          prices
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      // Route: Scan for opportunities
      if (path === '/scan') {
        const prices = await priceFetcher.fetchAllPrices();
        const patterns = patternDetector.detectAll(prices);

        return new Response(JSON.stringify({
          success: true,
          timestamp: new Date().toISOString(),
          patterns,
          currentPrices: prices
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      // Route: Get portfolio state
      if (path === '/portfolio') {
        const prices = await priceFetcher.fetchAllPrices();
        const portfolio = await portfolioManager.updatePositions(prices);

        return new Response(JSON.stringify({
          success: true,
          timestamp: new Date().toISOString(),
          portfolio
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      // Route: Execute trade (POST)
      if (path === '/trade' && request.method === 'POST') {
        const body = (await request.json()) as TradeRequest;
        const { action, pair, size } = body;

        const prices = await priceFetcher.fetchAllPrices();
        const price = prices[pair];

        if (!price) {
          return new Response(JSON.stringify({
            success: false,
            error: 'Invalid pair'
          }), { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
        }

        if (action === 'BUY') {
          await portfolioManager.openPosition(pair, size, price);
        } else if (action === 'SELL') {
          await portfolioManager.closePosition(pair, price);
        }

        const portfolio = await portfolioManager.updatePositions(prices);

        return new Response(JSON.stringify({
          success: true,
          action,
          pair,
          price,
          portfolio
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      // Default: API info
      return new Response(JSON.stringify({
        status: 'ok',
        name: 'Coinswarm Trading Worker',
        endpoints: {
          '/prices': 'GET - Current prices for all pairs',
          '/scan': 'GET - Scan for arbitrage and pattern opportunities',
          '/portfolio': 'GET - Current portfolio state',
          '/trade': 'POST - Execute a trade {action: BUY/SELL, pair, size}'
        },
        features: [
          'Multi-pair monitoring (BTC, SOL, ETH across stablecoins)',
          'Real-time pattern detection',
          'Stablecoin arbitrage detection',
          'Triangular arbitrage detection',
          'Spread trading detection',
          'Portfolio management'
        ]
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });

    } catch (error) {
      const err = error as Error;
      logger.error('Worker error', err);
      return new Response(
        JSON.stringify({
          success: false,
          error: err.message,
        }),
        {
          status: 500,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        }
      );
    }
  }
};
