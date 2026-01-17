from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN: str
    MASTER_SOURCE_ID: int
    REDIS_URL: str
    DATABASE_URL: str

    class Config:
        env_file = ".env"

settings = Settings()
