def test_pairing_workflow(client):
    # 1. Initiate pairing from CLI / Dashboard
    init_res = client.post("/api/v1/pairing/init", json={"device_name": "Test Pixel Device"})
    assert init_res.status_code == 200
    init_data = init_res.json()
    assert "pairing_pin" in init_data
    pin = init_data["pairing_pin"]
    assert len(pin) == 6
    assert pin.isdigit()

    # 2. Claim pairing from Android agent using PIN
    claim_res = client.post("/api/v1/pairing/claim", json={
        "pairing_pin": pin,
        "device_id": "android_unit_test_uuid_123",
        "device_name": "Pixel 7 Pro",
        "model": "Pixel 7 Pro",
        "os_version": "Android 14 (API 34)"
    })
    assert claim_res.status_code == 200
    claim_data = claim_res.json()
    assert claim_data["status"] == "success"
    assert "auth_token" in claim_data
    assert len(claim_data["auth_token"]) == 64  # 32 bytes hex

    # 3. List devices to verify registration
    devices_res = client.get("/api/v1/pairing/devices")
    assert devices_res.status_code == 200
    devices = devices_res.json()
    device_match = [d for d in devices if d["device_id"] == "android_unit_test_uuid_123"]
    assert len(device_match) == 1
    assert device_match[0]["status"] == "paired"

    # 4. Attempting to claim with the same PIN again must fail (one-time use)
    reuse_res = client.post("/api/v1/pairing/claim", json={
        "pairing_pin": pin,
        "device_id": "rogue_device_999",
        "device_name": "Rogue Device"
    })
    assert reuse_res.status_code == 401

def test_invalid_pin_claim(client):
    res = client.post("/api/v1/pairing/claim", json={
        "pairing_pin": "000000",
        "device_id": "device_invalid_pin"
    })
    assert res.status_code == 401

def test_re_pairing_existing_device(client):
    # Ensure a device can be paired, revoked, and then re-paired without UNIQUE constraint violation
    dev_id = "re_pairing_test_uuid_555"
    
    # 1. First pairing
    init1 = client.post("/api/v1/pairing/init", json={"device_name": "Initial Device"})
    pin1 = init1.json()["pairing_pin"]
    claim1 = client.post("/api/v1/pairing/claim", json={
        "pairing_pin": pin1,
        "device_id": dev_id,
        "device_name": "Initial Device Name"
    })
    assert claim1.status_code == 200
    token1 = claim1.json()["auth_token"]

    # 2. Revoke device
    revoke = client.post(f"/api/v1/pairing/revoke/{dev_id}")
    assert revoke.status_code == 200

    # 3. Re-pair same device_id with a fresh PIN
    init2 = client.post("/api/v1/pairing/init", json={"device_name": "Re-paired Device"})
    pin2 = init2.json()["pairing_pin"]
    claim2 = client.post("/api/v1/pairing/claim", json={
        "pairing_pin": pin2,
        "device_id": dev_id,
        "device_name": "Updated Device Name"
    })
    assert claim2.status_code == 200
    token2 = claim2.json()["auth_token"]
    assert token2 != token1

    # Verify device status is back to paired
    devices_res = client.get("/api/v1/pairing/devices")
    devices = devices_res.json()
    match = [d for d in devices if d["device_id"] == dev_id]
    assert len(match) == 1
    assert match[0]["status"] == "paired"
    assert match[0]["device_name"] == "Updated Device Name"

def test_expired_pin_rejection(client):
    from datetime import datetime, timezone, timedelta
    from database.connection import get_db

    # Insert an expired pending PIN directly
    expired_time = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    expired_pin = "888999"
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO devices (device_id, device_name, pairing_pin, pairing_pin_expires_at, status)
            VALUES ('pending_expired_test', 'Expired Device', ?, ?, 'pending')
            """,
            (expired_pin, expired_time),
        )

    claim_res = client.post("/api/v1/pairing/claim", json={
        "pairing_pin": expired_pin,
        "device_id": "expired_test_uuid_999",
        "device_name": "Expired Test"
    })
    assert claim_res.status_code == 401
    assert "expired" in claim_res.json()["detail"].lower()

def test_pairing_claim_rate_limiting(client):
    from backend.app.routes.pairing import _failed_claim_attempts
    _failed_claim_attempts.clear()

    # Make 5 failed attempts
    for _ in range(5):
        res = client.post("/api/v1/pairing/claim", json={
            "pairing_pin": "000000",
            "device_id": "brute_force_dev"
        })
        assert res.status_code == 401

    # 6th attempt must be throttled with HTTP 429
    res_throttled = client.post("/api/v1/pairing/claim", json={
        "pairing_pin": "000000",
        "device_id": "brute_force_dev"
    })
    assert res_throttled.status_code == 429
    assert "rate limited" in res_throttled.json()["detail"].lower()

    # Clean up so other tests are not affected
    _failed_claim_attempts.clear()
