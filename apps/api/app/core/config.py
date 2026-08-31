from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MARKET_PULSE_",
        env_file=".env",
        extra="ignore",
    )

    environment: str = "local"
    api_version: str = "0.1.0"
    database_url: str = "postgresql://market_pulse:market_pulse_local_only@127.0.0.1:5432/market_pulse"
    redis_url: str = "redis://127.0.0.1:6379/0"
    database_timeout_seconds: float = 2.0
    cache_timeout_seconds: float = 1.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
