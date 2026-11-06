"""Precedence and controlled fallback across providers (ADR-025).

One answer comes from exactly one provider: a series is never stitched from several sources.
The trace says which provider was primary, which one served, and why the others did not.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TypeVar

from app.providers.canonical import UnavailableReason
from app.providers.models import ProviderCapability
from app.providers.registry import (
    PRECEDENCE,
    ActivationDecision,
    ProviderRegistryEntry,
    activation_decision,
    get_entry,
)
from app.providers.resilience import CircuitBreaker
from app.providers.vendors import reason_for_error

T = TypeVar("T")

# When nothing served, the most actionable reason is reported first.
_REASON_PRIORITY = (
    UnavailableReason.RATE_LIMITED,
    UnavailableReason.SOURCE_ERROR,
    UnavailableReason.SCHEMA_UNSUPPORTED,
    UnavailableReason.PROVIDER_NOT_CONFIGURED,
    UnavailableReason.LICENSE_BLOCKED,
    UnavailableReason.DATASET_NOT_APPROVED,
    UnavailableReason.UNAVAILABLE,
)
# A refusal of one query (outside the plan, unreadable payload) says nothing about the
# provider's health, so it does not count toward opening its circuit (ADR-029).
QUERY_REFUSALS = frozenset(
    {UnavailableReason.LICENSE_BLOCKED, UnavailableReason.SCHEMA_UNSUPPORTED}
)


@dataclass(frozen=True)
class Attempt:
    provider_id: str
    outcome: str


@dataclass(frozen=True)
class FallbackTrace:
    capability: ProviderCapability
    market: str
    primary: str | None
    served_by: str | None
    attempts: tuple[Attempt, ...]
    reason: UnavailableReason | None

    @property
    def fallback_used(self) -> bool:
        return self.served_by is not None and self.served_by != self.primary


def serve(
    capability: ProviderCapability,
    market: str,
    call: Callable[[str], T],
    *,
    environ: Mapping[str, str] | None = None,
    breakers: Mapping[str, CircuitBreaker] | None = None,
    decide: Callable[
        [ProviderRegistryEntry, Mapping[str, str] | None], ActivationDecision
    ] = activation_decision,
    order: tuple[str, ...] | None = None,
) -> tuple[T | None, FallbackTrace]:
    order = tuple(
        provider_id
        for provider_id in (order or PRECEDENCE.get((capability, market), ()))
        if capability in get_entry(provider_id).capabilities
    )
    attempts: list[Attempt] = []
    reasons: list[UnavailableReason] = []
    for provider_id in order:
        decision = decide(get_entry(provider_id), environ)
        if not decision.allowed:
            reason = decision.reason or UnavailableReason.LICENSE_BLOCKED
            attempts.append(Attempt(provider_id, reason.value))
            reasons.append(reason)
            continue
        breaker = (breakers or {}).get(provider_id)
        if breaker and not breaker.allow_request():
            attempts.append(Attempt(provider_id, "CIRCUIT_OPEN"))
            reasons.append(UnavailableReason.SOURCE_ERROR)
            continue
        try:
            result = call(provider_id)
        except Exception as error:  # noqa: BLE001 - every failure becomes a public reason
            reason = reason_for_error(error)
            attempts.append(Attempt(provider_id, reason.value))
            reasons.append(reason)
            if breaker and reason not in QUERY_REFUSALS:
                breaker.record_failure()
            continue
        if breaker:
            breaker.record_success()
        attempts.append(Attempt(provider_id, "SERVED"))
        trace = FallbackTrace(
            capability, market, order[0] if order else None, provider_id, tuple(attempts), None
        )
        return result, trace
    reason = next(
        (item for item in _REASON_PRIORITY if item in reasons), UnavailableReason.UNAVAILABLE
    )
    return None, FallbackTrace(
        capability, market, order[0] if order else None, None, tuple(attempts), reason
    )
