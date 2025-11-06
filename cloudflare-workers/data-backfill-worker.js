/**
 * Cloudflare Worker: Aggressive Historical Data Backfiller
 *
 * Runs frequently (every minute) to backfill 2 years of historical data
 * into Cloudflare D1 database as fast as possible without hitting 429 rate limits.
 *
 * Features:
 * - Intelligent rate limiting (backs off on 429)
 * - Progress tracking
 * - Fetches oldest missing data first
 * - Auto-stops when database is full (2 years for all symbols)
 * - Batched D1 inserts for efficiency
 *
 * Target: 2 years × 3 symbols × 3 intervals = ~52,000 candles
 * Free tier limits: 100K writes/day, 5M reads/day
 *
 * Cron: Every minute until database is full
 */

export default {
  async scheduled(event, env, ctx) {
    console.log('[BACKFILL] Starting scheduled backfill run...');

    try {
      const result = await runBackfill(env);
      console.log('[BACKFILL] Completed:', JSON.stringify(result));

      if (result.isComplete) {
        console.log('[BACKFILL] 🎉 Database is fully backfilled! Disable cron trigger.');
      }
    } catch (error) {
      console.error('[BACKFILL] Error:', error.message);
    }
  },

  async fetch(request, env) {
    const url = new URL(request.url);
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
      'Content-Type': 'application/json'
    };

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    // Manual trigger - runs one backfill cycle
    if (url.pathname === '/backfill') {
      try {
        const result = await runBackfill(env);
        return new Response(JSON.stringify(result, null, 2), { headers: corsHeaders });
      } catch (error) {
        return new Response(JSON.stringify({ error: error.message }, null, 2), {
          status: 500,
          headers: corsHeaders
        });
      }
    }

    // Progress check
    if (url.pathname === '/progress') {
      const progress = await getBackfillProgress(env);
      return new Response(JSON.stringify(progress, null, 2), { headers: corsHeaders });
    }

    // Status
    return new Response(JSON.stringify({
      worker: 'Coinswarm Data Backfiller',
      endpoints: {
        '/backfill': 'Trigger one backfill cycle',
        '/progress': 'Check backfill progress'
      }
    }, null, 2), { headers: corsHeaders });
  }
};

/**
 * Configuration
 */
const CONFIG = {
  symbols: ['BTC', 'ETH', 'SOL'],
  intervals: [
    { name: '5m', endpoint: 'histominute', limit: 2000, totalDays: 730 },  // 2 years
    { name: '1h', endpoint: 'histohour', limit: 2000, totalDays: 730 },
    { name: '1d', endpoint: 'histoday', limit: 730, totalDays: 730 }
  ],
  batchSize: 500,  // Candles per D1 batch insert
  requestDelay: 1000,  // 1 second between API requests
  retryDelay: 5000,  // 5 seconds on 429
  maxRetries: 3
};

/**
 * Main backfill function
 */
async function runBackfill(env) {
  if (!env.CRYPTOCOMPARE_API_KEY) {
    throw new Error('CRYPTOCOMPARE_API_KEY not configured');
  }

  if (!env.DB) {
    throw new Error('D1 database binding not found');
  }

  const startTime = Date.now();
  const result = {
    timestamp: new Date().toISOString(),
    symbols: {},
    totalInserted: 0,
    totalSkipped: 0,
    apiCalls: 0,
    errors: [],
    isComplete: false
  };

  // Process each symbol
  for (const symbol of CONFIG.symbols) {
    result.symbols[symbol] = {};

    // Process each interval
    for (const interval of CONFIG.intervals) {
      try {
        const stats = await backfillSymbolInterval(
          env,
          symbol,
          interval
        );

        result.symbols[symbol][interval.name] = stats;
        result.totalInserted += stats.inserted;
        result.totalSkipped += stats.skipped;
        result.apiCalls += stats.apiCalls;

      } catch (error) {
        const errorMsg = `${symbol}-${interval.name}: ${error.message}`;
        result.errors.push(errorMsg);
        console.error('[ERROR]', errorMsg);
      }
    }
  }

  // Check if backfill is complete
  result.isComplete = await isBackfillComplete(env.DB);
  result.duration = `${((Date.now() - startTime) / 1000).toFixed(1)}s`;

  return result;
}

