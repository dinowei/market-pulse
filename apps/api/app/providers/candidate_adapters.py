from dataclasses import dataclass
from typing import Any, Callable

from app.providers.adapters import ProviderNotConfigured
from app.providers.models import ProviderDatasetRef, ProviderError


@dataclass(frozen=True)
class ProviderHttpResponse:
    status_code: int
    payload: Any


class ExternalProviderAdapter:
    def __init__(
        self,
        dataset: ProviderDatasetRef,
        token: str | None,
        transport: Callable[..., ProviderHttpResponse] | None = None,
        normalizer: Callable[[dict[str, Any], str, str, str], Any] | None = None,
    ) -> None:
        self.dataset = dataset
        self.token = token
        self.transport = transport
        self.normalizer = normalizer

    def ensure_configured(self) -> None:
        if not self.token or not self.transport:
            raise ProviderNotConfigured(self.name)

    def raise_for_status(self, response: ProviderHttpResponse, request_id: str) -> None:
        if response.status_code in (401, 403):
            raise ProviderError(
                "PROVIDER_UNAUTHORIZED", f"{self.name} authorization failed ({request_id})"
            )
        if response.status_code == 429:
            raise ProviderError(
                "PROVIDER_RATE_LIMIT", f"{self.name} rate limit ({request_id})", retryable=True
            )
        if response.status_code >= 500:
            raise ProviderError(
                "PROVIDER_UNAVAILABLE", f"{self.name} unavailable ({request_id})", retryable=True
            )
        if response.status_code >= 400:
            raise ProviderError("PROVIDER_ERROR", f"{self.name} request failed ({request_id})")

    def _request_payload(self, request_id: str, **params: Any) -> dict[str, Any]:
        self.ensure_configured()
        try:
            response = self.transport(**params)  # type: ignore[misc]
        except TimeoutError as exc:
            raise ProviderError(
                "PROVIDER_TIMEOUT", f"{self.name} timed out ({request_id})", retryable=True
            ) from exc
        self.raise_for_status(response, request_id)
        if not isinstance(response.payload, dict):
            raise ProviderError(
                "PROVIDER_PAYLOAD_INVALID", f"{self.name} payload invalid ({request_id})"
            )
        return response.payload

    def latest_quote(self, canonical_id: str) -> Any:
        if self.normalizer is None:
            raise ProviderNotConfigured(f"{self.name} normalizer not configured")
        payload = self._request_payload(canonical_id, symbol=canonical_id)
        return self.normalizer(payload, canonical_id, self.name, self.dataset.dataset)


class BrapiAdapter(ExternalProviderAdapter):
    name = "brapi"


class HgBrasilAdapter(ExternalProviderAdapter):
    name = "hg_brasil"


class TwelveDataAdapter(ExternalProviderAdapter):
    name = "twelve_data"


class AlphaVantageAdapter(ExternalProviderAdapter):
    name = "alpha_vantage"


class OpenExchangeRatesAdapter(ExternalProviderAdapter):
    name = "open_exchange_rates"


class MassiveAdapter(ExternalProviderAdapter):
    name = "massive"


class B3DevelopersAdapter(ExternalProviderAdapter):
    name = "b3_developers"
