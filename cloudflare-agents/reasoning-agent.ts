/**
 * Self-Reflective Reasoning Trading Agents
 *
 * Agents that:
 * 1. Analyze market conditions
 * 2. Query pattern library for best tools
 * 3. Reason about which patterns to combine
 * 4. Execute trades
 * 5. Reflect on outcomes and learn
 * 6. Compete for survival
 */

import { generatePatternId } from './ai-pattern-analyzer';

interface TradingAgent {
  agent_id: string;
  agent_name: string;
  generation: number;
  parent_id?: string;
  personality: string;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  total_roi: number;
  avg_roi_per_trade: number;
  fitness_score: number;
  decisions_made: number;
  reflections_completed: number;
  status: string;
}

interface AgentMemory {
  memory_id: string;
  agent_id: string;
  cycle_number: number;
  market_volatility: string;
  market_trend: string;
  market_volume: string;
  patterns_considered: string[];
  patterns_selected: string[];
  combination_reasoning: string;
  confidence_level: number;
  outcome?: string;
  roi?: number;
  reflection_text?: string;
  lessons_learned?: string;
  strategy_adjustment?: string;
}

interface AgentKnowledge {
  knowledge_id: string;
  agent_id: string;
  knowledge_type: string;
  pattern_id?: string;
  preference_strength?: number;
  condition?: string;
  recommended_action?: string;
  confidence: number;
  times_validated: number;
  times_contradicted: number;
}

interface MarketConditions {
  volatility: 'low' | 'medium' | 'high';
  trend: 'strong_up' | 'weak_up' | 'sideways' | 'weak_down' | 'strong_down';
  volume: 'low' | 'medium' | 'high';
  momentum: number;
}

/**
 * Analyze current market conditions from recent price data
 */
export async function analyzeMarketConditions(db: any): Promise<MarketConditions> {
  // Get recent price data from chaos_trades
  const recentTrades = await db.prepare(`
    SELECT price, timestamp, volume
    FROM chaos_trades
    ORDER BY timestamp DESC
    LIMIT 100
  `).all();

  if (!recentTrades.results || recentTrades.results.length < 10) {
    return {
      volatility: 'medium',
      trend: 'sideways',
      volume: 'medium',
      momentum: 0
    };
  }

  const prices = recentTrades.results.map((t: any) => t.price);
  const volumes = recentTrades.results.map((t: any) => t.volume || 1000);

  // Calculate volatility (standard deviation)
  const mean = prices.reduce((sum: number, p: number) => sum + p, 0) / prices.length;
  const variance = prices.reduce((sum: number, p: number) => sum + Math.pow(p - mean, 2), 0) / prices.length;
  const stdDev = Math.sqrt(variance);
  const volatilityPct = (stdDev / mean) * 100;

  // Calculate trend (linear regression slope)
  const n = prices.length;
  const sumX = (n * (n - 1)) / 2;
  const sumY = prices.reduce((sum: number, p: number) => sum + p, 0);
  const sumXY = prices.reduce((sum: number, p: number, i: number) => sum + (i * p), 0);
  const sumX2 = (n * (n - 1) * (2 * n - 1)) / 6;
  const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
  const momentum = (slope / mean) * 100; // as percentage

  // Calculate volume
  const avgVolume = volumes.reduce((sum: number, v: number) => sum + v, 0) / volumes.length;

  return {
    volatility: volatilityPct > 3 ? 'high' : volatilityPct > 1.5 ? 'medium' : 'low',
    trend: momentum > 2 ? 'strong_up' : momentum > 0.5 ? 'weak_up' : momentum < -2 ? 'strong_down' : momentum < -0.5 ? 'weak_down' : 'sideways',
    volume: avgVolume > 50000 ? 'high' : avgVolume > 10000 ? 'medium' : 'low',
    momentum
  };
}

/**
 * Get top patterns from library based on recent performance
 */
export async function getTopPatterns(db: any, limit: number = 20): Promise<any[]> {
  const patterns = await db.prepare(`
    SELECT
      pattern_id,
      pattern_name,
      votes,
      number_of_runs,
      head_to_head_wins,
      head_to_head_losses,
      origin,
      conditions
    FROM discovered_patterns
    WHERE status = 'winning'
      AND number_of_runs >= 3
    ORDER BY
      (CAST(votes AS REAL) / NULLIF(number_of_runs, 0)) DESC,
      head_to_head_wins DESC
    LIMIT ?
  `).bind(limit).all();

  return patterns.results || [];
}

/**
 * Get agent's learned knowledge
 */
