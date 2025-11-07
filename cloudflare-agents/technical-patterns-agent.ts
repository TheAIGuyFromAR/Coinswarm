/**
 * Technical Patterns Agent
 *
 * Implements classic technical analysis patterns and setups:
 * - Chart patterns (H&S, triangles, flags, wedges)
 * - Indicators (RSI, MACD, Bollinger Bands)
 * - Fibonacci retracements
 * - Volume patterns
 *
 * Generates variations with different parameters
 */

interface TechnicalSetup {
  name: string;
  description: string;
  type: 'chart_pattern' | 'indicator' | 'fibonacci' | 'volume';
  conditions: any;
  typical_success_rate: number;
}

/**
 * Classic technical analysis patterns
 */
const TECHNICAL_SETUPS: TechnicalSetup[] = [
  // Chart Patterns
  {
    name: "Head and Shoulders Top",
    description: "Bearish reversal: Left shoulder, head (higher), right shoulder, neckline break",
    type: 'chart_pattern',
    conditions: {
      structure: "Three peaks, middle highest",
      entry: "Break below neckline",
      target: "Neckline to head distance projected down"
    },
    typical_success_rate: 0.83
  },
  {
    name: "Double Bottom",
    description: "Bullish reversal: Two similar lows with resistance break",
    type: 'chart_pattern',
    conditions: {
      structure: "Two lows at similar price",
      entry: "Break above middle peak",
      target: "Bottom to peak distance projected up"
    },
    typical_success_rate: 0.78
  },
  {
    name: "Ascending Triangle",
    description: "Bullish continuation: Flat resistance, rising support",
    type: 'chart_pattern',
    conditions: {
      structure: "Higher lows, flat highs",
      entry: "Break above resistance",
      target: "Triangle height projected up"
    },
    typical_success_rate: 0.72
  },
  {
    name: "Bull Flag",
    description: "Bullish continuation: Strong move, consolidation, breakout",
    type: 'chart_pattern',
    conditions: {
      structure: "Steep rally, parallel channel down",
      entry: "Break above flag resistance",
      target: "Flagpole height projected up"
    },
    typical_success_rate: 0.68
  },
  {
    name: "Falling Wedge",
    description: "Bullish reversal: Converging trendlines, both declining",
    type: 'chart_pattern',
    conditions: {
      structure: "Lower highs and lows converging",
      entry: "Break above upper trendline",
      target: "Wedge height projected up"
    },
    typical_success_rate: 0.74
  },

  // Indicator-Based Patterns
  {
    name: "RSI Oversold Bounce",
    description: "Buy when RSI < 30, sell when RSI > 70",
    type: 'indicator',
    conditions: {
      entry: "RSI crosses above 30",
      exit: "RSI crosses above 70 or price +5%",
      timeframe: "4h or 1d"
    },
    typical_success_rate: 0.65
  },
  {
    name: "MACD Bullish Crossover",
    description: "MACD line crosses above signal line",
    type: 'indicator',
    conditions: {
      entry: "MACD crosses above signal, histogram positive",
      exit: "MACD crosses below signal",
      confirmation: "Price above 50 EMA"
    },
    typical_success_rate: 0.62
  },
  {
    name: "Bollinger Band Squeeze Breakout",
    description: "Low volatility followed by expansion",
    type: 'indicator',
    conditions: {
      setup: "BB width at 6-month low",
      entry: "Price breaks above upper band + volume spike",
      exit: "Price touches middle band or opposite band"
    },
    typical_success_rate: 0.71
  },
  {
    name: "Moving Average Golden Cross",
    description: "50 MA crosses above 200 MA (bullish)",
    type: 'indicator',
    conditions: {
      entry: "50 MA crosses above 200 MA",
      confirmation: "Both MAs trending up",
      exit: "50 MA crosses below 200 MA (death cross)"
    },
    typical_success_rate: 0.58
  },
  {
    name: "Stochastic RSI Oversold",
    description: "StochRSI < 20 in uptrend",
    type: 'indicator',
    conditions: {
      setup: "Price above 200 MA (uptrend)",
      entry: "StochRSI crosses above 20",
      exit: "StochRSI crosses above 80"
    },
    typical_success_rate: 0.67
  },

  // Fibonacci Patterns
  {
    name: "Fibonacci 61.8% Retracement Buy",
    description: "Buy at 61.8% retracement of prior move",
    type: 'fibonacci',
    conditions: {
      setup: "Strong move up, then pullback",
      entry: "Price bounces at 61.8% level",
      target: "161.8% extension"
    },
    typical_success_rate: 0.69
  },
  {
    name: "Fibonacci 38.2% Shallow Retracement",
    description: "Buy at 38.2% in strong trends",
    type: 'fibonacci',
    conditions: {
      setup: "Very strong trend",
      entry: "Bounce at 38.2% retracement",
      target: "New high/low"
    },
    typical_success_rate: 0.64
  },

  // Volume Patterns
  {
    name: "Volume Breakout Confirmation",
    description: "Price breakout with 2x average volume",
    type: 'volume',
    conditions: {
      setup: "Consolidation near resistance",
      entry: "Break resistance + volume > 2x average",
      exit: "Volume dries up or resistance rejection"
    },
    typical_success_rate: 0.73
  },
  {
    name: "Accumulation Volume Divergence",
    description: "Price flat but volume increasing (accumulation)",
    type: 'volume',
    conditions: {
      setup: "Price in range, volume trending up",
      entry: "Break above range",
      target: "Volume spike continuation"
    },
    typical_success_rate: 0.66
  },
  {
    name: "On-Balance Volume Breakout",
    description: "OBV breaks out before price",
    type: 'volume',
    conditions: {
      setup: "OBV making new highs, price still consolidating",
      entry: "Price follows OBV breakout",
      exit: "OBV divergence (price up, OBV down)"
    },
    typical_success_rate: 0.70
  }
];

