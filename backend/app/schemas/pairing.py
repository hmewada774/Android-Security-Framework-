from pydantic import BaseModel, Field
from typing import Optional

class PairingInitRequest(BaseModel):
    device_name: Optional[str] = "Android Device"

class PairingInitResponse(BaseModel):
    pairing_pin: str = Field(..., description="6-digit PIN to enter on Android agent")
    expires_in_seconds: int = 300
    message: str

class PairingClaimRequest(BaseModel):
    pairing_pin: str = Field(..., min_length=6, max_length=6)
    device_id: str = Field(..., min_length=4)
    device_name: Optional[str] = "Android Device"
    model: Optional[str] = "Unknown"
    os_version: Optional[str] = "Android"

class PairingClaimResponse(BaseModel):
    status: str
    auth_token: str
    device_id: str
    message: str

class DeviceStatusResponse(BaseModel):
    device_id: str
    device_name: Optional[str]
    model: Optional[str]
    os_version: Optional[str]
    status: str
    last_seen_at: Optional[str]
    created_at: Optional[str]
