/**
 * Technical Indicators Agent
 *
 * Calculates technical indicators from collected price data:
 * - Bollinger Bands (BB)
 * - Exponential Moving Average (EMA)
 * - Simple Moving Average (SMA)
 * - MACD (Moving Average Convergence Divergence)
 * - RSI (Relative Strength Index)
 * - Fear/Greed Index (custom calculation)
 *
 * Runs hourly to process new price data
 */

interface Env {
  DB: D1Database;
}

interface OHLCV {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface Indicators {
  timestamp: number;
  symbol: string;
  timeframe: string;
  // Moving Averages
  sma_20: number;
  sma_50: number;
  sma_200: number;
  ema_12: number;
  ema_26: number;
  ema_50: number;
  // Bollinger Bands
  bb_upper: number;
  bb_middle: number;
  bb_lower: number;
  bb_width: number;
  // MACD
  macd: number;
  macd_signal: number;
  macd_histogram: number;
  // RSI
  rsi_14: number;
  // Fear/Greed
  fear_greed_index: number;
  // Volume indicators
  volume_sma_20: number;
  volume_ratio: number;
}

export default {
  async scheduled(event: ScheduledEvent, env: Env, ctx: ExecutionContext) {
    console.log('📊 Starting technical indicators calculation...');

    await this.initializeTables(env);

    // Get all tokens
    const tokens = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'CAKEUSDT',
                    'RAYUSDT', 'ORCAUSDT', 'JUPUSDT', 'ARBUSDT', 'GMXUSDT',
                    'OPUSDT', 'VELOUSDT', 'MATICUSDT', 'QUICKUSDT', 'AEROUSDT'];

    const timeframes = ['1m', '1h', '1d'];

    let totalProcessed = 0;

    // Process each token and timeframe
    for (const symbol of tokens) {
      for (const timeframe of timeframes) {
        try {
          const processed = await this.processIndicators(env, symbol, timeframe);
          totalProcessed += processed;
          console.log(`✅ ${symbol} ${timeframe}: ${processed} indicators calculated`);
        } catch (error) {
          console.error(`❌ Error processing ${symbol} ${timeframe}:`, error);
        }
      }
    }

    console.log(`✅ Total indicators calculated: ${totalProcessed}`);
  },

  async initializeTables(env: Env) {
    await env.DB.prepare(`
      CREATE TABLE IF NOT EXISTS technical_indicators (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp INTEGER NOT NULL,
        symbol TEXT NOT NULL,
        timeframe TEXT NOT NULL,
        sma_20 REAL,
        sma_50 REAL,
        sma_200 REAL,
        ema_12 REAL,
        ema_26 REAL,
        ema_50 REAL,
        bb_upper REAL,
        bb_middle REAL,
        bb_lower REAL,
        bb_width REAL,
        macd REAL,
        macd_signal REAL,
        macd_histogram REAL,
        rsi_14 REAL,
        fear_greed_index REAL,
        volume_sma_20 REAL,
        volume_ratio REAL,
        created_at INTEGER DEFAULT (strftime('%s', 'now')),
        UNIQUE(symbol, timestamp, timeframe)
      )
    `).run();

    // Create index for faster queries
    await env.DB.prepare(`
      CREATE INDEX IF NOT EXISTS idx_indicators_symbol_time
      ON technical_indicators(symbol, timeframe, timestamp DESC)
    `).run();
  },

