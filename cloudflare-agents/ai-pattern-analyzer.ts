/**
 * AI-Powered Pattern Analyzer
 *
 * Uses Cloudflare Workers AI to discover patterns in trading data
 * Enhances statistical analysis with LLM-based insights
 */

import { MarketState } from './evolution-agent';

export interface PatternInsight {
  patternName: string;
  confidence: number;
  description: string;
  conditions: any;
  reasoning: string;
}

/**
 * Analyze trading patterns using Cloudflare AI
 *
 * Sends winner vs loser statistics to an LLM to identify
 * non-obvious patterns and correlations
 */
export async function analyzeWithAI(
  ai: any,
  winnerStats: MarketState,
  loserStats: MarketState,
  sampleSize: number
): Promise<PatternInsight[]> {

  const prompt = `You are an expert quantitative trading analyst. Analyze this chaos trading data to discover profitable patterns.

WINNER STATISTICS (${Math.floor(sampleSize * 0.4)} profitable trades):
- Avg Price: $${winnerStats.price.toFixed(2)}
- Avg Momentum (1-tick): ${(winnerStats.momentum1tick * 100).toFixed(3)}%
- Avg Momentum (5-tick): ${(winnerStats.momentum5tick * 100).toFixed(3)}%
- Avg vs SMA10: ${(winnerStats.vsSma10 * 100).toFixed(3)}%
- Avg Volume vs Avg: ${winnerStats.volumeVsAvg.toFixed(3)}x
- Avg Volatility: ${(winnerStats.volatility * 100).toFixed(3)}%

LOSER STATISTICS (${Math.floor(sampleSize * 0.6)} losing trades):
- Avg Price: $${loserStats.price.toFixed(2)}
- Avg Momentum (1-tick): ${(loserStats.momentum1tick * 100).toFixed(3)}%
- Avg Momentum (5-tick): ${(loserStats.momentum5tick * 100).toFixed(3)}%
- Avg vs SMA10: ${(loserStats.vsSma10 * 100).toFixed(3)}%
- Avg Volume vs Avg: ${loserStats.volumeVsAvg.toFixed(3)}x
- Avg Volatility: ${(loserStats.volatility * 100).toFixed(3)}%

TASK: Identify 1-3 specific trading patterns that distinguish winners from losers.

For each pattern, provide:
1. Pattern name (short, descriptive)
2. Confidence (0-1, based on statistical significance)
3. Description (one sentence)
4. Key conditions (specific thresholds)
5. Reasoning (why this pattern might work)

Focus on patterns with the largest differences and statistical significance.

Respond in JSON format:
{
  "patterns": [
    {
      "name": "Pattern Name",
      "confidence": 0.75,
      "description": "Brief description",
      "conditions": {
        "feature": "threshold_value"
      },
      "reasoning": "Why this works"
    }
  ]
}`;

  try {
    // Use Cloudflare Workers AI with Llama model
    const response = await ai.run('@cf/meta/llama-3.1-8b-instruct', {
      messages: [
        { role: 'system', content: 'You are a quantitative trading analyst. Always respond in valid JSON format.' },
        { role: 'user', content: prompt }
      ],
      temperature: 0.3,  // Lower temperature for more consistent analysis
      max_tokens: 1000
    });

    // Parse AI response
    const result = JSON.parse(response.response || '{"patterns": []}');

    return result.patterns || [];

  } catch (error) {
    console.error('AI analysis failed:', error);
    return [];
  }
}

/**
 * Validate pattern suggestions from AI
 *
 * Ensures patterns meet minimum criteria:
 * - Confidence > 0.5
 * - Has actionable conditions
 * - Description is meaningful
 */
export function validatePattern(pattern: PatternInsight): boolean {
  if (pattern.confidence < 0.5) {
    return false;
  }

  if (!pattern.conditions || Object.keys(pattern.conditions).length === 0) {
    return false;
  }

  if (!pattern.description || pattern.description.length < 10) {
    return false;
  }

  return true;
}

/**
 * Score pattern quality based on AI confidence and statistical significance
 */
export function scorePattern(
  pattern: PatternInsight,
  statisticalDifference: number,
  sampleSize: number
): number {
  // Combine AI confidence with statistical significance
  const aiScore = pattern.confidence;
  const statsScore = Math.min(statisticalDifference * 10, 1.0);  // Cap at 1.0
  const sampleScore = Math.min(sampleSize / 1000, 1.0);  // Reward larger samples

  // Weighted average
  return aiScore * 0.5 + statsScore * 0.3 + sampleScore * 0.2;
}

/**
 * Generate pattern ID from name
 */
export function generatePatternId(patternName: string): string {
  const slug = patternName
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');

  return `${slug}-${Date.now()}`;
}
