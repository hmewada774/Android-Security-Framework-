from pydantic import BaseModel, Field
from typing import Optional

class TypingSessionSubmit(BaseModel):
    device_id: str
    test_prompt_id: str
    wpm: float = Field(..., ge=0)
    accuracy_percent: float = Field(..., ge=0, le=100)
    avg_flight_time_ms: float = Field(..., ge=0)
    avg_hold_time_ms: float = Field(..., ge=0)
    total_keystrokes: int = Field(..., ge=1)
    error_count: int = Field(..., ge=0)
    session_id: Optional[str] = None

class TypingSessionResponse(BaseModel):
    status: str
    session_id: str
    benchmark_id: int
    message: str
