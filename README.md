# Android Security Framework (ASF)

> Native Android security monitoring framework controlled via Python CLI and local web dashboard. Designed for authorized testing on owner-controlled devices.

---

## Key Features
- **Python CLI Controller:** Manage devices, generate pairing codes, and tail security events.
- **FastAPI Async Backend:** High-speed event routing with WebSocket multiplexing.
- **Zero-Dependency Web Dashboard:** HTML5, CSS3, ES6 JavaScript; no React or complex node bundles.
- **Native Android Agent (Kotlin):** Jetpack Compose UI, MediaProjection screen sharing with explicit OS prompt, foreground service with notification indicator.
- **Sandboxed Typing Lab:** Isolated keystroke dynamics and flight/hold time analytics without global accessibility spying.
- **Embedded SQLite:** Zero-setup, serverless, atomic local storage with WAL enabled.

---

## Directory Layout
- `controller/`: Python terminal CLI and WebSocket listener.
- `backend/`: FastAPI application, endpoints, schemas, and WebSocket connection hub.
- `dashboard/`: Static web UI shell and canvas stream renderer.
- `android-agent/`: Native Android project source and configurations.
- `database/`: SQLite schema, migration scripts, and connection managers.
- `tests/`: Automated unit and integration test suite.
- `docs/`: Architecture diagrams, security model, and setup instructions.

---

## Quickstart (Phase 1 Foundation)

### 1. Run Automated Tests
```bash
python3 -m pytest tests/
```

### 2. Start the Backend Server
```bash
cd Android-Security-Framework
python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Open the Local Dashboard
Navigate to `http://127.0.0.1:8000` in your web browser.

### 4. Use the Python Controller
```bash
python3 controller/cli.py health
python3 controller/cli.py pair --name "Pixel 8 Test"
python3 controller/cli.py devices
```
