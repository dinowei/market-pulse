"""Provider abstractions, licensing gates and safe local adapters."""

from app.providers.gateway import ProviderGateway
from app.providers.licensing import LicenseDecision, LicenseService

__all__ = ["LicenseDecision", "LicenseService", "ProviderGateway"]
