from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone
from core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class TradeRecord(Base):
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    action = Column(String) # LONG or SHORT
    entry_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    status = Column(String, default="OPEN") # OPEN, WON, LOST, KILLED_BY_TIME
    pnl_r = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class DailyState(Base):
    __tablename__ = "daily_state"
    
    date_id = Column(String, primary_key=True) # e.g., "2024-02-15"
    current_pnl_r = Column(Float, default=0.0)
    killswitch_active = Column(Boolean, default=False)

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)