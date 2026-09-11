from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID, uuid4

import psycopg

from app.contracts import (
    WatchlistItemResponse,
    WatchlistResponse,
)
from app.core.config import Settings, get_settings
from app.instruments.catalog import (
    CatalogStatus,
    CoverageTier,
    DataSupportStatus,
    InstrumentCatalogEntry,
    get_catalog,
)


class WatchlistNotFound(LookupError):
    """The watchlist is absent or owned by another user."""


class WatchlistInvalid(ValueError):
    """The requested watchlist operation is invalid."""


class WatchlistConflict(ValueError):
    """The requested operation conflicts with existing state."""


def find_catalog_entry(canonical_id: str) -> InstrumentCatalogEntry:
    normalized = canonical_id.strip().casefold()
    for entry in get_catalog():
        if entry.canonical_id == normalized:
            return entry
    raise WatchlistInvalid("BLOCKED_SCOPE: instrument is not in the approved watchlist universe")


def validate_watchlist_instrument(canonical_id: str) -> InstrumentCatalogEntry:
    entry = find_catalog_entry(canonical_id)
    if entry.instrument_type.upper() == "MUTUAL_FUND":
        raise WatchlistInvalid("BLOCKED_SCOPE: mutual funds require licensed coverage")
    if entry.catalog_status is CatalogStatus.OUT_OF_SCOPE:
        raise WatchlistInvalid("BLOCKED_SCOPE: instrument is outside the supported scope")
    if entry.coverage_tier not in {CoverageTier.P0_OPERATIONAL, CoverageTier.P0_CATALOG}:
        raise WatchlistInvalid("BLOCKED_SCOPE: instrument is not operationally supported")
    if entry.data_support_status is DataSupportStatus.UNAVAILABLE:
        raise WatchlistInvalid("BLOCKED_SCOPE: instrument data is unavailable")
    return entry


class WatchlistStore(Protocol):
    def list(self, user_id: str) -> list[WatchlistResponse]: ...

    def get(self, user_id: str, watchlist_id: str) -> WatchlistResponse: ...

    def create(self, user_id: str, name: str, *, is_system: bool = False) -> WatchlistResponse: ...

    def rename(self, user_id: str, watchlist_id: str, name: str) -> WatchlistResponse: ...

    def delete(self, user_id: str, watchlist_id: str) -> None: ...

    def add_item(
        self, user_id: str, watchlist_id: str, canonical_id: str
    ) -> WatchlistItemResponse: ...

    def remove_item(self, user_id: str, watchlist_id: str, canonical_id: str) -> None: ...

    def reorder(
        self, user_id: str, watchlist_id: str, canonical_ids: list[str]
    ) -> WatchlistResponse: ...

    def favorite(self, user_id: str, canonical_id: str) -> WatchlistItemResponse: ...

    def unfavorite(self, user_id: str, canonical_id: str) -> None: ...


def _support_state(entry: InstrumentCatalogEntry) -> str:
    if entry.coverage_tier is CoverageTier.P0_OPERATIONAL:
        return "P0_OPERATIONAL"
    return "P0_CATALOG"


def _item_response(
    item_id: str, entry: InstrumentCatalogEntry, position: int
) -> WatchlistItemResponse:
    return WatchlistItemResponse(
        id=item_id,
        canonical_id=entry.canonical_id,
        symbol=entry.symbol,
        display_symbol=entry.display_symbol,
        name=entry.name,
        instrument_type=entry.instrument_type,
        exchange=entry.exchange,
        currency=entry.currency,
        timezone=entry.timezone,
        support_state=_support_state(entry),
        position=position,
    )


def _watchlist_response(
    watchlist_id: str,
    name: str,
    is_system: bool,
    created_at: datetime,
    updated_at: datetime,
    items: list[WatchlistItemResponse],
) -> WatchlistResponse:
    return WatchlistResponse(
        id=watchlist_id,
        name=name,
        is_system=is_system,
        items=items,
        created_at=created_at,
        updated_at=updated_at,
    )


@dataclass
class _MemoryWatchlist:
    id: str
    user_id: str
    name: str
    is_system: bool
    created_at: datetime
    updated_at: datetime
    items: list[tuple[str, str]] = field(default_factory=list)


