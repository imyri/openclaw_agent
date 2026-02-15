import os
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

os.environ["DATABASE_URL"] = "sqlite:///./test_openclaw_state.db"
os.environ["ENABLE_TESTNET"] = "true"
os.environ["EXECUTE_ORDERS"] = "false"
os.environ["INTERNAL_API_TOKEN"] = "test-internal-token"
os.environ["INTERNAL_API_URL"] = "http://testserver/internal/ai-event"
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"

from core.database import Base, SessionLocal, engine  # noqa: E402


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.execute(text("DELETE FROM trades"))
    db.execute(text("DELETE FROM daily_state"))
    db.commit()
    db.close()
    yield
    db = SessionLocal()
    db.execute(text("DELETE FROM trades"))
    db.execute(text("DELETE FROM daily_state"))
    db.commit()
    db.close()


@pytest.fixture()
def now_utc():
    return datetime.now(timezone.utc)
