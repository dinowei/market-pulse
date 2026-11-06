"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";
import type { components } from "../generated/api";
import { CANONICAL_ID } from "../lib/canonical-id";
import { FINANCIAL_DISCLAIMER } from "../lib/disclaimers";
import { decimalSign, formatDecimal, fractionToPercent } from "../lib/decimal-text";
import { allocation, assetClassLabel, symbolOf } from "../lib/series-stats";
import styles from "./private-pages.module.css";
import { EquityChart } from "./equity-chart";
import { DataStateBadge } from "./market-data";
import { isRateLimited, parseRetryAfter, RateLimitNotice, retryAfterSeconds } from "./rate-limit-notice";

type Portfolio = components["schemas"]["PortfolioResponse"];
type PortfolioList = components["schemas"]["PortfolioListResponse"];
type PortfolioEvent = components["schemas"]["PortfolioEventResponse"];
type PortfolioEventRequest = components["schemas"]["PortfolioEventRequest"];
type PortfolioEventType = components["schemas"]["PortfolioEventType"];
type PortfolioDrawdown = components["schemas"]["PortfolioDrawdownResponse"];
type PortfolioSummary = components["schemas"]["PortfolioSummaryResponse"];
type PortfolioValuation = components["schemas"]["PortfolioValuationResponse"];
type PortfolioPerformance = components["schemas"]["PortfolioPerformanceResponse"];
type EquityCurve = components["schemas"]["EquityCurveResponse"];
type PerformanceDecomposition = components["schemas"]["PerformanceDecompositionResponse"];
type PortfolioIncome = components["schemas"]["PortfolioIncomeResponse"];
type PortfolioEventMarkers = components["schemas"]["PortfolioEventMarkersResponse"];
type PortfolioOverview = components["schemas"]["PortfolioOverviewResponse"];

/** H-21: the eight read models of one portfolio in a single request. */
const overviewPath = (portfolioId: string) => `/api/v1/portfolios/${encodeURIComponent(portfolioId)}/overview`;

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const eventTypes = ["CASH_DEPOSIT", "CASH_WITHDRAWAL", "BUY", "SELL", "FEE"] as const satisfies readonly PortfolioEventType[];

// Categorical only: green and red stay reserved for up and down.
const SLICE_COLORS = ["var(--pa-cyan)", "var(--pa-violet)", "var(--pa-state-stale)", "var(--pa-market-flat)", "var(--pa-text-secondary)", "var(--pa-text-primary)"];
const money = (value: string | null | undefined, currency: string) => (value == null ? "Indisponível" : `${currency} ${formatDecimal(value)}`);
const percent = (fraction: string | null | undefined) => (fraction == null ? "Indisponível" : fractionToPercent(fraction));
const tone = (value: string | null | undefined) => ({ 1: "direction-up", [-1]: "direction-down" } as Record<number, string>)[decimalSign(value) ?? 0];

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", Accept: "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const error = new Error(`HTTP ${response.status}`) as Error & { status?: number; retryAfter?: number };
    error.status = response.status;
    error.retryAfter = parseRetryAfter(response.headers.get("Retry-After"));
    throw error;
  }
  return response.json() as Promise<T>;
}

function isSignedOut(error: unknown): boolean {
  return error instanceof Error && (error as Error & { status?: number }).status === 401;
}

