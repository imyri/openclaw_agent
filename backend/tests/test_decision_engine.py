import asyncio
from datetime import datetime, timezone

import aiohttp
import pytest

from ai.decision_engine import DecisionEngine
from models.schemas import MarketState


class _FakeResponse:
    def __init__(self, status: int, payload: dict):
        self.status = status
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self):
        return self._payload


class _FakeSession:
    def __init__(self, response: _FakeResponse):
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def post(self, url, json):
        return self._response


def _sample_market_state() -> MarketState:
    return MarketState(
        timestamp=datetime.now(timezone.utc),
        symbol="BTC/USDT",
        timeframe="5m",
        valid_poi_found=True,
        setup_type="BULLISH_MSS_WITH_DISPLACEMENT",
        stop_reference=100.0,
    )


def test_decision_engine_returns_wait_on_malformed_llm_output(monkeypatch):
    monkeypatch.setattr(DecisionEngine, "_load_execution_guide", lambda self: "guide")
    fake_response = _FakeResponse(status=200, payload={"response": "not-json-at-all"})
    monkeypatch.setattr(aiohttp, "ClientSession", lambda *args, **kwargs: _FakeSession(fake_response))

    engine = DecisionEngine()
    decision = asyncio.run(engine.evaluate_market(_sample_market_state()))

    assert decision.action == "WAIT"
    assert decision.confidence == 0
    assert decision.stop_reference == 100.0


def test_decision_engine_returns_wait_when_ollama_unavailable(monkeypatch):
    monkeypatch.setattr(DecisionEngine, "_load_execution_guide", lambda self: "guide")

    class _BrokenSession:
        async def __aenter__(self):
            raise aiohttp.ClientError("connection refused")

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(aiohttp, "ClientSession", lambda *args, **kwargs: _BrokenSession())

    engine = DecisionEngine()
    decision = asyncio.run(engine.evaluate_market(_sample_market_state()))

    assert decision.action == "WAIT"
    assert decision.confidence == 0
    assert "Connection Failure" in decision.reasoning
