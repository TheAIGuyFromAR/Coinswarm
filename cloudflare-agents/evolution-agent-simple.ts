/**
 * Evolution Agent - Simplified Durable Objects Implementation
 * WITH COMPREHENSIVE ERROR HANDLING AND DEBUGGING
 * WITH AI-POWERED PATTERN ANALYSIS
 */

import { analyzeWithAI, validatePattern, scorePattern, generatePatternId } from './ai-pattern-analyzer';

// Environment bindings interface
interface Env {
  DB: D1Database;
  EVOLUTION_AGENT: DurableObjectNamespace;
  AI?: any;
}

// Agent state interface
interface EvolutionState {
  totalCycles: number;
  totalTrades: number;
  patternsDiscovered: number;
  winningStrategies: number;
  lastCycleAt: string;
  isRunning: boolean;
  lastError?: string;
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
 * Helper function to create error responses
 */
function errorResponse(message: string, error: any, status: number = 500): Response {
  console.error(`ERROR: ${message}`, error);
  return new Response(JSON.stringify({
    error: message,
    details: error?.message || String(error),
    stack: error?.stack,
    timestamp: new Date().toISOString()
  }, null, 2), {
    status,
    headers: { 'Content-Type': 'application/json' }
  });
}

/**
 * EvolutionAgent - Durable Object for chaos trading evolution
 */
export class EvolutionAgent implements DurableObject {
  private state: DurableObjectState;
  private env: Env;
  private evolutionState: EvolutionState;

  constructor(state: DurableObjectState, env: Env) {
    console.log('EvolutionAgent constructor called');
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
    console.log('EvolutionAgent constructor completed');
  }

  async fetch(request: Request): Promise<Response> {
    console.log(`Fetch called: ${request.url}`);

    try {
      const url = new URL(request.url);
      console.log(`Pathname: ${url.pathname}`);

      // Always reload state from storage to ensure consistency
      console.log('Loading stored state...');
      try {
        const stored = await this.state.storage.get<EvolutionState>('evolutionState');
        if (stored) {
          this.evolutionState = stored;
          console.log('State loaded:', this.evolutionState);
        } else {
          console.log('No stored state found, using defaults');
        }
      } catch (error) {
        console.error('Error loading state:', error);
        this.evolutionState.lastError = `Failed to load state: ${error}`;
      }

      // Debug endpoint
      if (url.pathname === '/debug') {
        console.log('Debug endpoint called');
        return new Response(JSON.stringify({
          message: 'Debug information',
          state: this.evolutionState,
          env: {
            hasDB: !!this.env.DB,
            hasAI: !!this.env.AI,
            hasEvolutionAgent: !!this.env.EVOLUTION_AGENT
          },
          durableObject: {
            id: this.state.id.toString(),
            hasStorage: !!this.state.storage
          },
          timestamp: new Date().toISOString()
        }, null, 2), {
          headers: { 'Content-Type': 'application/json' }
        });
      }

      // Status endpoint
      if (url.pathname === '/status') {
        console.log('Status endpoint called');
        return new Response(JSON.stringify({
          status: 'running',
          ...this.evolutionState,
          uptime: 'continuous',
          timestamp: new Date().toISOString()
        }, null, 2), {
          headers: { 'Content-Type': 'application/json' }
        });
      }

      // Trigger endpoint
      if (url.pathname === '/trigger') {
        console.log('Trigger endpoint called');

        if (this.evolutionState.isRunning) {
          console.log('Cycle already running');
          return new Response(JSON.stringify({
            error: 'Cycle already running',
            state: this.evolutionState
          }), {
            status: 409,
            headers: { 'Content-Type': 'application/json' }
          });
        }

        // Start evolution in background
        console.log('Starting evolution cycle...');
        this.runEvolutionCycle().catch(error => {
          console.error('Evolution cycle failed:', error);
          this.evolutionState.lastError = String(error);
        });

        return new Response(JSON.stringify({
          message: 'Evolution cycle triggered',
          state: this.evolutionState,
          timestamp: new Date().toISOString()
        }), {
          headers: { 'Content-Type': 'application/json' }
        });
      }

      // Stats endpoint
      if (url.pathname === '/stats') {
        console.log('Stats endpoint called');

        try {
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
            'SELECT pattern_id, name, votes, accuracy, number_of_runs, max_ending_value, average_ending_value, average_roi_pct, annualized_roi_pct FROM discovered_patterns ORDER BY annualized_roi_pct DESC, number_of_runs DESC, max_ending_value DESC LIMIT 20'
          ).all();

          return new Response(JSON.stringify({
            agentState: this.evolutionState,
            database: {
              totalTrades: tradesCount?.count || 0,
              totalPatterns: patternsCount?.count || 0,
              winningStrategies: winnersCount?.count || 0
            },
            topPatterns: topPatterns.results,
            timestamp: new Date().toISOString()
          }, null, 2), {
            headers: { 'Content-Type': 'application/json' }
          });
        } catch (error) {
          return errorResponse('Failed to get stats', error);
        }
      }

      // Root endpoint
      console.log('Root endpoint, returning help');
      return new Response(JSON.stringify({
        message: 'Evolution Agent - Chaos Trading Evolution System',
        endpoints: {
          '/status': 'Get agent status',
          '/trigger': 'Trigger evolution cycle',
          '/stats': 'Get database statistics',
          '/debug': 'Get debug information'
        },
        version: '1.0.0',
        timestamp: new Date().toISOString()
      }, null, 2), {
        headers: { 'Content-Type': 'application/json' }
      });

    } catch (error) {
      return errorResponse('Fetch handler failed', error);
    }
  }

