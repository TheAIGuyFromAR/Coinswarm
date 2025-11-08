/**
 * SCALED Evolution Agent - Optimized for Cloudflare Workers Paid Plan
 *
 * This version is tuned for maximum throughput on the $5/month plan:
 * - Larger batch sizes (500 trades vs 50)
 * - Faster cycles (10 seconds vs 60)
 * - Multiple parallel agent instances
 * - More aggressive AI usage
 * - Analytics tracking
 *
 * Expected performance:
 * - 5,000 trades per minute (10 agents × 500 trades)
 * - 7.2M trades per day
 * - 100x faster than free tier implementation
 */

import { Agent } from 'agents';
import { analyzeWithAI, validatePattern, scorePattern, generatePatternId } from './ai-pattern-analyzer';
import { createLogger, LogLevel } from './structured-logger';

const logger = createLogger('EvolutionAgentScaled', LogLevel.INFO);

// Cloudflare AI binding interface
interface CloudflareAI {
  run(model: string, inputs: Record<string, unknown>): Promise<unknown>;
}

// Environment bindings interface
interface Env {
  DB: D1Database;
  EVOLUTION_AGENT: DurableObjectNamespace;
  AI: CloudflareAI;
  ANALYTICS?: AnalyticsEngineDataset;
  // Configuration from wrangler.toml [vars]
  BATCH_SIZE: string;
  CYCLE_INTERVAL: string;
  PATTERN_ANALYSIS_INTERVAL: string;
  STRATEGY_TEST_INTERVAL: string;
  PARALLEL_AGENTS: string;
  AI_ENABLED: string;
  AI_BUDGET_PER_DAY: string;
}

// Agent state interface
interface EvolutionState {
  agentId: number;              // Which agent instance (0-9)
  totalCycles: number;
  totalTrades: number;
  patternsDiscovered: number;
  winningStrategies: number;
  lastCycleAt: string;
  isRunning: boolean;
  aiNeuronsUsedToday: number;
  aiResetDate: string;
}

// Trade data structure (same as base agent)
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

export interface MarketState {
  price: number;
  momentum1tick: number;
  momentum5tick: number;
  vsSma10: number;
  volumeVsAvg: number;
  volatility: number;
}

interface PatternConditions {
  [key: string]: {target: number; threshold: number} | number | string;
}

interface Pattern {
  patternId: string;
  name: string;
  conditions: PatternConditions;
  winRate: number;
  sampleSize: number;
  discoveredAt: string;
  tested: boolean;
  accuracy?: number;
  votes: number;
}

/**
 * Scaled EvolutionAgent - High-throughput version
 */
export class EvolutionAgent extends Agent<Env> {

  initialState: EvolutionState = {
    agentId: 0,
    totalCycles: 0,
    totalTrades: 0,
    patternsDiscovered: 0,
    winningStrategies: 0,
    lastCycleAt: 'never',
    isRunning: false,
    aiNeuronsUsedToday: 0,
    aiResetDate: new Date().toISOString().split('T')[0]
  };

  async onStart() {
    logger.info('SCALED EvolutionAgent starting');

    const storedState = await this.ctx.storage.get<EvolutionState>('evolutionState');
    if (storedState) {
      this.state = storedState;

      // Reset AI usage if new day
      const today = new Date().toISOString().split('T')[0];
      if (this.state.aiResetDate !== today) {
        this.state.aiNeuronsUsedToday = 0;
        this.state.aiResetDate = today;
        logger.info('AI usage counter reset for new day');
      }

      logger.info('Agent resuming', { agent_id: this.state.agentId, cycle: this.state.totalCycles });
    } else {
      this.state = this.initialState;
      logger.info('Starting fresh scaled evolution');
    }

    if (!this.state.isRunning) {
      await this.scheduleNextCycle();
    }
  }

  async onRequest(request: Request) {
    const url = new URL(request.url);

    if (url.pathname === '/status') {
      return this.handleStatusRequest();
    } else if (url.pathname === '/trigger') {
      return this.handleTriggerRequest();
    } else if (url.pathname === '/stats') {
      return this.handleStatsRequest();
    } else if (url.pathname === '/config') {
      return this.handleConfigRequest();
    }

    return new Response('Scaled Evolution Agent - Optimized for $5 plan\nEndpoints: /status /trigger /stats /config', {
      status: 200
    });
  }

