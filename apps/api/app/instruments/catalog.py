from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.config import get_settings


class CatalogStatus(StrEnum):
    ACTIVE = "ACTIVE"
    CANDIDATE = "CANDIDATE"
    DEPRECATED = "DEPRECATED"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class CoverageTier(StrEnum):
    P0_OPERATIONAL = "P0_OPERATIONAL"
    P0_CATALOG = "P0_CATALOG"
    P1 = "P1"
    P2 = "P2"
    FUTURE_REVIEW = "FUTURE_REVIEW"


class DataSupportStatus(StrEnum):
    METADATA_ONLY = "METADATA_ONLY"
    PROVIDER_PENDING = "PROVIDER_PENDING"
    LICENSE_PENDING = "LICENSE_PENDING"
    DATA_AVAILABLE_APPROVED = "DATA_AVAILABLE_APPROVED"
    UNAVAILABLE = "UNAVAILABLE"


class InstrumentCatalogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    canonical_id: str = Field(pattern=r"^[a-z0-9]+(?:[.-][a-z0-9]+)+$")
    symbol: str = Field(min_length=1)
    display_symbol: str = Field(min_length=1)
    name: str = Field(min_length=1)
    instrument_type: str = Field(min_length=1)
    exchange: str | None = None
    venue: str | None = None
    country: str | None = None
    region: str | None = None
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    timezone: str = Field(min_length=1)
    aliases: tuple[str, ...] = ()
    catalog_status: CatalogStatus
    coverage_tier: CoverageTier
    data_support_status: DataSupportStatus
    notes: str | None = None

    @model_validator(mode="after")
    def mutual_funds_are_blocked(self) -> "InstrumentCatalogEntry":
        if self.instrument_type.upper() == "MUTUAL_FUND" and not (
            self.catalog_status is CatalogStatus.OUT_OF_SCOPE
            and self.data_support_status is DataSupportStatus.UNAVAILABLE
        ):
            raise ValueError("MUTUAL_FUND is blocked until licensed coverage is approved")
        return self