class InMemoryWatchlistService:
    def __init__(self) -> None:
        self.watchlists: dict[str, _MemoryWatchlist] = {}

    def _owned(self, user_id: str, watchlist_id: str) -> _MemoryWatchlist:
        watchlist = self.watchlists.get(watchlist_id)
        if watchlist is None or watchlist.user_id != user_id:
            raise WatchlistNotFound
        return watchlist

    def _response(self, watchlist: _MemoryWatchlist) -> WatchlistResponse:
        return _watchlist_response(
            watchlist.id,
            watchlist.name,
            watchlist.is_system,
            watchlist.created_at,
            watchlist.updated_at,
            [
                _item_response(item_id, find_catalog_entry(canonical_id), position)
                for position, (item_id, canonical_id) in enumerate(watchlist.items)
            ],
        )

    def list(self, user_id: str) -> list[WatchlistResponse]:
        return [self._response(w) for w in self.watchlists.values() if w.user_id == user_id]

    def get(self, user_id: str, watchlist_id: str) -> WatchlistResponse:
        return self._response(self._owned(user_id, watchlist_id))

    def create(self, user_id: str, name: str, *, is_system: bool = False) -> WatchlistResponse:
        if any(
            w.user_id == user_id and w.name.casefold() == name.casefold()
            for w in self.watchlists.values()
        ):
            raise WatchlistConflict
        now = datetime.now(timezone.utc)
        watchlist = _MemoryWatchlist(str(uuid4()), user_id, name, is_system, now, now)
        self.watchlists[watchlist.id] = watchlist
        return self._response(watchlist)

    def rename(self, user_id: str, watchlist_id: str, name: str) -> WatchlistResponse:
        watchlist = self._owned(user_id, watchlist_id)
        if watchlist.is_system:
            raise WatchlistInvalid("System watchlist cannot be renamed")
        if any(
            w.user_id == user_id and w.id != watchlist_id and w.name.casefold() == name.casefold()
            for w in self.watchlists.values()
        ):
            raise WatchlistConflict
        watchlist.name = name
        watchlist.updated_at = datetime.now(timezone.utc)
        return self._response(watchlist)

    def delete(self, user_id: str, watchlist_id: str) -> None:
        watchlist = self._owned(user_id, watchlist_id)
        if watchlist.is_system:
            raise WatchlistInvalid("System watchlist cannot be deleted")
        del self.watchlists[watchlist_id]

    def add_item(self, user_id: str, watchlist_id: str, canonical_id: str) -> WatchlistItemResponse:
        watchlist = self._owned(user_id, watchlist_id)
        entry = validate_watchlist_instrument(canonical_id)
        for item_id, existing in watchlist.items:
            if existing == entry.canonical_id:
                return _item_response(
                    item_id,
                    entry,
                    next(i for i, item in enumerate(watchlist.items) if item[0] == item_id),
                )
        item_id = str(uuid4())
        watchlist.items.append((item_id, entry.canonical_id))
        watchlist.updated_at = datetime.now(timezone.utc)
        return _item_response(item_id, entry, len(watchlist.items) - 1)

    def remove_item(self, user_id: str, watchlist_id: str, canonical_id: str) -> None:
        watchlist = self._owned(user_id, watchlist_id)
        normalized = canonical_id.strip().casefold()
        for index, (_item_id, existing) in enumerate(watchlist.items):
            if existing == normalized:
                watchlist.items.pop(index)
                watchlist.updated_at = datetime.now(timezone.utc)
                return
        raise WatchlistNotFound

    def reorder(
        self, user_id: str, watchlist_id: str, canonical_ids: list[str]
    ) -> WatchlistResponse:
        watchlist = self._owned(user_id, watchlist_id)
        normalized = [value.strip().casefold() for value in canonical_ids]
        existing = [canonical_id for _item_id, canonical_id in watchlist.items]
        if len(set(normalized)) != len(normalized) or set(normalized) != set(existing):
            raise WatchlistInvalid("Reorder must include every item exactly once")
        by_canonical = {canonical_id: item_id for item_id, canonical_id in watchlist.items}
        watchlist.items = [
            (by_canonical[canonical_id], canonical_id) for canonical_id in normalized
        ]
        watchlist.updated_at = datetime.now(timezone.utc)
        return self._response(watchlist)

    def favorite(self, user_id: str, canonical_id: str) -> WatchlistItemResponse:
        favorites = next(
            (w for w in self.watchlists.values() if w.user_id == user_id and w.is_system),
            None,
        )
        if favorites is None:
            favorites = self.create(user_id, "Favoritos", is_system=True)
            favorites_id = favorites.id
        else:
            favorites_id = favorites.id
        return self.add_item(user_id, favorites_id, canonical_id)

    def unfavorite(self, user_id: str, canonical_id: str) -> None:
        favorites = next(
            (w for w in self.watchlists.values() if w.user_id == user_id and w.is_system),
            None,
        )
        if favorites is None:
            raise WatchlistNotFound
        self.remove_item(user_id, favorites.id, canonical_id)


