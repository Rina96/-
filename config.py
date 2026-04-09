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
    
    # Green API (WhatsApp)
    GREEN_API_ID_INSTANCE: str = os.getenv("GREEN_API_ID_INSTANCE", "")
    GREEN_API_API_TOKEN_INSTANCE: str = os.getenv("GREEN_API_API_TOKEN_INSTANCE", "")
    GREEN_API_HOST: str = os.getenv("GREEN_API_HOST", "https://api.green-api.com")
    
    # amoCRM Integration
    AMOCRM_SUBDOMAIN: str = os.getenv("AMOCRM_SUBDOMAIN", "")
    AMOCRM_CLIENT_ID: str = os.getenv("AMOCRM_CLIENT_ID", "")
    AMOCRM_CLIENT_SECRET: str = os.getenv("AMOCRM_CLIENT_SECRET", "")
    AMOCRM_REDIRECT_URI: str = os.getenv("AMOCRM_REDIRECT_URI", "")
    
    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
