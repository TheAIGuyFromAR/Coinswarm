/**
 * INSTRUCTIONS FOR OTHER CLAUDE:
 *
 * Please deploy this Cloudflare Worker to fetch crypto data.
 *
 * Steps:
 * 1. Create a new Cloudflare Worker named "coinswarm-data-fetcher"
 * 2. Copy this entire file as the Worker code
 * 3. Deploy it
 * 4. Return the deployed Worker URL to the user
 *
 * The Worker URL will be:
 * https://coinswarm-data-fetcher.[subdomain].workers.dev
 *
 * User needs this URL to fetch historical crypto data for backtesting.
 */

export default {
  async fetch(request, env, ctx) {
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

    // Route: Fetch data from Binance
    if (path === '/fetch') {
      return await handleFetch(url, env, corsHeaders);
    }

    // Default: Show available endpoints
    return new Response(JSON.stringify({
      status: "ok",
      message: "Coinswarm Data Fetcher",
      endpoints: {
        fetch: "/fetch?symbol=BTCUSDT&timeframe=1h&days=30"
      },
      examples: [
        "?symbol=BTCUSDT&timeframe=1h&days=7",
        "?symbol=ETHUSDT&timeframe=1h&days=30",
        "?symbol=SOLUSDT&timeframe=1h&days=90"
      ]
    }, null, 2), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
};

async function handleFetch(url, env, corsHeaders) {
  const symbol = url.searchParams.get('symbol') || 'BTCUSDT';
  const timeframe = url.searchParams.get('timeframe') || '1h';
  const days = parseInt(url.searchParams.get('days') || '30');

  // Validate timeframe
  const validTimeframes = ['1m', '5m', '15m', '1h', '4h', '1d'];
  if (!validTimeframes.includes(timeframe)) {
    return new Response(JSON.stringify({
      error: `Invalid timeframe. Use: ${validTimeframes.join(', ')}`
    }), {
      status: 400,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }

  // Validate days (max 365)
  if (days < 1 || days > 365) {
    return new Response(JSON.stringify({
      error: 'Days must be between 1 and 365'
    }), {
      status: 400,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }

  try {
    // Calculate timestamps
    const now = Date.now();
    const startTime = now - (days * 24 * 60 * 60 * 1000);

    // Binance API endpoint (public, no auth needed)
    const binanceUrl = `https://api.binance.com/api/v3/klines?` +
      `symbol=${symbol}&interval=${timeframe}&startTime=${startTime}&endTime=${now}&limit=1000`;

    console.log(`Fetching ${symbol} ${timeframe} for ${days} days from Binance`);

    // Fetch from Binance
    const response = await fetch(binanceUrl);

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Binance API error: ${response.status} - ${errorText}`);
    }

    const data = await response.json();

    // Transform to readable format
    const transformed = data.map(candle => ({
      timestamp: new Date(candle[0]).toISOString(),
      open: parseFloat(candle[1]),
      high: parseFloat(candle[2]),
      low: parseFloat(candle[3]),
      close: parseFloat(candle[4]),
      price: parseFloat(candle[4]),  // close = price
      volume: parseFloat(candle[5])
    }));

    console.log(`Successfully fetched ${transformed.length} candles for ${symbol}`);

    // Return data
    return new Response(JSON.stringify({
      success: true,
      symbol,
      timeframe,
      days,
      candles: transformed.length,
      first: transformed[0]?.timestamp,
      last: transformed[transformed.length - 1]?.timestamp,
      firstPrice: transformed[0]?.price,
      lastPrice: transformed[transformed.length - 1]?.price,
      priceChange: transformed.length > 0
        ? ((transformed[transformed.length - 1].price - transformed[0].price) / transformed[0].price * 100).toFixed(2) + '%'
        : '0%',
      data: transformed
    }, null, 2), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });

  } catch (error) {
    console.error('Error:', error.message);

    return new Response(JSON.stringify({
      error: error.message,
      symbol,
      timeframe,
      days,
      hint: 'Check if symbol is valid (e.g., BTCUSDT, ETHUSDT, SOLUSDT)'
    }, null, 2), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
}