class PostgresWatchlistService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def _connection(self):
        return psycopg.connect(self.settings.database_url)

    def _ensure_instrument(
        self, connection: psycopg.Connection, entry: InstrumentCatalogEntry
    ) -> UUID:
        exchange_code = entry.exchange or "GLOBAL"
        country = (entry.country or "GL")[:2]
        timezone_name = entry.timezone
        currency = entry.currency
        connection.execute(
            "INSERT INTO exchanges (code,name,country,timezone,currency) VALUES (%s,%s,%s,%s,%s) "
            "ON CONFLICT (code) DO NOTHING",
            (exchange_code, exchange_code, country, timezone_name, currency),
        )
        row = connection.execute(
            "SELECT id FROM exchanges WHERE code=%s", (exchange_code,)
        ).fetchone()
        if row is None:
            raise WatchlistInvalid("Instrument exchange is unavailable")
        instrument = connection.execute(
            "INSERT INTO instruments "
            "(exchange_id,symbol,name,instrument_type,currency,status,canonical_id) "
            "VALUES (%s,%s,%s,%s,%s,'ACTIVE',%s) "
            "ON CONFLICT (canonical_id) DO UPDATE SET symbol=EXCLUDED.symbol "
            "RETURNING id",
            (
                row[0],
                entry.symbol,
                entry.name,
                entry.instrument_type,
                currency,
                entry.canonical_id,
            ),
        ).fetchone()
        if instrument is None:
            raise WatchlistInvalid("Instrument is unavailable")
        return instrument[0]

    def _row_to_response(self, row) -> WatchlistResponse:
        watchlist_id, name, is_system, created_at, updated_at = row[:5]
        items = []
        for (
            item_id,
            canonical_id,
            symbol,
            display_symbol,
            instrument_name,
            instrument_type,
            exchange,
            currency,
            timezone_name,
            position,
        ) in row[5] or []:
            entry = find_catalog_entry(canonical_id)
            items.append(
                _item_response(
                    str(item_id),
                    entry.model_copy(
                        update={
                            "symbol": symbol,
                            "name": instrument_name,
                            "instrument_type": instrument_type,
                            "exchange": exchange,
                            "currency": currency,
                            "timezone": timezone_name,
                        }
                    ),
                    position,
                )
            )
        return _watchlist_response(
            str(watchlist_id), name, is_system, created_at, updated_at, items
        )

    def _fetch(self, connection, user_id: str, watchlist_id: str | None = None):
        params: list[object] = [user_id]
        where = "w.user_id=%s"
        if watchlist_id is not None:
            where += " AND w.id=%s"
            params.append(watchlist_id)
        row = connection.execute(
            "SELECT w.id,w.name,w.is_system,w.created_at,w.updated_at, "
            "COALESCE(array_agg(ROW(wi.id,i.canonical_id,i.symbol,i.symbol,"
            "i.name,i.instrument_type,e.code,i.currency,e.timezone,wi.position) "
            "ORDER BY wi.position) FILTER (WHERE wi.id IS NOT NULL),'{}') "
            "FROM watchlists w LEFT JOIN watchlist_items wi ON wi.watchlist_id=w.id "
            "LEFT JOIN instruments i ON i.id=wi.instrument_id "
            "LEFT JOIN exchanges e ON e.id=i.exchange_id "
            f"WHERE {where} GROUP BY w.id ORDER BY w.created_at",
            params,
        ).fetchall()
        if watchlist_id is not None and not row:
            raise WatchlistNotFound
        return row

    def list(self, user_id: str) -> list[WatchlistResponse]:
        with self._connection() as connection:
            return [self._row_to_response(row) for row in self._fetch(connection, user_id)]

    def get(self, user_id: str, watchlist_id: str) -> WatchlistResponse:
        with self._connection() as connection:
            return self._row_to_response(self._fetch(connection, user_id, watchlist_id)[0])

    def create(self, user_id: str, name: str, *, is_system: bool = False) -> WatchlistResponse:
        try:
            with self._connection() as connection:
                row = connection.execute(
                    "INSERT INTO watchlists (user_id,name,is_system) "
                    "VALUES (%s,%s,%s) RETURNING id",
                    (user_id, name, is_system),
                ).fetchone()
                connection.commit()
                return self.get(user_id, str(row[0]))
        except psycopg.errors.UniqueViolation as exc:
            raise WatchlistConflict from exc

    def rename(self, user_id: str, watchlist_id: str, name: str) -> WatchlistResponse:
        with self._connection() as connection:
            result = connection.execute(
                "UPDATE watchlists SET name=%s,updated_at=now() "
                "WHERE id=%s AND user_id=%s AND is_system=FALSE",
                (name, watchlist_id, user_id),
            )
            if result.rowcount == 0:
                raise WatchlistNotFound
            connection.commit()
            return self.get(user_id, watchlist_id)

    def delete(self, user_id: str, watchlist_id: str) -> None:
        with self._connection() as connection:
            result = connection.execute(
                "DELETE FROM watchlists WHERE id=%s AND user_id=%s AND is_system=FALSE",
                (watchlist_id, user_id),
            )
            if result.rowcount == 0:
                raise WatchlistNotFound
            connection.commit()

    def add_item(self, user_id: str, watchlist_id: str, canonical_id: str) -> WatchlistItemResponse:
        entry = validate_watchlist_instrument(canonical_id)
        with self._connection() as connection:
            self._fetch(connection, user_id, watchlist_id)
            instrument_id = self._ensure_instrument(connection, entry)
            existing = connection.execute(
                "SELECT id,position FROM watchlist_items "
                "WHERE watchlist_id=%s AND instrument_id=%s",
                (watchlist_id, instrument_id),
            ).fetchone()
            if existing:
                connection.commit()
                return _item_response(str(existing[0]), entry, existing[1])
            position = connection.execute(
                "SELECT COALESCE(MAX(position)+1,0) FROM watchlist_items WHERE watchlist_id=%s",
                (watchlist_id,),
            ).fetchone()[0]
            row = connection.execute(
                "INSERT INTO watchlist_items "
                "(watchlist_id,instrument_id,position) VALUES (%s,%s,%s) "
                "RETURNING id",
                (watchlist_id, instrument_id, position),
            ).fetchone()
            connection.commit()
            return _item_response(str(row[0]), entry, position)

    def remove_item(self, user_id: str, watchlist_id: str, canonical_id: str) -> None:
        with self._connection() as connection:
            self._fetch(connection, user_id, watchlist_id)
            result = connection.execute(
                "DELETE FROM watchlist_items wi USING instruments i "
                "WHERE wi.watchlist_id=%s AND wi.instrument_id=i.id "
                "AND i.canonical_id=%s",
                (watchlist_id, canonical_id.strip().casefold()),
            )
            if result.rowcount == 0:
                raise WatchlistNotFound
            connection.commit()

    def reorder(
        self, user_id: str, watchlist_id: str, canonical_ids: list[str]
    ) -> WatchlistResponse:
        normalized = [value.strip().casefold() for value in canonical_ids]
        with self._connection() as connection:
            self._fetch(connection, user_id, watchlist_id)
            rows = connection.execute(
                "SELECT i.canonical_id FROM watchlist_items wi "
                "JOIN instruments i ON i.id=wi.instrument_id "
                "WHERE wi.watchlist_id=%s",
                (watchlist_id,),
            ).fetchall()
            existing = [row[0] for row in rows]
            if len(set(normalized)) != len(normalized) or set(normalized) != set(existing):
                raise WatchlistInvalid("Reorder must include every item exactly once")
            for position, canonical_id in enumerate(normalized):
                connection.execute(
                    "UPDATE watchlist_items wi SET position=%s "
                    "FROM instruments i WHERE wi.watchlist_id=%s "
                    "AND wi.instrument_id=i.id AND i.canonical_id=%s",
                    (position, watchlist_id, canonical_id),
                )
            connection.commit()
            return self.get(user_id, watchlist_id)

    def favorite(self, user_id: str, canonical_id: str) -> WatchlistItemResponse:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT id FROM watchlists "
                "WHERE user_id=%s AND is_system=TRUE AND name='Favoritos'",
                (user_id,),
            ).fetchone()
            if row is None:
                try:
                    row = connection.execute(
                        "INSERT INTO watchlists (user_id,name,is_system) "
                        "VALUES (%s,'Favoritos',TRUE) RETURNING id",
                        (user_id,),
                    ).fetchone()
                except psycopg.errors.UniqueViolation:
                    connection.rollback()
                    row = connection.execute(
                        "SELECT id FROM watchlists "
                        "WHERE user_id=%s AND is_system=TRUE AND name='Favoritos'",
                        (user_id,),
                    ).fetchone()
            connection.commit()
            return self.add_item(user_id, str(row[0]), canonical_id)

    def unfavorite(self, user_id: str, canonical_id: str) -> None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT id FROM watchlists "
                "WHERE user_id=%s AND is_system=TRUE AND name='Favoritos'",
                (user_id,),
            ).fetchone()
            if row is None:
                raise WatchlistNotFound
        self.remove_item(user_id, str(row[0]), canonical_id)


WatchlistService = PostgresWatchlistService
