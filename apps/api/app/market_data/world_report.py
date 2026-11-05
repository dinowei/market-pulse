"""World close report (ADR-030): one square per region, built only from served quotes.

The sentences are fixed rules over validated numbers. They state what moved, never why: a
cause would need evidence the quotes do not carry, so headlines appear beside them with
their source. Regions are read through US-listed ETFs, priced in dollars, and each square
says so.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from app.contracts import PublicQuote, WorldNewsItem, WorldRegion, WorldReportResponse

Basis = Literal["ETF", "AVERAGE", "NONE"]


def _etf(symbol: str) -> str:
    return "etf.us.nysearca.spy" if symbol == "SPY" else f"etf.us.listed.{symbol.lower()}"


@dataclass(frozen=True)
class RegionSpec:
    id: str
    title: str
    main: str | None
    members: tuple[str, ...]
    news_ticker: str | None
    average: bool = False


REGIONS: tuple[RegionSpec, ...] = (
    RegionSpec(
        "brasil",
        "Brasil",
        _etf("EWZ"),
        tuple(
            f"equity.br.b3.{symbol}"
            for symbol in ("petr4", "vale3", "itub4", "bbdc4", "bbas3", "abev3", "wege3", "b3sa3")
        ),
        "EWZ",
    ),
    RegionSpec(
        "america-do-sul", "América do Sul", _etf("ILF"), tuple(map(_etf, ("ECH", "ARGT"))), "ILF"
    ),
    RegionSpec(
        "estados-unidos",
        "Estados Unidos",
        _etf("SPY"),
        (
            "equity.us.nasdaq.nvda",
            "equity.us.nasdaq.msft",
            "equity.us.nasdaq.aapl",
            "equity.us.nasdaq.amzn",
            "equity.us.nasdaq.googl",
            "equity.us.nasdaq.meta",
            "equity.us.nasdaq.tsla",
            _etf("XLK"),
            _etf("XLF"),
            _etf("XLE"),
        ),
        "SPY",
    ),
    RegionSpec(
        "america-do-norte",
        "América do Norte (Canadá e México)",
        None,
        tuple(map(_etf, ("EWC", "EWW"))),
        "EWC",
        average=True,
    ),
    RegionSpec("europa", "Europa", _etf("VGK"), tuple(map(_etf, ("EWG", "EWU"))), "VGK"),
    RegionSpec(
        "asia",
        "Ásia e Oceania",
        None,
        tuple(map(_etf, ("EWJ", "FXI", "EWY", "INDA", "EWA"))),
        "FXI",
        average=True,
    ),
    RegionSpec(
        "moedas",
        "Moedas e cripto",
        None,
        (
            "fx.global.usd-brl",
            "fx.global.eur-usd",
            "crypto.global.btc-usd",
            "commodity.global.xau-usd",
        ),
        None,
    ),
)

LIMITATIONS = (
    "Cada região é lida por ETFs listados nos EUA, em dólar: inclui o câmbio e não é o índice "
    "local nem seus pontos.",
    "Os mercados fecham em horários diferentes; cada ativo traz a própria data.",
    "As frases descrevem o movimento dos ativos acompanhados e não afirmam a causa. Notícias "
    "aparecem ao lado, com a fonte.",
    "Conteúdo informativo para estudo; não é recomendação de investimento.",
)


def _usable(quote: PublicQuote) -> bool:
    return quote.freshness != "UNAVAILABLE" and quote.change_percent is not None


def _percent(value: Decimal) -> str:
    rounded = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sign = "+" if rounded > 0 else ""
    return f"{sign}{rounded}%".replace(".", ",")


def _unsigned(value: Decimal) -> str:
    return _percent(abs(value)).lstrip("+")


def _movement(value: Decimal) -> str:
    return "Alta" if value > 0 else "Queda" if value < 0 else "Estável"


def _session(quote: PublicQuote) -> date | None:
    official = quote.timestamp_official
    return quote.session_date or (official.date() if official else None)


def _summary(
    change: Decimal | None, basis_label: str, members: Sequence[PublicQuote], total: int
) -> str:
    known = sorted(
        (item for item in members if _usable(item)), key=lambda item: item.change_percent
    )
    if change is None and not known:
        return "Sem dados de fechamento para esta região agora."
    parts = []
    if change is not None:
        parts.append(f"{_movement(change)} de {_unsigned(change)} ({basis_label}).")
    if known:
        up = sum(item.change_percent > 0 for item in known)
        parts.append(f"{up} de {len(known)} ativos acompanhados subiram.")
        best, worst = known[-1], known[0]
        if best.change_percent > 0:
            parts.append(f"Maior alta: {best.symbol} {_percent(best.change_percent)}.")
        if worst.change_percent < 0:
            parts.append(f"Maior queda: {worst.symbol} {_percent(worst.change_percent)}.")
    if len(known) < total:
        parts.append(f"{total - len(known)} sem dado agora.")
    return " ".join(parts)


def _region(
    spec: RegionSpec,
    request_id: str,
    quote: Callable[[str, str], PublicQuote],
    news: Callable[[str], Sequence[Mapping[str, str]]],
) -> WorldRegion:
    main = quote(spec.main, request_id) if spec.main else None
    members = [quote(canonical_id, request_id) for canonical_id in spec.members]
    known = [item for item in members if _usable(item)]
    change: Decimal | None = None
    basis: Basis = "NONE"
    label = "sem medida única; veja cada ativo"
    session = max((day for day in map(_session, known) if day), default=None)
    if main is not None:
        label = f"via ETF {main.symbol}"
        if _usable(main):
            change, basis, session = main.change_percent, "ETF", _session(main)
    elif spec.average:
        label = f"média simples de {len(known)} ETFs"
        if known:
            change = sum((item.change_percent for item in known), Decimal(0)) / len(known)
            basis = "AVERAGE"
    everything = [*([main] if main else []), *members]
    reasons = [item.unavailable_reason for item in everything if item.unavailable_reason]
    articles = news(spec.news_ticker) if spec.news_ticker else ()
    return WorldRegion(
        id=spec.id,
        title=spec.title,
        basis=basis,
        basis_label=label,
        change_percent=change,
        session_date=session,
        summary=_summary(change, label, members, len(members)),
        members_with_data=len(known),
        members_total=len(members),
        unavailable_reason=reasons[0] if change is None and not known and reasons else None,
        members=everything,
        news=[WorldNewsItem(**item) for item in articles],
    )


def world_report(
    request_id: str,
    *,
    quote: Callable[[str, str], PublicQuote],
    news: Callable[[str], Sequence[Mapping[str, str]]],
) -> WorldReportResponse:
    return WorldReportResponse(
        regions=[_region(spec, request_id, quote, news) for spec in REGIONS],
        limitations=LIMITATIONS,
        request_id=request_id,
    )
