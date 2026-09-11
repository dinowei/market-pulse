"""Synthetic, factual economic calendar kept behind the DEMO boundary."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.contracts import (
    DataLevel,
    EconomicCalendarEvent,
    EconomicCalendarProvenance,
    EconomicEventImportance,
    EconomicEventStatus,
    EconomicEventValueStatus,
    Freshness,
)

UTC = timezone.utc
CALENDAR_MAX_DAYS = 366
CALENDAR_LIMIT = 100

_PRESCRIPTIVE_TERMS = re.compile(
    r"\b(?:buy|sell|bullish|bearish|compre|comprar|venda|vender|mantenha|segure|"
    r"recomend(?:amos|ação|acao)|sinal\s+de\s+(?:compra|venda)|vai\s+(?:subir|cair)|"
    r"target|price\s*target|action|signal)\b",
    re.IGNORECASE,
)


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def validate_calendar_text(text: str) -> bool:
    """Compliance gate shared by seed and dynamically assembled descriptions."""
    return _PRESCRIPTIVE_TERMS.search(_normalize(text)) is None


def validate_calendar_event(event: EconomicCalendarEvent) -> EconomicCalendarEvent:
    if not validate_calendar_text(f"{event.title} {event.description}"):
        raise ValueError("PRESCRIPTIVE_LANGUAGE")
    return event


def valid_timezone(value: str) -> bool:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        return False
    return True


def _event(
    event_id: str,
    event_key: str,
    country: str,
    timezone_name: str,
    event_date: date,
    title: str,
    description: str,
    importance: EconomicEventImportance,
    status: EconomicEventStatus,
    value_status: EconomicEventValueStatus,
    actual: Decimal | None = None,
    previous: Decimal | None = None,
    unit: str | None = None,
) -> EconomicCalendarEvent:
    zone = ZoneInfo(timezone_name)
    event_time = datetime.combine(event_date, time(hour=12), zone)
    collected = datetime.now(UTC)
    return validate_calendar_event(
        EconomicCalendarEvent(
            event_id=event_id,
            event_key=event_key,
            country=country,
            timezone=timezone_name,
            event_date=event_date,
            event_time=event_time,
            title=title,
            description=description,
            importance=importance,
            status=status,
            value_status=value_status,
            actual=actual,
            previous=previous,
            unit=unit,
            provenance=EconomicCalendarProvenance(
                source="market-pulse-demo",
                dataset="demo-economic-calendar",
                data_level=DataLevel.DEMO,
                freshness=Freshness.STALE,
                source_timestamp=event_time.astimezone(UTC),
                collected_at=collected,
                timezone=timezone_name,
                limitations=("Cenário sintético DEMO; não representa calendário oficial.",),
            ),
        )
    )


def demo_events() -> tuple[EconomicCalendarEvent, ...]:
    today = datetime.now(UTC).date()
    return (
        _event(
            "demo-br-ipca",
            "br.ipca.monthly.demo",
            "BR",
            "America/Sao_Paulo",
            today,
            "IPCA — variação mensal",
            "Divulgação mensal do índice de preços em cenário sintético.",
            EconomicEventImportance.HIGH,
            EconomicEventStatus.RELEASED,
            EconomicEventValueStatus.AVAILABLE,
            Decimal("0.42"),
            Decimal("0.38"),
            "%",
        ),
        _event(
            "demo-br-cdi",
            "br.cdi.daily.demo",
            "BR",
            "America/Sao_Paulo",
            today + timedelta(days=1),
            "CDI — referência diária",
            "Referência diária demonstrativa sem fonte externa aprovada.",
            EconomicEventImportance.MEDIUM,
            EconomicEventStatus.SCHEDULED,
            EconomicEventValueStatus.PENDING,
            None,
            Decimal("0.05"),
            "%",
        ),
        _event(
            "demo-us-cpi",
            "us.cpi.monthly.demo",
            "US",
            "America/New_York",
            today + timedelta(days=2),
            "CPI — variação mensal",
            "Publicação demonstrativa de indicador de preços dos Estados Unidos.",
            EconomicEventImportance.HIGH,
            EconomicEventStatus.UNAVAILABLE,
            EconomicEventValueStatus.UNAVAILABLE,
            None,
            None,
            "%",
        ),
    )


def filter_events(
    *,
    date_from: date,
    date_to: date,
    country: str | None = None,
    importance: EconomicEventImportance | None = None,
    timezone_name: str | None = None,
) -> list[EconomicCalendarEvent]:
    events = [event for event in demo_events() if date_from <= event.event_date <= date_to]
    if country:
        events = [event for event in events if event.country == country]
    if importance:
        events = [event for event in events if event.importance is importance]
    if timezone_name:
        events = [event for event in events if event.timezone == timezone_name]
    return sorted(
        events,
        key=lambda event: (
            event.event_date,
            event.event_time or datetime.min.replace(tzinfo=UTC),
            event.event_key,
        ),
    )
