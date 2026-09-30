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
        coverage_tier=CoverageTier.FUTURE_REVIEW,
        data_support_status=DataSupportStatus.METADATA_ONLY,
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
        coverage_tier=CoverageTier.FUTURE_REVIEW,
        data_support_status=DataSupportStatus.METADATA_ONLY,
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
