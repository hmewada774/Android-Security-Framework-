from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Header, status
from database.connection import get_db
from backend.app.schemas.telemetry import TelemetryReport, TelemetryResponse
from backend.app.websockets.connection_manager import manager

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])

@router.post("/report", response_model=TelemetryResponse)
async def submit_telemetry(data: TelemetryReport, authorization: str = Header(None)):
    now_iso = datetime.now(timezone.utc).isoformat()
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Expected 'Bearer <token>'.",
        )
    token = authorization[7:].strip()

    with get_db() as conn:
        # Strictly verify device ownership and paired status
        cur = conn.execute(
            "SELECT status FROM devices WHERE device_id = ? AND auth_token = ?",
            (data.device_id, token),
        )
        row = cur.fetchone()
        if not row or row["status"] != "paired":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Token does not match device_id or device is not paired.",
            )
            
        conn.execute(
            """
            INSERT INTO telemetry_logs (
                session_id, device_id, battery_level, is_charging,
                network_type, cpu_usage, ram_usage_mb, recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.session_id,
                data.device_id,
                data.battery_level,
                data.is_charging,
                data.network_type,
                data.cpu_usage,
                data.ram_usage_mb,
                now_iso,
            ),
        )
        # Update last seen
        conn.execute(
            "UPDATE devices SET last_seen_at = ? WHERE device_id = ?",
            (now_iso, data.device_id),
        )

    # Broadcast telemetry update to dashboards
    await manager.broadcast_to_dashboards({
        "event": "TELEMETRY_UPDATE",
        "data": {
            "device_id": data.device_id,
            "battery_level": data.battery_level,
            "is_charging": data.is_charging,
            "network_type": data.network_type,
            "cpu_usage": data.cpu_usage,
            "ram_usage_mb": data.ram_usage_mb,
            "recorded_at": now_iso,
        },
    })

    return TelemetryResponse(status="success", recorded_at=now_iso)

@router.get("/latest/{device_id}")
def get_latest_telemetry(device_id: str):
    """Retrieve the single most recent telemetry log for a device."""
    with get_db() as conn:
        cur = conn.execute(
            """
            SELECT battery_level, is_charging, network_type, cpu_usage, ram_usage_mb, recorded_at
            FROM telemetry_logs
            WHERE device_id = ?
            ORDER BY recorded_at DESC LIMIT 1
            """,
            (device_id,),
        )
        row = cur.fetchone()
        if not row:
            return {"available": False, "device_id": device_id, "message": "No telemetry data recorded yet."}
        return {"available": True, "device_id": device_id, "data": dict(row)}
