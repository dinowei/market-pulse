"""Offline Day 24 scenario plans, without persistence or public-provider wiring.

The calendar is fictitious: every Monday-Friday, including real holidays, has
a daily bar at 20:00 UTC. The final five dates also have hourly bars at 14:00
through 20:00 UTC. This is not the B3 calendar or actual market history.
Corporate actions are illustrative, unadjusted, and never applied to a ledger.
Reproducible fixture construction does not prove seed/reset idempotency in SQL.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, localcontext
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel

from app.contracts import EditorialPostCreateRequest, PerformanceProvenance
from app.editorial.validator import (
    EditorialBlock,
    EditorialSource,
    EditorialStatus,
    validate_editorial_blocks,
)
from app.instruments.catalog import InstrumentCatalogEntry
from app.market_data.corporate_actions import CorporateAction, normalize_corporate_action
from app.market_data.normalization import MarketBar
from app.portfolios.service import PortfolioEventInput, replay_events

DEMO_CUTOFF = datetime(2026, 1, 30, 20, tzinfo=timezone.utc)
DEMO_NAMESPACE = uuid5(NAMESPACE_URL, "urn:market-pulse:demo:day24:v1")
DEMO_LIMITATIONS = (
    "DEMO sintético e fictício; não representa instrumentos ou preços reais.",
    "Recorte histórico fixo em 2026-01-30 20:00 UTC; STALE, sem atualidade de mercado.",
    "Calendário fictício de segunda a sexta, incluindo feriados; não é o calendário B3.",
    "Todos os valores são denominados em BRL; índices sintéticos não replicam índices reais.",
    "Séries UNADJUSTED; eventos corporativos não ajustam barras nem creditam carteiras.",
)
DISCLAIMER = (
    "Conteúdo exclusivamente informativo e educacional. Não constitui recomendação de "
    "investimento, oferta, análise personalizada ou promessa de rentabilidade. Verifique "
    "as fontes, os horários e a classificação de atualização dos dados antes de tomar "
    "decisões financeiras."
)


@dataclass(frozen=True)
class DemoBar:
    id: str
    bar: MarketBar
    interval: str
    provenance: PerformanceProvenance


@dataclass(frozen=True)
class DemoCorporateAction:
    action: CorporateAction
    provenance: PerformanceProvenance


@dataclass(frozen=True)
class DemoUser:
    id: str
    owner_key: str
    name: str
    email: str


@dataclass(frozen=True)
class DemoWatchlist:
    id: str
    owner_key: str
    name: str
    canonical_ids: tuple[str, ...]


@dataclass(frozen=True)
class DemoFavorite:
    id: str
    owner_key: str
    canonical_id: str


@dataclass(frozen=True)
class DemoPortfolio:
    id: str
    owner_key: str
    name: str
    base_currency: str
    events: tuple[PortfolioEventInput, ...]


@dataclass(frozen=True)
class DemoEditorialDraft:
    id: str
    request: EditorialPostCreateRequest
    provenance: PerformanceProvenance
    status: EditorialStatus = EditorialStatus.DRAFT


def _json_value(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="python")
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: getattr(value, field.name) for field in fields(value)}
    if isinstance(value, (Decimal, datetime, date)):
        return value.isoformat() if isinstance(value, (datetime, date)) else str(value)
    raise TypeError("Unsupported DEMO manifest value")


@dataclass(frozen=True)
class DemoDataset:
    scenario_version: str
    cutoff: datetime
    instruments: tuple[InstrumentCatalogEntry, ...]
    daily_bars: tuple[DemoBar, ...]
    intraday_bars: tuple[DemoBar, ...]
    corporate_actions: tuple[DemoCorporateAction, ...]
    users: tuple[DemoUser, ...]
    watchlists: tuple[DemoWatchlist, ...]
    favorites: tuple[DemoFavorite, ...]
    portfolios: tuple[DemoPortfolio, ...]
    editorial_drafts: tuple[DemoEditorialDraft, ...]

    def fingerprint(self) -> str:
        """Hash full numerical content, dates, identity and provenance, not just counts."""
        manifest = json.dumps(
            self,
            default=_json_value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        return hashlib.sha256(manifest.encode("utf-8")).hexdigest()

    def summary(self) -> dict[str, str | int]:
        """Safe operational metadata only; no emails, ledger amounts or prices."""
        return {
            "scenario_version": self.scenario_version,
            "cutoff": self.cutoff.isoformat(),
            "fingerprint": self.fingerprint(),
            "instruments": len(self.instruments),
            "daily_bars": len(self.daily_bars),
            "intraday_bars": len(self.intraday_bars),
            "corporate_actions": len(self.corporate_actions),
            "users": len(self.users),
            "watchlists": len(self.watchlists),
            "favorites": len(self.favorites),
            "portfolios": len(self.portfolios),
            "portfolio_events": sum(len(item.events) for item in self.portfolios),
            "editorial_drafts": len(self.editorial_drafts),
        }


def _id(key: str) -> str:
    return str(uuid5(DEMO_NAMESPACE, key))


def _provenance(dataset: str, timestamp: datetime) -> PerformanceProvenance:
    return PerformanceProvenance(
        provider="demo",
        dataset=dataset,
        source="Market Pulse — fixture interna DEMO Day 24",
        data_level="DEMO",
        freshness="STALE",
        source_timestamp=timestamp,
        collected_at=DEMO_CUTOFF,
        latency_ms=None,
        limitations=DEMO_LIMITATIONS,
    )


# Explicit final-week anchors make ledger transactions independently checkable.
# Earlier bars use a small Decimal drift plus a bounded deterministic cycle.
_INSTRUMENTS = (
    ("MPXA3", "EQUITY", "Aster DEMO", ("100", "102", "104", "106", "108")),
    ("MPXB3", "EQUITY", "Brisa DEMO", ("60", "59", "59.5", "58", "58.5")),
    ("MPXC3", "EQUITY", "Cedro DEMO", ("30", "30", "31", "30.5", "31")),
    ("MPXD3", "EQUITY", "Duna DEMO", ("75", "76", "74", "77", "76")),
    ("MPXE3", "EQUITY", "Estrela DEMO", ("40", "39", "38", "39", "40")),
    ("MPET11", "ETF", "Tecnologia ETF DEMO", ("50", "49", "48", "47", "46")),
    ("MPBR11", "ETF", "Amplo ETF DEMO", ("80", "81", "82", "83", "84")),
    ("MPFI11", "FII", "Imóveis FII DEMO", ("20", "20.5", "21", "21.5", "22")),
    ("MPFR11", "FII", "Renda FII DEMO", ("25", "25.1", "25", "24.9", "25")),
    ("MPTECH", "INDEX", "Índice Tecnologia DEMO", ("1000", "1010", "995", "1020", "1030")),
    ("MPGLOBAL", "INDEX", "Índice Global DEMO", ("2000", "1990", "1980", "2000", "2010")),
)


def _catalog() -> tuple[InstrumentCatalogEntry, ...]:
    return tuple(
        InstrumentCatalogEntry(
            canonical_id=f"demo.{kind.lower()}.{symbol.lower()}",
            symbol=symbol,
            display_symbol=symbol,
            name=name,
            instrument_type=kind,
            exchange="DEMO",
            venue="DEMO",
            country="BR",
            region="DEMO",
            currency="BRL",
            timezone="UTC",
            catalog_status="CANDIDATE",
            coverage_tier="P0_CATALOG",
            data_support_status="METADATA_ONLY",
            notes=" ".join(DEMO_LIMITATIONS),
        )
        for symbol, kind, name, _ in _INSTRUMENTS
    )


def _bar(
    entry: InstrumentCatalogEntry, timestamp: datetime, close: Decimal, interval: str, sequence: int
) -> DemoBar:
    opening = close + (Decimal("0.10") if sequence % 2 else Decimal("-0.10"))
    bar = MarketBar.from_payload(
        {
            "canonical_id": entry.canonical_id,
            "timestamp": timestamp.isoformat(),
            "open": opening,
            "high": max(opening, close) + Decimal("0.20"),
            "low": min(opening, close) - Decimal("0.20"),
            "close": close,
            "volume": Decimal(1000 + sequence * 7),
            "currency": entry.currency,
            "adjustment_type": "UNADJUSTED",
        }
    )
    return DemoBar(
        _id(f"bar:{entry.canonical_id}:{interval}:{timestamp.isoformat()}"),
        bar,
        interval,
        _provenance(f"demo-day24-bars-{interval}", timestamp),
    )


def _history(
    instruments: tuple[InstrumentCatalogEntry, ...],
) -> tuple[tuple[DemoBar, ...], tuple[DemoBar, ...]]:
    timestamps = []
    current = datetime(2025, 1, 1, 20, tzinfo=timezone.utc)
    while current <= DEMO_CUTOFF:
        if current.weekday() < 5:
            timestamps.append(current)
        current += timedelta(days=1)
    daily, intraday = [], []
    cycle = (0, 1, 3, 1, 0, -1, -2, 0)
    for rank, entry in enumerate(instruments):
        anchors = tuple(Decimal(value) for value in _INSTRUMENTS[rank][3])
        slope = Decimal("0.03") if rank % 2 == 0 else Decimal("-0.02")
        for index, timestamp in enumerate(timestamps):
            offset = index - (len(timestamps) - 5)
            close = (
                anchors[offset]
                if offset >= 0
                else (anchors[0] + slope * offset + Decimal(cycle[offset % 8]) * Decimal("0.05"))
            )
            if offset < 0 and rank == 2:
                close = anchors[0] + Decimal(cycle[index % 8]) * Decimal("0.1")
            elif offset < 0 and rank == 3:
                close = anchors[0] + Decimal(cycle[index % 8]) * Decimal("5")
            elif offset < 0 and rank == 4:
                # A V-shaped drawdown followed by recovery, using only Decimal.
                progress = Decimal(index) / Decimal(len(timestamps) - 5)
                close = Decimal("28") + abs(progress - Decimal("0.5")) * Decimal("24")
                close = close.quantize(Decimal("0.01"))
            day_bar = _bar(entry, timestamp, close, "1d", index)
            if offset >= 0:
                hours = []
                for hour in range(14, 21):
                    intraday_close = close + Decimal(20 - hour) * Decimal("0.01")
                    hours.append(
                        _bar(
                            entry,
                            timestamp.replace(hour=hour),
                            intraday_close,
                            "1h",
                            index * 7 + hour - 14,
                        )
                    )
                intraday.extend(hours)
                day_bar = replace(
                    day_bar,
                    bar=replace(
                        day_bar.bar,
                        open=hours[0].bar.open,
                        close=hours[-1].bar.close,
                        high=max(item.bar.high for item in hours),
                        low=min(item.bar.low for item in hours),
                        volume=sum((item.bar.volume for item in hours), Decimal("0")),
                    ),
                )
            daily.append(day_bar)
    return tuple(daily), tuple(intraday)


def _portfolios(
    instruments: tuple[InstrumentCatalogEntry, ...], daily: tuple[DemoBar, ...]
) -> tuple[DemoPortfolio, ...]:
    by_symbol = {entry.symbol: entry.canonical_id for entry in instruments}
    closes = {(item.bar.canonical_id, item.bar.timestamp): item.bar.close for item in daily}
    plans = (
        (
            "A",
            "Alpha Demo",
            (
                (26, 12, "CASH_DEPOSIT", None, "10000"),
                (26, 20, "BUY", "MPXA3", "20"),
                (27, 12, "FEE", "MPXA3", "10"),
                (27, 20, "BUY", "MPET11", "10"),
                (28, 20, "SELL", "MPXA3", "5"),
            ),
        ),
        (
            "B",
            "Defensive Demo",
            (
                (26, 12, "CASH_DEPOSIT", None, "5000"),
                (26, 20, "BUY", "MPFI11", "40"),
                (27, 20, "BUY", "MPBR11", "10"),
                (28, 12, "FEE", "MPFI11", "20"),
                (28, 13, "REVERSAL", "MPFI11", "20"),
                (29, 12, "FEE", "MPFI11", "5"),
                (30, 12, "CASH_WITHDRAWAL", None, "200"),
            ),
        ),
    )
    result = []
    for owner, name, rows in plans:
        events = []
        for index, (day, hour, kind, symbol, amount) in enumerate(rows):
            occurred = datetime(2026, 1, day, hour, tzinfo=timezone.utc)
            canonical_id = by_symbol[symbol] if symbol else None
            trade = kind in {"BUY", "SELL"}
            quantity = Decimal(amount) if trade else None
            price = closes[canonical_id, occurred] if trade else None
            key = f"demo-day24:{owner}:event:{index}"
            events.append(
                PortfolioEventInput(
                    id=_id(key),
                    event_type=kind,
                    currency="BRL",
                    canonical_id=canonical_id,
                    quantity=quantity,
                    unit_price=price,
                    gross_amount=quantity * price if trade else Decimal(amount),
                    occurred_at=occurred,
                    created_at=occurred,
                    idempotency_key=key,
                    request_id="demo-day24-offline",
                    notes="DEMO: evento manual sintético planejado.",
                    reversal_of_event_id=events[-1].id if kind == "REVERSAL" else None,
                )
            )
        replay_events(events)
        result.append(DemoPortfolio(_id(f"portfolio:{owner}"), owner, name, "BRL", tuple(events)))
    return tuple(result)


def _corporate_actions(
    instruments: tuple[InstrumentCatalogEntry, ...],
) -> tuple[DemoCorporateAction, ...]:
    by_symbol = {entry.symbol: entry.canonical_id for entry in instruments}
    plans = (
        ("MPXA3", "CASH_DIVIDEND", {"gross_amount_per_share": "1.00"}),
        ("MPFI11", "CASH_DIVIDEND", {"gross_amount_per_share": "0.20"}),
        (
            "MPXB3",
            "JCP",
            {
                "gross_amount_per_share": "0.50",
                "net_amount_per_share": "0.425",
                "withholding_tax_rate": "0.15",
            },
        ),
        ("MPXC3", "SPLIT", {"split_ratio_from": "1", "split_ratio_to": "2"}),
    )
    result = []
    for index, (symbol, kind, values) in enumerate(plans):
        timestamp = datetime(2026, 1, 20 + index, 12, tzinfo=timezone.utc)
        key = f"demo-day24-action-{index}"
        action = normalize_corporate_action(
            {
                "action_type": kind,
                "status": "CONFIRMED",
                "currency": "BRL",
                "announced_date": timestamp.date().isoformat(),
                "ex_date": "2026-02-02" if kind == "SPLIT" else "2026-01-26",
                "record_date": None if kind == "SPLIT" else "2026-01-27",
                "payment_date": None if kind == "SPLIT" else "2026-01-30",
                "effective_date": "2026-02-02" if kind == "SPLIT" else None,
                "source_timestamp": timestamp.isoformat(),
                "external_id": key,
                **values,
            },
            instrument_id=by_symbol[symbol],
            provider="demo",
            dataset="demo-day24-corporate-actions",
            collected_at=DEMO_CUTOFF,
        )
        # The shared normalizer allocates an ingestion UUID; scenario identity
        # instead comes from the stable DEMO namespace after normalization.
        result.append(
            DemoCorporateAction(
                replace(action, event_id=_id(key)),
                _provenance("demo-day24-corporate-actions", timestamp),
            )
        )
    return tuple(result)


def _editorial_drafts() -> tuple[DemoEditorialDraft, ...]:
    result = []
    for day in (28, 29, 30):
        timestamp = datetime(2026, 1, day, 20, tzinfo=timezone.utc)
        source = EditorialSource(
            label="Fixture interna DEMO Day 24",
            publisher="Market Pulse DEMO",
            retrieved_at=DEMO_CUTOFF,
            justification="Cenário sintético determinístico criado localmente; sem fonte externa.",
        )
        sections = (
            ("FACT", f"Horário de corte DEMO: {timestamp.isoformat()}."),
            ("FACT", "Resumo factual DEMO: o cenário contém 11 instrumentos fictícios."),
            ("LIMITATION", "Mercados globais: sem dados reais; MPGLOBAL é índice fictício DEMO."),
            ("LIMITATION", "Brasil: instrumentos DEMO não correspondem a emissores reais."),
            ("LIMITATION", "Câmbio, juros e commodities: indisponíveis neste cenário DEMO."),
            ("LIMITATION", "Agenda econômica: indisponível; o calendário DEMO é fictício."),
            ("FACT", "Empresas em destaque: MPXA3 a MPXE3 são nomes fictícios da fixture DEMO."),
            ("LIMITATION", "Riscos e eventos: eventos corporativos DEMO não alteram o ledger."),
            ("FACT", "Fontes: fixture interna Market Pulse DEMO Day 24, sem notícias externas."),
            ("LIMITATION", "Limitações dos dados: " + " ".join(DEMO_LIMITATIONS)),
            ("LIMITATION", DISCLAIMER),
        )
        blocks = tuple(
            EditorialBlock(content_type=kind, text=text, sources=(source,))
            for kind, text in sections
        )
        if not validate_editorial_blocks(blocks).valid:
            raise ValueError("DEMO editorial fixture failed lexical validation")
        request = EditorialPostCreateRequest(
            slug=f"demo-morning-call-2026-01-{day}",
            title=f"Morning Call DEMO — 2026-01-{day}",
            summary=(
                "Edição informativa do cenário sintético DEMO local; sem dados de mercado real."
            ),
            content_date=timestamp.date(),
            blocks=blocks,
        )
        result.append(
            DemoEditorialDraft(
                _id(request.slug),
                request,
                _provenance("demo-day24-editorial", timestamp),
            )
        )
    return tuple(result)


def build_demo_dataset() -> DemoDataset:
    """Construct deterministic local plans; no DB, auth creation, config or network."""
    with localcontext() as context:
        context.prec = 28
        instruments = _catalog()
        daily, intraday = _history(instruments)
        by_symbol = {entry.symbol: entry.canonical_id for entry in instruments}
        users = tuple(
            DemoUser(
                _id(f"user:{owner}"),
                owner,
                f"Usuário DEMO {owner}",
                f"demo.{owner.lower()}@market-pulse.local",
            )
            for owner in ("A", "B")
        )
        watchlists = tuple(
            DemoWatchlist(
                _id(f"watchlist:{owner}"),
                owner,
                name,
                tuple(by_symbol[symbol] for symbol in symbols),
            )
            for owner, name, symbols in (
                ("A", "Growth Demo", ("MPXA3", "MPXB3", "MPET11")),
                ("B", "Income Demo", ("MPFI11", "MPFR11", "MPBR11")),
            )
        )
        favorites = tuple(
            DemoFavorite(
                _id(f"favorite:{owner}:{symbol}"),
                owner,
                by_symbol[symbol],
            )
            for owner, symbol in (
                ("A", "MPXA3"),
                ("A", "MPTECH"),
                ("B", "MPFI11"),
                ("B", "MPGLOBAL"),
            )
        )
        return DemoDataset(
            "day24-local-demo-v1",
            DEMO_CUTOFF,
            instruments,
            daily,
            intraday,
            _corporate_actions(instruments),
            users,
            watchlists,
            favorites,
            _portfolios(instruments, daily),
            _editorial_drafts(),
        )
