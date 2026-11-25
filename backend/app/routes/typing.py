import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Header, status
from database.connection import get_db
from database.events import record_security_event
from backend.app.schemas.typing import TypingSessionSubmit, TypingSessionResponse
from backend.app.websockets.connection_manager import manager

router = APIRouter(prefix="/typing", tags=["Typing Lab"])

@router.post("/session", response_model=TypingSessionResponse)
async def submit_typing_benchmark(data: TypingSessionSubmit, authorization: str = Header(None)):
    now_iso = datetime.now(timezone.utc).isoformat()
    session_id = data.session_id or f"type_{uuid.uuid4().hex[:12]}"
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

        # Ensure session record
        conn.execute(
            """
            INSERT OR IGNORE INTO monitoring_sessions (session_id, device_id, session_type, status, started_at)
            VALUES (?, ?, 'typing_lab', 'stopped', ?)
            """,
            (session_id, data.device_id, now_iso),
        )

        # Store benchmark record
        cur = conn.execute(
            """
            INSERT INTO typing_benchmarks (
                session_id, device_id, test_prompt_id, wpm, accuracy_percent,
                avg_flight_time_ms, avg_hold_time_ms, total_keystrokes,
                error_count, recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                data.device_id,
                data.test_prompt_id,
                data.wpm,
                data.accuracy_percent,
                data.avg_flight_time_ms,
                data.avg_hold_time_ms,
                data.total_keystrokes,
                data.error_count,
                now_iso,
            ),
        )
        benchmark_id = cur.lastrowid

    record_security_event(
        event_type="TYPING_BENCHMARK_RECORDED",
        device_id=data.device_id,
        session_id=session_id,
        event_status="SUCCESS",
        details=f"WPM: {data.wpm}, Acc: {data.accuracy_percent}%, Prompt: {data.test_prompt_id}",
    )

    await manager.broadcast_to_dashboards({
        "event": "TYPING_BENCHMARK_RECORDED",
        "data": {
            "session_id": session_id,
            "device_id": data.device_id,
            "wpm": data.wpm,
            "accuracy_percent": data.accuracy_percent,
            "avg_flight_time_ms": data.avg_flight_time_ms,
            "avg_hold_time_ms": data.avg_hold_time_ms,
            "recorded_at": now_iso,
        },
    })

    return TypingSessionResponse(
        status="success",
        session_id=session_id,
        benchmark_id=benchmark_id,
        message="Typing metrics successfully stored in isolated audit benchmark table.",
    )

@router.get("/benchmarks/{device_id}")
def get_device_benchmarks(device_id: str):
    """Retrieve recent typing benchmarks for a given device."""
    with get_db() as conn:
        cur = conn.execute(
            """
            SELECT id, session_id, test_prompt_id, wpm, accuracy_percent,
                   avg_flight_time_ms, avg_hold_time_ms, total_keystrokes,
                   error_count, recorded_at
            FROM typing_benchmarks
            WHERE device_id = ?
            ORDER BY recorded_at DESC LIMIT 20
            """,
            (device_id,),
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]
