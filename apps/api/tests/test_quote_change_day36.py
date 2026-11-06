"""Day 36: a quote without a previous close reports an unknown change, never an invented zero.

A zero change would render as FLAT (directive section 9) and state a fact nobody measured
(integrity policy: never fill an absent value).
"""

from fastapi.testclient import TestClient

from app.main import app


def test_quote_without_previous_close_has_no_change() -> None:
    body = TestClient(app).get("/api/v1/market-data/quotes/equity.br.b3.petr4").json()
    assert body["price"] is not None
    assert body["change"] is None
    assert body["change_percent"] is None
