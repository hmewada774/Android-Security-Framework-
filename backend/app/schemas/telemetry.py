from pydantic import BaseModel, Field
from typing import Optional

class TelemetryReport(BaseModel):
    device_id: str
    battery_level: Optional[int] = Field(None, ge=0, le=100)
    is_charging: Optional[bool] = None
    network_type: Optional[str] = None
    cpu_usage: Optional[float] = None
    ram_usage_mb: Optional[float] = None
    session_id: Optional[str] = None

class TelemetryResponse(BaseModel):
    status: str
    recorded_at: str
