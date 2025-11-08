/**
 * Agent Competition & Evolution System
 *
 * Agents compete head-to-head in trading battles
 * Winners survive and clone with mutations
 * Losers are eliminated
 * Population maintains constant size
 */

import { generatePatternId } from './ai-pattern-analyzer';
import { TradingAgent, agentDecision, executeAgentTrade, agentReflection } from './reasoning-agent';
import { createLogger, LogLevel } from './structured-logger';

const logger = createLogger('AgentCompetition', LogLevel.INFO);

// AI interface
interface CloudflareAI {
  run(model: string, inputs: Record<string, unknown>): Promise<{ response?: string; [key: string]: unknown }>;
}

interface CompetitionResult {
  competition_id: string;
  winner_id: string;
  eliminated_ids: string[];
  cloned_ids: string[];
  rankings: {
    agent_id: string;
    agent_name: string;
    roi: number;
    trades: number;
    rank: number;
  }[];
}

interface RankingResult {
  agent_id: string;
  agent_name: string;
  personality: string;
  generation: number;
  roi: number;
  total_roi: number;
  win_rate: number;
  trades: number;
  rank?: number;
}

interface RankedAgent {
  agent_id: string;
  agent_name: string;
  fitness_score: number;
  personality: string;
  generation: number;
}

/**
 * Initialize agent population with diverse personalities
 */
export async function initializeAgentPopulation(
  db: D1Database,
  populationSize: number = 10
): Promise<TradingAgent[]> {
  const personalities = [
    'conservative',
    'aggressive',
    'balanced',
    'contrarian',
    'momentum_hunter',
    'mean_reverter',
    'volatility_trader',
    'trend_follower',
    'scalper',
    'swing_trader'
  ];

  const agents: TradingAgent[] = [];

  for (let i = 0; i < populationSize; i++) {
    const personality = personalities[i % personalities.length];
    const agentId = generatePatternId(`agent-${personality}-${i}`);

    const agent: TradingAgent = {
      agent_id: agentId,
      agent_name: `${personality.toUpperCase()}-GEN1-${Math.floor(Math.random() * 1000)}`,
      generation: 1,
      personality,
      total_trades: 0,
      winning_trades: 0,
      losing_trades: 0,
      total_roi: 0,
      avg_roi_per_trade: 0,
      fitness_score: 0,
      decisions_made: 0,
      reflections_completed: 0,
      status: 'active'
    };

    // Insert into database
    await db.prepare(`
      INSERT INTO trading_agents (
        agent_id, agent_name, generation, personality, status
      ) VALUES (?, ?, ?, ?, 'active')
    `).bind(agent.agent_id, agent.agent_name, agent.generation, agent.personality).run();

    agents.push(agent);
  }

  logger.info('Initialized agent population', {
    count: agents.length,
    personalities: personalities.slice(0, populationSize),
  });
  return agents;
}

/**
 * Get all active agents
 */
export async function getActiveAgents(db: D1Database): Promise<TradingAgent[]> {
  const result = await db.prepare(`
    SELECT
      agent_id,
      agent_name,
      generation,
      parent_id,
      personality,
      total_trades,
      winning_trades,
      losing_trades,
      total_roi,
      avg_roi_per_trade,
      fitness_score,
      decisions_made,
      reflections_completed,
      status
    FROM trading_agents
    WHERE status = 'active'
    ORDER BY fitness_score DESC
  `).all();

  return (result.results || []) as unknown as TradingAgent[];
}

/**
 * Calculate agent fitness score
 * Fitness = (Win Rate × 50) + (Avg ROI × 10) + (Experience Factor × 20)
 */
export function calculateFitnessScore(agent: TradingAgent): number {
  if (agent.total_trades === 0) return 0;

  const winRate = agent.winning_trades / agent.total_trades;
  const avgRoi = agent.avg_roi_per_trade;

  // Experience factor: More trades = more reliable, but with diminishing returns
  const experienceFactor = Math.min(1, agent.total_trades / 50);

  // Sharpe-like ratio component
  const sharpeComponent = avgRoi / Math.max(1, Math.abs(avgRoi) * 0.1);

  const fitness =
    (winRate * 50) +
    (avgRoi * 10) +
    (experienceFactor * 20) +
    (sharpeComponent * 10);

  return Math.max(0, fitness);
}

/**
 * Update agent fitness scores
 */
export async function updateAgentFitness(db: D1Database): Promise<void> {
  const agents = await getActiveAgents(db);

  for (const agent of agents) {
    const fitness = calculateFitnessScore(agent);

    await db.prepare(`
      UPDATE trading_agents
      SET fitness_score = ?
      WHERE agent_id = ?
    `).bind(fitness, agent.agent_id).run();
  }
}

/**
 * Run agent competition
 * Each agent trades for a period, then results are compared
 */
