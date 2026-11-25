import json
import secrets
from datetime import datetime, timezone
from urllib.parse import urlparse
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database.connection import init_db, get_db
from database.events import record_security_event
from backend.app.config import settings
from backend.app.routes import (
    health_router,
    pairing_router,
    telemetry_router,
    typing_router,
    events_router,
    overview_router,
    monitoring_router,
)
from backend.app.websockets.connection_manager import manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite schema
    init_db()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

# Include API Routers
app.include_router(health_router, prefix=settings.API_V1_PREFIX)
app.include_router(pairing_router, prefix=settings.API_V1_PREFIX)
app.include_router(telemetry_router, prefix=settings.API_V1_PREFIX)
app.include_router(typing_router, prefix=settings.API_V1_PREFIX)
app.include_router(events_router, prefix=settings.API_V1_PREFIX)
app.include_router(overview_router, prefix=settings.API_V1_PREFIX)
app.include_router(monitoring_router, prefix=settings.API_V1_PREFIX)

# Static files & Dashboard Shell
if settings.STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(settings.STATIC_DIR)), name="static")

@app.get("/")
def serve_dashboard():
    index_path = settings.TEMPLATES_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": f"{settings.PROJECT_NAME} Backend Operational. UI shell loading."}

@app.get(f"{settings.API_V1_PREFIX}/auth/dashboard-token")
def get_dashboard_token():
    """Retrieve the active operator session token for local dashboard/CLI."""
    return {"token": settings.DASHBOARD_TOKEN}

# WebSocket Endpoints
@app.websocket("/ws/agent")
async def websocket_agent_endpoint(websocket: WebSocket, token: str = Query(None)):
    """
    Authenticated WebSocket endpoint for native Android Agent.
    Requires valid auth_token issued during pairing.
    """
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    device_id = None
    with get_db() as conn:
        cur = conn.execute(
            "SELECT device_id FROM devices WHERE auth_token = ? AND status = 'paired'",
            (token,),
        )
        row = cur.fetchone()
        if row:
            device_id = row["device_id"]

    if not device_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect_agent(device_id, websocket)
    record_security_event(event_type="AGENT_CONNECTED", device_id=device_id, event_status="SUCCESS")
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)
                event_type = data.get("type")
                if event_type == "screen_frame":
                    await manager.relay_screen_frame(device_id, data.get("frame"))
                elif event_type == "heartbeat":
                    await websocket.send_text(json.dumps({"type": "heartbeat_ack"}))
                elif event_type == "session_state":
                    new_state = data.get("state")
                    sess_type = data.get("session_type", "screen_share")
                    now_iso = datetime.now(timezone.utc).isoformat()
                    with get_db() as conn:
                        if new_state == "active":
                            sess_id = data.get("session_id", f"sess_{secrets.token_hex(6)}")
                            conn.execute(
                                """
                                INSERT OR REPLACE INTO monitoring_sessions (session_id, device_id, session_type, status, started_at)
                                VALUES (?, ?, ?, 'active', ?)
                                """,
                                (sess_id, device_id, sess_type, now_iso),
                            )
                            record_security_event(
                                event_type="SESSION_STARTED",
                                device_id=device_id,
                                session_id=sess_id,
                                event_status="ACTIVE",
                                details=f"Type: {sess_type}",
                            )
                        elif new_state == "stopped":
                            conn.execute(
                                """
                                UPDATE monitoring_sessions
                                SET status = 'stopped', ended_at = ?
                                WHERE device_id = ? AND status = 'active'
                                """,
                                (now_iso, device_id),
                            )
                            record_security_event(
                                event_type="SESSION_STOPPED",
                                device_id=device_id,
                                event_status="STOPPED",
                                details=f"Type: {sess_type}",
                            )
                    await manager.broadcast_to_dashboards({
                        "event": "SESSION_STATE",
                        "device_id": device_id,
                        "state": new_state,
                        "session_type": sess_type,
                    })
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect_agent(device_id)
        record_security_event(event_type="AGENT_DISCONNECTED", device_id=device_id, event_status="TERMINATED")
        # Update any open active sessions for this device to stopped
        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            conn.execute(
                "UPDATE monitoring_sessions SET status = 'stopped', ended_at = ? WHERE device_id = ? AND status = 'active'",
                (now_iso, device_id),
            )
        await manager.broadcast_to_dashboards({
            "event": "AGENT_DISCONNECTED",
            "device_id": device_id,
        })

@app.websocket("/ws/dashboard")
async def websocket_dashboard_endpoint(websocket: WebSocket, token: str = Query(None)):
    """
    WebSocket endpoint for local browser dashboard and terminal observers.
    Streams live telemetry, session alerts, and screen frames.
    Requires valid dashboard_token and validates origin against CSWSH.
    """
    # 1. Dashboard Token Authentication (constant-time comparison)
    if not token or not secrets.compare_digest(token, settings.DASHBOARD_TOKEN):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 2. CSWSH Origin validation
    origin = websocket.headers.get("origin")
    if origin:
        parsed = urlparse(origin)
        server_host = websocket.url.hostname or "127.0.0.1"
        allowed_hosts = {"localhost", "127.0.0.1", "0.0.0.0", server_host}
        if parsed.hostname not in allowed_hosts:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    await manager.connect_dashboard(websocket)
    try:
        while True:
            raw_msg = await websocket.receive_text()
            try:
                cmd_data = json.loads(raw_msg)
                event = cmd_data.get("event")
                if event == "COMMAND_STOP_STREAM":
                    target_dev = cmd_data.get("device_id")
                    stop_payload = {"command": "STOP_STREAM", "reason": "Operator stop requested"}
                    if target_dev:
                        await manager.send_command_to_agent(target_dev, stop_payload)
                    else:
                        await manager.send_command_to_all_agents(stop_payload)
                    
                    now_iso = datetime.now(timezone.utc).isoformat()
                    with get_db() as conn:
                        if target_dev:
                            conn.execute(
                                "UPDATE monitoring_sessions SET status = 'stopped', ended_at = ? WHERE device_id = ? AND status = 'active'",
                                (now_iso, target_dev),
                            )
                        else:
                            conn.execute(
                                "UPDATE monitoring_sessions SET status = 'stopped', ended_at = ? WHERE status = 'active'",
                                (now_iso,),
                            )

                    await manager.broadcast_to_dashboards({
                        "event": "SESSION_STATE",
                        "state": "stopped",
                        "session_type": "screen_share",
                        "device_id": target_dev or "all",
                    })
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect_dashboard(websocket)