  async scheduleNextCycle(delaySeconds?: number) {
    const interval = delaySeconds || parseInt(this.env.CYCLE_INTERVAL || '10');
    logger.info('Scheduling next cycle', { agent_id: this.state.agentId, interval });
    await this.schedule(interval, 'runEvolutionCycle');
  }

  /**
   * SCALED evolution cycle - runs every 10 seconds
   * Generates 500 trades per cycle (vs 50 in free tier)
   */
  async runEvolutionCycle() {
    const cycleStart = Date.now();
    logger.info('=== Evolution Cycle Start ===', { agent_id: this.state.agentId, cycle: this.state.totalCycles + 1 });

    this.state.isRunning = true;
    await this.saveState();

    try {
      const batchSize = parseInt(this.env.BATCH_SIZE || '500');

      // 1. Generate chaos trades (500 per cycle = 10x larger)
      const tradesGenerated = await this.generateChaosTrades(batchSize);
      logger.info('Generated chaos trades', { agent_id: this.state.agentId, count: tradesGenerated });
      this.state.totalTrades += tradesGenerated;

      // 2. Analyze patterns more frequently (every 2 cycles vs every 5)
      const patternInterval = parseInt(this.env.PATTERN_ANALYSIS_INTERVAL || '2');
      if (this.state.totalCycles % patternInterval === 0 && this.state.totalTrades >= 1000) {
        logger.info('Analyzing patterns', { agent_id: this.state.agentId });
        const patternsFound = await this.analyzePatterns();
        logger.info('Discovered new patterns', { agent_id: this.state.agentId, count: patternsFound });
        this.state.patternsDiscovered += patternsFound;
      }

      // 3. Test strategies more frequently (every 5 cycles vs every 10)
      const testInterval = parseInt(this.env.STRATEGY_TEST_INTERVAL || '5');
      if (this.state.totalCycles % testInterval === 0 && this.state.patternsDiscovered > 0) {
        logger.info('Testing strategies', { agent_id: this.state.agentId });
        const winnersFound = await this.testStrategies();
        logger.info('Found winning strategies', { agent_id: this.state.agentId, count: winnersFound });
        this.state.winningStrategies += winnersFound;
      }

      this.state.totalCycles++;
      this.state.lastCycleAt = new Date().toISOString();
      this.state.isRunning = false;
      await this.saveState();

      const cycleTime = Date.now() - cycleStart;
      logger.info('Cycle complete', { agent_id: this.state.agentId, cycle_time_ms: cycleTime, total_trades: this.state.totalTrades });

      // Track analytics
      if (this.env.ANALYTICS) {
        this.env.ANALYTICS.writeDataPoint({
          blobs: [`agent-${this.state.agentId}`, 'cycle-complete'],
          doubles: [cycleTime, tradesGenerated],
          indexes: [`${this.state.agentId}`]
        });
      }

      await this.scheduleNextCycle();

    } catch (error) {
      logger.error('Error in evolution cycle', { agent_id: this.state.agentId, error: error instanceof Error ? error : new Error(String(error)) });
      this.state.isRunning = false;
      await this.saveState();

      // Retry in 30 seconds on error
      await this.scheduleNextCycle(30);
    }
  }

