# === QUEUE ENQUEUE/CONSUME HELPERS ===
import os

USE_QUEUE = os.environ.get("USE_QUEUE", "1") == "1"  # Set to "0" for direct mode

async def enqueue_ingest_job(env, job):
    """
    Enqueue an ingestion job to the queue. In production, use Cloudflare Queue; locally, use a simple file or in-memory queue.
    """
    if hasattr(env, "HISTORICAL_DATA_QUEUE"):
        # Cloudflare Queue (production)
        await env.HISTORICAL_DATA_QUEUE.send(json.dumps(job))
    else:
        # Local fallback: append to a file (or implement in-memory queue)
        queue_file = "historical_ingest_queue.jsonl"
        with open(queue_file, "a") as f:
            f.write(json.dumps(job) + "\n")

# Example job: {"symbol": ..., "fsym": ..., "tsym": ..., "timeframe": ..., "tf_label": ..., "step": ..., "tier_label": ..., "toTs": ...}

async def process_ingest_job(env, job):
    """
    Process a single ingestion job (to be called by the queue consumer/worker).
    """
    try:
        batch = await paged_fetch_and_insert(
            env=env,
            symbol=job["symbol"],
            fsym=job["fsym"],
            tsym=job["tsym"],
            exchange="CCCAGG",
            timeframe=job["timeframe"],
            source="cryptocompare",
            api_key=env.CRYPTOCOMPARE_API_KEY,
            toTs=job["toTs"]
        )
        # Optionally: update progress, log, etc.
        return batch
    except Exception as e:
        print(f"Error processing ingest job: {e}")
        return {"error": str(e)}

import math
from datetime import datetime, timedelta



# === CONFIGURABLE TIERED FILL WINDOWS ===
# Each tier: fill this window for all pairs/timeframes before proceeding to the next
FILL_TIERS_DAYS = [
    30,    # 1 month
    90,    # 3 months
    180,   # 6 months
    365,   # 1 year
    365*2, # 2 years
    365*4  # 4 years
    # 'all' handled as final phase
]


# Remove duplicate definitions if present
def _remove_duplicate_cron_ingest():
    pass


# Remove duplicate definition at line 69

# Bitcoin: Get the latest timestamp in D1 for a given symbol and timeframe
async def get_latest_timestamp_d1(env, symbol, timeframe):
    sql = "SELECT MAX(timestamp) as max_ts FROM price_data WHERE symbol = ? AND timeframe = ?;"
    row = await env.DB.prepare(sql).bind(symbol, timeframe).first()
    return row["max_ts"] if row and row["max_ts"] is not None else None

# Bitcoin: Get the earliest timestamp in D1 for a given symbol and timeframe
async def get_earliest_timestamp_d1(env, symbol, timeframe):
    sql = "SELECT MIN(timestamp) as min_ts FROM price_data WHERE symbol = ? AND timeframe = ?;"
    row = await env.DB.prepare(sql).bind(symbol, timeframe).first()
    return row["min_ts"] if row and row["min_ts"] is not None else None

# Bitcoin: Helper to determine fetch direction and range
def get_fetch_direction(newer_than=None, older_than=None):
    if newer_than is not None and older_than is not None:
        # If both are set, decide based on which is further from now
        if newer_than > older_than:
            return 'backward'
        else:
            return 'forward'
    elif older_than is not None:
        return 'backward'
    else:
        return 'forward'


# --- D1 Meta-Table for Progress Tracking (Production, async) ---
async def ensure_progress_table_d1(env):
    # 🏴‍☠️ Create the meta-table if it doesn't exist (D1 SQL)
    sql = """
    CREATE TABLE IF NOT EXISTS ingestion_progress (
        symbol TEXT PRIMARY KEY,
        last_toTs INTEGER
    );
    """
    await env.DB.exec(sql)

async def get_last_toTs_d1(env, symbol):
    sql = "SELECT last_toTs FROM ingestion_progress WHERE symbol = ?;"
    row = await env.DB.prepare(sql).bind(symbol).first()
    return row["last_toTs"] if row and "last_toTs" in row else None

