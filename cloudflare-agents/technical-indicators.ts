/**
 * Technical Indicators Calculator
 *
 * Calculates ALL possible technical indicators for each chaos trade
 * to find which combinations correlate with successful outcomes
 */

export interface CandleData {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface TechnicalIndicators {
  // RSI
  rsi_14: number;
  rsi_oversold: boolean;  // RSI < 30
  rsi_overbought: boolean;  // RSI > 70

  // MACD
  macd_line: number;
  macd_signal: number;
  macd_histogram: number;
  macd_bullish_cross: boolean;
  macd_bearish_cross: boolean;

  // Bollinger Bands
  bb_upper: number;
  bb_middle: number;
  bb_lower: number;
  bb_position: number;  // -1 to 1 (where price is relative to bands)
  bb_squeeze: boolean;  // Bands are narrow (low volatility)
  bb_at_lower: boolean;  // Price near lower band
  bb_at_upper: boolean;  // Price near upper band

  // Moving Averages
  sma_10: number;
  sma_50: number;
  sma_200: number;
  ema_10: number;
  ema_50: number;
  price_vs_sma10: number;  // Percentage above/below
  price_vs_sma50: number;
  price_vs_sma200: number;
  above_sma10: boolean;
  above_sma50: boolean;
  above_sma200: boolean;
  golden_cross: boolean;  // SMA50 > SMA200
  death_cross: boolean;   // SMA50 < SMA200

  // Stochastic Oscillator
  stoch_k: number;
  stoch_d: number;
  stoch_oversold: boolean;  // %K < 20
  stoch_overbought: boolean;  // %K > 80
  stoch_bullish_cross: boolean;
  stoch_bearish_cross: boolean;

  // ATR (Volatility)
  atr_14: number;
  volatility_regime: 'low' | 'medium' | 'high';

  // Volume
  volume: number;
  volume_sma_20: number;
  volume_vs_avg: number;
  volume_spike: boolean;  // Volume > 2x average
  volume_dry: boolean;    // Volume < 0.5x average

  // Momentum
  momentum_1: number;   // 1-candle momentum
  momentum_5: number;   // 5-candle momentum
  momentum_10: number;  // 10-candle momentum
  momentum_positive: boolean;
  momentum_strong: boolean;  // abs(momentum_5) > 0.02

  // Trend
  trend_regime: 'uptrend' | 'downtrend' | 'sideways';
  higher_highs: boolean;
  lower_lows: boolean;

  // Temporal Features
  day_of_week: number;  // 0=Monday, 6=Sunday
  hour_of_day: number;  // 0-23
  month: number;        // 1-12
  week_of_month: number;  // 1-4
  is_weekend: boolean;
  is_monday: boolean;
  is_tuesday: boolean;
  is_wednesday: boolean;
  is_thursday: boolean;
  is_friday: boolean;
  is_market_hours: boolean;  // 9am-4pm EST

