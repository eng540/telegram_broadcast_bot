from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # المفاتيح الأساسية
    BOT_TOKEN: str
    ADMIN_ID: int
    MASTER_SOURCE_ID: int
    DATABASE_URL: str
    REDIS_URL: str
    
    # ✅ مفتاح Fal.ai (إلزامي الآن)
    FAL_KEY: str

    # الهوية
    CHANNEL_NAME: str = "روائع من الأدب العربي"
    CHANNEL_HANDLE: str = "@Rwaea3"
    CHANNEL_LINK: str = "https://t.me/Rwaea3"

    class Config:
        env_file = ".env"

settings = Settings()