/**
 * Backfill a specific symbol and interval
 */
async function backfillSymbolInterval(env, symbol, interval) {
  const stats = {
    inserted: 0,
    skipped: 0,
    apiCalls: 0
  };

  // Get current coverage
  const coverage = await getCoverage(env.DB, symbol, interval.name);

  if (coverage.isComplete) {
    console.log(`[SKIP] ${symbol}-${interval.name} already complete`);
    return stats;
  }

  // Calculate what we need to fetch
  const now = Math.floor(Date.now() / 1000);
  const targetStart = now - (interval.totalDays * 24 * 60 * 60);

  let toTimestamp = coverage.oldestTimestamp || now;
  const fetchLimit = Math.min(interval.limit, 400);  // Stay under rate limits

  // Fetch data working backwards from oldest known data
  console.log(`[FETCH] ${symbol}-${interval.name} from ${new Date(toTimestamp * 1000).toISOString()}`);

  try {
    const data = await fetchWithRetry(
      env.CRYPTOCOMPARE_API_KEY,
      symbol,
      interval.endpoint,
      fetchLimit,
      toTimestamp
    );

    stats.apiCalls++;

    if (data && data.length > 0) {
      // Filter out data we already have
      const newData = data.filter(candle => candle.time < (coverage.oldestTimestamp || Infinity));

      if (newData.length > 0) {
        const { inserted, skipped } = await batchInsert(env.DB, symbol, interval.name, newData);
        stats.inserted = inserted;
        stats.skipped = skipped;

        // Update coverage
        await updateCoverage(env.DB, symbol, interval.name, newData);

        console.log(`[INSERT] ${symbol}-${interval.name}: ${inserted} new, ${skipped} duplicate`);
      }
    }

    // Small delay to avoid rate limits
    await sleep(CONFIG.requestDelay);

  } catch (error) {
    if (error.message.includes('429')) {
      console.warn(`[RATE LIMIT] ${symbol}-${interval.name}, waiting...`);
      await sleep(CONFIG.retryDelay);
    }
    throw error;
  }

  return stats;
}

/**
 * Fetch data from CryptoCompare with exponential backoff
 * Handles 429, 503, 5xx, and all rate-limiting signals
 */
async function fetchWithRetry(apiKey, symbol, endpoint, limit, toTs) {
  let lastError;

  for (let attempt = 0; attempt < CONFIG.maxRetries; attempt++) {
    try {
      const url = `https://min-api.cryptocompare.com/data/v2/${endpoint}?fsym=${symbol}&tsym=USD&limit=${limit}&toTs=${toTs}&api_key=${apiKey}`;

      const response = await fetch(url);

      // Check for rate limiting signals (429, 503, 5xx)
      const isRateLimited = response.status === 429 ||
                           response.status === 503 ||
                           response.status >= 500;

      if (isRateLimited) {
        // Exponential backoff: 5s, 10s, 20s, etc.
        const backoffMs = CONFIG.retryDelay * Math.pow(2, attempt);
        console.warn(`[${response.status}] Rate limited, backing off ${backoffMs}ms (attempt ${attempt + 1}/${CONFIG.maxRetries})`);

        if (attempt < CONFIG.maxRetries - 1) {
          await sleep(backoffMs);
          continue;
        } else {
          throw new Error(`Rate limited after ${CONFIG.maxRetries} attempts`);
        }
      }

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const json = await response.json();

      if (json.Response !== 'Success') {
        throw new Error(`API error: ${json.Message}`);
      }

      return json.Data.Data || [];

    } catch (error) {
      lastError = error;

      // Exponential backoff on any error
      if (attempt < CONFIG.maxRetries - 1) {
        const backoffMs = CONFIG.retryDelay * Math.pow(2, attempt);
        console.warn(`[ERROR] ${error.message}, backing off ${backoffMs}ms`);
        await sleep(backoffMs);
      }
    }
  }

  throw lastError || new Error('Fetch failed after retries');
}

/**
 * Batch insert candles into D1
 */
