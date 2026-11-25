from datetime import datetime, timezone
from fastapi import APIRouter
from database.connection import get_db
from backend.app.websockets.connection_manager import manager
from backend.app.config import settings

router = APIRouter(prefix="/overview", tags=["Overview"])

@router.get("")
def get_system_overview():
    """Aggregated system metrics for the Overview module."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        # Paired devices count
        cur_paired = conn.execute("SELECT count(*) as cnt FROM devices WHERE status = 'paired'")
        paired_count = cur_paired.fetchone()["cnt"]

        # Active monitoring sessions count
        cur_sessions = conn.execute("SELECT count(*) as cnt FROM monitoring_sessions WHERE status = 'active'")
        active_sessions = cur_sessions.fetchone()["cnt"]

        # Recent 5 security events
        cur_events = conn.execute(
            """
            SELECT id, event_timestamp, device_id, event_type, session_id, event_status, details
            FROM security_events
            ORDER BY event_timestamp DESC LIMIT 6
            """
        )
        recent_events = [dict(r) for r in cur_events.fetchall()]

    connected_dev_ids = list(manager.active_agents.keys())

    return {
        "status": "operational",
        "version": settings.VERSION,
        "total_paired_devices": paired_count,
        "connected_devices": len(connected_dev_ids),
        "connected_device_ids": connected_dev_ids,
        "active_monitoring_sessions": active_sessions,
        "recent_events": recent_events,
        "timestamp": now_iso,
    }
