from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Sequence

from app.providers.models import (
    DataLevel,
    Freshness,
    ProviderCapability,
    ProviderProvenance,
    ProviderResult,
)


class DemoProvider:
    name = "demo"
    capabilities = frozenset(ProviderCapability)

    def latest_quote(self, instrument_id: str) -> ProviderResult[Decimal]:
        now = datetime.now(timezone.utc)
        return ProviderResult(
            value=Decimal("42.42"),
            provenance=ProviderProvenance(
                provider=self.name,
                dataset="demo-quotes",
                source="local-demo",
                source_timestamp=now,
                collected_at=now,
                data_level=DataLevel.DEMO,
                freshness=Freshness.STALE,
                currency="BRL",
                limitations=(
                    "Demonstração sintética; não representa cotação real.",
                    f"Instrumento demonstrativo: {instrument_id}.",
                ),
            ),
        )

    def _provenance(self, dataset: str, currency: str = "BRL") -> ProviderProvenance:
        now = datetime.now(timezone.utc)
        return ProviderProvenance(
            provider=self.name,
            dataset=dataset,
            source="local-demo",
            source_timestamp=now,
            collected_at=now,
            data_level=DataLevel.DEMO,
            freshness=Freshness.STALE,
            currency=currency,
            limitations=("Demonstração sintética; não representa mercado real.",),
        )

    def historical_bars(
        self, instrument_id: str, start: datetime, end: datetime
    ) -> ProviderResult[Sequence[dict[str, object]]]:
        del instrument_id
        points = [
            {
                "timestamp": start + timedelta(days=i),
                "open": Decimal("40"),
                "high": Decimal("41"),
                "low": Decimal("39"),
                "close": Decimal("40.5"),
                "volume": Decimal("1000"),
            }
            for i in range(max(1, min(3, (end - start).days + 1)))
        ]
        return ProviderResult(value=points, provenance=self._provenance("demo-history"))

    def fx_rate(self, base: str, quote: str) -> ProviderResult[Decimal]:
        del base, quote
        return ProviderResult(value=Decimal("5.00"), provenance=self._provenance("demo-fx", "BRL"))

    def instrument_metadata(self, instrument_id: str) -> ProviderResult[dict[str, str]]:
        return ProviderResult(
            value={"canonical_id": instrument_id, "symbol": "DEMO", "name": "Demo instrument"},
            provenance=self._provenance("demo-metadata"),
        )

    def dividends(self, instrument_id: str) -> ProviderResult[Sequence[dict[str, object]]]:
        del instrument_id
        return ProviderResult(
            value=(
                {
                    "action_type": "CASH_DIVIDEND",
                    "external_id": "demo-dividend-001",
                    "ex_date": "2026-01-10",
                    "payment_date": "2026-01-20",
                    "amount": Decimal("0.10"),
                    "currency": "BRL",
                },
            ),
            provenance=self._provenance("demo-dividends"),
        )

    def corporate_actions(self, instrument_id: str) -> ProviderResult[Sequence[dict[str, object]]]:
        del instrument_id
        return ProviderResult(
            value=(
                {
                    "action_type": "SPLIT",
                    "external_id": "demo-split-001",
                    "effective_date": "2026-01-15",
                    "split_ratio_from": Decimal("1"),
                    "split_ratio_to": Decimal("2"),
                },
            ),
            provenance=self._provenance("demo-corporate-actions"),
        )
