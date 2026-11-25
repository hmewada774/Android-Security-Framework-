import sqlite3
from database.connection import get_db, get_db_path

def test_database_tables_exist():
    with get_db() as conn:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
        )
        tables = [row["name"] for row in cur.fetchall()]
        
    expected_tables = ["devices", "monitoring_sessions", "telemetry_logs", "typing_benchmarks"]
    for t in expected_tables:
        assert t in tables, f"Expected table '{t}' was not found in SQLite database"

def test_database_foreign_keys_enabled():
    with get_db() as conn:
        cur = conn.execute("PRAGMA foreign_keys;")
        row = cur.fetchone()
        assert row[0] == 1, "SQLite foreign keys should be enabled"
