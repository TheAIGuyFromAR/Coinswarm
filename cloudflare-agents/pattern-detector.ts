/**
 * Pattern Detector for Cloudflare Workers
 *
 * Detects trading patterns in real-time across multiple pairs:
 * 1. Correlation patterns
 * 2. Spread trading opportunities
 * 3. Arbitrage opportunities
 * 4. Lead-lag patterns
 *
 * Runs in Cloudflare Workers for sub-100ms pattern detection
 */

interface PriceData {
  symbol: string;
  price: number;
  timestamp: string;
  volume?: number;
}

interface ArbitrageOpportunity {
  type: 'stablecoin' | 'triangular' | 'statistical';
  pairs: string[];
  profitPct: number;
  confidence: number;
  description: string;
  executionSteps: string[];
}

interface SpreadOpportunity {
  pair1: string;
  pair2: string;
  spread: number;
  meanSpread: number;
  zScore: number;
  signal: string;
}

/**
 * Stablecoin Arbitrage Detector
 * Finds price differences across BTC-USDT, BTC-USDC, BTC-BUSD
 */
export class StablecoinArbDetector {
  private minProfitPct: number;
  private transactionCost: number;

  constructor(minProfitPct = 0.001, transactionCost = 0.001) {
    this.minProfitPct = minProfitPct;
    this.transactionCost = transactionCost;
  }

  detect(prices: Record<string, number>): ArbitrageOpportunity[] {
    const opportunities: ArbitrageOpportunity[] = [];

    // Group by base asset
    const assetPrices: Record<string, Record<string, number>> = {};

    for (const [pair, price] of Object.entries(prices)) {
      const [base, quote] = pair.split('-');
      if (!assetPrices[base]) {
        assetPrices[base] = {};
      }
      assetPrices[base][quote] = price;
    }

    // Check for spreads across stablecoins
    for (const [base, stablecoins] of Object.entries(assetPrices)) {
      const coins = Object.keys(stablecoins);

      for (let i = 0; i < coins.length; i++) {
        for (let j = i + 1; j < coins.length; j++) {
          const stable1 = coins[i];
          const stable2 = coins[j];
          const price1 = stablecoins[stable1];
          const price2 = stablecoins[stable2];

          // Calculate spread
          const spreadPct = Math.abs(price2 - price1) / price1;
          const netProfit = spreadPct - (2 * this.transactionCost);

          if (netProfit > this.minProfitPct) {
            const buyPair = price1 < price2 ? `${base}-${stable1}` : `${base}-${stable2}`;
            const sellPair = price1 < price2 ? `${base}-${stable2}` : `${base}-${stable1}`;

            opportunities.push({
              type: 'stablecoin',
              pairs: [buyPair, sellPair],
              profitPct: netProfit * 100,
              confidence: 0.95,
              description: `Stablecoin arbitrage: ${buyPair} at $${Math.min(price1, price2).toFixed(2)} vs ${sellPair} at $${Math.max(price1, price2).toFixed(2)}`,
              executionSteps: [
                `Buy ${base} on ${buyPair}`,
                `Sell ${base} on ${sellPair}`,
                `Profit: ${(netProfit * 100).toFixed(3)}%`
              ]
            });
          }
        }
      }
    }

    return opportunities;
  }
}

/**
 * Triangular Arbitrage Detector
 * Finds profit in BTC→SOL→USD loops
 */
export class TriangularArbDetector {
  private minProfitPct: number;
  private transactionCost: number;

  constructor(minProfitPct = 0.001, transactionCost = 0.001) {
    this.minProfitPct = minProfitPct;
    this.transactionCost = transactionCost;
  }

