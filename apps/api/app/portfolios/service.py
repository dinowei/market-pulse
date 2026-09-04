from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Protocol
from uuid import uuid4

import psycopg

from app.contracts import (
    PortfolioCashBalanceResponse,
    PortfolioCreateRequest,
    PortfolioEventRequest,
    PortfolioEventResponse,
    PortfolioEventType,
    PortfolioListResponse,
    PortfolioPatchRequest,
    PortfolioPositionResponse,
    PortfolioResponse,
    PortfolioSummaryResponse,
)
from app.core.config import Settings, get_settings
from app.instruments.catalog import InstrumentCatalogEntry
from app.watchlists.service import validate_watchlist_instrument


class PortfolioNotFound(LookupError):
    """Portfolio or event is absent or owned by another user."""


class PortfolioConflict(ValueError):
    """The request conflicts with immutable or idempotent state."""


class PortfolioValidationError(ValueError):
    """A ledger event would violate a domain invariant."""


@dataclass(frozen=True)
class PortfolioEventInput:
    id: str
    event_type: str
    currency: str
    canonical_id: str | None
    quantity: Decimal | None
    unit_price: Decimal | None
    gross_amount: Decimal | None
    occurred_at: datetime
    created_at: datetime
    fee_amount: Decimal | None = None
    reversal_of_event_id: str | None = None
    idempotency_key: str = "replay"
    request_id: str = "replay"
    notes: str | None = None


@dataclass
class PortfolioPositionState:
    quantity: Decimal = Decimal("0")
    total_cost: Decimal = Decimal("0")

    @property
    def weighted_average_cost(self) -> Decimal:
        if self.quantity == 0:
            return Decimal("0")
        return self.total_cost / self.quantity


@dataclass
class PortfolioReplayState:
    cash_balances: dict[str, Decimal] = field(default_factory=dict)
    positions: dict[str, PortfolioPositionState] = field(default_factory=dict)
    event_count: int = 0
    last_event_at: datetime | None = None


SUPPORTED_EVENT_TYPES = {
    PortfolioEventType.CASH_DEPOSIT.value,
    PortfolioEventType.CASH_WITHDRAWAL.value,
    PortfolioEventType.BUY.value,
    PortfolioEventType.SELL.value,
    PortfolioEventType.FEE.value,
    PortfolioEventType.REVERSAL.value,
}


def _as_decimal(value: Decimal | None, field_name: str) -> Decimal:
    if value is None or not value.is_finite():
        raise PortfolioValidationError(f"{field_name} is required and must be finite")
    return value


def _cash(state: PortfolioReplayState, currency: str) -> Decimal:
    return state.cash_balances.get(currency, Decimal("0"))


def _set_cash(state: PortfolioReplayState, currency: str, amount: Decimal) -> None:
    if amount < 0:
        raise PortfolioValidationError("cash balance cannot be negative")
    state.cash_balances[currency] = amount


def _position(state: PortfolioReplayState, canonical_id: str) -> PortfolioPositionState:
    return state.positions.setdefault(canonical_id, PortfolioPositionState())


