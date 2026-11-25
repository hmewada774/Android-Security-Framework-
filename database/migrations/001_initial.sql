-- Android Security Framework (ASF) Database Schema
-- Version: 001_initial

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT UNIQUE NOT NULL,
    device_name TEXT,
    model TEXT,
    os_version TEXT,
    pairing_pin TEXT,
    pairing_pin_expires_at TEXT,
    auth_token TEXT UNIQUE,
    status TEXT NOT NULL DEFAULT 'unpaired' CHECK(status IN ('unpaired', 'pending', 'paired', 'revoked')),
    last_seen_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_devices_device_id ON devices(device_id);
CREATE INDEX IF NOT EXISTS idx_devices_auth_token ON devices(auth_token);

CREATE TABLE IF NOT EXISTS monitoring_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    device_id TEXT NOT NULL,
    session_type TEXT NOT NULL CHECK(session_type IN ('screen_share', 'telemetry', 'typing_lab')),
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'stopped', 'aborted')),
    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
    ended_at TEXT,
    FOREIGN KEY(device_id) REFERENCES devices(device_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON monitoring_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_device_id ON monitoring_sessions(device_id);

CREATE TABLE IF NOT EXISTS telemetry_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    device_id TEXT NOT NULL,
    battery_level INTEGER,
    is_charging BOOLEAN,
    network_type TEXT,
    cpu_usage REAL,
    ram_usage_mb REAL,
    recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES monitoring_sessions(session_id) ON DELETE SET NULL,
    FOREIGN KEY(device_id) REFERENCES devices(device_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_telemetry_device_time ON telemetry_logs(device_id, recorded_at);

CREATE TABLE IF NOT EXISTS typing_benchmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    device_id TEXT NOT NULL,
    test_prompt_id TEXT NOT NULL,
    wpm REAL NOT NULL,
    accuracy_percent REAL NOT NULL,
    avg_flight_time_ms REAL NOT NULL,
    avg_hold_time_ms REAL NOT NULL,
    total_keystrokes INTEGER NOT NULL,
    error_count INTEGER NOT NULL,
    recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES monitoring_sessions(session_id) ON DELETE SET NULL,
    FOREIGN KEY(device_id) REFERENCES devices(device_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_typing_device ON typing_benchmarks(device_id);

CREATE TABLE IF NOT EXISTS security_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    device_id TEXT,
    event_type TEXT NOT NULL,
    session_id TEXT,
    event_status TEXT NOT NULL,
    details TEXT
);

CREATE INDEX IF NOT EXISTS idx_events_timestamp ON security_events(event_timestamp);
CREATE INDEX IF NOT EXISTS idx_events_device ON security_events(device_id);
