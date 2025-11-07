/**
 * Backtest Worker for Cloudflare
 *
 * Runs pattern detection and trading simulations on real historical data
 * Features:
 * - Random time segment selection (prevents overfitting)
 * - Multi-pair testing (BTC, SOL, ETH × stablecoins)
 * - 5-minute candles (maximum granularity)
 * - Cross-pair pattern detection
 * - Portfolio-level risk management
 *
 * Endpoints:
 * - POST /backtest - Run backtest on random historical segment
 * - POST /backtest-multi - Run backtest across multiple random segments
 * - GET /results/{id} - Get backtest results
 */

import { MultiPatternDetector } from './pattern-detector';

interface Env {
  TRADING_KV: KVNamespace;
  HISTORICAL_PRICES: KVNamespace;
}

interface BacktestConfig {
  pairs: string[];
  interval: string;
  minDays: number;
  initialCapital: number;
  maxPositions: number;
  maxPerPairPct: number;
  minProfitThreshold: number;
  randomSegments?: number; // Number of random segments to test
}

interface BacktestResult {
  id: string;
  config: BacktestConfig;
  segment: {
    pairs: Record<string, { startTime: number; endTime: number; candleCount: number }>;
    durationDays: number;
  };
  performance: {
    totalTrades: number;
    winningTrades: number;
    losingTrades: number;
    winRate: number;
    totalPnL: number;
    totalPnLPct: number;
    sharpeRatio: number;
    maxDrawdown: number;
    avgTradeReturn: number;
  };
  patterns: {
    arbitrage: number;
    spreads: number;
    totalOpportunities: number;
    bestArbProfit: number;
    highestZScore: number;
  };
  trades: Trade[];
  equityCurve: { timestamp: number; equity: number }[];
  completedAt: string;
}

interface Trade {
  timestamp: number;
  pair: string;
  action: 'BUY' | 'SELL';
  price: number;
  size: number;
  pnl: number;
  reason: string;
}

/**
 * Backtest Engine
 * Simulates trading on historical data
 */
class BacktestEngine {
  private patternDetector: MultiPatternDetector;
  private historicalDataUrl: string;

  constructor(historicalDataUrl: string) {
    this.patternDetector = new MultiPatternDetector();
    this.historicalDataUrl = historicalDataUrl;
  }

  /**
   * Run backtest on random historical segment
   */
  async runBacktest(config: BacktestConfig): Promise<BacktestResult> {
    // Fetch random historical data for all pairs
    const datasets = await this.fetchMultiPairData(config.pairs, config.interval, config.minDays);

    // Initialize portfolio
    const portfolio = new BacktestPortfolio(config.initialCapital, config.maxPositions, config.maxPerPairPct);

    const trades: Trade[] = [];
    const equityCurve: { timestamp: number; equity: number }[] = [];
    const patterns = {
      arbitrage: 0,
      spreads: 0,
      totalOpportunities: 0,
      bestArbProfit: 0,
      highestZScore: 0
    };

    // Find common time range across all pairs
    const { startTime, endTime } = this.findCommonTimeRange(datasets);

    // Simulate trading minute-by-minute
    const candleCount = Math.min(...Object.values(datasets).map(d => d.candles.length));

    for (let i = 0; i < candleCount; i++) {
      // Get current prices across all pairs
      const currentPrices: Record<string, number> = {};
      const currentTimestamp = datasets[config.pairs[0]].candles[i].timestamp;

      for (const pair of config.pairs) {
        if (datasets[pair] && datasets[pair].candles[i]) {
          currentPrices[pair] = datasets[pair].candles[i].close;
        }
      }

      // Detect patterns
      const detectedPatterns = this.patternDetector.detectAll(currentPrices);

      // Update pattern stats
      patterns.arbitrage += detectedPatterns.arbitrage.length;
      patterns.spreads += detectedPatterns.spreads.length;
      patterns.totalOpportunities += detectedPatterns.summary.totalOpportunities;
      patterns.bestArbProfit = Math.max(patterns.bestArbProfit, detectedPatterns.summary.bestArbProfit);
      patterns.highestZScore = Math.max(patterns.highestZScore, detectedPatterns.summary.highestZScore);

      // Execute trades based on patterns
      const executedTrades = this.executeTradingLogic(
        detectedPatterns,
        currentPrices,
        currentTimestamp,
        portfolio,
        config.minProfitThreshold
      );

      trades.push(...executedTrades);

      // Update portfolio
      portfolio.updatePositions(currentPrices);

      // Record equity
      if (i % 288 === 0) { // Every day (288 5-minute candles = 1 day)
        equityCurve.push({
          timestamp: currentTimestamp,
          equity: portfolio.getTotalEquity()
        });
      }
    }

    // Close all positions at end
    const finalPrices: Record<string, number> = {};
    for (const pair of config.pairs) {
      if (datasets[pair]) {
        const lastCandle = datasets[pair].candles[datasets[pair].candles.length - 1];
        finalPrices[pair] = lastCandle.close;
      }
    }

    const closingTrades = portfolio.closeAllPositions(finalPrices);
    trades.push(...closingTrades);

    // Calculate performance metrics
    const performance = this.calculatePerformance(trades, equityCurve, config.initialCapital);

    // Build result
    const result: BacktestResult = {
      id: this.generateId(),
      config,
      segment: {
        pairs: Object.fromEntries(
          config.pairs.map(pair => [
            pair,
            {
              startTime: datasets[pair]?.startTime || 0,
              endTime: datasets[pair]?.endTime || 0,
              candleCount: datasets[pair]?.candles.length || 0
            }
          ])
        ),
        durationDays: (endTime - startTime) / (1000 * 60 * 60 * 24)
      },
      performance,
      patterns,
      trades,
      equityCurve,
      completedAt: new Date().toISOString()
    };

    return result;
  }

