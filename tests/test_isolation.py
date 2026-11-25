import json
import pytest
from backend.app.config import settings

def test_multi_device_websocket_isolation(client):
    dash_token = settings.DASHBOARD_TOKEN

    # 1. Pair Device A
    init_a = client.post("/api/v1/pairing/init", json={"device_name": "Device Alpha"})
    pin_a = init_a.json()["pairing_pin"]
    dev_a = "device_alpha_uuid_001"
    claim_a = client.post("/api/v1/pairing/claim", json={
        "pairing_pin": pin_a,
        "device_id": dev_a,
        "device_name": "Device Alpha"
    })
    token_a = claim_a.json()["auth_token"]

    # 2. Pair Device B
    init_b = client.post("/api/v1/pairing/init", json={"device_name": "Device Beta"})
    pin_b = init_b.json()["pairing_pin"]
    dev_b = "device_beta_uuid_002"
    claim_b = client.post("/api/v1/pairing/claim", json={
        "pairing_pin": pin_b,
        "device_id": dev_b,
        "device_name": "Device Beta"
    })
    token_b = claim_b.json()["auth_token"]

    # 3. Verify cross-device REST impersonation is rejected:
    # Token A used to submit telemetry for Device B -> 403 Forbidden
    cross_res = client.post(
        "/api/v1/telemetry/report",
        json={"device_id": dev_b, "battery_level": 75},
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert cross_res.status_code == 403

    # Token B used to submit typing session for Device A -> 403 Forbidden
    cross_typing = client.post(
        "/api/v1/typing/session",
        json={
            "device_id": dev_a,
            "test_prompt_id": "test_prompt",
            "wpm": 50.0,
            "accuracy_percent": 95.0,
            "avg_flight_time_ms": 120.0,
            "avg_hold_time_ms": 80.0,
            "total_keystrokes": 100,
            "error_count": 2
        },
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert cross_typing.status_code == 403

    # 4. Connect Dashboard, Agent A, and Agent B simultaneously
    with client.websocket_connect(f"/ws/dashboard?token={dash_token}") as dash_ws:
        with client.websocket_connect(f"/ws/agent?token={token_a}") as agent_a_ws:
            with client.websocket_connect(f"/ws/agent?token={token_b}") as agent_b_ws:
                # Dashboard consumes AGENT_CONNECTED events
                evt1 = json.loads(dash_ws.receive_text())
                evt2 = json.loads(dash_ws.receive_text())
                connected_devs = {evt1.get("device_id"), evt2.get("device_id")}
                assert dev_a in connected_devs
                assert dev_b in connected_devs

                # Agent A streams a frame
                frame_data_a = "FRAME_FROM_DEVICE_A"
                agent_a_ws.send_text(json.dumps({
                    "type": "screen_frame",
                    "frame": frame_data_a
                }))

                # Dashboard receives frame from Device A
                dash_frame = json.loads(dash_ws.receive_text())
                assert dash_frame["event"] == "SCREEN_FRAME"
                assert dash_frame["device_id"] == dev_a
                assert dash_frame["data"] == frame_data_a

                # Agent B does NOT receive Agent A's frame
                # Send heartbeat on Agent B to verify its socket queue contains only its own responses
                agent_b_ws.send_text(json.dumps({"type": "heartbeat"}))
                b_response = json.loads(agent_b_ws.receive_text())
                assert b_response["type"] == "heartbeat_ack"

                # Targeted stop command: Dashboard stops Device A only
                dash_ws.send_text(json.dumps({
                    "event": "COMMAND_STOP_STREAM",
                    "device_id": dev_a
                }))

                # Agent A receives STOP_STREAM
                a_cmd = json.loads(agent_a_ws.receive_text())
                assert a_cmd["command"] == "STOP_STREAM"

                # Agent B does NOT receive stop command, remains active
                agent_b_ws.send_text(json.dumps({"type": "heartbeat"}))
                b_ack = json.loads(agent_b_ws.receive_text())
                assert b_ack["type"] == "heartbeat_ack"
