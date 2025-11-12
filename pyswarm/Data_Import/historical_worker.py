"""
Historical Data Worker (Python, Cloudflare D1)

Pseudocode for full data ingestion and indicator computation pipeline:

PRIORITY ORDER:
1. For BTC-USDC, daily candles, from CryptoCompare, fetch and store all available data.
2. Repeat for hourly, then minute candles for BTC-USDC (CryptoCompare).
3. Repeat steps 1-2 for SOL-USDC (CryptoCompare).
4. For BTC-SOL (on any exchange that supports it), repeat above steps.
5. For each pair, fetch 3 months of data, then extend to 1 year, then 2 years.
6. Add more coin pairings (ETH-USDC, etc.).
7. Add more exchanges (Binance, CoinGecko, etc.).
8. Add longer timeframes (weekly, monthly).
9. Add intermediate timeframes (5m, 15m, etc.).
10. Add DEXes and on-chain sources.

For each (symbol, exchange, timeframe):
    For each day/hour/minute in desired range:
        1. Fetch OHLCV data from API (e.g., CryptoCompare)
        2. Insert into price_data table (D1)
        3. If enough candles exist, compute technical indicators (SMA, EMA, MACD, RSI, etc.)
        4. Insert computed indicators into technical_indicators table (D1)
        5. Repeat for next time period

---

# Step 1: Fetch BTC-USDC daily candles from CryptoCompare and store in D1
# (Implementation will follow after this pseudocode)

"""



import urllib.request
import urllib.parse
import json
from typing import Optional

CRYPTOCOMPARE_API_URL = "https://min-api.cryptocompare.com/data/v2/histoday"

def build_insert_sql(symbol, candle, timeframe, source):
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
    """
    Queue candles for batch processing instead of direct D1 writes.
    Batches of 10 candles per message to optimize queue operations.
    """
    if not candles:
        return

    # Batch candles into groups of 10 for efficient queueing
    batch_size = 10
    messages = []

    for i in range(0, len(candles), batch_size):
        batch = candles[i:i+batch_size]

        # Prepare batch of data points for queue
        data_points = []
        for candle in batch:
            data_points.append({
                "symbol": symbol,
                "timestamp": candle["time"],
                "timeframe": timeframe,
                "open": float(candle["open"]),
                "high": float(candle["high"]),
                "low": float(candle["low"]),
                "close": float(candle["close"]),
                "volumeFrom": float(candle.get("volumefrom", 0)),
                "volumeTo": float(candle.get("volumeto", 0)),
                "source": source
            })

        messages.append({"body": data_points})

    # Send all batches to queue
    if messages:
        await env.HISTORICAL_QUEUE.sendBatch(messages)
        print(f"Queued {len(candles)} candles for {symbol} in {len(messages)} batches")


def fetch_ohlcv_cryptocompare(
    fsym: str = "BTC",
    tsym: str = "USDC",
    exchange: str = "CCCAGG",
    limit: int = 2000,
    timeframe: str = "day",
    api_key: str = "",
    toTs: 'Optional[int]' = None
):
    """
    Fetch OHLCV data from CryptoCompare for any symbol pair, exchange, and timeframe.
    timeframe: 'day' (histoday), 'hour' (histohour), 'minute' (histominute)
    """
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
    # Use Cloudflare Workers fetch if in WORKER_MODE, else urllib for local
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
        if asyncio.get_event_loop().is_running():
            return asyncio.ensure_future(fetch_worker())
        else:
            return asyncio.get_event_loop().run_until_complete(fetch_worker())
    except ImportError:
        # Local mode: use urllib
        with urllib.request.urlopen(full_url) as resp:
            if resp.status != 200:
                raise Exception(f"HTTP error: {resp.status}")
            data = json.loads(resp.read().decode())
            if "Data" not in data or "Data" not in data["Data"]:
                print(f"Unexpected CryptoCompare response: {data}")
                raise Exception(f"Unexpected CryptoCompare response: {data}")
            return data["Data"]["Data"]

async def paged_fetch_and_insert(env, symbol, fsym, tsym, exchange, timeframe, source, api_key, toTs=None):
    """
    Fetch a single page (up to 2000 candles) for a symbol using toTs, insert into D1, and return info for next page.
    """
    limit = 2000
    candles = await fetch_ohlcv_cryptocompare(
        fsym=fsym, tsym=tsym, exchange=exchange, limit=limit, timeframe=timeframe, api_key=api_key, toTs=toTs
    )
    if not candles:
        return {"inserted": 0, "next_toTs": None, "oldest": None, "newest": None}
    # Deduplicate by timestamp (optional: could check D1 for existing, but assume INSERT OR IGNORE)
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
WORKER_MODE = False
try:
    from workers import Response, WorkerEntrypoint
    WORKER_MODE = True
except ImportError:
    pass

if WORKER_MODE:
    class Default(WorkerEntrypoint):
        async def fetch(self, request):
            import traceback
            url = request.url if hasattr(request, 'url') else getattr(request, 'path', None)
            method = request.method if hasattr(request, 'method') else None
            path = None
            if url:
                if isinstance(url, str):
                    path = url.split("/", 3)[-1] if "/" in url else url
                else:
                    path = getattr(url, 'pathname', None) or getattr(url, 'path', None)
            elif hasattr(request, 'path'):
                path = request.path

            if method == "POST" and (path == "trigger" or path == "/trigger"):
                try:
                    api_key = getattr(self.env, "CRYPTOCOMPARE_API_KEY", "")
                    # Parse toTs from POST body (JSON) or query param
                    toTs = None
                    try:
                        if hasattr(request, 'json'):
                            body = await request.json()
                            toTs = body.get("toTs")
                    except Exception:
                        pass
                    # Also allow toTs as query param
                    if toTs is None and hasattr(request, 'url') and hasattr(request.url, 'searchParams'):
                        toTs = request.url.searchParams.get("toTs")
                        if toTs is not None:
                            toTs = int(toTs)
                    result = await paged_fetch_and_insert(
                        self.env, "BTC-USDC", "BTC", "USDC", "CCCAGG", "day", "cryptocompare", api_key, toTs=toTs
                    )
                    return Response.from_json({
                        **result,
                        "message": f"Inserted {result['inserted']} BTC-USDC daily candles.",
                        "next_trigger": f"POST /trigger with toTs={result['next_toTs']}" if result['next_toTs'] else "done"
                    }, status=200)
                except Exception as e:
                    tb = traceback.format_exc()
                    print(f"Exception in /trigger: {e}\n{tb}")
                    return Response.from_json({
                        "error": str(e),
                        "traceback": tb
                    }, status=500)
            return Response.from_json({"status": "ok", "message": "Use POST /trigger to start ingestion."}, status=200)

if not WORKER_MODE:
    if __name__ == "__main__":
        import os
        api_key = os.environ.get("CRYPTOCOMPARE_API_KEY", "")
        import asyncio
        async def main():
            total_inserted = await paginated_fetch_and_insert(
                env=None,  # Replace with actual DB env if running with D1
                symbol="BTC-USDC", fsym="BTC", tsym="USDC", exchange="CCCAGG", timeframe="day", source="cryptocompare", api_key=api_key
            )
            print(f"Inserted {total_inserted} BTC-USDC daily candles.")
        asyncio.run(main())