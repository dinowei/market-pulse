from datetime import datetime
from decimal import Decimal
from typing import Protocol, Sequence

from app.providers.models import ProviderCapability, ProviderResult


class LatestQuoteProvider(Protocol):
    capabilities: frozenset[ProviderCapability]

    def latest_quote(self, instrument_id: str) -> ProviderResult[Decimal]: ...


class HistoricalBarsProvider(Protocol):
    capabilities: frozenset[ProviderCapability]

    def historical_bars(
        self, instrument_id: str, start: datetime, end: datetime
    ) -> ProviderResult[Sequence[tuple[datetime, Decimal]]]: ...


class FxRatesProvider(Protocol):
    capabilities: frozenset[ProviderCapability]

    def fx_rate(self, base: str, quote: str) -> ProviderResult[Decimal]: ...


class InstrumentMetadataProvider(Protocol):
    capabilities: frozenset[ProviderCapability]

    def instrument_metadata(self, instrument_id: str) -> ProviderResult[dict[str, str]]: ...


class DividendsProvider(Protocol):
    capabilities: frozenset[ProviderCapability]

    def dividends(self, instrument_id: str) -> ProviderResult[Sequence[dict[str, object]]]: ...


class CorporateActionsProvider(Protocol):
    capabilities: frozenset[ProviderCapability]

    def corporate_actions(
        self, instrument_id: str
    ) -> ProviderResult[Sequence[dict[str, object]]]: ...
