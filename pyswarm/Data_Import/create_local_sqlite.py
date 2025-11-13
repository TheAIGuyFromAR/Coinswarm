import os
import sqlite3


def create_local_db(db_path="historical_local.db"):
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

if __name__ == "__main__":
    db_path = os.environ.get("LOCAL_SQLITE_PATH", "historical_local.db")
    create_local_db(db_path)
    print(f"Created local SQLite DB at {db_path} with price_data schema.")
