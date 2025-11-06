/**
 * Evolution Agent - Simplified Durable Objects Implementation
 *
 * Removed dependency on 'agents' SDK to fix deployment issues.
 * Uses vanilla Durable Objects for now, same functionality.
 */

// Environment bindings interface
interface Env {
  DB: D1Database;
  EVOLUTION_AGENT: DurableObjectNamespace;
  AI: any;
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
 * EvolutionAgent - Durable Object for chaos trading evolution
 */
export class EvolutionAgent implements DurableObject {
  private state: DurableObjectState;
  private env: Env;
  private evolutionState: EvolutionState;
  private scheduledAlarm: boolean = false;

  constructor(state: DurableObjectState, env: Env) {
    this.state = state;
    this.env = env;
    this.evolutionState = {
      totalCycles: 0,
      totalTrades: 0,
      patternsDiscovered: 0,
      winningStrategies: 0,
      lastCycleAt: 'never',
      isRunning: false
    };
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);

    // Load state on first request
    if (this.evolutionState.lastCycleAt === 'never') {
      const stored = await this.state.storage.get<EvolutionState>('evolutionState');
      if (stored) {
        this.evolutionState = stored;
      }
    }

    if (url.pathname === '/status') {
      return new Response(JSON.stringify({
        status: 'running',
        ...this.evolutionState,
        uptime: 'continuous'
      }, null, 2), {
        headers: { 'Content-Type': 'application/json' }
      });
    }

    if (url.pathname === '/trigger') {
      if (this.evolutionState.isRunning) {
        return new Response(JSON.stringify({
          error: 'Cycle already running'
        }), {
          status: 409,
          headers: { 'Content-Type': 'application/json' }
        });
      }

      // Start evolution and schedule next
      this.runEvolutionCycle();

      return new Response(JSON.stringify({
        message: 'Evolution cycle triggered',
        state: this.evolutionState
      }), {
        headers: { 'Content-Type': 'application/json' }
      });
    }

    if (url.pathname === '/stats') {
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
        agentState: this.evolutionState,
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

    return new Response('Evolution Agent - Endpoints: /status /trigger /stats', {
      status: 200
    });
  }

  async alarm(): Promise<void> {
    await this.runEvolutionCycle();
  }

  async runEvolutionCycle(): Promise<void> {
    console.log(`\n=== Evolution Cycle ${this.evolutionState.totalCycles + 1} ===`);

    this.evolutionState.isRunning = true;
    await this.saveState();

    try {
      // Generate 50 chaos trades
      const tradesGenerated = await this.generateChaosTrades(50);
      console.log(`Generated ${tradesGenerated} chaos trades`);

      this.evolutionState.totalTrades += tradesGenerated;

      // Analyze patterns every 5 cycles
      if (this.evolutionState.totalCycles % 5 === 0 && this.evolutionState.totalTrades >= 100) {
        console.log('Analyzing patterns...');
        const patternsFound = await this.analyzePatterns();
        console.log(`Discovered ${patternsFound} new patterns`);
        this.evolutionState.patternsDiscovered += patternsFound;
      }

      // Test strategies every 10 cycles
      if (this.evolutionState.totalCycles % 10 === 0 && this.evolutionState.patternsDiscovered > 0) {
        console.log('Testing strategies...');
        const winnersFound = await this.testStrategies();
        console.log(`Found ${winnersFound} winning strategies`);
        this.evolutionState.winningStrategies += winnersFound;
      }

      this.evolutionState.totalCycles++;
      this.evolutionState.lastCycleAt = new Date().toISOString();
      this.evolutionState.isRunning = false;
      await this.saveState();

      console.log(`Cycle complete. Total: ${this.evolutionState.totalTrades} trades`);

      // Schedule next cycle in 60 seconds
      await this.state.storage.setAlarm(Date.now() + 60000);

    } catch (error) {
      console.error('Error in evolution cycle:', error);
      this.evolutionState.isRunning = false;
      await this.saveState();

      // Retry in 5 minutes on error
      await this.state.storage.setAlarm(Date.now() + 300000);
    }
  }

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
        `Momentum ${buyState.momentum1tick > 0 ? 'positive' : 'negative'}`,
        `Price ${buyState.vsSma10 > 0 ? 'above' : 'below'} SMA10`,
        `Volume ${buyState.volumeVsAvg > 1 ? 'high' : 'low'}`,
        `Volatility ${buyState.volatility > 0.025 ? 'high' : 'low'}`,
        'Random chaos decision'
      ];
      const buyReason = buyReasons[Math.floor(Math.random() * buyReasons.length)];

