
// Cloudflare Worker: Evolutionary Strategy Discovery

export default {
  // Cron trigger: Run every minute
  async scheduled(event, env, ctx) {
    const cronType = event.cron; // "*/1 * * * *" for every minute

    switch(event.cron) {
      case "*/1 * * * *":  // Every 1 minute
        return await generateChaosTrades(env);
      case "*/5 * * * *":  // Every 5 minutes
        return await analyzePatterns(env);
      case "*/10 * * * *": // Every 10 minutes
        return await testStrategies(env);
    }
  },

  // HTTP endpoint for manual triggering
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/generate") {
      return await generateChaosTrades(env);
    } else if (url.pathname === "/analyze") {
      return await analyzePatterns(env);
    } else if (url.pathname === "/test") {
      return await testStrategies(env);
    } else if (url.pathname === "/status") {
      return await getStatus(env);
    }

    return new Response("Evolution System Running", { status: 200 });
  }
};

// Generate 50 chaos trades (< 1 second)
async function generateChaosTrades(env) {
  const startTime = Date.now();
  const trades = [];

  for (let i = 0; i < 50; i++) {
    const entryPrice = Math.random() * (70000 - 60000) + 60000;
    const exitPrice = entryPrice * (Math.random() * (1.05 - 0.95) + 0.95);

    const trade = {
      entry_time: new Date().toISOString(),
      exit_time: new Date().toISOString(),
      entry_price: entryPrice,
      exit_price: exitPrice,
      pnl_pct: (exitPrice - entryPrice) / entryPrice,
      profitable: exitPrice > entryPrice,
      buy_reason: generateReason(),
      buy_state: {
        momentum_1tick: Math.random() * 0.1 - 0.05,
        vs_sma10: Math.random() * 0.2 - 0.1,
        volume_vs_avg: Math.random() * 1.5 - 0.5,
        volatility: Math.random() * 0.04 + 0.01
      },
      sell_reason: generateReason(),
      sell_state: {
        momentum_1tick: Math.random() * 0.1 - 0.05,
        vs_sma10: Math.random() * 0.2 - 0.1
      }
    };

    trades.push(trade);

    // Store in D1
    await env.DB.prepare(
      `INSERT INTO chaos_trades
       (entry_time, entry_price, exit_price, pnl_pct, profitable,
        buy_reason, buy_state, sell_reason, sell_state)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`
    ).bind(
      trade.entry_time,
      trade.entry_price,
      trade.exit_price,
      trade.pnl_pct,
      trade.profitable ? 1 : 0,
      trade.buy_reason,
      JSON.stringify(trade.buy_state),
      trade.sell_reason,
      JSON.stringify(trade.sell_state)
    ).run();
  }

  const duration = Date.now() - startTime;

  // Update stats
  const { results } = await env.DB.prepare(
    "SELECT COUNT(*) as total FROM chaos_trades"
  ).first();

  return new Response(JSON.stringify({
    status: "ok",
    action: "generate_chaos_trades",
    trades_generated: 50,
    total_trades: results?.total || 0,
    duration_ms: duration
  }), {
    headers: { "Content-Type": "application/json" }
  });
}

// Analyze patterns (every 5 minutes)
async function analyzePatterns(env) {
  const startTime = Date.now();

  // Get recent trades
  const { results: trades } = await env.DB.prepare(
    `SELECT * FROM chaos_trades ORDER BY id DESC LIMIT 1000`
  ).all();

  if (trades.length < 100) {
    return new Response(JSON.stringify({
      status: "skipped",
      reason: "not_enough_data",
      trades: trades.length
    }), {
      headers: { "Content-Type": "application/json" }
    });
  }

  // Separate winners and losers
  const winners = trades.filter(t => t.profitable === 1);
  const losers = trades.filter(t => t.profitable === 0);

  if (winners.length === 0 || losers.length === 0) {
    return new Response(JSON.stringify({
      status: "skipped",
      reason: "no_winners_or_losers"
    }), {
      headers: { "Content-Type": "application/json" }
    });
  }

  // Calculate pattern statistics
  const winnerStates = winners.map(t => JSON.parse(t.buy_state));
  const loserStates = losers.map(t => JSON.parse(t.buy_state));

  const winnerMomentum = winnerStates.reduce((sum, s) => sum + s.momentum_1tick, 0) / winnerStates.length;
  const loserMomentum = loserStates.reduce((sum, s) => sum + s.momentum_1tick, 0) / loserStates.length;

  const winnerVsSMA = winnerStates.reduce((sum, s) => sum + s.vs_sma10, 0) / winnerStates.length;
  const loserVsSMA = loserStates.reduce((sum, s) => sum + s.vs_sma10, 0) / loserStates.length;

  const pattern = {
    id: `pattern_${Date.now()}`,
    name: "Discovered Pattern",
    winner_momentum_avg: winnerMomentum,
    loser_momentum_avg: loserMomentum,
    momentum_diff: winnerMomentum - loserMomentum,
    winner_vs_sma_avg: winnerVsSMA,
    loser_vs_sma_avg: loserVsSMA,
    sma_diff: winnerVsSMA - loserVsSMA,
    sample_size: trades.length,
    win_rate: winners.length / trades.length,
    discovered_at: new Date().toISOString()
  };

  // Store pattern
  await env.DB.prepare(
    `INSERT INTO discovered_patterns
     (pattern_id, name, conditions, win_rate, sample_size, discovered_at)
     VALUES (?, ?, ?, ?, ?, ?)`
  ).bind(
    pattern.id,
    pattern.name,
    JSON.stringify(pattern),
    pattern.win_rate,
    pattern.sample_size,
    pattern.discovered_at
  ).run();

  const duration = Date.now() - startTime;

  return new Response(JSON.stringify({
    status: "ok",
    action: "analyze_patterns",
    pattern: pattern,
    duration_ms: duration
  }), {
    headers: { "Content-Type": "application/json" }
  });
}

