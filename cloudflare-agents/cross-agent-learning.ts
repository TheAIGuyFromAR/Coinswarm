/**
 * Cross-Agent Learning Network
 *
 * Enables agents to share knowledge and learn from high performers.
 * Accelerates overall learning by propagating successful strategies.
 *
 * How it works:
 * 1. Identify top 20% of agents by fitness
 * 2. Extract their successful knowledge (pattern preferences, rules, strategies)
 * 3. Share with bottom 50% of agents
 * 4. Track adoption and validate effectiveness
 * 5. Propagate only knowledge that helps multiple agents
 *
 * Example:
 * - Agent "Momentum Hunter" discovers: "RSI oversold + bull regime = 82% win"
 * - Shares with Agent "Contrarian"
 * - Contrarian adopts, tests on 100 trades, sees 78% win rate
 * - Knowledge validated → propagates to more agents
 * - Original insight now helps entire population
 */

import { createLogger, LogLevel } from './structured-logger';

const logger = createLogger('CrossAgentLearning', LogLevel.INFO);

interface KnowledgeItem {
  knowledge_id: string;
  knowledge_type: string; // 'pattern_preference', 'combination_rule', 'market_condition', 'avoid_condition'
  condition: string | null;
  recommended_action: string | null;
  pattern_id: string | null;
  preference_strength: number; // -1 to +1
  confidence: number; // 0 to 1
  times_validated: number;
  times_contradicted: number;
}

interface Agent {
  agent_id: string;
  agent_name: string;
  personality: string;
  generation: number;
  fitness_score: number;
  total_trades: number;
  winning_trades: number;
  avg_roi_per_trade: number;
}

interface KnowledgeSharingResult {
  sharingsCreated: number;
  teachersCount: number;
  studentsCount: number;
  knowledgeItemsShared: number;
}

/**
 * Cross-Agent Learning Coordinator
 */
export class CrossAgentLearning {
  private db: D1Database;

  constructor(db: D1Database) {
    this.db = db;
  }

  /**
   * Run knowledge sharing cycle
   * - Top agents teach bottom agents
   * - Track what was shared
   * - Schedule validation
   */
  async runKnowledgeSharingCycle(): Promise<KnowledgeSharingResult> {
    logger.info('Running Cross-Agent Learning cycle');

    try {
      // Step 1: Get active agents sorted by fitness
      const agents = await this.db.prepare(`
        SELECT agent_id, agent_name, personality, generation, fitness_score,
               total_trades, winning_trades, avg_roi_per_trade
        FROM trading_agents
        WHERE status = 'active'
        ORDER BY fitness_score DESC
      `).all();

      if (!agents.results || agents.results.length < 5) {
        logger.info('Not enough active agents for knowledge sharing', { minimum_required: 5 });
        return { sharingsCreated: 0, teachersCount: 0, studentsCount: 0, knowledgeItemsShared: 0 };
      }

      const allAgents = agents.results as unknown as Agent[];
      const totalAgents = allAgents.length;

      // Step 2: Identify teachers (top 20%) and students (bottom 50%)
      const teacherCount = Math.max(1, Math.floor(totalAgents * 0.2));
      const studentCount = Math.max(1, Math.floor(totalAgents * 0.5));

      const teachers = allAgents.slice(0, teacherCount);
      const students = allAgents.slice(-studentCount);

      logger.info('Identified teachers and students', {
        teachers_count: teachers.length,
        students_count: students.length
      });

      // Step 3: For each teacher, extract valuable knowledge
      let sharingsCreated = 0;
      let knowledgeItemsShared = 0;

      for (const teacher of teachers) {
        // Get teacher's best knowledge (high confidence, validated multiple times)
        const teacherKnowledge = await this.db.prepare(`
          SELECT knowledge_id, knowledge_type, condition, recommended_action,
                 pattern_id, preference_strength, confidence,
                 times_validated, times_contradicted
          FROM agent_knowledge
          WHERE agent_id = ?
            AND confidence >= 0.6
            AND times_validated >= 3
            AND (times_contradicted = 0 OR times_validated > times_contradicted * 2)
          ORDER BY confidence DESC, times_validated DESC
          LIMIT 5
        `).bind(teacher.agent_id).all();

        if (!teacherKnowledge.results || teacherKnowledge.results.length === 0) {
          logger.info('Teacher has no validated knowledge to share', { teacher_name: teacher.agent_name });
          continue;
        }

        const knowledgeItems = teacherKnowledge.results as unknown as KnowledgeItem[];
        logger.info('Teacher has knowledge to share', {
          teacher_name: teacher.agent_name,
          knowledge_items: knowledgeItems.length
        });

        // Step 4: Share with students
        for (const student of students) {
          // Don't teach yourself
          if (student.agent_id === teacher.agent_id) continue;

          // Check if student already has similar knowledge
          const studentHasKnowledge = await this.hasConflictingKnowledge(
            student.agent_id,
            knowledgeItems
          );

          if (studentHasKnowledge) {
            logger.debug('Student already has similar knowledge', { student_name: student.agent_name });
            continue;
          }

          // Share all knowledge items from this teacher to this student
          for (const knowledge of knowledgeItems) {
            const sharingId = `sharing-${teacher.agent_id}-${student.agent_id}-${knowledge.knowledge_id}-${Date.now()}`;

            await this.db.prepare(`
              INSERT INTO agent_knowledge_sharing (
                sharing_id, timestamp,
                teacher_agent_id, teacher_fitness, teacher_generation,
                student_agent_id, student_fitness_before, student_generation,
                knowledge_type, knowledge_content, knowledge_confidence,
                adopted, adoption_reason
              ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            `).bind(
              sharingId,
              new Date().toISOString(),
              teacher.agent_id,
              teacher.fitness_score,
              teacher.generation,
              student.agent_id,
              student.fitness_score,
              student.generation,
              knowledge.knowledge_type,
              JSON.stringify({
                knowledge_id: knowledge.knowledge_id,
                pattern_id: knowledge.pattern_id,
                condition: knowledge.condition,
                recommended_action: knowledge.recommended_action,
                preference_strength: knowledge.preference_strength,
                times_validated: knowledge.times_validated
              }),
              knowledge.confidence,
              1, // Auto-adopt knowledge from high performers
              `Auto-adopted from top performer ${teacher.agent_name} (fitness: ${teacher.fitness_score.toFixed(2)})`
            ).run();

            // Add knowledge to student's knowledge base
            await this.adoptKnowledge(student.agent_id, knowledge, sharingId);

            sharingsCreated++;
            knowledgeItemsShared++;
          }
        }
      }

      logger.info('Created knowledge sharings', { count: sharingsCreated });

      // Step 5: Update network metrics
      await this.updateNetworkMetrics(allAgents.length, teachers.length, sharingsCreated);

      return {
        sharingsCreated,
        teachersCount: teachers.length,
        studentsCount: students.length,
        knowledgeItemsShared
      };

    } catch (error) {
      logger.error('Failed to run knowledge sharing cycle', error instanceof Error ? error : new Error(String(error)));
      throw error;
    }
  }