  /**
   * Run backtest across multiple random segments
   */
  async runMultiSegmentBacktest(config: BacktestConfig): Promise<BacktestResult[]> {
    const results: BacktestResult[] = [];
    const segmentCount = config.randomSegments || 5;

    for (let i = 0; i < segmentCount; i++) {
      const result = await this.runBacktest(config);
      results.push(result);

      // Small delay to ensure different random segments
      await new Promise(resolve => setTimeout(resolve, 1000));
    }

    return results;
  }

  /**
   * Fetch multi-pair historical data
   */
  private async fetchMultiPairData(
    pairs: string[],
    interval: string,
    minDays: number
  ): Promise<Record<string, any>> {
    const datasets: Record<string, any> = {};

    for (const pair of pairs) {
      try {
        const response = await fetch(
          `${this.historicalDataUrl}/random?pair=${pair}&interval=${interval}&minDays=${minDays}`
        );
        const data = await response.json() as any;

        if (data.success && data.dataset) {
          datasets[pair] = data.dataset;
        }
      } catch (error) {
        console.error(`Error fetching data for ${pair}:`, error);
      }
    }

    return datasets;
  }

  private findCommonTimeRange(datasets: Record<string, any>): { startTime: number; endTime: number } {
    const starts = Object.values(datasets).map((d: any) => d.startTime);
    const ends = Object.values(datasets).map((d: any) => d.endTime);

    return {
      startTime: Math.max(...starts),
      endTime: Math.min(...ends)
    };
  }

  /**
   * Execute trading logic based on detected patterns
   */
  private executeTradingLogic(
    patterns: any,
    prices: Record<string, number>,
    timestamp: number,
    portfolio: BacktestPortfolio,
    minProfit: number
  ): Trade[] {
    const trades: Trade[] = [];

    // Execute arbitrage opportunities
    for (const arb of patterns.arbitrage) {
      if (arb.profitPct / 100 >= minProfit) {
        // Execute arbitrage: buy on cheaper pair, sell on expensive pair
        const [buyPair, sellPair] = arb.pairs;

        if (portfolio.canOpenPosition(buyPair, prices[buyPair])) {
          const size = portfolio.calculatePositionSize(buyPair, prices[buyPair]);

          portfolio.openPosition(buyPair, size, prices[buyPair]);
          trades.push({
            timestamp,
            pair: buyPair,
            action: 'BUY',
            price: prices[buyPair],
            size,
            pnl: 0,
            reason: `Arbitrage: ${arb.description}`
          });

          // Immediately sell on other pair
          const sellSize = size;
          const pnl = portfolio.closePosition(sellPair, prices[sellPair], sellSize);
          trades.push({
            timestamp,
            pair: sellPair,
            action: 'SELL',
            price: prices[sellPair],
            size: sellSize,
            pnl,
            reason: `Arbitrage exit: ${arb.description}`
          });
        }
      }
    }

    // Execute spread trading opportunities
    for (const spread of patterns.spreads) {
      if (Math.abs(spread.zScore) >= 2.0) {
        // Mean reversion trade
        const { pair1, pair2, zScore } = spread;

        if (zScore > 0) {
          // Spread too wide: buy pair2, sell pair1
          if (portfolio.canOpenPosition(pair2, prices[pair2])) {
            const size = portfolio.calculatePositionSize(pair2, prices[pair2]);
            portfolio.openPosition(pair2, size, prices[pair2]);
            trades.push({
              timestamp,
              pair: pair2,
              action: 'BUY',
              price: prices[pair2],
              size,
              pnl: 0,
              reason: `Spread trading: ${spread.signal}`
            });
          }
        } else {
          // Spread too narrow: buy pair1, sell pair2
          if (portfolio.canOpenPosition(pair1, prices[pair1])) {
            const size = portfolio.calculatePositionSize(pair1, prices[pair1]);
            portfolio.openPosition(pair1, size, prices[pair1]);
            trades.push({
              timestamp,
              pair: pair1,
              action: 'BUY',
              price: prices[pair1],
              size,
              pnl: 0,
              reason: `Spread trading: ${spread.signal}`
            });
          }
        }
      }
    }

    return trades;
  }

