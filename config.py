import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App Config
    APP_NAME: str = "AI Sales Lead Engine"
    DEBUG: bool = True
    
    # DB Config
    DATABASE_URL: str = "sqlite+aiosqlite:///./ai_sales.db"
    
    # AI Engine
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    VOICE_ENABLED: bool = True
    WHISPER_ENABLED: bool = True
    VISION_ENABLED: bool = True
    
    # Green API (WhatsApp)
    GREEN_API_ID_INSTANCE: str = os.getenv("GREEN_API_ID_INSTANCE", "")
    GREEN_API_API_TOKEN_INSTANCE: str = os.getenv("GREEN_API_API_TOKEN_INSTANCE", "")
    GREEN_API_HOST: str = os.getenv("GREEN_API_HOST", "https://api.green-api.com")
    
    # AlfaCRM (s20.online) Integration
    ALFA_SUBDOMAIN: str = os.getenv("ALFA_SUBDOMAIN", "shkolago")
    ALFA_EMAIL: str = os.getenv("ALFA_EMAIL", "schoolgoalmaty@gmail.com")
    ALFA_API_KEY: str = os.getenv("ALFA_API_KEY", "95a954c1-33e5-11f1-a996-3cecefbdd1ae")
    ALFA_APP_KEY: str = os.getenv("ALFA_APP_KEY", "325702e0f2a21a95b6df99e47dc82d02")
    ALFA_BASE_URL: str = os.getenv("ALFA_BASE_URL", "https://shkolago.s20.online")
    
    class Config:
        env_file = ".env"
        extra = "allow"

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """Converts postgres:// to postgresql+asyncpg:// for SQLAlchemy."""
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif "sqlite" in url and "aiosqlite" not in url:
            url = url.replace("sqlite:///", "sqlite+aiosqlite:///./")
        url = url.split("?")[0] if "sslmode" in url else url
        return url

settings = Settings()
