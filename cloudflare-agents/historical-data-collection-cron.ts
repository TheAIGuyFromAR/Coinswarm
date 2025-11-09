/**
 * Historical Data Collection Cron Worker
 *
 * Strategy (all run in parallel):
 * 1. CryptoCompare: Minute-level data (runs forever, best minute data source)
 * 2. CoinGecko: Daily data until 5 years complete
 * 3. Binance.US: Hourly data until 5 years complete (fastest source)
 *
 * Rate limiting at 56.25% of max (75% then 25% slower = 56.25%)
 */

interface Env {
  DB: D1Database;
  COINGECKO?: string;
  CRYPTOCOMPARE_API_KEY?: string;
}

interface CollectionProgress {
  symbol: string;
  coinId: string;
  minutesCollected: number;
  daysCollected: number;
  hoursCollected: number;
  totalMinutes: number;
  totalDays: number;
  totalHours: number;
  dailyStatus: 'pending' | 'in_progress' | 'completed' | 'paused';
  minuteStatus: 'pending' | 'in_progress' | 'completed' | 'paused';
  hourlyStatus: 'pending' | 'in_progress' | 'completed' | 'paused';
  errorCount: number;
  lastError: string;
}

// Token configuration
const TOKENS = [
  { symbol: 'BTCUSDT', coinId: 'bitcoin' },
  { symbol: 'ETHUSDT', coinId: 'ethereum' },
  { symbol: 'SOLUSDT', coinId: 'solana' },
  { symbol: 'BNBUSDT', coinId: 'binancecoin' },
  { symbol: 'CAKEUSDT', coinId: 'pancakeswap-token' },
  { symbol: 'RAYUSDT', coinId: 'raydium' },
  { symbol: 'ORCAUSDT', coinId: 'orca' },
  { symbol: 'JUPUSDT', coinId: 'jupiter-exchange-solana' },
  { symbol: 'ARBUSDT', coinId: 'arbitrum' },
  { symbol: 'GMXUSDT', coinId: 'gmx' },
  { symbol: 'OPUSDT', coinId: 'optimism' },
  { symbol: 'VELOUSDT', coinId: 'velodrome-finance' },
  { symbol: 'MATICUSDT', coinId: 'matic-network' },
  { symbol: 'QUICKUSDT', coinId: 'quickswap' },
  { symbol: 'AEROUSDT', coinId: 'aerodrome-finance' }
];

// Rate limiting at 56.25% of max (75% then 25% slower)
// CryptoCompare max: 30 calls/min → 16.875 calls/min = 3.56s delay
// CoinGecko max: 30 calls/min → 16.875 calls/min = 3.56s delay
// Binance.US max: 1200 weight/min → 675 weight/min = 89ms delay
const RATE_LIMIT_DELAY_MS = 3560; // 16.875 calls/min (56.25% of 30)
const BINANCE_RATE_LIMIT_MS = 89; // 675 calls/min (56.25% of 1200)

// Collection parameters
const YEARS_TO_COLLECT = 5;
const DAYS_PER_RUN = 365;  // CoinGecko: 1 year at a time
const MINUTES_PER_RUN = 2000;  // CryptoCompare: 2000 minutes (~33 hours) per call
const HOURS_PER_RUN = 1000;  // Binance.US: 1000 hours (~41 days) per call

/**
 * CoinGecko API Client - Daily OHLC data
 */
class CoinGeckoClient {
  private baseUrl = 'https://api.coingecko.com/api/v3';
  private apiKey?: string;

  constructor(apiKey?: string) {
    this.apiKey = apiKey;
  }

