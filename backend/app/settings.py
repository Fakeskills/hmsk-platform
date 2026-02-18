from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://hmsk:changeme@localhost:5432/hmsk"
    DATABASE_SYNC_URL: str = "postgresql+psycopg2://hmsk:changeme@localhost:5432/hmsk"

    JWT_SECRET: str = "CHANGE_ME_32_CHARS_MINIMUM_SECRET"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    APP_ENV: str = "development"
    APP_DEBUG: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
