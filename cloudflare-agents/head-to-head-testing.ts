/**
 * Head-to-Head Strategy Competition System
 *
 * Implements weighted random selection and head-to-head testing:
 * - Weighted by: fewer runs + more votes (exploration + exploitation)
 * - Random timeframes with bonus for longer periods
 * - Tracks wins/losses for evolutionary pressure
 */

interface Pattern {
  pattern_id: string;
  name: string;
  conditions: string;
  votes: number;
  number_of_runs: number;
  annualized_roi_pct: number | null;
  origin: string;
}

interface TestResult {
  patternId: string;
  roi: number;
  annualizedRoi: number;
  endingValue: number;
}

const TIMEFRAMES = [
  { name: '1m', minutes: 1, bonus: 1.0 },
  { name: '5m', minutes: 5, bonus: 1.05 },
  { name: '15m', minutes: 15, bonus: 1.1 },
  { name: '1h', minutes: 60, bonus: 1.2 },
  { name: '4h', minutes: 240, bonus: 1.5 },
  { name: '1d', minutes: 1440, bonus: 2.0 }
];

/**
 * Calculate selection weight for a pattern
 * Higher weight = more likely to be selected
 *
 * Formula: weight = (exploration_factor) × (exploitation_factor)
 * - exploration_factor = 100 / (runs + 1)  // Prefer untested patterns
 * - exploitation_factor = (votes + 10)     // Prefer winners, but give everyone a chance
 */
function calculateSelectionWeight(pattern: Pattern): number {
  const explorationFactor = 100 / (pattern.number_of_runs + 1);
  const exploitationFactor = Math.max(1, pattern.votes + 10);

  return explorationFactor * exploitationFactor;
}

/**
 * Weighted random selection of patterns
 * Returns array of [patternA, patternB]
 */
export async function selectPatternsForCompetition(db: any): Promise<[Pattern, Pattern] | null> {
  try {
    // Get all patterns
    const result = await db.prepare(`
      SELECT pattern_id, name, conditions, votes, number_of_runs, annualized_roi_pct, origin
      FROM discovered_patterns
      WHERE tested = 1
      ORDER BY RANDOM()
      LIMIT 50
    `).all();

    const patterns: Pattern[] = result.results;

    if (patterns.length < 2) {
      console.log('⚠️  Not enough patterns for head-to-head (need at least 2)');
      return null;
    }

    // Calculate weights for all patterns
    const weights = patterns.map(p => calculateSelectionWeight(p));
    const totalWeight = weights.reduce((sum, w) => sum + w, 0);

    // Weighted random selection for pattern A
    let randomA = Math.random() * totalWeight;
    let indexA = 0;
    for (let i = 0; i < weights.length; i++) {
      randomA -= weights[i];
      if (randomA <= 0) {
        indexA = i;
        break;
      }
    }

    // Weighted random selection for pattern B (different from A)
    const remainingPatterns = patterns.filter((_, i) => i !== indexA);
    const remainingWeights = weights.filter((_, i) => i !== indexA);
    const remainingTotalWeight = remainingWeights.reduce((sum, w) => sum + w, 0);

    let randomB = Math.random() * remainingTotalWeight;
    let indexB = 0;
    for (let i = 0; i < remainingWeights.length; i++) {
      randomB -= remainingWeights[i];
      if (randomB <= 0) {
        indexB = i;
        break;
      }
    }

    const patternA = patterns[indexA];
    const patternB = remainingPatterns[indexB];

    console.log(`🎲 Selected for competition:`);
    console.log(`  A: ${patternA.name} (runs: ${patternA.number_of_runs}, votes: ${patternA.votes}, weight: ${weights[indexA].toFixed(1)})`);
    console.log(`  B: ${patternB.name} (runs: ${remainingPatterns[indexB] ? 'unknown' : patternB.number_of_runs}, votes: ${patternB.votes})`);

    return [patternA, patternB];

  } catch (error) {
    console.error('Failed to select patterns:', error);
    return null;
  }
}

/**
 * Select random timeframe with weighted preference for longer periods
 */
function selectRandomTimeframe(): typeof TIMEFRAMES[0] {
  // Weight longer timeframes slightly higher
  const weights = TIMEFRAMES.map(tf => Math.pow(tf.bonus, 1.5));
  const totalWeight = weights.reduce((sum, w) => sum + w, 0);

  let random = Math.random() * totalWeight;
  for (let i = 0; i < TIMEFRAMES.length; i++) {
    random -= weights[i];
    if (random <= 0) {
      return TIMEFRAMES[i];
    }
  }

  return TIMEFRAMES[TIMEFRAMES.length - 1];
}

/**
 * Test a strategy on historical data
 * Returns simulated performance
 */
