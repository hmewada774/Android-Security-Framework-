from datetime import datetime, timezone
from database.connection import get_db

def record_security_event(
    event_type: str,
    device_id: str | None = None,
    session_id: str | None = None,
    event_status: str = "SUCCESS",
    details: str | None = None,
) -> int:
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO security_events (event_timestamp, device_id, event_type, session_id, event_status, details)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (now_iso, device_id, event_type, session_id, event_status, details),
        )
        return cur.lastrowid or 0
