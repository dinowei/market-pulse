"""Proventos and corporate events of one instrument (Day 41).

Outside the local DEMO there is no approved dataset, so the answer is UNAVAILABLE with a
reason. In the DEMO, only rows whose dataset passes the license gate are returned, and a
withheld row turns the whole answer UNAVAILABLE instead of showing a partial list as
complete.
"""

from app.contracts import (
    InstrumentCorporateAction,
    InstrumentCorporateActionsResponse,
    PerformanceProvenance,
)
from app.core.config import get_settings
from app.instruments.catalog import get_catalog
from app.providers.models import DataLevel, Freshness

DEMO_EVENTS_LIMITATION = (
    "Eventos sintéticos DEMO; não representam proventos ou eventos corporativos reais."
)


def _unavailable(
    canonical_id: str, reason: str, request_id: str
) -> InstrumentCorporateActionsResponse:
    return InstrumentCorporateActionsResponse(
        canonical_id=canonical_id,
        availability="UNAVAILABLE",
        unavailable_reason=reason,
        items=[],
        limitations=("Nenhum dataset aprovado de proventos e eventos para este instrumento.",),
        request_id=request_id,
    )


def instrument_corporate_actions(
    canonical_id: str, request_id: str
) -> InstrumentCorporateActionsResponse:
    if not any(entry.canonical_id == canonical_id for entry in get_catalog()):
        raise KeyError(canonical_id)
    if not get_settings().demo_enabled:
        return _unavailable(canonical_id, "DATASET_NOT_APPROVED", request_id)
    from app.demo.read_models import corporate_action_rows

    try:
        rows, withheld = corporate_action_rows(canonical_id)
    except Exception:
        return _unavailable(canonical_id, "SOURCE_UNAVAILABLE", request_id)
    if withheld:
        return _unavailable(canonical_id, "LICENSE_BLOCKED", request_id)
    items = [
        InstrumentCorporateAction(
            action_type=row["action_type"],
            status=row["status"],
            ex_date=row["ex_date"],
            payment_date=row["payment_date"],
            effective_date=row["effective_date"],
            gross_amount_per_share=row["gross_amount_per_share"],
            net_amount_per_share=row["net_amount_per_share"],
            currency=row["currency"],
            split_ratio_from=row["split_ratio_from"],
            split_ratio_to=row["split_ratio_to"],
            provenance=PerformanceProvenance(
                provider=row["provider"],
                dataset=row["dataset"],
                source=f"{row['provider']}/{row['dataset']}",
                data_level=DataLevel.DEMO,
                freshness=Freshness.STALE,
                source_timestamp=row["source_timestamp"],
                collected_at=row["collected_at"],
                latency_ms=max(
                    0, int((row["collected_at"] - row["source_timestamp"]).total_seconds() * 1000)
                ),
                limitations=(DEMO_EVENTS_LIMITATION,),
            ),
        )
        for row in rows
    ]
    return InstrumentCorporateActionsResponse(
        canonical_id=canonical_id,
        availability="AVAILABLE",
        items=items,
        limitations=(DEMO_EVENTS_LIMITATION,),
        request_id=request_id,
    )
