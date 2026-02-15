import asyncio
from datetime import datetime, timezone

import aiohttp

from ai.decision_engine import DecisionEngine
from core.config import settings
from core.database import SessionLocal
from core.logger import setup_logger
from execution.position_manager import PositionManager
from execution.risk_guard import RiskGuard
from models.schemas import ExecutionEvent
from notifications.telegram_bot import send_execution_alert
from strategy.data_feed import LiveDataFeed
from strategy.market_structure import QuantitativeEngine

logger = setup_logger("openclaw.worker")


if not settings.ENABLE_TESTNET:
    raise RuntimeError("ENABLE_TESTNET must remain true for this build.")
logger.info("TESTNET MODE ENABLED")

data_feed = LiveDataFeed(
    symbol=settings.TRADING_SYMBOL,
    timeframe=settings.TRADING_TIMEFRAME,
    max_candles=settings.MAX_CANDLES,
)
ai_brain = DecisionEngine()
risk_guard = RiskGuard(
    max_daily_drawdown_r=settings.MAX_DAILY_DRAWDOWN_R,
    max_trade_duration_mins=settings.MAX_TRADE_DURATION_MINS,
)
position_manager = PositionManager(
    risk_per_trade_percent=settings.RISK_PER_TRADE_PERCENT,
    min_rr_ratio=settings.MIN_RR_RATIO,
)


async def publish_event(event: ExecutionEvent) -> None:
    headers = {"X-Internal-Token": settings.INTERNAL_API_TOKEN}
    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                settings.INTERNAL_API_URL,
                headers=headers,
                json=event.model_dump(mode="json"),
            ) as response:
                if response.status >= 300:
                    body = await response.text()
                    logger.error("Failed posting ai-event status=%s body=%s", response.status, body)
    except Exception as exc:
        logger.error("Unable to publish ai-event: %s", exc)

    should_send_telegram = settings.TELEGRAM_ALERTS_ENABLED and (
        settings.TELEGRAM_ALERTS_INCLUDE_WAIT or event.status != "WAIT"
    )
    if should_send_telegram:
        await send_execution_alert(event)


async def process_closed_candle(locked_df):
    db = SessionLocal()
    try:
        if not risk_guard.check_daily_killswitch(db):
            event = ExecutionEvent(
                timestamp=datetime.now(timezone.utc),
                symbol=settings.TRADING_SYMBOL,
                action="WAIT",
                confidence=0,
                reasoning="Daily kill-switch active. Trading halted.",
                status="KILLSWITCH",
                price=float(locked_df["Close"].iloc[-1]),
                size=None,
                pnl_r=None,
            )
            await publish_event(event)
            return

        quant_engine = QuantitativeEngine(locked_df)
        market_state = quant_engine.run_execution_checklist()
        current_price = float(locked_df["Close"].iloc[-1])

        if not market_state.valid_poi_found:
            event = ExecutionEvent(
                symbol=settings.TRADING_SYMBOL,
                action="WAIT",
                confidence=0,
                reasoning="No valid quantitative POI found on closed candle.",
                status="WAIT",
                price=current_price,
                size=None,
                pnl_r=None,
            )
            await publish_event(event)
            return

        ai_decision = await ai_brain.evaluate_market(market_state)
        result = position_manager.validate_and_execute(
            ai_decision=ai_decision,
            symbol=settings.TRADING_SYMBOL,
            current_price=current_price,
            account_balance=settings.DEFAULT_ACCOUNT_BALANCE,
            db=db,
        )

        status_map = {
            "ignored": "IGNORED",
            "rejected": "REJECTED",
            "executed": "EXECUTED",
            "failed": "FAILED",
        }
        event = ExecutionEvent(
            symbol=settings.TRADING_SYMBOL,
            action=ai_decision.action,
            confidence=ai_decision.confidence,
            reasoning=ai_decision.reasoning if result.get("status") == "executed" else result.get("reason", ai_decision.reasoning),
            status=status_map.get(result.get("status", "failed"), "FAILED"),
            price=float(result.get("entry_price", current_price)),
            size=result.get("position_size"),
            pnl_r=None,
        )
        await publish_event(event)
    except Exception as exc:
        logger.error("Pipeline failure: %s", exc)
    finally:
        db.close()


async def main():
    logger.info("Initializing OpenClaw worker.")
    await data_feed.start_stream(on_candle_close_callback=process_closed_candle)


if __name__ == "__main__":
    asyncio.run(main())
