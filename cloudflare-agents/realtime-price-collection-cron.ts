/**
 * Real-Time Price Collection Cron Worker
 *
 * Runs every minute to collect current prices for all tokens
 * Uses intelligent round-robin with leaky bucket algorithm
 *
 * Rate limiting: 50% of each API's documented rate limit
 * - CoinGecko: 15 calls/min (50% of 30)
 * - CryptoCompare: 15 calls/min (50% of 30)
 * - Binance.US: 600 weight/min (50% of 1200)
 * - DexScreener: 150 calls/min (50% of 300)
 *
 * Algorithm: Choose source with highest available capacity percentage
 *
 * Requires secrets: COINGECKO, CRYPTOCOMPARE_API_KEY (deployed via GitHub Actions)
 */

interface Env {
  DB: D1Database;
  COINGECKO?: string;
  CRYPTOCOMPARE_API_KEY?: string;
}

interface RateLimitBucket {
  service: string;
  capacity: number;
  tokensRemaining: number;
  refillRate: number; // tokens per second
  lastRefill: number;
}

interface TokenPrice {
  symbol: string;
  price: number;
  timestamp: number;
  source: string;
}

// Token configuration
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

// Rate limit buckets (50% of documented max)
const RATE_LIMIT_BUCKETS = {
  coingecko: { capacity: 15, refillRate: 15 / 60 }, // 15 per minute = 0.25 per second
  cryptocompare: { capacity: 15, refillRate: 15 / 60 },
  binance: { capacity: 600, refillRate: 600 / 60 }, // 600 weight per minute = 10 per second
  dexscreener: { capacity: 150, refillRate: 150 / 60 }
};

/**
 * Leaky Bucket Rate Limiter
 * Tracks available capacity for each API service
 */
class LeakyBucketManager {
  private db: D1Database;

  constructor(db: D1Database) {
    this.db = db;
  }

  async initialize() {
    await this.db.prepare(`
      CREATE TABLE IF NOT EXISTS rate_limit_state (
        service TEXT PRIMARY KEY,
        capacity REAL NOT NULL,
        tokens_remaining REAL NOT NULL,
        refill_rate REAL NOT NULL,
        last_refill INTEGER NOT NULL
      )
    `).run();

    // Seed initial state
    const now = Date.now();
    for (const [service, config] of Object.entries(RATE_LIMIT_BUCKETS)) {
      await this.db.prepare(`
        INSERT OR IGNORE INTO rate_limit_state (service, capacity, tokens_remaining, refill_rate, last_refill)
        VALUES (?, ?, ?, ?, ?)
      `).bind(service, config.capacity, config.capacity, config.refillRate, now).run();
    }
  }

  /**
   * Refill buckets based on time elapsed since last refill
   */
  async refillBuckets() {
    const now = Date.now();
    const buckets = await this.db.prepare(`SELECT * FROM rate_limit_state`).all();

    for (const bucket of buckets.results as any[]) {
      const timeSinceRefill = (now - bucket.last_refill) / 1000; // seconds
      const tokensToAdd = timeSinceRefill * bucket.refill_rate;
      const newTokens = Math.min(bucket.capacity, bucket.tokens_remaining + tokensToAdd);

      await this.db.prepare(`
        UPDATE rate_limit_state
        SET tokens_remaining = ?, last_refill = ?
        WHERE service = ?
      `).bind(newTokens, now, bucket.service).run();
    }
  }

  /**
   * Get service with highest available capacity percentage
   */
  async getBestService(): Promise<string> {
    await this.refillBuckets();

    const buckets = await this.db.prepare(`SELECT * FROM rate_limit_state`).all();
    let bestService = '';
    let highestPercentage = 0;

    for (const bucket of buckets.results as any[]) {
      const percentage = bucket.tokens_remaining / bucket.capacity;
      if (percentage > highestPercentage) {
        highestPercentage = percentage;
        bestService = bucket.service;
      }
    }

    return bestService;
  }

