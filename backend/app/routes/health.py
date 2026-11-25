from datetime import datetime, timezone
from fastapi import APIRouter
from database.connection import get_db
from backend.app.schemas.health import HealthResponse
from backend.app.config import settings

router = APIRouter(tags=["Health"])

@router.get("/health", response_model=HealthResponse)
def get_health():
    now_iso = datetime.now(timezone.utc).isoformat()
    db_status = "unhealthy"
    details = {}
    
    try:
        with get_db() as conn:
            cur = conn.execute("SELECT count(*) as tbl_count FROM sqlite_master WHERE type='table';")
            row = cur.fetchone()
            tbl_count = row["tbl_count"] if row else 0
            db_status = "healthy"
            details["tables_found"] = tbl_count
    except Exception as e:
        details["db_error"] = str(e)
        
    return HealthResponse(
        status="operational" if db_status == "healthy" else "degraded",
        version=settings.VERSION,
        database=db_status,
        timestamp=now_iso,
        details=details,
    )