async def update_last_toTs_d1(env, symbol, toTs):
    sql = "INSERT OR REPLACE INTO ingestion_progress (symbol, last_toTs) VALUES (?, ?);"
    await env.DB.prepare(sql).bind(symbol, toTs).run()

async def cron_ingest_all_pairs_d1(env):
    # 🏴‍☠️ Starfleet Cron: Run this every X minutes to keep filling the D1 vault!
    api_key = getattr(env, "CRYPTOCOMPARE_API_KEY", "")
    await ensure_progress_table_d1(env)
    available_pairs = [
        ("BTC-USDC", "BTC", "USDC"),
        ("ETH-USDC", "ETH", "USDC"),
        ("SOL-USDC", "SOL", "USDC"),
        ("BTC-ETH", "BTC", "ETH"),
        ("BTC-SOL", "BTC", "SOL"),
        ("ETH-SOL", "ETH", "SOL"),
        ("mSOL-SOL", "mSOL", "SOL"),
        ("BONK-SOL", "BONK", "SOL"),
        ("WIF-SOL", "WIF", "SOL"),
        ("SAMO-SOL", "SAMO", "SOL"),
        ("POPCAT-SOL", "POPCAT", "SOL"),
        ("HADES-SOL", "HADES", "SOL"),
        ("MEOW-SOL", "MEOW", "SOL"),
        ("PENG-SOL", "PENG", "SOL"),
        ("BODEN-SOL", "BODEN", "SOL"),
        ("SHDW-SOL", "SHDW", "SOL"),
        ("CHEEMS-SOL", "CHEEMS", "SOL"),
        ("CAT-SOL", "CAT", "SOL"),
        ("SAI-SOL", "SAI", "SOL"),
        ("TROLL-SOL", "TROLL", "SOL"),
        ("GIGA-SOL", "GIGA", "SOL"),
        ("SNEK-SOL", "SNEK", "SOL"),
        ("BNB-USDC", "BNB", "USDC"),
        ("XRP-USDC", "XRP", "USDC"),
        ("LINK-USDC", "LINK", "USDC"),
        ("ARB-USDC", "ARB", "USDC"),
        ("OP-USDC", "OP", "USDC"),
        ("ADA-USDC", "ADA", "USDC"),
        ("DOGE-USDC", "DOGE", "USDC"),
        ("AVAX-USDC", "AVAX", "USDC"),
        ("TRX-USDC", "TRX", "USDC"),
        ("GRAPE-SOL", "GRAPE", "SOL"),
        ("KIN-SOL", "KIN", "SOL"),
        ("FIDA-SOL", "FIDA", "SOL"),
        ("STEP-SOL", "STEP", "SOL"),
        ("SLIM-SOL", "SLIM", "SOL"),
        ("LIQ-SOL", "LIQ", "SOL"),
        ("MEDIA-SOL", "MEDIA", "SOL"),
        ("SBR-SOL", "SBR", "SOL"),
        ("SUNNY-SOL", "SUNNY", "SOL"),
        ("TULIP-SOL", "TULIP", "SOL"),
        ("POLIS-SOL", "POLIS", "SOL"),
        ("ATLAS-SOL", "ATLAS", "SOL"),
        ("SNY-SOL", "SNY", "SOL"),
    ]
    results = []
    # Bitcoin: set these to control fill direction (could be params or config)
    fill_mode = 'forward'  # or 'backward'

    # Bitcoin: Priority order for ingestion (edit as needed)
    priority_order = [
        "BTC-USDC", "ETH-USDC", "SOL-USDC", "BTC-ETH", "BTC-SOL", "ETH-SOL",
        "mSOL-SOL", "BONK-SOL", "WIF-SOL", "SAMO-SOL", "POPCAT-SOL", "HADES-SOL",
        "MEOW-SOL", "PENG-SOL", "BODEN-SOL", "SHDW-SOL", "CHEEMS-SOL", "CAT-SOL",
        "SAI-SOL", "TROLL-SOL", "GIGA-SOL", "SNEK-SOL", "BNB-USDC", "XRP-USDC",
        "LINK-USDC", "ARB-USDC", "OP-USDC", "ADA-USDC", "DOGE-USDC", "AVAX-USDC",
        "TRX-USDC", "GRAPE-SOL", "KIN-SOL", "FIDA-SOL", "STEP-SOL", "SLIM-SOL",
        "LIQ-SOL", "MEDIA-SOL", "SBR-SOL", "SUNNY-SOL", "TULIP-SOL", "POLIS-SOL",
        "ATLAS-SOL", "SNY-SOL"
    ]
    # Sort available_pairs by priority_order
    pair_priority = {sym: i for i, sym in enumerate(priority_order)}
    available_pairs_sorted = sorted(
        available_pairs,
        key=lambda tup: pair_priority.get(tup[0], 9999)
    )


    import time
    now_ts = int(time.time())

    # TIERED FILL: For each tier, fill all pairs/timeframes for that window before proceeding to the next
    for tier_idx, tier_days in enumerate(FILL_TIERS_DAYS):
        tier_start_ts = now_ts - tier_days * 86400
        tier_label = f"{tier_days}d"
        print(f"\n=== Bitcoin: Starting fill tier {tier_label} (last {tier_days} days) ===")
        for timeframe, tf_label, step in [("day", "1d", 86400), ("hour", "1h", 3600)]:
            for symbol, fsym, tsym in available_pairs_sorted:
                latest_ts = await get_latest_timestamp_d1(env, symbol, tf_label)
                # Only fill up to now, but not before tier_start_ts
                toTs = None
                if latest_ts is None or latest_ts < tier_start_ts:
                    toTs = tier_start_ts
                else:
                    toTs = latest_ts + step
                job = {
                    "symbol": symbol,
                    "fsym": fsym,
                    "tsym": tsym,
                    "timeframe": timeframe,
                    "tf_label": tf_label,
                    "step": step,
                    "tier_label": tier_label,
                    "toTs": toTs
                }
                await enqueue_ingest_job(env, job)
                results.append({"symbol": symbol, "timeframe": timeframe, "phase": f"tier_{tier_label}", "enqueued": True})

    # FINAL PHASE: After all tiers, backfill all remaining history (oldest to start of last tier)
    last_tier_days = FILL_TIERS_DAYS[-1]
    last_tier_start_ts = now_ts - last_tier_days * 86400
    for timeframe, tf_label, step in [("day", "1d", 86400), ("hour", "1h", 3600)]:
        for symbol, fsym, tsym in available_pairs_sorted:
            earliest_ts = await get_earliest_timestamp_d1(env, symbol, tf_label)
            # Only backfill before last_tier_start_ts
            toTs = None
            if earliest_ts is not None and earliest_ts > last_tier_start_ts:
                toTs = earliest_ts - step
                job = {
                    "symbol": symbol,
                    "fsym": fsym,
                    "tsym": tsym,
                    "timeframe": timeframe,
                    "tf_label": tf_label,
                    "step": step,
                    "tier_label": f"pre_{last_tier_days}d",
                    "toTs": toTs
                }
                await enqueue_ingest_job(env, job)
                results.append({"symbol": symbol, "timeframe": timeframe, "phase": f"pre_{last_tier_days}d", "enqueued": True})

    # Phase 2: After all pairs/timeframes have 2 years, backfill the rest of history
    for timeframe, tf_label, step in [("day", "1d", 86400), ("hour", "1h", 3600)]:
        for symbol, fsym, tsym in available_pairs_sorted:
            try:
                earliest_ts = await get_earliest_timestamp_d1(env, symbol, tf_label)
                # Only backfill before last_tier_start_ts
                toTs = None
                if earliest_ts is not None and earliest_ts > last_tier_start_ts:
                    toTs = earliest_ts - step
                    print(f"Bitcoin: Backfilling {symbol} {timeframe} (pre-{last_tier_days}d phase) from toTs={toTs} (earliest in D1: {earliest_ts}) ...")
                    batch = await paged_fetch_and_insert(
                        env=env,
                        symbol=symbol, fsym=fsym, tsym=tsym, exchange="CCCAGG", timeframe=timeframe, source="cryptocompare", api_key=api_key, toTs=toTs
                    )
                    if batch and batch["next_toTs"]:
                        await update_last_toTs_d1(env, symbol, batch["next_toTs"])
                    results.append({"symbol": symbol, "timeframe": timeframe, "inserted": batch["inserted"], "phase": f"pre_{last_tier_days}d"})
                    print(f"Bitcoin: Inserted {batch['inserted']} {symbol} {timeframe} candles (pre-{last_tier_days}d phase).")
            except Exception as e:
                print(f"Bitcoin: Error backfilling {symbol} {timeframe} (pre-{last_tier_days}d phase): {e}")
                results.append({"symbol": symbol, "timeframe": timeframe, "phase": f"pre_{last_tier_days}d", "error": str(e)})
    print("🖖 [CRON] All voyages complete. Set phasers to profit!")
    return results