// Test strategies (every 10 minutes)
async function testStrategies(env) {
  const startTime = Date.now();

  // Get patterns to test
  const { results: patterns } = await env.DB.prepare(
    `SELECT * FROM discovered_patterns
     WHERE tested = 0
     ORDER BY discovered_at DESC
     LIMIT 5`
  ).all();

  if (patterns.length === 0) {
    return new Response(JSON.stringify({
      status: "skipped",
      reason: "no_patterns_to_test"
    }), {
      headers: { "Content-Type": "application/json" }
    });
  }

  const results = [];

  for (const pattern of patterns) {
    const conditions = JSON.parse(pattern.conditions);

    // Simple backtest: Count how many trades would match this pattern
    const { results: matchingTrades } = await env.DB.prepare(
      `SELECT * FROM chaos_trades LIMIT 100`
    ).all();

    // Score based on how well pattern predicts winners
    let correct = 0;
    let total = 0;

    for (const trade of matchingTrades) {
      const buyState = JSON.parse(trade.buy_state);

      // Check if trade matches pattern conditions
      const matchesMomentum = Math.abs(buyState.momentum_1tick - conditions.winner_momentum_avg) < 0.02;
      const matchesSMA = Math.abs(buyState.vs_sma10 - conditions.winner_vs_sma_avg) < 0.05;

      if (matchesMomentum && matchesSMA) {
        total++;
        if (trade.profitable === 1) {
          correct++;
        }
      }
    }

    const accuracy = total > 0 ? correct / total : 0;
    const vsRandom = accuracy - 0.5; // Compare to 50% random
    const vote = vsRandom > 0 ? 1 : -1;

    // Update pattern with test results
    await env.DB.prepare(
      `UPDATE discovered_patterns
       SET tested = 1, accuracy = ?, votes = ?, tested_at = ?
       WHERE pattern_id = ?`
    ).bind(accuracy, vote, new Date().toISOString(), pattern.pattern_id).run();

    results.push({
      pattern_id: pattern.pattern_id,
      accuracy: accuracy,
      vs_random: vsRandom,
      vote: vote > 0 ? "UPVOTE" : "DOWNVOTE"
    });
  }

  const duration = Date.now() - startTime;

  return new Response(JSON.stringify({
    status: "ok",
    action: "test_strategies",
    tested: results.length,
    results: results,
    duration_ms: duration
  }), {
    headers: { "Content-Type": "application/json" }
  });
}

// Get system status
async function getStatus(env) {
  const { results: tradeCount } = await env.DB.prepare(
    "SELECT COUNT(*) as count FROM chaos_trades"
  ).first();

  const { results: patternCount } = await env.DB.prepare(
    "SELECT COUNT(*) as count FROM discovered_patterns"
  ).first();

  const { results: winners } = await env.DB.prepare(
    `SELECT * FROM discovered_patterns
     WHERE votes > 0
     ORDER BY accuracy DESC
     LIMIT 5`
  ).all();

  return new Response(JSON.stringify({
    status: "running",
    total_trades: tradeCount?.count || 0,
    total_patterns: patternCount?.count || 0,
    winning_strategies: winners?.length || 0,
    top_strategies: winners || []
  }, null, 2), {
    headers: { "Content-Type": "application/json" }
  });
}

// Helper function
function generateReason() {
  const reasons = [
    "momentum positive",
    "below SMA - oversold",
    "high volume spike",
    "FOMO",
    "feels like the top",
    "profit target hit",
    "random walk",
    "gut feeling"
  ];
  return reasons[Math.floor(Math.random() * reasons.length)];
}