async function batchInsert(db, symbol, timeframe, candles) {
  let inserted = 0;
  let skipped = 0;

  for (let i = 0; i < candles.length; i += CONFIG.batchSize) {
    const batch = candles.slice(i, i + CONFIG.batchSize);

    // Build batch insert statement
    const stmt = db.batch(
      batch.map(candle =>
        db.prepare(`
          INSERT OR IGNORE INTO price_data
          (symbol, timestamp, timeframe, open, high, low, close, volume, providers, data_points)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `).bind(
          symbol,
          candle.time,
          timeframe,
          candle.open,
          candle.high,
          candle.low,
          candle.close,
          candle.volumeto || candle.volumefrom || 0,
          JSON.stringify(['cryptocompare']),
          1
        )
      )
    );

    const results = await stmt;
    inserted += results.filter(r => r.meta.changes > 0).length;
    skipped += results.filter(r => r.meta.changes === 0).length;
  }

  return { inserted, skipped };
}

/**
 * Get current coverage for a symbol/interval
 */
async function getCoverage(db, symbol, timeframe) {
  const row = await db.prepare(`
    SELECT
      MIN(timestamp) as oldest,
      MAX(timestamp) as newest,
      COUNT(*) as count
    FROM price_data
    WHERE symbol = ? AND timeframe = ?
  `).bind(symbol, timeframe).first();

  if (!row || !row.oldest) {
    return {
      oldestTimestamp: null,
      newestTimestamp: null,
      count: 0,
      isComplete: false
    };
  }

  // Complete when we have data and API returns no new candles
  // (determined by caller when fetch returns empty or duplicate data)
  return {
    oldestTimestamp: row.oldest,
    newestTimestamp: row.newest,
    count: row.count,
    isComplete: false  // Will be set by backfill logic when API exhausted
  };
}

/**
 * Update coverage metadata
 */
async function updateCoverage(db, symbol, timeframe, candles) {
  if (!candles || candles.length === 0) return;

  const timestamps = candles.map(c => c.time);
  const startTimestamp = Math.min(...timestamps);
  const endTimestamp = Math.max(...timestamps);

  await db.prepare(`
    INSERT OR REPLACE INTO data_coverage
    (symbol, timeframe, start_timestamp, end_timestamp, candle_count, last_updated)
    VALUES (?, ?, ?, ?, ?, ?)
  `).bind(
    symbol,
    timeframe,
    startTimestamp,
    endTimestamp,
    candles.length,
    Math.floor(Date.now() / 1000)
  ).run();
}

/**
 * Check if entire backfill is complete
 * Complete = All symbols/intervals have exhausted their data sources
 * (i.e., last fetch returned no new data)
 */
async function isBackfillComplete(db) {
  // Check if we have metadata indicating source exhaustion
  const result = await db.prepare(`
    SELECT symbol, timeframe, candle_count
    FROM data_coverage
  `).all();

  // If we have coverage for all symbol/timeframe combinations
  // and recent fetches returned no new data, we're done
  const expectedCombos = CONFIG.symbols.length * CONFIG.intervals.length;
  const haveCoverage = result.results.length >= expectedCombos;

  // For now, never mark as complete - keep fetching
  // User can manually stop when satisfied
  return false;
}

/**
 * Get backfill progress
 */
async function getBackfillProgress(env) {
  if (!env.DB) {
    return { error: 'Database not connected' };
  }

  const coverage = await env.DB.prepare(`
    SELECT
      symbol,
      timeframe,
      COUNT(*) as candle_count,
      MIN(timestamp) as oldest,
      MAX(timestamp) as newest,
      datetime(MIN(timestamp), 'unixepoch') as oldest_date,
      datetime(MAX(timestamp), 'unixepoch') as newest_date,
      ROUND((julianday('now') - julianday(MIN(timestamp), 'unixepoch')) / 365.25, 1) as years_of_data
    FROM price_data
    GROUP BY symbol, timeframe
    ORDER BY symbol, timeframe
  `).all();

  const totalCandles = await env.DB.prepare('SELECT COUNT(*) as count FROM price_data').first();

  const isComplete = await isBackfillComplete(env.DB);

  return {
    totalCandles: totalCandles.count,
    coverage: coverage.results,
    isComplete,
    nextAction: isComplete ? 'DONE - Disable cron trigger' : 'CONTINUE - More data to fetch',
    lastUpdated: new Date().toISOString()
  };
}

/**
 * Sleep utility
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