def _apply_event(
    state: PortfolioReplayState, event: PortfolioEventInput, *, inverse: bool = False
) -> None:
    event_type = (
        event.event_type.value
        if isinstance(event.event_type, PortfolioEventType)
        else event.event_type
    )
    multiplier = Decimal("-1") if inverse else Decimal("1")
    currency = event.currency
    if event_type in {
        PortfolioEventType.CASH_DEPOSIT.value,
        PortfolioEventType.CASH_WITHDRAWAL.value,
        PortfolioEventType.FEE.value,
    }:
        amount = _as_decimal(event.gross_amount, "gross_amount")
        if amount <= 0:
            raise PortfolioValidationError("gross_amount must be positive")
        direction = (
            Decimal("1") if event_type == PortfolioEventType.CASH_DEPOSIT.value else Decimal("-1")
        )
        _set_cash(state, currency, _cash(state, currency) + multiplier * direction * amount)
        return

    if event_type in {PortfolioEventType.BUY.value, PortfolioEventType.SELL.value}:
        if not event.canonical_id:
            raise PortfolioValidationError("canonical_id is required for asset events")
        quantity = _as_decimal(event.quantity, "quantity")
        unit_price = _as_decimal(event.unit_price, "unit_price")
        if quantity <= 0 or unit_price <= 0:
            raise PortfolioValidationError("quantity and unit_price must be positive")
        gross = event.gross_amount or quantity * unit_price
        if gross <= 0:
            raise PortfolioValidationError("gross_amount must be positive")
        fees = event.fee_amount or Decimal("0")
        if fees < 0:
            raise PortfolioValidationError("fee_amount cannot be negative")
        position = _position(state, event.canonical_id)
        if event_type == PortfolioEventType.BUY.value:
            _set_cash(state, currency, _cash(state, currency) - multiplier * (gross + fees))
            position.quantity += multiplier * quantity
            position.total_cost += multiplier * gross
        else:
            average = position.weighted_average_cost
            if not inverse and position.quantity < quantity:
                raise PortfolioValidationError("sell would create a negative position")
            _set_cash(state, currency, _cash(state, currency) + multiplier * (gross - fees))
            position.quantity -= multiplier * quantity
            position.total_cost -= multiplier * average * quantity
        if position.quantity < 0 or position.total_cost < 0:
            raise PortfolioValidationError("position cannot be negative")
        if position.quantity == 0:
            position.total_cost = Decimal("0")
        return

    if event_type == PortfolioEventType.REVERSAL.value:
        raise PortfolioValidationError("reversal requires its original event")
    raise PortfolioValidationError("unsupported portfolio event type")


def replay_events(events: list[PortfolioEventInput]) -> PortfolioReplayState:
    ordered = sorted(events, key=lambda item: (item.occurred_at, item.created_at, item.id))
    by_id = {item.id: item for item in ordered}
    state = PortfolioReplayState()
    reversed_ids: set[str] = set()
    for event in ordered:
        event_type = (
            event.event_type.value
            if isinstance(event.event_type, PortfolioEventType)
            else event.event_type
        )
        if event_type == PortfolioEventType.REVERSAL.value:
            target_id = event.reversal_of_event_id
            if not target_id or target_id not in by_id:
                raise PortfolioValidationError("reversal target does not exist")
            if target_id in reversed_ids:
                raise PortfolioValidationError("event has already been reversed")
            target = by_id[target_id]
            _apply_event(state, target, inverse=True)
            reversed_ids.add(target_id)
        else:
            _apply_event(state, event)
        state.event_count += 1
        state.last_event_at = event.occurred_at
    return state


def _event_hash(payload: PortfolioEventRequest) -> str:
    return hashlib.sha256(payload.model_dump_json().encode("utf-8")).hexdigest()


def _event_input_from_request(
    portfolio_id: str,
    payload: PortfolioEventRequest,
    *,
    event_id: str,
    idempotency_key: str,
    request_id: str,
) -> PortfolioEventInput:
    return PortfolioEventInput(
        id=event_id,
        event_type=payload.event_type.value,
        currency=payload.currency,
        canonical_id=payload.canonical_id,
        quantity=payload.quantity,
        unit_price=payload.unit_price,
        gross_amount=payload.gross_amount,
        occurred_at=payload.occurred_at,
        created_at=datetime.now(timezone.utc),
        fee_amount=payload.fee_amount,
        reversal_of_event_id=payload.reversal_of_event_id,
        idempotency_key=idempotency_key,
        request_id=request_id,
        notes=payload.notes,
    )


def validate_event(
    payload: PortfolioEventRequest, entry: InstrumentCatalogEntry | None = None
) -> None:
    if payload.event_type.value not in SUPPORTED_EVENT_TYPES:
        raise PortfolioValidationError("event type is not supported in Day 20")
    if payload.event_type is PortfolioEventType.REVERSAL:
        if not payload.reversal_of_event_id:
            raise PortfolioValidationError("reversal target is required")
        return
    if payload.event_type in {PortfolioEventType.BUY, PortfolioEventType.SELL}:
        if entry is None:
            raise PortfolioValidationError("a supported catalog instrument is required")
        if payload.quantity is None or payload.unit_price is None:
            raise PortfolioValidationError("quantity and unit_price are required")
        if payload.quantity <= 0 or payload.unit_price <= 0:
            raise PortfolioValidationError("quantity and unit_price must be positive")
    elif payload.gross_amount is None or payload.gross_amount <= 0:
        raise PortfolioValidationError("gross_amount must be positive")
    if payload.fee_amount is not None and payload.fee_amount < 0:
        raise PortfolioValidationError("fee_amount cannot be negative")


