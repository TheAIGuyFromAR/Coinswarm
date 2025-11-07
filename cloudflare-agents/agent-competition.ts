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

/**
 * Initialize agent population with diverse personalities
 */
export async function initializeAgentPopulation(
  db: any,
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
    const agentId = generatePatternId();
    const personality = personalities[i % personalities.length];

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

  console.log(`\n🧬 Initialized ${agents.length} agents with diverse personalities`);
  return agents;
}

/**
 * Get all active agents
 */
export async function getActiveAgents(db: any): Promise<TradingAgent[]> {
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

  return result.results || [];
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
export async function updateAgentFitness(db: any): Promise<void> {
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
  ai: any,
  db: any,
  cycleNumber: number,
  tradesPerAgent: number = 5
): Promise<CompetitionResult> {
  console.log(`\n🏆 AGENT COMPETITION - Cycle ${cycleNumber}`);

  // Get all active agents
  const agents = await getActiveAgents(db);

  if (agents.length === 0) {
    throw new Error('No active agents found. Initialize population first.');
  }

  console.log(`   ${agents.length} agents competing...`);

  // Each agent makes multiple trades
  const competitionResults: any[] = [];

  for (const agent of agents) {
    console.log(`\n   🤖 ${agent.agent_name} (Gen ${agent.generation})`);

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

        console.log(`      Trade ${i + 1}: ${outcome.outcome} (${outcome.roi.toFixed(2)}%)`);

      } catch (error) {
        console.error(`      Error on trade ${i + 1}:`, error);
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

    console.log(`      Final: ${avgRoi.toFixed(2)}% avg ROI, ${(winRate * 100).toFixed(0)}% win rate`);
  }

  // Sort by total ROI
  competitionResults.sort((a, b) => b.total_roi - a.total_roi);

  // Assign ranks
  competitionResults.forEach((r, i) => {
    r.rank = i + 1;
  });

  console.log('\n   📊 Competition Results:');
  competitionResults.slice(0, 3).forEach((r, i) => {
    console.log(`      ${i + 1}. ${r.agent_name}: ${r.total_roi.toFixed(2)}% (${(r.win_rate * 100).toFixed(0)}% WR)`);
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
  const competitionId = generatePatternId();
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
    JSON.stringify(competitionResults.map((r: any) => r.agent_id)),
    competitionResults[0].agent_id,
    JSON.stringify(competitionResults.map((r: any) => ({ agent_id: r.agent_id, rank: r.rank }))),
    JSON.stringify(competitionResults)
  ).run();

  return {
    competition_id: competitionId,
    winner_id: competitionResults[0].agent_id,
    eliminated_ids: [],
    cloned_ids: [],
    rankings: competitionResults.map((r: any) => ({
      agent_id: r.agent_id,
      agent_name: r.agent_name,
      roi: r.total_roi,
      trades: r.trades,
      rank: r.rank
    }))
  };
}

/**
 * Evolve agent population
 * - Eliminate bottom 20%
 * - Clone top 20% with mutations
 */
export async function evolveAgentPopulation(
  ai: any,
  db: any,
  competition: CompetitionResult
): Promise<{ eliminated: number; cloned: number }> {
  const agents = await getActiveAgents(db);

  if (agents.length < 5) {
    console.log('   ⚠️  Population too small for evolution, skipping');
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

  const totalAgents = rankedAgents.results.length;
  const eliminateCount = Math.max(1, Math.floor(totalAgents * 0.2));
  const cloneCount = eliminateCount; // Keep population constant

  // Eliminate bottom performers
  const toEliminate = rankedAgents.results.slice(-eliminateCount);
  const eliminatedIds: string[] = [];

  console.log(`\n   ☠️  Eliminating bottom ${eliminateCount} agents:`);
  for (const agent of toEliminate) {
    console.log(`      - ${agent.agent_name} (Fitness: ${agent.fitness_score.toFixed(1)})`);

    await db.prepare(`
      UPDATE trading_agents
      SET status = 'eliminated',
          eliminated_at = CURRENT_TIMESTAMP
      WHERE agent_id = ?
    `).bind(agent.agent_id).run();

    eliminatedIds.push(agent.agent_id);
  }

  // Clone top performers with mutations
  const toClone = rankedAgents.results.slice(0, cloneCount);
  const clonedIds: string[] = [];

  console.log(`\n   🧬 Cloning top ${cloneCount} agents with mutations:`);
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

    const cloneId = generatePatternId();
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
      generatePatternId(),
      parent.agent_id,
      cloneId,
      JSON.stringify({ mutation: mutationDesc })
    ).run();

    clonedIds.push(cloneId);

    console.log(`      + ${cloneName} (from ${parent.agent_name}) - ${mutationDesc}`);
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

  console.log(`\n   ✓ Evolution complete: ${eliminatedIds.length} eliminated, ${clonedIds.length} cloned`);

  return { eliminated: eliminatedIds.length, cloned: clonedIds.length };
}

/**
 * Run full competition cycle with evolution
 */
export async function runCompetitionCycle(
  ai: any,
  db: any,
  cycleNumber: number
): Promise<void> {
  // 1. Check if population exists
  const agents = await getActiveAgents(db);

  if (agents.length === 0) {
    console.log('   No agents found, initializing population...');
    await initializeAgentPopulation(db, 10);
  }

  // 2. Run competition
  const competition = await runAgentCompetition(ai, db, cycleNumber, 5);

  console.log(`\n   🏆 Winner: ${competition.rankings[0].agent_name} (${competition.rankings[0].roi.toFixed(2)}%)`);

  // 3. Evolve population (every 5 competitions)
  if (cycleNumber % 5 === 0) {
    const evolution = await evolveAgentPopulation(ai, db, competition);
    console.log(`   🧬 Population evolved: -${evolution.eliminated} +${evolution.cloned}`);
  } else {
    console.log('   ⏭️  Skipping evolution this round');
  }

  // 4. Show current population stats
  const updatedAgents = await getActiveAgents(db);
  const avgFitness = updatedAgents.reduce((sum: number, a: any) => sum + a.fitness_score, 0) / updatedAgents.length;
  const avgGeneration = updatedAgents.reduce((sum: number, a: any) => sum + a.generation, 0) / updatedAgents.length;

  console.log(`\n   📊 Population Stats:`);
  console.log(`      Active agents: ${updatedAgents.length}`);
  console.log(`      Avg fitness: ${avgFitness.toFixed(1)}`);
  console.log(`      Avg generation: ${avgGeneration.toFixed(1)}`);
}

export { CompetitionResult };
