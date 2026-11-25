import json
import urllib.request
import urllib.error
import asyncio
import websockets

DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"

def make_request(path: str, method: str = "GET", data: dict | None = None, base_url: str = DEFAULT_BACKEND_URL):
    url = f"{base_url}{path}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data else None
    
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            res_body = response.read().decode("utf-8")
            return json.loads(res_body)
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        try:
            return {"error": True, "code": e.code, "detail": json.loads(err_msg)}
        except Exception:
            return {"error": True, "code": e.code, "detail": err_msg}
    except Exception as e:
        return {"error": True, "detail": str(e)}

def check_health(base_url: str = DEFAULT_BACKEND_URL):
    return make_request("/api/v1/health", base_url=base_url)

def init_pairing(device_name: str = "Android Security Tester", base_url: str = DEFAULT_BACKEND_URL):
    return make_request("/api/v1/pairing/init", method="POST", data={"device_name": device_name}, base_url=base_url)

def list_devices(base_url: str = DEFAULT_BACKEND_URL):
    return make_request("/api/v1/pairing/devices", base_url=base_url)

def revoke_device(device_id: str, base_url: str = DEFAULT_BACKEND_URL):
    return make_request(f"/api/v1/pairing/revoke/{device_id}", method="POST", base_url=base_url)

def get_dashboard_token(base_url: str = DEFAULT_BACKEND_URL):
    res = make_request("/api/v1/auth/dashboard-token", base_url=base_url)
    return res.get("token")

async def monitor_events(base_url: str = DEFAULT_BACKEND_URL):
    token = get_dashboard_token(base_url)
    token_param = f"?token={token}" if token else ""
    ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://") + f"/ws/dashboard{token_param}"
    print(f"[*] Connecting to live event stream: {ws_url.split('?')[0]}")
    print("[*] Press Ctrl+C to exit monitor mode.\n")
    try:
        async with websockets.connect(ws_url) as ws:
            while True:
                msg = await ws.recv()
                try:
                    payload = json.loads(msg)
                    event = payload.get("event", "UNKNOWN")
                    if event == "SCREEN_FRAME":
                        print(f"[STREAM] Frame received from {payload.get('device_id')} (data size: {len(payload.get('data', ''))} chars)")
                    elif event == "TELEMETRY_UPDATE":
                        tel = payload.get("data", {})
                        print(f"[TELEMETRY] Device: {tel.get('device_id')} | Battery: {tel.get('battery_level')}% | Net: {tel.get('network_type')}")
                    elif event == "TYPING_BENCHMARK_RECORDED":
                        tb = payload.get("data", {})
                        print(f"[TYPING LAB] Device: {tb.get('device_id')} | WPM: {tb.get('wpm')} | Acc: {tb.get('accuracy_percent')}% | Flight: {tb.get('avg_flight_time_ms')}ms")
                    else:
                        print(f"[EVENT] {event}: {payload}")
                except Exception:
                    print(f"[RAW] {msg}")
    except asyncio.CancelledError:
        print("\n[*] Monitor cancelled.")
    except Exception as e:
        print(f"[!] WebSocket error: {e}")
