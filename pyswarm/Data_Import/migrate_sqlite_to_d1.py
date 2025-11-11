import sqlite3
import os
import requests
import time

# CONFIGURATION
SQLITE_PATH = "historical_local.db"
D1_API_URL = os.environ.get("D1_API_URL", "")  # e.g. https://api.cloudflare.com/client/v4/accounts/{account_id}/d1/database/{db_uuid}/query
D1_API_TOKEN = os.environ.get("D1_API_TOKEN", "")  # Cloudflare API Token with D1 write access
BATCH_SIZE = 500

def fetch_rows():
    conn = sqlite3.connect(SQLITE_PATH)
    c = conn.cursor()
    c.execute("SELECT symbol, timestamp, timeframe, open, high, low, close, volume_from, volume_to, source FROM price_data ORDER BY symbol, timeframe, timestamp")
    while True:
        rows = c.fetchmany(BATCH_SIZE)
        if not rows:
            break
        yield rows
    conn.close()

def insert_batch_to_d1(rows):
    # Prepare SQL for D1 batch insert
    values = []
    for row in rows:
        values.extend(row)
    placeholders = ", ".join(["(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"] * len(rows))
    sql = f"INSERT OR IGNORE INTO price_data (symbol, timestamp, timeframe, open, high, low, close, volume_from, volume_to, source) VALUES {placeholders};"
    payload = {"sql": sql, "params": values}
    headers = {
        "Authorization": f"Bearer {D1_API_TOKEN}",
        "Content-Type": "application/json"
    }
    resp = requests.post(D1_API_URL, json=payload, headers=headers)
    if not resp.ok:
        print(f"D1 insert error: {resp.status_code} {resp.text}")
    else:
        print(f"Inserted batch of {len(rows)} rows.")
    time.sleep(0.2)  # Rate limit to avoid D1 overload

def migrate_sqlite_to_d1():
    total = 0
    for rows in fetch_rows():
        insert_batch_to_d1(rows)
        total += len(rows)
        print(f"Total migrated: {total}")
    print("Migration complete.")

if __name__ == "__main__":
    if not D1_API_URL or not D1_API_TOKEN:
        print("Set D1_API_URL and D1_API_TOKEN environment variables!")
    else:
        migrate_sqlite_to_d1()
