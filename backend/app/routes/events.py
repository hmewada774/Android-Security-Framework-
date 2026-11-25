import csv
import io
import json
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Query, Response
from database.connection import get_db

router = APIRouter(prefix="/events", tags=["Security Events"])

@router.get("")
def list_events(device_id: Optional[str] = None, limit: int = Query(50, ge=1, le=500)):
    """List recent security audit events, optionally filtered by device."""
    with get_db() as conn:
        if device_id:
            cur = conn.execute(
                """
                SELECT id, event_timestamp, device_id, event_type, session_id, event_status, details
                FROM security_events
                WHERE device_id = ?
                ORDER BY event_timestamp DESC LIMIT ?
                """,
                (device_id, limit),
            )
        else:
            cur = conn.execute(
                """
                SELECT id, event_timestamp, device_id, event_type, session_id, event_status, details
                FROM security_events
                ORDER BY event_timestamp DESC LIMIT ?
                """,
                (limit,),
            )
        rows = cur.fetchall()
        return [dict(r) for r in rows]

@router.get("/export")
def export_events(
    format: str = Query("json", pattern="^(json|csv)$"),
    device_id: Optional[str] = None,
):
    """Export security audit events as JSON or CSV file download."""
    with get_db() as conn:
        if device_id:
            cur = conn.execute(
                """
                SELECT id, event_timestamp, device_id, event_type, session_id, event_status, details
                FROM security_events
                WHERE device_id = ?
                ORDER BY event_timestamp DESC
                """,
                (device_id,),
            )
        else:
            cur = conn.execute(
                """
                SELECT id, event_timestamp, device_id, event_type, session_id, event_status, details
                FROM security_events
                ORDER BY event_timestamp DESC
                """
            )
        rows = [dict(r) for r in cur.fetchall()]

    date_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dev_suffix = f"_{device_id}" if device_id else ""

    if format == "csv":
        output = io.StringIO()
        fieldnames = ["id", "event_timestamp", "device_id", "event_type", "session_id", "event_status", "details"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        csv_content = output.getvalue()
        filename = f"asf_security_events{dev_suffix}_{date_str}.csv"
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    else:
        json_content = json.dumps(rows, indent=2)
        filename = f"asf_security_events{dev_suffix}_{date_str}.json"
        return Response(
            content=json_content,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