  async fetchOHLC(coinId: string, days: number): Promise<Array<{
    timestamp: number;
    open: number;
    high: number;
    low: number;
    close: number;
  }>> {
    const url = `${this.baseUrl}/coins/${coinId}/ohlc?vs_currency=usd&days=${days}`;
    const headers: Record<string, string> = { 'Accept': 'application/json' };

    if (this.apiKey) {
      headers['x-cg-demo-api-key'] = this.apiKey;
    }

    const response = await fetch(url, { headers });
    if (!response.ok) {
      throw new Error(`CoinGecko API error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json() as Array<[number, number, number, number, number]>;
    return data.map(candle => ({
      timestamp: candle[0],
      open: candle[1],
      high: candle[2],
      low: candle[3],
      close: candle[4]
    }));
  }
}

/**
 * CryptoCompare API Client - Minute data
 * Best source for minute-level historical data
 */
class CryptoCompareClient {
  private baseUrl = 'https://min-api.cryptocompare.com/data';
  private apiKey?: string;

  constructor(apiKey?: string) {
    this.apiKey = apiKey;
  }

  /**
   * Fetch minute-level OHLCV data
   * @param symbol - Token symbol (e.g., 'BTCUSDT')
   * @param limit - Number of minutes to fetch (max 2000)
   * @param toTs - End timestamp (optional, defaults to now)
   */
  async fetchHistoMinute(symbol: string, limit: number = 2000, toTs?: number): Promise<Array<{
    timestamp: number;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  }>> {
    const fsym = symbol.replace(/USDT|USDC|BUSD/g, '');
    const tsym = 'USD';

    let url = `${this.baseUrl}/v2/histominute?fsym=${fsym}&tsym=${tsym}&limit=${limit}`;
    if (toTs) {
      url += `&toTs=${Math.floor(toTs)}`;
    }

    if (this.apiKey) {
      url += `&api_key=${this.apiKey}`;
    }

    const response = await fetch(url, {
      headers: { 'Accept': 'application/json' }
    });

    if (!response.ok) {
      throw new Error(`CryptoCompare API error: ${response.status} ${response.statusText}`);
    }

    const result = await response.json() as any;

    if (result.Response === 'Error') {
      throw new Error(`CryptoCompare: ${result.Message}`);
    }

    return result.Data.Data.map((candle: any) => ({
      timestamp: candle.time * 1000,
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
      volume: candle.volumefrom
    }));
  }
}

/**
 * Binance.US API Client - Hourly klines
 * Fast and reliable for hourly historical data
 */
class BinanceClient {
  private baseUrl = 'https://api.binance.us';

  /**
   * Fetch hourly klines from Binance.US
   * @param symbol - Binance symbol (e.g., 'BTCUSDT')
   * @param limit - Number of hours to fetch (max 1000)
   * @param endTime - End timestamp in ms (optional, defaults to now)
   */
  async fetchKlines(symbol: string, limit: number = 1000, endTime?: number): Promise<Array<{
    timestamp: number;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  }>> {
    let url = `${this.baseUrl}/api/v3/klines?symbol=${symbol}&interval=1h&limit=${limit}`;

    if (endTime) {
      url += `&endTime=${endTime}`;
    }

    const response = await fetch(url, {
      headers: { 'Accept': 'application/json' }
    });

    if (!response.ok) {
      throw new Error(`Binance API error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json() as Array<any>;

    return data.map((kline: any) => ({
      timestamp: kline[0], // Open time in ms
      open: parseFloat(kline[1]),
      high: parseFloat(kline[2]),
      low: parseFloat(kline[3]),
      close: parseFloat(kline[4]),
      volume: parseFloat(kline[5])
    }));
  }
}

export default {
  async scheduled(event: ScheduledEvent, env: Env, ctx: ExecutionContext) {
    console.log('⏰ Starting multi-timeframe collection...');

    // Initialize tables
    await env.DB.prepare(`
      CREATE TABLE IF NOT EXISTS collection_progress (
        symbol TEXT PRIMARY KEY,
        coin_id TEXT NOT NULL,
        minutes_collected INTEGER DEFAULT 0,
        days_collected INTEGER DEFAULT 0,
        hours_collected INTEGER DEFAULT 0,
        total_minutes INTEGER NOT NULL,
        total_days INTEGER NOT NULL,
        total_hours INTEGER NOT NULL,
        daily_status TEXT DEFAULT 'pending',
        minute_status TEXT DEFAULT 'pending',
        hourly_status TEXT DEFAULT 'pending',
        error_count INTEGER DEFAULT 0,
        last_error TEXT,
        last_minute_timestamp INTEGER,
        last_run INTEGER
      )
    `).run();

    await env.DB.prepare(`
      CREATE TABLE IF NOT EXISTS price_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        timestamp INTEGER NOT NULL,
        timeframe TEXT NOT NULL,
        open REAL NOT NULL,
        high REAL NOT NULL,
        low REAL NOT NULL,
        close REAL NOT NULL,
        volume REAL DEFAULT 0,
        source TEXT NOT NULL,
        created_at INTEGER DEFAULT (strftime('%s', 'now')),
        UNIQUE(symbol, timestamp, timeframe, source)
      )
    `).run();

    // Seed tokens
    const totalMinutes = 365 * 24 * 60 * YEARS_TO_COLLECT; // 5 years of minutes
    const totalDays = 365 * YEARS_TO_COLLECT;
    const totalHours = 365 * 24 * YEARS_TO_COLLECT;

    for (const token of TOKENS) {
      await env.DB.prepare(`
        INSERT OR IGNORE INTO collection_progress (
          symbol, coin_id,
          total_minutes, total_days, total_hours,
          daily_status, minute_status, hourly_status
        )
        VALUES (?, ?, ?, ?, ?, 'pending', 'pending', 'pending')
      `).bind(token.symbol, token.coinId, totalMinutes, totalDays, totalHours).run();
    }

    // Run all three collectors in parallel
    ctx.waitUntil(Promise.all([
      this.runMinuteCollection(env),
      this.runDailyCollection(env),
      this.runHourlyCollection(env)
    ]));
  },

  /**
   * Continuous minute-level data collection (runs forever)
   * Uses CryptoCompare to fetch minute candles working backwards from now
   */
  async runMinuteCollection(env: Env) {
    if (!env.CRYPTOCOMPARE_API_KEY) {
      console.warn('⚠️ CRYPTOCOMPARE_API_KEY not set, skipping minute collection');
      return;
    }

    const client = new CryptoCompareClient(env.CRYPTOCOMPARE_API_KEY);

    while (true) {
      // Get next token for minute data collection
      const token = await env.DB.prepare(`
        SELECT * FROM collection_progress
        WHERE minute_status NOT IN ('completed', 'paused')
        ORDER BY minutes_collected ASC
        LIMIT 1
      `).first<CollectionProgress>();

      if (!token) {
        console.log('✅ All minute data collected! Restarting from beginning...');
        // Reset all tokens to continue collecting forever
        await env.DB.prepare(`
          UPDATE collection_progress
          SET minute_status = 'pending', minutes_collected = 0, last_minute_timestamp = NULL
        `).run();
        continue;
      }

      try {
        const minutesToFetch = Math.min(MINUTES_PER_RUN, token.totalMinutes - token.minutesCollected);

        if (minutesToFetch <= 0) {
          await env.DB.prepare(`
            UPDATE collection_progress SET minute_status = 'completed' WHERE symbol = ?
          `).bind(token.symbol).run();
          continue;
        }

        // Work backwards from the last timestamp we collected (or now if first run)
        const toTs = token.lastMinuteTimestamp
          ? token.lastMinuteTimestamp / 1000
          : Math.floor(Date.now() / 1000);

        console.log(`📊 Fetching ${minutesToFetch} minutes for ${token.symbol} (minute data)`);
        const candles = await client.fetchHistoMinute(token.symbol, minutesToFetch, toTs);

        if (candles.length === 0) {
          console.log(`⚠️ No minute data returned for ${token.symbol}`);
          await new Promise(resolve => setTimeout(resolve, RATE_LIMIT_DELAY_MS));
          continue;
        }

        // Insert candles
        for (const candle of candles) {
          await env.DB.prepare(`
            INSERT OR IGNORE INTO price_data (symbol, timestamp, timeframe, open, high, low, close, volume, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
          `).bind(
            token.symbol,
            Math.floor(candle.timestamp / 1000),
            '1m',
            candle.open,
            candle.high,
            candle.low,
            candle.close,
            candle.volume,
            'cryptocompare'
          ).run();
        }

        // Update progress - track the oldest timestamp we've collected
        const oldestTimestamp = Math.min(...candles.map(c => c.timestamp));
        const newMinutes = token.minutesCollected + candles.length;

        await env.DB.prepare(`
          UPDATE collection_progress
          SET minutes_collected = ?,
              last_minute_timestamp = ?,
              minute_status = ?,
              error_count = 0,
              last_error = NULL
          WHERE symbol = ?
        `).bind(
          newMinutes,
          oldestTimestamp,
          newMinutes >= token.totalMinutes ? 'completed' : 'pending',
          token.symbol
        ).run();

        console.log(`✅ ${token.symbol}: ${newMinutes}/${token.totalMinutes} minutes (${Math.round(newMinutes/token.totalMinutes*100)}%)`);

      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        const newErrorCount = (token.errorCount || 0) + 1;

        await env.DB.prepare(`
          UPDATE collection_progress
          SET minute_status = ?, error_count = ?, last_error = ?
          WHERE symbol = ?
        `).bind(
          newErrorCount >= 3 ? 'paused' : 'pending',
          newErrorCount,
          errorMsg.substring(0, 500),
          token.symbol
        ).run();

        console.error(`❌ ${token.symbol} minute error (${newErrorCount}/3): ${errorMsg}`);
      }

      // Rate limiting
      await new Promise(resolve => setTimeout(resolve, RATE_LIMIT_DELAY_MS));
    }
  },

  /**
   * Daily data collection (until 5 years complete)
   * Uses CoinGecko for daily candles
   */
  async runDailyCollection(env: Env) {
    const coinGeckoClient = new CoinGeckoClient(env.COINGECKO);

    while (true) {
      // Get next token for daily data
      const token = await env.DB.prepare(`
        SELECT * FROM collection_progress
        WHERE daily_status NOT IN ('completed', 'paused')
        ORDER BY days_collected ASC
        LIMIT 1
      `).first<CollectionProgress>();

      if (!token) {
        console.log('✅ All daily data collected!');
        return;
      }

      try {
        const daysToFetch = Math.min(DAYS_PER_RUN, token.totalDays - token.daysCollected);

        if (daysToFetch <= 0) {
          await env.DB.prepare(`
            UPDATE collection_progress SET daily_status = 'completed' WHERE symbol = ?
          `).bind(token.symbol).run();
          continue;
        }

        console.log(`📅 Fetching ${daysToFetch} days for ${token.symbol} (daily data)`);
        const candles = await coinGeckoClient.fetchOHLC(token.coinId, daysToFetch);

        for (const candle of candles) {
          await env.DB.prepare(`
            INSERT OR IGNORE INTO price_data (symbol, timestamp, timeframe, open, high, low, close, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
          `).bind(
            token.symbol,
            Math.floor(candle.timestamp / 1000),
            '1d',
            candle.open,
            candle.high,
            candle.low,
            candle.close,
            'coingecko'
          ).run();
        }

        const newDays = token.daysCollected + daysToFetch;
        await env.DB.prepare(`
          UPDATE collection_progress
          SET days_collected = ?, daily_status = ?, error_count = 0, last_error = NULL
          WHERE symbol = ?
        `).bind(newDays, newDays >= token.totalDays ? 'completed' : 'pending', token.symbol).run();

        console.log(`✅ ${token.symbol}: ${newDays}/${token.totalDays} days (${Math.round(newDays/token.totalDays*100)}%)`);

      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        const newErrorCount = (token.errorCount || 0) + 1;

        await env.DB.prepare(`
          UPDATE collection_progress
          SET daily_status = ?, error_count = ?, last_error = ?
          WHERE symbol = ?
        `).bind(
          newErrorCount >= 3 ? 'paused' : 'pending',
          newErrorCount,
          errorMsg.substring(0, 500),
          token.symbol
        ).run();

        console.error(`❌ ${token.symbol} daily error (${newErrorCount}/3): ${errorMsg}`);
      }

      // Rate limiting
      await new Promise(resolve => setTimeout(resolve, RATE_LIMIT_DELAY_MS));
    }
  },

  /**
   * Hourly data collection (runs in parallel with daily)
   * Uses Binance.US for fast, reliable hourly klines
   */
  async runHourlyCollection(env: Env) {
    const client = new BinanceClient();
    while (true) {
      const token = await env.DB.prepare(`
        SELECT * FROM collection_progress
        WHERE hourly_status NOT IN ('completed', 'paused')
        ORDER BY hours_collected ASC
        LIMIT 1
      `).first<CollectionProgress>();

      if (!token) {
        console.log('✅ All hourly data collected!');
        return;
      }

      try {
        const hoursToFetch = Math.min(HOURS_PER_RUN, token.totalHours - token.hoursCollected);

        if (hoursToFetch <= 0) {
          await env.DB.prepare(`
            UPDATE collection_progress SET hourly_status = 'completed' WHERE symbol = ?
          `).bind(token.symbol).run();
          continue;
        }

        console.log(`⏰ Fetching ${hoursToFetch} hours for ${token.symbol} (hourly data)`);

        // Calculate endTime for fetching backwards
        const endTime = token.hoursCollected === 0
          ? Date.now()
          : Date.now() - (token.hoursCollected * 60 * 60 * 1000);

        const candles = await client.fetchKlines(token.symbol, hoursToFetch, endTime);

        for (const candle of candles) {
          await env.DB.prepare(`
            INSERT OR IGNORE INTO price_data (symbol, timestamp, timeframe, open, high, low, close, volume, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
          `).bind(
            token.symbol,
            Math.floor(candle.timestamp / 1000),
            '1h',
            candle.open,
            candle.high,
            candle.low,
            candle.close,
            candle.volume,
            'binance'
          ).run();
        }

        const newHours = token.hoursCollected + candles.length;
        await env.DB.prepare(`
          UPDATE collection_progress
          SET hours_collected = ?, hourly_status = ?, error_count = 0, last_error = NULL
          WHERE symbol = ?
        `).bind(newHours, newHours >= token.totalHours ? 'completed' : 'pending', token.symbol).run();

        console.log(`✅ ${token.symbol}: ${newHours}/${token.totalHours} hours (${Math.round(newHours/token.totalHours*100)}%)`);

      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        const newErrorCount = (token.errorCount || 0) + 1;

        await env.DB.prepare(`
          UPDATE collection_progress
          SET hourly_status = ?, error_count = ?, last_error = ?
          WHERE symbol = ?
        `).bind(
          newErrorCount >= 3 ? 'paused' : 'pending',
          newErrorCount,
          errorMsg.substring(0, 500),
          token.symbol
        ).run();

        console.error(`❌ ${token.symbol} hourly error (${newErrorCount}/3): ${errorMsg}`);
      }

      // Binance.US rate limiting (much faster than CoinGecko/CryptoCompare)
      await new Promise(resolve => setTimeout(resolve, BINANCE_RATE_LIMIT_MS));
    }
  },

  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === '/status') {
      const progress = await env.DB.prepare(`
        SELECT * FROM collection_progress ORDER BY days_collected ASC
      `).all();

      const stats = {
        tokens: progress.results,
        dailyCompleted: progress.results.filter((t: any) => t.daily_status === 'completed').length,
        minuteCompleted: progress.results.filter((t: any) => t.minute_status === 'completed').length,
        hourlyCompleted: progress.results.filter((t: any) => t.hourly_status === 'completed').length,
        totalTokens: TOKENS.length
      };

      return new Response(JSON.stringify(stats, null, 2), {
        headers: { 'Content-Type': 'application/json' }
      });
    }

    return new Response(JSON.stringify({
      status: 'ok',
      name: 'Multi-Timeframe Historical Data Collection Worker',
      strategy: {
        minute: 'CryptoCompare - runs forever (16.875 calls/min)',
        daily: 'CoinGecko - until 5 years complete (16.875 calls/min)',
        hourly: 'Binance.US - until 5 years complete (675 calls/min)'
      },
      parallel: 'All three collectors run simultaneously',
      tokens: TOKENS.length,
      timeframes: ['1m', '1h', '1d']
    }, null, 2), { headers: { 'Content-Type': 'application/json' } });
  }
};
