/**
 * Cloudflare Worker: Historical Data Fetcher
 *
 * Fetches historical crypto data from Binance and caches it.
 *
 * Endpoints:
 * - GET /fetch?symbol=BTCUSDT&timeframe=1h&days=30
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

    // Route: Fetch fresh data from Binance
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
        fetch: '/fetch?symbol=BTCUSDT&timeframe=1h&days=30',
        cached: '/cached?symbol=BTCUSDT'
      },
      instructions: 'See README for usage'
    }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
};

/**
 * Fetch fresh data from Binance API
 */
async function handleFetch(url, env, corsHeaders) {
  const symbol = url.searchParams.get('symbol') || 'BTCUSDT';
  const timeframe = url.searchParams.get('timeframe') || '1h';
  const days = parseInt(url.searchParams.get('days') || '30');

  console.log(`Fetching ${symbol} ${timeframe} for ${days} days`);

  try {
    // Calculate timestamps
    const now = Date.now();
    const startTime = now - (days * 24 * 60 * 60 * 1000);

    // Binance API endpoint
    const binanceUrl = `https://api.binance.com/api/v3/klines?` +
      `symbol=${symbol}&interval=${timeframe}&startTime=${startTime}&endTime=${now}&limit=1000`;

    // Fetch from Binance
    const response = await fetch(binanceUrl);

    if (!response.ok) {
      throw new Error(`Binance API error: ${response.status}`);
    }

    const data = await response.json();

    // Transform to our format
    const transformed = data.map(candle => ({
      timestamp: new Date(candle[0]).toISOString(),
      open: parseFloat(candle[1]),
      high: parseFloat(candle[2]),
      low: parseFloat(candle[3]),
      close: parseFloat(candle[4]),
      volume: parseFloat(candle[5])
    }));

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
      cached: true
    }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });

  } catch (error) {
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
