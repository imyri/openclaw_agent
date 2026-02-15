import asyncio
from datetime import datetime, timezone

import aiohttp

from core.config import settings


async def trigger_dashboard():
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": settings.TRADING_SYMBOL,
        "action": "LONG",
        "confidence": 81,
        "reasoning": "Simulated signal for dashboard path validation.",
        "status": "EXECUTED",
        "price": 69420.50,
        "size": 0.05,
        "pnl_r": 0.0,
    }

    headers = {"X-Internal-Token": settings.INTERNAL_API_TOKEN}
    url = settings.INTERNAL_API_URL
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as response:
            body = await response.text()
            print(f"Status: {response.status} Body: {body}")


if __name__ == "__main__":
    asyncio.run(trigger_dashboard())
