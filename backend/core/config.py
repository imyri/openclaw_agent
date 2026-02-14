from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Binance Keys
    BINANCE_API_KEY: str
    BINANCE_SECRET_KEY: str
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHAT_ID: str
    
    # Database
    DATABASE_URL: str
    
    # LLM
    OLLAMA_BASE_URL: str = "http://ollama-brain:11434"
    OLLAMA_MODEL: str = "deepseek-r1:7b"
    
    # Risk
    MAX_DAILY_DRAWDOWN_R: float = 2.0
    RISK_PER_TRADE_PERCENT: float = 0.01

    class Config:
        env_file = ".env"

settings = Settings()