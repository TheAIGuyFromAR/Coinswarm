import os
import sqlite3
import time
import json
import urllib.request
import urllib.parse


# Configurable via env or CLI
import argparse
DB_PATH = os.environ.get("LOCAL_SQLITE_PATH", "historical_local.db")
API_KEY = os.environ.get("CRYPTOCOMPARE_API_KEY", "")

def parse_args():
    parser = argparse.ArgumentParser(description="Fetch and fill local OHLCV data for any symbol/timeframe.")
    parser.add_argument("--symbol", type=str, default=os.environ.get("SYMBOL", "BTC-USDC"), help="Symbol name (e.g. BTC-USDC)")
    parser.add_argument("--fsym", type=str, default=os.environ.get("FSYM", "BTC"), help="From symbol (e.g. BTC)")
    parser.add_argument("--tsym", type=str, default=os.environ.get("TSYM", "USDC"), help="To symbol (e.g. USDC)")
    parser.add_argument("--exchange", type=str, default=os.environ.get("EXCHANGE", "CCCAGG"), help="Exchange (default: CCCAGG)")
    parser.add_argument("--timeframe", type=str, default=os.environ.get("TIMEFRAME", "day"), choices=["day", "hour", "minute"], help="Timeframe: day, hour, minute")
    parser.add_argument("--source", type=str, default=os.environ.get("SOURCE", "cryptocompare"), help="Data source")
    return parser.parse_args()

def fetch_ohlcv_cryptocompare(fsym, tsym, exchange, timeframe, limit=2000, toTs=None, api_key=""):
    endpoint_map = {"day": "histoday", "hour": "histohour", "minute": "histominute"}
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
    with urllib.request.urlopen(full_url) as resp:
        if resp.status != 200:
            raise Exception(f"HTTP error: {resp.status}")
        data = json.loads(resp.read().decode())
        if "Data" not in data or "Data" not in data["Data"]:
            print(f"Unexpected CryptoCompare response: {data}")
            raise Exception(f"Unexpected CryptoCompare response: {data}")
        return data["Data"]["Data"]

def create_local_db(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS price_data (
        symbol TEXT NOT NULL,
        timestamp INTEGER NOT NULL,
        timeframe TEXT NOT NULL,
        open REAL NOT NULL,
        high REAL NOT NULL,
        low REAL NOT NULL,
        close REAL NOT NULL,
        volume_from REAL,
        volume_to REAL,
        source TEXT NOT NULL,
        PRIMARY KEY (symbol, timestamp, timeframe, source)
    )
    ''')
    conn.commit()
    conn.close()

def insert_candles_to_sqlite(db_path, symbol, candles, timeframe, source):
    if not candles:
        return 0
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    rows = [
        (
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
        )
        for candle in candles
    ]
    c.executemany(
        "INSERT OR IGNORE INTO price_data (symbol, timestamp, timeframe, open, high, low, close, volume_from, volume_to, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows
    )
    conn.commit()
    inserted = c.rowcount
    conn.close()
    return inserted


def fill_local_db(symbol, fsym, tsym, exchange, timeframe, source):
    print(f"Creating local DB at {DB_PATH}...")
    create_local_db(DB_PATH)
    print(f"Fetching and inserting {symbol} {timeframe} candles...")
    toTs = None
    total_inserted = 0
    seen = set()
    while True:
        candles = fetch_ohlcv_cryptocompare(fsym, tsym, exchange, timeframe, limit=2000, toTs=toTs, api_key=API_KEY)
        if not candles:
            break
        # Deduplicate by timestamp
        new_candles = [c for c in candles if c["time"] not in seen]
        if not new_candles:
            break
        inserted = insert_candles_to_sqlite(DB_PATH, symbol, new_candles, timeframe, source)
        total_inserted += inserted
        for c in new_candles:
            seen.add(c["time"])
        print(f"Inserted {inserted} candles, total so far: {total_inserted}")
        if len(candles) < 2000:
            break
        toTs = min(c["time"] for c in new_candles) - 1
        time.sleep(0.5)  # Be nice to API
    print(f"Done. Total inserted: {total_inserted}")

if __name__ == "__main__":
    args = parse_args()
    fill_local_db(
        symbol=args.symbol,
        fsym=args.fsym,
        tsym=args.tsym,
        exchange=args.exchange,
        timeframe=args.timeframe,
        source=args.source
    )