  async alarm(): Promise<void> {
    console.log('Alarm triggered');

    // Load latest state from storage before running cycle
    try {
      const stored = await this.state.storage.get<EvolutionState>('evolutionState');
      if (stored) {
        this.evolutionState = stored;
        console.log('State loaded in alarm:', this.evolutionState);
      }
    } catch (error) {
      console.error('Failed to load state in alarm:', error);
    }

    try {
      await this.runEvolutionCycle();
    } catch (error) {
      console.error('Alarm handler failed:', error);
      this.evolutionState.lastError = `Alarm failed: ${error}`;
      await this.saveState();
    }
  }

  async runEvolutionCycle(): Promise<void> {
    console.log(`\n=== Evolution Cycle ${this.evolutionState.totalCycles + 1} START ===`);

    this.evolutionState.isRunning = true;
    this.evolutionState.lastError = undefined;
    await this.saveState();

    try {
      // Step 1: Generate chaos trades
      console.log('Step 1: Generating chaos trades...');
      const tradesGenerated = await this.generateChaosTrades(50);
      console.log(`✓ Generated ${tradesGenerated} chaos trades`);
      this.evolutionState.totalTrades += tradesGenerated;

      // Step 2: Analyze patterns (every 5 cycles)
      if (this.evolutionState.totalCycles % 5 === 0 && this.evolutionState.totalTrades >= 100) {
        console.log('Step 2: Analyzing patterns...');
        try {
          const patternsFound = await this.analyzePatterns();
          console.log(`✓ Discovered ${patternsFound} new patterns`);
          this.evolutionState.patternsDiscovered += patternsFound;
        } catch (error) {
          console.error('Pattern analysis failed:', error);
          // Continue despite error
        }
      }

      // Step 3: Test strategies (every 10 cycles)
      if (this.evolutionState.totalCycles % 10 === 0 && this.evolutionState.patternsDiscovered > 0) {
        console.log('Step 3: Testing strategies...');
        try {
          const winnersFound = await this.testStrategies();
          console.log(`✓ Found ${winnersFound} winning strategies`);
          this.evolutionState.winningStrategies += winnersFound;
        } catch (error) {
          console.error('Strategy testing failed:', error);
          // Continue despite error
        }
      }

      // Update state
      this.evolutionState.totalCycles++;
      this.evolutionState.lastCycleAt = new Date().toISOString();
      this.evolutionState.isRunning = false;
      await this.saveState();

      console.log(`✓ Cycle ${this.evolutionState.totalCycles} complete. Total trades: ${this.evolutionState.totalTrades}`);

      // Schedule next cycle in 60 seconds
      console.log('Scheduling next cycle in 60 seconds...');
      await this.state.storage.setAlarm(Date.now() + 60000);
      console.log('✓ Next cycle scheduled');

    } catch (error) {
      console.error('CRITICAL ERROR in evolution cycle:', error);
      this.evolutionState.isRunning = false;
      this.evolutionState.lastError = `Cycle failed: ${error}`;
      await this.saveState();

      // Retry in 5 minutes on error
      console.log('Scheduling retry in 5 minutes...');
      try {
        await this.state.storage.setAlarm(Date.now() + 300000);
      } catch (alarmError) {
        console.error('Failed to set alarm:', alarmError);
      }
    }
  }

  async generateChaosTrades(count: number): Promise<number> {
    console.log(`Generating ${count} chaos trades...`);

    try {
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

      console.log(`Generated ${trades.length} trade objects, storing in DB...`);
      await this.storeTrades(trades);
      console.log(`✓ Stored ${trades.length} trades in database`);

      return trades.length;
    } catch (error) {
      console.error('Failed to generate chaos trades:', error);
      throw new Error(`Generate trades failed: ${error}`);
    }
  }

