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

interface Env {
  TRADING_KV: KVNamespace;
  HISTORICAL_PRICES: KVNamespace;
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

  canOpenPosition(pair: string, size: number, price: number, maxPerPair: number = 0.3): boolean {
    // Check if we can open a position given risk limits
    // For now, simplified check
    return true; // TODO: Implement proper risk checks
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
 * Fetches current prices from exchanges
 */
class PriceFetcher {
  async fetchAllPrices(): Promise<Record<string, number>> {
    // In production, fetch from real exchanges
    // For now, mock prices with realistic values

    const basePrice = {
      BTC: 50000 + Math.random() * 1000,
      SOL: 100 + Math.random() * 5,
      ETH: 3000 + Math.random() * 100
    };

    // Add small random differences across stablecoins
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
        const body = await request.json() as any;
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

    } catch (error: any) {
      return new Response(JSON.stringify({
        success: false,
        error: error.message
      }), {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }
  }
};