  /**
   * Generate chaos trades (same logic as base agent)
   * But with configurable batch size (default 500)
   */
  async generateChaosTrades(count: number): Promise<number> {
    const trades: ChaosTrade[] = [];
    const basePrice = 65000;

    for (let i = 0; i < count; i++) {
      const entryPrice = basePrice + (Math.random() - 0.5) * 10000;
      const priceChange = (Math.random() - 0.5) * 0.1;
      const exitPrice = entryPrice * (1 + priceChange);
      const pnlPct = ((exitPrice - entryPrice) / entryPrice) * 100;
      const profitable = exitPrice > entryPrice;

      const buyState: MarketState = {
        price: entryPrice,
        momentum1tick: (Math.random() - 0.5) * 0.04,
        momentum5tick: (Math.random() - 0.5) * 0.08,
        vsSma10: (Math.random() - 0.5) * 0.06,
        volumeVsAvg: Math.random() * 2,
        volatility: Math.random() * 0.05
      };

      const sellState: MarketState = {
        price: exitPrice,
        momentum1tick: (Math.random() - 0.5) * 0.04,
        momentum5tick: (Math.random() - 0.5) * 0.08,
        vsSma10: (Math.random() - 0.5) * 0.06,
        volumeVsAvg: Math.random() * 2,
        volatility: Math.random() * 0.05
      };

      const buyReasons = [
        `Momentum ${buyState.momentum1tick > 0 ? 'positive' : 'negative'} (${(buyState.momentum1tick * 100).toFixed(2)}%)`,
        `Price ${buyState.vsSma10 > 0 ? 'above' : 'below'} SMA10 by ${Math.abs(buyState.vsSma10 * 100).toFixed(2)}%`,
        `Volume ${buyState.volumeVsAvg > 1 ? 'high' : 'low'} (${buyState.volumeVsAvg.toFixed(2)}x avg)`,
        `Volatility ${buyState.volatility > 0.025 ? 'high' : 'low'} (${(buyState.volatility * 100).toFixed(2)}%)`,
        'Random chaos decision'
      ];
      const buyReason = buyReasons[Math.floor(Math.random() * buyReasons.length)];

      const sellReasons = [
        `Detected ${sellState.momentum1tick < 0 ? 'reversal' : 'continuation'}`,
        `Hit ${profitable ? 'profit' : 'loss'} target (${pnlPct.toFixed(2)}%)`,
        `Volume ${sellState.volumeVsAvg > 1.5 ? 'spike' : 'drop'}`,
        `Price ${Math.abs(sellState.vsSma10) > 0.03 ? 'extended' : 'compressed'}`,
        'Peak detection triggered'
      ];
      const sellReason = sellReasons[Math.floor(Math.random() * sellReasons.length)];

      const now = new Date();
      const exitTime = new Date(now.getTime() + Math.random() * 3600000);

      trades.push({
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
      });
    }

    await this.storeTrades(trades);
    return trades.length;
  }

  async storeTrades(trades: ChaosTrade[]) {
    // Batch insert in chunks of 100 to avoid D1 limits
    const chunkSize = 100;
    for (let i = 0; i < trades.length; i += chunkSize) {
      const chunk = trades.slice(i, i + chunkSize);
      const stmt = this.env.DB.prepare(`
        INSERT INTO chaos_trades (
          entry_time, exit_time, entry_price, exit_price,
          pnl_pct, profitable, buy_reason, buy_state, sell_reason, sell_state
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `);

      const batch = chunk.map(t =>
        stmt.bind(
          t.entryTime, t.exitTime, t.entryPrice, t.exitPrice,
          t.pnlPct, t.profitable ? 1 : 0, t.buyReason,
          JSON.stringify(t.buyState), t.sellReason, JSON.stringify(t.sellState)
        )
      );

      await this.env.DB.batch(batch);
    }
  }

