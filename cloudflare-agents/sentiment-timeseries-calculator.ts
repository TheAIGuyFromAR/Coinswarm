/**
 * Sentiment Time-Series Calculator
 *
 * Calculates sentiment derivatives (velocity, acceleration, jerk) from historical snapshots.
 * Enables pattern discovery like:
 * - "RSI oversold + sentiment jerk positive = 84% win"
 * - "Price rising + sentiment velocity negative = reversal imminent"
 * - "Extreme fear + sentiment acceleration positive = capitulation ending"
 */

export interface SentimentSnapshot {
  timestamp: string;
  sentiment: number; // -1 to +1
  fear_greed: number; // 0-100
}

export interface SentimentDerivatives {
  // Current state
  sentiment: number;
  fear_greed: number;

  // Historical context
  sentiment_1hr_ago: number | null;
  sentiment_4hr_ago: number | null;
  sentiment_24hr_ago: number | null;

  // Direction (qualitative)
  direction: 'improving' | 'declining' | 'stable';

  // Derivatives (quantitative)
  velocity: number | null; // 1st derivative: ΔS/Δt (change per hour)
  acceleration: number | null; // 2nd derivative: Δ²S/Δt²
  jerk: number | null; // 3rd derivative: Δ³S/Δt³
}

export interface NewsContext {
  keywords: string[];
  headlines_1hr: string[];
  headlines_24hr: string[];
  volume_1hr: number;
  volume_24hr: number;
  sentiment_1hr: number | null;
  sentiment_24hr: number | null;
  sentiment_spread: number | null; // Standard deviation
}

/**
 * Calculate sentiment derivatives from time-series data
 */
export function calculateSentimentDerivatives(
  current: SentimentSnapshot,
  snapshots_1hr_ago: SentimentSnapshot[],
  snapshots_4hr_ago: SentimentSnapshot[],
  snapshots_24hr_ago: SentimentSnapshot[]
): SentimentDerivatives {

  // Get historical values (average if multiple snapshots in window)
  const sentiment_1hr_ago = average(snapshots_1hr_ago.map(s => s.sentiment));
  const sentiment_4hr_ago = average(snapshots_4hr_ago.map(s => s.sentiment));
  const sentiment_24hr_ago = average(snapshots_24hr_ago.map(s => s.sentiment));

  // Calculate velocity (1st derivative) - change per hour
  let velocity: number | null = null;
  if (sentiment_1hr_ago !== null) {
    velocity = current.sentiment - sentiment_1hr_ago; // Already per hour
  }

  // Calculate acceleration (2nd derivative) - change in velocity per hour
  let acceleration: number | null = null;
  if (velocity !== null && sentiment_4hr_ago !== null) {
    // Velocity 3 hours ago (using 4hr and 1hr snapshots)
    const velocity_3hr_ago = sentiment_1hr_ago - sentiment_4hr_ago;
    acceleration = (velocity - velocity_3hr_ago) / 3; // Spread over 3 hours
  }

  // Calculate jerk (3rd derivative) - change in acceleration per hour
  let jerk: number | null = null;
  if (acceleration !== null && sentiment_24hr_ago !== null) {
    // Need to calculate acceleration at an earlier time
    // Use 12hr ago and 24hr ago to get historical acceleration
    const sentiment_12hr_ago = average([
      ...snapshots_4hr_ago.map(s => s.sentiment),
      ...snapshots_24hr_ago.map(s => s.sentiment)
    ].filter(s => s !== null));

    if (sentiment_12hr_ago !== null) {
      const velocity_12hr_ago = sentiment_4hr_ago - sentiment_12hr_ago;
      const velocity_24hr_ago = sentiment_12hr_ago - sentiment_24hr_ago;
      const acceleration_18hr_ago = (velocity_12hr_ago - velocity_24hr_ago) / 12;

      jerk = (acceleration - acceleration_18hr_ago) / 18; // Spread over 18 hours
    }
  }

  // Determine direction
  let direction: 'improving' | 'declining' | 'stable' = 'stable';
  if (velocity !== null) {
    if (velocity > 0.03) direction = 'improving';
    else if (velocity < -0.03) direction = 'declining';
  }

  return {
    sentiment: current.sentiment,
    fear_greed: current.fear_greed,
    sentiment_1hr_ago,
    sentiment_4hr_ago,
    sentiment_24hr_ago,
    direction,
    velocity,
    acceleration,
    jerk
  };
}

/**
 * Extract keywords from news articles
 */
export function extractKeywords(articles: { title: string; body?: string }[]): string[] {
  // Common crypto keywords to track
  const keywordPatterns = [
    // Regulatory
    'regulation', 'sec', 'fda', 'ban', 'legal', 'lawsuit', 'etf', 'approval',
    // Market events
    'hack', 'exploit', 'crash', 'rally', 'ath', 'all-time high', 'bottom',
    // Institutional
    'institutional', 'blackrock', 'fidelity', 'grayscale', 'microstrategy',
    // Technical
    'upgrade', 'fork', 'halving', 'merge', 'scaling', 'layer 2',
    // Sentiment
    'bullish', 'bearish', 'fud', 'fomo', 'moon', 'rekt',
    // Macro
    'fed', 'interest rate', 'inflation', 'recession', 'dollar'
  ];

  const keywords = new Set<string>();

  for (const article of articles) {
    const text = `${article.title} ${article.body || ''}`.toLowerCase();

    for (const pattern of keywordPatterns) {
      if (text.includes(pattern.toLowerCase())) {
        keywords.add(pattern);
      }
    }
  }

  return Array.from(keywords);
}