  private calculatePerformance(
    trades: Trade[],
    equityCurve: { timestamp: number; equity: number }[],
    initialCapital: number
  ): any {
    const winningTrades = trades.filter(t => t.pnl > 0);
    const losingTrades = trades.filter(t => t.pnl < 0);
    const totalPnL = trades.reduce((sum, t) => sum + t.pnl, 0);

    // Calculate Sharpe ratio
    const returns = equityCurve.map((point, i) => {
      if (i === 0) return 0;
      return (point.equity - equityCurve[i - 1].equity) / equityCurve[i - 1].equity;
    });

    const avgReturn = returns.reduce((a, b) => a + b, 0) / returns.length;
    const variance = returns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / returns.length;
    const sharpeRatio = avgReturn / Math.sqrt(variance) * Math.sqrt(252); // Annualized

    // Calculate max drawdown
    let maxEquity = initialCapital;
    let maxDrawdown = 0;

    for (const point of equityCurve) {
      if (point.equity > maxEquity) {
        maxEquity = point.equity;
      }
      const drawdown = (maxEquity - point.equity) / maxEquity;
      if (drawdown > maxDrawdown) {
        maxDrawdown = drawdown;
      }
    }

    return {
      totalTrades: trades.length,
      winningTrades: winningTrades.length,
      losingTrades: losingTrades.length,
      winRate: trades.length > 0 ? winningTrades.length / trades.length : 0,
      totalPnL,
      totalPnLPct: (totalPnL / initialCapital) * 100,
      sharpeRatio: isNaN(sharpeRatio) ? 0 : sharpeRatio,
      maxDrawdown: maxDrawdown * 100,
      avgTradeReturn: trades.length > 0 ? totalPnL / trades.length : 0
    };
  }

