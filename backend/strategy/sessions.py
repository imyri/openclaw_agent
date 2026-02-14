from datetime import datetime, time
import pytz
import logging

logger = logging.getLogger("openclaw.sessions")

class SessionManager:
    """
    Strictly enforces UTC canonical session times and overlap killzones.
    """
    def __init__(self):
        self.utc_zone = pytz.utc

        # Defined strictly in UTC as per OpenClaw architectural rules
        self.sessions = {
            "SYDNEY": {"open": time(22, 0), "close": time(7, 0)},
            "TOKYO": {"open": time(0, 0), "close": time(9, 0)},
            "LONDON": {"open": time(8, 0), "close": time(17, 0)},
            "NEW_YORK": {"open": time(13, 0), "close": time(22, 0)}
        }
        
        self.overlaps = {
            "TOKYO_LONDON": {"start": time(8, 0), "end": time(9, 0)},
            "LONDON_NY": {"start": time(13, 0), "end": time(17, 0)}
        }

    def _is_time_between(self, current_time: time, start: time, end: time) -> bool:
        """Handles midnight wrap-arounds for UTC time checks."""
        if start < end:
            return start <= current_time <= end
        else: # Crosses midnight (e.g., Sydney)
            return current_time >= start or current_time <= end

    def get_active_sessions(self, current_dt_utc: datetime) -> list[str]:
        """Returns a list of currently active canonical sessions."""
        current_time = current_dt_utc.time()
        active = []
        for session, hours in self.sessions.items():
            if self._is_time_between(current_time, hours["open"], hours["close"]):
                active.append(session)
        return active

    def is_valid_killzone(self, current_dt_utc: datetime) -> bool:
        """
        Execution is ONLY allowed during high-volume overlaps or specific Silver Bullets.
        """
        current_time = current_dt_utc.time()
        
        # Check overlaps
        for overlap, hours in self.overlaps.items():
            if self._is_time_between(current_time, hours["start"], hours["end"]):
                return True
                
        # NY Silver Bullet (14:00 - 15:00 UTC / 10 AM - 11 AM EST)
        if self._is_time_between(current_time, time(14, 0), time(15, 0)):
            return True
            
        return False