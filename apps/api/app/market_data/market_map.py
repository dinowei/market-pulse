"""A market as a treemap (ADR-032): every tile is a real asset of a bulk provider answer.

B3 comes from one brapi list call, with the sector and market value the source declares. The
US comes from one Massive daily call; that call has neither, so the sector is this project's
own classification (it says so) and the size is the value traded in the session. Nothing is
estimated: a tile without a known change keeps it null and a market without data stays empty
with its reason.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from decimal import Decimal

from app.contracts import (
    DataLevel,
    Freshness,
    MarketMapResponse,
    MarketMapSector,
    MarketMapTile,
    MarketMover,
    MarketMoversResponse,
)
from app.instruments.catalog import get_catalog
from app.market_data import live_data
from app.market_data.public_market_data import public_quote

BR_SECTORS = {
    "Retail Trade": "Varejo",
    "Energy Minerals": "Petróleo, Gás e Energia",
    "Health Services": "Serviços de Saúde",
    "Utilities": "Utilidade Pública",
    "Finance": "Financeiro",
    "Consumer Services": "Serviços ao Consumidor",
    "Consumer Non-Durables": "Consumo não Durável",
    "Non-Energy Minerals": "Mineração e Metais",
    "Commercial Services": "Serviços Comerciais",
    "Distribution Services": "Distribuição",
    "Transportation": "Transporte",
    "Technology Services": "Serviços de Tecnologia",
    "Process Industries": "Indústria de Base",
    "Communications": "Comunicações",
    "Producer Manufacturing": "Bens Industriais",
    "Miscellaneous": "Diversos",
    "Electronic Technology": "Tecnologia Eletrônica",
    "Industrial Services": "Serviços Industriais",
    "Health Technology": "Tecnologia em Saúde",
    "Consumer Durables": "Consumo Durável",
}

US_UNIVERSE: dict[str, tuple[tuple[str, str], ...]] = {
    "Tecnologia": (
        ("NVDA", "NVIDIA"),
        ("AAPL", "Apple"),
        ("MSFT", "Microsoft"),
        ("AVGO", "Broadcom"),
        ("ORCL", "Oracle"),
        ("CRM", "Salesforce"),
        ("AMD", "AMD"),
        ("INTC", "Intel"),
        ("ADBE", "Adobe"),
        ("QCOM", "Qualcomm"),
        ("TXN", "Texas Instruments"),
        ("IBM", "IBM"),
        ("MU", "Micron"),
    ),
    "Comunicação": (
        ("GOOGL", "Alphabet"),
        ("META", "Meta"),
        ("NFLX", "Netflix"),
        ("DIS", "Disney"),
        ("T", "AT&T"),
        ("VZ", "Verizon"),
        ("CMCSA", "Comcast"),
    ),
    "Consumo Discricionário": (
        ("AMZN", "Amazon"),
        ("TSLA", "Tesla"),
        ("HD", "Home Depot"),
        ("MCD", "McDonald's"),
        ("NKE", "Nike"),
        ("SBUX", "Starbucks"),
        ("LOW", "Lowe's"),
    ),
    "Consumo Básico": (
        ("WMT", "Walmart"),
        ("COST", "Costco"),
        ("PG", "Procter & Gamble"),
        ("KO", "Coca-Cola"),
        ("PEP", "PepsiCo"),
    ),
    "Financeiro": (
        ("JPM", "JPMorgan"),
        ("V", "Visa"),
        ("MA", "Mastercard"),
        ("BAC", "Bank of America"),
        ("WFC", "Wells Fargo"),
        ("GS", "Goldman Sachs"),
        ("MS", "Morgan Stanley"),
        ("AXP", "American Express"),
    ),
    "Saúde": (
        ("LLY", "Eli Lilly"),
        ("UNH", "UnitedHealth"),
        ("JNJ", "Johnson & Johnson"),
        ("ABBV", "AbbVie"),
        ("MRK", "Merck"),
        ("PFE", "Pfizer"),
    ),
    "Energia": (("XOM", "ExxonMobil"), ("CVX", "Chevron"), ("COP", "ConocoPhillips")),
    "Indústria": (
        ("CAT", "Caterpillar"),
        ("BA", "Boeing"),
        ("GE", "GE Aerospace"),
        ("UPS", "UPS"),
        ("HON", "Honeywell"),
    ),
    "Materiais e Serviços Públicos": (("LIN", "Linde"), ("NEE", "NextEra Energy")),
}
live_data.US_MAP_TICKERS[0] = frozenset(
    ticker for group in US_UNIVERSE.values() for ticker, _ in group
)

BR_LIMITATIONS = (
    "Setor, valor de mercado, preço, variação e volume vêm de uma única resposta da brapi; a "
    "lista não traz horário por ativo.",
    "O valor de mercado é o da empresa: ações da mesma empresa (como PETR3 e PETR4) repetem o "
    "mesmo número, por isso a soma das áreas não é o valor da bolsa.",
    "A cor indica a direção e a intensidade da variação do dia; o número fica escrito no bloco "
    "e na tabela. Cotação com atraso.",
    "Conteúdo informativo para estudo; não é recomendação de investimento.",
)
US_LIMITATIONS = (
    "Preços do último pregão fechado (Massive), sem ajuste. Variação contra o pregão anterior.",
    "O tamanho é o valor negociado no pregão (fechamento × volume), não o valor de mercado: a "
    "chamada em lote não traz esse dado.",
    "O setor é uma classificação mantida neste projeto, não uma informação da fonte.",
    "Conteúdo informativo para estudo; não é recomendação de investimento.",
)


def _logo(url: object) -> str | None:
    return url if isinstance(url, str) and url.startswith("https://icons.brapi.dev/") else None


def _catalog_ids() -> dict[str, str]:
    return {entry.symbol: entry.canonical_id for entry in get_catalog()}


def _sectors(grouped: dict[str, list[MarketMapTile]]) -> list[MarketMapSector]:
    ordered = sorted(
        grouped.items(), key=lambda item: sum(tile.size_value for tile in item[1]), reverse=True
    )
    return [
        MarketMapSector(
            sector=name, tiles=sorted(tiles, key=lambda tile: tile.size_value, reverse=True)
        )
        for name, tiles in ordered
    ]


def unavailable_market_map(market: str, request_id: str, reason: str) -> MarketMapResponse:
    return MarketMapResponse(
        market=market,
        sizing="EQUAL",
        sectors=[],
        provider="none",
        dataset="none",
        data_level=DataLevel.DELAYED,
        freshness=Freshness.UNAVAILABLE,
        is_demo=False,
        limitations=["Sem dados para montar este mapa agora."],
        unavailable_reason=reason,
        request_id=request_id,
    )


def _real_br(request_id: str) -> MarketMapResponse:
    snapshot = live_data.br_snapshot()
    if snapshot is None:
        return unavailable_market_map("BR", request_id, "UNAVAILABLE")
    ids = _catalog_ids()
    grouped: dict[str, list[MarketMapTile]] = {}
    rows: Iterable[dict] = snapshot.data["rows"].values()
    for row in rows:
        if row["type"] != "stock" or not row.get("market_cap") or row["symbol"].endswith("F"):
            continue
        sector = BR_SECTORS.get(row.get("sector") or "", "Sem setor declarado")
        cap = Decimal(row["market_cap"])
        grouped.setdefault(sector, []).append(
            MarketMapTile(
                symbol=row["symbol"],
                name=row["name"],
                canonical_id=ids.get(row["symbol"]),
                price=Decimal(row["price"]),
                currency="BRL",
                change_percent=Decimal(row["change_percent"]) if row["change_percent"] else None,
                volume=Decimal(row["volume"]) if row["volume"] else None,
                market_cap=cap,
                size_value=cap,
                logo_url=_logo(row.get("logo")),
            )
        )
    session = snapshot.data.get("session")
    return MarketMapResponse(
        market="BR",
        sizing="MARKET_CAP",
        sectors=_sectors(grouped),
        provider="brapi",
        dataset="brapi.quote.list",
        data_level=DataLevel.DELAYED,
        freshness=snapshot.freshness,
        session_date=session,
        timestamp_collected=snapshot.fetched_at,
        is_demo=False,
        limitations=list(BR_LIMITATIONS),
        request_id=request_id,
    )


def _real_us(request_id: str) -> MarketMapResponse:
    snapshot = live_data._shared_us_snapshot()
    if snapshot is None:
        return unavailable_market_map("US", request_id, "UNAVAILABLE")
    ids = _catalog_ids()
    grouped: dict[str, list[MarketMapTile]] = {}
    for sector, members in US_UNIVERSE.items():
        for ticker, name in members:
            row = snapshot.data["rows"].get(ticker)
            if row is None or not row.get("volume"):
                continue
            close, volume = Decimal(row["close"]), Decimal(row["volume"])
            previous = Decimal(row["previous_close"]) if row.get("previous_close") else None
            grouped.setdefault(sector, []).append(
                MarketMapTile(
                    symbol=ticker,
                    name=name,
                    canonical_id=ids.get(ticker),
                    price=close,
                    currency="USD",
                    change_percent=(close - previous) / previous * 100 if previous else None,
                    volume=volume,
                    size_value=close * volume,
                )
            )
    return MarketMapResponse(
        market="US",
        sizing="TRADED_VALUE",
        sectors=_sectors(grouped),
        provider="massive",
        dataset="massive.aggs.grouped.1day.unadjusted",
        data_level=DataLevel.EOD,
        freshness=snapshot.freshness,
        session_date=snapshot.data.get("session"),
        timestamp_collected=snapshot.fetched_at,
        is_demo=False,
        limitations=list(US_LIMITATIONS),
        request_id=request_id,
    )


def real_market_map(market: str, request_id: str) -> MarketMapResponse:
    return _real_br(request_id) if market == "BR" else _real_us(request_id)


def demo_market_map(market: str, request_id: str) -> MarketMapResponse:
    """Local development only: the synthetic catalog, same area per tile, labeled DEMO."""
    country = "BR" if market == "BR" else "US"
    grouped: dict[str, list[MarketMapTile]] = {}
    for entry in get_catalog():
        if entry.country != country or entry.instrument_type.upper() != "EQUITY":
            continue
        try:
            quote = public_quote(entry.canonical_id, request_id)
        except KeyError:
            continue
        if quote.price is None:
            continue
        grouped.setdefault("Ações (demonstração)", []).append(
            MarketMapTile(
                symbol=quote.symbol,
                name=quote.name,
                canonical_id=quote.canonical_id,
                price=quote.price,
                currency=quote.currency,
                change_percent=quote.change_percent,
                size_value=Decimal(1),
            )
        )
    return MarketMapResponse(
        market=market,
        sizing="EQUAL",
        sectors=_sectors(grouped),
        provider="demo",
        dataset="demo.synthetic",
        data_level=DataLevel.DEMO,
        freshness=Freshness.FRESH if grouped else Freshness.UNAVAILABLE,
        timestamp_collected=datetime.now(UTC),
        is_demo=True,
        limitations=["Dados sintéticos de demonstração: não são cotações reais."],
        unavailable_reason=None if grouped else "DATASET_NOT_APPROVED",
        request_id=request_id,
    )


MOVERS_SIZE = 5
BR_MOVERS_LIMITATIONS = (
    "Ranking pelos números do dia entre as maiores empresas da B3 (brapi), sem filtro de opinião.",
    "Maior alta ou queda não indica o que vai acontecer. Não é recomendação de investimento.",
)
US_MOVERS_LIMITATIONS = (
    "Listas do Alpha Vantage para todo o mercado americano, inclusive ações de baixo preço e "
    "ETFs alavancados, que costumam ter as maiores variações.",
    "Maior alta ou queda não indica o que vai acontecer. Não é recomendação de investimento.",
)


def unavailable_movers(market: str, request_id: str, reason: str) -> MarketMoversResponse:
    return MarketMoversResponse(
        market=market,
        gainers=[],
        losers=[],
        most_active=[],
        provider="none",
        dataset="none",
        data_level=DataLevel.DELAYED,
        freshness=Freshness.UNAVAILABLE,
        limitations=[],
        unavailable_reason=reason,
        request_id=request_id,
    )


def real_movers(market: str, request_id: str) -> MarketMoversResponse:
    ids = _catalog_ids()
    snapshot = live_data.br_snapshot() if market == "BR" else live_data.us_movers()
    if snapshot is None:
        return unavailable_movers(market, request_id, "UNAVAILABLE")

    def item(row: dict, currency: str) -> MarketMover:
        return MarketMover(
            symbol=row["symbol"],
            canonical_id=ids.get(row["symbol"]),
            price=Decimal(row["price"]) if row.get("price") else None,
            currency=currency,
            change_percent=Decimal(row["change_percent"]) if row.get("change_percent") else None,
            volume=Decimal(row["volume"]) if row.get("volume") else None,
        )

    if market == "US":
        lists = {name: snapshot.data[name] for name in ("gainers", "losers", "most_active")}
        currency, provider, dataset = "USD", "alpha_vantage", "alpha_vantage.top_gainers_losers"
        limitations, level = US_MOVERS_LIMITATIONS, DataLevel.EOD
    else:
        rows = [
            row
            for row in snapshot.data["rows"].values()
            if row["type"] == "stock"
            and row.get("market_cap")
            and row.get("change_percent")
            and not row["symbol"].endswith("F")
        ]
        by_change = sorted(rows, key=lambda row: Decimal(row["change_percent"]))
        lists = {
            "gainers": [row for row in reversed(by_change) if Decimal(row["change_percent"]) > 0],
            "losers": [row for row in by_change if Decimal(row["change_percent"]) < 0],
            "most_active": sorted(
                (row for row in rows if row.get("volume")),
                key=lambda row: Decimal(row["volume"]) * Decimal(row["price"]),
                reverse=True,
            ),
        }
        currency, provider, dataset = "BRL", "brapi", "brapi.quote.list"
        limitations, level = BR_MOVERS_LIMITATIONS, DataLevel.DELAYED
    return MarketMoversResponse(
        market=market,
        gainers=[item(row, currency) for row in lists["gainers"][:MOVERS_SIZE]],
        losers=[item(row, currency) for row in lists["losers"][:MOVERS_SIZE]],
        most_active=[item(row, currency) for row in lists["most_active"][:MOVERS_SIZE]],
        provider=provider,
        dataset=dataset,
        data_level=level,
        freshness=snapshot.freshness,
        session_date=snapshot.data.get("session"),
        timestamp_collected=snapshot.fetched_at,
        limitations=list(limitations),
        request_id=request_id,
    )