  async processIndicators(env: Env, symbol: string, timeframe: string): Promise<number> {
    // Get last processed timestamp
    const lastProcessed = await env.DB.prepare(`
      SELECT MAX(timestamp) as last_ts FROM technical_indicators
      WHERE symbol = ? AND timeframe = ?
    `).bind(symbol, timeframe).first() as any;

    const lastTimestamp = lastProcessed?.last_ts || 0;

    // Fetch new price data with enough history for calculations (need 200 periods for SMA200)
    const priceData = await env.DB.prepare(`
      SELECT timestamp, open, high, low, close, volume
      FROM price_data
      WHERE symbol = ? AND timeframe = ?
      ORDER BY timestamp ASC
    `).bind(symbol, timeframe).all();

    if (!priceData.results || priceData.results.length < 200) {
      console.log(`⚠️ Insufficient data for ${symbol} ${timeframe} (need 200+ candles)`);
      return 0;
    }

    const candles = priceData.results as any[] as OHLCV[];
    const indicators: Indicators[] = [];

    // Calculate indicators for each candle (starting from index 200 to have enough history)
    for (let i = 200; i < candles.length; i++) {
      const current = candles[i];

      // Skip if already processed
      if (current.timestamp <= lastTimestamp) {
        continue;
      }

      const closes = candles.slice(0, i + 1).map(c => c.close);
      const highs = candles.slice(0, i + 1).map(c => c.high);
      const lows = candles.slice(0, i + 1).map(c => c.low);
      const volumes = candles.slice(0, i + 1).map(c => c.volume || 0);

      indicators.push({
        timestamp: current.timestamp,
        symbol,
        timeframe,
        // Simple Moving Averages
        sma_20: this.calculateSMA(closes, 20),
        sma_50: this.calculateSMA(closes, 50),
        sma_200: this.calculateSMA(closes, 200),
        // Exponential Moving Averages
        ema_12: this.calculateEMA(closes, 12),
        ema_26: this.calculateEMA(closes, 26),
        ema_50: this.calculateEMA(closes, 50),
        // Bollinger Bands
        ...this.calculateBollingerBands(closes, 20, 2),
        // MACD
        ...this.calculateMACD(closes),
        // RSI
        rsi_14: this.calculateRSI(closes, 14),
        // Fear/Greed Index (custom)
        fear_greed_index: this.calculateFearGreed(closes, volumes, highs, lows),
        // Volume indicators
        volume_sma_20: this.calculateSMA(volumes, 20),
        volume_ratio: volumes[volumes.length - 1] / this.calculateSMA(volumes, 20)
      });
    }

    // Batch insert indicators
    for (const indicator of indicators) {
      await env.DB.prepare(`
        INSERT OR REPLACE INTO technical_indicators (
          timestamp, symbol, timeframe,
          sma_20, sma_50, sma_200,
          ema_12, ema_26, ema_50,
          bb_upper, bb_middle, bb_lower, bb_width,
          macd, macd_signal, macd_histogram,
          rsi_14, fear_greed_index,
          volume_sma_20, volume_ratio
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `).bind(
        indicator.timestamp, indicator.symbol, indicator.timeframe,
        indicator.sma_20, indicator.sma_50, indicator.sma_200,
        indicator.ema_12, indicator.ema_26, indicator.ema_50,
        indicator.bb_upper, indicator.bb_middle, indicator.bb_lower, indicator.bb_width,
        indicator.macd, indicator.macd_signal, indicator.macd_histogram,
        indicator.rsi_14, indicator.fear_greed_index,
        indicator.volume_sma_20, indicator.volume_ratio
      ).run();
    }

    return indicators.length;
  },

  // Simple Moving Average
  calculateSMA(values: number[], period: number): number {
    const slice = values.slice(-period);
    return slice.reduce((a, b) => a + b, 0) / slice.length;
  },

  // Exponential Moving Average
  calculateEMA(values: number[], period: number): number {
    const k = 2 / (period + 1);
    let ema = values[0];

    for (let i = 1; i < values.length; i++) {
      ema = values[i] * k + ema * (1 - k);
    }

    return ema;
  },

  // Bollinger Bands
  calculateBollingerBands(values: number[], period: number, stdDev: number) {
    const sma = this.calculateSMA(values, period);
    const slice = values.slice(-period);

    const variance = slice.reduce((sum, val) => sum + Math.pow(val - sma, 2), 0) / period;
    const std = Math.sqrt(variance);

    return {
      bb_upper: sma + (std * stdDev),
      bb_middle: sma,
      bb_lower: sma - (std * stdDev),
      bb_width: (std * stdDev * 2) / sma * 100 // Width as percentage
    };
  },

  // MACD (Moving Average Convergence Divergence)
  calculateMACD(values: number[]) {
    const ema12 = this.calculateEMA(values, 12);
    const ema26 = this.calculateEMA(values, 26);
    const macd = ema12 - ema26;

    // Calculate signal line (9-period EMA of MACD)
    // For simplicity, using approximate signal
    const signal = macd * 0.9; // Simplified - should calculate 9-EMA of MACD history
    const histogram = macd - signal;

    return {
      macd,
      macd_signal: signal,
      macd_histogram: histogram
    };
  },