"""
// 🏴‍☠️ Crypto Pirate's Log: Historical Data Worker (Python, Cloudflare D1)
                            await update_last_toTs_d1(env, symbol, batch["next_toTs"])

// Starfleet Mission Briefing:
// 1. Engage warp drive to fetch BTC-USDC daily candles from CryptoCompare and beam them into D1.
// 2. Repeat for hourly, then minute candles for BTC-USDC (CryptoCompare).
// 3. Repeat for SOL-USDC, then all cross-pairs in the quadrant.
// 4. For each pair, chart a course for 3 months, then 1 year, then 2 years of data.
// 5. Add more coin pairings (ETH-USDC, etc.) to the manifest.
// 6. Expand to new exchanges (Binance, CoinGecko, etc.) as new star systems are discovered.
// 7. Add longer timeframes (weekly, monthly) to the captain's log.
// 8. Add intermediate timeframes (5m, 15m, etc.) for finer navigation.
// 9. Integrate DEXes and on-chain sources for the full crypto archipelago.

// For each (symbol, exchange, timeframe):
//   For each day/hour/minute in the chosen voyage:
//     1. Fetch OHLCV data from CryptoCompare (X marks the spot!)
//     2. Bury the loot in the price_data table (D1)
//     3. If enough candles are in the hold, compute technical indicators (SMA, EMA, MACD, RSI, etc.)
//     4. Store the indicators in the technical_indicators table (D1)
//     5. Repeat for the next time period—make it so!

// ---

// Step 1: Plunder BTC-USDC daily candles from CryptoCompare and stash them in D1
// (Implementation follows the pirate code and Starfleet regulations)
"""



