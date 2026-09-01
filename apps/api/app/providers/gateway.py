from typing import Any

from app.providers.licensing import LicenseDecision, LicenseService
from app.providers.models import ProviderCapability, ProviderDatasetRef, ProviderError


class ProviderGateway:
    def __init__(self, providers: list[Any], licensing: LicenseService | None = None) -> None:
        self._providers = providers
        self._licensing = licensing or LicenseService()

    def capabilities(self) -> dict[str, tuple[ProviderCapability, ...]]:
        return {
            getattr(provider, "name", provider.__class__.__name__): tuple(provider.capabilities)
            for provider in self._providers
        }

    def request(
        self, capability: ProviderCapability, dataset: ProviderDatasetRef, *args: Any, **kwargs: Any
    ) -> Any:
        if self._licensing.decide(dataset) is not LicenseDecision.ALLOW:
            raise PermissionError("Provider dataset is not approved for public use")
        for provider in self._providers:
            if capability not in provider.capabilities:
                continue
            method = getattr(provider, capability.value, None)
            if method is None:
                continue
            try:
                return method(*args, **kwargs)
            except TimeoutError as exc:
                raise ProviderError(
                    "PROVIDER_TIMEOUT", "Provider timed out", retryable=True
                ) from exc
            except Exception as exc:
                raise ProviderError("PROVIDER_UNAVAILABLE", "Provider unavailable") from exc
        raise LookupError(f"No provider supports capability {capability.value}")
