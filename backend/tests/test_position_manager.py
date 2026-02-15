from models.schemas import AIDecision
from core.database import SessionLocal
from execution.position_manager import PositionManager


class _DummyExchange:
    def create_order(self, *args, **kwargs):
        return {"id": "dummy-order"}


def test_position_manager_rejects_missing_levels(monkeypatch):
    monkeypatch.setattr("execution.position_manager.get_exchange_instance", lambda: _DummyExchange())
    manager = PositionManager(risk_per_trade_percent=0.01, min_rr_ratio=3.0)
    db = SessionLocal()
    try:
        decision = AIDecision(
            action="LONG",
            confidence=75,
            reasoning="entry present but no target/stop",
            entry_poi=100.0,
            target_liquidity=None,
            stop_reference=None,
        )
        result = manager.validate_and_execute(decision, "BTC/USDT", 100.0, 10000.0, db)
        assert result["status"] == "rejected"
    finally:
        db.close()


def test_position_manager_rejects_rr_below_threshold(monkeypatch):
    monkeypatch.setattr("execution.position_manager.get_exchange_instance", lambda: _DummyExchange())
    manager = PositionManager(risk_per_trade_percent=0.01, min_rr_ratio=3.0)
    db = SessionLocal()
    try:
        # entry 100, stop ref 99 -> stop 98.901 => risk ~=1.099, target 101 => reward=1 (RR<1)
        decision = AIDecision(
            action="LONG",
            confidence=75,
            reasoning="weak RR setup",
            entry_poi=100.0,
            target_liquidity=101.0,
            stop_reference=99.0,
        )
        result = manager.validate_and_execute(decision, "BTC/USDT", 100.0, 10000.0, db)
        assert result["status"] == "rejected"
        assert "Insufficient RR ratio" in result["reason"]
    finally:
        db.close()