import urllib.request
import urllib.parse
import json
from typing import Optional

CRYPTOCOMPARE_API_URL = "https://min-api.cryptocompare.com/data/v2/histoday"

def build_insert_sql(symbol, candle, timeframe, source):
    # Bitcoin: Prepare the SQL to insert a new OHLCV record if it doesn't already exist.
    return (
        "INSERT OR IGNORE INTO price_data "
        "(symbol, timestamp, timeframe, open, high, low, close, volume_from, volume_to, source) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
        [
            symbol,
            candle["time"],
            timeframe,
            candle["open"],
            candle["high"],
            candle["low"],
            candle["close"],
            candle.get("volumefrom", 0),
            candle.get("volumeto", 0),
            source
        ]
    )

async def insert_candles_to_d1(env, symbol, candles, timeframe, source):
    # Bitcoin: If there are no candles, nothing to insert.
    if not candles:
        return
    # Bitcoin: Deduplication - check if each (symbol, timestamp, timeframe) exists before insert.
    # If schema has UNIQUE(symbol, timestamp, timeframe), INSERT OR IGNORE is sufficient.
    sql = (
        "INSERT OR IGNORE INTO price_data "
        "(symbol, timestamp, timeframe, open, high, low, close, volume_from, volume_to, source) VALUES "
        + ", ".join(["(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"] * len(candles))
    )
    params = []
    for candle in candles:
        params.extend([
            symbol,
            candle["time"],
            timeframe,
            candle["open"],
            candle["high"],
            candle["low"],
            candle["close"],
            candle.get("volumefrom", 0),
            candle.get("volumeto", 0),
            source
        ])
    await env.DB.prepare(sql).bind(*params).run()
    # If you want to be extra careful, you could check for existence before insert, but with INSERT OR IGNORE and a UNIQUE constraint, this is not necessary for D1.


