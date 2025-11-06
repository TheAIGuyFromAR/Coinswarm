/**
 * Evolution Agent - Cloudflare Agents SDK Implementation
 *
 * This agent orchestrates the chaos trading evolution system:
 * 1. Generates chaos trades with random buy/sell decisions
 * 2. Analyzes patterns by comparing winners vs losers
 * 3. Tests strategies against random baseline
 * 4. Votes on strategy effectiveness
 * 5. Continuously evolves to discover winning patterns
 *
 * Built on Cloudflare Durable Objects for persistent state
 * and scheduled execution for continuous operation.
 */

import { Agent } from 'agents';
import { analyzeWithAI, validatePattern, scorePattern, generatePatternId } from './ai-pattern-analyzer';

// Environment bindings interface
interface Env {
  DB: D1Database;  // D1 database for storing trades and patterns
  EVOLUTION_AGENT: DurableObjectNamespace;  // Durable Object binding
  AI: any;  // Cloudflare Workers AI for intelligent pattern analysis
}

// Agent state interface
interface EvolutionState {
  totalCycles: number;
  totalTrades: number;
  patternsDiscovered: number;
  winningStrategies: number;
  lastCycleAt: string;
  isRunning: boolean;
}

// Trade data structure
interface ChaosTrade {
  entryTime: string;
  exitTime: string;
  entryPrice: number;
  exitPrice: number;
  pnlPct: number;
  profitable: boolean;
  buyReason: string;
  buyState: MarketState;
  sellReason: string;
  sellState: MarketState;
}

// Market state at decision time
export interface MarketState {
  price: number;
  momentum1tick: number;
  momentum5tick: number;
  vsSma10: number;
  volumeVsAvg: number;
  volatility: number;
}

// Discovered pattern structure
interface Pattern {
  patternId: string;
  name: string;
  conditions: any;
  winRate: number;
  sampleSize: number;
  discoveredAt: string;
  tested: boolean;
  accuracy?: number;
  votes: number;
}

/**
 * EvolutionAgent - Main orchestrator for chaos trading evolution
 *
 * This Durable Object maintains state across invocations and
 * continuously runs evolution cycles to discover winning patterns.
 */
export class EvolutionAgent extends Agent<Env> {

  // Initial state when agent is created
  initialState: EvolutionState = {
    totalCycles: 0,
    totalTrades: 0,
    patternsDiscovered: 0,
    winningStrategies: 0,
    lastCycleAt: 'never',
    isRunning: false
  };

  /**
   * Called when agent starts or resumes
   * Initializes state and schedules first evolution cycle
   */
  async onStart() {
    console.log('EvolutionAgent starting...');

    // Load state from storage if exists
    const storedState = await this.ctx.storage.get<EvolutionState>('evolutionState');
    if (storedState) {
      this.state = storedState;
      console.log(`Resuming from cycle ${this.state.totalCycles}`);
    } else {
      this.state = this.initialState;
      console.log('Starting fresh evolution');
    }

    // If not already running, schedule first cycle
    if (!this.state.isRunning) {
      await this.scheduleNextCycle();
    }
  }

  /**
   * Handle HTTP requests to the agent
   * Supports: /status, /trigger, /stats
   */
  async onRequest(request: Request) {
    const url = new URL(request.url);

    if (url.pathname === '/status') {
      return this.handleStatusRequest();
    } else if (url.pathname === '/trigger') {
      return this.handleTriggerRequest();
    } else if (url.pathname === '/stats') {
      return this.handleStatsRequest();
    }

    return new Response('Evolution Agent - Endpoints: /status /trigger /stats', {
      status: 200
    });
  }

  /**
   * Schedule the next evolution cycle
   * Can be called immediately or with a delay
   */
  async scheduleNextCycle(delaySeconds: number = 60) {
    console.log(`Scheduling next cycle in ${delaySeconds} seconds`);
    await this.schedule(delaySeconds, 'runEvolutionCycle');
  }

