from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Exchange
    BINANCE_API_KEY: str = ""
    BINANCE_SECRET_KEY: str = ""
    ENABLE_TESTNET: bool = True
    EXECUTE_ORDERS: bool = True
    TRADING_SYMBOL: str = "BTC/USDT"
    TRADING_TIMEFRAME: str = "5m"
    MAX_CANDLES: int = 100

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    TELEGRAM_ALERTS_ENABLED: bool = True
    TELEGRAM_ALERTS_INCLUDE_WAIT: bool = False

    # Database
    DATABASE_URL: str = "sqlite:///./openclaw_state.db"

    # LLM
    OLLAMA_BASE_URL: str = "http://ollama-brain:11434"
    OLLAMA_MODEL: str = "deepseek-r1:7b"
    OLLAMA_TIMEOUT_SECS: int = 30

    # Internal API bridge
    INTERNAL_API_TOKEN: str = "change-me"
    INTERNAL_API_URL: str = "http://backend:8000/internal/ai-event"

    # Risk
    MAX_DAILY_DRAWDOWN_R: float = 2.0
    RISK_PER_TRADE_PERCENT: float = 0.01
    MAX_TRADE_DURATION_MINS: int = 30
    DEFAULT_ACCOUNT_BALANCE: float = 10000.0
    MIN_RR_RATIO: float = 3.0

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