  /**
   * Consume tokens from a service's bucket
   */
  async consumeTokens(service: string, amount: number = 1) {
    await this.db.prepare(`
      UPDATE rate_limit_state
      SET tokens_remaining = tokens_remaining - ?
      WHERE service = ?
    `).bind(amount, service).run();
  }

  /**
   * Get current state of all buckets
   */
  async getState() {
    await this.refillBuckets();
    const buckets = await this.db.prepare(`SELECT * FROM rate_limit_state`).all();
    return buckets.results.map((b: any) => ({
      service: b.service,
      tokensRemaining: b.tokens_remaining,
      capacity: b.capacity,
      utilization: `${Math.round((b.tokens_remaining / b.capacity) * 100)}%`
    }));
  }
}

/**
 * CoinGecko Simple Price API
 */
class CoinGeckoClient {
  private apiKey?: string;

  constructor(apiKey?: string) {
    this.apiKey = apiKey;
  }

  async getCurrentPrice(coinId: string): Promise<number> {
    const headers: Record<string, string> = { 'Accept': 'application/json' };
    if (this.apiKey) {
      headers['x-cg-demo-api-key'] = this.apiKey;
    }

    const url = `https://api.coingecko.com/api/v3/simple/price?ids=${coinId}&vs_currencies=usd`;
    const response = await fetch(url, { headers });

    if (!response.ok) {
      throw new Error(`CoinGecko API error: ${response.status}`);
    }

    const data = await response.json() as any;
    return data[coinId]?.usd || 0;
  }
}

/**
 * CryptoCompare Price API
 */
class CryptoCompareClient {
  private apiKey?: string;

  constructor(apiKey?: string) {
    this.apiKey = apiKey;
  }

  async getCurrentPrice(symbol: string): Promise<number> {
    const fsym = symbol.replace(/USDT|USDC|BUSD/g, '');
    let url = `https://min-api.cryptocompare.com/data/price?fsym=${fsym}&tsyms=USD`;

    if (this.apiKey) {
      url += `&api_key=${this.apiKey}`;
    }

    const response = await fetch(url, { headers: { 'Accept': 'application/json' } });

    if (!response.ok) {
      throw new Error(`CryptoCompare API error: ${response.status}`);
    }

    const data = await response.json() as any;
    return data.USD || 0;
  }
}

/**
 * Binance.US Ticker Price API
 */
class BinanceClient {
  async getCurrentPrice(symbol: string): Promise<number> {
    const url = `https://api.binance.us/api/v3/ticker/price?symbol=${symbol}`;
    const response = await fetch(url, { headers: { 'Accept': 'application/json' } });

    if (!response.ok) {
      throw new Error(`Binance API error: ${response.status}`);
    }

    const data = await response.json() as any;
    return parseFloat(data.price) || 0;
  }
}

/**
 * DexScreener Price API
 */
class DexScreenerClient {
  async getCurrentPrice(symbol: string): Promise<number> {
    // DexScreener uses token addresses, so this is a simplified example
    // In production, you'd need to map symbols to token addresses
    const baseSymbol = symbol.replace(/USDT|USDC|BUSD/g, '');
    const url = `https://api.dexscreener.com/latest/dex/search?q=${baseSymbol}`;

    const response = await fetch(url, { headers: { 'Accept': 'application/json' } });

    if (!response.ok) {
      throw new Error(`DexScreener API error: ${response.status}`);
    }

    const data = await response.json() as any;
    const pair = data.pairs?.[0];
    return parseFloat(pair?.priceUsd) || 0;
  }
}

