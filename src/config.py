from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN: str
    MASTER_SOURCE_ID: int
    REDIS_URL: str
    DATABASE_URL: str
    ALLOWED_LINK_SUBSTRING: str
    ADMIN_ID: int = 0  # اختياري

    class Config:
        env_file = ".env"

settings = Settings()