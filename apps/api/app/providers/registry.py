"""Provider registry and lifecycle (ADR-025).

The registry is code, reviewed in pull requests: a provider is used only when its lifecycle
status is ACTIVE, every credential is present, and the dataset license passes the
LicenseService. A key in the environment never activates anything by itself.

Facts below were checked on the official pages listed in `evidence` on 2026-10-11. Unknown
terms stay None (not stated by the source) and are never filled with an assumption.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

from app.providers.canonical import UnavailableReason
from app.providers.models import ProviderCapability


class ProviderStatus(StrEnum):
    UNREVIEWED = "UNREVIEWED"
    CANDIDATE = "CANDIDATE"
    DOCUMENTED = "DOCUMENTED"
    CONFIGURED = "CONFIGURED"
    INTEGRATION_TESTED = "INTEGRATION_TESTED"
    LICENSE_REVIEW_PENDING = "LICENSE_REVIEW_PENDING"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    BLOCKED = "BLOCKED"
    REVOKED = "REVOKED"


_FORWARD = (
    ProviderStatus.UNREVIEWED,
    ProviderStatus.CANDIDATE,
    ProviderStatus.DOCUMENTED,
    ProviderStatus.CONFIGURED,
    ProviderStatus.INTEGRATION_TESTED,
    ProviderStatus.LICENSE_REVIEW_PENDING,
    ProviderStatus.APPROVED,
    ProviderStatus.ACTIVE,
)


def can_transition(current: ProviderStatus, target: ProviderStatus) -> bool:
    """One step forward at a time; pause/resume; block, revoke or re-review from anywhere."""

    if current is target:
        return False
    if target in {ProviderStatus.BLOCKED, ProviderStatus.REVOKED}:
        return current is not ProviderStatus.REVOKED
    if current is ProviderStatus.REVOKED:
        return False
    if target is ProviderStatus.UNREVIEWED:
        return current is ProviderStatus.BLOCKED
    if current is ProviderStatus.ACTIVE:
        return target is ProviderStatus.PAUSED
    if current is ProviderStatus.PAUSED:
        return target is ProviderStatus.ACTIVE
    if current in _FORWARD and target in _FORWARD:
        return _FORWARD.index(target) == _FORWARD.index(current) + 1
    return False


@dataclass(frozen=True)
class ProviderRegistryEntry:
    provider_id: str
    display_name: str
    status: ProviderStatus
    markets: tuple[str, ...]
    capabilities: frozenset[ProviderCapability]
    credential_envs: tuple[str, ...]
    auth: str
    base_url: str
    endpoints: Mapping[str, str]
    rate_limits: str
    error_handling: str
    license_status: str
    commercial_use: str | None
    redistribution: str | None
    storage: str | None
    attribution: str | None
    verified_on: date
    evidence: tuple[str, ...]
    divergences: tuple[str, ...] = ()
    blocked_reason: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)


VERIFIED_ON = date(2026, 10, 11)

REGISTRY: tuple[ProviderRegistryEntry, ...] = (
    ProviderRegistryEntry(
        provider_id="brapi",
        display_name="brapi",
        status=ProviderStatus.DOCUMENTED,
        markets=("BR",),
        capabilities=frozenset(
            {
                ProviderCapability.LATEST_QUOTE,
                ProviderCapability.HISTORICAL_BARS,
                ProviderCapability.DIVIDENDS,
            }
        ),
        credential_envs=("BRAPI_API_TOKEN",),
        auth="Header Authorization: Bearer <token>",
        base_url="https://brapi.dev/api",
        endpoints={
            "latest_quote": "GET /v2/stocks/quote?symbols=<TICKER>",
            "historical_bars": "GET /quote/<TICKERS>?range=<range>&interval=<interval>",
            "dividends": "GET /quote/<TICKERS>?dividends=true",
        },
        rate_limits=(
            "Gratuito: 15.000 req/mês, atualização a cada 30 min, 1 ticker por requisição, "
            "histórico de até 3 meses. Startup: 150.000/mês, 15 min, até 10 tickers. "
            "Pro: 500.000/mês, 5 min, até 20 tickers."
        ),
        error_handling=(
            "429 = cota do plano ou limite de requisições simultâneas; aguardar Retry-After. "
            "403 = dado fora do plano."
        ),
        license_status="UNREVIEWED",
        commercial_use=(
            "Página de preços indica planos pagos para apps, fintechs e produção; "
            "termos de uso não revisados."
        ),
        redistribution=None,
        storage=None,
        attribution=None,
        verified_on=VERIFIED_ON,
        evidence=(
            "https://brapi.dev/docs",
            "https://brapi.dev/docs/acoes",
            "https://brapi.dev/pricing",
        ),
        divergences=(
            "Duas gerações de endpoint: cotação em /v2/stocks/quote e histórico/dividendos em "
            "/quote/<tickers>; campos de data do histórico não documentados na página lida.",
            "PETR4, MGLU3, VALE3 e ITUB4 respondem sem chave (acesso livre não é licença).",
        ),
    ),
    ProviderRegistryEntry(
        provider_id="hg_brasil",
        display_name="HG Brasil Finance",
        status=ProviderStatus.CANDIDATE,
        markets=("BR",),
        capabilities=frozenset({ProviderCapability.LATEST_QUOTE, ProviderCapability.FX_RATES}),
        credential_envs=("HG_BRASIL_API_KEY",),
        auth="Parâmetro de query key=<chave>",
        base_url="https://api.hgbrasil.com",
        endpoints={"finance_summary": "GET /finance?key=<chave>"},
        rate_limits="Não informado nas páginas lidas; cotações atualizadas a cada 15 a 45 min.",
        error_handling="Não informado nas páginas lidas.",
        license_status="UNREVIEWED",
        commercial_use=None,
        redistribution=None,
        storage=None,
        attribution=None,
        verified_on=VERIFIED_ON,
        evidence=("https://hgbrasil.com/docs/finance", "https://hgbrasil.com/status/finance"),
        divergences=(
            "O exemplo de /finance não traz horário por moeda ou índice: sem horário da fonte, "
            "o normalizador fica bloqueado (SCHEMA_UNSUPPORTED).",
        ),
    ),
    ProviderRegistryEntry(
        provider_id="twelve_data",
        display_name="Twelve Data",
        status=ProviderStatus.DOCUMENTED,
        markets=("GLOBAL",),
        capabilities=frozenset(
            {
                ProviderCapability.LATEST_QUOTE,
                ProviderCapability.HISTORICAL_BARS,
                ProviderCapability.FX_RATES,
            }
        ),
        credential_envs=("TWELVE_DATA_API_KEY",),
        auth="Header Authorization: apikey <chave> (recomendado) ou apikey na query",
        base_url="https://api.twelvedata.com",
        endpoints={
            "latest_quote": "GET /quote?symbol=<SYMBOL>&timezone=UTC",
            "historical_bars": "GET /time_series?symbol=<SYMBOL>&interval=1day&timezone=UTC",
        },
        rate_limits=(
            "Basic gratuito: 8 créditos/min e 800/dia; /quote e /time_series custam 1 crédito "
            "por símbolo; Basic cobre 3 mercados não nomeados."
        ),
        error_handling=(
            'Corpo {"code","message","status":"error"}; 429 "API request limit reached".'
        ),
        license_status="UNREVIEWED",
        commercial_use=(
            "Planos individuais: uso pessoal, interno e não comercial; Basic com "
            '"Internal non-display usage" (exibir ao usuário exige outro plano).'
        ),
        redistribution=None,
        storage=None,
        attribution=None,
        verified_on=VERIFIED_ON,
        evidence=("https://twelvedata.com/docs", "https://twelvedata.com/pricing"),
        divergences=("Cobertura de B3 no plano Basic não confirmada.",),
    ),
    ProviderRegistryEntry(
        provider_id="alpha_vantage",
        display_name="Alpha Vantage",
        status=ProviderStatus.DOCUMENTED,
        markets=("GLOBAL",),
        capabilities=frozenset(
            {
                ProviderCapability.LATEST_QUOTE,
                ProviderCapability.HISTORICAL_BARS,
                ProviderCapability.FX_RATES,
                ProviderCapability.CORPORATE_ACTIONS,
            }
        ),
        credential_envs=("ALPHA_VANTAGE_API_KEY",),
        auth="Parâmetro de query apikey=<chave>",
        base_url="https://www.alphavantage.co/query",
        endpoints={
            "latest_quote": "GET ?function=GLOBAL_QUOTE&symbol=<SYMBOL>",
            "historical_bars": "GET ?function=TIME_SERIES_DAILY&symbol=<SYMBOL>",
        },
        rate_limits=(
            "Gratuito: 25 requisições por dia. GLOBAL_QUOTE atualiza no fim de cada pregão; "
            "tempo real ou 15 min nos EUA é premium; outputsize=full é premium."
        ),
        error_handling="Formato do erro de limite não informado na documentação lida.",
        license_status="UNREVIEWED",
        commercial_use=None,
        redistribution=None,
        storage=None,
        attribution=None,
        verified_on=VERIFIED_ON,
        evidence=(
            "https://www.alphavantage.co/documentation/",
            "https://www.alphavantage.co/support/",
        ),
        divergences=(
            "GLOBAL_QUOTE não traz moeda nem horário, só a data do pregão: o normalizador usa "
            "a moeda do catálogo e marca o dado como EOD.",
            "Suporte a B3 (sufixo de bolsa) não confirmado.",
        ),
    ),
    ProviderRegistryEntry(
        provider_id="open_exchange_rates",
        display_name="Open Exchange Rates",
        status=ProviderStatus.DOCUMENTED,
        markets=("FX",),
        capabilities=frozenset({ProviderCapability.FX_RATES}),
        credential_envs=("OPEN_EXCHANGE_RATES_APP_ID",),
        auth="Parâmetro de query app_id=<id>",
        base_url="https://openexchangerates.org/api",
        endpoints={"fx_rates": "GET /latest.json"},
        rate_limits=(
            "Free: 1.000 req/mês, horária, base USD. Developer: 10.000/mês, horária. "
            "Enterprise: 100.000/mês, 30 min. Unlimited: 5 min."
        ),
        error_handling=(
            'Corpo {"error","status","message","description"}; 401 missing/invalid_app_id; '
            "429 not_allowed (sem permissão, não é limite); 403 access_restricted (uso excessivo)."
        ),
        license_status="UNREVIEWED",
        commercial_use=None,
        redistribution=None,
        storage=None,
        attribution=None,
        verified_on=VERIFIED_ON,
        evidence=(
            "https://docs.openexchangerates.org/reference/latest-json",
            "https://docs.openexchangerates.org/reference/errors",
            "https://openexchangerates.org/signup",
        ),
        divergences=(
            "A página de licença remete aos termos de uso, não revisados; cache e "
            "redistribuição seguem desconhecidos.",
        ),
    ),
    ProviderRegistryEntry(
        provider_id="massive",
        display_name="Massive (antiga Polygon)",
        status=ProviderStatus.DOCUMENTED,
        markets=("US",),
        capabilities=frozenset(
            {
                ProviderCapability.LATEST_QUOTE,
                ProviderCapability.HISTORICAL_BARS,
                ProviderCapability.DIVIDENDS,
                ProviderCapability.CORPORATE_ACTIONS,
            }
        ),
        credential_envs=("MASSIVE_API_KEY",),
        auth="Header Authorization: Bearer <chave> ou apiKey na query",
        base_url="https://api.massive.com",
        endpoints={
            "historical_bars": (
                "GET /v2/aggs/ticker/<TICKER>/range/<multiplier>/<timespan>/<from>/<to>"
            ),
            "previous_close": "GET /v2/aggs/ticker/<TICKER>/prev",
            "dividends": "GET /stocks/v1/dividends",
            "splits": "GET /stocks/v1/splits",
        },
        rate_limits=(
            "Basic gratuito: 5 chamadas/min, fim do dia, 2 anos de histórico. Starter: "
            "ilimitado, 15 min de atraso. Advanced: tempo real."
        ),
        error_handling="Formato do erro de limite não informado nas páginas lidas.",
        license_status="UNREVIEWED",
        commercial_use='Planos Starter a Advanced rotulados "Individual use".',
        redistribution=None,
        storage=None,
        attribution=None,
        verified_on=VERIFIED_ON,
        evidence=(
            "https://massive.com/docs/rest/quickstart",
            "https://massive.com/docs/rest/stocks/overview.md",
            "https://massive.com/docs/rest/stocks/aggregates/custom-bars.md",
            "https://massive.com/pricing",
        ),
        divergences=(
            "A matriz de 2026-08-31 dizia que exibir a usuários exige plano Business; a página "
            "de preços lida não afirma isso. Fica como pendência de revisão de licença.",
            "Agregados ajustados por split por padrão (adjusted=true); o normalizador pede "
            "adjusted=false para não misturar séries.",
        ),
    ),
    ProviderRegistryEntry(
        provider_id="b3_developers",
        display_name="B3 for Developers",
        status=ProviderStatus.BLOCKED,
        markets=("BR",),
        capabilities=frozenset(),
        credential_envs=(
            "B3_DEVELOPERS_CLIENT_ID",
            "B3_DEVELOPERS_CLIENT_SECRET",
            "B3_DEVELOPERS_TOKEN_URL",
        ),
        auth="OAuth 2.0 client credentials (catálogo público)",
        base_url="https://developers.b3.com.br",
        endpoints={},
        rate_limits="Não informado.",
        error_handling="Não informado.",
        license_status="UNREVIEWED",
        commercial_use="Somente B2B; não oferecido a pessoas físicas.",
        redistribution=None,
        storage=None,
        attribution=None,
        verified_on=VERIFIED_ON,
        evidence=("https://developers.b3.com.br/apis",),
        blocked_reason=(
            "O catálogo público (114 APIs) não lista API de cotação nem de histórico de preços; "
            "acesso só por contrato B2B."
        ),
    ),
)

# Proposed order per capability and market. It applies only to providers that pass
# `activation_decision`; until then every chain resolves to nothing (fail closed).
PRECEDENCE: Mapping[tuple[ProviderCapability, str], tuple[str, ...]] = {
    (ProviderCapability.LATEST_QUOTE, "BR"): ("brapi", "hg_brasil"),
    (ProviderCapability.LATEST_QUOTE, "US"): ("massive", "twelve_data", "alpha_vantage"),
    (ProviderCapability.HISTORICAL_BARS, "BR"): ("brapi",),
    (ProviderCapability.HISTORICAL_BARS, "US"): ("massive", "twelve_data", "alpha_vantage"),
    (ProviderCapability.FX_RATES, "FX"): (
        "open_exchange_rates",
        "twelve_data",
        "hg_brasil",
        "alpha_vantage",
    ),
    (ProviderCapability.DIVIDENDS, "BR"): ("brapi",),
    (ProviderCapability.DIVIDENDS, "US"): ("massive",),
    (ProviderCapability.CORPORATE_ACTIONS, "US"): ("massive", "alpha_vantage"),
}


def get_entry(provider_id: str) -> ProviderRegistryEntry:
    for entry in REGISTRY:
        if entry.provider_id == provider_id:
            return entry
    raise KeyError(provider_id)


def credential_presence(
    entry: ProviderRegistryEntry, environ: Mapping[str, str] | None = None
) -> dict[str, bool]:
    """Presence only: values are never read into the result."""

    env = os.environ if environ is None else environ
    return {name: bool(env.get(name, "").strip()) for name in entry.credential_envs}


@dataclass(frozen=True)
class ActivationDecision:
    allowed: bool
    reason: UnavailableReason | None


def activation_decision(
    entry: ProviderRegistryEntry, environ: Mapping[str, str] | None = None
) -> ActivationDecision:
    """Fail closed; the reason is the public code shown when the provider cannot serve."""

    if entry.status in {ProviderStatus.BLOCKED, ProviderStatus.REVOKED}:
        return ActivationDecision(False, UnavailableReason.LICENSE_BLOCKED)
    if entry.status is ProviderStatus.PAUSED:
        return ActivationDecision(False, UnavailableReason.UNAVAILABLE)
    if entry.status is not ProviderStatus.ACTIVE:
        return ActivationDecision(False, UnavailableReason.DATASET_NOT_APPROVED)
    if entry.license_status != "PUBLIC_APPROVED":
        return ActivationDecision(False, UnavailableReason.LICENSE_BLOCKED)
    if not entry.credential_envs or not all(credential_presence(entry, environ).values()):
        return ActivationDecision(False, UnavailableReason.PROVIDER_NOT_CONFIGURED)
    return ActivationDecision(True, None)


def fallback_chain(
    capability: ProviderCapability,
    market: str,
    environ: Mapping[str, str] | None = None,
) -> tuple[str, ...]:
    """Providers allowed to serve this capability, in precedence order."""

    return tuple(
        provider_id
        for provider_id in PRECEDENCE.get((capability, market), ())
        if capability in get_entry(provider_id).capabilities
        and activation_decision(get_entry(provider_id), environ).allowed
    )
