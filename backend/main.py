from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json

app = FastAPI(title="OpenClaw Command-Centre API")

# Allow the Next.js frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    """Manages active WebSocket connections to broadcast AI thoughts."""
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Pushes structured JSON to all connected Next.js clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

@app.websocket("/ws/ai-feed")
async def ai_feed_endpoint(websocket: WebSocket):
    """The WebSocket tunnel for the frontend."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive. 
            # In production, worker.py will call manager.broadcast() 
            # every time the DecisionEngine outputs a new JSON thought.
            data = await websocket.receive_text() 
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/api/risk-state")
async def get_risk_state():
    """REST endpoint for initial dashboard load (PnL, Drawdown, Active Trades)."""
    # Fetch from SQLite database updated by execution/risk_guard.py
    return {
        "daily_pnl_r": 0.5,
        "max_drawdown_limit": -2.0,
        "killswitch_active": False,
        "active_trades": []
    }