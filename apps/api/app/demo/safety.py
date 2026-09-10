"""Fail-closed configuration checks, not a substitute for live database identity checks.

No connection is opened here. Seed/reset additionally verify live database identity,
migration state and exclusive DEMO ownership before writing.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlsplit

DEMO_DATABASE = "market_pulse_demo"
LOCAL_DEMO_CONFIRMATION = "market-pulse/local-demo/v1"
_ENVIRONMENTS = {"development": "local", "local": "local", "test": "test"}
_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_LIBPQ_OVERRIDES = (
    "PGHOST",
    "PGHOSTADDR",
    "PGPORT",
    "PGDATABASE",
    "PGUSER",
    "PGPASSWORD",
    "PGSERVICE",
    "PGSERVICEFILE",
    "PGPASSFILE",
    "PGOPTIONS",
)


class DemoSafetyError(ValueError):
    """Safe error that never includes the rejected configuration or credentials."""


@dataclass(frozen=True)
class DemoTarget:
    environment: str
    host: str
    port: int
    database: str = DEMO_DATABASE


def validate_demo_target(environment: Mapping[str, str], *, confirmation: str) -> DemoTarget:
    """Require every explicit barrier; never fall back to the primary connection.

    APP_ENV and the application's MARKET_PULSE_ENVIRONMENT must agree. URLs with
    query/fragment/connection overrides are rejected, including libpq host/service
    overrides. Resolving a local host to the actual server remains an integrated gate.
    """
    app_env = _ENVIRONMENTS.get(environment.get("APP_ENV", ""))
    runtime_env = environment.get("MARKET_PULSE_ENVIRONMENT")
    if (
        app_env is None
        or runtime_env not in {"local", "test"}
        or app_env != runtime_env
        or environment.get("MARKET_PULSE_DEMO_ENABLED") != "true"
        or confirmation != LOCAL_DEMO_CONFIRMATION
        or any(environment.get(key) for key in _LIBPQ_OVERRIDES)
    ):
        raise DemoSafetyError("Explicit, consistent local DEMO authorization is required")

    raw_url = environment.get("MARKET_PULSE_DEMO_DATABASE_URL", "")
    if not raw_url or any(char.isspace() for char in raw_url) or "?" in raw_url or "#" in raw_url:
        raise DemoSafetyError("An unambiguous dedicated local DEMO target is required")
    try:
        url = urlsplit(raw_url)
        port = 5432 if url.port is None else url.port
        valid = (
            url.scheme == "postgresql"
            and url.hostname in _LOCAL_HOSTS
            and bool(url.username)
            and url.path == f"/{DEMO_DATABASE}"
            and 1 <= port <= 65535
        )
    except ValueError:
        raise DemoSafetyError("Invalid dedicated local DEMO target") from None
    if not valid:
        raise DemoSafetyError("Only the explicitly authorized local DEMO database is allowed")
    return DemoTarget(environment=runtime_env, host=url.hostname, port=port)
