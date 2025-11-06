/**
 * Coinswarm Worker with Cloudflare D1 Integration
 *
 * This Worker:
 * 1. Fetches real-time crypto data from multiple sources
 * 2. Stores historical data in Cloudflare D1
 * 3. Serves cached data for fast, rate-limit-free backtesting
 *
 * D1 Binding: env.DB
 */

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    try {
      // Route: Store data in D1
      if (path === '/store' && request.method === 'POST') {
        return await handleStore(request, env, corsHeaders);
      }

      // Route: Query data from D1
      if (path === '/query') {
        return await handleQuery(url, env, corsHeaders);
      }

      // Route: Get data coverage
      if (path === '/coverage') {
        return await handleCoverage(url, env, corsHeaders);
      }

      // Route: Get statistics
      if (path === '/stats') {
        return await handleStats(url, env, corsHeaders);
      }

      // Route: Fetch fresh data (and optionally store)
      if (path === '/fetch') {
        return await handleFetch(url, env, corsHeaders);
      }

      // Default: Show endpoints
      return new Response(JSON.stringify({
        status: "ok",
        message: "Coinswarm Historical Data API with D1 Storage",
        endpoints: {
          query: "/query?symbol=BTC&days=30 - Get data from D1",
          coverage: "/coverage?symbol=BTC - Check what data we have",
          stats: "/stats?symbol=BTC&period=30d - Get statistics",
          fetch: "/fetch?symbol=BTCUSDT&timeframe=1h&days=7 - Fetch and store fresh data",
          store: "POST /store - Store data in D1 (JSON body)"
        }
      }, null, 2), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });

    } catch (error) {
      return new Response(JSON.stringify({
        error: error.message,
        stack: error.stack
      }), {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }
  }
};


/**
 * Query data from D1
 */
async function handleQuery(url, env, corsHeaders) {
  const symbol = url.searchParams.get('symbol') || 'BTC';
  const days = parseInt(url.searchParams.get('days') || '30');
  const timeframe = url.searchParams.get('timeframe') || '1h';

  const endTime = Math.floor(Date.now() / 1000);
  const startTime = endTime - (days * 24 * 60 * 60);

  // Query D1
  const result = await env.DB.prepare(`
    SELECT
      symbol,
      timestamp,
      timeframe,
      open,
      high,
      low,
      close,
      volume,
      providers,
      data_points,
      variance
    FROM price_data
    WHERE symbol = ?
      AND timeframe = ?
      AND timestamp >= ?
      AND timestamp <= ?
    ORDER BY timestamp ASC
  `).bind(symbol, timeframe, startTime, endTime).all();

  if (!result.success) {
    throw new Error('D1 query failed');
  }

  const candles = result.results.map(row => ({
    timestamp: new Date(row.timestamp * 1000).toISOString(),
    open: row.open,
    high: row.high,
    low: row.low,
    close: row.close,
    price: row.close,
    volume: row.volume,
    providers: row.providers ? JSON.parse(row.providers) : [],
    dataPoints: row.data_points,
    variance: row.variance
  }));

  const firstPrice = candles[0]?.close || 0;
  const lastPrice = candles[candles.length - 1]?.close || 0;
  const priceChange = firstPrice > 0
    ? ((lastPrice - firstPrice) / firstPrice * 100).toFixed(2) + '%'
    : '0%';

  return new Response(JSON.stringify({
    success: true,
    source: "d1",
    symbol,
    timeframe,
    days,
    candles: candles.length,
    first: candles[0]?.timestamp,
    last: candles[candles.length - 1]?.timestamp,
    firstPrice,
    lastPrice,
    priceChange,
    data: candles
  }, null, 2), {
    headers: { ...corsHeaders, 'Content-Type': 'application/json' }
  });
}


/**
 * Get data coverage
 */
async function handleCoverage(url, env, corsHeaders) {
  const symbol = url.searchParams.get('symbol');

  let query;
  if (symbol) {
    query = await env.DB.prepare(`
      SELECT
        symbol,
        timeframe,
        MIN(start_timestamp) as earliest,
        MAX(end_timestamp) as latest,
        SUM(candle_count) as total_candles,
        MAX(last_updated) as last_updated
      FROM data_coverage
      WHERE symbol = ?
      GROUP BY symbol, timeframe
    `).bind(symbol).all();
  } else {
    query = await env.DB.prepare(`
      SELECT
        symbol,
        timeframe,
        MIN(start_timestamp) as earliest,
        MAX(end_timestamp) as latest,
        SUM(candle_count) as total_candles,
        MAX(last_updated) as last_updated
      FROM data_coverage
      GROUP BY symbol, timeframe
    `).all();
  }

  const coverage = query.results.map(row => ({
    symbol: row.symbol,
    timeframe: row.timeframe,
    earliest: new Date(row.earliest * 1000).toISOString(),
    latest: new Date(row.latest * 1000).toISOString(),
    totalCandles: row.total_candles,
    lastUpdated: new Date(row.last_updated * 1000).toISOString()
  }));

  return new Response(JSON.stringify({
    success: true,
    coverage
  }, null, 2), {
    headers: { ...corsHeaders, 'Content-Type': 'application/json' }
  });
}


