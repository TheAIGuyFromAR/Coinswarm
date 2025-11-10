/**
 * Database Initialization Script for Historical Data Collection
 *
 * This script initializes the collection_progress table with all tokens.
 * Run this manually if the cron hasn't seeded the database yet.
 *
 * Deploy as a separate worker or add as an HTTP endpoint to the cron worker.
 */

interface Env {
  DB: D1Database;
}

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

const YEARS_TO_COLLECT = 5;

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === '/init' && request.method === 'POST') {
      try {
        console.log('🔧 Initializing database...');

        // Create tables
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

        console.log('✅ collection_progress table created');

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

        console.log('✅ price_data table created');

        // Seed tokens
        const totalMinutes = 365 * 24 * 60 * YEARS_TO_COLLECT;
        const totalDays = 365 * YEARS_TO_COLLECT;
        const totalHours = 365 * 24 * YEARS_TO_COLLECT;

        let insertedCount = 0;
        let skippedCount = 0;

        for (const token of TOKENS) {
          try {
            const result = await env.DB.prepare(`
              INSERT OR IGNORE INTO collection_progress (
                symbol, coin_id,
                total_minutes, total_days, total_hours,
                daily_status, minute_status, hourly_status
              )
              VALUES (?, ?, ?, ?, ?, 'pending', 'pending', 'pending')
            `).bind(token.symbol, token.coinId, totalMinutes, totalDays, totalHours).run();

            if (result.meta.changes > 0) {
              insertedCount++;
              console.log(`✅ Inserted ${token.symbol}`);
            } else {
              skippedCount++;
              console.log(`⏭️  Skipped ${token.symbol} (already exists)`);
            }
          } catch (error) {
            console.error(`❌ Failed to insert ${token.symbol}:`, error);
          }
        }

        // Verify insertion
        const count = await env.DB.prepare(`
          SELECT COUNT(*) as count FROM collection_progress
        `).first();

        return new Response(JSON.stringify({
          success: true,
          message: 'Database initialized successfully',
          inserted: insertedCount,
          skipped: skippedCount,
          totalInDb: count?.count || 0,
          expectedTotal: TOKENS.length
        }, null, 2), {
          headers: { 'Content-Type': 'application/json' }
        });

      } catch (error) {
        console.error('❌ Database initialization failed:', error);
        return new Response(JSON.stringify({
          success: false,
          error: error instanceof Error ? error.message : String(error),
          stack: error instanceof Error ? error.stack : undefined
        }, null, 2), {
          status: 500,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    }

    // Status endpoint to check initialization
    if (url.pathname === '/check') {
      try {
        const count = await env.DB.prepare(`
          SELECT COUNT(*) as count FROM collection_progress
        `).first();

        const sample = await env.DB.prepare(`
          SELECT * FROM collection_progress LIMIT 3
        `).all();

        return new Response(JSON.stringify({
          status: 'ok',
          tokensInDatabase: count?.count || 0,
          expectedTokens: TOKENS.length,
          initialized: (count?.count || 0) === TOKENS.length,
          sampleTokens: sample.results
        }, null, 2), {
          headers: { 'Content-Type': 'application/json' }
        });
      } catch (error) {
        return new Response(JSON.stringify({
          error: 'Database query failed',
          message: error instanceof Error ? error.message : String(error)
        }, null, 2), {
          status: 500,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    }

    return new Response(JSON.stringify({
      name: 'Collection Database Initializer',
      endpoints: {
        'POST /init': 'Initialize database tables and seed tokens',
        'GET /check': 'Check initialization status'
      },
      usage: 'curl -X POST https://your-worker.workers.dev/init'
    }, null, 2), {
      headers: { 'Content-Type': 'application/json' }
    });
  }
};
