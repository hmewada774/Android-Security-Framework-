import secrets
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, status
from database.connection import get_db
from database.events import record_security_event
from backend.app.websockets.connection_manager import manager

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])

class StartSessionRequest(BaseModel):
    device_id: str
    session_type: str = "screen_share"

class StopSessionRequest(BaseModel):
    device_id: Optional[str] = None
    session_id: Optional[str] = None

@router.get("/sessions")
def list_monitoring_sessions(limit: int = 20):
    """Retrieve recent monitoring sessions with device details."""
    with get_db() as conn:
        cur = conn.execute(
            """
            SELECT s.id, s.session_id, s.device_id, s.session_type, s.status, s.started_at, s.ended_at,
                   d.device_name, d.model
            FROM monitoring_sessions s
            LEFT JOIN devices d ON s.device_id = d.device_id
            ORDER BY s.started_at DESC LIMIT ?
            """,
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]

@router.post("/start")
async def start_monitoring_session(req: StartSessionRequest):
    """
    Request initiation of a monitoring session on a paired device.
    Verifies that the agent is actively connected via WebSocket.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    device_id = req.device_id

    # Verify device exists and is paired
    with get_db() as conn:
        cur = conn.execute("SELECT status, device_name FROM devices WHERE device_id = ?", (device_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Device not found.")
        if row["status"] != "paired":
            raise HTTPException(status_code=403, detail="Device is not authorized or paired.")

    # Check if agent is connected via WebSocket
    is_connected = device_id in manager.active_agents
    if not is_connected:
        return {
            "status": "pending_agent_connection",
            "connected": False,
            "message": "Device is not currently connected via WebSocket. Native Android agent must be running.",
        }

    session_id = f"sess_{secrets.token_hex(6)}"
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO monitoring_sessions (session_id, device_id, session_type, status, started_at)
            VALUES (?, ?, ?, 'active', ?)
            """,
            (session_id, device_id, req.session_type, now_iso),
        )

    # Dispatch start command to Android agent
    await manager.send_command_to_agent(device_id, {
        "command": "START_STREAM",
        "session_id": session_id,
        "session_type": req.session_type,
    })

    record_security_event(
        event_type="SESSION_STARTED",
        device_id=device_id,
        session_id=session_id,
        event_status="ACTIVE",
        details=f"Type: {req.session_type}",
    )

    await manager.broadcast_to_dashboards({
        "event": "SESSION_STATE",
        "device_id": device_id,
        "session_id": session_id,
        "state": "active",
        "session_type": req.session_type,
    })

    return {
        "status": "started",
        "connected": True,
        "session_id": session_id,
        "device_id": device_id,
        "message": "Start stream command dispatched to connected Android agent.",
    }

@router.post("/stop")
async def stop_monitoring_session(req: StopSessionRequest):
    """
    Explicit operator stop command.
    Signals the connected agent, updates SQLite session to stopped, and broadcasts state.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    device_id = req.device_id

    stop_payload = {"command": "STOP_STREAM", "reason": "Operator stop requested"}
    if device_id:
        await manager.send_command_to_agent(device_id, stop_payload)
    else:
        await manager.send_command_to_all_agents(stop_payload)

    with get_db() as conn:
        if device_id:
            conn.execute(
                "UPDATE monitoring_sessions SET status = 'stopped', ended_at = ? WHERE device_id = ? AND status = 'active'",
                (now_iso, device_id),
            )
        else:
            conn.execute(
                "UPDATE monitoring_sessions SET status = 'stopped', ended_at = ? WHERE status = 'active'",
                (now_iso,),
            )

    record_security_event(
        event_type="SESSION_STOPPED",
        device_id=device_id,
        event_status="TERMINATED",
        details="Operator issued stop command",
    )

    await manager.broadcast_to_dashboards({
        "event": "SESSION_STATE",
        "state": "stopped",
        "session_type": "screen_share",
        "device_id": device_id or "all",
    })

    return {"status": "stopped", "device_id": device_id or "all", "message": "Session terminated."}
