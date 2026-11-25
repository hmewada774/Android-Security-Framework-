import json
import pytest
from starlette.websockets import WebSocketDisconnect
from backend.app.config import settings

def test_websocket_agent_unauthenticated(client):
    # 1. No token provided
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/agent"):
            pass
    assert exc_info.value.code == 1008

    # 2. Invalid token provided
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/agent?token=invalid_hex_token_999999"):
            pass
    assert exc_info.value.code == 1008

def test_websocket_dashboard_authentication_and_origin(client):
    dash_token = settings.DASHBOARD_TOKEN

    # 1. Missing token -> 1008
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/dashboard"):
            pass
    assert exc_info.value.code == 1008

    # 2. Invalid token -> 1008
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/dashboard?token=invalid_observer_token_123"):
            pass
    assert exc_info.value.code == 1008

    # 3. Valid token with foreign malicious origin -> 1008
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            f"/ws/dashboard?token={dash_token}",
            headers={"Origin": "https://malicious-attacker.com"}
        ):
            pass
    assert exc_info.value.code == 1008

    # 4. Host header tampering with invalid token cannot bypass auth -> 1008
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            "/ws/dashboard?token=bad_token",
            headers={"Host": "127.0.0.1"}
        ):
            pass
    assert exc_info.value.code == 1008

    # 5. Valid token & valid local origin -> Connects successfully
    with client.websocket_connect(
        f"/ws/dashboard?token={dash_token}",
        headers={"Origin": "http://127.0.0.1:8000"}
    ) as ws:
        assert ws is not None

def test_websocket_agent_and_dashboard_relay(client):
    dash_token = settings.DASHBOARD_TOKEN

    # Pair a test device
    init_res = client.post("/api/v1/pairing/init", json={"device_name": "WS Test Device"})
    pin = init_res.json()["pairing_pin"]
    dev_id = "ws_test_device_999"
    claim = client.post("/api/v1/pairing/claim", json={
        "pairing_pin": pin,
        "device_id": dev_id,
        "device_name": "WS Test Device"
    })
    token = claim.json()["auth_token"]

    # Connect authenticated dashboard observer
    with client.websocket_connect(f"/ws/dashboard?token={dash_token}") as dash_ws:
        # Connect agent
        with client.websocket_connect(f"/ws/agent?token={token}") as agent_ws:
            # Dashboard should receive AGENT_CONNECTED
            dash_msg = json.loads(dash_ws.receive_text())
            assert dash_msg["event"] == "AGENT_CONNECTED"
            assert dash_msg["device_id"] == dev_id

            # Agent sends heartbeat
            agent_ws.send_text(json.dumps({"type": "heartbeat"}))
            ack = json.loads(agent_ws.receive_text())
            assert ack["type"] == "heartbeat_ack"

            # Agent streams a sample screen frame
            dummy_frame = "base64_encoded_dummy_jpeg_stream_data"
            agent_ws.send_text(json.dumps({
                "type": "screen_frame",
                "frame": dummy_frame
            }))
            frame_msg = json.loads(dash_ws.receive_text())
            assert frame_msg["event"] == "SCREEN_FRAME"
            assert frame_msg["device_id"] == dev_id
            assert frame_msg["data"] == dummy_frame

            # Dashboard operator clicks "Stop Monitoring"
            dash_ws.send_text(json.dumps({
                "event": "COMMAND_STOP_STREAM",
                "device_id": dev_id
            }))

            # Agent must receive STOP_STREAM command
            agent_cmd = json.loads(agent_ws.receive_text())
            assert agent_cmd["command"] == "STOP_STREAM"

            # Dashboard receives SESSION_STATE stopped
            stop_notify = json.loads(dash_ws.receive_text())
            assert stop_notify["event"] == "SESSION_STATE"
            assert stop_notify["state"] == "stopped"

            # Duplicate stop command handled safely without crash
            dash_ws.send_text(json.dumps({
                "event": "COMMAND_STOP_STREAM",
                "device_id": dev_id
            }))
            dup_cmd = json.loads(agent_ws.receive_text())
            assert dup_cmd["command"] == "STOP_STREAM"

def test_websocket_agent_revocation_disconnect(client):
    # Pair a device
    init_res = client.post("/api/v1/pairing/init", json={"device_name": "Revoke WS Device"})
    pin = init_res.json()["pairing_pin"]
    dev_id = "ws_revoke_dev_888"
    claim = client.post("/api/v1/pairing/claim", json={
        "pairing_pin": pin,
        "device_id": dev_id,
        "device_name": "Revoke WS Device"
    })
    token = claim.json()["auth_token"]

    # Connect agent WebSocket
    with client.websocket_connect(f"/ws/agent?token={token}") as agent_ws:
        # Revoke device via REST API while socket is active
        revoke_res = client.post(f"/api/v1/pairing/revoke/{dev_id}")
        assert revoke_res.status_code == 200

        # Active WebSocket must be closed with 1008
        with pytest.raises(WebSocketDisconnect) as exc_info:
            agent_ws.receive_text()
        assert exc_info.value.code == 1008

def test_dashboard_cswsh_protection(client):
    dash_token = settings.DASHBOARD_TOKEN
    # Foreign malicious origin should be rejected with 1008 even with a valid token
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            f"/ws/dashboard?token={dash_token}",
            headers={"Origin": "https://malicious-attacker-site.com"}
        ):
            pass
    assert exc_info.value.code == 1008
