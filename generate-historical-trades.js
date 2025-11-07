/**
 * Generate realistic historical trades with:
 * - Real price movements (synthetic but realistic)
 * - Random entry times
 * - Random hold durations (1min to 24hrs)
 * - Varied market conditions
 */

// Generate realistic BTC price series with trends and volatility
function generatePriceSeries(numPoints = 100000) {
  const prices = [];
  let basePrice = 65000;
  let trend = 0;
  let volatility = 0.02;

  for (let i = 0; i < numPoints; i++) {
    // Change trend occasionally (every ~1000 points = trend shift)
    if (Math.random() < 0.001) {
      trend = (Math.random() - 0.5) * 0.0005; // -0.025% to +0.025% per tick
    }

    // Change volatility occasionally
    if (Math.random() < 0.002) {
      volatility = 0.01 + Math.random() * 0.03; // 1% to 4% volatility
    }

    // Price movement with trend + random walk
    const trendMove = basePrice * trend;
    const randomMove = basePrice * (Math.random() - 0.5) * volatility;
    basePrice = Math.max(20000, Math.min(100000, basePrice + trendMove + randomMove));

    prices.push({
      time: new Date(Date.now() - (numPoints - i) * 60000).toISOString(), // 1 min intervals
      price: basePrice,
      volume: 100 + Math.random() * 500
    });
  }

  return prices;
}

// Calculate market state indicators
function calculateMarketState(prices, index) {
  const current = prices[index];

  // Momentum (1-tick and 5-tick)
  const momentum1tick = index > 0
    ? (current.price - prices[index - 1].price) / prices[index - 1].price
    : 0;

  const momentum5tick = index >= 5
    ? (current.price - prices[index - 5].price) / prices[index - 5].price
    : 0;

  // SMA10
  const sma10Start = Math.max(0, index - 9);
  const sma10Prices = prices.slice(sma10Start, index + 1).map(p => p.price);
  const sma10 = sma10Prices.reduce((a, b) => a + b, 0) / sma10Prices.length;
  const vsSma10 = (current.price - sma10) / sma10;

  // Volume vs average
  const volumeStart = Math.max(0, index - 19);
  const recentVolumes = prices.slice(volumeStart, index + 1).map(p => p.volume);
  const avgVolume = recentVolumes.reduce((a, b) => a + b, 0) / recentVolumes.length;
  const volumeVsAvg = current.volume / avgVolume;

  // Volatility (std dev of last 20 returns)
  const returns = [];
  for (let i = Math.max(1, index - 19); i <= index; i++) {
    returns.push((prices[i].price - prices[i-1].price) / prices[i-1].price);
  }
  const avgReturn = returns.reduce((a, b) => a + b, 0) / returns.length;
  const variance = returns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / returns.length;
  const volatility = Math.sqrt(variance);

  return {
    price: current.price,
    momentum1tick,
    momentum5tick,
    vsSma10,
    volumeVsAvg,
    volatility
  };
}

