"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import type { components } from "../generated/api";
import { EquityChart } from "./equity-chart";
import { DataStateBadge } from "./market-data";

type Portfolio = components["schemas"]["PortfolioResponse"];
type PortfolioList = components["schemas"]["PortfolioListResponse"];
type PortfolioEvent = components["schemas"]["PortfolioEventResponse"];
type PortfolioEventRequest = components["schemas"]["PortfolioEventRequest"];
type PortfolioEventType = components["schemas"]["PortfolioEventType"];
type PortfolioSummary = components["schemas"]["PortfolioSummaryResponse"];
type PortfolioValuation = components["schemas"]["PortfolioValuationResponse"];
type PortfolioPerformance = components["schemas"]["PortfolioPerformanceResponse"];
type EquityCurve = components["schemas"]["EquityCurveResponse"];
type PerformanceDecomposition = components["schemas"]["PerformanceDecompositionResponse"];
type PortfolioIncome = components["schemas"]["PortfolioIncomeResponse"];
type PortfolioEventMarkers = components["schemas"]["PortfolioEventMarkersResponse"];

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const eventTypes = ["CASH_DEPOSIT", "CASH_WITHDRAWAL", "BUY", "SELL", "FEE"] as const satisfies readonly PortfolioEventType[];

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", Accept: "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const error = new Error(`HTTP ${response.status}`) as Error & { status?: number };
    error.status = response.status;
    throw error;
  }
  return response.json() as Promise<T>;
}

function isSignedOut(error: unknown): boolean {
  return error instanceof Error && (error as Error & { status?: number }).status === 401;
}