class PortfolioService(Protocol):
    def list(self, user_id: str) -> PortfolioListResponse: ...
    def create(self, user_id: str, payload: PortfolioCreateRequest) -> PortfolioResponse: ...
    def get(self, user_id: str, portfolio_id: str) -> PortfolioResponse: ...
    def patch(
        self, user_id: str, portfolio_id: str, payload: PortfolioPatchRequest
    ) -> PortfolioResponse: ...
    def add_event(
        self,
        user_id: str,
        portfolio_id: str,
        payload: PortfolioEventRequest,
        idempotency_key: str,
        request_id: str,
    ) -> PortfolioEventResponse: ...
    def events(self, user_id: str, portfolio_id: str) -> list[PortfolioEventResponse]: ...
    def positions(self, user_id: str, portfolio_id: str) -> list[PortfolioPositionResponse]: ...
    def cash_balances(
        self, user_id: str, portfolio_id: str
    ) -> list[PortfolioCashBalanceResponse]: ...
    def summary(self, user_id: str, portfolio_id: str) -> PortfolioSummaryResponse: ...
    def reverse_event(
        self, user_id: str, portfolio_id: str, event_id: str, idempotency_key: str, request_id: str
    ) -> PortfolioEventResponse: ...


@dataclass
class _MemoryPortfolio:
    id: str
    user_id: str
    name: str
    base_currency: str
    created_at: datetime
    updated_at: datetime
    events: list[PortfolioEventInput] = field(default_factory=list)
    idempotency: dict[str, tuple[str, PortfolioEventResponse]] = field(default_factory=dict)


