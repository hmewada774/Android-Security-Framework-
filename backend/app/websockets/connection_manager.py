import json
from typing import Dict, List, Set
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # device_id -> WebSocket
        self.active_agents: Dict[str, WebSocket] = {}
        # set of connected dashboard / CLI observer websockets
        self.active_dashboards: Set[WebSocket] = set()

    async def connect_agent(self, device_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_agents[device_id] = websocket
        await self.broadcast_to_dashboards({
            "event": "AGENT_CONNECTED",
            "device_id": device_id,
        })

    def disconnect_agent(self, device_id: str):
        if device_id in self.active_agents:
            del self.active_agents[device_id]

    async def disconnect_and_close_agent(self, device_id: str, code: int = 1008, reason: str = "Session Terminated"):
        if device_id in self.active_agents:
            ws = self.active_agents.pop(device_id)
            try:
                await ws.close(code=code, reason=reason)
            except Exception:
                pass
            await self.broadcast_to_dashboards({
                "event": "AGENT_DISCONNECTED",
                "device_id": device_id,
                "reason": reason,
            })

    async def send_command_to_agent(self, device_id: str, data: dict) -> bool:
        if device_id in self.active_agents:
            try:
                await self.active_agents[device_id].send_text(json.dumps(data))
                return True
            except Exception:
                await self.disconnect_and_close_agent(device_id, reason="Communication error")
        return False

    async def send_command_to_all_agents(self, data: dict):
        device_ids = list(self.active_agents.keys())
        for dev_id in device_ids:
            await self.send_command_to_agent(dev_id, data)

    async def connect_dashboard(self, websocket: WebSocket):
        await websocket.accept()
        self.active_dashboards.add(websocket)

    def disconnect_dashboard(self, websocket: WebSocket):
        self.active_dashboards.discard(websocket)

    async def broadcast_to_dashboards(self, data: dict):
        message = json.dumps(data)
        stale = []
        for ws in self.active_dashboards:
            try:
                await ws.send_text(message)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.active_dashboards.discard(ws)

    async def relay_screen_frame(self, device_id: str, frame_data: str):
        await self.broadcast_to_dashboards({
            "event": "SCREEN_FRAME",
            "device_id": device_id,
            "data": frame_data,
        })

manager = ConnectionManager()
