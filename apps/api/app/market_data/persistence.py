from dataclasses import dataclass, field

from app.market_data.normalization import MarketBar


@dataclass
class PriceBarStore:
    items: dict[tuple[str, str, str, object, str], MarketBar] = field(default_factory=dict)
    quarantine: list[MarketBar] = field(default_factory=list)

    def upsert(self, bar: MarketBar, *, provider: str, dataset: str) -> str:
        key = (bar.canonical_id, provider, dataset, bar.timestamp, bar.adjustment_type.value)
        current = self.items.get(key)
        if current is None:
            self.items[key] = bar
            return "inserted"
        if current == bar:
            return "unchanged"
        self.quarantine.append(bar)
        return "quarantined"

    def upsert_batch(self, bars: list[MarketBar], *, provider: str, dataset: str) -> list[str]:
        return [self.upsert(bar, provider=provider, dataset=dataset) for bar in bars]
