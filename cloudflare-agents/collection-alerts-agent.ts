/**
 * Collection Alerts Agent
 *
 * Monitors data collection progress and sends alerts when milestones are reached:
 * - Daily data collection complete (all tokens)
 * - Hourly data collection complete (all tokens)
 * - Minute data collection 25%, 50%, 75%, 100% complete
 * - Individual token completion
 * - Error alerts (tokens paused due to errors)
 *
 * Runs every 15 minutes to check progress
 */

interface Env {
  DB: D1Database;
  WEBHOOK_URL?: string; // Optional webhook for external notifications
}

interface Alert {
  id?: number;
  alertType: string;
  message: string;
  severity: 'info' | 'warning' | 'success' | 'error';
  timestamp: number;
  acknowledged: boolean;
  metadata?: string;
}

interface CollectionMilestone {
  dailyComplete: boolean;
  hourlyComplete: boolean;
  minuteProgress: number;
  tokensWithErrors: number;
}

export default {
  async scheduled(event: ScheduledEvent, env: Env, ctx: ExecutionContext) {
    console.log('🔔 Starting collection alerts check...');

    await this.initializeTables(env);

    const milestones = await this.checkMilestones(env);
    const newAlerts: Alert[] = [];

    // Check daily data completion
    if (milestones.dailyComplete) {
      const alreadyAlerted = await this.hasAlert(env, 'daily_complete');
      if (!alreadyAlerted) {
        newAlerts.push({
          alertType: 'daily_complete',
          message: '🎉 Daily data collection complete! All 15 tokens have 5 years of daily OHLCV data.',
          severity: 'success',
          timestamp: Math.floor(Date.now() / 1000),
          acknowledged: false
        });
      }
    }

    // Check hourly data completion
    if (milestones.hourlyComplete) {
      const alreadyAlerted = await this.hasAlert(env, 'hourly_complete');
      if (!alreadyAlerted) {
        newAlerts.push({
          alertType: 'hourly_complete',
          message: '🎉 Hourly data collection complete! All 15 tokens have 5 years of hourly OHLCV data.',
          severity: 'success',
          timestamp: Math.floor(Date.now() / 1000),
          acknowledged: false
        });
      }
    }

    // Check minute data milestones (25%, 50%, 75%, 100%)
    const minuteMilestones = [25, 50, 75, 100];
    for (const milestone of minuteMilestones) {
      if (milestones.minuteProgress >= milestone) {
        const alertType = `minute_${milestone}`;
        const alreadyAlerted = await this.hasAlert(env, alertType);
        if (!alreadyAlerted) {
          newAlerts.push({
            alertType,
            message: `📊 Minute data collection ${milestone}% complete! Progress: ${Math.round(milestones.minuteProgress)}%`,
            severity: milestone === 100 ? 'success' : 'info',
            timestamp: Math.floor(Date.now() / 1000),
            acknowledged: false
          });
        }
      }
    }

    // Check for tokens with errors
    if (milestones.tokensWithErrors > 0) {
      const alreadyAlerted = await this.hasAlert(env, 'tokens_paused');
      if (!alreadyAlerted) {
        const pausedTokens = await env.DB.prepare(`
          SELECT symbol, last_error FROM collection_progress
          WHERE minute_status = 'paused' OR hourly_status = 'paused' OR daily_status = 'paused'
        `).all();

        const tokenList = pausedTokens.results.map((t: any) => t.symbol).join(', ');

        newAlerts.push({
          alertType: 'tokens_paused',
          message: `⚠️ ${milestones.tokensWithErrors} token(s) paused due to errors: ${tokenList}`,
          severity: 'warning',
          timestamp: Math.floor(Date.now() / 1000),
          acknowledged: false,
          metadata: JSON.stringify(pausedTokens.results)
        });
      }
    }

    // Store new alerts
    for (const alert of newAlerts) {
      await this.saveAlert(env, alert);
      console.log(`🔔 Alert: ${alert.message}`);

      // Send webhook notification if configured
      if (env.WEBHOOK_URL) {
        await this.sendWebhook(env.WEBHOOK_URL, alert);
      }
    }

    // Check for individual token completions
    await this.checkTokenCompletions(env);

    console.log(`✅ Alert check complete. ${newAlerts.length} new alerts created.`);
  },

  async initializeTables(env: Env) {
    await env.DB.prepare(`
      CREATE TABLE IF NOT EXISTS collection_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alert_type TEXT UNIQUE NOT NULL,
        message TEXT NOT NULL,
        severity TEXT NOT NULL,
        timestamp INTEGER NOT NULL,
        acknowledged BOOLEAN DEFAULT FALSE,
        metadata TEXT,
        created_at INTEGER DEFAULT (strftime('%s', 'now'))
      )
    `).run();

    // Index for faster queries
    await env.DB.prepare(`
      CREATE INDEX IF NOT EXISTS idx_alerts_type
      ON collection_alerts(alert_type, acknowledged)
    `).run();
  },

  async checkMilestones(env: Env): Promise<CollectionMilestone> {
    const stats = await env.DB.prepare(`
      SELECT
        COUNT(*) as total,
        SUM(CASE WHEN minute_status = 'completed' THEN 1 ELSE 0 END) as minute_complete,
        SUM(CASE WHEN hourly_status = 'completed' THEN 1 ELSE 0 END) as hourly_complete,
        SUM(CASE WHEN daily_status = 'completed' THEN 1 ELSE 0 END) as daily_complete,
        SUM(CASE WHEN minute_status = 'paused' OR hourly_status = 'paused' OR daily_status = 'paused' THEN 1 ELSE 0 END) as paused,
        SUM(minutes_collected) as total_minutes_collected,
        SUM(total_minutes) as total_minutes_target
      FROM collection_progress
    `).first() as any;

    return {
      dailyComplete: stats.daily_complete === stats.total,
      hourlyComplete: stats.hourly_complete === stats.total,
      minuteProgress: stats.total_minutes_target > 0
        ? (stats.total_minutes_collected / stats.total_minutes_target) * 100
        : 0,
      tokensWithErrors: stats.paused || 0
    };
  },

  async hasAlert(env: Env, alertType: string): Promise<boolean> {
    const existing = await env.DB.prepare(`
      SELECT id FROM collection_alerts WHERE alert_type = ?
    `).bind(alertType).first();

    return existing !== null;
  },

  async saveAlert(env: Env, alert: Alert) {
    await env.DB.prepare(`
      INSERT INTO collection_alerts (alert_type, message, severity, timestamp, acknowledged, metadata)
      VALUES (?, ?, ?, ?, ?, ?)
    `).bind(
      alert.alertType,
      alert.message,
      alert.severity,
      alert.timestamp,
      alert.acknowledged,
      alert.metadata || null
    ).run();
  },

  async checkTokenCompletions(env: Env) {
    // Check for newly completed tokens
    const completedTokens = await env.DB.prepare(`
      SELECT symbol FROM collection_progress
      WHERE daily_status = 'completed' AND hourly_status = 'completed'
    `).all();

    for (const token of completedTokens.results as any[]) {
      const alertType = `token_complete_${token.symbol}`;
      const alreadyAlerted = await this.hasAlert(env, alertType);

      if (!alreadyAlerted) {
        await this.saveAlert(env, {
          alertType,
          message: `✅ ${token.symbol} collection complete! Daily and hourly data fully collected.`,
          severity: 'success',
          timestamp: Math.floor(Date.now() / 1000),
          acknowledged: false
        });
      }
    }
  },

  async sendWebhook(webhookUrl: string, alert: Alert) {
    try {
      await fetch(webhookUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: alert.alertType,
          message: alert.message,
          severity: alert.severity,
          timestamp: alert.timestamp,
          metadata: alert.metadata
        })
      });
      console.log(`📤 Webhook sent for alert: ${alert.alertType}`);
    } catch (error) {
      console.error(`❌ Failed to send webhook:`, error);
    }
  },

  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    // CORS headers
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
      'Content-Type': 'application/json'
    };

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    // Get all alerts
    if (url.pathname === '/alerts') {
      const acknowledged = url.searchParams.get('acknowledged') === 'true';

      let query = 'SELECT * FROM collection_alerts';
      if (!acknowledged) {
        query += ' WHERE acknowledged = FALSE';
      }
      query += ' ORDER BY timestamp DESC';

      const alerts = await env.DB.prepare(query).all();

      return new Response(JSON.stringify({
        success: true,
        alerts: alerts.results
      }, null, 2), { headers: corsHeaders });
    }

    // Acknowledge an alert
    if (url.pathname.startsWith('/alerts/') && request.method === 'POST') {
      const parts = url.pathname.split('/');
      const alertId = parseInt(parts[2]);

      await env.DB.prepare(`
        UPDATE collection_alerts SET acknowledged = TRUE WHERE id = ?
      `).bind(alertId).run();

      return new Response(JSON.stringify({ success: true }), { headers: corsHeaders });
    }

    // Get summary
    if (url.pathname === '/summary') {
      const milestones = await this.checkMilestones(env);
      const unacknowledgedCount = await env.DB.prepare(`
        SELECT COUNT(*) as count FROM collection_alerts WHERE acknowledged = FALSE
      `).first() as any;

      return new Response(JSON.stringify({
        milestones,
        unacknowledgedAlerts: unacknowledgedCount.count
      }, null, 2), { headers: corsHeaders });
    }

    // Manual trigger
    if (url.pathname === '/check' && request.method === 'POST') {
      await this.scheduled({} as ScheduledEvent, env, {} as ExecutionContext);
      return new Response(JSON.stringify({ success: true }), { headers: corsHeaders });
    }

    return new Response(JSON.stringify({
      status: 'ok',
      name: 'Collection Alerts Agent',
      endpoints: [
        'GET /alerts?acknowledged=false',
        'POST /alerts/{id} - Acknowledge alert',
        'GET /summary',
        'POST /check - Manual trigger'
      ],
      alertTypes: [
        'daily_complete - All tokens daily data collected',
        'hourly_complete - All tokens hourly data collected',
        'minute_25/50/75/100 - Minute collection milestones',
        'tokens_paused - Tokens with errors',
        'token_complete_{symbol} - Individual token completion'
      ]
    }, null, 2), { headers: corsHeaders });
  }
};
