from __future__ import annotations

from datetime import datetime, timezone

import aiohttp
from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.config import settings
from core.database import SessionLocal, TradeRecord, get_db
from core.logger import setup_logger
from models.schemas import ExecutionEvent, RiskState

logger = setup_logger("openclaw.api")

app = FastAPI(title="OpenClaw Command-Centre API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()


def _build_risk_state(db: Session) -> RiskState:
    today = datetime.now(timezone.utc).date().isoformat()
    row = db.execute(
        text("SELECT current_pnl_r, killswitch_active FROM daily_state WHERE date_id = :date_id"),
        {"date_id": today},
    ).fetchone()

    daily_pnl_r = float(row[0]) if row else 0.0
    killswitch_active = bool(row[1]) if row else False

    active_trades = db.query(TradeRecord).filter(TradeRecord.status == "OPEN").all()
    active_trade_payload = [
        {
            "id": trade.id,
            "symbol": trade.symbol,
            "action": trade.action,
            "entry_price": trade.entry_price,
            "stop_loss": trade.stop_loss,
            "take_profit": trade.take_profit,
            "created_at": trade.created_at.isoformat() if trade.created_at else None,
        }
        for trade in active_trades
    ]

    return RiskState(
        daily_pnl_r=daily_pnl_r,
        max_drawdown_limit=-settings.MAX_DAILY_DRAWDOWN_R,
        killswitch_active=killswitch_active,
        active_trades=active_trade_payload,
    )


@app.websocket("/ws/ai-feed")
async def ai_feed_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/internal/ai-event")
async def ingest_ai_event(
    event: ExecutionEvent,
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
):
    if x_internal_token != settings.INTERNAL_API_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized internal event")

    payload = event.model_dump(mode="json")
    await manager.broadcast(payload)
    return {"status": "ok"}


@app.get("/api/risk-state", response_model=RiskState)
async def get_risk_state(db: Session = Depends(get_db)):
    return _build_risk_state(db)


@app.get("/health/live")
async def health_live():
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready():
    checks = {"database": False, "ollama": False}

    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as exc:
        logger.error("Readiness DB check failed: %s", exc)
    finally:
        db.close()

    try:
        timeout = aiohttp.ClientTimeout(total=3)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags") as response:
                checks["ollama"] = response.status == 200
    except Exception as exc:
        logger.error("Readiness Ollama check failed: %s", exc)

    if not all(checks.values()):
        raise HTTPException(status_code=503, detail={"status": "not_ready", "checks": checks})
    return {"status": "ready", "checks": checks}