  detect(prices: Record<string, number>): ArbitrageOpportunity[] {
    const opportunities: ArbitrageOpportunity[] = [];

    // Check BTC-SOL-USD triangle
    const btcUsd = prices['BTC-USDT'];
    const solUsd = prices['SOL-USDT'];
    const btcSol = prices['BTC-SOL'];

    if (btcUsd && solUsd && btcSol) {
      // Calculate implied BTC-SOL from cross rates
      const impliedBtcSol = btcUsd / solUsd;
      const spread = Math.abs(btcSol - impliedBtcSol) / impliedBtcSol;
      const netProfit = spread - (3 * this.transactionCost);

      if (netProfit > this.minProfitPct) {
        opportunities.push({
          type: 'triangular',
          pairs: ['BTC-USDT', 'SOL-USDT', 'BTC-SOL'],
          profitPct: netProfit * 100,
          confidence: 0.8,
          description: `Triangular arbitrage: Direct BTC-SOL (${btcSol.toFixed(2)}) vs implied (${impliedBtcSol.toFixed(2)})`,
          executionSteps: [
            'Buy BTC with USD',
            'Trade BTC for SOL',
            'Sell SOL for USD',
            `Profit: ${(netProfit * 100).toFixed(3)}%`
          ]
        });
      }
    }

    return opportunities;
  }
}

/**
 * Spread Trading Detector
 * Finds mean reversion opportunities on cointegrated pairs
 */
export class SpreadTradingDetector {
  private spreadHistory: Map<string, number[]>;
  private lookbackPeriod: number;

  constructor(lookbackPeriod = 100) {
    this.spreadHistory = new Map();
    this.lookbackPeriod = lookbackPeriod;
  }

  detect(prices: Record<string, number>): SpreadOpportunity[] {
    const opportunities: SpreadOpportunity[] = [];

    // Find same-asset pairs (BTC-USDT vs BTC-USDC)
    const pairs = Object.keys(prices);

    for (let i = 0; i < pairs.length; i++) {
      for (let j = i + 1; j < pairs.length; j++) {
        const pair1 = pairs[i];
        const pair2 = pairs[j];

        // Check if same base asset
        const [base1] = pair1.split('-');
        const [base2] = pair2.split('-');

        if (base1 !== base2) continue;

        // Calculate spread
        const price1 = prices[pair1];
        const price2 = prices[pair2];
        const spread = price1 - price2;

        // Track spread history
        const key = `${pair1}_${pair2}`;
        if (!this.spreadHistory.has(key)) {
          this.spreadHistory.set(key, []);
        }
        const history = this.spreadHistory.get(key)!;
        history.push(spread);
        if (history.length > this.lookbackPeriod) {
          history.shift();
        }

        // Calculate statistics
        if (history.length < 10) continue;

        const meanSpread = history.reduce((a, b) => a + b, 0) / history.length;
        const variance = history.reduce((a, b) => a + Math.pow(b - meanSpread, 2), 0) / history.length;
        const stdSpread = Math.sqrt(variance);

        if (stdSpread === 0) continue;

        const zScore = (spread - meanSpread) / stdSpread;

        // Detect opportunities
        if (Math.abs(zScore) > 2.0) {
          opportunities.push({
            pair1,
            pair2,
            spread,
            meanSpread,
            zScore,
            signal: zScore > 0
              ? `Buy ${pair2}, Sell ${pair1} (spread will narrow)`
              : `Buy ${pair1}, Sell ${pair2} (spread will widen)`
          });
        }
      }
    }

    return opportunities;
  }
}

/**
 * Multi-Pattern Detector
 * Combines all detection methods
 */
export class MultiPatternDetector {
  private stablecoinDetector: StablecoinArbDetector;
  private triangularDetector: TriangularArbDetector;
  private spreadDetector: SpreadTradingDetector;

  constructor() {
    this.stablecoinDetector = new StablecoinArbDetector();
    this.triangularDetector = new TriangularArbDetector();
    this.spreadDetector = new SpreadTradingDetector();
  }

  /**
   * Detect all patterns across current prices
   */
  detectAll(prices: Record<string, number>) {
    const arbOpportunities = [
      ...this.stablecoinDetector.detect(prices),
      ...this.triangularDetector.detect(prices)
    ];

    const spreadOpportunities = this.spreadDetector.detect(prices);

    // Sort arbitrage by profit
    arbOpportunities.sort((a, b) => b.profitPct - a.profitPct);

    return {
      arbitrage: arbOpportunities,
      spreads: spreadOpportunities,
      summary: {
        totalOpportunities: arbOpportunities.length + spreadOpportunities.length,
        bestArbProfit: arbOpportunities[0]?.profitPct || 0,
        highestZScore: Math.max(...spreadOpportunities.map(s => Math.abs(s.zScore)), 0)
      }
    };
  }
}