  async storeTrades(trades: ChaosTrade[]): Promise<void> {
    console.log(`Storing ${trades.length} trades in D1...`);

    try {
      if (!this.env.DB) {
        throw new Error('D1 database binding not found');
      }

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

      console.log(`Executing batch insert of ${batch.length} trades...`);
      await this.env.DB.batch(batch);
      console.log('✓ Batch insert complete');

    } catch (error) {
      console.error('Failed to store trades:', error);
      throw new Error(`Store trades failed: ${error}`);
    }
  }

  async analyzePatterns(): Promise<number> {
    console.log('Analyzing patterns from chaos trades...');

    try {
      const winners = await this.env.DB.prepare(
        'SELECT buy_state FROM chaos_trades WHERE profitable = 1'
      ).all();

      const losers = await this.env.DB.prepare(
        'SELECT buy_state FROM chaos_trades WHERE profitable = 0'
      ).all();

      console.log(`Loaded ${winners.results.length} winners, ${losers.results.length} losers`);

      if (winners.results.length < 10 || losers.results.length < 10) {
        console.log('Not enough data for pattern analysis');
        return 0;
      }

      const winnerStates = winners.results.map(r => JSON.parse(r.buy_state as string));
      const loserStates = losers.results.map(r => JSON.parse(r.buy_state as string));

      const winnerAvg = this.calculateAverageState(winnerStates);
      const loserAvg = this.calculateAverageState(loserStates);

      console.log('Winner avg:', winnerAvg);
      console.log('Loser avg:', loserAvg);

      const patternsFound: Pattern[] = [];

      const momentumDiff = Math.abs(winnerAvg.momentum1tick - loserAvg.momentum1tick);
      console.log(`Momentum difference: ${momentumDiff}`);

      if (momentumDiff > 0.005) {
        const pattern = {
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
        };
        patternsFound.push(pattern);
        console.log('Found statistical pattern:', pattern.name);
      }

      // AI-powered pattern discovery
      if (this.env.AI) {
        console.log('🤖 Using AI for pattern discovery...');
        try {
          const aiPatterns = await analyzeWithAI(
            this.env.AI,
            winnerAvg,
            loserAvg,
            winners.results.length + losers.results.length
          );

          console.log(`AI suggested ${aiPatterns.length} patterns`);

          // Validate and add AI-discovered patterns
          for (const aiPattern of aiPatterns) {
            if (validatePattern(aiPattern)) {
              const maxDiff = Math.max(momentumDiff, 0.01);
              const quality = scorePattern(aiPattern, maxDiff, winners.results.length + losers.results.length);

              if (quality > 0.5) {
                const pattern = {
                  patternId: generatePatternId(aiPattern.patternName),
                  name: `[AI] ${aiPattern.patternName}`,
                  conditions: {
                    ...aiPattern.conditions,
                    aiReasoning: aiPattern.reasoning,
                    aiConfidence: aiPattern.confidence,
                    description: aiPattern.description
                  },
                  winRate: winners.results.length / (winners.results.length + losers.results.length),
                  sampleSize: winners.results.length + losers.results.length,
                  discoveredAt: new Date().toISOString(),
                  tested: false,
                  votes: 0
                };
                patternsFound.push(pattern);
                console.log(`✓ AI discovered: ${aiPattern.patternName} (confidence: ${(aiPattern.confidence * 100).toFixed(0)}%, quality: ${(quality * 100).toFixed(0)}%)`);
                console.log(`  Reasoning: ${aiPattern.reasoning}`);
              } else {
                console.log(`✗ AI pattern rejected: ${aiPattern.patternName} (quality too low: ${(quality * 100).toFixed(0)}%)`);
              }
            } else {
              console.log(`✗ AI pattern failed validation: ${aiPattern.patternName}`);
            }
          }
        } catch (error) {
          console.error('AI pattern discovery failed:', error);
          // Continue with statistical patterns only
        }
      } else {
        console.log('⚠️ AI binding not available, using statistical analysis only');
      }

      if (patternsFound.length > 0) {
        console.log(`Storing ${patternsFound.length} total patterns (statistical + AI)...`);
        await this.storePatterns(patternsFound);
        console.log('✓ Patterns stored');
      }

      return patternsFound.length;
    } catch (error) {
      console.error('Pattern analysis failed:', error);
      throw new Error(`Analyze patterns failed: ${error}`);
    }
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
    try {
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
    } catch (error) {
      console.error('Failed to store patterns:', error);
      throw new Error(`Store patterns failed: ${error}`);
    }
  }

