def test_telemetry_and_typing_flow(client):
    # Setup paired device first
    init_res = client.post("/api/v1/pairing/init", json={"device_name": "Telemetry Test Device"})
    pin = init_res.json()["pairing_pin"]
    
    device_id = "test_telemetry_dev_456"
    claim = client.post("/api/v1/pairing/claim", json={
        "pairing_pin": pin,
        "device_id": device_id,
        "device_name": "Test Device",
        "model": "SM-G998B",
        "os_version": "Android 13"
    })
    token = claim.json()["auth_token"]

    # Test Telemetry submission with valid Bearer token
    tel_res = client.post(
        "/api/v1/telemetry/report",
        json={
            "device_id": device_id,
            "battery_level": 88,
            "is_charging": True,
            "network_type": "Wi-Fi (5 GHz)",
            "cpu_usage": 14.5,
            "ram_usage_mb": 1850.0
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert tel_res.status_code == 200
    assert tel_res.json()["status"] == "success"

    # Test Typing Benchmark submission (dedicated sandbox lab) with Bearer token
    type_res = client.post(
        "/api/v1/typing/session",
        json={
            "device_id": device_id,
            "test_prompt_id": "prompt_sec_01",
            "wpm": 62.4,
            "accuracy_percent": 98.5,
            "avg_flight_time_ms": 112.0,
            "avg_hold_time_ms": 78.5,
            "total_keystrokes": 180,
            "error_count": 3
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert type_res.status_code == 200
    type_data = type_res.json()
    assert type_data["status"] == "success"
    assert type_data["benchmark_id"] >= 1

    # Verify benchmark retrieval
    benchmarks_res = client.get(f"/api/v1/typing/benchmarks/{device_id}")
    assert benchmarks_res.status_code == 200
    benchmarks = benchmarks_res.json()
    assert len(benchmarks) >= 1
    assert benchmarks[0]["wpm"] == 62.4
    assert benchmarks[0]["avg_flight_time_ms"] == 112.0

def test_unpaired_device_telemetry_forbidden(client):
    # Missing token -> 401
    missing_res = client.post("/api/v1/telemetry/report", json={
        "device_id": "unknown_unpaired_device_000",
        "battery_level": 50
    })
    assert missing_res.status_code == 401

    # Invalid / unpaired device token -> 403
    unpaired_res = client.post(
        "/api/v1/telemetry/report",
        json={"device_id": "unknown_unpaired_device_000", "battery_level": 50},
        headers={"Authorization": "Bearer fake_token_unknown_123"}
    )
    assert unpaired_res.status_code == 403

def test_bearer_token_authentication_and_revocation(client):
    # 1. Pair a new device
    init_res = client.post("/api/v1/pairing/init", json={"device_name": "Auth Test Device"})
    pin = init_res.json()["pairing_pin"]
    dev_id = "auth_enforce_dev_777"
    claim = client.post("/api/v1/pairing/claim", json={
        "pairing_pin": pin,
        "device_id": dev_id,
        "device_name": "Secured Agent"
    })
    token = claim.json()["auth_token"]

    # 2. Submit telemetry with correct Bearer header
    valid_res = client.post(
        "/api/v1/telemetry/report",
        json={"device_id": dev_id, "battery_level": 95},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert valid_res.status_code == 200

    # 3. Submit telemetry with forged/invalid Bearer header
    invalid_res = client.post(
        "/api/v1/telemetry/report",
        json={"device_id": dev_id, "battery_level": 95},
        headers={"Authorization": "Bearer fake_token_hex_1234567890"}
    )
    assert invalid_res.status_code == 403

    # 4. Revoke device
    revoke_res = client.post(f"/api/v1/pairing/revoke/{dev_id}")
    assert revoke_res.status_code == 200

    # 5. Subsequent submission must be rejected
    revoked_res = client.post(
        "/api/v1/telemetry/report",
        json={"device_id": dev_id, "battery_level": 95},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert revoked_res.status_code == 403