  private generateId(): string {
    return `bt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

/**
 * Backtest Portfolio
 * Manages positions and capital during backtest
 */
class BacktestPortfolio {
  private cash: number;
  private initialCapital: number;
  private positions: Map<string, { size: number; entryPrice: number }>;
  private maxPositions: number;
  private maxPerPairPct: number;

  constructor(initialCapital: number, maxPositions: number, maxPerPairPct: number) {
    this.cash = initialCapital;
    this.initialCapital = initialCapital;
    this.positions = new Map();
    this.maxPositions = maxPositions;
    this.maxPerPairPct = maxPerPairPct;
  }

  canOpenPosition(pair: string, price: number): boolean {
    return this.positions.size < this.maxPositions && this.cash > 0;
  }

  calculatePositionSize(pair: string, price: number): number {
    const maxInvestment = this.initialCapital * this.maxPerPairPct;
    const availableCash = Math.min(this.cash, maxInvestment);
    return availableCash / price;
  }

  openPosition(pair: string, size: number, price: number): void {
    const cost = size * price;
    this.cash -= cost;
    this.positions.set(pair, { size, entryPrice: price });
  }

  closePosition(pair: string, price: number, size?: number): number {
    const position = this.positions.get(pair);
    if (!position) return 0;

    const closeSize = size || position.size;
    const proceeds = closeSize * price;
    const cost = closeSize * position.entryPrice;
    const pnl = proceeds - cost;

    this.cash += proceeds;

    if (closeSize >= position.size) {
      this.positions.delete(pair);
    } else {
      position.size -= closeSize;
    }

    return pnl;
  }

  closeAllPositions(prices: Record<string, number>): Trade[] {
    const trades: Trade[] = [];
    const timestamp = Date.now();

    for (const [pair, position] of this.positions.entries()) {
      const price = prices[pair];
      if (price) {
        const pnl = this.closePosition(pair, price);
        trades.push({
          timestamp,
          pair,
          action: 'SELL',
          price,
          size: position.size,
          pnl,
          reason: 'Close all positions at end of backtest'
        });
      }
    }

    return trades;
  }

  updatePositions(prices: Record<string, number>): void {
    // Update mark-to-market values (for tracking only)
  }

  getTotalEquity(): number {
    let equity = this.cash;
    // Add unrealized PnL from open positions
    // (implementation would require current prices)
    return equity;
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
      const historicalDataUrl = 'https://coinswarm-historical-data.your-subdomain.workers.dev';
      const backtestEngine = new BacktestEngine(historicalDataUrl);

      // Route: Run single backtest
      if (path === '/backtest' && request.method === 'POST') {
        const config = await request.json() as BacktestConfig;

        // Validate config
        if (!config.pairs || config.pairs.length === 0) {
          return new Response(JSON.stringify({
            success: false,
            error: 'Missing required field: pairs'
          }), { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
        }

        // Set defaults
        config.interval = config.interval || '5m';
        config.minDays = config.minDays || 30;
        config.initialCapital = config.initialCapital || 100000;
        config.maxPositions = config.maxPositions || 10;
        config.maxPerPairPct = config.maxPerPairPct || 0.30;
        config.minProfitThreshold = config.minProfitThreshold || 0.001;

        const result = await backtestEngine.runBacktest(config);

        // Store result in KV
        await env.TRADING_KV.put(`backtest:${result.id}`, JSON.stringify(result), {
          expirationTtl: 60 * 60 * 24 * 7 // 7 days
        });

        return new Response(JSON.stringify({
          success: true,
          result
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      // Route: Run multi-segment backtest
      if (path === '/backtest-multi' && request.method === 'POST') {
        const config = await request.json() as BacktestConfig;
        config.randomSegments = config.randomSegments || 5;

        const results = await backtestEngine.runMultiSegmentBacktest(config);

        // Aggregate results
        const avgWinRate = results.reduce((sum, r) => sum + r.performance.winRate, 0) / results.length;
        const avgPnLPct = results.reduce((sum, r) => sum + r.performance.totalPnLPct, 0) / results.length;
        const avgSharpe = results.reduce((sum, r) => sum + r.performance.sharpeRatio, 0) / results.length;

        return new Response(JSON.stringify({
          success: true,
          segmentCount: results.length,
          aggregatePerformance: {
            avgWinRate,
            avgPnLPct,
            avgSharpe
          },
          results
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      // Route: Get backtest results
      if (path.startsWith('/results/')) {
        const id = path.split('/').pop();
        const result = await env.TRADING_KV.get(`backtest:${id}`, 'json');

        if (!result) {
          return new Response(JSON.stringify({
            success: false,
            error: 'Backtest result not found'
          }), { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
        }

        return new Response(JSON.stringify({
          success: true,
          result
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      // Default: API info
      return new Response(JSON.stringify({
        status: 'ok',
        name: 'Coinswarm Backtest Worker',
        endpoints: {
          'POST /backtest': 'Run backtest on random historical segment',
          'POST /backtest-multi': 'Run backtest across multiple random segments',
          'GET /results/{id}': 'Get backtest results'
        },
        features: [
          'Random time segment selection (prevents overfitting)',
          'Multi-pair testing (BTC, SOL, ETH × stablecoins)',
          '5-minute candles (maximum granularity)',
          'Cross-pair pattern detection',
          'Portfolio-level risk management',
          'Arbitrage and spread trading simulation',
          'Comprehensive performance metrics'
        ]
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });

    } catch (error: any) {
      return new Response(JSON.stringify({
        success: false,
        error: error.message,
        stack: error.stack
      }), {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }
  }
};