export function PortfoliosPanel() {
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
  const [eventType, setEventType] = useState<PortfolioEventType>("CASH_DEPOSIT");
  const [currency, setCurrency] = useState("BRL");
  const [canonicalId, setCanonicalId] = useState("");
  const [quantity, setQuantity] = useState("");
  const [unitPrice, setUnitPrice] = useState("");
  const [grossAmount, setGrossAmount] = useState("");
  const [loading, setLoading] = useState(true);
  const [signedOut, setSignedOut] = useState(false);
  const [error, setError] = useState<string>();

  const loadDetails = useCallback(async (portfolioId: string) => {
    if (!portfolioId) return;
    try {
      const [nextSummary, nextEvents, nextValuation, nextPerformance, nextCurve, nextDecomposition, nextIncome, nextMarkers] = await Promise.all([
        requestJson<PortfolioSummary>(`/api/v1/portfolios/${portfolioId}/summary`),
        requestJson<PortfolioEvent[]>(`/api/v1/portfolios/${portfolioId}/events`),
        requestJson<PortfolioValuation>(`/api/v1/portfolios/${portfolioId}/valuation`),
        requestJson<PortfolioPerformance>(`/api/v1/portfolios/${portfolioId}/performance`),
        requestJson<EquityCurve>(`/api/v1/portfolios/${portfolioId}/equity-curve`),
        requestJson<PerformanceDecomposition>(`/api/v1/portfolios/${portfolioId}/performance/decomposition`),
        requestJson<PortfolioIncome[]>(`/api/v1/portfolios/${portfolioId}/income`),
        requestJson<PortfolioEventMarkers>(`/api/v1/portfolios/${portfolioId}/event-markers`),
      ]);
      setSummary(nextSummary);
      setEvents(nextEvents);
      setValuation(nextValuation);
      setPerformance(nextPerformance);
      setEquityCurve(nextCurve);
      setDecomposition(nextDecomposition);
      setIncome(nextIncome);
      setMarkers(nextMarkers);
    } catch (reason) {
      if (isSignedOut(reason)) setSignedOut(true);
      else setError("Não foi possível carregar os detalhes da carteira.");
    }
  }, []);

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
        else setError("Não foi possível carregar suas carteiras.");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    let active = true;
    Promise.all([
      requestJson<PortfolioSummary>(`/api/v1/portfolios/${selectedId}/summary`),
      requestJson<PortfolioEvent[]>(`/api/v1/portfolios/${selectedId}/events`),
      requestJson<PortfolioValuation>(`/api/v1/portfolios/${selectedId}/valuation`),
      requestJson<PortfolioPerformance>(`/api/v1/portfolios/${selectedId}/performance`),
      requestJson<EquityCurve>(`/api/v1/portfolios/${selectedId}/equity-curve`),
      requestJson<PerformanceDecomposition>(`/api/v1/portfolios/${selectedId}/performance/decomposition`),
      requestJson<PortfolioIncome[]>(`/api/v1/portfolios/${selectedId}/income`),
      requestJson<PortfolioEventMarkers>(`/api/v1/portfolios/${selectedId}/event-markers`),
    ]).then(([nextSummary, nextEvents, nextValuation, nextPerformance, nextCurve, nextDecomposition, nextIncome, nextMarkers]) => {
      if (!active) return;
      setSummary(nextSummary);
      setEvents(nextEvents);
      setValuation(nextValuation);
      setPerformance(nextPerformance);
      setEquityCurve(nextCurve);
      setDecomposition(nextDecomposition);
      setIncome(nextIncome);
      setMarkers(nextMarkers);
    }).catch((reason) => {
      if (!active) return;
      if (isSignedOut(reason)) setSignedOut(true);
      else setError("Não foi possível carregar os detalhes da carteira.");
    });
    return () => { active = false; };
  }, [selectedId]);

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

  if (loading) return <main className="portfolios-page terminal-root"><h1 className="sr-only">Carteiras informativas</h1><p className="loading-state">Carregando carteiras…</p></main>;
  if (signedOut) return <main className="portfolios-page terminal-root"><section className="portfolios-card" aria-labelledby="portfolios-title"><p className="eyebrow">ÁREA PRIVADA</p><h1 id="portfolios-title">Carteiras</h1><p className="muted">Entre para acessar suas carteiras informativas.</p><Link className="auth-submit portfolios-link" href="/login">Ir para login</Link></section></main>;

  return <main className="portfolios-page terminal-root" data-theme="dark">
    <header className="portfolios-header"><div><p className="eyebrow">PARTICLE ATLAS / ÁREA PRIVADA</p><h1 id="portfolios-title">Carteiras informativas</h1></div><Link href="/" className="portfolios-back">Voltar ao terminal</Link></header>
    <p className="portfolios-disclaimer">Esta carteira mostra eventos, caixa, posições, valuation, P&amp;L e TWR factuais, sempre acompanhados de metodologia. Estados possíveis: DEMO, STALE, PARTIAL e UNAVAILABLE.</p>
    {error && <p className="state-note" role="alert">{error}</p>}
    {valuation?.provenance[0] && <DataStateBadge dataLevel={valuation.provenance[0].data_level} freshness={valuation.provenance[0].freshness} />}
    <section className="portfolios-toolbar" aria-label="Controles de carteira">
      <form onSubmit={createPortfolio} className="portfolio-form"><label htmlFor="portfolio-name">Nova carteira</label><div className="portfolio-form-row"><input id="portfolio-name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Nome da carteira" /><select aria-label="Moeda base" value={baseCurrency} onChange={(event) => setBaseCurrency(event.target.value)}><option>BRL</option><option>USD</option></select><button type="submit">Criar</button></div></form>
      <form onSubmit={createEvent} className="portfolio-form"><label htmlFor="portfolio-event-type">Registrar evento manual</label><div className="portfolio-form-grid"><select id="portfolio-event-type" value={eventType} onChange={(event) => setEventType(event.target.value as PortfolioEventType)}>{eventTypes.map((type) => <option key={type}>{type}</option>)}</select><input aria-label="Moeda do evento" value={currency} onChange={(event) => setCurrency(event.target.value.toUpperCase())} maxLength={3} /><input aria-label="Canonical ID do ativo" value={canonicalId} onChange={(event) => setCanonicalId(event.target.value)} placeholder="canonical_id (BUY/SELL)" /><input aria-label="Quantidade" value={quantity} onChange={(event) => setQuantity(event.target.value)} placeholder="Quantidade" inputMode="decimal" /><input aria-label="Preço unitário" value={unitPrice} onChange={(event) => setUnitPrice(event.target.value)} placeholder="Preço unitário" inputMode="decimal" /><input aria-label="Valor bruto" value={grossAmount} onChange={(event) => setGrossAmount(event.target.value)} placeholder="Valor bruto" inputMode="decimal" /><button type="submit" disabled={!selectedId}>Registrar</button></div></form>
    </section>
    {portfolios.length === 0 && <section className="portfolios-card"><p className="muted">Nenhuma carteira criada ainda.</p></section>}
    {portfolios.length > 0 && <><section className="portfolio-selector" aria-label="Selecionar carteira"><label htmlFor="portfolio-select">Carteira</label><select id="portfolio-select" value={selectedId} onChange={(event) => setSelectedId(event.target.value)}>{portfolios.map((portfolio) => <option key={portfolio.id} value={portfolio.id}>{portfolio.name} · {portfolio.base_currency}</option>)}</select></section><section className="portfolio-summary-grid"><div className="portfolios-card"><h2>Resumo factual</h2><dl className="portfolio-metrics"><div><dt>Patrimônio em {valuation?.base_currency ?? "moeda-base"}</dt><dd>{valuation?.total_value_base ?? "UNAVAILABLE"}</dd></div><div><dt>P&amp;L realizado</dt><dd>{performance?.realized_pnl ?? "UNAVAILABLE"}</dd></div><div><dt>P&amp;L não realizado</dt><dd>{performance?.unrealized_pnl ?? "UNAVAILABLE"}</dd></div><div><dt>TWR</dt><dd>{performance?.twr ?? "UNAVAILABLE"}</dd></div></dl><p className="state-note">Estado: {performance?.status ?? "UNAVAILABLE"}. Metodologia: {performance?.methodology ?? "sem dados"}</p><p className="state-note">Proveniência: {valuation?.provenance.map((item) => `${item.provider}/${item.dataset} · ${item.data_level}/${item.freshness} · fonte ${item.source_timestamp} · coleta ${item.collected_at}`).join("; ") || "UNAVAILABLE"}</p></div><div className="portfolios-card"><h2>Caixa por moeda</h2><table><caption>Saldos reconstruídos do ledger</caption><thead><tr><th scope="col">Moeda</th><th scope="col">Saldo</th></tr></thead><tbody>{Object.entries(summary?.cash_balances ?? {}).map(([key, value]) => <tr key={key}><th scope="row">{key}</th><td>{value}</td></tr>)}</tbody></table></div></section><section className="portfolios-card">
      <h2>Evolução patrimonial</h2>
      <p className="muted">Gráfico SVG leve; pontos ausentes permanecem indisponíveis.</p>
      <EquityChart points={equityCurve?.points ?? []} markers={markers?.items ?? []} />
      <h3>Eventos no gráfico</h3>
      <p className="muted">Cada marcador referencia um evento persistido do ledger ou uma ação corporativa homologada.</p>
      <table><caption>Proventos e eventos corporativos</caption><thead><tr><th scope="col">Data ex</th><th scope="col">Tipo</th><th scope="col">Ativo</th><th scope="col">Status</th><th scope="col">Pagamento</th><th scope="col">Valor</th><th scope="col">Fonte</th></tr></thead><tbody>{income.map((item) => <tr key={`${item.source_type}-${item.source_id}`}><th scope="row">{item.ex_date ?? "UNAVAILABLE"}</th><td>{item.event_type}</td><td>{item.canonical_id}</td><td>{item.status}</td><td>{item.payment_date ?? "UNAVAILABLE"}</td><td>{item.gross_amount_per_unit ?? item.split_ratio_to ?? "UNAVAILABLE"} {item.currency ?? ""}</td><td>{item.provenance.data_level}/{item.provenance.freshness} · {item.payer}</td></tr>)}</tbody></table>
      <table><caption>Fallback tabular dos marcadores</caption><thead><tr><th scope="col">Data</th><th scope="col">Tipo</th><th scope="col">Ativo</th><th scope="col">Origem</th><th scope="col">Fonte</th></tr></thead><tbody>{(markers?.items ?? []).map((marker) => <tr key={`${marker.source_type}-${marker.source_id}`}><th scope="row">{marker.occurred_at}</th><td>{marker.event_type}</td><td>{marker.canonical_id}</td><td>{marker.source_type} · {marker.source_id}</td><td>{marker.provenance.data_level}/{marker.provenance.freshness}</td></tr>)}</tbody></table>
      <table><caption>Fallback tabular da equity curve</caption><thead><tr><th scope="col">Data</th><th scope="col">Patrimônio</th><th scope="col">Estado</th><th scope="col">Dados ausentes</th></tr></thead><tbody>{(equityCurve?.points ?? []).map((point) => <tr key={point.valuation_date}><th scope="row">{point.valuation_date}</th><td>{point.total_value_base ?? "UNAVAILABLE"}</td><td>{point.valuation_status} / {point.freshness}</td><td>{point.missing_inputs.join(", ") || "—"}</td></tr>)}</tbody></table></section><section className="portfolio-summary-grid"><div className="portfolios-card"><h2>Posições atuais</h2><table><caption>Quantidade, custo médio, valor e P&amp;L</caption><thead><tr><th scope="col">Ativo</th><th scope="col">Quantidade</th><th scope="col">Custo médio</th><th scope="col">Valor atual</th><th scope="col">P&amp;L</th></tr></thead><tbody>{(valuation?.positions ?? []).map((position) => <tr key={position.canonical_id}><th scope="row">{position.canonical_id}</th><td>{position.quantity}</td><td>{position.weighted_average_cost}</td><td>{position.market_value_base ?? "UNAVAILABLE"}</td><td>{position.unrealized_pnl ?? "UNAVAILABLE"}</td></tr>)}</tbody></table></div><div className="portfolios-card"><h2>Decomposição de impactos</h2><dl className="portfolio-metrics"><div><dt>Preço</dt><dd>{decomposition?.price_effect ?? "UNAVAILABLE"}</dd></div><div><dt>FX</dt><dd>{decomposition?.fx_effect ?? "UNAVAILABLE"}</dd></div><div><dt>Fluxo de caixa</dt><dd>{decomposition?.cash_flow_effect ?? "UNAVAILABLE"}</dd></div><div><dt>Taxas</dt><dd>{decomposition?.fees_effect ?? "UNAVAILABLE"}</dd></div><div><dt>Indisponível/não classificado</dt><dd>{decomposition?.unclassified_or_unavailable ?? "UNAVAILABLE"}</dd></div></dl><p className="state-note">Fonte e limitações: {decomposition?.provenance.map((item) => `${item.provider}/${item.dataset} (${item.data_level}/${item.freshness})`).join("; ") || "UNAVAILABLE"}</p></div></section><section className="portfolios-card"><h2>Ledger append-only</h2><table><caption>Eventos manuais, ordenados por ocorrência</caption><thead><tr><th scope="col">Data</th><th scope="col">Tipo</th><th scope="col">Ativo</th><th scope="col">Moeda</th><th scope="col">Valor</th></tr></thead><tbody>{events.map((item) => <tr key={item.id}><th scope="row">{item.occurred_at}</th><td>{item.event_type}</td><td>{item.canonical_id ?? "—"}</td><td>{item.currency}</td><td>{item.gross_amount ?? item.unit_price ?? "—"}</td></tr>)}</tbody></table></section></>}
  </main>;
}
