"""Basic P0 heatmap (Day 37, ADR-019).

Each tile is the same PublicQuote the quote endpoint returns, so price, change, DataLevel,
Freshness, provider, dataset and timestamps keep one source of truth. Nothing is derived
here: a tile without a previous close keeps a null change, and an instrument without an
approved dataset stays UNAVAILABLE.
"""

from app.contracts import HeatmapGroup, HeatmapResponse
from app.instruments.catalog import CatalogStatus, get_catalog
from app.market_data.public_market_data import public_quote

# Tradable instruments only; indices are references (benchmarks), not heatmap members.
HEATMAP_INSTRUMENT_TYPES = ("EQUITY", "ETF", "FII", "BDR")

HEATMAP_LIMITATIONS = (
    "Setor indisponível: nenhum dataset aprovado traz classificação setorial; os blocos "
    "são agrupados por tipo de instrumento.",
    "Valor de mercado indisponível: todos os blocos têm a mesma área.",
    "A cor indica só a direção da variação contra o fechamento anterior (alta, queda ou "
    "estável); a intensidade é lida no valor, não na cor.",
)


def market_heatmap(request_id: str) -> HeatmapResponse:
    entries = [
        entry
        for entry in get_catalog()
        if entry.instrument_type.upper() in HEATMAP_INSTRUMENT_TYPES
        and entry.catalog_status is not CatalogStatus.OUT_OF_SCOPE
    ]
    groups = [
        HeatmapGroup(
            group=kind,
            tiles=[
                public_quote(entry.canonical_id, request_id)
                for entry in entries
                if entry.instrument_type.upper() == kind
            ],
        )
        for kind in HEATMAP_INSTRUMENT_TYPES
    ]
    return HeatmapResponse(
        groups=[group for group in groups if group.tiles],
        limitations=HEATMAP_LIMITATIONS,
        request_id=request_id,
    )
