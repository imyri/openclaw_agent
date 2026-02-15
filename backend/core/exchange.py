import logging

import ccxt

from core.config import settings

logger = logging.getLogger("openclaw.exchange")


def get_exchange_instance():
    """Initializes an authenticated Binance USDM ccxt client in testnet mode only."""
    try:
        if not settings.ENABLE_TESTNET:
            raise RuntimeError("ENABLE_TESTNET must be true. Real-money mode is disabled in this build.")

        exchange = ccxt.binanceusdm(
            {
                "apiKey": settings.BINANCE_API_KEY,
                "secret": settings.BINANCE_SECRET_KEY,
                "enableRateLimit": True,
            }
        )
        exchange.set_sandbox_mode(True)
        logger.info("TESTNET MODE ENABLED for Binance Futures execution.")
        return exchange
    except Exception as exc:
        logger.critical("Failed to initialize exchange: %s", exc)
        raise
