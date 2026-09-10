"""Deterministic, informational portfolio valuation and performance engine."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum

from app.contracts import (
    EquityCurvePointResponse,
    EquityCurveResponse,
    PerformanceDecompositionResponse,
    PerformanceProvenance,
    PortfolioEventResponse,
    PortfolioPerformanceResponse,
    PortfolioValuationPositionResponse,
    PortfolioValuationResponse,
)
from app.contracts import (
    PerformanceStatus as ContractPerformanceStatus,
)
from app.core.config import get_settings
from app.portfolios.service import PortfolioEventInput
from app.providers.models import DataLevel, Freshness

UTC = timezone.utc


class PerformanceStatus(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class PriceMark:
    canonical_id: str
    value: Decimal
    currency: str
    provider: str
    dataset: str
    data_level: DataLevel | str
    freshness: Freshness | str
    source_timestamp: datetime
    collected_at: datetime
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class FxMark:
    base_currency: str
    quote_currency: str
    rate: Decimal
    provider: str
    dataset: str
    data_level: DataLevel | str
    freshness: Freshness | str
    source_timestamp: datetime
    collected_at: datetime
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class ValuationPosition:
    canonical_id: str
    quantity: Decimal
    currency: str
    remaining_cost_basis: Decimal
    weighted_average_cost: Decimal
    price: Decimal | None
    market_value_native: Decimal | None
    market_value_base: Decimal | None
    unrealized_pnl: Decimal | None
    fx_rate: Decimal | None
    status: PerformanceStatus
    missing_inputs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ValuationResult:
    base_currency: str
    cash_balances: dict[str, Decimal]
    cash_value_base: Decimal | None
    positions_value_base: Decimal | None
    total_value_base: Decimal | None
    realized_pnl: Decimal | None
    unrealized_pnl: Decimal | None
    positions: list[ValuationPosition]
    status: PerformanceStatus
    missing_inputs: tuple[str, ...] = ()
    provenance: tuple[PriceMark | FxMark, ...] = ()


@dataclass(frozen=True)
class TWRPoint:
    timestamp: datetime
    value: Decimal
    external_flow: Decimal


@dataclass(frozen=True)
class TWRResult:
    twr: Decimal | None
    status: PerformanceStatus
    methodology: str
    missing_inputs: tuple[str, ...] = ()


def _event_value(event: PortfolioEventInput, field_name: str) -> Decimal:
    value = getattr(event, field_name)
    if value is None or not value.is_finite():
        raise ValueError(f"{field_name} is required")
    return value


def _effective_events(events: list[PortfolioEventInput]) -> list[tuple[PortfolioEventInput, bool]]:
    ordered = sorted(events, key=lambda item: (item.occurred_at, item.created_at, item.id))
    by_id = {event.id: event for event in ordered}
    result: list[tuple[PortfolioEventInput, bool]] = []
    reversed_ids: set[str] = set()
    for event in ordered:
        if event.event_type == "REVERSAL":
            target_id = event.reversal_of_event_id
            if not target_id or target_id not in by_id:
                raise ValueError("reversal target does not exist")
            if target_id in reversed_ids:
                raise ValueError("event has already been reversed")
            result.append((by_id[target_id], True))
            reversed_ids.add(target_id)
        else:
            result.append((event, False))
    return result


def _replay_financials(
    events: list[PortfolioEventInput],
) -> tuple[dict[str, Decimal], dict[str, tuple[Decimal, Decimal]], dict[str, Decimal]]:
    cash: dict[str, Decimal] = {}
    positions: dict[str, tuple[Decimal, Decimal]] = {}
    realized: dict[str, Decimal] = {}
    for event, inverse in _effective_events(events):
        sign = Decimal("-1") if inverse else Decimal("1")
        currency = event.currency
        amount = event.gross_amount
        if event.event_type in {"CASH_DEPOSIT", "CASH_WITHDRAWAL", "FEE"}:
            amount = _event_value(event, "gross_amount")
            direction = Decimal("1") if event.event_type == "CASH_DEPOSIT" else Decimal("-1")
            cash[currency] = cash.get(currency, Decimal("0")) + sign * direction * amount
            continue
        if event.event_type not in {"BUY", "SELL"}:
            continue
        quantity = _event_value(event, "quantity")
        unit_price = _event_value(event, "unit_price")
        gross = amount if amount is not None else quantity * unit_price
        fee = event.fee_amount or Decimal("0")
        key = event.canonical_id
        if not key:
            raise ValueError("canonical_id is required")
        quantity_before, cost_before = positions.get(key, (Decimal("0"), Decimal("0")))
        if event.event_type == "BUY":
            cash[currency] = cash.get(currency, Decimal("0")) - sign * (gross + fee)
            positions[key] = (quantity_before + sign * quantity, cost_before + sign * (gross + fee))
        else:
            average = cost_before / quantity_before if quantity_before else Decimal("0")
            sale_pnl = (gross - fee) - average * quantity
            realized[currency] = realized.get(currency, Decimal("0")) + sign * sale_pnl
            cash[currency] = cash.get(currency, Decimal("0")) + sign * (gross - fee)
            positions[key] = (
                quantity_before - sign * quantity,
                cost_before - sign * average * quantity,
            )
    return cash, positions, realized


def _convert(
    amount: Decimal, currency: str, base_currency: str, fx_rates: dict[tuple[str, str], FxMark]
) -> tuple[Decimal | None, FxMark | None]:
    if currency == base_currency:
        return amount, None
    mark = fx_rates.get((currency, base_currency))
    if mark is None or mark.rate <= 0:
        return None, None
    return amount * mark.rate, mark


def calculate_valuation(
    events: list[PortfolioEventInput],
    *,
    base_currency: str,
    prices: dict[str, PriceMark],
    fx_rates: dict[tuple[str, str], FxMark],
) -> ValuationResult:
    cash, positions, realized_by_currency = _replay_financials(events)
    missing: set[str] = set()
    provenance: list[PriceMark | FxMark] = []
    cash_base = Decimal("0")
    cash_complete = True
    for currency, amount in cash.items():
        converted, fx = _convert(amount, currency, base_currency, fx_rates)
        if converted is None:
            missing.add(f"FX_{currency}_{base_currency}")
            cash_complete = False
        else:
            cash_base += converted
            if fx:
                provenance.append(fx)
    valuation_positions: list[ValuationPosition] = []
    positions_base = Decimal("0")
    unrealized_base = Decimal("0")
    positions_complete = True
    for canonical_id, (quantity, cost_basis) in sorted(positions.items()):
        if quantity <= 0:
            continue
        price_mark = prices.get(canonical_id)
        if price_mark is None or price_mark.value <= 0:
            missing.add(f"PRICE_{canonical_id}")
            positions_complete = False
            valuation_positions.append(
                ValuationPosition(
                    canonical_id,
                    quantity,
                    "XXX",
                    cost_basis,
                    cost_basis / quantity,
                    None,
                    None,
                    None,
                    None,
                    None,
                    PerformanceStatus.UNAVAILABLE,
                    (f"PRICE_{canonical_id}",),
                )
            )
            continue
        provenance.append(price_mark)
        native = quantity * price_mark.value
        converted, fx = _convert(native, price_mark.currency, base_currency, fx_rates)
        position_missing: list[str] = []
        if converted is None:
            position_missing.append(f"FX_{price_mark.currency}_{base_currency}")
            missing.update(position_missing)
            positions_complete = False
        else:
            positions_base += converted
            converted_cost, _ = _convert(cost_basis, price_mark.currency, base_currency, fx_rates)
            if converted_cost is not None:
                unrealized_base += converted - converted_cost
        valuation_positions.append(
            ValuationPosition(
                canonical_id,
                quantity,
                price_mark.currency,
                cost_basis,
                cost_basis / quantity,
                price_mark.value,
                native,
                converted,
                (converted - (converted_cost or Decimal("0")))
                if converted is not None and converted_cost is not None
                else None,
                fx.rate if fx else (Decimal("1") if price_mark.currency == base_currency else None),
                PerformanceStatus.COMPLETE if not position_missing else PerformanceStatus.PARTIAL,
                tuple(position_missing),
            )
        )
    realized_base: Decimal | None = Decimal("0")
    for currency, amount in realized_by_currency.items():
        converted, fx = _convert(amount, currency, base_currency, fx_rates)
        if converted is None:
            realized_base = None
            missing.add(f"FX_{currency}_{base_currency}")
            cash_complete = False
        else:
            realized_base += converted
            if fx:
                provenance.append(fx)
    status = (
        PerformanceStatus.COMPLETE
        if not missing and cash_complete and positions_complete
        else PerformanceStatus.PARTIAL
    )
    return ValuationResult(
        base_currency,
        cash,
        cash_base if cash_complete else None,
        positions_base if positions_complete else None,
        cash_base + positions_base if cash_complete and positions_complete else None,
        realized_base if cash_complete else None,
        unrealized_base if positions_complete else None,
        valuation_positions,
        status,
        tuple(sorted(missing)),
        tuple(provenance),
    )


def calculate_twr(points: list[TWRPoint]) -> TWRResult:
    ordered = sorted(points, key=lambda point: point.timestamp)
    if len(ordered) < 2:
        raise ValueError("TWR requires a beginning value")
    factor = Decimal("1")
    for previous, current in zip(ordered, ordered[1:]):
        if previous.value <= 0:
            raise ValueError("TWR beginning value must be positive")
        factor *= (current.value - current.external_flow) / previous.value
    return TWRResult(
        twr=factor - Decimal("1"),
        status=PerformanceStatus.COMPLETE,
        methodology=(
            "Time-weighted return: cada fluxo externo é removido do valor final "
            "do subperíodo antes da composição multiplicativa."
        ),
    )


def event_inputs(events: list[PortfolioEventResponse]) -> list[PortfolioEventInput]:
    return [
        PortfolioEventInput(
            id=item.id,
            event_type=item.event_type.value,
            currency=item.currency,
            canonical_id=item.canonical_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            gross_amount=item.gross_amount,
            fee_amount=item.fee_amount,
            occurred_at=item.occurred_at,
            created_at=item.created_at,
            reversal_of_event_id=item.reversal_of_event_id,
            idempotency_key=item.idempotency_key,
            request_id=item.request_id,
            notes=item.notes,
        )
        for item in events
    ]


def demo_price_marks(
    events: list[PortfolioEventInput],
) -> tuple[dict[str, PriceMark], dict[tuple[str, str], FxMark]]:
    if get_settings().demo_enabled:
        from app.demo.read_models import price_marks

        return price_marks([item.canonical_id for item in events]), {}
    now = datetime.now(UTC)
    prices: dict[str, PriceMark] = {}
    currencies = {"equity.us.nasdaq.aapl": "USD", "equity.br.b3.petr4": "BRL"}
    for event in events:
        if event.canonical_id and event.canonical_id not in prices:
            currency = currencies.get(event.canonical_id, event.currency)
            prices[event.canonical_id] = PriceMark(
                event.canonical_id,
                Decimal("42.42"),
                currency,
                "demo",
                "demo-portfolio-marks",
                DataLevel.DEMO,
                Freshness.STALE,
                now,
                now,
                ("Marca sintética local; não representa mercado real.",),
            )
    fx = FxMark(
        "USD",
        "BRL",
        Decimal("5.00"),
        "demo",
        "demo-portfolio-fx",
        DataLevel.DEMO,
        Freshness.STALE,
        now,
        now,
        ("Taxa sintética local; não representa mercado real.",),
    )
    return prices, {("USD", "BRL"): fx}


@dataclass
class PortfolioPerformanceService:
    portfolio_service: object

    def _inputs(self, user_id: str, portfolio_id: str) -> tuple[object, list[PortfolioEventInput]]:
        portfolio = self.portfolio_service.get(user_id, portfolio_id)
        events = event_inputs(self.portfolio_service.events(user_id, portfolio_id))
        return portfolio, events

    def valuation(self, user_id: str, portfolio_id: str):
        portfolio, events = self._inputs(user_id, portfolio_id)
        events, outside_window = self._valuation_window(events)
        prices, fx = demo_price_marks(events)
        result = calculate_valuation(
            events, base_currency=portfolio.base_currency, prices=prices, fx_rates=fx
        )
        if outside_window:
            result = replace(
                result,
                status=PerformanceStatus.PARTIAL
                if result.status == PerformanceStatus.COMPLETE
                else result.status,
                missing_inputs=(*result.missing_inputs, "EVENTS_AFTER_DEMO_CUTOFF"),
            )
        return portfolio, events, result

    @staticmethod
    def _valuation_window(events):
        if not get_settings().demo_enabled:
            return events, False
        from app.demo.dataset import DEMO_CUTOFF

        eligible = [event for event in events if event.occurred_at <= DEMO_CUTOFF]
        return eligible, len(eligible) != len(events)

    def twr(self, user_id: str, portfolio_id: str) -> TWRResult:
        _, events = self._inputs(user_id, portfolio_id)
        events, outside_window = self._valuation_window(events)
        if outside_window:
            return TWRResult(
                None,
                PerformanceStatus.UNAVAILABLE,
                "TWR indisponível: há eventos posteriores ao corte histórico DEMO.",
                ("EVENTS_AFTER_DEMO_CUTOFF",),
            )
        if get_settings().demo_enabled and events:
            curve = self.equity_curve_response(user_id, portfolio_id)
            days = curve.points
            if days and days[0].total_value_base is not None and days[0].total_value_base <= 0:
                return TWRResult(
                    None,
                    PerformanceStatus.UNAVAILABLE,
                    "TWR exige patrimônio inicial estritamente positivo.",
                    ("POSITIVE_BEGINNING_VALUATION",),
                )
            later_flows = (
                any(
                    event.event_type in {"CASH_DEPOSIT", "CASH_WITHDRAWAL", "REVERSAL"}
                    and event.occurred_at.date() > days[0].valuation_date
                    for event in events
                )
                if days
                else True
            )
            if (
                len(days) >= 2
                and not later_flows
                and all(
                    point.total_value_base is not None and point.valuation_status == "COMPLETE"
                    for point in days
                )
            ):
                return calculate_twr(
                    [
                        TWRPoint(
                            datetime.combine(point.valuation_date, datetime.min.time(), UTC),
                            point.total_value_base,
                            Decimal("0"),
                        )
                        for point in (days[0], days[-1])
                    ]
                )
        if len(events) < 2:
            return TWRResult(
                None,
                PerformanceStatus.UNAVAILABLE,
                "TWR exige pelo menos dois pontos de valuation aprovados.",
                ("HISTORICAL_VALUATION",),
            )
        return TWRResult(
            None,
            PerformanceStatus.UNAVAILABLE,
            "TWR P0 requer série histórica de valuation aprovada; nenhuma série real é ativada.",
            ("HISTORICAL_VALUATION",),
        )

    @staticmethod
    def _provenance(items: tuple[PriceMark | FxMark, ...]) -> tuple[PerformanceProvenance, ...]:
        return tuple(
            PerformanceProvenance(
                provider=item.provider,
                dataset=item.dataset,
                source="local-demo",
                data_level=DataLevel(item.data_level),
                freshness=Freshness(item.freshness),
                source_timestamp=item.source_timestamp,
                collected_at=item.collected_at,
                latency_ms=max(
                    0, int((item.collected_at - item.source_timestamp).total_seconds() * 1000)
                ),
                limitations=item.limitations,
            )
            for item in items
        )

    def valuation_response(self, user_id: str, portfolio_id: str) -> PortfolioValuationResponse:
        portfolio, _, result = self.valuation(user_id, portfolio_id)
        as_of = max(
            (item.source_timestamp for item in result.provenance), default=datetime.now(UTC)
        )
        window_note = ""
        if get_settings().demo_enabled:
            from app.demo.dataset import DEMO_CUTOFF

            as_of = DEMO_CUTOFF
            window_note = (
                f" Corte DEMO: {DEMO_CUTOFF.isoformat()}; somente eventos até esse instante."
                " Eventos posteriores ficam preservados no ledger e não entram neste recorte."
            )
        return PortfolioValuationResponse(
            portfolio_id=portfolio.id,
            base_currency=portfolio.base_currency,
            as_of=as_of,
            cash_value_base=result.cash_value_base,
            positions_value_base=result.positions_value_base,
            total_value_base=result.total_value_base,
            realized_pnl=result.realized_pnl,
            unrealized_pnl=result.unrealized_pnl,
            status=ContractPerformanceStatus(result.status.value),
            missing_inputs=result.missing_inputs,
            methodology=(
                "Replay append-only com Decimal; preço DEMO aprovado apenas como "
                "fixture sintética local e conversão FX explícita."
            )
            + window_note,
            provenance=self._provenance(result.provenance),
            positions=[
                PortfolioValuationPositionResponse(
                    canonical_id=item.canonical_id,
                    quantity=item.quantity,
                    currency=item.currency,
                    remaining_cost_basis=item.remaining_cost_basis,
                    weighted_average_cost=item.weighted_average_cost,
                    price=item.price,
                    market_value_native=item.market_value_native,
                    market_value_base=item.market_value_base,
                    unrealized_pnl=item.unrealized_pnl,
                    fx_rate=item.fx_rate,
                    status=ContractPerformanceStatus(item.status.value),
                    missing_inputs=item.missing_inputs,
                )
                for item in result.positions
            ],
        )

    def performance_response(self, user_id: str, portfolio_id: str) -> PortfolioPerformanceResponse:
        valuation = self.valuation_response(user_id, portfolio_id)
        twr = self.twr(user_id, portfolio_id)
        return PortfolioPerformanceResponse(
            portfolio_id=valuation.portfolio_id,
            base_currency=valuation.base_currency,
            realized_pnl=valuation.realized_pnl,
            unrealized_pnl=valuation.unrealized_pnl,
            twr=twr.twr,
            status=ContractPerformanceStatus.PARTIAL
            if valuation.status is not ContractPerformanceStatus.COMPLETE or twr.twr is None
            else ContractPerformanceStatus.COMPLETE,
            methodology=f"{valuation.methodology} {twr.methodology}",
            missing_inputs=tuple(sorted(set(valuation.missing_inputs) | set(twr.missing_inputs))),
            provenance=valuation.provenance,
        )

    def equity_curve_response(self, user_id: str, portfolio_id: str) -> EquityCurveResponse:
        portfolio, events = self._inputs(user_id, portfolio_id)
        events, _ = self._valuation_window(events)
        prices, fx = demo_price_marks(events)
        dates = sorted({item.occurred_at.date() for item in events}) or [datetime.now(UTC).date()]
        window_note = ""
        if get_settings().demo_enabled:
            from datetime import timedelta

            from app.demo.dataset import DEMO_CUTOFF

            first = min((item.occurred_at.date() for item in events), default=DEMO_CUTOFF.date())
            dates = [
                first + timedelta(days=offset)
                for offset in range((DEMO_CUTOFF.date() - first).days + 1)
                if events and (first + timedelta(days=offset)).weekday() < 5
            ]
            window_note = (
                f" Corte DEMO: {DEMO_CUTOFF.isoformat()}; eventos posteriores não são projetados"
                " para pontos históricos. O ledger original permanece intacto."
            )
        points: list[EquityCurvePointResponse] = []
        provenance: tuple[PerformanceProvenance, ...] = ()
        for day in dates:
            events_at_day = [item for item in events if item.occurred_at.date() <= day]
            if get_settings().demo_enabled:
                from app.demo.read_models import price_marks

                prices = price_marks([item.canonical_id for item in events_at_day], as_of=day)
            result = calculate_valuation(
                events_at_day,
                base_currency=portfolio.base_currency,
                prices=prices,
                fx_rates=fx,
            )
            points.append(
                EquityCurvePointResponse(
                    valuation_date=day,
                    total_value_base=result.total_value_base,
                    cash_value_base=result.cash_value_base,
                    positions_value_base=result.positions_value_base,
                    data_level=DataLevel.DEMO,
                    freshness=Freshness.STALE,
                    valuation_status=ContractPerformanceStatus(result.status.value),
                    missing_inputs=result.missing_inputs,
                )
            )
            provenance += self._provenance(result.provenance)
        return EquityCurveResponse(
            portfolio_id=portfolio.id,
            base_currency=portfolio.base_currency,
            methodology=(
                "Valuations por data, sem interpolação; no cenário DEMO persistido, cada ponto "
                "usa exclusivamente a barra daquela sessão. TWR indisponível quando faltam "
                "valuations nas fronteiras de fluxos externos."
            )
            + window_note,
            points=points,
            provenance=provenance,
        )

    def decomposition_response(
        self, user_id: str, portfolio_id: str
    ) -> PerformanceDecompositionResponse:
        valuation = self.valuation_response(user_id, portfolio_id)
        status = valuation.status
        return PerformanceDecompositionResponse(
            portfolio_id=valuation.portfolio_id,
            base_currency=valuation.base_currency,
            price_effect=valuation.unrealized_pnl,
            fx_effect=None,
            cash_flow_effect=None,
            fees_effect=None,
            income_effect=None,
            unclassified_or_unavailable=None
            if status is ContractPerformanceStatus.COMPLETE
            else Decimal("0"),
            status=status,
            methodology=(
                "Decomposição P0 informa apenas efeito de preço disponível; FX, "
                "fluxos, taxas e proventos não são inferidos sem série histórica "
                "aprovada."
            ),
            missing_inputs=valuation.missing_inputs,
            provenance=valuation.provenance,
        )
