/**
 * Grand Competition Agent
 * Elite tier where agents compete in full historical runs
 *
 * Rules:
 * 1. Full dataset backtest (beginning to end)
 * 2. Shot clock: Must trade within N candles (can't sit idle)
 * 3. Active trading: Must increase stake (no buy & hold)
 * 4. Ranked on multi-factor score
 *
 * Scoring:
 * - Exponential rewards for outperforming market
 * - CUBIC rewards for profiting in bear markets
 * - Linear penalty for underperforming
 * - Activity requirements (shot clock compliance)
 * - Consistency bonuses (win rate, Sharpe, drawdown)
 * - Asymmetry rewards (big wins, small losses)
 */

interface Env {
  DB: D1Database;
}

interface CompetitionConfig {
  shotClockCandles: number; // Max candles between trades
  minTradesPerRun: number; // Minimum trades required
  startingCapital: number;
  dataset: {
    pair: string;
    startTime: string;
    endTime: string;
  };
}

interface MarketRegime {
  startTime: string;
  endTime: string;
  regime: 'bull' | 'bear' | 'sideways' | 'volatile';
  priceChangePct: number;
  startPrice: number;
  endPrice: number;
}

interface CompetitionTrade {
  entryTime: string;
  exitTime: string;
  entryPrice: number;
  exitPrice: number;
  positionSize: number;
  capitalBefore: number;
  capitalAfter: number;
  pnl: number;
  pnlPct: number;
  profitable: boolean;
  marketRegime: 'bull' | 'bear' | 'sideways';
  marketRoiDuringTrade: number;
  candlesSinceLastTrade: number;
  shotClockViolation: boolean;
  entryReason: string;
  exitReason: string;
  confidence: number;
}

interface CompetitionRun {
  runId?: number;
  agentId: number;
  agentName: string;

  // Run parameters
  startTime: string;
  endTime: string;
  datasetSize: number;

  // Performance
  startingCapital: number;
  endingCapital: number;
  totalRoiPct: number;
  totalTrades: number;
  profitableTrades: number;
  winRate: number;

  // Activity
  avgCandlesBetweenTrades: number;
  maxIdleCandles: number;
  activityPenalty: number;

  // Market condition performance
  bullMarketRoi: number;
  bearMarketRoi: number;
  sidewaysMarketRoi: number;

  // Benchmark
  marketRoi: number; // Buy & hold
  alpha: number; // Excess return

  // Risk metrics
  sharpeRatio: number;
  maxDrawdownPct: number;
  avgTradeDurationMinutes: number;

  // Asymmetry
  avgWinSize: number;
  avgLossSize: number;
  profitFactor: number;

  // Scores
  baseScore: number;
  marketConditionMultiplier: number;
  activityMultiplier: number;
  consistencyMultiplier: number;
  asymmetryMultiplier: number;
  finalScore: number;

  // Rankings
  rankByScore?: number;
  rankByRoi?: number;
  rankByWinRate?: number;
  rankByAlpha?: number;

  completed: boolean;
  errorMessage?: string;
  completedAt?: string;
}

/**
 * Calculate multi-factor competition score
 */
