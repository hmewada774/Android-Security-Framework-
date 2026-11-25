import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "asf.db"

def get_db_path() -> Path:
    env_path = os.getenv("ASF_DB_PATH")
    if env_path:
        return Path(env_path)
    return DEFAULT_DB_PATH

def init_db(db_path: Path | None = None) -> None:
    target_path = db_path or get_db_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    migration_file = Path(__file__).resolve().parent / "migrations" / "001_initial.sql"
    
    with sqlite3.connect(target_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        with open(migration_file, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()

@contextmanager
def get_db(db_path: Path | None = None):
    target_path = db_path or get_db_path()
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
