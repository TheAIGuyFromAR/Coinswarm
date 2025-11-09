/**
 * Data Collection Monitoring Dashboard
 *
 * Provides comprehensive monitoring and visualization of all data collection workers:
 * - Real-time price collection (every minute)
 * - Historical minute data (CryptoCompare)
 * - Historical hourly data (Binance.US)
 * - Historical daily data (CoinGecko)
 */

interface Env {
  DB: D1Database;
}

interface CollectionStats {
  totalTokens: number;
  minuteProgress: {
    completed: number;
    inProgress: number;
    paused: number;
    totalMinutesCollected: number;
    totalMinutesTarget: number;
    percentComplete: number;
  };
  hourlyProgress: {
    completed: number;
    inProgress: number;
    paused: number;
    totalHoursCollected: number;
    totalHoursTarget: number;
    percentComplete: number;
  };
  dailyProgress: {
    completed: number;
    inProgress: number;
    paused: number;
    totalDaysCollected: number;
    totalDaysTarget: number;
    percentComplete: number;
  };
  realtimePrices: {
    lastUpdate: number;
    pricesCollected: number;
    sourcesUsed: Record<string, number>;
  };
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    // CORS headers for frontend access
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
      'Content-Type': 'application/json'
    };

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    // Main dashboard endpoint
    if (url.pathname === '/' || url.pathname === '/dashboard') {
      const stats = await this.getCollectionStats(env);
      return new Response(this.renderHTML(stats), {
        headers: { 'Content-Type': 'text/html' }
      });
    }

    // JSON API endpoint
    if (url.pathname === '/api/stats') {
      const stats = await this.getCollectionStats(env);
      return new Response(JSON.stringify(stats, null, 2), { headers: corsHeaders });
    }

    // Token-specific progress
    if (url.pathname === '/api/tokens') {
      const tokens = await env.DB.prepare(`
        SELECT
          symbol,
          coin_id,
          minutes_collected,
          total_minutes,
          hours_collected,
          total_hours,
          days_collected,
          total_days,
          minute_status,
          hourly_status,
          daily_status,
          error_count,
          last_error
        FROM collection_progress
        ORDER BY symbol
      `).all();

      return new Response(JSON.stringify(tokens.results, null, 2), { headers: corsHeaders });
    }

    // Recent prices
    if (url.pathname === '/api/prices/recent') {
      const prices = await env.DB.prepare(`
        SELECT * FROM realtime_prices
        WHERE timestamp > ?
        ORDER BY timestamp DESC
        LIMIT 100
      `).bind(Math.floor(Date.now() / 1000) - 600).all(); // Last 10 minutes

      return new Response(JSON.stringify(prices.results, null, 2), { headers: corsHeaders });
    }

    // Rate limit bucket status
    if (url.pathname === '/api/buckets') {
      const buckets = await env.DB.prepare(`
        SELECT * FROM rate_limit_state
      `).all();

      return new Response(JSON.stringify(buckets.results, null, 2), { headers: corsHeaders });
    }

    // Health check
    if (url.pathname === '/health') {
      const health = {
        status: 'healthy',
        timestamp: Date.now(),
        workers: {
          historical: 'running',
          realtime: 'running',
          monitor: 'running'
        }
      };
      return new Response(JSON.stringify(health, null, 2), { headers: corsHeaders });
    }

    return new Response(JSON.stringify({ error: 'Not found' }), {
      status: 404,
      headers: corsHeaders
    });
  },

  async getCollectionStats(env: Env): Promise<CollectionStats> {
    // Get historical collection progress
    const progress = await env.DB.prepare(`
      SELECT
        COUNT(*) as total,
        SUM(CASE WHEN minute_status = 'completed' THEN 1 ELSE 0 END) as minute_complete,
        SUM(CASE WHEN hourly_status = 'completed' THEN 1 ELSE 0 END) as hourly_complete,
        SUM(CASE WHEN daily_status = 'completed' THEN 1 ELSE 0 END) as daily_complete,
        SUM(CASE WHEN minute_status = 'paused' THEN 1 ELSE 0 END) as minute_paused,
        SUM(CASE WHEN hourly_status = 'paused' THEN 1 ELSE 0 END) as hourly_paused,
        SUM(CASE WHEN daily_status = 'paused' THEN 1 ELSE 0 END) as daily_paused,
        SUM(minutes_collected) as total_minutes_collected,
        SUM(total_minutes) as total_minutes_target,
        SUM(hours_collected) as total_hours_collected,
        SUM(total_hours) as total_hours_target,
        SUM(days_collected) as total_days_collected,
        SUM(total_days) as total_days_target
      FROM collection_progress
    `).first() as any;

    // Get realtime price stats
    const realtimeStats = await env.DB.prepare(`
      SELECT
        MAX(timestamp) as last_update,
        COUNT(*) as total_prices,
        source
      FROM realtime_prices
      WHERE timestamp > ?
      GROUP BY source
    `).bind(Math.floor(Date.now() / 1000) - 3600).all(); // Last hour

    const sourcesUsed: Record<string, number> = {};
    for (const row of realtimeStats.results as any[]) {
      sourcesUsed[row.source] = row.total_prices;
    }

    const lastUpdate = realtimeStats.results.length > 0
      ? Math.max(...(realtimeStats.results as any[]).map((r: any) => r.last_update))
      : 0;

    const totalPrices = Object.values(sourcesUsed).reduce((a, b) => a + b, 0);

    return {
      totalTokens: progress.total || 0,
      minuteProgress: {
        completed: progress.minute_complete || 0,
        inProgress: (progress.total || 0) - (progress.minute_complete || 0) - (progress.minute_paused || 0),
        paused: progress.minute_paused || 0,
        totalMinutesCollected: progress.total_minutes_collected || 0,
        totalMinutesTarget: progress.total_minutes_target || 0,
        percentComplete: progress.total_minutes_target > 0
          ? Math.round((progress.total_minutes_collected / progress.total_minutes_target) * 100)
          : 0
      },
      hourlyProgress: {
        completed: progress.hourly_complete || 0,
        inProgress: (progress.total || 0) - (progress.hourly_complete || 0) - (progress.hourly_paused || 0),
        paused: progress.hourly_paused || 0,
        totalHoursCollected: progress.total_hours_collected || 0,
        totalHoursTarget: progress.total_hours_target || 0,
        percentComplete: progress.total_hours_target > 0
          ? Math.round((progress.total_hours_collected / progress.total_hours_target) * 100)
          : 0
      },
      dailyProgress: {
        completed: progress.daily_complete || 0,
        inProgress: (progress.total || 0) - (progress.daily_complete || 0) - (progress.daily_paused || 0),
        paused: progress.daily_paused || 0,
        totalDaysCollected: progress.total_days_collected || 0,
        totalDaysTarget: progress.total_days_target || 0,
        percentComplete: progress.total_days_target > 0
          ? Math.round((progress.total_days_collected / progress.total_days_target) * 100)
          : 0
      },
      realtimePrices: {
        lastUpdate,
        pricesCollected: totalPrices,
        sourcesUsed
      }
    };
  },

  renderHTML(stats: CollectionStats): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Coinswarm Data Collection Monitor</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      min-height: 100vh;
      padding: 20px;
      color: #333;
    }
    .container {
      max-width: 1400px;
      margin: 0 auto;
    }
    .header {
      text-align: center;
      color: white;
      margin-bottom: 30px;
    }
    .header h1 {
      font-size: 2.5rem;
      margin-bottom: 10px;
      text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    .header p {
      font-size: 1.1rem;
      opacity: 0.9;
    }
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 20px;
      margin-bottom: 30px;
    }
    .card {
      background: white;
      border-radius: 12px;
      padding: 24px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.2);
      transition: transform 0.2s;
    }
    .card:hover {
      transform: translateY(-5px);
    }
    .card-title {
      font-size: 1.2rem;
      font-weight: 600;
      margin-bottom: 16px;
      color: #667eea;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .progress-bar {
      width: 100%;
      height: 24px;
      background: #e0e0e0;
      border-radius: 12px;
      overflow: hidden;
      margin: 12px 0;
    }
    .progress-fill {
      height: 100%;
      background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
      transition: width 0.3s ease;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-weight: 600;
      font-size: 0.85rem;
    }
    .stat-row {
      display: flex;
      justify-content: space-between;
      padding: 8px 0;
      border-bottom: 1px solid #f0f0f0;
    }
    .stat-row:last-child {
      border-bottom: none;
    }
    .stat-label {
      color: #666;
    }
    .stat-value {
      font-weight: 600;
      color: #333;
    }
    .status-badge {
      display: inline-block;
      padding: 4px 12px;
      border-radius: 12px;
      font-size: 0.85rem;
      font-weight: 600;
    }
    .status-completed {
      background: #d4edda;
      color: #155724;
    }
    .status-running {
      background: #fff3cd;
      color: #856404;
    }
    .status-paused {
      background: #f8d7da;
      color: #721c24;
    }
    .refresh-notice {
      text-align: center;
      color: white;
      margin-top: 20px;
      font-size: 0.9rem;
      opacity: 0.8;
    }
    .emoji {
      font-size: 1.4rem;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>📊 Coinswarm Data Collection Monitor</h1>
      <p>Real-time tracking of historical and live price data collection</p>
    </div>

    <div class="stats-grid">
      <!-- Minute Data Card -->
      <div class="card">
        <div class="card-title">
          <span class="emoji">⏱️</span>
          Minute Data (CryptoCompare)
        </div>
        <div class="progress-bar">
          <div class="progress-fill" style="width: ${stats.minuteProgress.percentComplete}%">
            ${stats.minuteProgress.percentComplete}%
          </div>
        </div>
        <div class="stat-row">
          <span class="stat-label">Completed Tokens</span>
          <span class="stat-value">${stats.minuteProgress.completed}/${stats.totalTokens}</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">In Progress</span>
          <span class="stat-value">${stats.minuteProgress.inProgress}</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">Paused</span>
          <span class="stat-value">${stats.minuteProgress.paused}</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">Minutes Collected</span>
          <span class="stat-value">${stats.minuteProgress.totalMinutesCollected.toLocaleString()}/${stats.minuteProgress.totalMinutesTarget.toLocaleString()}</span>
        </div>
      </div>

      <!-- Hourly Data Card -->
      <div class="card">
        <div class="card-title">
          <span class="emoji">⏰</span>
          Hourly Data (Binance.US)
        </div>
        <div class="progress-bar">
          <div class="progress-fill" style="width: ${stats.hourlyProgress.percentComplete}%">
            ${stats.hourlyProgress.percentComplete}%
          </div>
        </div>
        <div class="stat-row">
          <span class="stat-label">Completed Tokens</span>
          <span class="stat-value">${stats.hourlyProgress.completed}/${stats.totalTokens}</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">In Progress</span>
          <span class="stat-value">${stats.hourlyProgress.inProgress}</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">Paused</span>
          <span class="stat-value">${stats.hourlyProgress.paused}</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">Hours Collected</span>
          <span class="stat-value">${stats.hourlyProgress.totalHoursCollected.toLocaleString()}/${stats.hourlyProgress.totalHoursTarget.toLocaleString()}</span>
        </div>
      </div>

      <!-- Daily Data Card -->
      <div class="card">
        <div class="card-title">
          <span class="emoji">📅</span>
          Daily Data (CoinGecko)
        </div>
        <div class="progress-bar">
          <div class="progress-fill" style="width: ${stats.dailyProgress.percentComplete}%">
            ${stats.dailyProgress.percentComplete}%
          </div>
        </div>
        <div class="stat-row">
          <span class="stat-label">Completed Tokens</span>
          <span class="stat-value">${stats.dailyProgress.completed}/${stats.totalTokens}</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">In Progress</span>
          <span class="stat-value">${stats.dailyProgress.inProgress}</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">Paused</span>
          <span class="stat-value">${stats.dailyProgress.paused}</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">Days Collected</span>
          <span class="stat-value">${stats.dailyProgress.totalDaysCollected.toLocaleString()}/${stats.dailyProgress.totalDaysTarget.toLocaleString()}</span>
        </div>
      </div>

      <!-- Real-time Prices Card -->
      <div class="card">
        <div class="card-title">
          <span class="emoji">🔴</span>
          Real-time Prices
        </div>
        <div class="stat-row">
          <span class="stat-label">Last Update</span>
          <span class="stat-value">${stats.realtimePrices.lastUpdate > 0 ? new Date(stats.realtimePrices.lastUpdate * 1000).toLocaleTimeString() : 'N/A'}</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">Prices Collected (1h)</span>
          <span class="stat-value">${stats.realtimePrices.pricesCollected}</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">Sources Used</span>
          <span class="stat-value">${Object.keys(stats.realtimePrices.sourcesUsed).length}</span>
        </div>
        ${Object.entries(stats.realtimePrices.sourcesUsed).map(([source, count]) => `
          <div class="stat-row">
            <span class="stat-label">${source}</span>
            <span class="stat-value">${count}</span>
          </div>
        `).join('')}
      </div>
    </div>

    <div class="refresh-notice">
      🔄 Auto-refreshing every 30 seconds
    </div>
  </div>

  <script>
    // Auto-refresh every 30 seconds
    setTimeout(() => location.reload(), 30000);
  </script>
</body>
</html>`;
  }
};
