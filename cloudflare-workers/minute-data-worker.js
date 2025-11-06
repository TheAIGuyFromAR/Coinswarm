/**
 * Cloudflare Worker: Minute-Level Historical Data
 *
 * Fetches 5min, 15min, 30min, 1hour intervals from Kraken
 * Supports up to 720 candles per request (~2.5 days for 5min)
 *
 * Endpoints:
 * - GET /data?symbol=BTC&interval=5m&limit=720
 * - GET /data?symbol=BTC&interval=15m&limit=720
 * - GET /data?symbol=BTC&interval=30m&limit=720
 * - GET /data?symbol=BTC&interval=1h&limit=720
 *
 * For longer periods, use pagination:
 * - GET /data?symbol=BTC&interval=5m&limit=720&since=TIMESTAMP
 */

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    if (path === '/data') {
      return await handleData(url, corsHeaders);
    }

    // Default: Instructions
    return new Response(JSON.stringify({
      status: 'ok',
      message: 'Coinswarm Minute-Level Data Fetcher',
      intervals: {
        '5m': '5 minutes (720 candles = 2.5 days)',
        '15m': '15 minutes (720 candles = 7.5 days)',
        '30m': '30 minutes (720 candles = 15 days)',
        '1h': '1 hour (720 candles = 30 days)'
      },
      endpoints: {
        data: '/data?symbol=BTC&interval=5m&limit=720'
      },
      examples: [
        '/data?symbol=BTC&interval=5m&limit=720  (2.5 days at 5min)',
        '/data?symbol=BTC&interval=15m&limit=720 (7.5 days at 15min)',
        '/data?symbol=BTC&interval=30m&limit=720 (15 days at 30min)',
        '/data?symbol=ETH&interval=5m&limit=500',
        '/data?symbol=SOL&interval=15m&limit=1000'
      ],
      pagination: {
        note: 'For data older than max period, use since parameter',
        example: '/data?symbol=BTC&interval=5m&limit=720&since=1699000000'
      }
    }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
};

async function handleData(url, corsHeaders) {
  const symbol = url.searchParams.get('symbol') || 'BTC';
  const interval = url.searchParams.get('interval') || '1h';
  const limit = Math.min(parseInt(url.searchParams.get('limit') || '720'), 720);
  const since = url.searchParams.get('since') || null;

  console.log(`Fetching ${symbol} ${interval} (${limit} candles)`);

  try {
    const data = await fetchFromKraken(symbol, interval, limit, since);

    if (!data || data.length === 0) {
      throw new Error('No data returned from Kraken');
    }

    // Calculate stats
    const firstPrice = data[0].close;
    const lastPrice = data[data.length - 1].close;
    const priceChange = ((lastPrice - firstPrice) / firstPrice * 100).toFixed(2);

    // Calculate time range
    const firstTime = new Date(data[0].timestamp).getTime();
    const lastTime = new Date(data[data.length - 1].timestamp).getTime();
    const durationHours = (lastTime - firstTime) / (1000 * 60 * 60);

    return new Response(JSON.stringify({
      success: true,
      symbol,
      interval,
      dataPoints: data.length,
      durationHours: durationHours.toFixed(2),
      source: 'kraken',
      first: data[0].timestamp,
      last: data[data.length - 1].timestamp,
      firstPrice,
      lastPrice,
      priceChange: `${priceChange > 0 ? '+' : ''}${priceChange}%`,
      nextSince: data[0].unix, // For pagination
      data
    }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });

  } catch (error) {
    console.error('Fetch error:', error);
    return new Response(JSON.stringify({
      success: false,
      error: error.message,
      symbol,
      interval
    }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
}

async function fetchFromKraken(symbol, interval, limit, since) {
  // Map symbols to Kraken pairs
  const pairs = {
    'BTC': 'XXBTZUSD',
    'ETH': 'XETHZUSD',
    'SOL': 'SOLUSD',
    'AVAX': 'AVAXUSD',
    'MATIC': 'MATICUSD',
    'ADA': 'ADAUSD',
    'DOT': 'DOTUSD'
  };

  const pair = pairs[symbol] || pairs['BTC'];

  // Map intervals to Kraken format (in minutes)
  const intervalMap = {
    '1m': 1,
    '5m': 5,
    '15m': 15,
    '30m': 30,
    '1h': 60,
    '4h': 240,
    '1d': 1440
  };

  const krakenInterval = intervalMap[interval] || 60;

  // Build URL
  let url = `https://api.kraken.com/0/public/OHLC?pair=${pair}&interval=${krakenInterval}`;

  if (since) {
    url += `&since=${since}`;
  }

  console.log(`Kraken URL: ${url}`);

  try {
    const response = await fetch(url);

    if (!response.ok) {
      console.error(`Kraken HTTP ${response.status}`);
      throw new Error(`Kraken returned ${response.status}`);
    }

    const data = await response.json();

    // Check for errors
    if (data.error && data.error.length > 0) {
      console.error('Kraken API error:', data.error);
      throw new Error(`Kraken error: ${data.error.join(', ')}`);
    }

    // Get OHLC data
    const ohlc = data.result[pair];
    if (!ohlc) {
      throw new Error(`No data for pair ${pair}`);
    }

    // Convert to our format
    const candles = ohlc.slice(0, limit).map(candle => ({
      timestamp: new Date(candle[0] * 1000).toISOString(),
      unix: candle[0],
      open: parseFloat(candle[1]),
      high: parseFloat(candle[2]),
      low: parseFloat(candle[3]),
      close: parseFloat(candle[4]),
      volume: parseFloat(candle[6]),
      trades: parseInt(candle[7]),
      source: 'kraken'
    }));

    // Reverse to have oldest first
    candles.reverse();

    console.log(`Fetched ${candles.length} candles`);
    return candles;

  } catch (error) {
    console.error('Kraken fetch error:', error);
    throw error;
  }
}