/**
 * Calculate news context from articles
 */
export function calculateNewsContext(
  articles_1hr: { title: string; body?: string; sentiment?: number; published_on: number }[],
  articles_24hr: { title: string; body?: string; sentiment?: number; published_on: number }[]
): NewsContext {

  const keywords = extractKeywords([...articles_1hr, ...articles_24hr]);

  const headlines_1hr = articles_1hr.map(a => a.title);
  const headlines_24hr = articles_24hr.map(a => a.title);

  const volume_1hr = articles_1hr.length;
  const volume_24hr = articles_24hr.length;

  const sentiments_1hr = articles_1hr
    .map(a => a.sentiment)
    .filter(s => s !== undefined && s !== null) as number[];

  const sentiments_24hr = articles_24hr
    .map(a => a.sentiment)
    .filter(s => s !== undefined && s !== null) as number[];

  const sentiment_1hr = sentiments_1hr.length > 0
    ? sentiments_1hr.reduce((sum, s) => sum + s, 0) / sentiments_1hr.length
    : null;

  const sentiment_24hr = sentiments_24hr.length > 0
    ? sentiments_24hr.reduce((sum, s) => sum + s, 0) / sentiments_24hr.length
    : null;

  // Calculate sentiment spread (standard deviation)
  let sentiment_spread: number | null = null;
  if (sentiments_24hr.length > 1 && sentiment_24hr !== null) {
    const variance = sentiments_24hr
      .map(s => Math.pow(s - sentiment_24hr, 2))
      .reduce((sum, v) => sum + v, 0) / sentiments_24hr.length;
    sentiment_spread = Math.sqrt(variance);
  }

  return {
    keywords,
    headlines_1hr,
    headlines_24hr,
    volume_1hr,
    volume_24hr,
    sentiment_1hr,
    sentiment_24hr,
    sentiment_spread
  };
}

/**
 * Helper: Calculate average of numbers (handles nulls)
 */
function average(values: (number | null)[]): number | null {
  const valid = values.filter(v => v !== null) as number[];
  if (valid.length === 0) return null;
  return valid.reduce((sum, v) => sum + v, 0) / valid.length;
}

/**
 * Classify derivatives for pattern matching
 */
export interface DerivativeClassifications {
  velocity_class: 'rapidly_improving' | 'improving' | 'stable' | 'declining' | 'rapidly_declining';
  acceleration_class: 'accelerating_improvement' | 'slight_acceleration' | 'constant' | 'slight_deceleration' | 'accelerating_decline';
  jerk_class: 'positive' | 'neutral' | 'negative';
}

export function classifyDerivatives(derivatives: SentimentDerivatives): DerivativeClassifications {
  let velocity_class: DerivativeClassifications['velocity_class'] = 'stable';
  if (derivatives.velocity !== null) {
    if (derivatives.velocity > 0.1) velocity_class = 'rapidly_improving';
    else if (derivatives.velocity > 0.03) velocity_class = 'improving';
    else if (derivatives.velocity < -0.1) velocity_class = 'rapidly_declining';
    else if (derivatives.velocity < -0.03) velocity_class = 'declining';
  }

  let acceleration_class: DerivativeClassifications['acceleration_class'] = 'constant';
  if (derivatives.acceleration !== null) {
    if (derivatives.acceleration > 0.05) acceleration_class = 'accelerating_improvement';
    else if (derivatives.acceleration > 0) acceleration_class = 'slight_acceleration';
    else if (derivatives.acceleration < -0.05) acceleration_class = 'accelerating_decline';
    else if (derivatives.acceleration < 0) acceleration_class = 'slight_deceleration';
  }

  let jerk_class: DerivativeClassifications['jerk_class'] = 'neutral';
  if (derivatives.jerk !== null) {
    if (derivatives.jerk > 0.01) jerk_class = 'positive';
    else if (derivatives.jerk < -0.01) jerk_class = 'negative';
  }

  return { velocity_class, acceleration_class, jerk_class };
}

/**
 * Example pattern discovery queries:
 *
 * 1. Contrarian signals (sentiment improving while price falling):
 *    WHERE sentiment_velocity > 0.05 AND entry_momentum_1 < -0.01
 *
 * 2. Early rally detection (acceleration turning positive):
 *    WHERE sentiment_acceleration > 0.02 AND entry_rsi_14 < 40
 *
 * 3. Momentum fading (positive velocity but negative jerk):
 *    WHERE sentiment_velocity > 0 AND sentiment_jerk < -0.01
 *
 * 4. Capitulation ending (extreme fear with improving acceleration):
 *    WHERE sentiment_fear_greed < 25 AND sentiment_acceleration > 0.05
 *
 * 5. News spike + positive sentiment:
 *    WHERE news_volume_1hr >= 5 AND news_sentiment_1hr > 0.5
 */