export async function getAgentKnowledge(db: any, agentId: string): Promise<AgentKnowledge[]> {
  const knowledge = await db.prepare(`
    SELECT *
    FROM agent_knowledge
    WHERE agent_id = ?
    ORDER BY confidence DESC, times_validated DESC
    LIMIT 50
  `).bind(agentId).all();

  return knowledge.results || [];
}

/**
 * Agent makes a trading decision using AI reasoning
 */
export async function agentDecision(
  ai: any,
  db: any,
  agent: TradingAgent,
  cycleNumber: number
): Promise<AgentMemory> {
  // 1. Analyze current market
  const market = await analyzeMarketConditions(db);

  // 2. Get top patterns from library
  const topPatterns = await getTopPatterns(db, 20);

  // 3. Get agent's learned knowledge
  const knowledge = await getAgentKnowledge(db, agent.agent_id);

  // 4. Get recent successful memories for context
  const recentMemories = await db.prepare(`
    SELECT
      patterns_selected,
      combination_reasoning,
      outcome,
      roi,
      lessons_learned
    FROM agent_memories
    WHERE agent_id = ?
      AND outcome = 'win'
    ORDER BY decision_timestamp DESC
    LIMIT 10
  `).bind(agent.agent_id).all();

  // 5. Build AI reasoning prompt
  const prompt = `You are "${agent.agent_name}", a ${agent.personality} trading agent (Generation ${agent.generation}).

CURRENT MARKET CONDITIONS:
- Volatility: ${market.volatility}
- Trend: ${market.trend} (momentum: ${market.momentum.toFixed(2)}%)
- Volume: ${market.volume}

YOUR PERFORMANCE:
- Win Rate: ${agent.total_trades > 0 ? ((agent.winning_trades / agent.total_trades) * 100).toFixed(1) : 0}%
- Avg ROI: ${agent.avg_roi_per_trade.toFixed(2)}%
- Total Trades: ${agent.total_trades}

AVAILABLE PATTERNS (Top 20 from library):
${topPatterns.slice(0, 10).map((p: any, i: number) =>
  `${i+1}. ${p.pattern_id}: ${p.pattern_name} (Origin: ${p.origin}, Votes: ${p.votes}, Runs: ${p.number_of_runs}, H2H: ${p.head_to_head_wins}W-${p.head_to_head_losses}L)`
).join('\n')}

YOUR LEARNED KNOWLEDGE:
${knowledge.slice(0, 5).map((k: any) =>
  `- ${k.knowledge_type}: ${k.condition || ''} → ${k.recommended_action || 'Prefer pattern ' + k.pattern_id} (Confidence: ${(k.confidence * 100).toFixed(0)}%)`
).join('\n')}

RECENT SUCCESSFUL STRATEGIES:
${(recentMemories.results || []).slice(0, 3).map((m: any) =>
  `- Patterns: ${m.patterns_selected} → ROI: ${m.roi?.toFixed(2)}% | Lesson: ${m.lessons_learned}`
).join('\n')}

TASK:
Based on current market conditions and your learned knowledge, select 2-4 patterns to combine for a trade.

Respond in JSON format:
{
  "patterns_selected": ["pattern_id_1", "pattern_id_2", ...],
  "reasoning": "Detailed explanation of why these patterns work together in current conditions",
  "confidence": 0.0-1.0,
  "expected_outcome": "Brief prediction"
}

Remember: You are ${agent.personality}, so select patterns that match your personality.`;

  const response = await ai.run('@cf/meta/llama-3.1-8b-instruct', {
    messages: [
      {
        role: 'system',
        content: 'You are a self-reflective trading agent that learns from experience and adapts strategies.'
      },
      {
        role: 'user',
        content: prompt
      }
    ],
    temperature: 0.7,
    max_tokens: 1000
  });

  let decision: any;
  try {
    const text = response.response || '{}';
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    decision = JSON.parse(jsonMatch ? jsonMatch[0] : '{}');
  } catch (e) {
    // Fallback to random selection
    const randomPatterns = topPatterns.sort(() => Math.random() - 0.5).slice(0, 2);
    decision = {
      patterns_selected: randomPatterns.map((p: any) => p.pattern_id),
      reasoning: 'Using top-rated patterns from library',
      confidence: 0.5,
      expected_outcome: 'Unknown'
    };
  }

  // Create memory record
  const memoryId = generatePatternId(`memory-${agent.agent_id}-${cycleNumber}`);
  const memory: AgentMemory = {
    memory_id: memoryId,
    agent_id: agent.agent_id,
    cycle_number: cycleNumber,
    market_volatility: market.volatility,
    market_trend: market.trend,
    market_volume: market.volume,
    patterns_considered: topPatterns.map((p: any) => p.pattern_id),
    patterns_selected: decision.patterns_selected || [],
    combination_reasoning: decision.reasoning || '',
    confidence_level: decision.confidence || 0.5
  };

  // Store memory
  await db.prepare(`
    INSERT INTO agent_memories (
      memory_id, agent_id, cycle_number,
      market_volatility, market_trend, market_volume,
      patterns_considered, patterns_selected,
      combination_reasoning, confidence_level
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).bind(
    memory.memory_id,
    memory.agent_id,
    memory.cycle_number,
    memory.market_volatility,
    memory.market_trend,
    memory.market_volume,
    JSON.stringify(memory.patterns_considered),
    JSON.stringify(memory.patterns_selected),
    memory.combination_reasoning,
    memory.confidence_level
  ).run();

  // Update agent decision count
  await db.prepare(`
    UPDATE trading_agents
    SET decisions_made = decisions_made + 1,
        last_active_at = CURRENT_TIMESTAMP
    WHERE agent_id = ?
  `).bind(agent.agent_id).run();

  return memory;
}

/**
 * Execute trade based on agent's pattern combination
 * Returns simulated outcome
 */
export async function executeAgentTrade(
  db: any,
  memory: AgentMemory
): Promise<{ outcome: string; roi: number; roiAnnualized: number }> {
  // For now, simulate by testing the combined patterns
  // In production, this would execute real trades

  const patterns = await db.prepare(`
    SELECT pattern_id, votes, number_of_runs
    FROM discovered_patterns
    WHERE pattern_id IN (${memory.patterns_selected.map(() => '?').join(',')})
  `).bind(...memory.patterns_selected).all();

  if (!patterns.results || patterns.results.length === 0) {
    return { outcome: 'loss', roi: -2.5, roiAnnualized: -30 };
  }

  // Calculate combined performance (weighted average)
  let totalWeight = 0;
  let weightedRoi = 0;

  for (const pattern of patterns.results) {
    const weight = (pattern.votes || 1) / Math.max(1, pattern.number_of_runs || 1);
    totalWeight += weight;
    // Simulate ROI based on pattern quality
    const patternRoi = ((pattern.votes || 0) / Math.max(1, pattern.number_of_runs)) * 10 - 2;
    weightedRoi += patternRoi * weight;
  }

  const baseRoi = totalWeight > 0 ? weightedRoi / totalWeight : 0;

  // Add combination bonus/penalty
  const combinationBonus = memory.patterns_selected.length > 1 ?
    (Math.random() - 0.3) * 5 : 0; // Combinations can be better or worse

  const finalRoi = baseRoi + combinationBonus + (Math.random() - 0.5) * 2;
  const roiAnnualized = finalRoi * 365 / 24; // Assume 24hr trade

  return {
    outcome: finalRoi > 0 ? 'win' : 'loss',
    roi: finalRoi,
    roiAnnualized
  };
}

/**
 * Agent reflects on decision outcome and learns
 */
export async function agentReflection(
  ai: any,
  db: any,
  agent: TradingAgent,
  memory: AgentMemory,
  outcome: { outcome: string; roi: number; roiAnnualized: number }
): Promise<void> {
  // Update memory with outcome
  await db.prepare(`
    UPDATE agent_memories
    SET outcome = ?,
        roi = ?,
        roi_annualized = ?,
        reflected_at = CURRENT_TIMESTAMP
    WHERE memory_id = ?
  `).bind(outcome.outcome, outcome.roi, outcome.roiAnnualized, memory.memory_id).run();

  memory.outcome = outcome.outcome;
  memory.roi = outcome.roi;

  // Generate reflection using AI
  const reflectionPrompt = `You are "${agent.agent_name}", analyzing your recent trading decision.

DECISION YOU MADE:
- Market: ${memory.market_volatility} volatility, ${memory.market_trend} trend, ${memory.market_volume} volume
- Patterns Used: ${memory.patterns_selected.join(', ')}
- Your Reasoning: ${memory.combination_reasoning}
- Your Confidence: ${(memory.confidence_level * 100).toFixed(0)}%

OUTCOME:
- Result: ${outcome.outcome.toUpperCase()}
- ROI: ${outcome.roi.toFixed(2)}%
- Annualized: ${outcome.roiAnnualized.toFixed(2)}%

TASK: Reflect deeply on this outcome.

Respond in JSON format:
{
  "reflection": "Honest analysis of what happened and why",
  "lessons_learned": "Key takeaway for future decisions",
  "strategy_adjustment": "How to adapt your approach",
  "pattern_feedback": {
    "pattern_id": "increase_preference" or "decrease_preference" or "neutral"
  }
}`;

  const response = await ai.run('@cf/meta/llama-3.1-8b-instruct', {
    messages: [
      {
        role: 'system',
        content: 'You are a self-reflective agent that learns from both successes and failures.'
      },
      {
        role: 'user',
        content: reflectionPrompt
      }
    ],
    temperature: 0.6,
    max_tokens: 800
  });

  let reflection: any;
  try {
    const text = response.response || '{}';
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    reflection = JSON.parse(jsonMatch ? jsonMatch[0] : '{}');
  } catch (e) {
    reflection = {
      reflection: 'Analysis pending',
      lessons_learned: 'Continue testing',
      strategy_adjustment: 'Monitor performance'
    };
  }

  // Store reflection
  await db.prepare(`
    UPDATE agent_memories
    SET reflection_text = ?,
        lessons_learned = ?,
        strategy_adjustment = ?
    WHERE memory_id = ?
  `).bind(
    reflection.reflection || '',
    reflection.lessons_learned || '',
    reflection.strategy_adjustment || '',
    memory.memory_id
  ).run();

  // Update agent knowledge based on reflection
  if (reflection.pattern_feedback) {
    for (const [patternId, feedback] of Object.entries(reflection.pattern_feedback)) {
      const adjustment = feedback === 'increase_preference' ? 0.1 :
                        feedback === 'decrease_preference' ? -0.1 : 0;

      if (adjustment !== 0) {
        // Check if knowledge exists
        const existing = await db.prepare(`
          SELECT knowledge_id, preference_strength, times_validated, times_contradicted
          FROM agent_knowledge
          WHERE agent_id = ? AND pattern_id = ? AND knowledge_type = 'pattern_preference'
        `).bind(agent.agent_id, patternId).first();

        if (existing) {
          const newStrength = Math.max(-1, Math.min(1, (existing.preference_strength || 0) + adjustment));
          const validated = outcome.outcome === 'win' ? existing.times_validated + 1 : existing.times_validated;
          const contradicted = outcome.outcome === 'loss' ? existing.times_contradicted + 1 : existing.times_contradicted;

          await db.prepare(`
            UPDATE agent_knowledge
            SET preference_strength = ?,
                times_validated = ?,
                times_contradicted = ?,
                confidence = ?,
                last_updated = CURRENT_TIMESTAMP
            WHERE knowledge_id = ?
          `).bind(
            newStrength,
            validated,
            contradicted,
            validated / Math.max(1, validated + contradicted),
            existing.knowledge_id
          ).run();
        } else {
          // Create new knowledge
          await db.prepare(`
            INSERT INTO agent_knowledge (
              knowledge_id, agent_id, knowledge_type, pattern_id,
              preference_strength, confidence, times_validated, times_contradicted
            ) VALUES (?, ?, 'pattern_preference', ?, ?, ?, ?, ?)
          `).bind(
            generatePatternId(`knowledge-${agent.agent_id}-${patternId}`),
            agent.agent_id,
            patternId,
            adjustment,
            outcome.outcome === 'win' ? 0.7 : 0.3,
            outcome.outcome === 'win' ? 1 : 0,
            outcome.outcome === 'loss' ? 1 : 0
          ).run();
        }
      }
    }
  }

  // Update agent stats
  const isWin = outcome.outcome === 'win';
  await db.prepare(`
    UPDATE trading_agents
    SET total_trades = total_trades + 1,
        winning_trades = winning_trades + ?,
        losing_trades = losing_trades + ?,
        total_roi = total_roi + ?,
        avg_roi_per_trade = (total_roi + ?) / (total_trades + 1),
        reflections_completed = reflections_completed + 1
    WHERE agent_id = ?
  `).bind(
    isWin ? 1 : 0,
    isWin ? 0 : 1,
    outcome.roi,
    outcome.roi,
    agent.agent_id
  ).run();
}

/**
 * Run one full agent decision cycle
 */
export async function runAgentCycle(
  ai: any,
  db: any,
  agent: TradingAgent,
  cycleNumber: number
): Promise<void> {
  console.log(`\n🤖 Agent ${agent.agent_name} making decision (Cycle ${cycleNumber})...`);

  // 1. Make decision
  const memory = await agentDecision(ai, db, agent, cycleNumber);
  console.log(`   └─ Selected patterns: ${memory.patterns_selected.join(', ')}`);
  console.log(`   └─ Reasoning: ${memory.combination_reasoning.substring(0, 100)}...`);

  // 2. Execute trade
  const outcome = await executeAgentTrade(db, memory);
  console.log(`   └─ Outcome: ${outcome.outcome.toUpperCase()} | ROI: ${outcome.roi.toFixed(2)}%`);

  // 3. Reflect and learn
  await agentReflection(ai, db, agent, memory, outcome);
  console.log(`   └─ Reflection complete, knowledge updated`);
}

export { TradingAgent, AgentMemory, AgentKnowledge, MarketConditions };
