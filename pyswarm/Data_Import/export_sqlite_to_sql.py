import sqlite3

# Path to your local SQLite database
SQLITE_DB = 'historical_local.db'
# Output SQL file
SQL_DUMP_FILE = 'historical_local.sql'

def export_sqlite_to_sql():
    conn = sqlite3.connect(SQLITE_DB)
    with open(SQL_DUMP_FILE, 'w', encoding='utf-8') as f:
        for line in conn.iterdump():
            # Skip SQLite-specific PRAGMA statements for D1 compatibility
            if line.startswith('PRAGMA') or line.startswith('BEGIN TRANSACTION;') or line.startswith('COMMIT;'):
                continue
            f.write(f'{line}\n')
    conn.close()
    print(f'Exported {SQLITE_DB} to {SQL_DUMP_FILE}')

if __name__ == '__main__':
    export_sqlite_to_sql()
