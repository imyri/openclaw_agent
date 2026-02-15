import asyncio
from datetime import datetime, timezone

import pandas as pd

import worker
from models.schemas import AIDecision, FVGZone, MarketState


def _locked_df():
    ts = datetime.now(timezone.utc)
    return pd.DataFrame(
        [[100.0, 101.0, 99.0, 100.5, 1000]],
        columns=["Open", "High", "Low", "Close", "Volume"],
        index=[ts],
    )


def test_worker_pipeline_emits_executed_event_with_mocked_llm(monkeypatch):
    class _FakeQuantEngine:
        def __init__(self, df):
            self.df = df

        def run_execution_checklist(self):
            return MarketState(
                timestamp=datetime.now(timezone.utc),
                symbol="BTC/USDT",
                timeframe="5m",
                valid_poi_found=True,
                setup_type="BULLISH_MSS_WITH_DISPLACEMENT",
                stop_reference=99.0,
                closest_bullish_fvg=FVGZone(top=101.0, bottom=99.0),
            )

    async def _fake_eval(_):
        return AIDecision(
            action="LONG",
            confidence=85,
            reasoning="Mocked LLM decision",
            entry_poi=100.0,
            target_liquidity=104.0,
            stop_reference=99.0,
        )

    def _fake_execute(**kwargs):
        return {
            "status": "executed",
            "entry_price": 100.0,
            "position_size": 0.05,
            "entry_order_id": "paper-order",
        }

    events = []

    async def _fake_publish(event):
        events.append(event)

    monkeypatch.setattr(worker, "QuantitativeEngine", _FakeQuantEngine)
    monkeypatch.setattr(worker.ai_brain, "evaluate_market", _fake_eval)
    monkeypatch.setattr(worker.position_manager, "validate_and_execute", _fake_execute)
    monkeypatch.setattr(worker, "publish_event", _fake_publish)
    monkeypatch.setattr(worker.risk_guard, "check_daily_killswitch", lambda db: True)

    asyncio.run(worker.process_closed_candle(_locked_df()))

    assert len(events) == 1
    assert events[0].status == "EXECUTED"
    assert events[0].action == "LONG"