async function testStrategy(pattern: Pattern, timeframe: typeof TIMEFRAMES[0], db: any): Promise<TestResult> {
  try {
    // Get random historical trades for testing
    const tradesResult = await db.prepare(`
      SELECT entry_price, exit_price, pnl_pct, buy_state, sell_state
      FROM chaos_trades
      ORDER BY RANDOM()
      LIMIT 100
    `).all();

    if (!tradesResult.results || tradesResult.results.length === 0) {
      throw new Error('No historical trades available');
    }

    const trades = tradesResult.results;
    const conditions = JSON.parse(pattern.conditions);

    // Simulate strategy performance
    let totalReturn = 0;
    let tradesMatched = 0;

    for (const trade of trades) {
      const buyState = JSON.parse(trade.buy_state);

      // Check if trade matches pattern conditions (simplified)
      let matches = true;

      if (conditions.momentum1tick !== undefined) {
        const threshold = conditions.momentum1tick.threshold || 0.001;
        if (Math.abs(buyState.momentum1tick - conditions.momentum1tick.target) > threshold) {
          matches = false;
        }
      }

      if (conditions.volatility !== undefined && matches) {
        const threshold = conditions.volatility.threshold || 0.001;
        if (Math.abs(buyState.volatility - conditions.volatility.target) > threshold) {
          matches = false;
        }
      }

      if (matches) {
        totalReturn += trade.pnl_pct;
        tradesMatched++;
      }
    }

    // Calculate metrics
    const avgReturn = tradesMatched > 0 ? totalReturn / tradesMatched : 0;
    const endingValue = 1 + (avgReturn / 100);

    // Annualize based on timeframe
    const tradesPerYear = (365 * 24 * 60) / timeframe.minutes;
    const annualizedRoi = avgReturn * tradesPerYear;

    return {
      patternId: pattern.pattern_id,
      roi: avgReturn,
      annualizedRoi,
      endingValue
    };

  } catch (error) {
    console.error(`Failed to test strategy ${pattern.name}:`, error);
    return {
      patternId: pattern.pattern_id,
      roi: 0,
      annualizedRoi: 0,
      endingValue: 1
    };
  }
}

/**
 * Run head-to-head competition between two patterns
 */
export async function runHeadToHeadCompetition(db: any): Promise<boolean> {
  console.log('⚔️  Starting head-to-head competition...');

  try {
    // Select two patterns
    const selection = await selectPatternsForCompetition(db);
    if (!selection) {
      return false;
    }

    const [patternA, patternB] = selection;

    // Select random timeframe
    const timeframe = selectRandomTimeframe();
    console.log(`⏱️  Timeframe: ${timeframe.name} (bonus: ${timeframe.bonus}x)`);

    // Test both strategies
    console.log('🧪 Testing pattern A...');
    const resultA = await testStrategy(patternA, timeframe, db);

    console.log('🧪 Testing pattern B...');
    const resultB = await testStrategy(patternB, timeframe, db);

    // Apply timeframe bonus
    const scoreA = resultA.annualizedRoi * timeframe.bonus;
    const scoreB = resultB.annualizedRoi * timeframe.bonus;

    // Determine winner
    const winnerId = scoreA > scoreB ? patternA.pattern_id : patternB.pattern_id;
    const loserId = scoreA > scoreB ? patternB.pattern_id : patternA.pattern_id;

    console.log(`📊 Results:`);
    console.log(`  ${patternA.name}: ${resultA.annualizedRoi.toFixed(2)}% × ${timeframe.bonus} = ${scoreA.toFixed(2)}%`);
    console.log(`  ${patternB.name}: ${resultB.annualizedRoi.toFixed(2)}% × ${timeframe.bonus} = ${scoreB.toFixed(2)}%`);
    console.log(`  🏆 Winner: ${scoreA > scoreB ? patternA.name : patternB.name}`);

    // Update database
    // Winner: +1 vote, +1 h2h_win
    await db.prepare(`
      UPDATE discovered_patterns
      SET votes = votes + 1,
          head_to_head_wins = head_to_head_wins + 1,
          last_tested_at = datetime('now')
      WHERE pattern_id = ?
    `).bind(winnerId).run();

    // Loser: -1 vote, +1 h2h_loss
    await db.prepare(`
      UPDATE discovered_patterns
      SET votes = votes - 1,
          head_to_head_losses = head_to_head_losses + 1,
          last_tested_at = datetime('now')
      WHERE pattern_id = ?
    `).bind(loserId).run();

    // Record matchup
    await db.prepare(`
      INSERT INTO h2h_matchups (
        pattern_a_id, pattern_b_id, timeframe,
        pattern_a_roi, pattern_b_roi, timeframe_bonus, winner_id
      ) VALUES (?, ?, ?, ?, ?, ?, ?)
    `).bind(
      patternA.pattern_id,
      patternB.pattern_id,
      timeframe.name,
      resultA.annualizedRoi,
      resultB.annualizedRoi,
      timeframe.bonus,
      winnerId
    ).run();

    console.log('✅ Competition complete, results recorded');
    return true;

  } catch (error) {
    console.error('❌ Head-to-head competition failed:', error);
    return false;
  }
}
