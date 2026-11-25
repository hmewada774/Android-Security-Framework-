import json
import pytest

def test_overview_endpoint(client):
    res = client.get("/api/v1/overview")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "operational"
    assert "total_paired_devices" in data
    assert "connected_devices" in data
    assert "active_monitoring_sessions" in data
    assert "recent_events" in data
    assert isinstance(data["recent_events"], list)

def test_security_events_and_export(client):
    # 1. Pair a device to generate a security event
    init_res = client.post("/api/v1/pairing/init", json={"device_name": "Event Device"})
    pin = init_res.json()["pairing_pin"]
    dev_id = "evt_test_dev_111"
    claim_res = client.post("/api/v1/pairing/claim", json={
        "pairing_pin": pin,
        "device_id": dev_id,
        "device_name": "Event Device"
    })
    assert claim_res.status_code == 200

    # 2. Query events endpoint
    events_res = client.get("/api/v1/events")
    assert events_res.status_code == 200
    events = events_res.json()
    assert len(events) >= 1
    types = [e["event_type"] for e in events]
    assert "DEVICE_PAIRED" in types

    # Filter by device_id
    filtered_res = client.get(f"/api/v1/events?device_id={dev_id}")
    assert filtered_res.status_code == 200
    filtered = filtered_res.json()
    assert len(filtered) >= 1
    assert all(e["device_id"] == dev_id for e in filtered)

    # 3. Export as JSON
    json_export = client.get(f"/api/v1/events/export?format=json&device_id={dev_id}")
    assert json_export.status_code == 200
    assert "application/json" in json_export.headers["content-type"]
    assert "attachment" in json_export.headers.get("content-disposition", "")
    exported_data = json.loads(json_export.text)
    assert isinstance(exported_data, list)
    assert len(exported_data) >= 1

    # 4. Export as CSV
    csv_export = client.get(f"/api/v1/events/export?format=csv&device_id={dev_id}")
    assert csv_export.status_code == 200
    assert "text/csv" in csv_export.headers["content-type"]
    assert "attachment" in csv_export.headers.get("content-disposition", "")
    csv_text = csv_export.text
    assert "event_timestamp,device_id,event_type" in csv_text
    assert dev_id in csv_text

def test_latest_telemetry_unavailable_and_available(client):
    # Pair device
    init_res = client.post("/api/v1/pairing/init", json={"device_name": "Telemetry Avail Dev"})
    pin = init_res.json()["pairing_pin"]
    dev_id = "tel_avail_dev_222"
    claim = client.post("/api/v1/pairing/claim", json={
        "pairing_pin": pin,
        "device_id": dev_id,
        "device_name": "Telemetry Avail Dev"
    })
    token = claim.json()["auth_token"]

    # 1. Before submitting telemetry -> available is False
    res_before = client.get(f"/api/v1/telemetry/latest/{dev_id}")
    assert res_before.status_code == 200
    data_before = res_before.json()
    assert data_before["available"] is False
    assert "No telemetry" in data_before["message"]

    # 2. Submit telemetry
    client.post(
        "/api/v1/telemetry/report",
        json={
            "device_id": dev_id,
            "battery_level": 77,
            "is_charging": False,
            "network_type": "Wi-Fi (6 GHz)",
            "cpu_usage": 18.2,
            "ram_usage_mb": 2048.0
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    # 3. After submitting telemetry -> available is True with real values
    res_after = client.get(f"/api/v1/telemetry/latest/{dev_id}")
    assert res_after.status_code == 200
    data_after = res_after.json()
    assert data_after["available"] is True
    assert data_after["data"]["battery_level"] == 77
    assert data_after["data"]["network_type"] == "Wi-Fi (6 GHz)"
    assert data_after["data"]["cpu_usage"] == 18.2

def test_monitoring_start_and_stop_endpoints(client):
    # Pair device
    init_res = client.post("/api/v1/pairing/init", json={"device_name": "Mon Dev"})
    pin = init_res.json()["pairing_pin"]
    dev_id = "mon_dev_333"
    client.post("/api/v1/pairing/claim", json={
        "pairing_pin": pin,
        "device_id": dev_id,
        "device_name": "Mon Dev"
    })

    # Start when agent is offline -> pending_agent_connection
    start_res = client.post("/api/v1/monitoring/start", json={"device_id": dev_id})
    assert start_res.status_code == 200
    start_data = start_res.json()
    assert start_data["status"] == "pending_agent_connection"
    assert start_data["connected"] is False

    # Stop endpoint execution
    stop_res = client.post("/api/v1/monitoring/stop", json={"device_id": dev_id})
    assert stop_res.status_code == 200
    assert stop_res.json()["status"] == "stopped"

    # List sessions
    sessions_res = client.get("/api/v1/monitoring/sessions")
    assert sessions_res.status_code == 200
    assert isinstance(sessions_res.json(), list)
