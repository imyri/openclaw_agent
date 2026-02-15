from __future__ import annotations

from datetime import datetime, timezone

import aiohttp

from core.config import settings
from core.logger import setup_logger
from models.schemas import ExecutionEvent

logger = setup_logger("openclaw.telegram")


def _telegram_enabled() -> bool:
    return (
        settings.TELEGRAM_ALERTS_ENABLED
        and bool(settings.TELEGRAM_BOT_TOKEN.strip())
        and bool(settings.TELEGRAM_CHAT_ID.strip())
    )


async def send_telegram_message(text: str) -> bool:
    """Send raw text message to Telegram. Returns True on success."""
    if not _telegram_enabled():
        logger.warning("Telegram alerts disabled or credentials missing.")
        return False

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": settings.TELEGRAM_CHAT_ID,
        "text": text,
    }

    timeout = aiohttp.ClientTimeout(total=10)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    body = await response.text()
                    logger.error("Telegram send failed status=%s body=%s", response.status, body)
                    return False
        return True
    except Exception as exc:
        logger.error("Telegram send exception: %s", exc)
        return False


def format_execution_event_message(event: ExecutionEvent) -> str:
    ts = event.timestamp.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    price = f"{event.price:.2f}" if event.price is not None else "-"
    size = f"{event.size:.6f}" if event.size is not None else "-"
    pnl_r = f"{event.pnl_r:.2f}" if event.pnl_r is not None else "-"
    return (
        "OpenClaw Alert\n"
        f"Time: {ts}\n"
        f"Symbol: {event.symbol}\n"
        f"Status: {event.status}\n"
        f"Action: {event.action}\n"
        f"Confidence: {event.confidence}%\n"
        f"Price: {price}\n"
        f"Size: {size}\n"
        f"PnL(R): {pnl_r}\n"
        f"Reason: {event.reasoning}"
    )


async def send_execution_alert(event: ExecutionEvent) -> bool:
    msg = format_execution_event_message(event)
    return await send_telegram_message(msg)


async def send_daily_8am_report(market_data: dict, news_data: dict):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    trade_lines = []
    for pair, data in market_data.items():
        trade_lines.append(
            f"{pair}: Bias={data.get('bias', 'Neutral')} | POI={data.get('poi', 'N/A')} | "
            f"Reason={data.get('reasoning', 'Awaiting setup')}"
        )
    if not trade_lines:
        trade_lines.append("No trade opportunities yet.")

    news_lines = []
    for event in news_data or []:
        news_lines.append(f"{event['time']} UTC | {event['currency']} | {event['event_name']}")
    if not news_lines:
        news_lines.append("No major events scheduled.")

    text = (
        "OpenClaw Daily Briefing\n"
        f"Date: {today}\n\n"
        "Trade Opportunities:\n"
        + "\n".join(trade_lines)
        + "\n\nUpcoming High-Impact News:\n"
        + "\n".join(news_lines)
    )
    await send_telegram_message(text)
