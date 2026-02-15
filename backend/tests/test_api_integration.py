from datetime import datetime, timezone

from fastapi.testclient import TestClient

from core.config import settings
from core.database import DailyState, SessionLocal, TradeRecord
from main import app


def test_internal_event_is_broadcast_to_websocket():
    event_payload = {
        "timestamp": datetime(2026, 2, 15, tzinfo=timezone.utc).isoformat(),
        "symbol": "BTC/USDT",
        "action": "LONG",
        "confidence": 88,
        "reasoning": "Integration test broadcast",
        "status": "EXECUTED",
        "price": 70000.0,
        "size": 0.1,
        "pnl_r": 0.0,
    }

    with TestClient(app) as client:
        with client.websocket_connect("/ws/ai-feed") as websocket:
            response = client.post(
                "/internal/ai-event",
                headers={"X-Internal-Token": settings.INTERNAL_API_TOKEN},
                json=event_payload,
            )
            assert response.status_code == 200
            message = websocket.receive_json()
            assert message["symbol"] == event_payload["symbol"]
            assert message["action"] == event_payload["action"]
            assert message["confidence"] == event_payload["confidence"]
            assert message["status"] == event_payload["status"]


def test_risk_state_endpoint_reads_from_database():
    db = SessionLocal()
    today = datetime.now(timezone.utc).date().isoformat()
    db.add(DailyState(date_id=today, current_pnl_r=-0.75, killswitch_active=False))
    db.add(
        TradeRecord(
            symbol="BTC/USDT",
            action="LONG",
            entry_price=60000.0,
            stop_loss=59500.0,
            take_profit=61500.0,
            position_size=0.02,
            status="OPEN",
            pnl_r=0.0,
        )
    )
    db.commit()
    db.close()

    with TestClient(app) as client:
        response = client.get("/api/risk-state")
        assert response.status_code == 200
        payload = response.json()
        assert payload["daily_pnl_r"] == -0.75
        assert payload["killswitch_active"] is False
        assert len(payload["active_trades"]) == 1
