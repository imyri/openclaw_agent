import os
import aiohttp
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send_telegram_message(text: str):
    """Sends a raw text message to the configured Telegram chat."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Warning: Telegram credentials missing. Message not sent.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            if response.status != 200:
                print(f"Failed to send Telegram message: {await response.text()}")

async def send_daily_8am_report(market_data: dict, news_data: dict):
    """
    Constructs and sends the daily 8:00 AM IST report.
    - market_data: dict containing current POIs, FVGs, and bias for XAUUSD, EURUSD, USDJPY.
    - news_data: dict containing today's high-impact news (FOMC, NFP, etc.).
    """
    
    # 1. Format Trade Opportunities
    trade_section = "📊 *TODAY'S OPENCLAW TRADE OPPORTUNITIES*\n\n"
    for pair, data in market_data.items():
        trade_section += f"🔸 *{pair}*\n"
        trade_section += f"   • Bias: {data.get('bias', 'Neutral')}\n"
        trade_section += f"   • Reasoning: {data.get('reasoning', 'Awaiting clear MSS/FVG setup.')}\n"
        trade_section += f"   • POI: {data.get('poi', 'None identified yet')}\n\n"

    # 2. Format Upcoming News
    news_section = "🚨 *UPCOMING HIGH-IMPACT NEWS*\n\n"
    if not news_data:
        news_section += "   • No major FOMC/NFP events scheduled for today.\n"
    else:
        for event in news_data:
            news_section += f"   • *{event['time']} UTC*: {event['currency']} - {event['event_name']}\n"

    # 3. Combine and Send
    full_message = f"🌅 *OpenClaw Daily Briefing*\nDate: {datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%Y-%m-%d')}\n\n"
    full_message += trade_section + news_section
    
    await send_telegram_message(full_message)