  /**
   * Check if student already has conflicting knowledge
   */
  private async hasConflictingKnowledge(
    studentId: string,
    knowledgeItems: KnowledgeItem[]
  ): Promise<boolean> {
    // Check if student has knowledge about the same patterns
    const patternIds = knowledgeItems
      .filter(k => k.pattern_id)
      .map(k => k.pattern_id);

    if (patternIds.length === 0) return false;

    const existing = await this.db.prepare(`
      SELECT COUNT(*) as count
      FROM agent_knowledge
      WHERE agent_id = ? AND pattern_id IN (${patternIds.map(() => '?').join(',')})
    `).bind(studentId, ...patternIds).first();

    return (existing?.count as number) > 0;
  }

  /**
   * Adopt knowledge into student's knowledge base
   */
  private async adoptKnowledge(
    studentId: string,
    knowledge: KnowledgeItem,
    sharingId: string
  ): Promise<void> {
    const newKnowledgeId = `knowledge-${studentId}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    await this.db.prepare(`
      INSERT INTO agent_knowledge (
        knowledge_id, agent_id, knowledge_type,
        pattern_id, preference_strength,
        condition, recommended_action, confidence,
        times_validated, times_contradicted, last_updated
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).bind(
      newKnowledgeId,
      studentId,
      knowledge.knowledge_type,
      knowledge.pattern_id,
      knowledge.preference_strength,
      knowledge.condition,
      knowledge.recommended_action,
      knowledge.confidence * 0.8, // Start with slightly lower confidence
      0, // Student needs to validate themselves
      0,
      new Date().toISOString()
    ).run();

    logger.info('Student adopted knowledge', {
      student_id: studentId,
      knowledge_id: knowledge.knowledge_id
    });
  }

