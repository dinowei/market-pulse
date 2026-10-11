"""ADR-025: provider registry, lifecycle, activation and precedence (no network, no keys)."""

from datetime import datetime, timedelta, timezone

import pytest

from app.providers.adapters import CANDIDATE_ADAPTERS
from app.providers.canonical import UnavailableReason
from app.providers.models import ProviderCapability, ProviderError
from app.providers.precedence import serve
from app.providers.registry import (
    PRECEDENCE,
    REGISTRY,
    ProviderStatus,
    activation_decision,
    can_transition,
    credential_presence,
    fallback_chain,
    get_entry,
)
from app.providers.resilience import (
    CircuitBreaker,
    RetryPolicy,
    backoff_delay,
    parse_retry_after,
)

NOW = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)


def test_no_provider_is_active_and_every_one_names_its_evidence() -> None:
    assert {entry.provider_id for entry in REGISTRY} == {
        "brapi",
        "hg_brasil",
        "twelve_data",
        "alpha_vantage",
        "open_exchange_rates",
        "massive",
        "b3_developers",
    }
    for entry in REGISTRY:
        assert entry.status not in {ProviderStatus.APPROVED, ProviderStatus.ACTIVE}, entry
        assert entry.license_status == "UNREVIEWED"
        assert entry.evidence and all(url.startswith("https://") for url in entry.evidence)
        assert not activation_decision(entry, {}).allowed


def test_registry_matches_the_existing_candidate_adapters() -> None:
    by_id = {entry.provider_id: entry for entry in REGISTRY}
    for adapter in CANDIDATE_ADAPTERS:
        entry = by_id[adapter.name]
        assert adapter.credential_env in entry.credential_envs
        assert adapter.enabled is False


def test_a_key_in_the_environment_never_activates_a_provider() -> None:
    environ = {name: "fake-not-a-key" for entry in REGISTRY for name in entry.credential_envs}
    for entry in REGISTRY:
        decision = activation_decision(entry, environ)
        assert not decision.allowed
        assert decision.reason in {
            UnavailableReason.DATASET_NOT_APPROVED,
            UnavailableReason.LICENSE_BLOCKED,
        }
    for capability, market in PRECEDENCE:
        assert fallback_chain(capability, market, environ) == ()


def test_credential_presence_never_returns_values() -> None:
    entry = get_entry("b3_developers")
    presence = credential_presence(entry, {"B3_DEVELOPERS_CLIENT_ID": "secret-value"})
    assert presence == {
        "B3_DEVELOPERS_CLIENT_ID": True,
        "B3_DEVELOPERS_CLIENT_SECRET": False,
        "B3_DEVELOPERS_TOKEN_URL": False,
    }
    assert "secret-value" not in repr(presence)


def test_lifecycle_moves_one_step_at_a_time_and_can_always_be_stopped() -> None:
    assert can_transition(ProviderStatus.UNREVIEWED, ProviderStatus.CANDIDATE)
    assert not can_transition(ProviderStatus.UNREVIEWED, ProviderStatus.ACTIVE)
    assert not can_transition(ProviderStatus.DOCUMENTED, ProviderStatus.APPROVED)
    assert can_transition(ProviderStatus.APPROVED, ProviderStatus.ACTIVE)
    assert can_transition(ProviderStatus.ACTIVE, ProviderStatus.PAUSED)
    assert can_transition(ProviderStatus.PAUSED, ProviderStatus.ACTIVE)
    for status in ProviderStatus:
        if status is not ProviderStatus.REVOKED:
            assert can_transition(status, ProviderStatus.REVOKED)
    assert not can_transition(ProviderStatus.REVOKED, ProviderStatus.UNREVIEWED)
    assert can_transition(ProviderStatus.BLOCKED, ProviderStatus.UNREVIEWED)


def test_precedence_only_names_providers_with_the_capability() -> None:
    for (capability, _market), order in PRECEDENCE.items():
        assert order, capability
        for provider_id in order:
            assert capability in get_entry(provider_id).capabilities, (capability, provider_id)


