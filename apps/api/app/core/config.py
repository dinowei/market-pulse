import json
from functools import lru_cache
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

PROTECTED_ENVIRONMENTS = frozenset({"production", "staging"})
ALLOWED_PROTECTED_SAMESITE = frozenset({"lax", "strict"})


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
    # NoDecode: the env value is parsed below, so both formats documented in .env.example
    # (JSON array or comma-separated) work instead of failing the boot on non-JSON input.
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    retention_days: int = 90
    registration_enabled: bool | None = None
    # H-23 (ADR-020): proxies in front of the API that append to X-Forwarded-For. 0 ignores
    # the header (the socket peer is the client); only set it for a measured, exclusive chain.
    trusted_proxy_hops: Annotated[int, Field(ge=0, le=5)] = 0
    # ADR-027: providers the owner approved for the private staging, comma-separated registry
    # ids. Empty keeps real data off. Refused in production, with DEMO or with open sign-up.
    real_data_providers: Annotated[tuple[str, ...], NoDecode] = ()

    @field_validator("real_data_providers", mode="before")
    @classmethod
    def _parse_provider_ids(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.split(",")
        if isinstance(value, (list, tuple)):
            ids = (str(item).strip().lower() for item in value)
            return tuple(dict.fromkeys(item for item in ids if item))
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            text = value.strip()
            value = json.loads(text) if text.startswith("[") else text.split(",")
        if isinstance(value, list):
            # Browsers send Origin without a trailing slash; keep the allowlist comparable.
            return [str(item).strip().rstrip("/") for item in value if str(item).strip()]
        return value

    @field_validator("registration_enabled", mode="before")
    @classmethod
    def _blank_registration_means_default(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value


def is_protected_environment(settings: Settings) -> bool:
    return settings.environment.lower() in PROTECTED_ENVIRONMENTS


def registration_open(settings: Settings) -> bool:
    """Self-service registration fails closed in production/staging unless explicitly enabled."""
    if settings.registration_enabled is not None:
        return settings.registration_enabled
    return not is_protected_environment(settings)


def validate_real_data_settings(settings: Settings) -> None:
    """ADR-027: real data only in a private staging, never mixed with DEMO."""

    if not settings.real_data_providers:
        return
    if settings.environment.lower() == "production":
        raise ProductionConfigurationError(
            "Forbidden configuration: MARKET_PULSE_REAL_DATA_PROVIDERS is not allowed in "
            "production before a PUBLIC_APPROVED license decision"
        )
    if settings.demo_enabled:
        raise ProductionConfigurationError(
            "Forbidden configuration: MARKET_PULSE_REAL_DATA_PROVIDERS and "
            "MARKET_PULSE_DEMO_ENABLED cannot be combined (DEMO and real data never mix)"
        )
    if registration_open(settings):
        raise ProductionConfigurationError(
            "Forbidden configuration: MARKET_PULSE_REAL_DATA_PROVIDERS requires registration "
            "to stay closed (private use by the owner's account)"
        )
    from app.providers.registry import owner_use_blockers

    blockers = owner_use_blockers(settings.real_data_providers)
    if blockers:
        raise ProductionConfigurationError(
            "Invalid setting: MARKET_PULSE_REAL_DATA_PROVIDERS names providers that cannot be "
            f"used: {', '.join(blockers)}"
        )


def validate_production_settings(settings: Settings) -> None:
    """Validate that production and staging environments have all mandatory configuration.

    In local/development/test environments, default local values are permitted.
    In production and staging:
      - MARKET_PULSE_DATABASE_URL must be a valid postgres URL without default local password.
      - MARKET_PULSE_REDIS_URL must be a valid redis URL.
      - MARKET_PULSE_INTERNAL_REFRESH_SECRET must be set and >= 16 characters.
      - MARKET_PULSE_CORS_ORIGINS must not contain wildcards, empty values, or localhost.
      - MARKET_PULSE_DEMO_ENABLED must be False.
      - MARKET_PULSE_AUTH_COOKIE_SAMESITE must be lax or strict (ADR-008: same-origin proxy).
    """
    if not is_protected_environment(settings):
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

    # 6. Session cookie must stay first-party
    if settings.auth_cookie_samesite.lower() not in ALLOWED_PROTECTED_SAMESITE:
        raise ProductionConfigurationError(
            "Insecure setting: MARKET_PULSE_AUTH_COOKIE_SAMESITE must be lax or strict "
            "in production/staging"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