  // Support/Resistance
  near_recent_high: boolean;  // Within 1% of 50-candle high
  near_recent_low: boolean;   // Within 1% of 50-candle low
  at_resistance: boolean;
  at_support: boolean;
}

/**
 * Calculate RSI (Relative Strength Index)
 */
export function calculateRSI(candles: CandleData[], period: number = 14, index: number): number {
  if (index < period) return 50; // Not enough data

  let gains = 0;
  let losses = 0;

  for (let i = index - period + 1; i <= index; i++) {
    const change = candles[i].close - candles[i - 1].close;
    if (change > 0) {
      gains += change;
    } else {
      losses += Math.abs(change);
    }
  }

  const avgGain = gains / period;
  const avgLoss = losses / period;

  if (avgLoss === 0) return 100;

  const rs = avgGain / avgLoss;
  return 100 - (100 / (1 + rs));
}

/**
 * Calculate MACD (Moving Average Convergence Divergence)
 */
export function calculateMACD(candles: CandleData[], index: number): {
  macd: number;
  signal: number;
  histogram: number;
} {
  const ema12 = calculateEMA(candles, 12, index);
  const ema26 = calculateEMA(candles, 26, index);
  const macd = ema12 - ema26;

  // Calculate signal line (9-period EMA of MACD)
  // Simplified: use last 9 MACD values
  const signal = macd; // Simplified for now
  const histogram = macd - signal;

  return { macd, signal, histogram };
}

/**
 * Calculate EMA (Exponential Moving Average)
 */
export function calculateEMA(candles: CandleData[], period: number, index: number): number {
  if (index < period) {
    // Fall back to SMA
    return calculateSMA(candles, period, index);
  }

  const multiplier = 2 / (period + 1);
  let ema = calculateSMA(candles, period, index - period);

  for (let i = index - period + 1; i <= index; i++) {
    ema = (candles[i].close - ema) * multiplier + ema;
  }

  return ema;
}

/**
 * Calculate SMA (Simple Moving Average)
 */
export function calculateSMA(candles: CandleData[], period: number, index: number): number {
  const start = Math.max(0, index - period + 1);
  const slice = candles.slice(start, index + 1);
  const sum = slice.reduce((acc, c) => acc + c.close, 0);
  return sum / slice.length;
}

/**
 * Calculate Bollinger Bands
 */
export function calculateBollingerBands(candles: CandleData[], period: number, stdDev: number, index: number): {
  upper: number;
  middle: number;
  lower: number;
} {
  const middle = calculateSMA(candles, period, index);

  // Calculate standard deviation
  const start = Math.max(0, index - period + 1);
  const slice = candles.slice(start, index + 1);
  const variance = slice.reduce((acc, c) => acc + Math.pow(c.close - middle, 2), 0) / slice.length;
  const std = Math.sqrt(variance);

  return {
    upper: middle + (stdDev * std),
    middle,
    lower: middle - (stdDev * std)
  };
}

/**
 * Calculate Stochastic Oscillator
 */
export function calculateStochastic(candles: CandleData[], period: number, index: number): {
  k: number;
  d: number;
} {
  if (index < period) return { k: 50, d: 50 };

  const start = index - period + 1;
  const slice = candles.slice(start, index + 1);

  const highest = Math.max(...slice.map(c => c.high));
  const lowest = Math.min(...slice.map(c => c.low));
  const current = candles[index].close;

  const k = lowest === highest ? 50 : ((current - lowest) / (highest - lowest)) * 100;
  const d = k; // Simplified: should be 3-period SMA of %K

  return { k, d };
}

/**
 * Calculate ATR (Average True Range)
 */
export function calculateATR(candles: CandleData[], period: number, index: number): number {
  if (index < period) return 0;

  let trSum = 0;
  for (let i = index - period + 1; i <= index; i++) {
    const high = candles[i].high;
    const low = candles[i].low;
    const prevClose = i > 0 ? candles[i - 1].close : candles[i].close;

    const tr = Math.max(
      high - low,
      Math.abs(high - prevClose),
      Math.abs(low - prevClose)
    );

    trSum += tr;
  }

  return trSum / period;
}

/**
 * Calculate ALL technical indicators for a given candle
 */
export function calculateAllIndicators(candles: CandleData[], index: number): TechnicalIndicators {
  const current = candles[index];
  const timestamp = current.timestamp;
  const date = new Date(timestamp);

  // RSI
  const rsi_14 = calculateRSI(candles, 14, index);
  const rsi_oversold = rsi_14 < 30;
  const rsi_overbought = rsi_14 > 70;

  // MACD
  const macd = calculateMACD(candles, index);
  const prevMACD = index > 0 ? calculateMACD(candles, index - 1) : macd;
  const macd_bullish_cross = macd.macd > macd.signal && prevMACD.macd <= prevMACD.signal;
  const macd_bearish_cross = macd.macd < macd.signal && prevMACD.macd >= prevMACD.signal;

  // Bollinger Bands
  const bb = calculateBollingerBands(candles, 20, 2, index);
  const bb_width = bb.upper - bb.lower;
  const bb_position = bb_width > 0 ? (current.close - bb.lower) / bb_width : 0.5;
  const bb_squeeze = bb_width / bb.middle < 0.1;
  const bb_at_lower = bb_position < 0.1;
  const bb_at_upper = bb_position > 0.9;

  // Moving Averages
  const sma_10 = calculateSMA(candles, 10, index);
  const sma_50 = calculateSMA(candles, 50, index);
  const sma_200 = calculateSMA(candles, 200, index);
  const ema_10 = calculateEMA(candles, 10, index);
  const ema_50 = calculateEMA(candles, 50, index);

  const price_vs_sma10 = (current.close - sma_10) / sma_10;
  const price_vs_sma50 = (current.close - sma_50) / sma_50;
  const price_vs_sma200 = (current.close - sma_200) / sma_200;

  const above_sma10 = current.close > sma_10;
  const above_sma50 = current.close > sma_50;
  const above_sma200 = current.close > sma_200;
  const golden_cross = sma_50 > sma_200;
  const death_cross = sma_50 < sma_200;

  // Stochastic
  const stoch = calculateStochastic(candles, 14, index);
  const stoch_oversold = stoch.k < 20;
  const stoch_overbought = stoch.k > 80;
  const prevStoch = index > 0 ? calculateStochastic(candles, 14, index - 1) : stoch;
  const stoch_bullish_cross = stoch.k > stoch.d && prevStoch.k <= prevStoch.d;
  const stoch_bearish_cross = stoch.k < stoch.d && prevStoch.k >= prevStoch.d;

  // ATR
  const atr_14 = calculateATR(candles, 14, index);
  const atr_pct = atr_14 / current.close;
  let volatility_regime: 'low' | 'medium' | 'high' = 'medium';
  if (atr_pct < 0.01) volatility_regime = 'low';
  if (atr_pct > 0.03) volatility_regime = 'high';

  // Volume
  const volume_sma_20 = candles.slice(Math.max(0, index - 19), index + 1)
    .reduce((sum, c) => sum + c.volume, 0) / Math.min(20, index + 1);
  const volume_vs_avg = volume_sma_20 > 0 ? current.volume / volume_sma_20 : 1;
  const volume_spike = volume_vs_avg > 2;
  const volume_dry = volume_vs_avg < 0.5;

  // Momentum
  const momentum_1 = index >= 1 ? (current.close - candles[index - 1].close) / candles[index - 1].close : 0;
  const momentum_5 = index >= 5 ? (current.close - candles[index - 5].close) / candles[index - 5].close : 0;
  const momentum_10 = index >= 10 ? (current.close - candles[index - 10].close) / candles[index - 10].close : 0;
  const momentum_positive = momentum_5 > 0;
  const momentum_strong = Math.abs(momentum_5) > 0.02;

  // Trend
  const last20 = candles.slice(Math.max(0, index - 19), index + 1);
  const highs = last20.map(c => c.high);
  const lows = last20.map(c => c.low);
  const higher_highs = highs[highs.length - 1] > highs[0];
  const lower_lows = lows[lows.length - 1] < lows[0];

  let trend_regime: 'uptrend' | 'downtrend' | 'sideways' = 'sideways';
  if (above_sma50 && momentum_5 > 0.01) trend_regime = 'uptrend';
  if (!above_sma50 && momentum_5 < -0.01) trend_regime = 'downtrend';

  // Temporal
  const day_of_week = date.getUTCDay(); // 0=Sunday, 1=Monday, etc.
  const hour_of_day = date.getUTCHours();
  const month = date.getUTCMonth() + 1;
  const day_of_month = date.getUTCDate();
  const week_of_month = Math.ceil(day_of_month / 7);

  const is_weekend = day_of_week === 0 || day_of_week === 6;
  const is_monday = day_of_week === 1;
  const is_tuesday = day_of_week === 2;
  const is_wednesday = day_of_week === 3;
  const is_thursday = day_of_week === 4;
  const is_friday = day_of_week === 5;
  const is_market_hours = hour_of_day >= 14 && hour_of_day < 21; // 9am-4pm EST in UTC

  // Support/Resistance
  const last50 = candles.slice(Math.max(0, index - 49), index + 1);
  const recent_high = Math.max(...last50.map(c => c.high));
  const recent_low = Math.min(...last50.map(c => c.low));
  const near_recent_high = current.close > recent_high * 0.99;
  const near_recent_low = current.close < recent_low * 1.01;
  const at_resistance = near_recent_high;
  const at_support = near_recent_low;

  return {
    rsi_14,
    rsi_oversold,
    rsi_overbought,
    macd_line: macd.macd,
    macd_signal: macd.signal,
    macd_histogram: macd.histogram,
    macd_bullish_cross,
    macd_bearish_cross,
    bb_upper: bb.upper,
    bb_middle: bb.middle,
    bb_lower: bb.lower,
    bb_position,
    bb_squeeze,
    bb_at_lower,
    bb_at_upper,
    sma_10,
    sma_50,
    sma_200,
    ema_10,
    ema_50,
    price_vs_sma10,
    price_vs_sma50,
    price_vs_sma200,
    above_sma10,
    above_sma50,
    above_sma200,
    golden_cross,
    death_cross,
    stoch_k: stoch.k,
    stoch_d: stoch.d,
    stoch_oversold,
    stoch_overbought,
    stoch_bullish_cross,
    stoch_bearish_cross,
    atr_14,
    volatility_regime,
    volume: current.volume,
    volume_sma_20,
    volume_vs_avg,
    volume_spike,
    volume_dry,
    momentum_1,
    momentum_5,
    momentum_10,
    momentum_positive,
    momentum_strong,
    trend_regime,
    higher_highs,
    lower_lows,
    day_of_week,
    hour_of_day,
    month,
    week_of_month,
    is_weekend,
    is_monday,
    is_tuesday,
    is_wednesday,
    is_thursday,
    is_friday,
    is_market_hours,
    near_recent_high,
    near_recent_low,
    at_resistance,
    at_support
  };
}

/**
 * Generate human-readable rationalization for why this trade might have been made
 */
export function generateTradeRationalization(indicators: TechnicalIndicators, action: 'BUY' | 'SELL'): string[] {
  const reasons: string[] = [];

  if (action === 'BUY') {
    if (indicators.rsi_oversold) reasons.push('RSI oversold (<30) - potential bounce');
    if (indicators.macd_bullish_cross) reasons.push('MACD bullish crossover');
    if (indicators.stoch_oversold) reasons.push('Stochastic oversold - reversal signal');
    if (indicators.bb_at_lower) reasons.push('Price at lower Bollinger Band - oversold');
    if (indicators.at_support) reasons.push('Price at support level');
    if (indicators.momentum_positive && indicators.above_sma50) reasons.push('Positive momentum with uptrend');
    if (indicators.golden_cross) reasons.push('Golden cross (SMA50 > SMA200)');
    if (indicators.volume_spike && indicators.momentum_positive) reasons.push('Volume spike with positive momentum');
    if (indicators.is_tuesday && indicators.hour_of_day === 15) reasons.push('Tuesday 3pm - historically favorable');
    if (indicators.month === 10) reasons.push('October effect - seasonal pattern');
  } else {
    if (indicators.rsi_overbought) reasons.push('RSI overbought (>70) - potential reversal');
    if (indicators.macd_bearish_cross) reasons.push('MACD bearish crossover');
    if (indicators.stoch_overbought) reasons.push('Stochastic overbought - reversal signal');
    if (indicators.bb_at_upper) reasons.push('Price at upper Bollinger Band - overbought');
    if (indicators.at_resistance) reasons.push('Price at resistance level');
    if (!indicators.momentum_positive && !indicators.above_sma50) reasons.push('Negative momentum with downtrend');
    if (indicators.death_cross) reasons.push('Death cross (SMA50 < SMA200)');
    if (indicators.volume_dry) reasons.push('Low volume - weak support');
  }

  if (reasons.length === 0) {
    reasons.push('Random chaos trade - no clear technical signal');
  }

  return reasons;
}
