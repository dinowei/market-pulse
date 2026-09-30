from functools import lru_cache
from urllib.parse import urlsplit

from pydantic_settings import BaseSettings, SettingsConfigDict


class ProductionConfigurationError(RuntimeError):
    """Raised when required production/staging configuration is missing or malformed."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MARKET_PULSE_",
        env_file=".env",
        extra="ignore",
    )

    environment: str = "local"
    api_version: str = "0.1.0"
    database_url: str = (
        "postgresql://market_pulse:market_pulse_local_only@127.0.0.1:5432/market_pulse"
    )
    redis_url: str = "redis://127.0.0.1:6379/0"
    demo_enabled: bool = False
    demo_database_url: str | None = None
    database_timeout_seconds: float = 2.0
    cache_timeout_seconds: float = 1.0
    internal_refresh_secret: str | None = None
    refresh_max_items: int = 20
    refresh_item_timeout_seconds: float = 5.0
    refresh_total_timeout_seconds: float = 30.0
    auth_cookie_name: str = "market_pulse_session"
    auth_session_ttl_seconds: int = 60 * 60 * 24 * 7
    auth_cookie_secure: bool = False
    auth_cookie_samesite: str = "lax"
    auth_rate_limit_max_attempts: int = 5
    auth_rate_limit_window_seconds: int = 60
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    retention_days: int = 90


def validate_production_settings(settings: Settings) -> None:
    """Validate that production and staging environments have all mandatory configuration.

    In local/development/test environments, default local values are permitted.
    In production and staging:
      - MARKET_PULSE_DATABASE_URL must be a valid postgres URL without default local password.
      - MARKET_PULSE_REDIS_URL must be a valid redis URL.
      - MARKET_PULSE_INTERNAL_REFRESH_SECRET must be set and >= 16 characters.
      - MARKET_PULSE_CORS_ORIGINS must not contain wildcards, empty values, or localhost.
      - MARKET_PULSE_DEMO_ENABLED must be False.
    """
    env = settings.environment.lower()
    if env not in {"production", "staging"}:
        return

    # 1. Demo mode must be disabled
    if settings.demo_enabled:
        raise ProductionConfigurationError(
            "Forbidden configuration: MARKET_PULSE_DEMO_ENABLED must be false in production/staging"
        )

    # 2. Database URL validation
    if not settings.database_url:
        raise ProductionConfigurationError(
            "Missing required setting: MARKET_PULSE_DATABASE_URL is required in production/staging"
        )
    if "market_pulse_local_only" in settings.database_url:
        raise ProductionConfigurationError(
            "Insecure setting: MARKET_PULSE_DATABASE_URL cannot use default local credentials "
            "in production/staging"
        )
    try:
        db_split = urlsplit(settings.database_url)
        if db_split.scheme not in {"postgresql", "postgres"} or not db_split.hostname:
            raise ValueError
    except Exception:
        raise ProductionConfigurationError(
            "Malformed setting: MARKET_PULSE_DATABASE_URL must be a valid PostgreSQL connection URL"
        )

    # 3. Redis URL validation
    if not settings.redis_url:
        raise ProductionConfigurationError(
            "Missing required setting: MARKET_PULSE_REDIS_URL is required in production/staging"
        )
    try:
        redis_split = urlsplit(settings.redis_url)
        if redis_split.scheme not in {"redis", "rediss"} or not redis_split.hostname:
            raise ValueError
    except Exception:
        raise ProductionConfigurationError(
            "Malformed setting: MARKET_PULSE_REDIS_URL must be a valid Redis connection URL"
        )

    # 4. Internal refresh secret
    if not settings.internal_refresh_secret or len(settings.internal_refresh_secret) < 16:
        raise ProductionConfigurationError(
            "Missing or insecure setting: MARKET_PULSE_INTERNAL_REFRESH_SECRET must be set and "
            "contain at least 16 characters in production/staging"
        )

    # 5. CORS origins
    if not settings.cors_origins:
        raise ProductionConfigurationError(
            "Missing required setting: MARKET_PULSE_CORS_ORIGINS must specify allowed origins "
            "in production/staging"
        )
    for origin in settings.cors_origins:
        if origin == "*":
            raise ProductionConfigurationError(
                "Insecure setting: MARKET_PULSE_CORS_ORIGINS cannot contain wildcard (*) "
                "with credentials in production/staging"
            )
        if "localhost" in origin or "127.0.0.1" in origin:
            raise ProductionConfigurationError(
                f"Insecure setting: MARKET_PULSE_CORS_ORIGINS cannot reference "
                f"local host ({origin}) in production/staging"
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
