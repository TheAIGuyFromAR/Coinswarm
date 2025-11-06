/**
 * Cloudflare Worker: Historical Data Fetcher (PAGINATED FOR 2+ YEARS)
 *
 * Fetches historical crypto data from Binance with pagination.
 * Can now get 2+ years instead of just 30 days!
 *
 * Endpoints:
 * - GET /fetch?symbol=BTCUSDT&timeframe=1h&days=730  (2 years!)
 * - GET /cached?symbol=BTCUSDT
 *
 * Deploy: wrangler publish
 * Free tier: 100K requests/day
 */

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    // CORS headers
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };

    // Handle OPTIONS for CORS
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    // Route: Fetch fresh data from Binance (WITH PAGINATION!)
    if (path === '/fetch') {
      return await handleFetch(url, env, corsHeaders);
    }

    // Route: Get cached data
    if (path === '/cached') {
      return await handleCached(url, env, corsHeaders);
    }

    // Default: Instructions
    return new Response(JSON.stringify({
      endpoints: {
        fetch: '/fetch?symbol=BTCUSDT&timeframe=1h&days=730 (NOW SUPPORTS 2+ YEARS!)',
        cached: '/cached?symbol=BTCUSDT'
      },
      instructions: 'See README for usage',
      update: 'Now supports 2+ years via Binance pagination!'
    }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
};

/**
 * Fetch fresh data from Binance API (PAGINATED)
 */
async function handleFetch(url, env, corsHeaders) {
  const symbol = url.searchParams.get('symbol') || 'BTCUSDT';
  const timeframe = url.searchParams.get('timeframe') || '1h';
  const days = parseInt(url.searchParams.get('days') || '30');

  console.log(`Fetching ${symbol} ${timeframe} for ${days} days (with pagination)`);

  try {
    // Fetch ALL candles using pagination
    const allCandles = await fetchAllCandlesPaginated(symbol, timeframe, days);

    if (!allCandles || allCandles.length === 0) {
      throw new Error('No data returned from Binance');
    }

    // Transform to our format
    const transformed = allCandles.map(candle => ({
      timestamp: new Date(candle[0]).toISOString(),
      open: parseFloat(candle[1]),
      high: parseFloat(candle[2]),
      low: parseFloat(candle[3]),
      close: parseFloat(candle[4]),
      volume: parseFloat(candle[5])
    }));

    console.log(`Successfully fetched ${transformed.length} candles`);

    // Cache in KV storage (if available)
    if (env.DATA_CACHE) {
      const cacheKey = `${symbol}_${timeframe}_${days}d`;
      await env.DATA_CACHE.put(cacheKey, JSON.stringify(transformed), {
        expirationTtl: 3600  // Cache for 1 hour
      });
      console.log(`Cached ${transformed.length} candles at ${cacheKey}`);
    }

    return new Response(JSON.stringify({
      symbol,
      timeframe,
      days,
      candles: transformed.length,
      data: transformed,
      cached: true,
      paginated: true  // Indicate this used pagination
    }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });

  } catch (error) {
    console.error('Error fetching data:', error);
    return new Response(JSON.stringify({
      error: error.message,
      symbol,
      timeframe,
      days
    }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Fetch all candles from Binance with pagination
 * Loops until we have all requested data
 */
async function fetchAllCandlesPaginated(symbol, timeframe, days) {
  const allCandles = [];
  const now = Date.now();
  const targetStart = now - (days * 24 * 60 * 60 * 1000);

  let currentStart = targetStart;
  let attempts = 0;
  const maxAttempts = Math.ceil(days / 42) + 5;  // ~42 days per 1000 candles + buffer

  console.log(`Target: ${days} days from ${new Date(targetStart).toISOString()} to ${new Date(now).toISOString()}`);

  while (allCandles.length < days * 24 && attempts < maxAttempts) {
    attempts++;

    // Binance API: fetch up to 1000 candles
    const binanceUrl = `https://api.binance.com/api/v3/klines?` +
      `symbol=${symbol}&interval=${timeframe}&startTime=${currentStart}&endTime=${now}&limit=1000`;

    console.log(`Attempt ${attempts}: Fetching from ${new Date(currentStart).toISOString()}`);

    try {
      const response = await fetch(binanceUrl);

      if (!response.ok) {
        console.error(`Binance API error: ${response.status}`);
        break;
      }

      const candles = await response.json();

      if (!candles || candles.length === 0) {
        console.log('No more candles available');
        break;
      }

      // Add to collection
      allCandles.push(...candles);
      console.log(`Fetched ${candles.length} candles, total: ${allCandles.length}`);

      // Move start time to after last candle
      const lastCandleTime = candles[candles.length - 1][0];
      currentStart = lastCandleTime + 1;

      // If we've reached current time, stop
      if (lastCandleTime >= now - (3600 * 1000)) {
        console.log('Reached current time');
        break;
      }

      // Rate limit: small delay between requests
      if (attempts < maxAttempts - 1) {
        await sleep(50);  // 50ms delay = 20 req/sec (Binance allows ~1200/min)
      }

    } catch (error) {
      console.error(`Error in pagination attempt ${attempts}:`, error);
      break;
    }
  }

  console.log(`Pagination complete: ${allCandles.length} candles in ${attempts} attempts`);
  return allCandles;
}

/**
 * Get cached data from KV storage
 */
async function handleCached(url, env, corsHeaders) {
  const symbol = url.searchParams.get('symbol') || 'BTCUSDT';
  const timeframe = url.searchParams.get('timeframe') || '1h';
  const days = parseInt(url.searchParams.get('days') || '30');

  if (!env.DATA_CACHE) {
    return new Response(JSON.stringify({
      error: 'KV storage not configured'
    }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }

  const cacheKey = `${symbol}_${timeframe}_${days}d`;
  const cached = await env.DATA_CACHE.get(cacheKey);

  if (!cached) {
    return new Response(JSON.stringify({
      error: 'No cached data',
      hint: `Use /fetch?symbol=${symbol}&timeframe=${timeframe}&days=${days} first`
    }), {
      status: 404,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }

  const data = JSON.parse(cached);

  return new Response(JSON.stringify({
    symbol,
    timeframe,
    days,
    candles: data.length,
    data,
    cached: true
  }), {
    headers: { ...corsHeaders, 'Content-Type': 'application/json' }
  });
}

/**
 * Sleep helper for rate limiting
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
