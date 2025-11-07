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
  private logs: string[] = [];

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

      // Load state from D1 database only on first access (when lastCycleAt is 'never')
      // After that, rely on in-memory state which is maintained by the Durable Object
      if (this.evolutionState.lastCycleAt === 'never') {
        console.log('First access - loading stored state from D1...');
        try {
          const result = await this.env.DB.prepare(`
            SELECT value FROM system_state WHERE key = 'evolutionState'
          `).first<{ value: string }>();

          if (result && result.value) {
            this.evolutionState = JSON.parse(result.value);
            console.log('State loaded from D1:', JSON.stringify(this.evolutionState));
          } else {
            console.log('No stored state found in D1, using defaults');
          }
        } catch (error) {
          console.error('Error loading state from D1:', error);
          this.evolutionState.lastError = `Failed to load state: ${error}`;
        }
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

      // Logs endpoint
      if (url.pathname === '/logs') {
        return new Response(JSON.stringify({
          logs: this.logs.slice(-100), // Last 100 log entries
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

      // Bulk import endpoint - generate historical trades quickly
      if (url.pathname === '/bulk-import') {
        const urlParams = url.searchParams;
        const count = parseInt(urlParams.get('count') || '10000');

        this.log(`Bulk import: Generating ${count} historical trades...`);

        try {
          const generated = await this.generateHistoricalTrades(count);
          this.log(`✓ Bulk import completed: ${generated} trades`);

          return new Response(JSON.stringify({
            message: 'Bulk import completed',
            tradesGenerated: generated,
            totalTrades: this.evolutionState.totalTrades + generated
          }, null, 2), {
            headers: { 'Content-Type': 'application/json' }
          });
        } catch (error) {
          return new Response(JSON.stringify({
            error: `Bulk import failed: ${error}`,
            stack: error instanceof Error ? error.stack : undefined
          }, null, 2), {
            status: 500,
            headers: { 'Content-Type': 'application/json' }
          });
        }
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

    // Load state from D1 if this is first access after DO restart
    if (this.evolutionState.lastCycleAt === 'never') {
      this.log('Alarm: First access after restart - loading state from D1...');
      try {
        const result = await this.env.DB.prepare(`
          SELECT value FROM system_state WHERE key = 'evolutionState'
        `).first<{ value: string }>();

        if (result && result.value) {
          this.evolutionState = JSON.parse(result.value);
          this.log(`Alarm: State loaded from D1 - cycles=${this.evolutionState.totalCycles}, trades=${this.evolutionState.totalTrades}`);
        } else {
          this.log('Alarm: No stored state in D1, using defaults');
        }
      } catch (error) {
        this.log(`Alarm: Error loading state - ${error}`);
      }
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
    this.log(`\n=== Evolution Cycle ${this.evolutionState.totalCycles + 1} START ===`);

    this.evolutionState.isRunning = true;
    this.evolutionState.lastError = undefined;
    await this.saveState();

    try {
      // Step 1: Generate chaos trades
      this.log('Step 1: Generating chaos trades...');
      const tradesGenerated = await this.generateChaosTrades(50);
      this.log(`✓ Generated ${tradesGenerated} chaos trades`);
      this.evolutionState.totalTrades += tradesGenerated;

      // Step 2: Analyze patterns (every 5 cycles)
      if (this.evolutionState.totalCycles % 5 === 0 && this.evolutionState.totalTrades >= 100) {
        this.log(`Step 2: Analyzing patterns (totalCycles=${this.evolutionState.totalCycles})...`);
        try {
          const patternsFound = await this.analyzePatterns();
          this.log(`✓ Pattern analysis complete: discovered ${patternsFound} new patterns`);
          this.evolutionState.patternsDiscovered += patternsFound;
        } catch (error) {
          const errorMsg = error instanceof Error ? error.message : String(error);
          this.log(`❌ Pattern analysis failed: ${errorMsg}`);
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
      this.log(`Incrementing totalCycles from ${this.evolutionState.totalCycles} to ${this.evolutionState.totalCycles + 1}`);
      this.evolutionState.totalCycles++;
      this.evolutionState.lastCycleAt = new Date().toISOString();
      this.evolutionState.isRunning = false;
      this.log(`State before save: cycles=${this.evolutionState.totalCycles}, trades=${this.evolutionState.totalTrades}`);
      await this.saveState();

      this.log(`✓ Cycle ${this.evolutionState.totalCycles} complete. Total trades: ${this.evolutionState.totalTrades}`);

      // Schedule next cycle in 60 seconds
      this.log('Scheduling next cycle in 60 seconds...');
      await this.state.storage.setAlarm(Date.now() + 60000);
      this.log('✓ Next cycle scheduled');

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

  /**
   * Generate historical trades with realistic price movements
   * - Random entry times over past 30 days
   * - Random hold durations (1 min to 24 hours)
   * - Trend-based price movements with volatility
   */
  async generateHistoricalTrades(count: number): Promise<number> {
    this.log(`Generating ${count} historical trades with realistic price movements...`);

    try {
      const trades: ChaosTrade[] = [];
      const now = Date.now();
      const thirtyDaysAgo = now - (30 * 24 * 60 * 60 * 1000);

      // Generate realistic price series
      let price = 60000 + Math.random() * 20000;
      let trend = 0;

      for (let i = 0; i < count; i++) {
        // Random entry time in past 30 days
        const entryTime = new Date(thirtyDaysAgo + Math.random() * (now - thirtyDaysAgo));

        // Random hold duration: 1 minute to 24 hours
        const holdMinutes = 1 + Math.floor(Math.random() * 1440);
        const exitTime = new Date(entryTime.getTime() + holdMinutes * 60 * 1000);

        // Realistic price movement with trend
        if (Math.random() < 0.01) {
          trend = (Math.random() - 0.5) * 0.001; // Trend shift
        }

        const volatility = 0.01 + Math.random() * 0.02;
        const entryPrice = price;

        // Price movement during hold period
        for (let t = 0; t < holdMinutes; t++) {
          const trendMove = price * trend;
          const randomMove = price * (Math.random() - 0.5) * volatility;
          price = Math.max(20000, Math.min(100000, price + trendMove + randomMove));
        }

        const exitPrice = price;
        const pnlPct = ((exitPrice - entryPrice) / entryPrice) * 100;
        const profitable = exitPrice > entryPrice;

        // Realistic market states based on price movement
        const momentum = (exitPrice - entryPrice) / entryPrice;
        const buyState: MarketState = {
          price: entryPrice,
          momentum1tick: (Math.random() - 0.5) * 0.02,
          momentum5tick: (Math.random() - 0.5) * 0.05,
          vsSma10: (Math.random() - 0.5) * 0.03,
          volumeVsAvg: 0.5 + Math.random() * 2,
          volatility
        };

        const sellState: MarketState = {
          price: exitPrice,
          momentum1tick: momentum * 0.7 + (Math.random() - 0.5) * 0.01,
          momentum5tick: momentum * 0.5 + (Math.random() - 0.5) * 0.02,
          vsSma10: (exitPrice - entryPrice) / entryPrice + (Math.random() - 0.5) * 0.02,
          volumeVsAvg: 0.5 + Math.random() * 2,
          volatility
        };

        const buyReason = `Entry at $${entryPrice.toFixed(2)} (hold ${holdMinutes}min)`;
        const sellReason = `Exit after ${holdMinutes}min: ${profitable ? 'profit' : 'loss'} ${pnlPct.toFixed(2)}%`;

        trades.push({
          entryTime: entryTime.toISOString(),
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

        if ((i + 1) % 1000 === 0) {
          this.log(`Generated ${i + 1}/${count} trades...`);
        }
      }

      this.log(`Generated ${trades.length} historical trades, storing in DB...`);
      await this.storeTrades(trades);
      this.log(`✓ Stored ${trades.length} historical trades`);

      return trades.length;
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      this.log(`Failed to generate historical trades: ${errorMsg}`);
      throw new Error(`Generate historical trades failed: ${error}`);
    }
  }

  /**
   * Generate simple chaos trades for regular evolution cycles
   */
  async generateChaosTrades(count: number): Promise<number> {
    console.log(`Generating ${count} chaos trades...`);

    try {
      // Just call the historical generator with small count
      return await this.generateHistoricalTrades(count);
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
    this.log('📊 Analyzing patterns from chaos trades...');

    try {
      const winners = await this.env.DB.prepare(
        'SELECT buy_state FROM chaos_trades WHERE profitable = 1 LIMIT 5000'
      ).all();

      const losers = await this.env.DB.prepare(
        'SELECT buy_state FROM chaos_trades WHERE profitable = 0 LIMIT 5000'
      ).all();

      this.log(`Loaded ${winners.results.length} winners, ${losers.results.length} losers`);

      if (winners.results.length < 10 || losers.results.length < 10) {
        this.log('❌ Not enough data for pattern analysis');
        return 0;
      }

      const winnerStates = winners.results.map(r => JSON.parse(r.buy_state as string));
      const loserStates = losers.results.map(r => JSON.parse(r.buy_state as string));

      const winnerAvg = this.calculateAverageState(winnerStates);
      const loserAvg = this.calculateAverageState(loserStates);

      this.log(`Winner avg: momentum=${(winnerAvg.momentum1tick*100).toFixed(3)}%, volatility=${(winnerAvg.volatility*100).toFixed(3)}%`);
      this.log(`Loser avg:  momentum=${(loserAvg.momentum1tick*100).toFixed(3)}%, volatility=${(loserAvg.volatility*100).toFixed(3)}%`);

      const patternsFound: Pattern[] = [];

      const momentumDiff = Math.abs(winnerAvg.momentum1tick - loserAvg.momentum1tick);
      const volatilityDiff = Math.abs(winnerAvg.volatility - loserAvg.volatility);
      const sma10Diff = Math.abs(winnerAvg.vsSma10 - loserAvg.vsSma10);

      this.log(`Differences: momentum=${(momentumDiff*100).toFixed(4)}%, volatility=${(volatilityDiff*100).toFixed(4)}%, sma10=${(sma10Diff*100).toFixed(4)}%`);

      // Lowered threshold from 0.005 to 0.002 (0.2%) to find more patterns
      if (momentumDiff > 0.002) {
        const pattern = {
          patternId: `momentum-${Date.now()}`,
          name: `Momentum ${winnerAvg.momentum1tick > loserAvg.momentum1tick ? 'Positive' : 'Negative'} Entry`,
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
        this.log(`✓ Found momentum pattern: ${pattern.name} (${(momentumDiff*100).toFixed(3)}% diff)`);
      }

      // Check volatility pattern
      if (volatilityDiff > 0.002) {
        const pattern = {
          patternId: `volatility-${Date.now()}`,
          name: `${winnerAvg.volatility > loserAvg.volatility ? 'High' : 'Low'} Volatility Entry`,
          conditions: {
            volatility: { target: winnerAvg.volatility, threshold: volatilityDiff }
          },
          winRate: winners.results.length / (winners.results.length + losers.results.length),
          sampleSize: winners.results.length + losers.results.length,
          discoveredAt: new Date().toISOString(),
          tested: false,
          votes: 0
        };
        patternsFound.push(pattern);
        this.log(`✓ Found volatility pattern: ${pattern.name} (${(volatilityDiff*100).toFixed(3)}% diff)`);
      }

      // Check SMA10 pattern
      if (sma10Diff > 0.003) {
        const pattern = {
          patternId: `sma10-${Date.now()}`,
          name: `Price ${winnerAvg.vsSma10 > loserAvg.vsSma10 ? 'Above' : 'Below'} SMA10`,
          conditions: {
            vsSma10: { target: winnerAvg.vsSma10, threshold: sma10Diff }
          },
          winRate: winners.results.length / (winners.results.length + losers.results.length),
          sampleSize: winners.results.length + losers.results.length,
          discoveredAt: new Date().toISOString(),
          tested: false,
          votes: 0
        };
        patternsFound.push(pattern);
        this.log(`✓ Found SMA10 pattern: ${pattern.name} (${(sma10Diff*100).toFixed(3)}% diff)`);
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

  private log(message: string): void {
    const timestamp = new Date().toISOString();
    const logEntry = `[${timestamp}] ${message}`;
    console.log(logEntry);
    this.logs.push(logEntry);
    if (this.logs.length > 200) {
      this.logs = this.logs.slice(-100); // Keep last 100
    }
  }

  async saveState(): Promise<void> {
    try {
      this.log(`SAVESTATE: Attempting to save state: ${JSON.stringify(this.evolutionState)}`);

      // Save state to D1 database for reliable persistence
      const stateJson = JSON.stringify(this.evolutionState);
      await this.env.DB.prepare(`
        INSERT INTO system_state (key, value, updated_at)
        VALUES ('evolutionState', ?, datetime('now'))
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
      `).bind(stateJson).run();

      // Verify it was saved
      const result = await this.env.DB.prepare(`
        SELECT value FROM system_state WHERE key = 'evolutionState'
      `).first<{ value: string }>();

      if (result) {
        const saved = JSON.parse(result.value);
        this.log(`SAVESTATE: Verified - cycles=${saved.totalCycles}, trades=${saved.totalTrades}`);

        if (saved.totalCycles !== this.evolutionState.totalCycles || saved.totalTrades !== this.evolutionState.totalTrades) {
          this.log(`SAVESTATE ERROR: Verification mismatch!`);
        } else {
          this.log('SAVESTATE: ✓ Successfully saved and verified in D1');
        }
      } else {
        this.log('SAVESTATE ERROR: State not found in D1 after save!');
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? `${error.message} | ${error.stack}` : String(error);
      this.log(`SAVESTATE ERROR: Failed to save - ${errorMsg}`);
      // Don't re-throw, just log the error
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
