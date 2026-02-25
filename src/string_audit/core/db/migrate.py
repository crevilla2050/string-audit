import sqlite3
from pathlib import Path
from datetime import datetime

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
DB_PATH = Path(__file__).parent / "data/dennis.db"

def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
    """)

    applied = {
        row[0] for row in cur.execute("SELECT version FROM schema_migrations")
    }

    for file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        version = file.name
        if version in applied:
            continue

        sql = file.read_text()
        cur.executescript(sql)

        cur.execute(
            "INSERT INTO schema_migrations VALUES (?, ?)",
            (version, datetime.utcnow().isoformat())
        )

        print(f"Applied migration {version}")

    conn.commit()
    conn.close()