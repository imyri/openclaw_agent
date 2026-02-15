from core.database import SessionLocal
from execution.risk_guard import RiskGuard


def test_risk_guard_trips_killswitch_at_daily_limit():
    guard = RiskGuard(max_daily_drawdown_r=2.0)
    db = SessionLocal()
    try:
        guard.update_daily_pnl(db, -2.1)
        assert guard.check_daily_killswitch(db) is False
    finally:
        db.close()