export default {
  async scheduled(event: ScheduledEvent, env: Env, ctx: ExecutionContext) {
    console.log('⏰ Starting real-time price collection...');

    const bucketManager = new LeakyBucketManager(env.DB);
    await bucketManager.initialize();

    // Initialize API clients
    const clients = {
      coingecko: new CoinGeckoClient(env.COINGECKO),
      cryptocompare: new CryptoCompareClient(env.CRYPTOCOMPARE_API_KEY),
      binance: new BinanceClient(),
      dexscreener: new DexScreenerClient()
    };

    // Ensure price_data table exists
    await env.DB.prepare(`
      CREATE TABLE IF NOT EXISTS realtime_prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        price REAL NOT NULL,
        timestamp INTEGER NOT NULL,
        source TEXT NOT NULL,
        created_at INTEGER DEFAULT (strftime('%s', 'now')),
        UNIQUE(symbol, timestamp, source)
      )
    `).run();

    const prices: TokenPrice[] = [];
    const now = Date.now();

    // Collect prices for all tokens using intelligent source selection
    for (const token of TOKENS) {
      try {
        // Choose best service (highest available capacity)
        const bestService = await bucketManager.getBestService();
        console.log(`📊 Fetching ${token.symbol} from ${bestService}`);

        let price = 0;

        // Fetch price from chosen service
        switch (bestService) {
          case 'coingecko':
            price = await clients.coingecko.getCurrentPrice(token.coinId);
            await bucketManager.consumeTokens('coingecko', 1);
            break;
          case 'cryptocompare':
            price = await clients.cryptocompare.getCurrentPrice(token.symbol);
            await bucketManager.consumeTokens('cryptocompare', 1);
            break;
          case 'binance':
            price = await clients.binance.getCurrentPrice(token.symbol);
            await bucketManager.consumeTokens('binance', 1); // Weight of 1 for ticker price
            break;
          case 'dexscreener':
            price = await clients.dexscreener.getCurrentPrice(token.symbol);
            await bucketManager.consumeTokens('dexscreener', 1);
            break;
        }

        if (price > 0) {
          prices.push({
            symbol: token.symbol,
            price,
            timestamp: Math.floor(now / 1000),
            source: bestService
          });

          // Store in database
          await env.DB.prepare(`
            INSERT OR REPLACE INTO realtime_prices (symbol, price, timestamp, source)
            VALUES (?, ?, ?, ?)
          `).bind(token.symbol, price, Math.floor(now / 1000), bestService).run();

          console.log(`✅ ${token.symbol}: $${price.toFixed(2)} (${bestService})`);
        }

      } catch (error) {
        console.error(`❌ Error fetching ${token.symbol}:`, error);
      }
    }

    // Log bucket state
    const bucketState = await bucketManager.getState();
    console.log('📊 Rate limit bucket state:', JSON.stringify(bucketState, null, 2));

    console.log(`✅ Collected ${prices.length}/${TOKENS.length} prices`);
  },

  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === '/status') {
      const bucketManager = new LeakyBucketManager(env.DB);
      await bucketManager.initialize();
      const bucketState = await bucketManager.getState();

      const recentPrices = await env.DB.prepare(`
        SELECT * FROM realtime_prices
        WHERE timestamp > ?
        ORDER BY timestamp DESC
        LIMIT 50
      `).bind(Math.floor(Date.now() / 1000) - 300).all(); // Last 5 minutes

      return new Response(JSON.stringify({
        success: true,
        buckets: bucketState,
        recentPrices: recentPrices.results,
        tokensTracked: TOKENS.length
      }, null, 2), { headers: { 'Content-Type': 'application/json' } });
    }

    if (url.pathname === '/latest') {
      const prices = await env.DB.prepare(`
        SELECT DISTINCT ON (symbol) *
        FROM realtime_prices
        ORDER BY symbol, timestamp DESC
      `).all();

      return new Response(JSON.stringify({
        success: true,
        prices: prices.results,
        count: prices.results.length
      }, null, 2), { headers: { 'Content-Type': 'application/json' } });
    }

    return new Response(JSON.stringify({
      status: 'ok',
      name: 'Real-Time Price Collection Worker',
      schedule: 'Every minute',
      algorithm: 'Leaky bucket with intelligent round-robin',
      rateLimits: '25% of each API max capacity',
      tokens: TOKENS.length,
      endpoints: ['/status', '/latest']
    }, null, 2), { headers: { 'Content-Type': 'application/json' } });
  }
};