  /**
   * Validate knowledge sharing effectiveness
   * - Called after agents have had time to test adopted knowledge
   */
  async validateKnowledgeSharings(): Promise<number> {
    logger.info('Validating knowledge sharings');

    try {
      // Get pending validations (sharings from at least 50 cycles ago)
      const pendingSharings = await this.db.prepare(`
        SELECT
          aks.sharing_id,
          aks.student_agent_id,
          aks.student_fitness_before,
          aks.knowledge_content,
          ta.fitness_score as current_fitness,
          ta.total_trades
        FROM agent_knowledge_sharing aks
        JOIN trading_agents ta ON aks.student_agent_id = ta.agent_id
        WHERE aks.knowledge_validated_at IS NULL
          AND aks.adopted = 1
          AND datetime(aks.timestamp) <= datetime('now', '-50 minutes')
        LIMIT 100
      `).all();

      if (!pendingSharings.results || pendingSharings.results.length === 0) {
        logger.info('No pending knowledge validations');
        return 0;
      }

      logger.info('Validating knowledge sharings', { count: pendingSharings.results.length });

      let validatedCount = 0;

      for (const sharing of pendingSharings.results as any[]) {
        const fitnessBefore = sharing.student_fitness_before;
        const fitnessCurrent = sharing.current_fitness;
        const fitnessDelta = fitnessCurrent - fitnessBefore;

        // Determine if knowledge helped
        let knowledgeHelped = 0;
        if (fitnessDelta > 0.1) knowledgeHelped = 1;  // Significant improvement
        else if (fitnessDelta < -0.1) knowledgeHelped = -1;  // Knowledge hurt

        // Update validation
        await this.db.prepare(`
          UPDATE agent_knowledge_sharing
          SET student_fitness_after = ?,
              fitness_delta = ?,
              knowledge_helped = ?,
              knowledge_validated_at = ?,
              validation_sample_size = ?
          WHERE sharing_id = ?
        `).bind(
          fitnessCurrent,
          fitnessDelta,
          knowledgeHelped,
          new Date().toISOString(),
          sharing.total_trades,
          sharing.sharing_id
        ).run();

        validatedCount++;
      }

      logger.info('Validated knowledge sharings', { count: validatedCount });
      return validatedCount;

    } catch (error) {
      logger.error('Failed to validate knowledge sharings', error instanceof Error ? error : new Error(String(error)));
      throw error;
    }
  }

  /**
   * Update network learning metrics
   */
  private async updateNetworkMetrics(
    totalAgents: number,
    activeTeachers: number,
    sharingsThisCycle: number
  ): Promise<void> {
    try {
      const metricId = `metric-${Date.now()}`;

      // Get aggregate stats
      const stats = await this.db.prepare(`
        SELECT
          COUNT(DISTINCT agent_id) as active_count,
          AVG(fitness_score) as avg_fitness,
          MAX(fitness_score) as top_fitness
        FROM trading_agents
        WHERE status = 'active'
      `).first();

      const knowledgeCount = await this.db.prepare(`
        SELECT COUNT(DISTINCT knowledge_id) as count
        FROM agent_knowledge
      `).first();

      const successfulAdoptions = await this.db.prepare(`
        SELECT COUNT(*) as count
        FROM agent_knowledge_sharing
        WHERE knowledge_helped = 1
      `).first();

      const failedAdoptions = await this.db.prepare(`
        SELECT COUNT(*) as count
        FROM agent_knowledge_sharing
        WHERE knowledge_helped = -1
      `).first();

      const totalSharings = await this.db.prepare(`
        SELECT COUNT(*) as count
        FROM agent_knowledge_sharing
      `).first();

      await this.db.prepare(`
        INSERT INTO network_learning_metrics (
          metric_id, timestamp, cycle_number,
          total_agents, active_agents, knowledge_items,
          sharing_events_this_cycle, total_sharing_events,
          successful_adoptions, failed_adoptions,
          average_fitness, top_agent_fitness
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `).bind(
        metricId,
        new Date().toISOString(),
        0, // TODO: Get actual cycle number from evolution state
        totalAgents,
        stats?.active_count || 0,
        knowledgeCount?.count || 0,
        sharingsThisCycle,
        totalSharings?.count || 0,
        successfulAdoptions?.count || 0,
        failedAdoptions?.count || 0,
        stats?.avg_fitness || 0,
        stats?.top_fitness || 0
      ).run();

      logger.info('Updated network learning metrics');

    } catch (error) {
      logger.error('Failed to update network metrics', error instanceof Error ? error : new Error(String(error)));
      // Don't throw - this is not critical
    }
  }
}

/**
 * Run cross-agent learning cycle
 * Called every 25 cycles (between pattern discovery and agent evolution)
 */
export async function runCrossAgentLearning(db: D1Database): Promise<void> {
  logger.info('=== CROSS-AGENT LEARNING CYCLE START ===');

  try {
    const learning = new CrossAgentLearning(db);

    // Share knowledge from high performers to learners
    const result = await learning.runKnowledgeSharingCycle();

    logger.info('Knowledge Sharing Results', {
      teachers: result.teachersCount,
      students: result.studentsCount,
      knowledge_items_shared: result.knowledgeItemsShared,
      total_sharings_created: result.sharingsCreated
    });

    // Validate previous sharings
    const validated = await learning.validateKnowledgeSharings();
    logger.info('Validated previous knowledge sharings', { count: validated });

    logger.info('=== Cross-agent learning cycle complete ===');

  } catch (error) {
    logger.error('Cross-agent learning failed', error instanceof Error ? error : new Error(String(error)));
    throw error;
  }
}