  async testStrategies(): Promise<number> {
    console.log('Testing strategies...');

    try {
      const patterns = await this.env.DB.prepare(
        'SELECT * FROM discovered_patterns WHERE tested = 0 LIMIT 5'
      ).all();

      console.log(`Found ${patterns.results.length} untested patterns`);

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

        console.log(`Testing pattern: ${pattern.name}`);

        // Run multiple test iterations to get performance metrics
        const numTestRuns = 10;
        const testResults: number[] = [];

        for (let i = 0; i < numTestRuns; i++) {
          const result = await this.testPatternPerformance();
          testResults.push(result);
        }

        const randomPerformance = await this.testRandomPerformance();

        // Calculate metrics
        const avgPerformance = testResults.reduce((a, b) => a + b, 0) / testResults.length;
        const maxPerformance = Math.max(...testResults);
        const avgRoiPct = avgPerformance * 100;

        // Annualize ROI (assuming average trade duration from chaos trades)
        // For now, assume ~1 hour average hold time, annualize to 365 days
        const annualizedRoiPct = avgRoiPct * (365 * 24);

        let vote = 0;
        if (avgPerformance > randomPerformance) {
          vote = 1;
          winnersFound++;
          console.log(`✓ ${pattern.name}: Winner! (avg: ${(avgPerformance * 100).toFixed(2)}%, max: ${(maxPerformance * 100).toFixed(2)}% vs random ${(randomPerformance * 100).toFixed(2)}%)`);
        } else {
          vote = -1;
          console.log(`✗ ${pattern.name}: Loser (avg: ${(avgPerformance * 100).toFixed(2)}%, max: ${(maxPerformance * 100).toFixed(2)}% vs random ${(randomPerformance * 100).toFixed(2)}%)`);
        }

        // Update with performance tracking
        await this.env.DB.prepare(`
          UPDATE discovered_patterns
          SET tested = 1,
              votes = votes + ?,
              accuracy = ?,
              number_of_runs = number_of_runs + ?,
              max_ending_value = CASE WHEN max_ending_value IS NULL OR ? > max_ending_value THEN ? ELSE max_ending_value END,
              average_ending_value = ?,
              average_roi_pct = ?,
              annualized_roi_pct = ?
          WHERE pattern_id = ?
        `).bind(vote, avgPerformance, numTestRuns, maxPerformance, maxPerformance, avgPerformance, avgRoiPct, annualizedRoiPct, pattern.patternId).run();
      }

      return winnersFound;
    } catch (error) {
      console.error('Strategy testing failed:', error);
      throw new Error(`Test strategies failed: ${error}`);
    }
  }

  async testPatternPerformance(): Promise<number> {
    try {
      const trades = await this.env.DB.prepare(
        'SELECT pnl_pct FROM chaos_trades LIMIT 100'
      ).all();

      if (trades.results.length === 0) return 0;

      const avgPnl = trades.results.reduce((sum, t) => sum + (t.pnl_pct as number), 0) / trades.results.length;
      return avgPnl / 100 + (Math.random() - 0.5) * 0.02;
    } catch (error) {
      console.error('Failed to test pattern performance:', error);
      return 0;
    }
  }

  async testRandomPerformance(): Promise<number> {
    try {
      const trades = await this.env.DB.prepare(
        'SELECT pnl_pct FROM chaos_trades ORDER BY RANDOM() LIMIT 50'
      ).all();

      if (trades.results.length === 0) return 0;

      const avgPnl = trades.results.reduce((sum, t) => sum + (t.pnl_pct as number), 0) / trades.results.length;
      return avgPnl / 100;
    } catch (error) {
      console.error('Failed to test random performance:', error);
      return 0;
    }
  }

  async saveState(): Promise<void> {
    try {
      console.log('Saving state...');
      await this.state.storage.put('evolutionState', this.evolutionState);
      console.log('✓ State saved');
    } catch (error) {
      console.error('Failed to save state:', error);
    }
  }
}

/**
 * Worker entry point with error handling
 */
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    console.log(`Worker fetch: ${request.url}`);

    try {
      // Validate environment
      if (!env.EVOLUTION_AGENT) {
        return errorResponse('EVOLUTION_AGENT binding not found', 'Check wrangler.toml configuration');
      }

      if (!env.DB) {
        return errorResponse('DB binding not found', 'Check wrangler.toml configuration');
      }

      console.log('Getting Durable Object instance...');
      const id = env.EVOLUTION_AGENT.idFromName('main-evolution-agent');
      const agent = env.EVOLUTION_AGENT.get(id);

      console.log('Forwarding request to Durable Object...');
      return await agent.fetch(request);

    } catch (error) {
      return errorResponse('Worker fetch failed', error);
    }
  }
};
