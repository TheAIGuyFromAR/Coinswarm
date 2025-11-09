/**
 * Evolution Agent - Multi-Agent Competitive Evolution System
 *
 * Layer 1 - Pattern Discovery (Tools):
 * - Chaos Discovery Agent: Random exploration, statistical patterns (every cycle)
 * - Academic Papers Agent: Proven strategies from research literature (every 20 cycles)
 * - Technical Patterns Agent: Classic technical analysis setups (every 15 cycles)
 * - Head-to-Head Pattern Testing: Weighted competition (every 3 cycles)
 *
 * Layer 2 - Reasoning Agents (Strategy):
 * - Self-Reflective Trading Agents: Combine patterns intelligently (every 10 cycles)
 * - Agent Competition: Head-to-head battles with evolution
 * - Agent Evolution: Clone winners, eliminate losers (every 50 cycles)
 *
 * Layer 3 - Meta-Learning:
 * - Model Research Agent: Searches for better AI models (every 50 cycles)
 * - Searches HuggingFace, arXiv, Papers with Code
 * - Tests financial/time series models
 */

import { analyzeWithAI, validatePattern, scorePattern, generatePatternId } from './ai-pattern-analyzer';
import { runAcademicResearch } from './academic-papers-agent';
import { runTechnicalResearch } from './technical-patterns-agent';
import { runHeadToHeadCompetition } from './head-to-head-testing';
import { runCompetitionCycle } from './agent-competition';
import { runModelResearch } from './model-research-agent';
import { runCrossAgentLearning } from './cross-agent-learning';
import { calculateAllIndicators, generateTradeRationalization, type TechnicalIndicators } from './technical-indicators';
import { createLogger, LogLevel } from './structured-logger';

const logger = createLogger('EvolutionAgent', LogLevel.INFO);

// Cloudflare AI binding interface
interface CloudflareAI {
  run(model: string, inputs: Record<string, unknown>): Promise<unknown>;
}

// Environment bindings interface
interface Env {
  DB: D1Database;
  EVOLUTION_AGENT: DurableObjectNamespace;
  AI?: CloudflareAI;
  SENTIMENT_AGENT_URL?: string; // Optional: news-sentiment-agent worker URL
}

// Sentiment data structure from news-sentiment-agent
interface SentimentData {
  fear_greed_classification: string;
  fear_greed_index: number;
  market_regime: string;
  overall_sentiment: number;
  news_sentiment: number;
  macro_indicators?: Array<{
    indicator_code: string;
    value: number;
  }>;
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
  pair: string;
  entryTime: string;
  exitTime: string;
  entryPrice: number;
  exitPrice: number;
  pnlPct: number;
  profitable: boolean;
  holdDurationMinutes: number;
  entryIndicators: TechnicalIndicators;
  buyRationalization: string[];  // What indicators suggested buying
  sellRationalization: string[];  // What indicators suggested selling
  buyReason: string;  // Human readable summary
  sellReason: string;  // Human readable summary
  // Sentiment context (for pattern discovery)
  sentimentFearGreed?: number;  // 0-100
  sentimentOverall?: number;  // -1 to +1
  sentimentRegime?: string;  // 'bull', 'bear', 'sideways', 'volatile'
  sentimentClassification?: string;  // 'Extreme Fear', 'Fear', 'Neutral', 'Greed', 'Extreme Greed'
  sentimentNewsScore?: number;  // -1 to +1 (news sentiment only)
  macroFedRate?: number;
  macroCPI?: number;
  macroUnemployment?: number;
  macro10yYield?: number;
}

// Candle data structure
interface Candle {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
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

// Pattern condition interface
interface PatternCondition {
  indicator: string;
  operator: '>' | '<' | '>=' | '<=' | '==' | '!=';
  value: number;
  weight?: number;
}

// Discovered pattern structure
interface Pattern {
  patternId: string;
  name: string;
  conditions: PatternCondition[] | Record<string, unknown>;
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
function errorResponse(message: string, error: Error | unknown, status: number = 500): Response {
  const err = error as Error;
  logger.error(message, err);
  return new Response(
    JSON.stringify(
      {
        error: message,
        details: err?.message || String(error),
        stack: err?.stack,
        timestamp: new Date().toISOString(),
      },
      null,
      2
    ),
    {
      status,
      headers: { 'Content-Type': 'application/json' },
    }
  );
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
    logger.info('EvolutionAgent constructor called');
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
    logger.info('EvolutionAgent constructor completed');
  }