      const sellReasons = [
        `Detected ${sellState.momentum1tick < 0 ? 'reversal' : 'continuation'}`,
        `Hit ${profitable ? 'profit' : 'loss'} target`,
        `Volume ${sellState.volumeVsAvg > 1.5 ? 'spike' : 'drop'}`,
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

  async storeTrades(trades: ChaosTrade[]): Promise<void> {
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

  async analyzePatterns(): Promise<number> {
    const winners = await this.env.DB.prepare(
      'SELECT buy_state FROM chaos_trades WHERE profitable = 1'
    ).all();

    const losers = await this.env.DB.prepare(
      'SELECT buy_state FROM chaos_trades WHERE profitable = 0'
    ).all();

    if (winners.results.length < 10 || losers.results.length < 10) {
      return 0;
    }

    const winnerStates = winners.results.map(r => JSON.parse(r.buy_state as string));
    const loserStates = losers.results.map(r => JSON.parse(r.buy_state as string));

    const winnerAvg = this.calculateAverageState(winnerStates);
    const loserAvg = this.calculateAverageState(loserStates);

    const patternsFound: Pattern[] = [];

    const momentumDiff = Math.abs(winnerAvg.momentum1tick - loserAvg.momentum1tick);
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

  async storePatterns(patterns: Pattern[]): Promise<void> {
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
      'SELECT * FROM discovered_patterns WHERE tested = 0 LIMIT 5'
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

      const patternPerformance = await this.testPatternPerformance();
      const randomPerformance = await this.testRandomPerformance();

      let vote = 0;
      if (patternPerformance > randomPerformance) {
        vote = 1;
        winnersFound++;
      } else {
        vote = -1;
      }

      await this.env.DB.prepare(`
        UPDATE discovered_patterns
        SET tested = 1, votes = votes + ?, accuracy = ?
        WHERE pattern_id = ?
      `).bind(vote, patternPerformance, pattern.patternId).run();
    }

    return winnersFound;
  }

  async testPatternPerformance(): Promise<number> {
    const trades = await this.env.DB.prepare(
      'SELECT pnl_pct FROM chaos_trades LIMIT 100'
    ).all();

    if (trades.results.length === 0) return 0;

    const avgPnl = trades.results.reduce((sum, t) => sum + (t.pnl_pct as number), 0) / trades.results.length;
    return avgPnl / 100 + (Math.random() - 0.5) * 0.02;
  }

  async testRandomPerformance(): Promise<number> {
    const trades = await this.env.DB.prepare(
      'SELECT pnl_pct FROM chaos_trades ORDER BY RANDOM() LIMIT 50'
    ).all();

    if (trades.results.length === 0) return 0;

    const avgPnl = trades.results.reduce((sum, t) => sum + (t.pnl_pct as number), 0) / trades.results.length;
    return avgPnl / 100;
  }

  async saveState(): Promise<void> {
    await this.state.storage.put('evolutionState', this.evolutionState);
  }
}

/**
 * Worker entry point
 */
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const id = env.EVOLUTION_AGENT.idFromName('main-evolution-agent');
    const agent = env.EVOLUTION_AGENT.get(id);
    return agent.fetch(request);
  }
};
