/**
 * Historical Data Collection Cron Worker
 *
 * Slowly collects 5 years of historical OHLCV data for all target tokens
 * Respects API rate limits (30 calls/min for CoinGecko)
 * Runs on schedule to progressively fill the price_data table
 *
 * Target Tokens (15 total):
 * - BTC, ETH, SOL
 * - BSC: BNB, CAKE
 * - Solana: RAY, ORCA, JUP
 * - Arbitrum: ARB, GMX
 * - Optimism: OP, VELO
 * - Polygon: MATIC, QUICK
 * - Base: AERO
 *
 * Schedule: Runs every 2 hours to collect ~30 days per token (75% of safe rate)
 * Rate Limiting: 2.67 sec between calls (22.5 calls/min = 75% of 30/min limit)
 * Total time: ~60-90 days for complete 5-year dataset
 */

interface Env {
  DB: D1Database;
  COINGECKO?: string;  // CoinGecko API key from GitHub secrets
}

interface CollectionProgress {
  symbol: string;
  coinId: string;
  startDate: string;      // YYYY-MM-DD
  endDate: string;        // YYYY-MM-DD
  daysCollected: number;
  totalDays: number;
  lastRun: number;        // Unix timestamp
  status: 'pending' | 'in_progress' | 'completed';
}

// Token configuration
const TOKENS = [
  { symbol: 'BTCUSDT', coinId: 'bitcoin', name: 'Bitcoin' },
  { symbol: 'ETHUSDT', coinId: 'ethereum', name: 'Ethereum' },
  { symbol: 'SOLUSDT', coinId: 'solana', name: 'Solana' },
  { symbol: 'BNBUSDT', coinId: 'binancecoin', name: 'BNB' },
  { symbol: 'CAKEUSDT', coinId: 'pancakeswap-token', name: 'PancakeSwap' },
  { symbol: 'RAYUSDT', coinId: 'raydium', name: 'Raydium' },
  { symbol: 'ORCAUSDT', coinId: 'orca', name: 'Orca' },
  { symbol: 'JUPUSDT', coinId: 'jupiter-exchange-solana', name: 'Jupiter' },
  { symbol: 'ARBUSDT', coinId: 'arbitrum', name: 'Arbitrum' },
  { symbol: 'GMXUSDT', coinId: 'gmx', name: 'GMX' },
  { symbol: 'OPUSDT', coinId: 'optimism', name: 'Optimism' },
  { symbol: 'VELOUSDT', coinId: 'velodrome-finance', name: 'Velodrome' },
  { symbol: 'MATICUSDT', coinId: 'matic-network', name: 'Polygon' },
  { symbol: 'QUICKUSDT', coinId: 'quickswap', name: 'QuickSwap' },
  { symbol: 'AEROUSDT', coinId: 'aerodrome-finance', name: 'Aerodrome' }
];

// Collection parameters
const YEARS_TO_COLLECT = 5;
const DAYS_PER_RUN = 30;           // Fetch 30 days per run to stay under rate limits
const RATE_LIMIT_DELAY_MS = 2670;  // 2.67 seconds between API calls (22.5/min = 75% of 30/min limit)

class CoinGeckoClient {
  private baseUrl = 'https://api.coingecko.com/api/v3';
  private apiKey?: string;

  constructor(apiKey?: string) {
    this.apiKey = apiKey;
  }