// Generate a random trade from historical data
function generateTrade(prices, index) {
  // Random hold duration: 1 minute to 24 hours (1 to 1440 ticks)
  const minHold = 1;
  const maxHold = 1440;
  const holdDuration = Math.floor(minHold + Math.random() * (maxHold - minHold));

  // Make sure we don't go past end of price series
  if (index + holdDuration >= prices.length) {
    return null;
  }

  const entryIndex = index;
  const exitIndex = index + holdDuration;

  const entryState = calculateMarketState(prices, entryIndex);
  const exitState = calculateMarketState(prices, exitIndex);

  const entryPrice = prices[entryIndex].price;
  const exitPrice = prices[exitIndex].price;
  const pnlPct = ((exitPrice - entryPrice) / entryPrice) * 100;
  const profitable = exitPrice > entryPrice ? 1 : 0;

  // Generate realistic buy/sell reasons based on state
  const buyReasons = [
    `Momentum ${entryState.momentum1tick > 0 ? 'positive' : 'negative'} (${(entryState.momentum1tick * 100).toFixed(2)}%)`,
    `Price ${entryState.vsSma10 > 0 ? 'above' : 'below'} SMA10 (${(entryState.vsSma10 * 100).toFixed(2)}%)`,
    `Volume ${entryState.volumeVsAvg > 1 ? 'high' : 'low'} (${entryState.volumeVsAvg.toFixed(2)}x avg)`,
    `Volatility ${entryState.volatility > 0.015 ? 'high' : 'low'} (${(entryState.volatility * 100).toFixed(2)}%)`,
  ];
  const buyReason = buyReasons[Math.floor(Math.random() * buyReasons.length)];

  const sellReasons = [
    `Hold duration ${holdDuration} minutes reached`,
    `${profitable ? 'Profit' : 'Loss'} target: ${pnlPct.toFixed(2)}%`,
    `Momentum ${exitState.momentum1tick < 0 ? 'reversal' : 'continuation'} detected`,
    `Volume ${exitState.volumeVsAvg > 1.5 ? 'spike' : 'drop'} (${exitState.volumeVsAvg.toFixed(2)}x)`,
  ];
  const sellReason = sellReasons[Math.floor(Math.random() * sellReasons.length)];

  return {
    entry_time: prices[entryIndex].time,
    exit_time: prices[exitIndex].time,
    entry_price: entryPrice,
    exit_price: exitPrice,
    pnl_pct: pnlPct,
    profitable,
    buy_reason: buyReason,
    buy_state: JSON.stringify(entryState),
    sell_reason: sellReason,
    sell_state: JSON.stringify(exitState)
  };
}

// Generate batch of trades
function generateHistoricalTrades(numTrades = 50000) {
  console.log(`Generating ${numTrades} historical trades...`);

  // Generate enough price data (need extra for hold durations)
  const pricePoints = numTrades * 3; // 3x to account for varying hold times
  console.log(`Generating ${pricePoints} price points...`);
  const prices = generatePriceSeries(pricePoints);

  const trades = [];
  const usedIndices = new Set();

  let attempts = 0;
  while (trades.length < numTrades && attempts < numTrades * 2) {
    // Random entry point (but leave room for max hold duration)
    const maxEntryIndex = prices.length - 1440 - 1;
    const entryIndex = Math.floor(Math.random() * maxEntryIndex);

    // Skip if we've used this entry point
    if (usedIndices.has(entryIndex)) {
      attempts++;
      continue;
    }

    const trade = generateTrade(prices, entryIndex);
    if (trade) {
      trades.push(trade);
      usedIndices.add(entryIndex);
    }

    attempts++;

    if (trades.length % 5000 === 0) {
      console.log(`Generated ${trades.length} trades...`);
    }
  }

  console.log(`✓ Generated ${trades.length} trades`);
  return trades;
}

// Generate SQL INSERT statements
const trades = generateHistoricalTrades(50000);

console.log('\n-- Historical Trades SQL Insert');
console.log('-- Generated with random entry times and hold durations\n');

// Batch insert in chunks of 500
const chunkSize = 500;
for (let i = 0; i < trades.length; i += chunkSize) {
  const chunk = trades.slice(i, i + chunkSize);

  console.log(`-- Batch ${Math.floor(i / chunkSize) + 1} of ${Math.ceil(trades.length / chunkSize)}`);
  console.log('INSERT INTO chaos_trades (entry_time, exit_time, entry_price, exit_price, pnl_pct, profitable, buy_reason, buy_state, sell_reason, sell_state) VALUES');

  const values = chunk.map(t =>
    `('${t.entry_time}', '${t.exit_time}', ${t.entry_price}, ${t.exit_price}, ${t.pnl_pct}, ${t.profitable}, '${t.buy_reason.replace(/'/g, "''")}', '${t.buy_state.replace(/'/g, "''")}', '${t.sell_reason.replace(/'/g, "''")}', '${t.sell_state.replace(/'/g, "''")}')`
  );

  console.log(values.join(',\n') + ';\n');
}

console.log(`\n-- Total: ${trades.length} historical trades generated`);