function calculateCompetitionScore(run: CompetitionRun, regimes: MarketRegime[]): number {
  // 1. BASE SCORE = total ROI
  const baseScore = run.totalRoiPct;

  // 2. MARKET CONDITION MULTIPLIER
  let marketConditionMultiplier = 1.0;

  // Detect overall market trend
  const overallMarketRoi = run.marketRoi;
  const agentRoi = run.totalRoiPct;

  if (overallMarketRoi < 0 && agentRoi > 0) {
    // CUBIC reward: Profit in bear market
    // Example: Market -20%, Agent +50% → multiplier = (50/|-20|)^3 = 15.625x
    marketConditionMultiplier = Math.pow(Math.abs(agentRoi / overallMarketRoi), 3);
  } else if (overallMarketRoi > 0 && agentRoi > overallMarketRoi) {
    // EXPONENTIAL reward: Outperform bull market
    // Example: Market +80%, Agent +100% → multiplier = (100/80)^2 = 1.56x
    marketConditionMultiplier = Math.pow(agentRoi / overallMarketRoi, 2);
  } else if (overallMarketRoi > 0 && agentRoi < overallMarketRoi) {
    // LINEAR penalty: Underperform bull market
    // Example: Market +80%, Agent +60% → multiplier = 60/80 = 0.75x
    marketConditionMultiplier = agentRoi / overallMarketRoi;
  }

  // 3. ACTIVITY MULTIPLIER (shot clock compliance)
  let activityMultiplier = 1.0;

  const shotClockLimit = 288; // 24 hours (288 * 5min candles)
  if (run.maxIdleCandles > shotClockLimit) {
    // Penalty for sitting idle too long
    activityMultiplier = Math.max(0.1, 1 - (run.maxIdleCandles - shotClockLimit) / shotClockLimit);
  }

  // Also check minimum trade frequency
  const minTradesPerDay = 1;
  const runDurationDays = (new Date(run.endTime).getTime() - new Date(run.startTime).getTime()) / (1000 * 60 * 60 * 24);
  const expectedMinTrades = Math.floor(runDurationDays * minTradesPerDay);

  if (run.totalTrades < expectedMinTrades) {
    activityMultiplier *= Math.max(0.5, run.totalTrades / expectedMinTrades);
  }

  // 4. CONSISTENCY MULTIPLIER (win rate, Sharpe, drawdown)
  let consistencyMultiplier = 1.0;

  // Win rate bonus (square root to avoid over-weighting)
  // 50% win rate = 1.0x, 60% = 1.10x, 70% = 1.18x
  consistencyMultiplier *= Math.pow(run.winRate / 50, 0.5);

  // Sharpe ratio bonus
  consistencyMultiplier *= Math.max(1.0, 1 + (run.sharpeRatio - 1) * 0.2);

  // Drawdown penalty
  consistencyMultiplier *= 1 / (1 + Math.abs(run.maxDrawdownPct) / 100);

  // 5. ASYMMETRY MULTIPLIER (profit factor, risk/reward)
  let asymmetryMultiplier = 1.0;

  // Profit factor bonus (log scale)
  // Profit factor 2.0 = 1.69x, 3.0 = 2.20x
  if (run.profitFactor > 1) {
    asymmetryMultiplier *= Math.log(run.profitFactor + 1) + 1;
  }

  // Risk/Reward ratio
  if (run.avgLossSize > 0) {
    const riskRewardRatio = run.avgWinSize / run.avgLossSize;
    asymmetryMultiplier *= Math.max(0.5, Math.min(2.0, riskRewardRatio / 2));
  }

  // FINAL SCORE
  const finalScore = baseScore * marketConditionMultiplier * activityMultiplier * consistencyMultiplier * asymmetryMultiplier;

  // Update run object
  run.baseScore = baseScore;
  run.marketConditionMultiplier = marketConditionMultiplier;
  run.activityMultiplier = activityMultiplier;
  run.consistencyMultiplier = consistencyMultiplier;
  run.asymmetryMultiplier = asymmetryMultiplier;
  run.finalScore = finalScore;

  return finalScore;
}

/**
 * Detect market regimes from price data
 */
async function detectMarketRegimes(
  env: Env,
  pair: string,
  startTime: string,
  endTime: string
): Promise<MarketRegime[]> {
  // For now, use simple rolling window approach
  // In production, would fetch actual price data and calculate regimes

  // Simplified: Split into weekly periods and classify
  const regimes: MarketRegime[] = [];

  // This would be replaced with actual price data analysis
  // For now, return placeholder
  return regimes;
}

/**
 * Calculate buy & hold benchmark
 */
function calculateBuyHoldBenchmark(
  startPrice: number,
  endPrice: number
): number {
  return ((endPrice - startPrice) / startPrice) * 100;
}

/**
 * Store competition run in database
 */
async function storeCompetitionRun(
  env: Env,
  run: CompetitionRun
): Promise<number> {
  const result = await env.DB.prepare(`
    INSERT INTO competition_runs (
      agent_id, agent_name,
      start_time, end_time, dataset_size,
      starting_capital, ending_capital, total_roi_pct,
      total_trades, profitable_trades, win_rate,
      avg_candles_between_trades, max_idle_candles, activity_penalty,
      bull_market_roi, bear_market_roi, sideways_market_roi,
      market_roi, alpha,
      sharpe_ratio, max_drawdown_pct, avg_trade_duration_minutes,
      avg_win_size, avg_loss_size, profit_factor,
      base_score, market_condition_multiplier, activity_multiplier,
      consistency_multiplier, asymmetry_multiplier, final_score,
      completed, completed_at
    ) VALUES (
      ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
      ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
      ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
    )
  `).bind(
    run.agentId, run.agentName,
    run.startTime, run.endTime, run.datasetSize,
    run.startingCapital, run.endingCapital, run.totalRoiPct,
    run.totalTrades, run.profitableTrades, run.winRate,
    run.avgCandlesBetweenTrades, run.maxIdleCandles, run.activityPenalty,
    run.bullMarketRoi, run.bearMarketRoi, run.sidewaysMarketRoi,
    run.marketRoi, run.alpha,
    run.sharpeRatio, run.maxDrawdownPct, run.avgTradeDurationMinutes,
    run.avgWinSize, run.avgLossSize, run.profitFactor,
    run.baseScore, run.marketConditionMultiplier, run.activityMultiplier,
    run.consistencyMultiplier, run.asymmetryMultiplier, run.finalScore,
    run.completed ? 1 : 0, run.completedAt || new Date().toISOString()
  ).run();

  return result.meta.last_row_id;
}

