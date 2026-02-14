import logging
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger("openclaw.risk_guard")

class RiskGuard:
    """
    The ultimate circuit breaker. Bypasses the LLM entirely to enforce survival.
    """
    def __init__(self, max_daily_drawdown_r: float = 2.0, max_trade_duration_mins: int = 30):
        self.max_daily_drawdown_r = max_daily_drawdown_r
        self.max_trade_duration_mins = max_trade_duration_mins
        
        # In production, these should be loaded from your local SQLite database
        self.current_daily_r_pnl = 0.0  
        self.active_trades = {}         

    def check_daily_killswitch(self) -> bool:
        """
        If we are down -2R for the day, cut the data feed and halt execution.
        """
        if self.current_daily_r_pnl <= -self.max_daily_drawdown_r:
            logger.critical(f"🛑 DAILY KILL-SWITCH ACTIVATED. Current PnL: {self.current_daily_r_pnl}R.")
            return False # Trading is NOT allowed
        return True      # Trading is allowed

    def enforce_time_stops(self, current_time: datetime) -> list:
        """
        Scans active trades. Kills any trade that has stagnated beyond 30 minutes.
        Returns a list of trade IDs that need to be force-closed by the Position Manager.
        """
        trades_to_kill = []
        for trade_id, trade_data in self.active_trades.items():
            duration = (current_time - trade_data['entry_time']).total_seconds() / 60.0
            if duration >= self.max_trade_duration_mins:
                logger.warning(f"⏱️ TIME STOP: Trade {trade_id} stagnated for {duration} mins. Killing.")
                trades_to_kill.append(trade_id)
                
        return trades_to_kill