from dataclasses import dataclass

from app.providers.models import ProviderCapability, ProviderError


class ProviderNotConfigured(ProviderError):
    def __init__(self, provider: str) -> None:
        super().__init__("PROVIDER_NOT_CONFIGURED", f"Provider {provider} is not configured")


@dataclass(frozen=True)
class CandidateAdapter:
    name: str
    credential_env: str
    capabilities: frozenset[ProviderCapability]
    enabled: bool = False

    def ensure_configured(self) -> None:
        if not self.enabled:
            raise ProviderNotConfigured(self.name)


CANDIDATE_ADAPTERS = (
    CandidateAdapter(
        "brapi", "BRAPI_API_TOKEN",
        frozenset({ProviderCapability.LATEST_QUOTE, ProviderCapability.HISTORICAL_BARS,
                   ProviderCapability.DIVIDENDS}),
    ),
    CandidateAdapter(
        "hg_brasil", "HG_BRASIL_API_KEY",
        frozenset({ProviderCapability.LATEST_QUOTE, ProviderCapability.FX_RATES}),
    ),
    CandidateAdapter(
        "twelve_data", "TWELVE_DATA_API_KEY",
        frozenset({ProviderCapability.LATEST_QUOTE, ProviderCapability.HISTORICAL_BARS,
                   ProviderCapability.FX_RATES}),
    ),
    CandidateAdapter(
        "alpha_vantage", "ALPHA_VANTAGE_API_KEY",
        frozenset({ProviderCapability.LATEST_QUOTE, ProviderCapability.HISTORICAL_BARS,
                   ProviderCapability.FX_RATES}),
    ),
    CandidateAdapter(
        "open_exchange_rates", "OPEN_EXCHANGE_RATES_APP_ID",
        frozenset({ProviderCapability.FX_RATES}),
    ),
    CandidateAdapter(
        "massive", "MASSIVE_API_KEY",
        frozenset({ProviderCapability.LATEST_QUOTE, ProviderCapability.HISTORICAL_BARS,
                   ProviderCapability.DIVIDENDS, ProviderCapability.CORPORATE_ACTIONS}),
    ),
    CandidateAdapter(
        "b3_developers", "B3_DEVELOPERS_CLIENT_ID",
        frozenset({ProviderCapability.INSTRUMENT_METADATA}),
    ),
)