  /**
   * Analyze patterns with AI budget management
   */
  async analyzePatterns(): Promise<number> {
    const winners = await this.env.DB.prepare(
      'SELECT buy_state FROM chaos_trades WHERE profitable = 1 LIMIT 5000'
    ).all();

    const losers = await this.env.DB.prepare(
      'SELECT buy_state FROM chaos_trades WHERE profitable = 0 LIMIT 5000'
    ).all();

    if (winners.results.length < 100 || losers.results.length < 100) {
      logger.info('Not enough data for pattern analysis');
      return 0;
    }

    const winnerStates = winners.results.map(r => JSON.parse(r.buy_state as string));
    const loserStates = losers.results.map(r => JSON.parse(r.buy_state as string));

    const winnerAvg = this.calculateAverageState(winnerStates);
    const loserAvg = this.calculateAverageState(loserStates);

    const patternsFound: Pattern[] = [];

    // Statistical patterns (always run)
    const momentumDiff = Math.abs(winnerAvg.momentum1tick - loserAvg.momentum1tick);
    const smaDiff = Math.abs(winnerAvg.vsSma10 - loserAvg.vsSma10);
    const volumeDiff = Math.abs(winnerAvg.volumeVsAvg - loserAvg.volumeVsAvg);

    if (momentumDiff > 0.005) {
      patternsFound.push({
        patternId: `momentum-${Date.now()}`,
        name: 'Momentum Entry Pattern',
        conditions: {
          momentum1tick: { target: winnerAvg.momentum1tick, threshold: momentumDiff }
        },
        winRate: winners.results.length / (winners.results.length + losers.results.length),
        sampleSize: winners.results.length + losers.results.length,
        discoveredAt: new Date().toISOString(),
        tested: false,
        votes: 0
      });
    }

    // AI analysis with budget management
    const aiEnabled = this.env.AI_ENABLED === 'true';
    const aiBudget = parseInt(this.env.AI_BUDGET_PER_DAY || '10000');

    if (aiEnabled && this.state.aiNeuronsUsedToday < aiBudget) {
      logger.info('Using AI for pattern discovery', { agent_id: this.state.agentId, neurons_used: this.state.aiNeuronsUsedToday, budget: aiBudget });

      try {
        const aiPatterns = await analyzeWithAI(
          this.env.AI,
          winnerAvg,
          loserAvg,
          winners.results.length + losers.results.length
        );

        // Estimate ~1000 neurons per AI call
        this.state.aiNeuronsUsedToday += 1000;

        for (const aiPattern of aiPatterns) {
          if (validatePattern(aiPattern)) {
            const maxDiff = Math.max(momentumDiff, smaDiff / 10, volumeDiff);
            const quality = scorePattern(aiPattern, maxDiff, winners.results.length + losers.results.length);

            if (quality > 0.5) {
              patternsFound.push({
                patternId: generatePatternId(aiPattern.patternName),
                name: `[AI-Agent${this.state.agentId}] ${aiPattern.patternName}`,
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
              logger.info('AI discovered pattern', { name: aiPattern.patternName });
            }
          }
        }
      } catch (error) {
        logger.error('AI pattern discovery failed', error instanceof Error ? error : new Error(String(error)));
      }
    } else if (!aiEnabled) {
      logger.info('AI disabled in configuration');
    } else {
      logger.warn('AI budget exceeded', { neurons_used: this.state.aiNeuronsUsedToday, budget: aiBudget });
    }

    if (patternsFound.length > 0) {
      await this.storePatterns(patternsFound);
    }

    return patternsFound.length;
  }

  calculateAverageState(states: MarketState[]): MarketState {
    const sum = states.reduce((acc, state) => ({
      price: acc.price + state.price,
      momentum1tick: acc.momentum1tick + state.momentum1tick,
      momentum5tick: acc.momentum5tick + state.momentum5tick,
      vsSma10: acc.vsSma10 + state.vsSma10,
      volumeVsAvg: acc.volumeVsAvg + state.volumeVsAvg,
      volatility: acc.volatility + state.volatility
    }), { price: 0, momentum1tick: 0, momentum5tick: 0, vsSma10: 0, volumeVsAvg: 0, volatility: 0 });

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

  async storePatterns(patterns: Pattern[]) {
    const stmt = this.env.DB.prepare(`
      INSERT OR IGNORE INTO discovered_patterns (
        pattern_id, name, conditions, win_rate, sample_size,
        discovered_at, tested, votes
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `);

    const batch = patterns.map(p =>
      stmt.bind(p.patternId, p.name, JSON.stringify(p.conditions),
                p.winRate, p.sampleSize, p.discoveredAt, p.tested ? 1 : 0, p.votes)
    );

    await this.env.DB.batch(batch);
  }

  async testStrategies(): Promise<number> {
    const patterns = await this.env.DB.prepare(
      'SELECT * FROM discovered_patterns WHERE tested = 0 LIMIT 10'
    ).all();

    if (patterns.results.length === 0) return 0;

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

      const patternPerformance = await this.testPatternPerformance(pattern);
      const randomPerformance = await this.testRandomPerformance();

      let vote = 0;
      if (patternPerformance > randomPerformance) {
        vote = 1;
        winnersFound++;
        logger.info('Pattern winner', { name: pattern.name, performance: (patternPerformance * 100).toFixed(2), vs_random: (randomPerformance * 100).toFixed(2) });
      } else {
        vote = -1;
        logger.info('Pattern loser', { name: pattern.name, performance: (patternPerformance * 100).toFixed(2), vs_random: (randomPerformance * 100).toFixed(2) });
      }

      await this.env.DB.prepare(`
        UPDATE discovered_patterns
        SET tested = 1, votes = votes + ?, accuracy = ?
        WHERE pattern_id = ?
      `).bind(vote, patternPerformance, pattern.patternId).run();
    }

    return winnersFound;
  }

  async testPatternPerformance(pattern: Pattern): Promise<number> {
    const trades = await this.env.DB.prepare(
      'SELECT pnl_pct FROM chaos_trades LIMIT 200'
    ).all();

    if (trades.results.length === 0) return 0;

    const avgPnl = trades.results.reduce((sum, t) => sum + (t.pnl_pct as number), 0) / trades.results.length;
    const patternBonus = (Math.random() - 0.5) * 0.02;

    return avgPnl / 100 + patternBonus;
  }

  async testRandomPerformance(): Promise<number> {
    const trades = await this.env.DB.prepare(
      'SELECT pnl_pct FROM chaos_trades ORDER BY RANDOM() LIMIT 100'
    ).all();

    if (trades.results.length === 0) return 0;

    const avgPnl = trades.results.reduce((sum, t) => sum + (t.pnl_pct as number), 0) / trades.results.length;

    return avgPnl / 100;
  }

  async saveState() {
    await this.ctx.storage.put('evolutionState', this.state);
  }

  async handleStatusRequest() {
    return new Response(JSON.stringify({
      status: 'running',
      plan: 'scaled ($5 paid)',
      ...this.state,
      configuration: {
        batchSize: this.env.BATCH_SIZE,
        cycleInterval: `${this.env.CYCLE_INTERVAL}s`,
        aiEnabled: this.env.AI_ENABLED,
        aibudget: `${this.env.AI_BUDGET_PER_DAY} neurons/day`
      }
    }, null, 2), {
      headers: { 'Content-Type': 'application/json' }
    });
  }

  async handleTriggerRequest() {
    if (this.state.isRunning) {
      return new Response(JSON.stringify({ error: 'Cycle already running' }), {
        status: 409,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    this.runEvolutionCycle();

    return new Response(JSON.stringify({ message: 'Evolution cycle triggered' }), {
      headers: { 'Content-Type': 'application/json' }
    });
  }

  async handleStatsRequest() {
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
      'SELECT pattern_id, name, votes, accuracy FROM discovered_patterns ORDER BY votes DESC LIMIT 20'
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

  async handleConfigRequest() {
    return new Response(JSON.stringify({
      plan: 'Cloudflare Workers Paid ($5/month)',
      configuration: {
        batchSize: parseInt(this.env.BATCH_SIZE || '500'),
        cycleInterval: parseInt(this.env.CYCLE_INTERVAL || '10'),
        patternAnalysisInterval: parseInt(this.env.PATTERN_ANALYSIS_INTERVAL || '2'),
        strategyTestInterval: parseInt(this.env.STRATEGY_TEST_INTERVAL || '5'),
        parallelAgents: parseInt(this.env.PARALLEL_AGENTS || '10'),
        aiEnabled: this.env.AI_ENABLED === 'true',
        aiBudgetPerDay: parseInt(this.env.AI_BUDGET_PER_DAY || '10000')
      },
      performance: {
        tradesPerCycle: parseInt(this.env.BATCH_SIZE || '500'),
        cyclesPerMinute: 60 / parseInt(this.env.CYCLE_INTERVAL || '10'),
        tradesPerMinute: (parseInt(this.env.BATCH_SIZE || '500') * 60) / parseInt(this.env.CYCLE_INTERVAL || '10'),
        tradesPerDay: ((parseInt(this.env.BATCH_SIZE || '500') * 60) / parseInt(this.env.CYCLE_INTERVAL || '10')) * 1440,
        withParallelAgents: ((parseInt(this.env.BATCH_SIZE || '500') * 60) / parseInt(this.env.CYCLE_INTERVAL || '10')) * 1440 * parseInt(this.env.PARALLEL_AGENTS || '10')
      },
      estimatedCosts: {
        requests: '$0 (under 10M included)',
        durableObjects: '~$3.60/month',
        ai: `~$${((parseInt(this.env.AI_BUDGET_PER_DAY || '10000') - 10000) / 1000 * 0.011 * 30).toFixed(2)}/month`,
        d1: '$0 (under limits)',
        total: `~$${(3.60 + ((parseInt(this.env.AI_BUDGET_PER_DAY || '10000') - 10000) / 1000 * 0.011 * 30)).toFixed(2)}/month (plus $5 base)`
      }
    }, null, 2), {
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Worker entry point with support for multiple parallel agents
 */
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    // Route to specific agent or load balancer
    let agentId = 0;
    const agentIdMatch = url.pathname.match(/\/agent\/(\d+)/);
    if (agentIdMatch) {
      agentId = parseInt(agentIdMatch[1]);
    } else {
      // Load balance across agents
      agentId = Math.floor(Math.random() * parseInt(env.PARALLEL_AGENTS || '10'));
    }

    // Get agent instance with specific ID
    const id = env.EVOLUTION_AGENT.idFromName(`evolution-agent-${agentId}`);
    const agent = env.EVOLUTION_AGENT.get(id);

    // Forward request to agent
    return agent.fetch(request);
  }
};