/**
 * Get statistics
 */
async function handleStats(url, env, corsHeaders) {
  const symbol = url.searchParams.get('symbol') || 'BTC';
  const period = url.searchParams.get('period') || '30d';

  const result = await env.DB.prepare(`
    SELECT * FROM price_stats
    WHERE symbol = ? AND period = ?
    ORDER BY start_timestamp DESC
    LIMIT 1
  `).bind(symbol, period).first();

  if (!result) {
    return new Response(JSON.stringify({
      success: false,
      error: `No stats found for ${symbol} ${period}`
    }), {
      status: 404,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }

  return new Response(JSON.stringify({
    success: true,
    symbol: result.symbol,
    period: result.period,
    startDate: new Date(result.start_timestamp * 1000).toISOString(),
    endDate: new Date(result.end_timestamp * 1000).toISOString(),
    openPrice: result.open_price,
    closePrice: result.close_price,
    highPrice: result.high_price,
    lowPrice: result.low_price,
    priceChangePct: result.price_change_pct,
    totalVolume: result.total_volume,
    avgVolume: result.avg_volume,
    volatility: result.volatility
  }, null, 2), {
    headers: { ...corsHeaders, 'Content-Type': 'application/json' }
  });
}


/**
 * Store data in D1
 */
async function handleStore(request, env, corsHeaders) {
  const data = await request.json();

  if (!data.symbol || !data.candles) {
    return new Response(JSON.stringify({
      error: "Missing symbol or candles"
    }), {
      status: 400,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }

  let inserted = 0;
  let updated = 0;

  for (const candle of data.candles) {
    const timestamp = Math.floor(new Date(candle.timestamp).getTime() / 1000);

    try {
      await env.DB.prepare(`
        INSERT INTO price_data
          (symbol, timestamp, timeframe, open, high, low, close, volume, providers, data_points, variance)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol, timestamp, timeframe)
        DO UPDATE SET
          open = excluded.open,
          high = excluded.high,
          low = excluded.low,
          close = excluded.close,
          volume = excluded.volume,
          providers = excluded.providers,
          data_points = excluded.data_points,
          variance = excluded.variance
      `).bind(
        data.symbol,
        timestamp,
        data.timeframe || '1h',
        candle.open,
        candle.high,
        candle.low,
        candle.close,
        candle.volume || 0,
        JSON.stringify(candle.providers || []),
        candle.dataPoints || 1,
        candle.variance || 0
      ).run();

      inserted++;
    } catch (e) {
      console.error(`Error inserting candle: ${e.message}`);
    }
  }

  // Update coverage
  const timestamps = data.candles.map(c => Math.floor(new Date(c.timestamp).getTime() / 1000));
  const startTime = Math.min(...timestamps);
  const endTime = Math.max(...timestamps);

  await env.DB.prepare(`
    INSERT INTO data_coverage (symbol, timeframe, start_timestamp, end_timestamp, candle_count)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(symbol, timeframe, start_timestamp)
    DO UPDATE SET
      end_timestamp = excluded.end_timestamp,
      candle_count = excluded.candle_count,
      last_updated = strftime('%s', 'now')
  `).bind(
    data.symbol,
    data.timeframe || '1h',
    startTime,
    endTime,
    data.candles.length
  ).run();

  return new Response(JSON.stringify({
    success: true,
    symbol: data.symbol,
    inserted,
    updated
  }, null, 2), {
    headers: { ...corsHeaders, 'Content-Type': 'application/json' }
  });
}


/**
 * Fetch fresh data from external API
 * (Keep existing fetch logic from original worker)
 */
async function handleFetch(url, env, corsHeaders) {
  // ... existing fetch logic ...
  return new Response(JSON.stringify({
    info: "Fetch endpoint - implement Binance API fetch here"
  }), {
    headers: { ...corsHeaders, 'Content-Type': 'application/json' }
  });
}
