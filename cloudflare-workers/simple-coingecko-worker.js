/**
 * Simple Cloudflare Worker - CoinGecko Historical Data
 *
 * Uses CoinGecko's FREE API to fetch up to 365 days of data
 * No API key required!
 *
 * P0 Requirement: 180+ days ✅ (we can get 365 days)
 *
 * Endpoints:
 * - GET /data?symbol=BTC&days=180  (up to 365 days)
 *
 * Deploy: Auto-deployed via GitHub Actions
 * Last updated: 2025-11-06
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

    // Route: Fetch historical data
    if (path === '/data') {
      return await handleData(url, corsHeaders);
    }

    // Default: Instructions
    return new Response(JSON.stringify({
      status: 'ok',
      message: 'Coinswarm CoinGecko Data Fetcher',
      capabilities: {
        maxDays: 365,
        p0Met: true,
        apiKeyRequired: false
      },
      endpoints: {
        data: '/data?symbol=BTC&days=180 (up to 365 days, free)'
      },
      examples: [
        '/data?symbol=BTC&days=180  (6 months - P0)',
        '/data?symbol=BTC&days=365  (1 year - max free)',
        '/data?symbol=ETH&days=180',
        '/data?symbol=SOL&days=180'
      ]
    }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
};

async function handleData(url, corsHeaders) {
  const symbol = url.searchParams.get('symbol') || 'BTC';
  const days = Math.min(parseInt(url.searchParams.get('days') || '180'), 365);
  const interval = days > 90 ? 'daily' : 'hourly';

  console.log(`Fetching ${symbol} for ${days} days (${interval})`);

  try {
    const data = await fetchFromCoinGecko(symbol, days, interval);

    if (!data || data.length === 0) {
      throw new Error('No data returned from CoinGecko');
    }

    // Calculate stats
    const firstPrice = data[0].price;
    const lastPrice = data[data.length - 1].price;
    const priceChange = ((lastPrice - firstPrice) / firstPrice * 100).toFixed(2);

    // Calculate actual days covered
    const firstTime = new Date(data[0].timestamp).getTime();
    const lastTime = new Date(data[data.length - 1].timestamp).getTime();
    const actualDays = Math.round((lastTime - firstTime) / (24 * 60 * 60 * 1000));

    return new Response(JSON.stringify({
      success: true,
      symbol,
      requestedDays: days,
      actualDays,
      dataPoints: data.length,
      interval,
      source: 'coingecko',
      first: data[0].timestamp,
      last: data[data.length - 1].timestamp,
      firstPrice,
      lastPrice,
      priceChange: `${priceChange > 0 ? '+' : ''}${priceChange}%`,
      p0Met: actualDays >= 180,
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
      days
    }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
}

async function fetchFromCoinGecko(symbol, days, interval) {
  // Map symbols to CoinGecko IDs
  const coinIds = {
    'BTC': 'bitcoin',
    'ETH': 'ethereum',
    'SOL': 'solana',
    'AVAX': 'avalanche-2',
    'MATIC': 'matic-network',
    'ADA': 'cardano',
    'DOT': 'polkadot',
    'LINK': 'chainlink',
    'UNI': 'uniswap'
  };

  const coinId = coinIds[symbol] || coinIds['BTC'];

  const url = `https://api.coingecko.com/api/v3/coins/${coinId}/market_chart?vs_currency=usd&days=${days}&interval=${interval}`;

  console.log(`Fetching: ${url}`);

  try {
    const response = await fetch(url, {
      headers: {
        'User-Agent': 'Coinswarm/1.0',
        'Accept': 'application/json'
      }
    });

    if (!response.ok) {
      console.error(`CoinGecko HTTP ${response.status}`);
      throw new Error(`CoinGecko returned ${response.status}`);
    }

    const data = await response.json();

    // Check for API error
    if (data.error) {
      console.error('CoinGecko API error:', data.error);
      throw new Error(data.error.error_message || 'CoinGecko API error');
    }

    const prices = data.prices || [];
    const volumes = data.total_volumes || [];

    const candles = [];
    for (let i = 0; i < prices.length; i++) {
      const [timestamp, price] = prices[i];
      const volume = volumes[i] ? volumes[i][1] : 0;

      candles.push({
        timestamp: new Date(timestamp).toISOString(),
        price,
        volume,
        source: 'coingecko'
      });
    }

    console.log(`Fetched ${candles.length} candles`);
    return candles;

  } catch (error) {
    console.error('CoinGecko fetch error:', error);
    throw error;
  }
}
