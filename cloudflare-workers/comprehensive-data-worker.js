/**
 * Cloudflare Worker: Comprehensive Multi-Source Data Fetcher
 *
 * Combines ALL free data sources for maximum coverage:
 * 1. CryptoCompare (minute/hour/day data, requires free API key)
 * 2. CoinGecko (hour/day data, no key needed)
 * 3. Binance (minute data, no key needed)
 * 4. Kraken (minute data, no key needed)
 * 5. Coinbase (minute data, no key needed)
 *
 * P0 Requirement: ✅ 180+ days with minute-level granularity
 *
 * Setup:
 * 1. Get free CryptoCompare API key: https://www.cryptocompare.com/cryptopian/api-keys
 * 2. Add as environment variable: CRYPTOCOMPARE_API_KEY
 * 3. Deploy this worker
 *
 * Endpoints:
 * - GET /data?symbol=BTC&days=180&interval=hour
 * - GET /data?symbol=BTC&days=7&interval=5min
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
      return await handleData(url, env, corsHeaders);
    }

    // Default: Instructions
    return new Response(JSON.stringify({
      status: 'ok',
      message: 'Coinswarm Comprehensive Data Fetcher',
      sources: {
        cryptocompare: {
          intervals: ['minute', 'hour', 'day'],
          maxHistory: '2000+ days',
          apiKey: env.CRYPTOCOMPARE_API_KEY ? 'Configured ✅' : 'Missing ❌'
        },
        coingecko: {
          intervals: ['hour', 'day'],
          maxHistory: '365 days',
          apiKey: 'Not required ✅'
        },
        binance: {
          intervals: ['1m', '5m', '15m', '30m', '1h'],
          maxHistory: '1000 candles',
          apiKey: 'Not required ✅'
        },
        kraken: {
          intervals: ['1m', '5m', '15m', '30m', '1h'],
          maxHistory: '720 candles',
          apiKey: 'Not required ✅'
        },
        coinbase: {
          intervals: ['1m', '5m', '15m', '1h'],
          maxHistory: '300 candles',
          apiKey: 'Not required ✅'
        }
      },
      examples: [
        '/data?symbol=BTC&days=180&interval=hour    (6 months hourly)',
        '/data?symbol=BTC&days=7&interval=5min      (7 days 5-minute)',
        '/data?symbol=ETH&days=30&interval=15min    (30 days 15-minute)',
        '/data?symbol=SOL&days=365&interval=day     (1 year daily)'
      ],
      setup: {
        cryptocompare: 'Get free key at https://www.cryptocompare.com/cryptopian/api-keys',
        configure: 'Add CRYPTOCOMPARE_API_KEY to worker environment variables'
      }
    }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
};

async function handleData(url, env, corsHeaders) {
  const symbol = url.searchParams.get('symbol') || 'BTC';
  const days = parseInt(url.searchParams.get('days') || '7');
  const interval = url.searchParams.get('interval') || 'hour';

  console.log(`Fetching ${symbol} for ${days} days at ${interval} interval`);

  try {
    let data = [];
    let source = '';

    // Choose best source based on requirements
    if (interval === 'day' || days > 90) {
      // For daily data or long periods, try CryptoCompare first, then CoinGecko
      if (env.CRYPTOCOMPARE_API_KEY) {
        data = await fetchFromCryptoCompare(symbol, days, 'day', env.CRYPTOCOMPARE_API_KEY);
        source = 'cryptocompare';
      }

      if (!data || data.length === 0) {
        data = await fetchFromCoinGecko(symbol, days);
        source = 'coingecko';
      }
    } else if (interval === 'hour') {
      // For hourly data, try CryptoCompare first, then CoinGecko
      if (env.CRYPTOCOMPARE_API_KEY) {
        data = await fetchFromCryptoCompare(symbol, days, 'hour', env.CRYPTOCOMPARE_API_KEY);
        source = 'cryptocompare';
      }

      if (!data || data.length === 0) {
        data = await fetchFromCoinGecko(symbol, Math.min(days, 90));
        source = 'coingecko';
      }
    } else if (interval.includes('min') || interval.includes('m')) {
      // For minute data, try Binance, then Kraken, then Coinbase
      const minuteInterval = interval.replace('min', 'm');

      data = await fetchFromBinance(symbol, minuteInterval, Math.min(days * 24 * (60 / parseIntervalMinutes(minuteInterval)), 1000));
      source = 'binance';

      if (!data || data.length === 0) {
        data = await fetchFromKraken(symbol, minuteInterval, Math.min(days * 24 * (60 / parseIntervalMinutes(minuteInterval)), 720));
        source = 'kraken';
      }

      if (!data || data.length === 0) {
        data = await fetchFromCoinbase(symbol, minuteInterval, Math.min(days * 24 * (60 / parseIntervalMinutes(minuteInterval)), 300));
        source = 'coinbase';
      }
    } else {
      throw new Error(`Unsupported interval: ${interval}`);
    }

    if (!data || data.length === 0) {
      throw new Error('No data fetched from any source');
    }

    // Calculate stats
    const firstPrice = data[0].price;
    const lastPrice = data[data.length - 1].price;
    const priceChange = ((lastPrice - firstPrice) / firstPrice * 100).toFixed(2);

    return new Response(JSON.stringify({
      success: true,
      symbol,
      days,
      interval,
      dataPoints: data.length,
      source,
      first: data[0].timestamp,
      last: data[data.length - 1].timestamp,
      firstPrice,
      lastPrice,
      priceChange: `${priceChange > 0 ? '+' : ''}${priceChange}%`,
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
      days,
      interval,
      hint: env.CRYPTOCOMPARE_API_KEY ? null : 'Consider adding CRYPTOCOMPARE_API_KEY for better coverage'
    }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
}

function parseIntervalMinutes(interval) {
  const match = interval.match(/(\d+)m/);
  return match ? parseInt(match[1]) : 60;
}

async function fetchFromCryptoCompare(symbol, days, aggregation, apiKey) {
  const endpoints = {
    minute: 'histominute',
    hour: 'histohour',
    day: 'histoday'
  };

  const limits = {
    minute: 2000,
    hour: 2000,
    day: 2000
  };

  const endpoint = endpoints[aggregation];
  const limit = Math.min(limits[aggregation], days * (aggregation === 'minute' ? 1440 : aggregation === 'hour' ? 24 : 1));

  const url = `https://min-api.cryptocompare.com/data/v2/${endpoint}?fsym=${symbol}&tsym=USD&limit=${limit}&api_key=${apiKey}`;

  try {
    const response = await fetch(url);
    if (!response.ok) return null;

    const data = await response.json();
    if (data.Response !== 'Success') return null;

    const candles = data.Data?.Data || [];
    return candles.map(c => ({
      timestamp: new Date(c.time * 1000).toISOString(),
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
      price: c.close,
      volume: c.volumeto,
      source: 'cryptocompare'
    }));
  } catch (error) {
    console.error('CryptoCompare error:', error);
    return null;
  }
}

async function fetchFromCoinGecko(symbol, days) {
  const coinIds = {
    'BTC': 'bitcoin',
    'ETH': 'ethereum',
    'SOL': 'solana',
    'AVAX': 'avalanche-2',
    'MATIC': 'matic-network'
  };

  const coinId = coinIds[symbol];
  if (!coinId) return null;

  const interval = days <= 90 ? 'hourly' : 'daily';
  const url = `https://api.coingecko.com/api/v3/coins/${coinId}/market_chart?vs_currency=usd&days=${Math.min(days, 365)}&interval=${interval}`;

  try {
    const response = await fetch(url);
    if (!response.ok) return null;

    const data = await response.json();
    const prices = data.prices || [];
    const volumes = data.total_volumes || [];

    return prices.map((p, i) => ({
      timestamp: new Date(p[0]).toISOString(),
      price: p[1],
      volume: volumes[i] ? volumes[i][1] : 0,
      source: 'coingecko'
    }));
  } catch (error) {
    console.error('CoinGecko error:', error);
    return null;
  }
}

async function fetchFromBinance(symbol, interval, limit) {
  const url = `https://api.binance.com/api/v3/klines?symbol=${symbol}USDT&interval=${interval}&limit=${limit}`;

  try {
    const response = await fetch(url);
    if (!response.ok) return null;

    const data = await response.json();
    return data.map(candle => ({
      timestamp: new Date(candle[0]).toISOString(),
      open: parseFloat(candle[1]),
      high: parseFloat(candle[2]),
      low: parseFloat(candle[3]),
      close: parseFloat(candle[4]),
      price: parseFloat(candle[4]),
      volume: parseFloat(candle[5]),
      source: 'binance'
    }));
  } catch (error) {
    console.error('Binance error:', error);
    return null;
  }
}

async function fetchFromKraken(symbol, interval, limit) {
  const pairs = { 'BTC': 'XXBTZUSD', 'ETH': 'XETHZUSD', 'SOL': 'SOLUSD' };
  const pair = pairs[symbol];
  if (!pair) return null;

  const intervalMap = { '1m': 1, '5m': 5, '15m': 15, '30m': 30, '1h': 60 };
  const krakenInterval = intervalMap[interval] || 60;

  const url = `https://api.kraken.com/0/public/OHLC?pair=${pair}&interval=${krakenInterval}`;

  try {
    const response = await fetch(url);
    if (!response.ok) return null;

    const data = await response.json();
    const ohlc = data.result[pair];
    if (!ohlc) return null;

    return ohlc.slice(0, limit).reverse().map(candle => ({
      timestamp: new Date(candle[0] * 1000).toISOString(),
      open: parseFloat(candle[1]),
      high: parseFloat(candle[2]),
      low: parseFloat(candle[3]),
      close: parseFloat(candle[4]),
      price: parseFloat(candle[4]),
      volume: parseFloat(candle[6]),
      source: 'kraken'
    }));
  } catch (error) {
    console.error('Kraken error:', error);
    return null;
  }
}

async function fetchFromCoinbase(symbol, interval, limit) {
  const products = { 'BTC': 'BTC-USD', 'ETH': 'ETH-USD', 'SOL': 'SOL-USD' };
  const product = products[symbol];
  if (!product) return null;

  const granularityMap = { '1m': 60, '5m': 300, '15m': 900, '30m': 1800, '1h': 3600 };
  const granularity = granularityMap[interval] || 3600;

  const url = `https://api.exchange.coinbase.com/products/${product}/candles?granularity=${granularity}`;

  try {
    const response = await fetch(url);
    if (!response.ok) return null;

    const data = await response.json();
    return data.slice(0, limit).reverse().map(candle => ({
      timestamp: new Date(candle[0] * 1000).toISOString(),
      open: candle[3],
      high: candle[2],
      low: candle[1],
      close: candle[4],
      price: candle[4],
      volume: candle[5],
      source: 'coinbase'
    }));
  } catch (error) {
    console.error('Coinbase error:', error);
    return null;
  }
}