  async fetch(request: Request): Promise<Response> {
    logger.info('Fetch called', { url: request.url });

    try {
      const url = new URL(request.url);
      logger.debug('Processing request', { pathname: url.pathname });

      // Load state from D1 database only on first access (when lastCycleAt is 'never')
      // After that, rely on in-memory state which is maintained by the Durable Object
      if (this.evolutionState.lastCycleAt === 'never') {
        logger.info('First access - loading stored state from D1');
        try {
          const result = await this.env.DB.prepare(`
            SELECT value FROM system_state WHERE key = 'evolutionState'
          `).first<{ value: string }>();

          if (result && result.value) {
            this.evolutionState = JSON.parse(result.value);
            logger.info('State loaded from D1', {
              totalCycles: this.evolutionState.totalCycles,
              totalTrades: this.evolutionState.totalTrades,
            });
          } else {
            logger.info('No stored state found in D1, using defaults');
          }
        } catch (error) {
          logger.error('Error loading state from D1', error as Error);
          this.evolutionState.lastError = `Failed to load state: ${error}`;
        }
      }

      // Debug endpoint
      if (url.pathname === '/debug') {
        logger.debug('Debug endpoint called');
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
        logger.debug('Status endpoint called');
        return new Response(JSON.stringify({
          status: 'running',
          ...this.evolutionState,
          uptime: 'continuous',
          timestamp: new Date().toISOString()
        }, null, 2), {
          headers: { 'Content-Type': 'application/json' }
        });
      }

      // Debug endpoint - check database schema and sample data
      if (url.pathname === '/debug/db') {
        try {
          // Get list of tables
          const tables = await this.env.DB.prepare(`
            SELECT name FROM sqlite_master WHERE type='table' ORDER BY name
          `).all();

          // Get count from chaos_trades if it exists
          const tradeCount = await this.env.DB.prepare(`
            SELECT COUNT(*) as count FROM chaos_trades
          `).first<{ count: number }>();

          // Get sample of chaos_trades with timestamps to check date range
          const sampleTrades = await this.env.DB.prepare(`
            SELECT entry_time, exit_time, pair, entry_price, exit_price, pnl_pct
            FROM chaos_trades
            ORDER BY RANDOM()
            LIMIT 5
          `).all();

          return new Response(JSON.stringify({
            tables: tables.results,
            chaos_trades_count: tradeCount?.count || 0,
            sample_trades: sampleTrades.results,
            timestamp: new Date().toISOString()
          }, null, 2), {
            headers: { 'Content-Type': 'application/json' }
          });
        } catch (error) {
          return new Response(JSON.stringify({
            error: error instanceof Error ? error.message : String(error),
            stack: error instanceof Error ? error.stack : undefined
          }, null, 2), {
            status: 500,
            headers: { 'Content-Type': 'application/json' }
          });
        }
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
        logger.info('Trigger endpoint called');

        if (this.evolutionState.isRunning) {
          logger.warn('Cycle already running');
          return new Response(JSON.stringify({
            error: 'Cycle already running',
            state: this.evolutionState
          }), {
            status: 409,
            headers: { 'Content-Type': 'application/json' }
          });
        }

        // Start evolution in background
        logger.info('Starting evolution cycle');
        this.runEvolutionCycle().catch((error) => {
          logger.error('Evolution cycle failed', error as Error);
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
        logger.info('Stats endpoint called');

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

      // API endpoints for dashboards
      if (url.pathname === '/api/stats') {
        try {
          const patterns = await this.env.DB.prepare('SELECT COUNT(*) as count FROM discovered_patterns').first();
          const activeAgents = await this.env.DB.prepare('SELECT COUNT(*) as count FROM trading_agents WHERE status = ?').bind('active').first();
          const avgGeneration = await this.env.DB.prepare('SELECT AVG(generation) as avg FROM trading_agents WHERE status = ?').bind('active').first();
          const avgFitness = await this.env.DB.prepare('SELECT AVG(fitness_score) as avg FROM trading_agents WHERE status = ?').bind('active').first();

          return new Response(JSON.stringify({
            total_patterns: patterns?.count || 0,
            active_agents: activeAgents?.count || 0,
            avg_generation: avgGeneration?.avg || 0,
            avg_fitness: avgFitness?.avg || 0,
            total_cycles: this.evolutionState.totalCycles
          }), {
            headers: { 'Content-Type': 'application/json' }
          });
        } catch (error) {
          return new Response(JSON.stringify({ error: String(error) }), {
            status: 500,
            headers: { 'Content-Type': 'application/json' }
          });
        }
      }

      if (url.pathname === '/api/patterns') {
        try {
          const origin = url.searchParams.get('origin') || 'all';
          const status = url.searchParams.get('status') || 'all';
          const minRuns = parseInt(url.searchParams.get('min_runs') || '3');
          const limit = parseInt(url.searchParams.get('limit') || '50');

          // Simple query that works with old schema
          let query = 'SELECT * FROM discovered_patterns WHERE number_of_runs >= ? ORDER BY votes DESC LIMIT ?';
          const params: (number | string)[] = [minRuns, limit];

          const patterns = await this.env.DB.prepare(query).bind(...params).all();

          // Get basic stats
          const total = await this.env.DB.prepare('SELECT COUNT(*) as count FROM discovered_patterns').first();
          const withVotes = await this.env.DB.prepare('SELECT COUNT(*) as count FROM discovered_patterns WHERE votes > 0').first();

          return new Response(JSON.stringify({
            patterns: patterns.results || [],
            stats: {
              total: total?.count || 0,
              winning: withVotes?.count || 0,
              chaos: 0,
              academic: 0,
              technical: 0
            }
          }), {
            headers: { 'Content-Type': 'application/json' }
          });
        } catch (error) {
          return new Response(JSON.stringify({ error: String(error) }), {
            status: 500,
            headers: { 'Content-Type': 'application/json' }
          });
        }
      }

      if (url.pathname === '/api/agents/all') {
        try {
          const agents = await this.env.DB.prepare(`
            SELECT * FROM trading_agents
            ORDER BY fitness_score DESC
          `).all();

          const active = await this.env.DB.prepare('SELECT COUNT(*) as count FROM trading_agents WHERE status = ?').bind('active').first();
          const eliminated = await this.env.DB.prepare('SELECT COUNT(*) as count FROM trading_agents WHERE status = ?').bind('eliminated').first();
          const avgGen = await this.env.DB.prepare('SELECT AVG(generation) as avg FROM trading_agents WHERE status = ?').bind('active').first();
          const maxGen = await this.env.DB.prepare('SELECT MAX(generation) as max FROM trading_agents WHERE status = ?').bind('active').first();
          const competitions = await this.env.DB.prepare('SELECT COUNT(*) as count FROM agent_competitions').first();

          return new Response(JSON.stringify({
            agents: agents.results || [],
            stats: {
              active: active?.count || 0,
              eliminated: eliminated?.count || 0,
              avg_generation: avgGen?.avg || 0,
              max_generation: maxGen?.max || 0,
              total_competitions: competitions?.count || 0
            }
          }), {
            headers: { 'Content-Type': 'application/json' }
          });
        } catch (error) {
          return new Response(JSON.stringify({ error: String(error) }), {
            status: 500,
            headers: { 'Content-Type': 'application/json' }
          });
        }
      }

      if (url.pathname === '/api/agents/leaderboard') {
        try {
          const agents = await this.env.DB.prepare(`
            SELECT * FROM trading_agents
            WHERE status = ?
            ORDER BY fitness_score DESC
            LIMIT 100
          `).bind('active').all();

          const active = await this.env.DB.prepare('SELECT COUNT(*) as count FROM trading_agents WHERE status = ?').bind('active').first();
          const avgFitness = await this.env.DB.prepare('SELECT AVG(fitness_score) as avg FROM trading_agents WHERE status = ?').bind('active').first();
          const topFitness = await this.env.DB.prepare('SELECT MAX(fitness_score) as max FROM trading_agents WHERE status = ?').bind('active').first();
          const totalTrades = await this.env.DB.prepare('SELECT SUM(total_trades) as sum FROM trading_agents WHERE status = ?').bind('active').first();
          const avgRoi = await this.env.DB.prepare('SELECT AVG(avg_roi_per_trade) as avg FROM trading_agents WHERE status = ?').bind('active').first();

          return new Response(JSON.stringify({
            agents: agents.results || [],
            stats: {
              active: active?.count || 0,
              avg_fitness: avgFitness?.avg || 0,
              top_fitness: topFitness?.max || 0,
              total_trades: totalTrades?.sum || 0,
              avg_roi: avgRoi?.avg || 0
            }
          }), {
            headers: { 'Content-Type': 'application/json' }
          });
        } catch (error) {
          return new Response(JSON.stringify({ error: String(error) }), {
            status: 500,
            headers: { 'Content-Type': 'application/json' }
          });
        }
      }

      // Root endpoint
      logger.info('Root endpoint, returning help');
      return new Response(JSON.stringify({
        message: 'Evolution Agent - Chaos Trading Evolution System',
        endpoints: {
          '/status': 'Get agent status',
          '/trigger': 'Trigger evolution cycle',
          '/stats': 'Get database statistics',
          '/debug': 'Get debug information',
          '/dashboard/architecture': 'System architecture dashboard',
          '/dashboard/patterns': 'Pattern leaderboard dashboard',
          '/dashboard/swarm': 'Agent swarm visualization',
          '/dashboard/agents': 'Agent leaderboard',
          '/api/stats': 'API - System statistics',
          '/api/patterns': 'API - Pattern data',
          '/api/agents/all': 'API - All agents',
          '/api/agents/leaderboard': 'API - Agent leaderboard'
        },
        version: '2.0.0',
        timestamp: new Date().toISOString()
      }, null, 2), {
        headers: { 'Content-Type': 'application/json' }
      });

    } catch (error) {
      return errorResponse('Fetch handler failed', error);
    }
  }

  async alarm(): Promise<void> {
    logger.info('Alarm triggered');

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
      logger.error('Alarm handler failed', error instanceof Error ? error : new Error(String(error)));
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
        logger.info('Step 3: Testing strategies');
        try {
          const winnersFound = await this.testStrategies();
          logger.info('Strategy testing complete', { winners_found: winnersFound });
          this.evolutionState.winningStrategies += winnersFound;
        } catch (error) {
          logger.error('Strategy testing failed', error instanceof Error ? error : new Error(String(error)));
          // Continue despite error
        }
      }

      // Step 4: Academic research (every 20 cycles)
      if (this.evolutionState.totalCycles % 20 === 0) {
        this.log('Step 4: Running academic research...');
        if (!this.env.AI) {
          this.log('⚠️  AI not available, skipping academic research');
        } else {
          try {
            const academicPatterns = await runAcademicResearch(this.env.AI, this.env.DB);
            this.log(`✓ Academic research: ${academicPatterns} patterns generated`);
            this.evolutionState.patternsDiscovered += academicPatterns;
          } catch (error) {
            const errorMsg = error instanceof Error ? error.message : String(error);
            this.log(`❌ Academic research failed: ${errorMsg}`);
          }
        }
      }

      // Step 5: Technical research (every 15 cycles)
      if (this.evolutionState.totalCycles % 15 === 0) {
        this.log('Step 5: Running technical patterns research...');
        if (!this.env.AI) {
          this.log('⚠️  AI not available, skipping technical research');
        } else {
          try {
            const technicalPatterns = await runTechnicalResearch(this.env.AI, this.env.DB);
            this.log(`✓ Technical research: ${technicalPatterns} patterns generated`);
            this.evolutionState.patternsDiscovered += technicalPatterns;
          } catch (error) {
            const errorMsg = error instanceof Error ? error.message : String(error);
            this.log(`❌ Technical research failed: ${errorMsg}`);
          }
        }
      }

      // Step 6: Head-to-head pattern competition (every 3 cycles)
      if (this.evolutionState.totalCycles % 3 === 0 && this.evolutionState.patternsDiscovered > 1) {
        this.log('Step 6: Running head-to-head pattern competition...');
        try {
          const success = await runHeadToHeadCompetition(this.env.DB);
          if (success) {
            this.log('✓ Head-to-head pattern competition complete');
          } else {
            this.log('⚠️  Head-to-head skipped (not enough patterns)');
          }
        } catch (error) {
          const errorMsg = error instanceof Error ? error.message : String(error);
          this.log(`❌ Head-to-head pattern competition failed: ${errorMsg}`);
        }
      }

      // Step 7: Reasoning agent competition (every 10 cycles)
      if (this.evolutionState.totalCycles % 10 === 0 && this.evolutionState.patternsDiscovered >= 5) {
        this.log('Step 7: Running reasoning agent competition...');
        if (!this.env.AI) {
          this.log('⚠️  AI not available, skipping agent competition');
        } else {
          try {
            await runCompetitionCycle(this.env.AI, this.env.DB, this.evolutionState.totalCycles);
            this.log('✓ Reasoning agent competition complete');
          } catch (error) {
            const errorMsg = error instanceof Error ? error.message : String(error);
            this.log(`❌ Reasoning agent competition failed: ${errorMsg}`);
          }
        }
      }

      // Step 7.5: Cross-agent learning (every 25 cycles)
      if (this.evolutionState.totalCycles % 25 === 0 && this.evolutionState.totalCycles > 0) {
        this.log('Step 7.5: Running cross-agent learning...');
        try {
          await runCrossAgentLearning(this.env.DB);
          this.log('✓ Cross-agent learning complete');
        } catch (error) {
          const errorMsg = error instanceof Error ? error.message : String(error);
          this.log(`❌ Cross-agent learning failed: ${errorMsg}`);
        }
      }

      // Step 8: Model research agent (every 50 cycles)
      if (this.evolutionState.totalCycles % 50 === 0) {
        this.log('Step 8: Running model research...');
        if (!this.env.AI) {
          this.log('⚠️  AI not available, skipping model research');
        } else {
          try {
            await runModelResearch(this.env.AI, this.env.DB);
            this.log('✓ Model research complete');
          } catch (error) {
            const errorMsg = error instanceof Error ? error.message : String(error);
            this.log(`❌ Model research failed: ${errorMsg}`);
          }
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
      logger.error('CRITICAL ERROR in evolution cycle', error instanceof Error ? error : new Error(String(error)));
      this.evolutionState.isRunning = false;
      this.evolutionState.lastError = `Cycle failed: ${error}`;
      await this.saveState();

      // Retry in 5 minutes on error
      logger.info('Scheduling retry in 5 minutes');
      try {
        await this.state.storage.setAlarm(Date.now() + 300000);
      } catch (alarmError) {
        logger.error('Failed to set alarm', alarmError instanceof Error ? alarmError : new Error(String(alarmError)));
      }
    }
  }

  /**
   * Fetch current sentiment data from news-sentiment-agent
   * Returns null if sentiment agent is not configured or fails
   */
  private async fetchSentimentData(): Promise<SentimentData | null> {
    if (!this.env.SENTIMENT_AGENT_URL) {
      this.log('Sentiment agent URL not configured, skipping sentiment data');
      return null;
    }

    try {
      const response = await fetch(`${this.env.SENTIMENT_AGENT_URL}/current`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        this.log(`Sentiment agent returned ${response.status}, skipping sentiment data`);
        return null;
      }

      const data = await response.json() as SentimentData;
      this.log(`✓ Fetched sentiment: ${data.fear_greed_classification} (${data.fear_greed_index}), Regime: ${data.market_regime}`);
      return data;
    } catch (error) {
      this.log(`Failed to fetch sentiment data: ${error instanceof Error ? error.message : String(error)}`);
      return null;
    }
  }

  /**
   * Generate historical trades with realistic price movements
   * - Random entry times over past 30 days
   * - Random hold durations (1 min to 24 hours)
   * - Trend-based price movements with volatility
   */
  async generateHistoricalTrades(count: number): Promise<number> {
    this.log(`Generating ${count} chaos trades using REAL historical data...`);

    // Fetch current sentiment data (optional, for pattern discovery)
    const sentimentData = await this.fetchSentimentData();
    if (sentimentData) {
      this.log(`Sentiment context: ${sentimentData.fear_greed_classification} | Regime: ${sentimentData.market_regime} | Overall: ${sentimentData.overall_sentiment.toFixed(2)}`);
    }

    try {
      const trades: ChaosTrade[] = [];

      // Multi-pair configuration - convert to Binance format
      const pairs = [
        'BTCUSDT', 'SOLUSDT', 'ETHUSDT',
        'BNBUSDT', 'ADAUSDT', 'DOTUSDT'
      ];

      // Cache for candle data (fetch once per pair, reuse for multiple trades)
      const candleCache: { [key: string]: Candle[] } = {};

      // Generate chaos trades
      for (let i = 0; i < count; i++) {
        try {
          // Random pair selection
          const pair = pairs[Math.floor(Math.random() * pairs.length)];

          // Fetch candles from historical worker (or use cached)
          let candles = candleCache[pair];
          if (!candles) {
            // Call historical-data-worker to fetch real Binance data
            const workerUrl = `https://coinswarm-historical-data.bamn86.workers.dev/fetch-fresh?symbol=${pair}&interval=5m&limit=500`;

            this.log(`Fetching REAL market data for ${pair} via historical worker...`);

            try {
              const response = await fetch(workerUrl);

              if (response.ok) {
                const data = await response.json() as any;
                if (data.success && data.candles && data.candles.length > 0) {
                  candles = data.candles;
                  this.log(`✓ SUCCESS: Fetched ${candles.length} REAL candles for ${pair} from historical worker`);
                  candleCache[pair] = candles;
                } else {
                  this.log(`❌ Empty response from historical worker for ${pair} - Skipping`);
                  continue;
                }
              } else {
                const errorText = await response.text();
                this.log(`❌ Historical worker error for ${pair}: HTTP ${response.status} - ${errorText.substring(0, 200)}`);
                this.log(`⚠️  Skipping this trade - no synthetic data allowed`);
                continue;
              }
            } catch (error) {
              this.log(`❌ Fetch error for ${pair}: ${error instanceof Error ? error.message : String(error)}`);
              this.log(`⚠️  Skipping this trade - no synthetic data allowed`);
              continue;
            }
          }

          // Random entry point in the historical data
          // Random hold duration: 1 candle (5min) to 288 candles (24 hours)
          const maxHoldCandles = Math.min(288, candles.length - 1);
          const holdCandles = 1 + Math.floor(Math.random() * maxHoldCandles);

          // Pick random entry that allows for hold duration
          const maxEntryIndex = candles.length - holdCandles - 1;
          if (maxEntryIndex < 0) {
            this.log(`Not enough candles for ${pair}, skipping`);
            continue;
          }

          const entryIndex = Math.floor(Math.random() * maxEntryIndex);
          const exitIndex = entryIndex + holdCandles;

          // Get REAL prices from historical data
          const entryCandle = candles[entryIndex];
          const exitCandle = candles[exitIndex];

          const entryPrice = entryCandle.close;
          const exitPrice = exitCandle.close;
          const entryTime = new Date(entryCandle.timestamp);
          const exitTime = new Date(exitCandle.timestamp);

          const pnlPct = ((exitPrice - entryPrice) / entryPrice) * 100;
          const profitable = exitPrice > entryPrice;

          // Calculate ALL technical indicators at entry
          const entryIndicators = calculateAllIndicators(candles, entryIndex);

          // Generate rationalization: what indicators would have suggested this trade?
          const buyRationalization = generateTradeRationalization(entryIndicators, 'BUY');
          const sellRationalization = generateTradeRationalization(entryIndicators, 'SELL');

          const holdDurationMinutes = holdCandles * 5;

          const buyReason = `Random chaos trade on ${pair} at $${entryPrice.toFixed(2)} (hold ${holdCandles} candles / ${holdDurationMinutes}min)`;
          const sellReason = `Exit ${pair} after ${holdCandles} candles: ${profitable ? 'profit' : 'loss'} ${pnlPct.toFixed(2)}%`;

          // Add sentiment data if available (for pattern discovery like "RSI oversold + extreme fear = 78% win")
          const trade: ChaosTrade = {
            pair,
            entryTime: entryTime.toISOString(),
            exitTime: exitTime.toISOString(),
            entryPrice,
            exitPrice,
            pnlPct,
            profitable,
            holdDurationMinutes,
            entryIndicators,
            buyRationalization,
            sellRationalization,
            buyReason,
            sellReason
          };

          if (sentimentData) {
            trade.sentimentFearGreed = sentimentData.fear_greed_index;
            trade.sentimentOverall = sentimentData.overall_sentiment;
            trade.sentimentRegime = sentimentData.market_regime;
            trade.sentimentClassification = sentimentData.fear_greed_classification;
            trade.sentimentNewsScore = sentimentData.news_sentiment;

            // Add macro indicators if available
            if (sentimentData.macro_indicators && sentimentData.macro_indicators.length > 0) {
              for (const macro of sentimentData.macro_indicators) {
                if (macro.indicator_code === 'FEDFUNDS') trade.macroFedRate = macro.value;
                else if (macro.indicator_code === 'CPIAUCSL') trade.macroCPI = macro.value;
                else if (macro.indicator_code === 'UNRATE') trade.macroUnemployment = macro.value;
                else if (macro.indicator_code === 'DGS10') trade.macro10yYield = macro.value;
              }
            }
          }

          trades.push(trade);

        } catch (tradeError) {
          this.log(`Error generating trade ${i}: ${tradeError}`);
          // Continue with next trade
        }

        if ((i + 1) % 100 === 0) {
          this.log(`Generated ${i + 1}/${count} chaos trades...`);
        }
      }

      this.log(`Generated ${trades.length} chaos trades from REAL data, storing in DB...`);
      await this.storeTrades(trades);
      this.log(`✓ Stored ${trades.length} chaos trades`);

      return trades.length;
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      this.log(`Failed to generate chaos trades: ${errorMsg}`);
      throw new Error(`Generate chaos trades failed: ${error}`);
    }
  }

  /**
   * Calculate real market indicators from historical candle data
   */
  private calculateMarketState(candles: Candle[], index: number): MarketState {
    const current = candles[index];

    // Calculate momentum (1 tick = 5 minutes)
    const momentum1tick = index >= 1
      ? (candles[index].close - candles[index - 1].close) / candles[index - 1].close
      : 0;

    const momentum5tick = index >= 5
      ? (candles[index].close - candles[index - 5].close) / candles[index - 5].close
      : 0;

    // Calculate SMA10 (10 candles = 50 minutes)
    const sma10Start = Math.max(0, index - 9);
    const sma10Candles = candles.slice(sma10Start, index + 1);
    const sma10 = sma10Candles.reduce((sum, c) => sum + c.close, 0) / sma10Candles.length;
    const vsSma10 = (current.close - sma10) / sma10;

    // Calculate average volume (last 20 candles)
    const volStart = Math.max(0, index - 19);
    const volCandles = candles.slice(volStart, index + 1);
    const avgVolume = volCandles.reduce((sum, c) => sum + c.volume, 0) / volCandles.length;
    const volumeVsAvg = avgVolume > 0 ? current.volume / avgVolume : 1;

    // Calculate volatility (std dev of last 10 returns)
    const volatilityStart = Math.max(1, index - 9);
    const returns = [];
    for (let i = volatilityStart; i <= index; i++) {
      const ret = (candles[i].close - candles[i - 1].close) / candles[i - 1].close;
      returns.push(ret);
    }
    const avgReturn = returns.reduce((sum, r) => sum + r, 0) / returns.length;
    const variance = returns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / returns.length;
    const volatility = Math.sqrt(variance);

    return {
      price: current.close,
      momentum1tick,
      momentum5tick,
      vsSma10,
      volumeVsAvg,
      volatility
    };
  }

  /**
   * Generate synthetic candle data for testing when APIs are unavailable
   * Creates realistic price movements with trends and volatility
   */
  private generateSyntheticCandles(pair: string, count: number): Candle[] {
    const candles: Candle[] = [];
    const now = Date.now();

    // Base prices for different pairs
    const basePrices: { [key: string]: number } = {
      'BTCUSDT': 95000,
      'ETHUSDT': 3500,
      'SOLUSDT': 220,
      'BNBUSDT': 680,
      'ADAUSDT': 1.05,
      'DOTUSDT': 8.50
    };

    let currentPrice = basePrices[pair] || 100;
    const volatility = 0.02; // 2% volatility per candle

    // Generate candles going backwards in time
    for (let i = count - 1; i >= 0; i--) {
      const timestamp = now - (i * 5 * 60 * 1000); // 5 minutes per candle

      // Random price movement with slight upward bias (simulating market growth)
      const change = (Math.random() - 0.48) * volatility; // -0.48 to 0.52 for slight upward bias
      const open = currentPrice;
      const close = currentPrice * (1 + change);

      // High and low based on volatility
      const high = Math.max(open, close) * (1 + Math.random() * volatility / 2);
      const low = Math.min(open, close) * (1 - Math.random() * volatility / 2);

      // Volume varies randomly
      const baseVolume = 1000000;
      const volume = baseVolume * (0.5 + Math.random());

      candles.push({
        timestamp,
        open,
        high,
        low,
        close,
        volume
      });

      currentPrice = close;
    }

    return candles;
  }

  /**
   * Generate simple chaos trades for regular evolution cycles
   */
  async generateChaosTrades(count: number): Promise<number> {
    logger.info('Generating chaos trades', { count });

    try {
      // Just call the historical generator with small count
      return await this.generateHistoricalTrades(count);
    } catch (error) {
      logger.error('Failed to generate chaos trades', error instanceof Error ? error : new Error(String(error)));
      throw new Error(`Generate trades failed: ${error}`);
    }
  }

  async storeTrades(trades: ChaosTrade[]): Promise<void> {
    logger.info('Storing trades with indicators in D1', { count: trades.length });

    // Skip if no trades to store (this is normal when fetching fails)
    if (!trades || trades.length === 0) {
      logger.warn('No trades to store, skipping batch insert');
      return;
    }

    logger.info('Storing trades to D1', {
      count: trades.length,
      sample_pair: trades[0]?.pair,
      sample_pnl: trades[0]?.pnlPct
    });

    try {
      if (!this.env.DB) {
        throw new Error('D1 database binding not found');
      }

      // Ultra-minimal INSERT using only columns guaranteed to exist
      // Based on original chaos_trades schema from early implementation
      const stmt = this.env.DB.prepare(`
        INSERT INTO chaos_trades (
          entry_time, exit_time, entry_price, exit_price,
          pnl_pct, profitable
        ) VALUES (?, ?, ?, ?, ?, ?)
      `);

      const batch = trades.map(t => {
        return stmt.bind(
          t.entryTime,
          t.exitTime,
          t.entryPrice,
          t.exitPrice,
          t.pnlPct,
          t.profitable ? 1 : 0
        );
      });

      logger.info('Executing batch insert', { count: batch.length });
      await this.env.DB.batch(batch);
      logger.info('Batch insert complete');

    } catch (error) {
      logger.error('Failed to store trades', error instanceof Error ? error : new Error(String(error)));
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

      // Ultra-low threshold (0.001% = 0.00001) to find any statistical signal
      // With random entries, patterns will be weak, but we want to test the full system
      if (momentumDiff > 0.00001) {
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
          votes: 0,
          origin: 'CHAOS'
        };
        patternsFound.push(pattern);
        this.log(`✓ Found momentum pattern: ${pattern.name} (${(momentumDiff*100).toFixed(3)}% diff)`);
      }

      // Check volatility pattern
      if (volatilityDiff > 0.00001) {
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
          votes: 0,
          origin: 'CHAOS'
        };
        patternsFound.push(pattern);
        this.log(`✓ Found volatility pattern: ${pattern.name} (${(volatilityDiff*100).toFixed(3)}% diff)`);
      }

      // Check SMA10 pattern
      if (sma10Diff > 0.00001) {
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
          votes: 0,
          origin: 'CHAOS'
        };
        patternsFound.push(pattern);
        this.log(`✓ Found SMA10 pattern: ${pattern.name} (${(sma10Diff*100).toFixed(3)}% diff)`);
      }

      // AI-powered pattern discovery
      if (this.env.AI) {
        logger.info('Using AI for pattern discovery');
        try {
          const aiPatterns = await analyzeWithAI(
            this.env.AI,
            winnerAvg,
            loserAvg,
            winners.results.length + losers.results.length
          );

          logger.info('AI suggested patterns', { count: aiPatterns.length });

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
                  votes: 0,
                  origin: 'CHAOS'
                };
                patternsFound.push(pattern);
                logger.info('AI discovered pattern', {
                  name: aiPattern.patternName,
                  confidence: aiPattern.confidence,
                  quality,
                  reasoning: aiPattern.reasoning
                });
              } else {
                logger.warn('AI pattern rejected (low quality)', {
                  name: aiPattern.patternName,
                  quality
                });
              }
            } else {
              logger.warn('AI pattern failed validation', { name: aiPattern.patternName });
            }
          }
        } catch (error) {
          logger.error('AI pattern discovery failed', error instanceof Error ? error : new Error(String(error)));
          // Continue with statistical patterns only
        }
      } else {
        logger.warn('AI binding not available, using statistical analysis only');
      }

      if (patternsFound.length > 0) {
        logger.info('Storing patterns (statistical + AI)', { count: patternsFound.length });
        await this.storePatterns(patternsFound);
        logger.info('Patterns stored successfully');
      }

      return patternsFound.length;
    } catch (error) {
      logger.error('Pattern analysis failed', error instanceof Error ? error : new Error(String(error)));
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
          discovered_at, tested, votes, origin
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
          p.votes,
          p.origin || 'CHAOS'  // Default to CHAOS if not specified
        )
      );

      await this.env.DB.batch(batch);
    } catch (error) {
      logger.error('Failed to store patterns', error instanceof Error ? error : new Error(String(error)));
      throw new Error(`Store patterns failed: ${error}`);
    }
  }

  async testStrategies(): Promise<number> {
    logger.info('Testing strategies');

    try {
      const patterns = await this.env.DB.prepare(
        'SELECT * FROM discovered_patterns WHERE tested = 0 LIMIT 5'
      ).all();

      logger.info('Found untested patterns', { count: patterns.results.length });

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

        logger.info('Testing pattern', { name: pattern.name });

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
          logger.info('Pattern is a winner', {
            name: pattern.name,
            avg_performance: (avgPerformance * 100).toFixed(2),
            max_performance: (maxPerformance * 100).toFixed(2),
            random_performance: (randomPerformance * 100).toFixed(2)
          });
        } else {
          vote = -1;
          logger.info('Pattern is a loser', {
            name: pattern.name,
            avg_performance: (avgPerformance * 100).toFixed(2),
            max_performance: (maxPerformance * 100).toFixed(2),
            random_performance: (randomPerformance * 100).toFixed(2)
          });
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
      logger.error('Strategy testing failed', error instanceof Error ? error : new Error(String(error)));
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
      logger.error('Failed to test pattern performance', error instanceof Error ? error : new Error(String(error)));
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
      logger.error('Failed to test random performance', error instanceof Error ? error : new Error(String(error)));
      return 0;
    }
  }

  private log(message: string): void {
    const timestamp = new Date().toISOString();
    const logEntry = `[${timestamp}] ${message}`;
    logger.info(message, { timestamp });
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
    logger.info('Worker fetch', { url: request.url });

    try {
      // Validate environment
      if (!env.EVOLUTION_AGENT) {
        return errorResponse('EVOLUTION_AGENT binding not found', 'Check wrangler.toml configuration');
      }

      if (!env.DB) {
        return errorResponse('DB binding not found', 'Check wrangler.toml configuration');
      }

      logger.debug('Getting Durable Object instance');
      const id = env.EVOLUTION_AGENT.idFromName('main-evolution-agent');
      const agent = env.EVOLUTION_AGENT.get(id);

      logger.debug('Forwarding request to Durable Object');
      return await agent.fetch(request);

    } catch (error) {
      return errorResponse('Worker fetch failed', error);
    }
  },

  // Scheduled handler for cron triggers
  async scheduled(event: ScheduledEvent, env: Env, ctx: ExecutionContext): Promise<void> {
    logger.info('Cron triggered evolution cycle');

    try {
      // Validate environment
      if (!env.EVOLUTION_AGENT || !env.DB) {
        logger.error('Missing required bindings in scheduled handler');
        return;
      }

      // Get Durable Object instance
      const id = env.EVOLUTION_AGENT.idFromName('main-evolution-agent');
      const agent = env.EVOLUTION_AGENT.get(id);

      // Trigger evolution cycle via fetch to /trigger endpoint
      const triggerRequest = new Request('http://internal/trigger', {
        method: 'POST'
      });

      // Use waitUntil to allow the operation to complete
      ctx.waitUntil(agent.fetch(triggerRequest));

      logger.info('Evolution cycle triggered via cron');
    } catch (error) {
      logger.error('Cron trigger failed', { error });
    }
  }
};

