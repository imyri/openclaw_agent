import ccxt
import logging
from core.config import settings

logger = logging.getLogger("openclaw.exchange")

def get_exchange_instance():
    """Initializes and returns the authenticated ccxt Binance instance."""
    try:
        exchange = ccxt.binanceusdm({
            'apiKey': settings.BINANCE_API_KEY,
            'secret': settings.BINANCE_SECRET_KEY,
            'enableRateLimit': True,
        })
        exchange.set_sandbox_mode(True)
        # Optional: Test connection in prod
        # exchange.check_required_credentials()
        return exchange
    except Exception as e:
        logger.critical(f"Failed to initialize exchange: {e}")
        raise