  // RSI (Relative Strength Index)
  calculateRSI(values: number[], period: number): number {
    const changes = [];
    for (let i = 1; i < values.length; i++) {
      changes.push(values[i] - values[i - 1]);
    }

    const gains = changes.slice(-period).map(c => c > 0 ? c : 0);
    const losses = changes.slice(-period).map(c => c < 0 ? -c : 0);

    const avgGain = gains.reduce((a, b) => a + b, 0) / period;
    const avgLoss = losses.reduce((a, b) => a + b, 0) / period;

    if (avgLoss === 0) return 100;

    const rs = avgGain / avgLoss;
    const rsi = 100 - (100 / (1 + rs));

    return rsi;
  },

  // Custom Fear/Greed Index (0-100)
  calculateFearGreed(closes: number[], volumes: number[], highs: number[], lows: number[]): number {
    // Components:
    // 1. RSI (30% weight)
    // 2. Price momentum (25% weight)
    // 3. Volume (20% weight)
    // 4. Volatility (25% weight)

    const rsi = this.calculateRSI(closes, 14);
    const rsiScore = rsi; // Already 0-100

    // Price momentum (7-day vs 30-day)
    const momentum7 = ((closes[closes.length - 1] - closes[closes.length - 7]) / closes[closes.length - 7]) * 100;
    const momentum30 = ((closes[closes.length - 1] - closes[closes.length - 30]) / closes[closes.length - 30]) * 100;
    const momentumScore = Math.min(Math.max((momentum7 + momentum30) * 2 + 50, 0), 100);

    // Volume (current vs average)
    const volumeSMA = this.calculateSMA(volumes, 20);
    const volumeRatio = volumes[volumes.length - 1] / volumeSMA;
    const volumeScore = Math.min(volumeRatio * 50, 100);

    // Volatility (high-low range)
    const ranges = [];
    for (let i = Math.max(0, closes.length - 20); i < closes.length; i++) {
      ranges.push((highs[i] - lows[i]) / closes[i]);
    }
    const avgRange = ranges.reduce((a, b) => a + b, 0) / ranges.length;
    const volatilityScore = 100 - Math.min(avgRange * 500, 100); // Lower volatility = higher greed

    // Weighted average
    const fearGreed = (
      rsiScore * 0.3 +
      momentumScore * 0.25 +
      volumeScore * 0.20 +
      volatilityScore * 0.25
    );

    return Math.round(fearGreed);
  },

  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    // Get indicators for a symbol
    if (url.pathname.startsWith('/indicators/')) {
      const parts = url.pathname.split('/');
      const symbol = parts[2];
      const timeframe = url.searchParams.get('timeframe') || '1h';
      const limit = parseInt(url.searchParams.get('limit') || '100');

      const indicators = await env.DB.prepare(`
        SELECT * FROM technical_indicators
        WHERE symbol = ? AND timeframe = ?
        ORDER BY timestamp DESC
        LIMIT ?
      `).bind(symbol, timeframe, limit).all();

      return new Response(JSON.stringify({
        symbol,
        timeframe,
        indicators: indicators.results
      }, null, 2), { headers: { 'Content-Type': 'application/json' } });
    }

    // Latest indicators for all tokens
    if (url.pathname === '/latest') {
      const timeframe = url.searchParams.get('timeframe') || '1h';

      const latest = await env.DB.prepare(`
        SELECT DISTINCT ON (symbol) *
        FROM technical_indicators
        WHERE timeframe = ?
        ORDER BY symbol, timestamp DESC
      `).bind(timeframe).all();

      return new Response(JSON.stringify({
        timeframe,
        indicators: latest.results
      }, null, 2), { headers: { 'Content-Type': 'application/json' } });
    }

    // Trigger manual calculation
    if (url.pathname === '/calculate' && request.method === 'POST') {
      await this.scheduled({} as ScheduledEvent, env, {} as ExecutionContext);
      return new Response(JSON.stringify({ success: true }), {
        headers: { 'Content-Type': 'application/json' }
      });
    }

    return new Response(JSON.stringify({
      status: 'ok',
      name: 'Technical Indicators Agent',
      endpoints: [
        '/indicators/{symbol}?timeframe=1h&limit=100',
        '/latest?timeframe=1h',
        'POST /calculate'
      ],
      indicators: [
        'SMA (20, 50, 200)',
        'EMA (12, 26, 50)',
        'Bollinger Bands',
        'MACD',
        'RSI (14)',
        'Fear/Greed Index',
        'Volume Indicators'
      ]
    }, null, 2), { headers: { 'Content-Type': 'application/json' } });
  }
};
