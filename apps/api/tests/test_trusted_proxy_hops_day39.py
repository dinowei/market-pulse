"""H-23 (ADR-020): client address behind a known number of trusted proxies."""

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

import app.core.client_ip as client_ip_module
from app.auth.service import InMemoryRateLimiter
from app.core.client_ip import client_ip
from app.core.config import Settings
from app.main import app


def _request(forwarded: list[str], peer: str = "10.0.0.9") -> Request:
    headers = [(b"x-forwarded-for", value.encode()) for value in forwarded]
    return Request({"type": "http", "headers": headers, "client": (peer, 1234)})


@pytest.fixture
def hops(monkeypatch):
    def use(count: int) -> None:
        settings = Settings(trusted_proxy_hops=count)
        monkeypatch.setattr(client_ip_module, "get_settings", lambda: settings)

    return use


def test_without_trusted_hops_the_header_is_ignored(hops) -> None:
    hops(0)
    assert client_ip(_request(["203.0.113.77"])) == "10.0.0.9"


def test_the_client_is_the_nth_entry_from_the_right(hops) -> None:
    hops(1)
    assert client_ip(_request(["203.0.113.77, 198.51.100.4"])) == "198.51.100.4"
    hops(2)
    assert client_ip(_request(["203.0.113.77, 198.51.100.4, 192.0.2.10"])) == "198.51.100.4"
    assert client_ip(_request(["203.0.113.77", "198.51.100.4, 192.0.2.10"])) == "198.51.100.4"


def test_prepended_entries_cannot_change_the_address(hops) -> None:
    hops(1)
    honest = client_ip(_request(["198.51.100.4"]))
    forged = client_ip(_request(["1.2.3.4, 5.6.7.8, 198.51.100.4"]))
    assert honest == forged == "198.51.100.4"


def test_short_or_invalid_headers_fall_back_to_the_peer(hops) -> None:
    hops(2)
    assert client_ip(_request(["198.51.100.4"])) == "10.0.0.9", "fewer entries than hops"
    assert client_ip(_request([])) == "10.0.0.9"
    hops(1)
    assert client_ip(_request(["not-an-ip"])) == "10.0.0.9"
    assert client_ip(_request(["2001:db8::1"])) == "2001:db8::1"


def test_rotating_forged_prefixes_do_not_buy_a_new_login_quota(hops) -> None:
    hops(1)
    limiter = InMemoryRateLimiter(max_attempts=3)
    app.state.rate_limiter = limiter
    try:
        client = TestClient(app)
        body = {"email": "nobody@example.invalid", "password": "Wrong-password-123"}
        statuses = [
            client.post(
                "/api/v1/auth/login",
                json=body,
                headers={"X-Forwarded-For": f"203.0.113.{attempt}, 198.51.100.4"},
            ).status_code
            for attempt in range(5)
        ]
        assert statuses[3:] == [429, 429], "the 4th attempt is still limited"
        assert set(limiter.counts) == {"rate_limit:auth:ip:198.51.100.4"}
    finally:
        app.state.rate_limiter = None


def test_the_setting_rejects_unreasonable_values() -> None:
    with pytest.raises(ValueError):
        Settings(trusted_proxy_hops=-1)
    with pytest.raises(ValueError):
        Settings(trusted_proxy_hops=6)