export async function runAgentCompetition(
  ai: CloudflareAI,
  db: D1Database,
  cycleNumber: number,
  tradesPerAgent: number = 5
): Promise<CompetitionResult> {
  logger.info('Agent competition cycle started', {
    cycle: cycleNumber,
    trades_per_agent: tradesPerAgent,
  });

  // Get all active agents
  const agents = await getActiveAgents(db);

  if (agents.length === 0) {
    throw new Error('No active agents found. Initialize population first.');
  }

  logger.info('Agents competing', { count: agents.length });

  // Each agent makes multiple trades
  const competitionResults: RankingResult[] = [];

  for (const agent of agents) {
    logger.debug('Agent competing', {
      agent_name: agent.agent_name,
      agent_id: agent.agent_id,
      generation: agent.generation,
    });

    let totalRoi = 0;
    let wins = 0;
    let trades = 0;

    for (let i = 0; i < tradesPerAgent; i++) {
      try {
        // Make decision
        const memory = await agentDecision(ai, db, agent, cycleNumber);

        // Execute trade
        const outcome = await executeAgentTrade(db, memory);

        // Reflect
        await agentReflection(ai, db, agent, memory, outcome);

        totalRoi += outcome.roi;
        if (outcome.outcome === 'win') wins++;
        trades++;

        logger.debug('Trade completed', {
          agent_id: agent.agent_id,
          trade_num: i + 1,
          outcome: outcome.outcome,
          roi: outcome.roi.toFixed(2),
        });

      } catch (error) {
        logger.error('Trade failed', {
          agent_id: agent.agent_id,
          trade_num: i + 1,
          error: error instanceof Error ? error.message : String(error),
        });
      }

      // Small delay between trades
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    const avgRoi = trades > 0 ? totalRoi / trades : 0;
    const winRate = trades > 0 ? wins / trades : 0;

    competitionResults.push({
      agent_id: agent.agent_id,
      agent_name: agent.agent_name,
      personality: agent.personality,
      generation: agent.generation,
      roi: avgRoi,
      total_roi: totalRoi,
      win_rate: winRate,
      trades
    });

    logger.info('Agent competition finished', {
      agent_id: agent.agent_id,
      agent_name: agent.agent_name,
      avg_roi: avgRoi.toFixed(2),
      win_rate: (winRate * 100).toFixed(0),
      total_trades: trades,
    });
  }

  // Sort by total ROI
  competitionResults.sort((a, b) => b.total_roi - a.total_roi);

  // Assign ranks
  competitionResults.forEach((r, i) => {
    r.rank = i + 1;
  });

  logger.info('Competition results', {
    top_3: competitionResults.slice(0, 3).map((r, i) => ({
      rank: i + 1,
      name: r.agent_name,
      roi: r.total_roi.toFixed(2),
      win_rate: (r.win_rate * 100).toFixed(0),
    })),
  });

  // Update agent fitness scores
  await updateAgentFitness(db);

  // Update competition counts
  for (const result of competitionResults) {
    const isWinner = result.rank === 1;

    await db.prepare(`
      UPDATE trading_agents
      SET competitions_entered = competitions_entered + 1,
          competitions_won = competitions_won + ?,
          rank = ?
      WHERE agent_id = ?
    `).bind(
      isWinner ? 1 : 0,
      result.rank,
      result.agent_id
    ).run();
  }

  // Store competition record
  const competitionId = generatePatternId(`competition-${Date.now()}`);
  await db.prepare(`
    INSERT INTO agent_competitions (
      competition_id,
      timeframe,
      participants,
      winner_id,
      rankings,
      performance_data
    ) VALUES (?, ?, ?, ?, ?, ?)
  `).bind(
    competitionId,
    `${tradesPerAgent} trades per agent`,
    JSON.stringify(competitionResults.map((r) => r.agent_id)),
    competitionResults[0].agent_id,
    JSON.stringify(competitionResults.map((r) => ({ agent_id: r.agent_id, rank: r.rank }))),
    JSON.stringify(competitionResults)
  ).run();

  return {
    competition_id: competitionId,
    winner_id: competitionResults[0].agent_id,
    eliminated_ids: [],
    cloned_ids: [],
    rankings: competitionResults.map((r) => ({
      agent_id: r.agent_id,
      agent_name: r.agent_name,
      roi: r.total_roi,
      trades: r.trades,
      rank: r.rank || 0
    }))
  };
}

/**
 * Evolve agent population
 * - Eliminate bottom 20%
 * - Clone top 20% with mutations
 */
export async function evolveAgentPopulation(
  ai: CloudflareAI,
  db: D1Database,
  competition: CompetitionResult
): Promise<{ eliminated: number; cloned: number }> {
  const agents = await getActiveAgents(db);

  if (agents.length < 5) {
    logger.warn('Population too small for evolution, skipping', { agent_count: agents.length });
    return { eliminated: 0, cloned: 0 };
  }

  // Update fitness first
  await updateAgentFitness(db);

  // Get updated rankings
  const rankedAgents = await db.prepare(`
    SELECT agent_id, agent_name, fitness_score, personality, generation
    FROM trading_agents
    WHERE status = 'active'
    ORDER BY fitness_score DESC
  `).all();

  const rankedList = (rankedAgents.results || []) as unknown as RankedAgent[];
  const totalAgents = rankedList.length;
  const eliminateCount = Math.max(1, Math.floor(totalAgents * 0.2));
  const cloneCount = eliminateCount; // Keep population constant

  // Eliminate bottom performers
  const toEliminate = rankedList.slice(-eliminateCount);
  const eliminatedIds: string[] = [];

  logger.info('Eliminating bottom agents', {
    count: eliminateCount,
  });
  for (const agent of toEliminate) {
    logger.debug('Eliminating agent', {
      name: agent.agent_name,
      fitness: agent.fitness_score.toFixed(1),
    });

    await db.prepare(`
      UPDATE trading_agents
      SET status = 'eliminated',
          eliminated_at = CURRENT_TIMESTAMP
      WHERE agent_id = ?
    `).bind(agent.agent_id).run();

    eliminatedIds.push(agent.agent_id);
  }

  // Clone top performers with mutations
  const toClone = rankedList.slice(0, cloneCount);
  const clonedIds: string[] = [];

  logger.info('Cloning top agents with mutations', { count: cloneCount });
  for (const parent of toClone) {
    const mutationType = Math.random();
    let newPersonality = parent.personality;
    let mutationDesc = 'none';

    // 30% chance of personality mutation
    if (mutationType < 0.3) {
      const personalities = ['conservative', 'aggressive', 'balanced', 'contrarian',
                            'momentum_hunter', 'mean_reverter', 'volatility_trader',
                            'trend_follower', 'scalper', 'swing_trader'];

      newPersonality = personalities[Math.floor(Math.random() * personalities.length)];
      mutationDesc = `personality: ${parent.personality} → ${newPersonality}`;
    }

    const cloneId = generatePatternId(`clone-${newPersonality}-gen${parent.generation + 1}`);
    const cloneName = `${newPersonality.toUpperCase()}-GEN${parent.generation + 1}-${Math.floor(Math.random() * 1000)}`;

    await db.prepare(`
      INSERT INTO trading_agents (
        agent_id, agent_name, generation, parent_id, personality, status
      ) VALUES (?, ?, ?, ?, ?, 'active')
    `).bind(
      cloneId,
      cloneName,
      parent.generation + 1,
      parent.agent_id,
      newPersonality
    ).run();

    // Record lineage
    await db.prepare(`
      INSERT INTO agent_lineage (
        lineage_id, ancestor_id, descendant_id, generation_gap, mutation_type, mutation_details
      ) VALUES (?, ?, ?, 1, 'evolution', ?)
    `).bind(
      generatePatternId(`lineage-${parent.agent_id}-${cloneId}`),
      parent.agent_id,
      cloneId,
      JSON.stringify({ mutation: mutationDesc })
    ).run();

    clonedIds.push(cloneId);

    logger.info('Clone created', {
      clone_name: cloneName,
      parent_name: parent.agent_name,
      mutation: mutationDesc,
    });
  }

  // Update competition record with evolution outcomes
  await db.prepare(`
    UPDATE agent_competitions
    SET agents_eliminated = ?,
        agents_cloned = ?
    WHERE competition_id = ?
  `).bind(
    JSON.stringify(eliminatedIds),
    JSON.stringify(clonedIds),
    competition.competition_id
  ).run();

  logger.info('Evolution cycle complete', {
    eliminated_count: eliminatedIds.length,
    cloned_count: clonedIds.length,
  });

  return { eliminated: eliminatedIds.length, cloned: clonedIds.length };
}

/**
 * Run full competition cycle with evolution
 */
export async function runCompetitionCycle(
  ai: CloudflareAI,
  db: D1Database,
  cycleNumber: number
): Promise<void> {
  // 1. Check if population exists
  const agents = await getActiveAgents(db);

  if (agents.length === 0) {
    logger.warn('No agents found, initializing population');
    await initializeAgentPopulation(db, 10);
  }

  // 2. Run competition
  const competition = await runAgentCompetition(ai, db, cycleNumber, 5);

  logger.info('Competition winner', {
    winner: competition.rankings[0].agent_name,
    roi: competition.rankings[0].roi.toFixed(2),
  });

  // 3. Evolve population (every 5 competitions)
  if (cycleNumber % 5 === 0) {
    const evolution = await evolveAgentPopulation(ai, db, competition);
    logger.info('Population evolved', {
      eliminated: evolution.eliminated,
      cloned: evolution.cloned,
    });
  } else {
    logger.info('Evolution skipped this round');
  }

  // 4. Show current population stats
  const updatedAgents = await getActiveAgents(db);
  const avgFitness = updatedAgents.reduce((sum: number, a: TradingAgent) => sum + a.fitness_score, 0) / updatedAgents.length;
  const avgGeneration = updatedAgents.reduce((sum: number, a: TradingAgent) => sum + a.generation, 0) / updatedAgents.length;

  logger.info('Population stats', {
    active_agents: updatedAgents.length,
    avg_fitness: avgFitness.toFixed(1),
    avg_generation: avgGeneration.toFixed(1),
  });
}

export type { CompetitionResult };