/**
 * Get competition leaderboard
 */
async function getCompetitionLeaderboard(
  env: Env,
  limit: number = 50
): Promise<any[]> {
  const result = await env.DB.prepare(`
    SELECT
      agent_id,
      agent_name,
      total_runs,
      best_score,
      avg_score,
      best_roi,
      avg_win_rate,
      best_alpha,
      avg_bear_market_roi,
      profitable_runs,
      profitable_in_bear,
      last_run_at
    FROM competition_leaderboard
    ORDER BY best_score DESC
    LIMIT ?
  `).bind(limit).all();

  return result.results;
}

/**
 * Cloudflare Worker handler
 */
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;

    // CORS headers
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
      'Content-Type': 'application/json'
    };

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    try {
      // Route: Get competition leaderboard
      if (path === '/leaderboard' && request.method === 'GET') {
        const limit = parseInt(url.searchParams.get('limit') || '50');
        const leaderboard = await getCompetitionLeaderboard(env, limit);

        return new Response(JSON.stringify({
          leaderboard,
          timestamp: new Date().toISOString()
        }), { headers: corsHeaders });
      }

      // Route: Get agent's competition history
      if (path === '/agent' && request.method === 'GET') {
        const agentId = url.searchParams.get('id');

        if (!agentId) {
          return new Response(JSON.stringify({ error: 'Missing agent ID' }), {
            status: 400,
            headers: corsHeaders
          });
        }

        const runs = await env.DB.prepare(`
          SELECT * FROM competition_runs
          WHERE agent_id = ?
          ORDER BY final_score DESC
          LIMIT 100
        `).bind(agentId).all();

        return new Response(JSON.stringify({
          agent_id: agentId,
          runs: runs.results,
          timestamp: new Date().toISOString()
        }), { headers: corsHeaders });
      }

      // Route: Submit competition run (for external agents)
      if (path === '/submit' && request.method === 'POST') {
        const run = await request.json() as CompetitionRun;

        // Validate run
        if (!run.agentId || !run.agentName || !run.totalRoiPct) {
          return new Response(JSON.stringify({ error: 'Invalid run data' }), {
            status: 400,
            headers: corsHeaders
          });
        }

        // Calculate score
        const regimes = await detectMarketRegimes(env, 'BTC-USDT', run.startTime, run.endTime);
        calculateCompetitionScore(run, regimes);

        // Store run
        const runId = await storeCompetitionRun(env, run);

        return new Response(JSON.stringify({
          message: 'Competition run submitted',
          run_id: runId,
          final_score: run.finalScore,
          timestamp: new Date().toISOString()
        }), { headers: corsHeaders });
      }

      // Route: Root
      if (path === '/' && request.method === 'GET') {
        return new Response(JSON.stringify({
          message: 'Grand Competition - Elite Agent Arena',
          description: 'Agents compete in full historical runs with sophisticated multi-factor scoring',
          endpoints: {
            '/leaderboard': 'GET - Competition leaderboard',
            '/agent?id=<id>': 'GET - Agent competition history',
            '/submit': 'POST - Submit competition run',
            '/stats': 'GET - Competition statistics'
          },
          scoring: {
            bearMarketProfit: 'Cubic reward (up to 15x+)',
            bullMarketOutperform: 'Exponential reward (up to 2-3x)',
            activityRequirement: 'Shot clock: Must trade within 24hrs',
            consistency: 'Win rate, Sharpe ratio, drawdown',
            asymmetry: 'Profit factor, risk/reward ratio'
          },
          version: '1.0.0',
          timestamp: new Date().toISOString()
        }), { headers: corsHeaders });
      }

      return new Response(JSON.stringify({ error: 'Not found' }), {
        status: 404,
        headers: corsHeaders
      });

    } catch (error) {
      console.error('Error:', error);
      return new Response(JSON.stringify({
        error: 'Internal server error',
        message: error instanceof Error ? error.message : String(error)
      }), {
        status: 500,
        headers: corsHeaders
      });
    }
  }
};
