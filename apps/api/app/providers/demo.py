from datetime import datetime, timezone
from decimal import Decimal

from app.providers.models import (
    DataLevel,
    Freshness,
    ProviderCapability,
    ProviderProvenance,
    ProviderResult,
)


class DemoProvider:
    name = "demo"
    capabilities = frozenset({ProviderCapability.LATEST_QUOTE})

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
                    "Demonstração local; não representa cotação real.",
                    f"Instrumento demonstrativo: {instrument_id}.",
                ),
            ),
        )