/**
 * Generate variations of a technical setup using AI
 */
export async function generateTechnicalVariations(
  ai: any,
  setup: TechnicalSetup
): Promise<any[]> {

  const prompt = `You are an expert technical analyst. Create 3 specific trading patterns based on this setup for crypto day trading.

TECHNICAL SETUP:
Name: ${setup.name}
Description: ${setup.description}
Type: ${setup.type}
Conditions: ${JSON.stringify(setup.conditions)}
Historical Success Rate: ${(setup.typical_success_rate * 100).toFixed(0)}%

TASK: Generate 3 variations adapted for different crypto timeframes:
1. Short-term (5min-1hr holds) - Aggressive parameters
2. Medium-term (4hr-1day holds) - Standard parameters
3. Long-term (1day+ holds) - Conservative parameters

For each variation specify:
- momentum_threshold: How much momentum needed (-0.01 to 0.01)
- volatility_range: Acceptable volatility (0.01 to 0.05)
- volume_multiplier: Volume vs average (0.5 to 3.0)
- hold_duration_minutes: How long to hold (5 to 1440)
- stop_loss_pct: Stop loss percentage (1 to 10)
- take_profit_pct: Take profit percentage (2 to 20)

OUTPUT: Valid JSON array with these numeric fields.`;

  try {
    const response = await ai.run('@cf/meta/llama-3.1-8b-instruct', {
      messages: [
        {
          role: 'system',
          content: 'You are a technical analysis expert. Always respond in valid JSON format with numeric values.'
        },
        { role: 'user', content: prompt }
      ],
      temperature: 0.3,
      max_tokens: 1500
    });

    const result = JSON.parse(response.response || '[]');
    return Array.isArray(result) ? result : [];

  } catch (error) {
    console.error(`Failed to generate variations for ${setup.name}:`, error);
    return generateFallbackTechnicalVariations(setup);
  }
}

/**
 * Fallback: Generate basic technical variations without AI
 */
function generateFallbackTechnicalVariations(setup: TechnicalSetup): any[] {
  return [
    {
      name: `${setup.name} - Short`,
      timeframe: "5min-1hr",
      momentum_threshold: 0.003,
      volatility_range: 0.02,
      volume_multiplier: 1.5,
      hold_duration_minutes: 30,
      stop_loss_pct: 2,
      take_profit_pct: 4
    },
    {
      name: `${setup.name} - Medium`,
      timeframe: "4hr-1day",
      momentum_threshold: 0.001,
      volatility_range: 0.015,
      volume_multiplier: 1.2,
      hold_duration_minutes: 240,
      stop_loss_pct: 3,
      take_profit_pct: 8
    },
    {
      name: `${setup.name} - Long`,
      timeframe: "1day+",
      momentum_threshold: 0.0005,
      volatility_range: 0.01,
      volume_multiplier: 1.0,
      hold_duration_minutes: 1440,
      stop_loss_pct: 5,
      take_profit_pct: 15
    }
  ];
}

/**
 * Convert technical setup variation to pattern format
 */
export function convertToPattern(setup: TechnicalSetup, variation: any, origin: string = 'technical'): any {
  return {
    patternId: `${origin}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    name: `[Technical] ${variation.name || setup.name}`,
    conditions: {
      type: setup.type,
      setup_description: setup.description,
      ...variation,
      typical_success_rate: setup.typical_success_rate
    },
    winRate: setup.typical_success_rate,
    sampleSize: 0,
    discoveredAt: new Date().toISOString(),
    tested: 0,
    votes: 0,
    origin,
    sourceDetail: setup.name
  };
}

/**
 * Main technical patterns research cycle
 */
export async function runTechnicalResearch(ai: any, db: any): Promise<number> {
  console.log('📊 Technical Patterns Agent: Starting research cycle...');

  let patternsGenerated = 0;

  try {
    // Process 3 setups per cycle
    const setupsToProcess = TECHNICAL_SETUPS.slice(0, 3);

    for (const setup of setupsToProcess) {
      console.log(`📐 Processing: ${setup.name} (${setup.type})`);

      try {
        // Generate variations using AI
        const variations = await generateTechnicalVariations(ai, setup);
        console.log(`  ✓ Generated ${variations.length} variations`);

        // Convert to pattern format and store
        for (const variation of variations) {
          const pattern = convertToPattern(setup, variation, 'technical');

          await db.prepare(`
            INSERT OR IGNORE INTO discovered_patterns (
              pattern_id, name, conditions, win_rate, sample_size,
              discovered_at, tested, votes, origin, source_detail
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
          `).bind(
            pattern.patternId,
            pattern.name,
            JSON.stringify(pattern.conditions),
            pattern.winRate,
            pattern.sampleSize,
            pattern.discoveredAt,
            pattern.tested,
            pattern.votes,
            pattern.origin,
            pattern.sourceDetail
          ).run();

          patternsGenerated++;
        }

        console.log(`  ✓ Stored ${variations.length} patterns`);

      } catch (error) {
        console.error(`  ✗ Failed to process ${setup.name}:`, error);
      }
    }

    console.log(`✅ Technical research complete: ${patternsGenerated} patterns generated`);
    return patternsGenerated;

  } catch (error) {
    console.error('❌ Technical research failed:', error);
    return 0;
  }
}
