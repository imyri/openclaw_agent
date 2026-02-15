from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from core.database import DailyState, TradeRecord

logger = logging.getLogger("openclaw.risk_guard")


class RiskGuard:
    """
    Central risk controller backed by DB state.
    """

    def __init__(self, max_daily_drawdown_r: float = 2.0, max_trade_duration_mins: int = 30):
        self.max_daily_drawdown_r = max_daily_drawdown_r
        self.max_trade_duration_mins = max_trade_duration_mins

    def _today_id(self) -> str:
        return datetime.now(timezone.utc).date().isoformat()

    def get_or_create_daily_state(self, db: Session) -> DailyState:
        state = db.get(DailyState, self._today_id())
        if state:
            return state

        state = DailyState(
            date_id=self._today_id(),
            current_pnl_r=0.0,
            killswitch_active=False,
        )
        db.add(state)
        db.commit()
        db.refresh(state)
        return state

    def check_daily_killswitch(self, db: Session) -> bool:
        """
        Returns True when trading is allowed, False when killswitch is active.
        """
        state = self.get_or_create_daily_state(db)
        should_halt = state.current_pnl_r <= -self.max_daily_drawdown_r

        if state.killswitch_active != should_halt:
            state.killswitch_active = should_halt
            db.commit()

        if should_halt:
            logger.critical(
                "DAILY KILL-SWITCH ACTIVATED. Current PnL: %.2fR, Limit: -%.2fR",
                state.current_pnl_r,
                self.max_daily_drawdown_r,
            )
        return not should_halt

    def update_daily_pnl(self, db: Session, delta_r: float) -> DailyState:
        state = self.get_or_create_daily_state(db)
        state.current_pnl_r += float(delta_r)
        state.killswitch_active = state.current_pnl_r <= -self.max_daily_drawdown_r
        db.commit()
        db.refresh(state)
        return state

    def enforce_time_stops(self, db: Session, current_time: datetime) -> list[int]:
        """
        Returns open trade IDs that exceeded max duration.
        """
        open_trades = db.query(TradeRecord).filter(TradeRecord.status == "OPEN").all()
        trades_to_kill: list[int] = []
        for trade in open_trades:
            duration_mins = (current_time - trade.created_at).total_seconds() / 60.0
            if duration_mins >= self.max_trade_duration_mins:
                logger.warning(
                    "TIME STOP triggered for trade %s at %.2f minutes.",
                    trade.id,
                    duration_mins,
                )
                trades_to_kill.append(trade.id)
        return trades_to_kill