MASTER_CATALOG: tuple[InstrumentCatalogEntry, ...] = (
    InstrumentCatalogEntry(
        canonical_id="equity.br.b3.petr4",
        symbol="PETR4",
        display_symbol="PETR4",
        name="Petrobras PN",
        instrument_type="EQUITY",
        exchange="B3",
        venue="B3",
        country="BR",
        region="BR",
        currency="BRL",
        timezone="America/Sao_Paulo",
        catalog_status=CatalogStatus.ACTIVE,
        coverage_tier=CoverageTier.P0_OPERATIONAL,
        data_support_status=DataSupportStatus.PROVIDER_PENDING,
        notes="Metadados aprovados para o universo operacional; preço depende de provider/licença.",
    ),
    InstrumentCatalogEntry(
        canonical_id="equity.us.nasdaq.aapl",
        symbol="AAPL",
        display_symbol="AAPL",
        name="Apple Inc.",
        instrument_type="EQUITY",
        exchange="NASDAQ",
        venue="NASDAQ",
        country="US",
        region="US",
        currency="USD",
        timezone="America/New_York",
        catalog_status=CatalogStatus.ACTIVE,
        coverage_tier=CoverageTier.P0_OPERATIONAL,
        data_support_status=DataSupportStatus.PROVIDER_PENDING,
    ),
    InstrumentCatalogEntry(
        canonical_id="fii.br.b3.mxrf11",
        symbol="MXRF11",
        display_symbol="MXRF11",
        name="Maxi Renda FII",
        instrument_type="FII",
        exchange="B3",
        venue="B3",
        country="BR",
        region="BR",
        currency="BRL",
        timezone="America/Sao_Paulo",
        catalog_status=CatalogStatus.CANDIDATE,
        coverage_tier=CoverageTier.P0_CATALOG,
        data_support_status=DataSupportStatus.LICENSE_PENDING,
    ),
    InstrumentCatalogEntry(
        canonical_id="crypto.global.btc-usd",
        symbol="BTC-USD",
        display_symbol="BTC/USD",
        name="Bitcoin",
        instrument_type="CRYPTO",
        country="GLOBAL",
        region="GLOBAL",
        currency="USD",
        timezone="UTC",
        aliases=("BTC/USD",),
        catalog_status=CatalogStatus.CANDIDATE,
        coverage_tier=CoverageTier.P1,
        data_support_status=DataSupportStatus.PROVIDER_PENDING,
    ),
    InstrumentCatalogEntry(
        canonical_id="bdr.br.b3.aapl34",
        symbol="AAPL34",
        display_symbol="AAPL34",
        name="Apple BDR",
        instrument_type="BDR",
        exchange="B3",
        venue="B3",
        country="BR",
        region="BR",
        currency="BRL",
        timezone="America/Sao_Paulo",
        catalog_status=CatalogStatus.CANDIDATE,
        coverage_tier=CoverageTier.P1,
        data_support_status=DataSupportStatus.PROVIDER_PENDING,
    ),
    # ADR-023 named them with metadata only. ADR-029: the owner's private staging prices them
    # through brapi (ADR-027); outside that session they stay UNAVAILABLE, as before.
    InstrumentCatalogEntry(
        canonical_id="equity.br.b3.vale3",
        symbol="VALE3",
        display_symbol="VALE3",
        name="Vale ON",
        instrument_type="EQUITY",
        exchange="B3",
        venue="B3",
        country="BR",
        region="BR",
        currency="BRL",
        timezone="America/Sao_Paulo",
        catalog_status=CatalogStatus.CANDIDATE,
        coverage_tier=CoverageTier.P1,
        data_support_status=DataSupportStatus.PROVIDER_PENDING,
    ),
    InstrumentCatalogEntry(
        canonical_id="equity.br.b3.cmin3",
        symbol="CMIN3",
        display_symbol="CMIN3",
        name="CSN Mineração ON",
        instrument_type="EQUITY",
        exchange="B3",
        venue="B3",
        country="BR",
        region="BR",
        currency="BRL",
        timezone="America/Sao_Paulo",
        catalog_status=CatalogStatus.CANDIDATE,
        coverage_tier=CoverageTier.P1,
        data_support_status=DataSupportStatus.PROVIDER_PENDING,
    ),
    # ADR-029: instruments the owner's plans serve (probed 2026-10-13). Priced only in the
    # owner's private session (ADR-027); everywhere else they are UNAVAILABLE.
    InstrumentCatalogEntry(
        canonical_id="equity.br.b3.itub4",
        symbol="ITUB4",
        display_symbol="ITUB4",
        name="Itaú Unibanco PN",
        instrument_type="EQUITY",
        exchange="B3",
        venue="B3",
        country="BR",
        region="BR",
        currency="BRL",
        timezone="America/Sao_Paulo",
        catalog_status=CatalogStatus.CANDIDATE,
        coverage_tier=CoverageTier.P1,
        data_support_status=DataSupportStatus.PROVIDER_PENDING,
    ),
    InstrumentCatalogEntry(
        canonical_id="equity.br.b3.wege3",
        symbol="WEGE3",
        display_symbol="WEGE3",
        name="WEG ON",
        instrument_type="EQUITY",
        exchange="B3",
        venue="B3",
        country="BR",
        region="BR",
        currency="BRL",
        timezone="America/Sao_Paulo",
        catalog_status=CatalogStatus.CANDIDATE,
        coverage_tier=CoverageTier.P1,
        data_support_status=DataSupportStatus.PROVIDER_PENDING,
    ),
    InstrumentCatalogEntry(
        canonical_id="etf.br.b3.bova11",
        symbol="BOVA11",
        display_symbol="BOVA11",
        name="iShares Ibovespa ETF",
        instrument_type="ETF",
        exchange="B3",
        venue="B3",
        country="BR",
        region="BR",
        currency="BRL",
        timezone="America/Sao_Paulo",
        catalog_status=CatalogStatus.CANDIDATE,
        coverage_tier=CoverageTier.P1,
        data_support_status=DataSupportStatus.PROVIDER_PENDING,
    ),
    InstrumentCatalogEntry(
        canonical_id="equity.us.nasdaq.msft",
        symbol="MSFT",
        display_symbol="MSFT",
        name="Microsoft Corporation",
        instrument_type="EQUITY",
        exchange="NASDAQ",
        venue="NASDAQ",
        country="US",
        region="US",
        currency="USD",
        timezone="America/New_York",
        catalog_status=CatalogStatus.CANDIDATE,
        coverage_tier=CoverageTier.P1,
        data_support_status=DataSupportStatus.PROVIDER_PENDING,
    ),
    InstrumentCatalogEntry(
        canonical_id="equity.us.nasdaq.nvda",
        symbol="NVDA",
        display_symbol="NVDA",
        name="NVIDIA Corporation",
        instrument_type="EQUITY",
        exchange="NASDAQ",
        venue="NASDAQ",
        country="US",
        region="US",
        currency="USD",
        timezone="America/New_York",
        catalog_status=CatalogStatus.CANDIDATE,
        coverage_tier=CoverageTier.P1,
        data_support_status=DataSupportStatus.PROVIDER_PENDING,
    ),
    InstrumentCatalogEntry(
        canonical_id="etf.us.nysearca.spy",
        symbol="SPY",
        display_symbol="SPY",
        name="SPDR S&P 500 ETF Trust",
        instrument_type="ETF",
        exchange="NYSE Arca",
        venue="NYSE Arca",
        country="US",
        region="US",
        currency="USD",
        timezone="America/New_York",
        catalog_status=CatalogStatus.CANDIDATE,
        coverage_tier=CoverageTier.P1,
        data_support_status=DataSupportStatus.PROVIDER_PENDING,
    ),
    InstrumentCatalogEntry(
        canonical_id="crypto.global.eth-usd",
        symbol="ETH-USD",
        display_symbol="ETH/USD",
        name="Ethereum",
        instrument_type="CRYPTO",
        country="GLOBAL",
        region="GLOBAL",
        currency="USD",
        timezone="UTC",
        aliases=("ETH/USD",),
        catalog_status=CatalogStatus.CANDIDATE,
        coverage_tier=CoverageTier.P1,
        data_support_status=DataSupportStatus.PROVIDER_PENDING,
    ),
    InstrumentCatalogEntry(
        canonical_id="fx.global.usd-brl",
        symbol="USD-BRL",
        display_symbol="USD/BRL",
        name="Dólar americano / Real",
        instrument_type="FX",
        country="GLOBAL",
        region="GLOBAL",
        currency="BRL",
        timezone="UTC",
        aliases=("USD/BRL", "USDBRL"),
        catalog_status=CatalogStatus.CANDIDATE,
        coverage_tier=CoverageTier.P1,
        data_support_status=DataSupportStatus.PROVIDER_PENDING,
    ),
    InstrumentCatalogEntry(
        canonical_id="fx.global.eur-usd",
        symbol="EUR-USD",
        display_symbol="EUR/USD",
        name="Euro / Dólar americano",
        instrument_type="FX",
        country="GLOBAL",
        region="GLOBAL",
        currency="USD",
        timezone="UTC",
        aliases=("EUR/USD", "EURUSD"),
        catalog_status=CatalogStatus.CANDIDATE,
        coverage_tier=CoverageTier.P1,
        data_support_status=DataSupportStatus.PROVIDER_PENDING,
    ),
    InstrumentCatalogEntry(
        canonical_id="commodity.global.xau-usd",
        symbol="XAU-USD",
        display_symbol="XAU/USD",
        name="Ouro à vista (onça troy)",
        instrument_type="COMMODITY",
        country="GLOBAL",
        region="GLOBAL",
        currency="USD",
        timezone="UTC",
        aliases=("XAU/USD", "Ouro"),
        catalog_status=CatalogStatus.CANDIDATE,
        coverage_tier=CoverageTier.P1,
        data_support_status=DataSupportStatus.PROVIDER_PENDING,
    ),
)

P0_OPERATIONAL_UNIVERSE = frozenset({"equity.br.b3.petr4", "equity.us.nasdaq.aapl"})
FUTURE_CANDIDATE_UNIVERSE = frozenset(
    entry.canonical_id
    for entry in MASTER_CATALOG
    if entry.canonical_id not in P0_OPERATIONAL_UNIVERSE
)


def get_catalog() -> tuple[InstrumentCatalogEntry, ...]:
    if get_settings().demo_enabled:
        try:
            from app.demo.read_models import catalog_entries

            return catalog_entries()
        except Exception:
            return MASTER_CATALOG
    return MASTER_CATALOG


def search_catalog(query: str) -> list[InstrumentCatalogEntry]:
    normalized = query.strip().casefold()
    if not normalized:
        return []
    return [
        entry
        for entry in get_catalog()
        if normalized in entry.symbol.casefold()
        or normalized in entry.display_symbol.casefold()
        or normalized in entry.name.casefold()
        or normalized in entry.canonical_id.casefold()
        or any(normalized in alias.casefold() for alias in entry.aliases)
    ]
