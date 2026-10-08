"""Read models for portfolio income and event markers.

The module only projects persisted ledger/corporate-action rows. It never
creates decorative markers and it never changes portfolio calculations.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import psycopg

from app.contracts import (
    DataLevel,
    Freshness,
    MarkerSourceType,
    PerformanceProvenance,
    PortfolioEventMarkerResponse,
    PortfolioEventMarkersResponse,
    PortfolioIncomeResponse,
    PortfolioIncomeStatus,
    PortfolioIncomeType,
)
from app.core.config import Settings, get_settings
from app.portfolios.income import derive_income_status, validate_marker_references


class PortfolioReadModelNotFound(LookupError):
    """Portfolio does not exist or belongs to another user."""


def _provenance(
    provider: str | None,
    dataset: str | None,
    source_timestamp: datetime | None,
    collected_at: datetime | None,
) -> PerformanceProvenance:
    collected = collected_at or datetime.now(timezone.utc)
    return PerformanceProvenance(
        provider=provider or "market-pulse-demo",
        dataset=dataset or "demo-portfolio-events",
        source=f"{provider or 'market-pulse-demo'}/{dataset or 'demo-portfolio-events'}",
        data_level=DataLevel.DEMO,
        freshness=Freshness.STALE,
        source_timestamp=source_timestamp or collected,
        collected_at=collected,
        latency_ms=0,
        limitations=("Projeção informativa DEMO; não é recomendação financeira.",),
    )


class PostgresPortfolioDay27Service:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _connection(self):
        return psycopg.connect(self.settings.database_url)

    @staticmethod
    def _ensure_owned(connection, user_id: str, portfolio_id: str) -> None:
        if connection.execute(
            "SELECT 1 FROM portfolios WHERE id=%s AND user_id=%s", (portfolio_id, user_id)
        ).fetchone() is None:
            raise PortfolioReadModelNotFound

    def income(self, user_id: str, portfolio_id: str) -> list[PortfolioIncomeResponse]:
        today = date.today()
        with self._connection() as connection:
            self._ensure_owned(connection, user_id, portfolio_id)
            ledger_rows = connection.execute(
                "SELECT pe.id, i.canonical_id, i.name, pe.event_date, pe.gross_amount, "
                "pe.quantity, pe.currency, pe.created_at "
                "FROM portfolio_events pe LEFT JOIN instruments i ON i.id=pe.instrument_id "
                "WHERE pe.portfolio_id=%s AND pe.event_type='DIVIDEND' "
                "ORDER BY pe.event_date, pe.id",
                (portfolio_id,),
            ).fetchall()
            held_instruments = connection.execute(
                "SELECT DISTINCT instrument_id FROM portfolio_events "
                "WHERE portfolio_id=%s AND instrument_id IS NOT NULL",
                (portfolio_id,),
            ).fetchall()
            action_rows = connection.execute(
                "SELECT ca.id, i.canonical_id, i.name, ca.action_type, ca.status, "
                "ca.ex_date, ca.payment_date, ca.gross_amount_per_share, "
                "ca.net_amount_per_share, ca.currency, ca.split_ratio_from, "
                "ca.split_ratio_to, ca.source_timestamp, ca.collected_at, "
                "p.name, d.name "
                "FROM corporate_actions ca JOIN instruments i ON i.id=ca.instrument_id "
                "LEFT JOIN providers p ON p.id=ca.provider_id "
                "LEFT JOIN datasets d ON d.id=ca.dataset_id "
                "WHERE ca.instrument_id = ANY(%s) "
                "AND ca.action_type IN ('CASH_DIVIDEND','JCP','SPLIT','REVERSE_SPLIT') "
                "ORDER BY ca.ex_date NULLS LAST, ca.payment_date NULLS LAST, ca.id",
                ([row[0] for row in held_instruments],),
            ).fetchall()
        receipts = {(str(row[1]), row[3]) for row in ledger_rows}
        items: list[PortfolioIncomeResponse] = []
        for row in ledger_rows:
            event_date = row[3]
            items.append(
                PortfolioIncomeResponse(
                    portfolio_id=portfolio_id,
                    source_type=MarkerSourceType.LEDGER_EVENT,
                    source_id=str(row[0]),
                    canonical_id=row[1],
                    event_type=PortfolioIncomeType.DIVIDEND,
                    status=PortfolioIncomeStatus.APPLIED,
                    ex_date=event_date,
                    payment_date=event_date,
                    payer=row[2],
                    gross_amount_per_unit=row[4],
                    quantity=row[5],
                    currency=row[6],
                    provenance=_provenance("market-pulse-demo", "portfolio-ledger", row[7], row[7]),
                )
            )
        for row in action_rows:
            event_type = PortfolioIncomeType(row[3].replace("CASH_", ""))
            has_receipt = (row[1], row[6]) in receipts if row[6] is not None else False
            status = derive_income_status(
                payment_date=row[6],
                today=today,
                has_ledger_receipt=has_receipt,
                corporate_status=row[4],
            )
            items.append(
                PortfolioIncomeResponse(
                    portfolio_id=portfolio_id,
                    source_type=MarkerSourceType.CORPORATE_ACTION,
                    source_id=str(row[0]),
                    canonical_id=row[1],
                    event_type=event_type,
                    status=PortfolioIncomeStatus(status.value),
                    ex_date=row[5],
                    payment_date=row[6],
                    payer=row[2],
                    gross_amount_per_unit=row[7],
                    net_amount_per_unit=row[8],
                    currency=row[9],
                    split_ratio_from=row[10],
                    split_ratio_to=row[11],
                    provenance=_provenance(row[14], row[15], row[12], row[13]),
                )
            )
        return sorted(items, key=lambda item: (item.ex_date or date.max, item.source_id))

    def markers(self, user_id: str, portfolio_id: str) -> PortfolioEventMarkersResponse:
        with self._connection() as connection:
            self._ensure_owned(connection, user_id, portfolio_id)
            ledger_rows = connection.execute(
                "SELECT pe.id, pe.event_type, i.canonical_id, pe.occurred_at, "
                "pe.quantity, pe.gross_amount, pe.currency, pe.created_at "
                "FROM portfolio_events pe LEFT JOIN instruments i ON i.id=pe.instrument_id "
                "WHERE pe.portfolio_id=%s AND pe.event_type IN "
                "('BUY','SELL','CASH_DEPOSIT','CASH_WITHDRAWAL','DIVIDEND') "
                "ORDER BY pe.occurred_at, pe.id",
                (portfolio_id,),
            ).fetchall()
            action_rows = connection.execute(
                "SELECT ca.id, ca.action_type, i.canonical_id, i.currency, "
                "COALESCE(ca.effective_date, ca.ex_date, ca.payment_date), "
                "ca.gross_amount_per_share, ca.currency, ca.source_timestamp, "
                "ca.collected_at, p.name, d.name "
                "FROM corporate_actions ca JOIN instruments i ON i.id=ca.instrument_id "
                "LEFT JOIN providers p ON p.id=ca.provider_id "
                "LEFT JOIN datasets d ON d.id=ca.dataset_id "
                "WHERE ca.status IN ('CONFIRMED','CORRECTED') "
                "AND ca.instrument_id IN (SELECT DISTINCT instrument_id FROM portfolio_events "
                "WHERE portfolio_id=%s AND instrument_id IS NOT NULL) "
                "ORDER BY COALESCE(ca.effective_date, ca.ex_date, ca.payment_date), ca.id",
                (portfolio_id,),
            ).fetchall()
            ledger_ids = {str(row[0]) for row in ledger_rows}
            action_ids = {str(row[0]) for row in action_rows}
        markers: list[PortfolioEventMarkerResponse] = []
        for row in ledger_rows:
            markers.append(
                PortfolioEventMarkerResponse(
                    portfolio_id=portfolio_id,
                    source_type=MarkerSourceType.LEDGER_EVENT,
                    source_id=str(row[0]),
                    event_type=str(row[1]),
                    canonical_id=row[2] or f"cash.{str(row[6]).lower()}",
                    occurred_at=row[3],
                    quantity=row[4],
                    amount=row[5],
                    currency=row[6],
                    provenance=_provenance("market-pulse-demo", "portfolio-ledger", row[7], row[7]),
                )
            )
        for row in action_rows:
            occurred_at = datetime.combine(
                row[4] or date.today(), datetime.min.time(), timezone.utc
            )
            markers.append(
                PortfolioEventMarkerResponse(
                    portfolio_id=portfolio_id,
                    source_type=MarkerSourceType.CORPORATE_ACTION,
                    source_id=str(row[0]),
                    event_type=str(row[1]),
                    canonical_id=row[2],
                    occurred_at=occurred_at,
                    amount=row[5],
                    currency=row[6] or row[3],
                    provenance=_provenance(row[9], row[10], row[7], row[8]),
                )
            )
        validate_marker_references(
            [
                {"source_type": item.source_type.value, "source_id": item.source_id}
                for item in markers
            ],
            ledger_ids,
            action_ids,
        )
        return PortfolioEventMarkersResponse(portfolio_id=portfolio_id, items=markers)
