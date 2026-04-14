# api/websocket.py
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.inference import engine

router = APIRouter()

class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()


@router.websocket("/ws/control")
async def websocket_control(websocket: WebSocket):
    """
    WebSocket 接口 — 用于实时控制

    支持的消息类型:
    - {"type": "config", "interval": 0.5}   → 调整预测频率
    - {"type": "pause"}                      → 暂停预测
    - {"type": "resume"}                     → 恢复预测
    - {"type": "status"}                     → 查询状态
    """
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg["type"] == "config":
                engine.update_config(interval=msg.get("interval"))
                await websocket.send_json({
                    "type": "config_updated",
                    "interval": msg.get("interval")
                })

            elif msg["type"] == "pause":
                engine.stop()
                await websocket.send_json({"type": "paused"})

            elif msg["type"] == "resume":
                engine._running = True
                await websocket.send_json({"type": "resumed"})

            elif msg["type"] == "status":
                await websocket.send_json({
                    "type": "status",
                    "running": engine._running,
                    "interval": engine._interval,
                    "buffer_size": len(engine.buffer)
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