def test_serve_reports_why_nothing_served_while_providers_are_not_approved() -> None:
    calls: list[str] = []
    result, trace = serve(ProviderCapability.LATEST_QUOTE, "BR", calls.append)
    assert result is None and calls == [], "no network call without activation"
    assert trace.primary == "brapi"
    assert trace.served_by is None and not trace.fallback_used
    assert trace.reason is UnavailableReason.DATASET_NOT_APPROVED
    assert [attempt.outcome for attempt in trace.attempts] == ["DATASET_NOT_APPROVED"] * 2


def test_serve_falls_back_once_and_keeps_the_trace(monkeypatch) -> None:
    import app.providers.precedence as precedence
    from app.providers.registry import ActivationDecision

    monkeypatch.setattr(
        precedence,
        "activation_decision",
        lambda entry, environ=None: ActivationDecision(True, None),
    )

    def call(provider_id: str) -> str:
        if provider_id == "massive":
            raise ProviderError("PROVIDER_RATE_LIMIT", "limit", retryable=True)
        return f"quote-from-{provider_id}"

    breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=60, clock=lambda: 0.0)
    result, trace = serve(
        ProviderCapability.LATEST_QUOTE, "US", call, breakers={"massive": breaker}
    )
    assert result == "quote-from-twelve_data"
    assert (trace.primary, trace.served_by, trace.fallback_used) == ("massive", "twelve_data", True)
    assert [attempt.outcome for attempt in trace.attempts] == ["RATE_LIMITED", "SERVED"]
    assert breaker.state == CircuitBreaker.OPEN
    _, again = serve(ProviderCapability.LATEST_QUOTE, "US", call, breakers={"massive": breaker})
    assert again.attempts[0].outcome == "CIRCUIT_OPEN"


def test_retry_after_and_backoff() -> None:
    assert parse_retry_after("30", NOW) == 30.0
    assert parse_retry_after("99999", NOW) == 3600.0
    later = (NOW + timedelta(seconds=90)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    assert parse_retry_after(later, NOW) == 90.0
    assert parse_retry_after("soon", NOW) is None
    assert parse_retry_after(None, NOW) is None
    policy = RetryPolicy(max_attempts=3, base_delay_seconds=1, max_delay_seconds=4)
    assert backoff_delay(2, policy, retry_after=12.0) == 12.0
    assert 0 <= backoff_delay(5, policy) <= 4


def test_circuit_breaker_opens_and_half_opens() -> None:
    clock = {"now": 0.0}
    breaker = CircuitBreaker(failure_threshold=2, cooldown_seconds=30, clock=lambda: clock["now"])
    breaker.record_failure()
    assert breaker.allow_request()
    breaker.record_failure()
    assert breaker.state == CircuitBreaker.OPEN and not breaker.allow_request()
    clock["now"] = 31
    assert breaker.state == CircuitBreaker.HALF_OPEN and breaker.allow_request()
    breaker.record_failure()
    assert breaker.state == CircuitBreaker.OPEN
    clock["now"] = 62
    breaker.record_success()
    assert breaker.state == CircuitBreaker.CLOSED
    with pytest.raises(ValueError):
        CircuitBreaker(failure_threshold=0, cooldown_seconds=1)


def test_admin_registry_shows_presence_only_and_never_the_value(monkeypatch) -> None:
    from app.admin.system import _provider_registry

    monkeypatch.setenv("BRAPI_API_TOKEN", "FAKE-TOKEN-0002")
    items = {item.provider_id: item for item in _provider_registry()}
    assert len(items) == 7
    assert items["brapi"].credentials == {"BRAPI_API_TOKEN": True}
    assert items["brapi"].activation == "DATASET_NOT_APPROVED", "a key alone activates nothing"
    assert items["b3_developers"].activation == "LICENSE_BLOCKED"
    assert items["b3_developers"].blocked_reason
    dumped = "".join(item.model_dump_json() for item in items.values())
    assert "FAKE-TOKEN-0002" not in dumped
