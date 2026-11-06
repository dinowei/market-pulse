"""ADR-030: the world report states facts from quotes and never fills in a missing one."""

from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from app.contracts import PublicQuote
from app.instruments.catalog import MASTER_CATALOG
from app.main import app
from app.market_data.world_report import REGIONS, _summary, world_report
from app.providers.vendors import massive_news


def _quote(canonical_id: str, change: str | None, symbol: str = "X") -> PublicQuote:
    now = datetime.now(UTC)
    return PublicQuote(
        canonical_id=canonical_id,
        symbol=symbol,
        name=symbol,
        asset_type="ETF",
        currency="USD",
        price=None if change is None else Decimal("10"),
        change_percent=None if change is None else Decimal(change),
        data_level="DELAYED",
        freshness="UNAVAILABLE" if change is None else "FRESH",
        provider="test",
        dataset="test",
        timestamp_collected=now,
        session_date=date(2026, 11, 4),
        limitations=(),
        unavailable_reason="RATE_LIMITED" if change is None else None,
        request_id="r",
    )


def test_every_region_member_exists_in_the_catalog():
    ids = {entry.canonical_id for entry in MASTER_CATALOG}
    for spec in REGIONS:
        for canonical_id in (spec.main, *spec.members):
            assert canonical_id is None or canonical_id in ids, canonical_id


def _report(changes):
    return world_report(
        "r",
        quote=lambda cid, _r: _quote(cid, changes.get(cid), cid.split(".")[-1].upper()),
        news=lambda _t: (),
    )


def test_a_region_uses_its_etf_and_names_the_extremes_without_a_cause():
    report = _report(
        {"etf.us.listed.vgk": "-0.5", "etf.us.listed.ewg": "1.25", "etf.us.listed.ewu": "-2"}
    )
    europe = next(item for item in report.regions if item.id == "europa")
    assert europe.basis == "ETF" and europe.change_percent == Decimal("-0.5")
    assert "Queda de 0,50% (via ETF VGK)" in europe.summary
    assert "Maior alta: EWG +1,25%" in europe.summary
    assert "Maior queda: EWU -2,00%" in europe.summary
    assert "porque" not in europe.summary.lower()


def test_asia_is_a_declared_simple_average_of_what_has_data():
    report = _report({"etf.us.listed.ewj": "1", "etf.us.listed.fxi": "3"})
    asia = next(item for item in report.regions if item.id == "asia")
    assert asia.basis == "AVERAGE" and asia.change_percent == Decimal("2")
    assert asia.basis_label == "média simples de 2 ETFs"
    assert asia.members_with_data == 2 and "3 sem dado agora" in asia.summary


def test_no_data_is_never_zero():
    for region in _report({}).regions:
        assert region.change_percent is None and region.basis == "NONE"
        assert region.unavailable_reason == "RATE_LIMITED"
    assert _summary(None, "x", [], 0).startswith("Sem dados")


def test_currencies_get_no_meaningless_average():
    report = _report({"fx.global.usd-brl": "0.2", "crypto.global.btc-usd": "-3"})
    money = next(item for item in report.regions if item.id == "moedas")
    assert money.change_percent is None and money.members_with_data == 2


def test_malformed_news_is_left_out():
    article = {
        "title": "T",
        "publisher": {"name": "P"},
        "published_utc": "2026-11-04T10:00:00Z",
    }
    items = massive_news(
        {
            "results": [
                {**article, "article_url": "https://example.com/a"},
                {**article, "article_url": "javascript:alert(1)"},
                {"title": "sem fonte"},
            ]
        }
    )
    assert [item["url"] for item in items] == ["https://example.com/a"]


def test_the_endpoint_answers_without_news_outside_the_owner_session():
    body = TestClient(app).get("/api/v1/market-data/world-report").json()
    assert {region["id"] for region in body["regions"]} == {spec.id for spec in REGIONS}
    assert all(region["news"] == [] for region in body["regions"])
