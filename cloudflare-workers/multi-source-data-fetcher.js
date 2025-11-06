/**
 * Cloudflare Worker: Multi-Source Historical Data Fetcher
 *
 * Fetches 2+ years of historical data from multiple sources:
 * 1. CoinGecko (free, 365 days/call, goes back years)
 * 2. CryptoCompare (free, 2000 hours/call, goes back years)
 * 3. Kraken (backup)
 * 4. Coinbase (backup)
 * 5. Pyth Network (Solana oracle - future)
 *
 * Endpoints:
 * - GET /multi-price?symbol=BTC&days=730&aggregate=true
 * - GET /price (original endpoint for 30 days)
 *
 * Deploy: wrangler publish
 */

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    // CORS headers
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };

    // Handle OPTIONS for CORS
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    // Route: Multi-source historical data (2+ years)
    if (path === '/multi-price') {
      return await handleMultiSourcePrice(url, corsHeaders);
    }

    // Route: Original price endpoint (Kraken/Coinbase, 30 days)
    if (path === '/price') {
      return await handlePrice(url, corsHeaders);
    }

    // Route: DeFi data
    if (path === '/defi') {
      return await handleDefi(url, corsHeaders);
    }

    // Route: Oracle data (Pyth, Switchboard)
    if (path === '/oracle') {
      return await handleOracle(url, corsHeaders);
    }

    // Default: Instructions
    return new Response(JSON.stringify({
      status: 'ok',
      message: 'Coinswarm Multi-Source DeFi Data Fetcher',
      providers: {
        centralized: ['Kraken', 'Coinbase', 'CoinGecko', 'CryptoCompare'],
        defi: ['DeFiLlama', 'Jupiter (Solana)', 'Pyth Network'],
        oracles: ['Pyth', 'Switchboard']
      },
      endpoints: {
        'multi-price': '/multi-price?symbol=BTC&days=730&aggregate=true (2+ years from multiple sources)',
        price: '/price?symbol=BTC&days=7&aggregate=true (30 days max from Kraken/Coinbase)',
        defi: '/defi?protocol=uniswap (or chain=solana)',
        oracle: '/oracle?symbol=SOL&source=pyth'
      }
    }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
};

/**
 * Multi-source price fetcher (2+ years)
 */
async function handleMultiSourcePrice(url, corsHeaders) {
  const symbol = url.searchParams.get('symbol') || 'BTC';
  const days = parseInt(url.searchParams.get('days') || '730');
  const aggregate = url.searchParams.get('aggregate') === 'true';

  console.log(`Multi-source fetch: ${symbol} for ${days} days`);

  try {
    const allCandles = [];
    const providersUsed = [];

    // Source 1: CryptoCompare (best for historical data)
    console.log('Fetching from CryptoCompare...');
    const ccData = await fetchFromCryptoCompare(symbol, days);
    if (ccData && ccData.length > 0) {
      allCandles.push(...ccData);
      providersUsed.push('CryptoCompare');
      console.log(`CryptoCompare: ${ccData.length} candles`);
    }

    // Source 2: CoinGecko (if CryptoCompare insufficient)
    if (allCandles.length < days * 24 * 0.9) {  // Less than 90% coverage
      console.log('CryptoCompare insufficient, trying CoinGecko...');
      const cgData = await fetchFromCoinGecko(symbol, days);
      if (cgData && cgData.length > 0) {
        allCandles.push(...cgData);
        providersUsed.push('CoinGecko');
        console.log(`CoinGecko: ${cgData.length} candles`);
      }
    }

    // Deduplicate by timestamp
    const uniqueCandles = deduplicateCandles(allCandles);

    // Sort by timestamp
    uniqueCandles.sort((a, b) =>
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );

    if (uniqueCandles.length === 0) {
      throw new Error('No data fetched from any source');
    }

    // Calculate stats
    const firstPrice = uniqueCandles[0].price;
    const lastPrice = uniqueCandles[uniqueCandles.length - 1].price;
    const priceChange = ((lastPrice - firstPrice) / firstPrice * 100).toFixed(2);

    return new Response(JSON.stringify({
      success: true,
      symbol,
      days,
      aggregated: aggregate,
      dataPoints: uniqueCandles.length,
      providersUsed,
      first: uniqueCandles[0].timestamp,
      last: uniqueCandles[uniqueCandles.length - 1].timestamp,
      firstPrice,
      lastPrice,
      priceChange: `${priceChange > 0 ? '+' : ''}${priceChange}%`,
      data: uniqueCandles
    }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });

  } catch (error) {
    console.error('Multi-source fetch error:', error);
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

/**
 * Fetch from CryptoCompare (free, goes back years)
 */
async function fetchFromCryptoCompare(symbol, days) {
  // CryptoCompare limit: 2000 hours per call
  const hoursNeeded = days * 24;
  const callsNeeded = Math.ceil(hoursNeeded / 2000);

  const allCandles = [];
  const now = Math.floor(Date.now() / 1000);

  for (let i = 0; i < callsNeeded; i++) {
    const toTs = now - (i * 2000 * 3600);
    const limit = Math.min(2000, hoursNeeded - (i * 2000));

    const url = `https://min-api.cryptocompare.com/data/v2/histohour?fsym=${symbol}&tsym=USD&limit=${limit}&toTs=${toTs}`;

    try {
      const response = await fetch(url, {
        headers: { 'User-Agent': 'Coinswarm/1.0' }
      });

      if (!response.ok) {
        console.error(`CryptoCompare HTTP ${response.status}`);
        break;
      }

      const data = await response.json();

      if (data.Response !== 'Success') {
        console.error(`CryptoCompare error: ${data.Message}`);
        break;
      }

      const candles = data.Data?.Data || [];

      for (const candle of candles) {
        allCandles.push({
          timestamp: new Date(candle.time * 1000).toISOString(),
          open: candle.open,
          high: candle.high,
          low: candle.low,
          close: candle.close,
          price: candle.close,
          volume: candle.volumeto,
          source: 'cryptocompare'
        });
      }

      // Rate limit: wait 1s between calls
      if (i < callsNeeded - 1) {
        await sleep(1000);
      }

    } catch (error) {
      console.error(`CryptoCompare fetch error:`, error);
      break;
    }
  }

  return allCandles;
}

/**
 * Fetch from CoinGecko (free, 365 days at a time)
 */
async function fetchFromCoinGecko(symbol, days) {
  // Map symbol to CoinGecko ID
  const coinIds = {
    'BTC': 'bitcoin',
    'ETH': 'ethereum',
    'SOL': 'solana',
    'AVAX': 'avalanche-2',
    'MATIC': 'matic-network'
  };

  const coinId = coinIds[symbol];
  if (!coinId) {
    console.error(`Unknown CoinGecko ID for ${symbol}`);
    return null;
  }

  const allCandles = [];

  // CoinGecko max 365 days per call, need multiple calls for 2+ years
  const callsNeeded = Math.ceil(days / 365);

  for (let i = 0; i < callsNeeded; i++) {
    const daysThisCall = Math.min(365, days - (i * 365));

    const url = `https://api.coingecko.com/api/v3/coins/${coinId}/market_chart?vs_currency=usd&days=${daysThisCall}&interval=hourly`;

    try {
      const response = await fetch(url, {
        headers: { 'User-Agent': 'Coinswarm/1.0' }
      });

      if (!response.ok) {
        console.error(`CoinGecko HTTP ${response.status}`);
        break;
      }

      const data = await response.json();

      const prices = data.prices || [];
      const volumes = data.total_volumes || [];

      for (let j = 0; j < prices.length; j++) {
        const [timestamp, price] = prices[j];
        const volume = volumes[j] ? volumes[j][1] : 0;

        allCandles.push({
          timestamp: new Date(timestamp).toISOString(),
          price,
          volume,
          source: 'coingecko'
        });
      }

      // Rate limit: CoinGecko free tier allows 50 calls/min
      if (i < callsNeeded - 1) {
        await sleep(2000);  // 2s between calls
      }

    } catch (error) {
      console.error(`CoinGecko fetch error:`, error);
      break;
    }
  }

  return allCandles;
}

/**
 * Original price endpoint (Kraken/Coinbase aggregated)
 */
async function handlePrice(url, corsHeaders) {
  const symbol = url.searchParams.get('symbol') || 'BTC';
  const days = parseInt(url.searchParams.get('days') || '7');

  try {
    // Fetch from both Kraken and Coinbase
    const krakenData = await fetchFromKraken(symbol, days);
    const coinbaseData = await fetchFromCoinbase(symbol, days);

    // Aggregate
    const allCandles = [];
    if (krakenData) allCandles.push(...krakenData);
    if (coinbaseData) allCandles.push(...coinbaseData);

    const uniqueCandles = deduplicateCandles(allCandles);
    uniqueCandles.sort((a, b) =>
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );

    const providersUsed = [];
    if (krakenData && krakenData.length > 0) providersUsed.push('Kraken');
    if (coinbaseData && coinbaseData.length > 0) providersUsed.push('Coinbase');

    if (uniqueCandles.length === 0) {
      throw new Error('No data from Kraken or Coinbase');
    }

    const firstPrice = uniqueCandles[0].price;
    const lastPrice = uniqueCandles[uniqueCandles.length - 1].price;
    const priceChange = ((lastPrice - firstPrice) / firstPrice * 100).toFixed(2);

    return new Response(JSON.stringify({
      success: true,
      symbol,
      days,
      aggregated: true,
      dataPoints: uniqueCandles.length,
      providersUsed,
      first: uniqueCandles[0].timestamp,
      last: uniqueCandles[uniqueCandles.length - 1].timestamp,
      firstPrice,
      lastPrice,
      priceChange: `${priceChange > 0 ? '+' : ''}${priceChange}%`,
      data: uniqueCandles
    }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });

  } catch (error) {
    return new Response(JSON.stringify({
      success: false,
      error: error.message
    }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Fetch from Kraken
 */
async function fetchFromKraken(symbol, days) {
  const pairs = {
    'BTC': 'XXBTZUSD',
    'ETH': 'XETHZUSD',
    'SOL': 'SOLUSD'
  };

  const pair = pairs[symbol];
  if (!pair) return null;

  const since = Math.floor(Date.now() / 1000) - (days * 24 * 60 * 60);
  const url = `https://api.kraken.com/0/public/OHLC?pair=${pair}&interval=60&since=${since}`;

  try {
    const response = await fetch(url);
    if (!response.ok) return null;

    const data = await response.json();
    if (data.error && data.error.length > 0) return null;

    const ohlc = data.result[pair];
    if (!ohlc) return null;

    return ohlc.map(candle => ({
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

/**
 * Fetch from Coinbase
 */
async function fetchFromCoinbase(symbol, days) {
  const products = {
    'BTC': 'BTC-USD',
    'ETH': 'ETH-USD',
    'SOL': 'SOL-USD'
  };

  const product = products[symbol];
  if (!product) return null;

  // Coinbase max 300 candles per call
  const granularity = 3600;  // 1 hour
  const end = Math.floor(Date.now() / 1000);
  const start = end - (days * 24 * 60 * 60);

  const url = `https://api.exchange.coinbase.com/products/${product}/candles?start=${start}&end=${end}&granularity=${granularity}`;

  try {
    const response = await fetch(url, {
      headers: { 'User-Agent': 'Coinswarm/1.0' }
    });

    if (!response.ok) return null;

    const data = await response.json();

    return data.map(candle => ({
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

/**
 * Handle DeFi data requests
 */
async function handleDefi(url, corsHeaders) {
  // Placeholder for DeFiLlama, Jupiter integration
  return new Response(JSON.stringify({
    success: false,
    error: 'DeFi endpoints coming soon'
  }), {
    status: 501,
    headers: { ...corsHeaders, 'Content-Type': 'application/json' }
  });
}

/**
 * Handle oracle data requests (Pyth, Switchboard)
 */
async function handleOracle(url, corsHeaders) {
  // Placeholder for Pyth, Switchboard integration
  return new Response(JSON.stringify({
    success: false,
    error: 'Oracle endpoints coming soon'
  }), {
    status: 501,
    headers: { ...corsHeaders, 'Content-Type': 'application/json' }
  });
}

/**
 * Deduplicate candles by timestamp
 */
function deduplicateCandles(candles) {
  const seen = new Map();

  for (const candle of candles) {
    const ts = candle.timestamp;

    if (!seen.has(ts)) {
      seen.set(ts, candle);
    } else {
      // Average if duplicate (better than just keeping first)
      const existing = seen.get(ts);
      existing.price = (existing.price + candle.price) / 2;

      if (existing.volume !== undefined && candle.volume !== undefined) {
        existing.volume = (existing.volume + candle.volume) / 2;
      }
    }
  }

  return Array.from(seen.values());
}

/**
 * Sleep helper
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