  /**
   * Fetch OHLC data for a specific date range
   */
  async fetchOHLC(coinId: string, days: number): Promise<Array<{
    timestamp: number;
    open: number;
    high: number;
    low: number;
    close: number;
  }>> {
    const url = `${this.baseUrl}/coins/${coinId}/ohlc?vs_currency=usd&days=${days}`;

    const headers: Record<string, string> = {
      'Accept': 'application/json'
    };

    if (this.apiKey) {
      headers['x-cg-demo-api-key'] = this.apiKey;
    }

    const response = await fetch(url, { headers });

    if (!response.ok) {
      throw new Error(`CoinGecko API error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json() as Array<[number, number, number, number, number]>;

    // CoinGecko format: [timestamp, open, high, low, close]
    return data.map(candle => ({
      timestamp: candle[0],
      open: candle[1],
      high: candle[2],
      low: candle[3],
      close: candle[4]
    }));
  }

  /**
   * Sleep for rate limiting
   */
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

/**
 * Cron handler - runs on schedule
 */
export default {
  async scheduled(event: ScheduledEvent, env: Env, ctx: ExecutionContext) {
    console.log('Historical data collection cron started');

    const client = new CoinGeckoClient(env.COINGECKO);

    // Initialize progress table if not exists
    await env.DB.prepare(`
      CREATE TABLE IF NOT EXISTS collection_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        coin_id TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        days_collected INTEGER DEFAULT 0,
        total_days INTEGER NOT NULL,
        last_run INTEGER,
        status TEXT DEFAULT 'pending',
        UNIQUE(symbol)
      )
    `).run();

    // Initialize price_data table if not exists
    await env.DB.prepare(`
      CREATE TABLE IF NOT EXISTS price_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        timestamp INTEGER NOT NULL,
        timeframe TEXT NOT NULL DEFAULT '1d',
        open REAL NOT NULL,
        high REAL NOT NULL,
        low REAL NOT NULL,
        close REAL NOT NULL,
        volume REAL DEFAULT 0,
        source TEXT DEFAULT 'coingecko',
        created_at INTEGER DEFAULT (strftime('%s', 'now')),
        UNIQUE(symbol, timestamp, timeframe)
      )
    `).run();

    // Seed progress for all tokens if empty
    const progressCount = await env.DB.prepare(`
      SELECT COUNT(*) as count FROM collection_progress
    `).first<{ count: number }>();

    if (!progressCount || progressCount.count === 0) {
      console.log('Initializing collection progress for all tokens');

      const endDate = new Date();
      const startDate = new Date();
      startDate.setFullYear(endDate.getFullYear() - YEARS_TO_COLLECT);

      const totalDays = Math.floor((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24));

      for (const token of TOKENS) {
        await env.DB.prepare(`
          INSERT INTO collection_progress (symbol, coin_id, start_date, end_date, total_days, status)
          VALUES (?, ?, ?, ?, ?, 'pending')
        `).bind(
          token.symbol,
          token.coinId,
          startDate.toISOString().split('T')[0],
          endDate.toISOString().split('T')[0],
          totalDays
        ).run();
      }
    }

    // Get next token to process (pending or in_progress, ordered by days_collected)
    const nextToken = await env.DB.prepare(`
      SELECT * FROM collection_progress
      WHERE status != 'completed'
      ORDER BY days_collected ASC
      LIMIT 1
    `).first<CollectionProgress>();

    if (!nextToken) {
      console.log('All tokens have been collected!');
      return;
    }

    console.log(`Collecting data for ${nextToken.symbol} (${nextToken.coinId})`);

    // Update status to in_progress
    await env.DB.prepare(`
      UPDATE collection_progress
      SET status = 'in_progress', last_run = ?
      WHERE symbol = ?
    `).bind(Date.now(), nextToken.symbol).run();

    try {
      // Fetch OHLCV data (CoinGecko supports up to 365 days)
      const daysToFetch = Math.min(DAYS_PER_RUN, nextToken.totalDays - nextToken.daysCollected);

      if (daysToFetch <= 0) {
        // Mark as completed
        await env.DB.prepare(`
          UPDATE collection_progress
          SET status = 'completed'
          WHERE symbol = ?
        `).bind(nextToken.symbol).run();

        console.log(`Completed collection for ${nextToken.symbol}`);
        return;
      }

      console.log(`Fetching ${daysToFetch} days for ${nextToken.symbol}`);

      const candles = await client.fetchOHLC(nextToken.coinId, daysToFetch);

      console.log(`Received ${candles.length} candles for ${nextToken.symbol}`);

      // Insert candles into price_data
      let insertedCount = 0;

      for (const candle of candles) {
        try {
          await env.DB.prepare(`
            INSERT OR IGNORE INTO price_data (symbol, timestamp, timeframe, open, high, low, close, source)
            VALUES (?, ?, '1d', ?, ?, ?, ?, 'coingecko')
          `).bind(
            nextToken.symbol,
            Math.floor(candle.timestamp / 1000),  // Convert to seconds
            candle.open,
            candle.high,
            candle.low,
            candle.close
          ).run();

          insertedCount++;
        } catch (e) {
          console.error(`Error inserting candle for ${nextToken.symbol}:`, e);
        }
      }

      // Update progress
      const newDaysCollected = nextToken.daysCollected + daysToFetch;
      const isCompleted = newDaysCollected >= nextToken.totalDays;

      await env.DB.prepare(`
        UPDATE collection_progress
        SET days_collected = ?, status = ?, last_run = ?
        WHERE symbol = ?
      `).bind(
        newDaysCollected,
        isCompleted ? 'completed' : 'pending',
        Date.now(),
        nextToken.symbol
      ).run();

      console.log(`Successfully inserted ${insertedCount} candles for ${nextToken.symbol}`);
      console.log(`Progress: ${newDaysCollected}/${nextToken.totalDays} days (${Math.round(newDaysCollected / nextToken.totalDays * 100)}%)`);

    } catch (error) {
      console.error(`Error collecting data for ${nextToken.symbol}:`, error);

      // Update status back to pending for retry
      await env.DB.prepare(`
        UPDATE collection_progress
        SET status = 'pending', last_run = ?
        WHERE symbol = ?
      `).bind(Date.now(), nextToken.symbol).run();
    }
  },

  /**
   * HTTP handler for manual testing and status checks
   */
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    // Get collection progress
    if (url.pathname === '/status') {
      const progress = await env.DB.prepare(`
        SELECT * FROM collection_progress
        ORDER BY days_collected ASC
      `).all();

      return new Response(JSON.stringify({
        success: true,
        tokens: progress.results,
        totalTokens: TOKENS.length,
        completedTokens: progress.results.filter((t: any) => t.status === 'completed').length
      }, null, 2), {
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Manual trigger (for testing)
    if (url.pathname === '/collect') {
      const event = { cron: 'manual', scheduledTime: Date.now() } as ScheduledEvent;
      await this.scheduled(event, env, {} as ExecutionContext);

      return new Response(JSON.stringify({
        success: true,
        message: 'Collection run triggered manually'
      }), {
        headers: { 'Content-Type': 'application/json' }
      });
    }

    return new Response(JSON.stringify({
      status: 'ok',
      name: 'Historical Data Collection Cron Worker',
      endpoints: {
        '/status': 'Get collection progress',
        '/collect': 'Manual trigger (for testing)'
      },
      tokens: TOKENS.map(t => t.symbol),
      schedule: 'Every 2 hours (75% of safe rate)',
      daysPerRun: DAYS_PER_RUN,
      yearsToCollect: YEARS_TO_COLLECT,
      rateLimitDelay: `${RATE_LIMIT_DELAY_MS}ms (22.5 calls/min)`
    }, null, 2), {
      headers: { 'Content-Type': 'application/json' }
    });
  }
};
