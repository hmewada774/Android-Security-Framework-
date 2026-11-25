from .health import router as health_router
from .pairing import router as pairing_router
from .telemetry import router as telemetry_router
from .typing import router as typing_router
from .events import router as events_router
from .overview import router as overview_router
from .monitoring import router as monitoring_router

__all__ = [
    "health_router",
    "pairing_router",
    "telemetry_router",
    "typing_router",
    "events_router",
    "overview_router",
    "monitoring_router",
]
