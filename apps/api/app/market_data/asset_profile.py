"""Everything the sources say about one asset (ADR-032), each fact with its source.

Facts are copied, never computed or scored: a field a source does not send is not listed. The
page shows them as reference for study; nothing here is an opinion on the asset.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.contracts import AssetDividend, AssetFact, AssetProfileResponse, WorldNewsItem
from app.market_data import live_data

PRICE = "Faixa de preço"
SIZE = "Tamanho e negociação"
RESULTS = "Indicadores da fonte"
COMPANY = "Empresa"

# Source field -> (label, kind, group). Percent fields arrive as fractions and are scaled once.
BRAPI_QUOTE = {
    "regularMarketOpen": ("Abertura", "MONEY", PRICE),
    "regularMarketDayHigh": ("Máxima do dia", "MONEY", PRICE),
    "regularMarketDayLow": ("Mínima do dia", "MONEY", PRICE),
    "regularMarketPreviousClose": ("Fechamento anterior", "MONEY", PRICE),
    "fiftyTwoWeekHigh": ("Máxima de 52 semanas", "MONEY", PRICE),
    "fiftyTwoWeekLow": ("Mínima de 52 semanas", "MONEY", PRICE),
    "regularMarketVolume": ("Volume do dia", "INTEGER", SIZE),
    "marketCap": ("Valor de mercado", "MONEY", SIZE),
    "priceEarnings": ("Preço/lucro (P/L)", "NUMBER", RESULTS),
    "earningsPerShare": ("Lucro por ação", "MONEY", RESULTS),
}
BRAPI_STATS = {
    "enterpriseValue": ("Valor da firma", "MONEY", SIZE),
    "sharesOutstanding": ("Ações em circulação", "INTEGER", SIZE),
    "floatShares": ("Ações em livre negociação", "INTEGER", SIZE),
    "bookValue": ("Valor patrimonial por ação", "MONEY", RESULTS),
    "priceToBook": ("Preço/valor patrimonial", "NUMBER", RESULTS),
    "forwardPE": ("P/L projetado pela fonte", "NUMBER", RESULTS),
    "pegRatio": ("Índice PEG", "NUMBER", RESULTS),
    "beta": ("Beta", "NUMBER", RESULTS),
    "profitMargins": ("Margem de lucro", "PERCENT", RESULTS),
    "earningsQuarterlyGrowth": ("Crescimento trimestral do lucro", "PERCENT", RESULTS),
    "netIncomeToCommon": ("Lucro líquido", "MONEY", RESULTS),
    "enterpriseToRevenue": ("Valor da firma/receita", "NUMBER", RESULTS),
    "enterpriseToEbitda": ("Valor da firma/EBITDA", "NUMBER", RESULTS),
    "52WeekChange": ("Variação em 52 semanas", "PERCENT", PRICE),
    "ytdReturn": ("Retorno no ano", "PERCENT", PRICE),
    "heldPercentInsiders": ("Em mãos de controladores", "PERCENT", SIZE),
    "heldPercentInstitutions": ("Em mãos de instituições", "PERCENT", SIZE),
    "lastDividendValue": ("Último provento por ação", "MONEY", RESULTS),
}
BRAPI_COMPANY = {
    "sectorDisp": ("Setor", "TEXT", COMPANY),
    "industryDisp": ("Indústria", "TEXT", COMPANY),
    "listingSegment": ("Segmento de listagem", "TEXT", COMPANY),
    "fullTimeEmployees": ("Funcionários", "INTEGER", COMPANY),
    "startDate": ("Início das atividades", "DATE", COMPANY),
}
TWELVE_QUOTE = {
    "open": ("Abertura", "MONEY", PRICE),
    "high": ("Máxima do dia", "MONEY", PRICE),
    "low": ("Mínima do dia", "MONEY", PRICE),
    "previous_close": ("Fechamento anterior", "MONEY", PRICE),
    "volume": ("Volume do dia", "INTEGER", SIZE),
    "average_volume": ("Volume médio", "INTEGER", SIZE),
}
TWELVE_RANGE = {
    "high": ("Máxima de 52 semanas", "MONEY", PRICE),
    "low": ("Mínima de 52 semanas", "MONEY", PRICE),
}
MASSIVE_DETAILS = {
    "market_cap": ("Valor de mercado", "MONEY", SIZE),
    "share_class_shares_outstanding": ("Ações em circulação", "INTEGER", SIZE),
    "sic_description": ("Atividade (SIC)", "TEXT", COMPANY),
    "primary_exchange": ("Bolsa principal", "TEXT", COMPANY),
    "total_employees": ("Funcionários", "INTEGER", COMPANY),
    "list_date": ("Listada desde", "DATE", COMPANY),
}

LIMITATIONS = (
    "Fatos copiados das fontes, sem cálculo nem opinião deste site. Resumo da empresa no "
    "idioma da fonte.",
    "Indicadores da fonte podem estar defasados; a data de referência é a de cada fonte.",
    "Conteúdo informativo para estudo; não é recomendação de investimento.",
)


def _clean(value: Any, kind: str) -> str | None:
    if value is None or isinstance(value, bool | dict | list):
        return None
    if kind == "TEXT":
        return str(value).strip() or None
    if kind == "DATE":
        text = str(value)[:10]
        try:
            return date.fromisoformat(text).isoformat()
        except ValueError:
            return None
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        return None
    if not number.is_finite():
        return None
    return str(number * 100) if kind == "PERCENT" else str(number)


def _facts(
    data: Mapping[str, Any], fields: Mapping[str, tuple[str, str, str]], source: str
) -> list[AssetFact]:
    facts = []
    for key, (label, kind, group) in fields.items():
        value = _clean(data.get(key), kind)
        if value is not None:
            facts.append(
                AssetFact(key=key, label=label, value=value, kind=kind, group=group, source=source)
            )
    return facts


def _first_result(section: Any) -> Mapping[str, Any]:
    results = section.get("results") if isinstance(section, Mapping) else None
    if isinstance(results, list) and results and isinstance(results[0], Mapping):
        return results[0]
    return results if isinstance(results, Mapping) else {}


def _day(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _dividend(label: Any, amount: Any, currency: Any, ex: Any, pay: Any, source: str):
    try:
        value = Decimal(str(amount))
    except InvalidOperation:
        return None
    if not value.is_finite() or value <= 0:
        return None
    return AssetDividend(
        label=str(label or "Provento"),
        amount=value,
        currency=str(currency or "BRL").upper(),
        ex_date=_day(ex),
        pay_date=_day(pay),
        source=source,
    )


def real_asset_profile(canonical_id: str, request_id: str) -> AssetProfileResponse:
    sections = live_data.live_profile(canonical_id)
    facts: list[AssetFact] = []
    summary = summary_source = website = logo = None
    dividends: list[AssetDividend] = []
    instrument = live_data.LIVE_INSTRUMENTS.get(canonical_id)

    if "brapi" in sections:
        data = _first_result(sections["brapi"])
        profile = (
            data.get("summaryProfile") if isinstance(data.get("summaryProfile"), Mapping) else {}
        )
        stats = data.get("defaultKeyStatistics")
        stats = stats if isinstance(stats, Mapping) else {}
        facts += _facts(data, BRAPI_QUOTE, "brapi")
        facts += _facts(stats, BRAPI_STATS, "brapi")
        facts += _facts(profile, BRAPI_COMPANY, "brapi")
        if isinstance(data.get("logourl"), str) and data["logourl"].startswith(
            "https://icons.brapi.dev/"
        ):
            logo = data["logourl"]
        if isinstance(profile.get("longBusinessSummary"), str):
            summary, summary_source = profile["longBusinessSummary"], "brapi"
        if isinstance(profile.get("website"), str) and profile["website"].startswith("https://"):
            website = profile["website"]
        history = data.get("dividendsData")
        rows = history.get("cashDividends") if isinstance(history, Mapping) else None
        for row in (rows or [])[:12]:
            if isinstance(row, Mapping):
                item = _dividend(
                    row.get("label"),
                    row.get("rate"),
                    data.get("currency"),
                    row.get("exDate") or row.get("lastDatePrior"),
                    row.get("paymentDate"),
                    "brapi",
                )
                if item:
                    dividends.append(item)
    if "twelve_quote" in sections and isinstance(sections["twelve_quote"], Mapping):
        data = sections["twelve_quote"]
        facts += _facts(data, TWELVE_QUOTE, "twelve_data")
        if isinstance(data.get("fifty_two_week"), Mapping):
            facts += _facts(data["fifty_two_week"], TWELVE_RANGE, "twelve_data")
    if "massive_details" in sections:
        data = _first_result(sections["massive_details"])
        have = {fact.key for fact in facts}
        facts += [fact for fact in _facts(data, MASSIVE_DETAILS, "massive") if fact.key not in have]
        if isinstance(data.get("description"), str) and not summary:
            summary, summary_source = data["description"], "massive"
        if isinstance(data.get("homepage_url"), str) and data["homepage_url"].startswith(
            "https://"
        ):
            website = website or data["homepage_url"]
    twelve_logo = sections.get("twelve_logo")
    if isinstance(twelve_logo, Mapping) and str(twelve_logo.get("url", "")).startswith(
        "https://api.twelvedata.com/logo/"
    ):
        logo = logo or twelve_logo["url"]
    if "massive_dividends" in sections and isinstance(sections["massive_dividends"], Mapping):
        rows = sections["massive_dividends"].get("results")
        for row in rows if isinstance(rows, list) else []:
            if isinstance(row, Mapping):
                item = _dividend(
                    "Dividendo",
                    row.get("cash_amount"),
                    row.get("currency"),
                    row.get("ex_dividend_date"),
                    row.get("pay_date"),
                    "massive",
                )
                if item:
                    dividends.append(item)

    news: list[WorldNewsItem] = []
    if instrument is not None and "massive" in instrument.symbols:
        news = [
            WorldNewsItem(**item) for item in live_data.live_news(instrument.symbols["massive"])
        ]
    empty = not (facts or summary or dividends or news)
    return AssetProfileResponse(
        canonical_id=canonical_id,
        facts=facts,
        summary=summary,
        summary_source=summary_source,
        website=website,
        logo_url=logo,
        dividends=dividends,
        news=news,
        limitations=list(LIMITATIONS),
        unavailable_reason="UNAVAILABLE" if empty else None,
        request_id=request_id,
    )


def empty_asset_profile(canonical_id: str, request_id: str, reason: str) -> AssetProfileResponse:
    return AssetProfileResponse(
        canonical_id=canonical_id,
        facts=[],
        dividends=[],
        news=[],
        limitations=[],
        unavailable_reason=reason,
        request_id=request_id,
    )