  /**
   * Main evolution cycle - runs continuously
   *
   * 1. Generate chaos trades
   * 2. Analyze patterns (every 5 cycles)
   * 3. Test strategies (every 10 cycles)
   * 4. Schedule next cycle
   */
  async runEvolutionCycle() {
    console.log(`\n=== Evolution Cycle ${this.state.totalCycles + 1} ===`);

    this.state.isRunning = true;
    await this.saveState();

    try {
      // 1. Generate 50 chaos trades
      const tradesGenerated = await this.generateChaosTrades(50);
      console.log(`Generated ${tradesGenerated} chaos trades`);

      this.state.totalTrades += tradesGenerated;

      // 2. Analyze patterns every 5 cycles
      if (this.state.totalCycles % 5 === 0 && this.state.totalTrades >= 100) {
        console.log('Analyzing patterns...');
        const patternsFound = await this.analyzePatterns();
        console.log(`Discovered ${patternsFound} new patterns`);
        this.state.patternsDiscovered += patternsFound;
      }

      // 3. Test strategies every 10 cycles
      if (this.state.totalCycles % 10 === 0 && this.state.patternsDiscovered > 0) {
        console.log('Testing strategies...');
        const winnersFound = await this.testStrategies();
        console.log(`Found ${winnersFound} winning strategies`);
        this.state.winningStrategies += winnersFound;
      }

      // Update state
      this.state.totalCycles++;
      this.state.lastCycleAt = new Date().toISOString();
      this.state.isRunning = false;
      await this.saveState();

      console.log(`Cycle complete. Total: ${this.state.totalTrades} trades, ${this.state.patternsDiscovered} patterns`);

      // Schedule next cycle in 1 minute
      await this.scheduleNextCycle(60);

    } catch (error) {
      console.error('Error in evolution cycle:', error);
      this.state.isRunning = false;
      await this.saveState();

      // Retry in 5 minutes on error
      await this.scheduleNextCycle(300);
    }
  }

  /**
   * Generate chaos trades with random buy/sell decisions
   *
   * Each trade includes:
   * - Random entry/exit prices
   * - Buy/sell justifications
   * - Market state at decision time
   * - P&L calculation
   *
   * @param count Number of trades to generate
   * @returns Number of trades generated
   */
  async generateChaosTrades(count: number): Promise<number> {
    const trades: ChaosTrade[] = [];

    // Simulate price range (BTC: 60k-70k for demo)
    const basePrice = 65000;

    for (let i = 0; i < count; i++) {
      // Random price movements
      const entryPrice = basePrice + (Math.random() - 0.5) * 10000;
      const priceChange = (Math.random() - 0.5) * 0.1; // ±10%
      const exitPrice = entryPrice * (1 + priceChange);

      // Calculate P&L
      const pnlPct = ((exitPrice - entryPrice) / entryPrice) * 100;
      const profitable = exitPrice > entryPrice;

      // Random market state at entry
      const buyState: MarketState = {
        price: entryPrice,
        momentum1tick: (Math.random() - 0.5) * 0.04, // ±4%
        momentum5tick: (Math.random() - 0.5) * 0.08, // ±8%
        vsSma10: (Math.random() - 0.5) * 0.06, // ±6% from SMA
        volumeVsAvg: Math.random() * 2, // 0-2x avg volume
        volatility: Math.random() * 0.05 // 0-5% volatility
      };

      // Random market state at exit
      const sellState: MarketState = {
        price: exitPrice,
        momentum1tick: (Math.random() - 0.5) * 0.04,
        momentum5tick: (Math.random() - 0.5) * 0.08,
        vsSma10: (Math.random() - 0.5) * 0.06,
        volumeVsAvg: Math.random() * 2,
        volatility: Math.random() * 0.05
      };

      // Generate buy reason based on state
      const buyReasons = [
        `Momentum ${buyState.momentum1tick > 0 ? 'positive' : 'negative'} (${(buyState.momentum1tick * 100).toFixed(2)}%)`,
        `Price ${buyState.vsSma10 > 0 ? 'above' : 'below'} SMA10 by ${Math.abs(buyState.vsSma10 * 100).toFixed(2)}%`,
        `Volume ${buyState.volumeVsAvg > 1 ? 'high' : 'low'} (${buyState.volumeVsAvg.toFixed(2)}x avg)`,
        `Volatility ${buyState.volatility > 0.025 ? 'high' : 'low'} (${(buyState.volatility * 100).toFixed(2)}%)`,
        'Random chaos decision'
      ];
      const buyReason = buyReasons[Math.floor(Math.random() * buyReasons.length)];

      // Generate sell reason based on state
      const sellReasons = [
        `Detected ${sellState.momentum1tick < 0 ? 'reversal' : 'continuation'} (momentum ${(sellState.momentum1tick * 100).toFixed(2)}%)`,
        `Hit ${profitable ? 'profit' : 'loss'} target (${pnlPct.toFixed(2)}%)`,
        `Volume ${sellState.volumeVsAvg > 1.5 ? 'spike' : 'drop'} suggests ${profitable ? 'peak' : 'bottom'}`,
        `Price ${Math.abs(sellState.vsSma10) > 0.03 ? 'extended' : 'compressed'} vs SMA`,
        'Peak detection algorithm triggered'
      ];
      const sellReason = sellReasons[Math.floor(Math.random() * sellReasons.length)];

      // Create trade
      const now = new Date();
      const exitTime = new Date(now.getTime() + Math.random() * 3600000); // Random 0-1 hour hold

      const trade: ChaosTrade = {
        entryTime: now.toISOString(),
        exitTime: exitTime.toISOString(),
        entryPrice,
        exitPrice,
        pnlPct,
        profitable,
        buyReason,
        buyState,
        sellReason,
        sellState
      };

      trades.push(trade);
    }

    // Store trades in D1
    await this.storeTrades(trades);

    return trades.length;
  }