def fetch_ohlcv_cryptocompare(
    fsym: str = "BTC",
    tsym: str = "USDC",
    exchange: str = "CCCAGG",
    limit: int = 2000,
    timeframe: str = "day",
    api_key: str = "",
    toTs: 'Optional[int]' = None
):
    # Bitcoin: Fetch OHLCV data from CryptoCompare for any pair, exchange, and timeframe.
    # timeframe: 'day', 'hour', 'minute'
    endpoint_map = {
        "day": "histoday",
        "hour": "histohour",
        "minute": "histominute"
    }
    endpoint = endpoint_map.get(timeframe, "histoday")
    url = f"https://min-api.cryptocompare.com/data/v2/{endpoint}"
    params = {
        "fsym": fsym,
        "tsym": tsym,
        "limit": limit,
        "e": exchange
    }
    if toTs is not None:
        params["toTs"] = toTs
    full_url = url + "?" + urllib.parse.urlencode(params)
    if api_key:
        full_url += f"&api_key={api_key}"
    # 🏴‍☠️ Use Cloudflare Workers fetch if in WORKER_MODE, else use urllib for local plundering
    try:
        from workers import fetch as cf_fetch
        import asyncio
        async def fetch_worker():
            resp = await cf_fetch(full_url)
            if resp.status != 200:
                raise Exception(f"HTTP error: {resp.status}")
            text = await resp.text()
            data = json.loads(text)
            if "Data" not in data or "Data" not in data["Data"]:
                print(f"Unexpected CryptoCompare response: {text}")
                raise Exception(f"Unexpected CryptoCompare response: {text}")
            return data["Data"]["Data"]
        # 🖖 Engage async warp for Workers mode
        if asyncio.get_event_loop().is_running():
            return asyncio.ensure_future(fetch_worker())
        else:
            return asyncio.get_event_loop().run_until_complete(fetch_worker())
    except ImportError:
        # 🏴‍☠️ Local mode: use urllib to row to the API island
        with urllib.request.urlopen(full_url) as resp:
            if resp.status != 200:
                raise Exception(f"HTTP error: {resp.status}")
            data = json.loads(resp.read().decode())
            if "Data" not in data or "Data" not in data["Data"]:
                print(f"Unexpected CryptoCompare response: {data}")
                raise Exception(f"Unexpected CryptoCompare response: {data}")
            return data["Data"]["Data"]

async def paged_fetch_and_insert(env, symbol, fsym, tsym, exchange, timeframe, source, api_key, toTs=None):
    # Bitcoin: Fetch a single page (up to 2000 candles) for a symbol using toTs, insert into D1, and return info for next page.
    limit = 2000
    candles = await fetch_ohlcv_cryptocompare(
        fsym=fsym, tsym=tsym, exchange=exchange, limit=limit, timeframe=timeframe, api_key=api_key, toTs=toTs
    )
    if not candles:
        # Bitcoin: No data found for this page.
        return {"inserted": 0, "next_toTs": None, "oldest": None, "newest": None}
    # Bitcoin: Deduplication is handled by INSERT OR IGNORE and UNIQUE(symbol, timestamp, timeframe) in D1 schema.
    await insert_candles_to_d1(env, symbol, candles, "1d", source)
    times = [c["time"] for c in candles]
    oldest = min(times)
    newest = max(times)
    next_toTs = oldest - 1 if len(candles) == limit else None
    return {
        "inserted": len(candles),
        "next_toTs": next_toTs,
        "oldest": oldest,
        "newest": newest,
        "candles": candles
    }

# Only production D1/Cloudflare Worker logic remains below
from workers import Response, WorkerEntrypoint

class Default(WorkerEntrypoint):
    async def scheduled(self, event):
        # Bitcoin: This method is called by Cloudflare Worker cron triggers
        try:
            results = await cron_ingest_all_pairs_d1(self.env)
            return Response.from_json({"status": "ok", "results": results}, status=200)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"Exception in scheduled: {e}\n{tb}")
            return Response.from_json({"error": str(e), "traceback": tb}, status=500)

if __name__ == "__main__":
    print("This script is production-ready for D1. Deploy as a Cloudflare Worker with scheduled triggers.")