class InMemoryPortfolioService:
    def __init__(self) -> None:
        self.portfolios: dict[str, _MemoryPortfolio] = {}

    def _owned(self, user_id: str, portfolio_id: str) -> _MemoryPortfolio:
        item = self.portfolios.get(portfolio_id)
        if item is None or item.user_id != user_id:
            raise PortfolioNotFound
        return item

    @staticmethod
    def _response(item: _MemoryPortfolio) -> PortfolioResponse:
        return PortfolioResponse(
            id=item.id,
            name=item.name,
            base_currency=item.base_currency,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    @staticmethod
    def _event_response(portfolio_id: str, event: PortfolioEventInput) -> PortfolioEventResponse:
        return PortfolioEventResponse(
            id=event.id,
            portfolio_id=portfolio_id,
            event_type=event.event_type,
            occurred_at=event.occurred_at,
            canonical_id=event.canonical_id,
            currency=event.currency,
            quantity=event.quantity,
            unit_price=event.unit_price,
            gross_amount=event.gross_amount,
            fee_amount=event.fee_amount,
            notes=event.notes,
            idempotency_key=event.idempotency_key,
            reversal_of_event_id=event.reversal_of_event_id,
            created_at=event.created_at,
            request_id=event.request_id,
        )

    def list(self, user_id: str) -> PortfolioListResponse:
        return PortfolioListResponse(
            items=[
                self._response(item) for item in self.portfolios.values() if item.user_id == user_id
            ]
        )

    def create(self, user_id: str, payload: PortfolioCreateRequest) -> PortfolioResponse:
        if any(
            item.user_id == user_id and item.name.casefold() == payload.name.casefold()
            for item in self.portfolios.values()
        ):
            raise PortfolioConflict("portfolio name already exists")
        now = datetime.now(timezone.utc)
        item = _MemoryPortfolio(
            str(uuid4()), user_id, payload.name, payload.base_currency, now, now
        )
        self.portfolios[item.id] = item
        return self._response(item)

    def get(self, user_id: str, portfolio_id: str) -> PortfolioResponse:
        return self._response(self._owned(user_id, portfolio_id))

    def patch(
        self, user_id: str, portfolio_id: str, payload: PortfolioPatchRequest
    ) -> PortfolioResponse:
        item = self._owned(user_id, portfolio_id)
        if payload.base_currency is not None and payload.base_currency != item.base_currency:
            raise PortfolioConflict("base currency is immutable")
        if payload.name is not None:
            item.name = payload.name
        item.updated_at = datetime.now(timezone.utc)
        return self._response(item)

    def _validate_payload(self, payload: PortfolioEventRequest) -> InstrumentCatalogEntry | None:
        entry = None
        if payload.canonical_id:
            try:
                entry = validate_watchlist_instrument(payload.canonical_id)
            except ValueError as exc:
                raise PortfolioValidationError(str(exc)) from exc
        validate_event(payload, entry)
        return entry

    def add_event(
        self,
        user_id: str,
        portfolio_id: str,
        payload: PortfolioEventRequest,
        idempotency_key: str,
        request_id: str,
    ) -> PortfolioEventResponse:
        item = self._owned(user_id, portfolio_id)
        entry = self._validate_payload(payload)
        if payload.event_type in {PortfolioEventType.BUY, PortfolioEventType.SELL}:
            assert entry is not None
            payload = payload.model_copy(update={"canonical_id": entry.canonical_id})
        payload_hash = _event_hash(payload)
        existing = item.idempotency.get(idempotency_key)
        if existing:
            if existing[0] != payload_hash:
                raise PortfolioConflict("Idempotency-Key was reused with a different payload")
            return existing[1]
        candidate = _event_input_from_request(
            portfolio_id,
            payload,
            event_id=str(uuid4()),
            idempotency_key=idempotency_key,
            request_id=request_id,
        )
        replay_events([*item.events, candidate])
        item.events.append(candidate)
        item.updated_at = datetime.now(timezone.utc)
        response = self._event_response(portfolio_id, candidate)
        item.idempotency[idempotency_key] = (payload_hash, response)
        return response

    def events(self, user_id: str, portfolio_id: str) -> list[PortfolioEventResponse]:
        item = self._owned(user_id, portfolio_id)
        return [
            self._event_response(item.id, event)
            for event in sorted(
                item.events, key=lambda value: (value.occurred_at, value.created_at, value.id)
            )
        ]

    def _replay(self, user_id: str, portfolio_id: str) -> PortfolioReplayState:
        item = self._owned(user_id, portfolio_id)
        return replay_events(item.events)

    def positions(self, user_id: str, portfolio_id: str) -> list[PortfolioPositionResponse]:
        state = self._replay(user_id, portfolio_id)
        return [
            PortfolioPositionResponse(
                canonical_id=key,
                quantity=value.quantity,
                total_cost=value.total_cost,
                weighted_average_cost=value.weighted_average_cost,
            )
            for key, value in sorted(state.positions.items())
            if value.quantity != 0
        ]

    def cash_balances(self, user_id: str, portfolio_id: str) -> list[PortfolioCashBalanceResponse]:
        state = self._replay(user_id, portfolio_id)
        return [
            PortfolioCashBalanceResponse(currency=key, balance=value)
            for key, value in sorted(state.cash_balances.items())
        ]

    def summary(self, user_id: str, portfolio_id: str) -> PortfolioSummaryResponse:
        portfolio = self._owned(user_id, portfolio_id)
        state = replay_events(portfolio.events)
        return PortfolioSummaryResponse(
            portfolio_id=portfolio.id,
            base_currency=portfolio.base_currency,
            cash_balances=state.cash_balances,
            positions=[
                PortfolioPositionResponse(
                    canonical_id=key,
                    quantity=value.quantity,
                    total_cost=value.total_cost,
                    weighted_average_cost=value.weighted_average_cost,
                )
                for key, value in sorted(state.positions.items())
                if value.quantity != 0
            ],
            event_count=state.event_count,
            last_event_at=state.last_event_at,
        )

    def reverse_event(
        self, user_id: str, portfolio_id: str, event_id: str, idempotency_key: str, request_id: str
    ) -> PortfolioEventResponse:
        item = self._owned(user_id, portfolio_id)
        target = next((event for event in item.events if event.id == event_id), None)
        if target is None:
            raise PortfolioNotFound
        if target.event_type == PortfolioEventType.REVERSAL.value or any(
            event.reversal_of_event_id == event_id for event in item.events
        ):
            raise PortfolioConflict("event has already been reversed")
        payload = PortfolioEventRequest(
            event_type=PortfolioEventType.REVERSAL,
            currency=target.currency,
            canonical_id=target.canonical_id,
            quantity=target.quantity,
            unit_price=target.unit_price,
            gross_amount=target.gross_amount,
            fee_amount=target.fee_amount,
            reversal_of_event_id=event_id,
            occurred_at=datetime.now(timezone.utc),
        )
        candidate = _event_input_from_request(
            portfolio_id,
            payload,
            event_id=str(uuid4()),
            idempotency_key=idempotency_key,
            request_id=request_id,
        )
        replay_events([*item.events, candidate])
        item.events.append(candidate)
        response = self._event_response(portfolio_id, candidate)
        item.idempotency[idempotency_key] = (_event_hash(payload), response)
        return response


class PostgresPortfolioService(InMemoryPortfolioService):
    """PostgreSQL-backed implementation; replay and validation stay shared."""

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__()
        self.settings = settings or get_settings()

    def _connection(self):
        return psycopg.connect(self.settings.database_url)

    @staticmethod
    def _portfolio_from_row(row) -> PortfolioResponse:
        return PortfolioResponse(
            id=str(row[0]), name=row[1], base_currency=row[2], created_at=row[3], updated_at=row[4]
        )

    def _owned_row(self, connection, user_id: str, portfolio_id: str):
        row = connection.execute(
            "SELECT id,name,base_currency,created_at,updated_at "
            "FROM portfolios WHERE id=%s AND user_id=%s",
            (portfolio_id, user_id),
        ).fetchone()
        if row is None:
            raise PortfolioNotFound
        return row

    def list(self, user_id: str) -> PortfolioListResponse:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT id,name,base_currency,created_at,updated_at "
                "FROM portfolios WHERE user_id=%s ORDER BY created_at,id",
                (user_id,),
            ).fetchall()
        return PortfolioListResponse(items=[self._portfolio_from_row(row) for row in rows])

    def create(self, user_id: str, payload: PortfolioCreateRequest) -> PortfolioResponse:
        try:
            with self._connection() as connection:
                row = connection.execute(
                    "INSERT INTO portfolios (user_id,name,base_currency) "
                    "VALUES (%s,%s,%s) "
                    "RETURNING id,name,base_currency,created_at,updated_at",
                    (user_id, payload.name, payload.base_currency),
                ).fetchone()
                connection.commit()
                return self._portfolio_from_row(row)
        except psycopg.errors.UniqueViolation as exc:
            raise PortfolioConflict("portfolio name already exists") from exc

    def get(self, user_id: str, portfolio_id: str) -> PortfolioResponse:
        with self._connection() as connection:
            return self._portfolio_from_row(self._owned_row(connection, user_id, portfolio_id))

    def patch(
        self, user_id: str, portfolio_id: str, payload: PortfolioPatchRequest
    ) -> PortfolioResponse:
        with self._connection() as connection:
            current = self._owned_row(connection, user_id, portfolio_id)
            if payload.base_currency is not None and payload.base_currency != current[2]:
                raise PortfolioConflict("base currency is immutable")
            name = payload.name or current[1]
            connection.execute(
                "UPDATE portfolios SET name=%s,updated_at=now() WHERE id=%s AND user_id=%s",
                (name, portfolio_id, user_id),
            )
            connection.commit()
            return self.get(user_id, portfolio_id)

    def _db_events(self, connection, user_id: str, portfolio_id: str) -> list[PortfolioEventInput]:
        self._owned_row(connection, user_id, portfolio_id)
        rows = connection.execute(
            "SELECT id,event_type,occurred_at,currency,quantity,price,gross_amount,fees,note,"
            "idempotency_key,reversed_event_id,created_at,request_id,instrument_id "
            "FROM portfolio_events WHERE portfolio_id=%s "
            "ORDER BY occurred_at,created_at,id",
            (portfolio_id,),
        ).fetchall()
        events: list[PortfolioEventInput] = []
        for row in rows:
            canonical_id = None
            if row[13] is not None:
                canonical_id = connection.execute(
                    "SELECT canonical_id FROM instruments WHERE id=%s", (row[13],)
                ).fetchone()[0]
            events.append(
                PortfolioEventInput(
                    id=str(row[0]),
                    event_type=str(row[1]),
                    occurred_at=row[2],
                    currency=row[3],
                    quantity=row[4],
                    unit_price=row[5],
                    gross_amount=row[6],
                    fee_amount=row[7],
                    notes=row[8],
                    idempotency_key=row[9],
                    reversal_of_event_id=str(row[10]) if row[10] else None,
                    created_at=row[11],
                    request_id=row[12],
                    canonical_id=canonical_id,
                )
            )
        return events

    def events(self, user_id: str, portfolio_id: str) -> list[PortfolioEventResponse]:
        with self._connection() as connection:
            values = self._db_events(connection, user_id, portfolio_id)
        return [self._event_response(portfolio_id, item) for item in values]

    def add_event(
        self,
        user_id: str,
        portfolio_id: str,
        payload: PortfolioEventRequest,
        idempotency_key: str,
        request_id: str,
    ) -> PortfolioEventResponse:
        if len(idempotency_key) > 128:
            raise PortfolioValidationError("Idempotency-Key is too long")
        entry = None
        if payload.canonical_id:
            entry = validate_watchlist_instrument(payload.canonical_id)
            payload = payload.model_copy(update={"canonical_id": entry.canonical_id})
        validate_event(payload, entry)
        payload_hash = _event_hash(payload)
        with self._connection() as connection:
            self._owned_row(connection, user_id, portfolio_id)
            existing = connection.execute(
                "SELECT id,payload_hash FROM portfolio_events "
                "WHERE portfolio_id=%s AND idempotency_key=%s",
                (portfolio_id, idempotency_key),
            ).fetchone()
            if existing:
                if existing[1] != payload_hash:
                    raise PortfolioConflict("Idempotency-Key was reused with a different payload")
                row = connection.execute(
                    "SELECT id,event_type,occurred_at,currency,quantity,price,gross_amount,fees,"
                    "note,"
                    "idempotency_key,reversed_event_id,created_at,request_id "
                    "FROM portfolio_events WHERE id=%s",
                    (existing[0],),
                ).fetchone()
                return self._event_response(
                    portfolio_id,
                    PortfolioEventInput(
                        id=str(row[0]),
                        event_type=str(row[1]),
                        occurred_at=row[2],
                        currency=row[3],
                        quantity=row[4],
                        unit_price=row[5],
                        gross_amount=row[6],
                        fee_amount=row[7],
                        notes=row[8],
                        idempotency_key=row[9],
                        reversal_of_event_id=str(row[10]) if row[10] else None,
                        created_at=row[11],
                        request_id=row[12],
                        canonical_id=payload.canonical_id,
                    ),
                )
            events = self._db_events(connection, user_id, portfolio_id)
            candidate = _event_input_from_request(
                portfolio_id,
                payload,
                event_id=str(uuid4()),
                idempotency_key=idempotency_key,
                request_id=request_id,
            )
            replay_events([*events, candidate])
            instrument_id = None
            if entry is not None:
                instrument_id = self._ensure_instrument(connection, entry)
            row = connection.execute(
                "INSERT INTO portfolio_events "
                "(id,portfolio_id,instrument_id,event_type,event_date,occurred_at,"
                "quantity,price,gross_amount,fees,currency,created_by,source,note,"
                "idempotency_key,payload_hash,request_id,reversed_event_id) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'USER',%s,%s,%s,%s,%s) "
                "RETURNING id,event_type,occurred_at,currency,quantity,price,gross_amount,"
                "fees,note,idempotency_key,reversed_event_id,created_at,request_id",
                (
                    candidate.id,
                    portfolio_id,
                    instrument_id,
                    payload.event_type.value,
                    payload.occurred_at.date(),
                    payload.occurred_at,
                    payload.quantity,
                    payload.unit_price,
                    payload.gross_amount,
                    payload.fee_amount,
                    payload.currency,
                    user_id,
                    payload.notes,
                    idempotency_key,
                    payload_hash,
                    request_id,
                    payload.reversal_of_event_id,
                ),
            ).fetchone()
            connection.commit()
        return self._event_response(
            portfolio_id,
            PortfolioEventInput(
                id=str(row[0]),
                event_type=str(row[1]),
                occurred_at=row[2],
                currency=row[3],
                quantity=row[4],
                unit_price=row[5],
                gross_amount=row[6],
                fee_amount=row[7],
                notes=row[8],
                idempotency_key=row[9],
                reversal_of_event_id=str(row[10]) if row[10] else None,
                created_at=row[11],
                request_id=row[12],
                canonical_id=payload.canonical_id,
            ),
        )

    def _ensure_instrument(self, connection, entry: InstrumentCatalogEntry):
        exchange_code = entry.exchange or "GLOBAL"
        connection.execute(
            "INSERT INTO exchanges (code,name,country,timezone,currency) "
            "VALUES (%s,%s,%s,%s,%s) ON CONFLICT (code) DO NOTHING",
            (
                exchange_code,
                exchange_code,
                (entry.country or "GL")[:2],
                entry.timezone,
                entry.currency,
            ),
        )
        exchange_id = connection.execute(
            "SELECT id FROM exchanges WHERE code=%s", (exchange_code,)
        ).fetchone()[0]
        row = connection.execute(
            "INSERT INTO instruments "
            "(exchange_id,symbol,name,instrument_type,currency,status,canonical_id) "
            "VALUES (%s,%s,%s,%s,%s,'ACTIVE',%s) "
            "ON CONFLICT (canonical_id) DO UPDATE SET symbol=EXCLUDED.symbol "
            "RETURNING id",
            (
                exchange_id,
                entry.symbol,
                entry.name,
                entry.instrument_type,
                entry.currency,
                entry.canonical_id,
            ),
        ).fetchone()
        return row[0]

    def _state(self, user_id: str, portfolio_id: str) -> PortfolioReplayState:
        with self._connection() as connection:
            events = self._db_events(connection, user_id, portfolio_id)
        return replay_events(events)

    def positions(self, user_id: str, portfolio_id: str) -> list[PortfolioPositionResponse]:
        state = self._state(user_id, portfolio_id)
        return [
            PortfolioPositionResponse(
                canonical_id=key,
                quantity=value.quantity,
                total_cost=value.total_cost,
                weighted_average_cost=value.weighted_average_cost,
            )
            for key, value in sorted(state.positions.items())
            if value.quantity != 0
        ]

    def cash_balances(self, user_id: str, portfolio_id: str) -> list[PortfolioCashBalanceResponse]:
        state = self._state(user_id, portfolio_id)
        return [
            PortfolioCashBalanceResponse(currency=key, balance=value)
            for key, value in sorted(state.cash_balances.items())
        ]

    def summary(self, user_id: str, portfolio_id: str) -> PortfolioSummaryResponse:
        portfolio = self.get(user_id, portfolio_id)
        state = self._state(user_id, portfolio_id)
        return PortfolioSummaryResponse(
            portfolio_id=portfolio.id,
            base_currency=portfolio.base_currency,
            cash_balances=state.cash_balances,
            positions=[
                PortfolioPositionResponse(
                    canonical_id=key,
                    quantity=value.quantity,
                    total_cost=value.total_cost,
                    weighted_average_cost=value.weighted_average_cost,
                )
                for key, value in sorted(state.positions.items())
                if value.quantity != 0
            ],
            event_count=state.event_count,
            last_event_at=state.last_event_at,
        )

    def reverse_event(
        self, user_id: str, portfolio_id: str, event_id: str, idempotency_key: str, request_id: str
    ) -> PortfolioEventResponse:
        with self._connection() as connection:
            events = self._db_events(connection, user_id, portfolio_id)
            target = next((item for item in events if item.id == event_id), None)
            if target is None:
                raise PortfolioNotFound
            if target.event_type == PortfolioEventType.REVERSAL.value or any(
                item.reversal_of_event_id == event_id for item in events
            ):
                raise PortfolioConflict("event has already been reversed")
        payload = PortfolioEventRequest(
            event_type=PortfolioEventType.REVERSAL,
            currency=target.currency,
            canonical_id=target.canonical_id,
            quantity=target.quantity,
            unit_price=target.unit_price,
            gross_amount=target.gross_amount,
            fee_amount=target.fee_amount,
            reversal_of_event_id=event_id,
            occurred_at=datetime.now(timezone.utc),
        )
        event = self.add_event(user_id, portfolio_id, payload, idempotency_key, request_id)
        return event


PortfolioServiceImpl = PostgresPortfolioService