export function PortfoliosPanel({ initialCanonicalId = "" }: { initialCanonicalId?: string }) {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [summary, setSummary] = useState<PortfolioSummary>();
  const [events, setEvents] = useState<PortfolioEvent[]>([]);
  const [valuation, setValuation] = useState<PortfolioValuation>();
  const [performance, setPerformance] = useState<PortfolioPerformance>();
  const [equityCurve, setEquityCurve] = useState<EquityCurve>();
  const [decomposition, setDecomposition] = useState<PerformanceDecomposition>();
  const [income, setIncome] = useState<PortfolioIncome[]>([]);
  const [markers, setMarkers] = useState<PortfolioEventMarkers>();
  const [name, setName] = useState("");
  const [baseCurrency, setBaseCurrency] = useState("BRL");
  const [eventType, setEventType] = useState<PortfolioEventType>(initialCanonicalId ? "BUY" : "CASH_DEPOSIT");
  const [currency, setCurrency] = useState("BRL");
  const [canonicalId, setCanonicalId] = useState(initialCanonicalId);
  const [drawdown, setDrawdown] = useState<PortfolioDrawdown>();
  const [quantity, setQuantity] = useState("");
  const [unitPrice, setUnitPrice] = useState("");
  const [grossAmount, setGrossAmount] = useState("");
  const [loading, setLoading] = useState(true);
  const [signedOut, setSignedOut] = useState(false);
  const [error, setError] = useState<string>();
  const [rateLimit, setRateLimit] = useState<{ retryAfter?: number }>();
  const [attempt, setAttempt] = useState(0);

  const applyOverview = useCallback((overview: PortfolioOverview) => {
    setSummary(overview.summary);
    setEvents(overview.events);
    setValuation(overview.valuation);
    setPerformance(overview.performance);
    setEquityCurve(overview.equity_curve);
    setDecomposition(overview.decomposition);
    setDrawdown(overview.drawdown);
    setIncome(overview.income);
    setMarkers(overview.event_markers);
  }, []);

  const loadDetails = useCallback(async (portfolioId: string) => {
    if (!portfolioId) return;
    try {
      applyOverview(await requestJson<PortfolioOverview>(overviewPath(portfolioId)));
    } catch (reason) {
      if (isSignedOut(reason)) setSignedOut(true);
      else if (isRateLimited(reason)) setRateLimit({ retryAfter: retryAfterSeconds(reason) });
      else setError("Não foi possível carregar os detalhes da carteira.");
    }
  }, [applyOverview]);

  useEffect(() => {
    let active = true;
    requestJson<PortfolioList>("/api/v1/portfolios")
      .then((data) => {
        if (!active) return;
        setPortfolios(data.items);
        setSelectedId((current) => current || data.items[0]?.id || "");
        setSignedOut(false);
      })
      .catch((reason) => {
        if (!active) return;
        if (isSignedOut(reason)) setSignedOut(true);
        else if (isRateLimited(reason)) setRateLimit({ retryAfter: retryAfterSeconds(reason) });
        else setError("Não foi possível carregar suas carteiras.");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [attempt]);

  useEffect(() => {
    if (!selectedId) return;
    let active = true;
    requestJson<PortfolioOverview>(overviewPath(selectedId)).then((overview) => {
      if (!active) return;
      applyOverview(overview);
    }).catch((reason) => {
      if (!active) return;
      if (isSignedOut(reason)) setSignedOut(true);
      else if (isRateLimited(reason)) setRateLimit({ retryAfter: retryAfterSeconds(reason) });
      else setError("Não foi possível carregar os detalhes da carteira.");
    });
    return () => { active = false; };
  }, [selectedId, attempt, applyOverview]);

  async function createPortfolio(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim()) return;
    try {
      const created = await requestJson<Portfolio>("/api/v1/portfolios", { method: "POST", body: JSON.stringify({ name: name.trim(), base_currency: baseCurrency }) });
      setName("");
      setPortfolios((current) => [...current, created]);
      setSelectedId(created.id);
    } catch { setError("Não foi possível criar a carteira."); }
  }

  async function createEvent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedId) return;
    const payload: PortfolioEventRequest = {
      event_type: eventType,
      currency,
      canonical_id: canonicalId.trim() || null,
      quantity: quantity || null,
      unit_price: unitPrice || null,
      gross_amount: grossAmount || null,
      fee_amount: null,
      notes: null,
      occurred_at: new Date().toISOString(),
    };
    try {
      await requestJson<PortfolioEvent>(`/api/v1/portfolios/${selectedId}/events`, {
        method: "POST",
        headers: { "Idempotency-Key": globalThis.crypto.randomUUID() },
        body: JSON.stringify(payload),
      });
      setQuantity(""); setUnitPrice(""); setGrossAmount(""); setCanonicalId("");
      await loadDetails(selectedId);
    } catch { setError("Evento inválido ou saldo/posição insuficiente."); }
  }

  const retry = () => { setRateLimit(undefined); setError(undefined); setLoading(true); setAttempt((current) => current + 1); };

  const shell = `${styles.page} terminal-root`;
  if (loading) return <main id="main-content" className={shell}><h1 className="sr-only">Carteiras informativas</h1><p className="loading-state">Carregando carteiras…</p></main>;
  if (signedOut) return <main id="main-content" className={shell}><section className={styles.glass} aria-labelledby="portfolios-title"><h1 id="portfolios-title">Carteiras</h1><p className="muted">Entre para acessar suas carteiras informativas.</p><Link className="auth-submit portfolios-link" href="/login">Ir para login</Link></section></main>;

  const base = valuation?.base_currency ?? "";
  const { slices, unpriced } = allocation(valuation?.positions ?? [], valuation?.cash_value_base);

  return <main id="main-content" className={shell}>
    <section className={styles.hero}>
      <div>
        <span className={styles.chip}>Área privada</span>
        <h1 id="portfolios-title">Carteiras informativas</h1>
        <p>Eventos, caixa, posições, P&amp;L e TWR calculados só do que você registrou, sempre com metodologia. Estados possíveis: DEMO, STALE, PARTIAL e UNAVAILABLE. {FINANCIAL_DISCLAIMER}</p>
      </div>
    </section>
    {rateLimit && <RateLimitNotice retryAfter={rateLimit.retryAfter} onRetry={retry} />}
    {error && <p className="state-note" role="alert">{error}</p>}

    {portfolios.length > 0 && <div className={styles.pills} role="group" aria-label="Carteira">{portfolios.map((portfolio) => <button key={portfolio.id} type="button" aria-pressed={selectedId === portfolio.id} onClick={() => setSelectedId(portfolio.id)}>{portfolio.name}<small>{portfolio.base_currency}</small></button>)}{valuation?.provenance[0] && <DataStateBadge dataLevel={valuation.provenance[0].data_level} freshness={valuation.provenance[0].freshness} />}</div>}

    <section className={`${styles.glass} ${styles.tools}`} aria-label="Controles de carteira">
      <form onSubmit={createPortfolio} className={styles.tool}><label htmlFor="portfolio-name">Nova carteira</label><div className={styles.row}><input id="portfolio-name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Nome da carteira" /><select aria-label="Moeda base" value={baseCurrency} onChange={(event) => setBaseCurrency(event.target.value)}><option>BRL</option><option>USD</option></select><button type="submit" className={styles.button}>Criar</button></div></form>
      <form onSubmit={createEvent} className={styles.tool}><label htmlFor="portfolio-event-type">Registrar evento manual</label><div className={styles.grid3}><select id="portfolio-event-type" value={eventType} onChange={(event) => setEventType(event.target.value as PortfolioEventType)}>{eventTypes.map((type) => <option key={type}>{type}</option>)}</select><input aria-label="Moeda do evento" value={currency} onChange={(event) => setCurrency(event.target.value.toUpperCase())} maxLength={3} /><input aria-label="Canonical ID do ativo" value={canonicalId} onChange={(event) => setCanonicalId(event.target.value)} placeholder="canonical_id (BUY/SELL)" /><input aria-label="Quantidade" value={quantity} onChange={(event) => setQuantity(event.target.value)} placeholder="Quantidade" inputMode="decimal" /><input aria-label="Preço unitário" value={unitPrice} onChange={(event) => setUnitPrice(event.target.value)} placeholder="Preço unitário" inputMode="decimal" /><input aria-label="Valor bruto" value={grossAmount} onChange={(event) => setGrossAmount(event.target.value)} placeholder="Valor bruto" inputMode="decimal" /><button type="submit" className={styles.button} disabled={!selectedId}>Registrar</button></div></form>
    </section>

    {portfolios.length === 0 && <section className={styles.glass}><p className="muted">Nenhuma carteira criada ainda. Crie uma acima e registre um depósito para começar.</p></section>}
    {portfolios.length > 0 && <>
      <ul className={styles.metrics} aria-label="Indicadores da carteira">
        <li className={styles.metric}><span>Patrimônio</span><strong>{money(valuation?.total_value_base, base)}</strong></li>
        <li className={styles.metric}><span>P&amp;L não realizado</span><strong className={tone(performance?.unrealized_pnl)}>{money(performance?.unrealized_pnl, base)}</strong></li>
        <li className={styles.metric}><span>P&amp;L realizado</span><strong className={tone(performance?.realized_pnl)}>{money(performance?.realized_pnl, base)}</strong></li>
        <li className={styles.metric}><span>Retorno ponderado no tempo (TWR)</span><strong className={tone(performance?.twr)}>{percent(performance?.twr)}</strong></li>
        <li className={styles.metric}><span>Queda máxima (drawdown)</span><strong>{percent(drawdown?.status === "COMPLETE" ? drawdown.max_drawdown : null)}</strong></li>
      </ul>

      <div className={styles.twoCols}>
        <section className={styles.glass} aria-labelledby="allocation-title">
          <h2 id="allocation-title">Alocação por classe</h2>
          {slices.length === 0 ? <p className="muted">Sem posições nem caixa avaliados ainda.</p> : <div className={styles.donutBox}>
            <svg className={styles.donut} viewBox="0 0 42 42" aria-hidden="true" focusable="false">
              {slices.map((slice, index) => <circle key={slice.label} cx="21" cy="21" r="15.915" pathLength={100} stroke={SLICE_COLORS[index % SLICE_COLORS.length]} strokeDasharray={`${slice.percent} ${100 - slice.percent}`} strokeDashoffset={-slice.start} />)}
            </svg>
            <ul className={styles.legend} aria-label="Peso de cada classe">{slices.map((slice, index) => <li key={slice.label}><i style={{ background: SLICE_COLORS[index % SLICE_COLORS.length] }} />{slice.label}: {slice.percentText}</li>)}</ul>
          </div>}
          {unpriced > 0 && <p className={styles.note}>{unpriced} {unpriced === 1 ? "posição sem preço ficou" : "posições sem preço ficaram"} fora do cálculo.</p>}
        </section>
        <section className={styles.glass} aria-labelledby="equity-title">
          <h2 id="equity-title">Evolução patrimonial</h2>
          <EquityChart points={equityCurve?.points ?? []} markers={markers?.items ?? []} />
          <p className={styles.note}>Pontos ausentes permanecem indisponíveis. Cada marcador referencia um evento persistido do ledger ou uma ação corporativa homologada.</p>
        </section>
      </div>

      <section className={styles.glass} aria-labelledby="positions-title">
        <h2 id="positions-title">Posições atuais</h2>
        <div className="table-wrap"><table>
          <caption className="sr-only">Quantidade, custo médio, valor e P&amp;L</caption>
          <thead><tr><th scope="col">Ativo</th><th scope="col">Classe</th><th scope="col">Quantidade</th><th scope="col">Custo médio</th><th scope="col">Preço</th><th scope="col">Valor atual</th><th scope="col">P&amp;L</th><th scope="col">Estado</th></tr></thead>
          <tbody>{(valuation?.positions ?? []).map((position) => <tr key={position.canonical_id}>
            <th scope="row"><Link href={`/assets?id=${encodeURIComponent(position.canonical_id)}`}>{symbolOf(position.canonical_id)}</Link></th>
            <td>{assetClassLabel(position.canonical_id)}</td>
            <td>{position.quantity}</td>
            <td>{money(position.weighted_average_cost, position.currency)}</td>
            <td>{money(position.price, position.currency)}</td>
            <td>{money(position.market_value_base, base)}</td>
            <td className={tone(position.unrealized_pnl)}>{money(position.unrealized_pnl, base)}</td>
            <td><small>{position.status}{position.missing_inputs?.length ? `: ${position.missing_inputs.join(", ")}` : ""}</small></td>
          </tr>)}</tbody>
        </table></div>
      </section>

      <div className={styles.twoCols}>
        <section className={styles.glass}><h2>Caixa por moeda</h2><dl className="portfolio-metrics">{Object.entries(summary?.cash_balances ?? {}).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{formatDecimal(value)}</dd></div>)}</dl>{Object.keys(summary?.cash_balances ?? {}).length === 0 && <p className="muted">Sem caixa registrado no ledger.</p>}</section>
        <section className={styles.glass}><h2>Decomposição de impactos</h2><dl className="portfolio-metrics"><div><dt>Preço</dt><dd>{decomposition?.price_effect ?? "UNAVAILABLE"}</dd></div><div><dt>FX</dt><dd>{decomposition?.fx_effect ?? "UNAVAILABLE"}</dd></div><div><dt>Fluxo de caixa</dt><dd>{decomposition?.cash_flow_effect ?? "UNAVAILABLE"}</dd></div><div><dt>Taxas</dt><dd>{decomposition?.fees_effect ?? "UNAVAILABLE"}</dd></div><div><dt>Indisponível/não classificado</dt><dd>{decomposition?.unclassified_or_unavailable ?? "UNAVAILABLE"}</dd></div></dl><p className={styles.note}>Fonte e limitações: {decomposition?.provenance.map((item) => `${item.provider}/${item.dataset} (${item.data_level}/${item.freshness})`).join("; ") || "UNAVAILABLE"}</p></section>
      </div>

      <section className={styles.glass} aria-labelledby="income-title">
        <h2 id="income-title">Proventos e eventos corporativos</h2>
        {income.length === 0 ? <p className="muted">Nenhum provento homologado para os ativos desta carteira.</p> : <div className="table-wrap"><table><caption className="sr-only">Proventos e eventos corporativos</caption><thead><tr><th scope="col">Data ex</th><th scope="col">Tipo</th><th scope="col">Ativo</th><th scope="col">Status</th><th scope="col">Pagamento</th><th scope="col">Valor</th><th scope="col">Fonte</th></tr></thead><tbody>{income.map((item) => <tr key={`${item.source_type}-${item.source_id}`}><th scope="row">{item.ex_date ?? "UNAVAILABLE"}</th><td>{item.event_type}</td><td>{item.canonical_id}</td><td>{item.status}</td><td>{item.payment_date ?? "UNAVAILABLE"}</td><td>{item.gross_amount_per_unit ?? item.split_ratio_to ?? "UNAVAILABLE"} {item.currency ?? ""}</td><td>{item.provenance.data_level}/{item.provenance.freshness} · {item.payer}</td></tr>)}</tbody></table></div>}
      </section>

      <section className={styles.glass} aria-labelledby="audit-title">
        <h2 id="audit-title">Detalhes e auditoria</h2>
        <details className={styles.more}><summary>Resumo factual e metodologia</summary><dl className="portfolio-metrics"><div><dt>Patrimônio em {valuation?.base_currency ?? "moeda-base"}</dt><dd>{valuation?.total_value_base ?? "UNAVAILABLE"}</dd></div><div><dt>P&amp;L realizado</dt><dd>{performance?.realized_pnl ?? "UNAVAILABLE"}</dd></div><div><dt>P&amp;L não realizado</dt><dd>{performance?.unrealized_pnl ?? "UNAVAILABLE"}</dd></div><div><dt>TWR</dt><dd>{performance?.twr ?? "UNAVAILABLE"}</dd></div></dl><p className="state-note">Estado: {performance?.status ?? "UNAVAILABLE"}. Metodologia: {performance?.methodology ?? "sem dados"}</p><p className="state-note">Proveniência: {valuation?.provenance.map((item) => `${item.provider}/${item.dataset} · ${item.data_level}/${item.freshness} · fonte ${item.source_timestamp} · coleta ${item.collected_at}`).join("; ") || "UNAVAILABLE"}</p></details>
        <details className={styles.more}><summary>Drawdown dia a dia</summary>{drawdown?.status === "COMPLETE" ? <><dl className="portfolio-metrics"><div><dt>Drawdown máximo (fração do pico)</dt><dd>{drawdown.max_drawdown}</dd></div><div><dt>Pico</dt><dd>{drawdown.peak_date ?? "—"}</dd></div><div><dt>Vale</dt><dd>{drawdown.trough_date ?? "—"}</dd></div></dl><div className="table-wrap"><table><caption>Drawdown diário em relação ao maior patrimônio anterior ({drawdown.base_currency})</caption><thead><tr><th scope="col">Data</th><th scope="col">Patrimônio</th><th scope="col">Pico</th><th scope="col">Drawdown</th></tr></thead><tbody>{drawdown.points.map((point) => <tr key={point.valuation_date}><th scope="row">{point.valuation_date}</th><td>{point.total_value_base}</td><td>{point.peak_value_base}</td><td>{point.drawdown}</td></tr>)}</tbody></table></div></> : <p className="muted">Indisponível: {drawdown?.missing_inputs.join(", ") || "sem dados"}.</p>}<p className="muted">Metodologia: {drawdown?.methodology ?? "sem dados"}</p></details>
        <details className={styles.more}><summary>Tabela da evolução patrimonial</summary><div className="table-wrap"><table><caption>Fallback tabular da equity curve</caption><thead><tr><th scope="col">Data</th><th scope="col">Patrimônio</th><th scope="col">Estado</th><th scope="col">Dados ausentes</th></tr></thead><tbody>{(equityCurve?.points ?? []).map((point) => <tr key={point.valuation_date}><th scope="row">{point.valuation_date}</th><td>{point.total_value_base ?? "UNAVAILABLE"}</td><td>{point.valuation_status} / {point.freshness}</td><td>{point.missing_inputs.join(", ") || "—"}</td></tr>)}</tbody></table></div></details>
        <details className={styles.more}><summary>Tabela dos marcadores do gráfico</summary><div className="table-wrap"><table><caption>Fallback tabular dos marcadores</caption><thead><tr><th scope="col">Data</th><th scope="col">Tipo</th><th scope="col">Ativo</th><th scope="col">Origem</th><th scope="col">Fonte</th></tr></thead><tbody>{(markers?.items ?? []).map((marker) => <tr key={`${marker.source_type}-${marker.source_id}`}><th scope="row">{marker.occurred_at}</th><td>{marker.event_type}</td><td>{marker.canonical_id}</td><td>{marker.source_type} · {marker.source_id}</td><td>{marker.provenance.data_level}/{marker.provenance.freshness}</td></tr>)}</tbody></table></div></details>
        <details className={styles.more}><summary>Ledger append-only</summary><div className="table-wrap"><table><caption>Eventos manuais, ordenados por ocorrência</caption><thead><tr><th scope="col">Data</th><th scope="col">Tipo</th><th scope="col">Ativo</th><th scope="col">Moeda</th><th scope="col">Valor</th></tr></thead><tbody>{events.map((item) => <tr key={item.id}><th scope="row">{item.occurred_at}</th><td>{item.event_type}</td><td>{item.canonical_id ?? "—"}</td><td>{item.currency}</td><td>{item.gross_amount ?? item.unit_price ?? "—"}</td></tr>)}</tbody></table></div></details>
      </section>
    </>}
  </main>;
}

// Static page (ADR-005): the asset passed by the asset page is read on the client.
export function PortfoliosFromQuery() {
  const requested = useSearchParams().get("canonical_id") ?? "";
  return <PortfoliosPanel initialCanonicalId={CANONICAL_ID.test(requested) ? requested : ""} />;
}
