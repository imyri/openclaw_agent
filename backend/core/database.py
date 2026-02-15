from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from core.config import settings

engine_kwargs = {}
if settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class TradeRecord(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    action = Column(String)  # LONG or SHORT
    entry_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    position_size = Column(Float, default=0.0)
    status = Column(String, default="OPEN")  # OPEN, WON, LOST, KILLED_BY_TIME, FAILED
    pnl_r = Column(Float, default=0.0)
    exchange_order_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class DailyState(Base):
    __tablename__ = "daily_state"

    date_id = Column(String, primary_key=True)  # e.g. 2026-02-15
    current_pnl_r = Column(Float, default=0.0)
    killswitch_active = Column(Boolean, default=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Create tables on module import for local/dev startup.
init_db()