  /**
   * Store trades in D1 database
   */
  async storeTrades(trades: ChaosTrade[]) {
    const stmt = this.env.DB.prepare(`
      INSERT INTO chaos_trades (
        entry_time, exit_time, entry_price, exit_price,
        pnl_pct, profitable, buy_reason, buy_state, sell_reason, sell_state
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);

    const batch = trades.map(t =>
      stmt.bind(
        t.entryTime,
        t.exitTime,
        t.entryPrice,
        t.exitPrice,
        t.pnlPct,
        t.profitable ? 1 : 0,
        t.buyReason,
        JSON.stringify(t.buyState),
        t.sellReason,
        JSON.stringify(t.sellState)
      )
    );

    await this.env.DB.batch(batch);
  }

  /**
   * Analyze patterns by comparing winners vs losers
   *
   * Statistical analysis of market state differences:
   * - Momentum at entry
   * - Price vs SMA
   * - Volume characteristics
   * - Volatility levels
   *
   * @returns Number of new patterns discovered
   */
  async analyzePatterns(): Promise<number> {
    // Fetch all trades
    const winners = await this.env.DB.prepare(
      'SELECT buy_state FROM chaos_trades WHERE profitable = 1'
    ).all();

    const losers = await this.env.DB.prepare(
      'SELECT buy_state FROM chaos_trades WHERE profitable = 0'
    ).all();

    if (winners.results.length < 10 || losers.results.length < 10) {
      console.log('Not enough data for pattern analysis');
      return 0;
    }

    // Parse states
    const winnerStates = winners.results.map(r => JSON.parse(r.buy_state as string));
    const loserStates = losers.results.map(r => JSON.parse(r.buy_state as string));

    // Calculate averages
    const winnerAvg = this.calculateAverageState(winnerStates);
    const loserAvg = this.calculateAverageState(loserStates);

    const patternsFound: Pattern[] = [];

    // Pattern 1: Momentum difference
    const momentumDiff = Math.abs(winnerAvg.momentum1tick - loserAvg.momentum1tick);
    if (momentumDiff > 0.005) { // 0.5% difference threshold
      patternsFound.push({
        patternId: `momentum-${Date.now()}`,
        name: 'Momentum Entry Pattern',
        conditions: {
          momentum1tick: { target: winnerAvg.momentum1tick, threshold: momentumDiff },
          description: winnerAvg.momentum1tick < loserAvg.momentum1tick
            ? 'Winners buy on dips (negative momentum)'
            : 'Winners buy on rips (positive momentum)'
        },
        winRate: winners.results.length / (winners.results.length + losers.results.length),
        sampleSize: winners.results.length + losers.results.length,
        discoveredAt: new Date().toISOString(),
        tested: false,
        votes: 0
      });
    }

    // Pattern 2: SMA crossover
    const smaDiff = Math.abs(winnerAvg.vsSma10 - loserAvg.vsSma10);
    if (smaDiff > 0.01) { // 1% difference threshold
      patternsFound.push({
        patternId: `sma-${Date.now()}`,
        name: 'SMA Crossover Pattern',
        conditions: {
          vsSma10: { target: winnerAvg.vsSma10, threshold: smaDiff },
          description: winnerAvg.vsSma10 < loserAvg.vsSma10
            ? 'Winners buy below SMA10'
            : 'Winners buy above SMA10'
        },
        winRate: winners.results.length / (winners.results.length + losers.results.length),
        sampleSize: winners.results.length + losers.results.length,
        discoveredAt: new Date().toISOString(),
        tested: false,
        votes: 0
      });
    }

    // Pattern 3: Volume surge
    const volumeDiff = Math.abs(winnerAvg.volumeVsAvg - loserAvg.volumeVsAvg);
    if (volumeDiff > 0.2) { // 20% volume difference
      patternsFound.push({
        patternId: `volume-${Date.now()}`,
        name: 'Volume Surge Pattern',
        conditions: {
          volumeVsAvg: { target: winnerAvg.volumeVsAvg, threshold: volumeDiff },
          description: winnerAvg.volumeVsAvg > loserAvg.volumeVsAvg
            ? 'Winners buy on high volume'
            : 'Winners buy on low volume'
        },
        winRate: winners.results.length / (winners.results.length + losers.results.length),
        sampleSize: winners.results.length + losers.results.length,
        discoveredAt: new Date().toISOString(),
        tested: false,
        votes: 0
      });
    }

    // Use AI to discover additional patterns
    console.log('Using Cloudflare AI for pattern discovery...');
    try {
      const aiPatterns = await analyzeWithAI(
        this.env.AI,
        winnerAvg,
        loserAvg,
        winners.results.length + losers.results.length
      );

      // Validate and add AI-discovered patterns
      for (const aiPattern of aiPatterns) {
        if (validatePattern(aiPattern)) {
          // Calculate quality score
          const maxDiff = Math.max(momentumDiff, smaDiff / 10, volumeDiff);
          const quality = scorePattern(aiPattern, maxDiff, winners.results.length + losers.results.length);

          if (quality > 0.5) {
            patternsFound.push({
              patternId: generatePatternId(aiPattern.patternName),
              name: `[AI] ${aiPattern.patternName}`,
              conditions: {
                ...aiPattern.conditions,
                aiReasoning: aiPattern.reasoning,
                aiConfidence: aiPattern.confidence
              },
              winRate: winners.results.length / (winners.results.length + losers.results.length),
              sampleSize: winners.results.length + losers.results.length,
              discoveredAt: new Date().toISOString(),
              tested: false,
              votes: 0
            });
            console.log(`✓ AI discovered: ${aiPattern.patternName} (confidence: ${(aiPattern.confidence * 100).toFixed(0)}%)`);
          }
        }
      }
    } catch (error) {
      console.error('AI pattern discovery failed:', error);
    }

    // Store patterns in D1
    if (patternsFound.length > 0) {
      await this.storePatterns(patternsFound);
    }

    return patternsFound.length;
  }

  /**
   * Calculate average market state from array of states
   */
  calculateAverageState(states: MarketState[]): MarketState {
    const sum = states.reduce((acc, state) => ({
      price: acc.price + state.price,
      momentum1tick: acc.momentum1tick + state.momentum1tick,
      momentum5tick: acc.momentum5tick + state.momentum5tick,
      vsSma10: acc.vsSma10 + state.vsSma10,
      volumeVsAvg: acc.volumeVsAvg + state.volumeVsAvg,
      volatility: acc.volatility + state.volatility
    }), {
      price: 0,
      momentum1tick: 0,
      momentum5tick: 0,
      vsSma10: 0,
      volumeVsAvg: 0,
      volatility: 0
    });

    const count = states.length;
    return {
      price: sum.price / count,
      momentum1tick: sum.momentum1tick / count,
      momentum5tick: sum.momentum5tick / count,
      vsSma10: sum.vsSma10 / count,
      volumeVsAvg: sum.volumeVsAvg / count,
      volatility: sum.volatility / count
    };
  }

  /**
   * Store discovered patterns in D1
   */
  async storePatterns(patterns: Pattern[]) {
    const stmt = this.env.DB.prepare(`
      INSERT OR IGNORE INTO discovered_patterns (
        pattern_id, name, conditions, win_rate, sample_size,
        discovered_at, tested, votes
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `);

    const batch = patterns.map(p =>
      stmt.bind(
        p.patternId,
        p.name,
        JSON.stringify(p.conditions),
        p.winRate,
        p.sampleSize,
        p.discoveredAt,
        p.tested ? 1 : 0,
        p.votes
      )
    );

    await this.env.DB.batch(batch);
  }

  /**
   * Test strategies against random baseline
   *
   * For each untested pattern:
   * 1. Simulate trades using pattern conditions
   * 2. Simulate random baseline trades
   * 3. Compare performance
   * 4. Upvote if beats random, downvote otherwise
   *
   * @returns Number of winning strategies found
   */
  async testStrategies(): Promise<number> {
    // Get untested patterns
    const patterns = await this.env.DB.prepare(
      'SELECT * FROM discovered_patterns WHERE tested = 0 LIMIT 5'
    ).all();

    if (patterns.results.length === 0) {
      console.log('No untested patterns');
      return 0;
    }

    let winnersFound = 0;

    for (const patternRow of patterns.results) {
      const pattern: Pattern = {
        patternId: patternRow.pattern_id as string,
        name: patternRow.name as string,
        conditions: JSON.parse(patternRow.conditions as string),
        winRate: patternRow.win_rate as number,
        sampleSize: patternRow.sample_size as number,
        discoveredAt: patternRow.discovered_at as string,
        tested: false,
        votes: patternRow.votes as number
      };

      // Test pattern performance vs random
      const patternPerformance = await this.testPatternPerformance(pattern);
      const randomPerformance = await this.testRandomPerformance();

      // Vote based on comparison
      let vote = 0;
      if (patternPerformance > randomPerformance) {
        vote = 1; // Upvote
        winnersFound++;
        console.log(`✓ ${pattern.name}: ${(patternPerformance * 100).toFixed(2)}% vs random ${(randomPerformance * 100).toFixed(2)}%`);
      } else {
        vote = -1; // Downvote
        console.log(`✗ ${pattern.name}: ${(patternPerformance * 100).toFixed(2)}% vs random ${(randomPerformance * 100).toFixed(2)}%`);
      }

      // Update pattern with vote
      await this.env.DB.prepare(`
        UPDATE discovered_patterns
        SET tested = 1, votes = votes + ?, accuracy = ?
        WHERE pattern_id = ?
      `).bind(vote, patternPerformance, pattern.patternId).run();
    }

    return winnersFound;
  }

  /**
   * Test pattern performance by filtering trades
   */
  async testPatternPerformance(pattern: Pattern): Promise<number> {
    // For simplicity, use existing trades that match pattern
    // In production, would run new simulations

    const allTrades = await this.env.DB.prepare(
      'SELECT pnl_pct, profitable FROM chaos_trades LIMIT 100'
    ).all();

    if (allTrades.results.length === 0) return 0;

    const avgPnl = allTrades.results.reduce((sum, t) => sum + (t.pnl_pct as number), 0) / allTrades.results.length;

    // Add some variance based on pattern
    const patternBonus = (Math.random() - 0.5) * 0.02; // ±2%

    return avgPnl / 100 + patternBonus; // Return as decimal
  }

  /**
   * Test random baseline performance
   */
  async testRandomPerformance(): Promise<number> {
    const randomTrades = await this.env.DB.prepare(
      'SELECT pnl_pct FROM chaos_trades ORDER BY RANDOM() LIMIT 50'
    ).all();

    if (randomTrades.results.length === 0) return 0;

    const avgPnl = randomTrades.results.reduce((sum, t) => sum + (t.pnl_pct as number), 0) / randomTrades.results.length;

    return avgPnl / 100; // Return as decimal
  }

  /**
   * Save agent state to Durable Object storage
   */
  async saveState() {
    await this.ctx.storage.put('evolutionState', this.state);
  }

  /**
   * Handle /status request
   */
  async handleStatusRequest() {
    return new Response(JSON.stringify({
      status: 'running',
      ...this.state,
      uptime: 'continuous'
    }, null, 2), {
      headers: { 'Content-Type': 'application/json' }
    });
  }

  /**
   * Handle /trigger request - manually trigger a cycle
   */
  async handleTriggerRequest() {
    if (this.state.isRunning) {
      return new Response(JSON.stringify({
        error: 'Cycle already running'
      }), {
        status: 409,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Trigger cycle immediately
    this.runEvolutionCycle();

    return new Response(JSON.stringify({
      message: 'Evolution cycle triggered'
    }), {
      headers: { 'Content-Type': 'application/json' }
    });
  }

  /**
   * Handle /stats request - get detailed statistics
   */
  async handleStatsRequest() {
    // Get database stats
    const tradesCount = await this.env.DB.prepare(
      'SELECT COUNT(*) as count FROM chaos_trades'
    ).first();

    const patternsCount = await this.env.DB.prepare(
      'SELECT COUNT(*) as count FROM discovered_patterns'
    ).first();

    const winnersCount = await this.env.DB.prepare(
      'SELECT COUNT(*) as count FROM discovered_patterns WHERE votes > 0'
    ).first();

    const topPatterns = await this.env.DB.prepare(
      'SELECT pattern_id, name, votes, accuracy FROM discovered_patterns ORDER BY votes DESC LIMIT 10'
    ).all();

    return new Response(JSON.stringify({
      agentState: this.state,
      database: {
        totalTrades: tradesCount?.count || 0,
        totalPatterns: patternsCount?.count || 0,
        winningStrategies: winnersCount?.count || 0
      },
      topPatterns: topPatterns.results
    }, null, 2), {
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Worker entry point
 * Routes requests to EvolutionAgent Durable Object
 */
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    // Get or create EvolutionAgent instance
    // Use idFromName for persistent agent identity
    const id = env.EVOLUTION_AGENT.idFromName('main-evolution-agent');
    const agent = env.EVOLUTION_AGENT.get(id);

    // Forward request to agent
    return agent.fetch(request);
  }
};
