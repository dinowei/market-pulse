from typing import Any

from app.providers.licensing import DatasetAccessRequest, LicenseDecision, LicenseService
from app.providers.models import DataLevel, ProviderCapability, ProviderDatasetRef, ProviderError


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
        purpose = kwargs.pop("purpose", None)
        modality = kwargs.pop("modality", None)
        environment = kwargs.pop("environment", None)
        data_level = kwargs.pop("data_level", None)
        if any(value is not None for value in (purpose, modality, environment, data_level)):
            decision = self._licensing.decide_access(
                DatasetAccessRequest(
                    dataset=dataset,
                    capability=capability,
                    purpose=purpose or "public_api",
                    modality=modality or "api",
                    environment=environment or "production",
                    data_level=data_level or DataLevel.DELAYED,
                )
            )
            allowed = decision.allowed
        else:
            allowed = self._licensing.decide(dataset) is LicenseDecision.ALLOW
        if not allowed:
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

    def request_with_fallback(
        self,
        capability: ProviderCapability,
        datasets: list[ProviderDatasetRef],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Try only explicitly public-approved datasets, failing closed otherwise."""
        last_error: Exception | None = None
        for dataset in datasets:
            if self._licensing.decide(dataset) is not LicenseDecision.ALLOW:
                continue
            try:
                return self.request(capability, dataset, *args, **kwargs)
            except (ProviderError, LookupError) as exc:
                last_error = exc
        if last_error:
            raise ProviderError(
                "PROVIDER_UNAVAILABLE", "No approved provider is available"
            ) from last_error
        raise PermissionError("No provider dataset is approved for public use")
