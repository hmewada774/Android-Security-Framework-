import os
import secrets
from pathlib import Path

class Settings:
    PROJECT_NAME: str = "Android Security Framework (ASF)"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DASHBOARD_DIR: Path = BASE_DIR / "dashboard"
    STATIC_DIR: Path = DASHBOARD_DIR / "static"
    TEMPLATES_DIR: Path = DASHBOARD_DIR / "templates"
    DB_PATH: Path = BASE_DIR / "asf.db"
    
    # Secure defaults: bind to localhost only by default
    HOST: str = os.getenv("ASF_HOST", "127.0.0.1")
    PORT: int = int(os.getenv("ASF_PORT", "8000"))
    DEBUG: bool = os.getenv("ASF_DEBUG", "false").lower() in ("true", "1")
    
    # Dashboard / Operator authentication token
    DASHBOARD_TOKEN: str = os.getenv("ASF_DASHBOARD_TOKEN", secrets.token_hex(32))

settings = Settings()
