"use client";

import type { components } from "../generated/api";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ParticleChart } from "./particle-chart";
import { ChartTypeToggle, effectiveChartKind } from "./chart-type-toggle";
import { candleAvailability, type ChartKind } from "../lib/chart-geometry";
import { MorningCallPanel } from "./morning-call";
import { DISPLAY_MAX_POINTS, downsamplingSummary } from "../lib/downsampling-note";
import { SiteHeader } from "./site-header";
import { FINANCIAL_DISCLAIMER } from "../lib/disclaimers";
import { describeChange } from "../lib/price-direction";
import { formatReason } from "../lib/unavailable-reasons";
import { DEFAULT_BENCHMARK_ID } from "../lib/comparison-defaults";

type PublicQuote = components["schemas"]["PublicQuote"];
type PublicHistorySeries = components["schemas"]["PublicHistorySeries"];
type PublicHistoryPoint = components["schemas"]["PublicHistoryPoint"];
type DataLevel = components["schemas"]["DataLevel"];
type Freshness = components["schemas"]["Freshness"];
type HistoryPeriod = components["schemas"]["HistoryPeriod"];
type SeriesMode = components["schemas"]["SeriesMode"];
type InstrumentSummary = components["schemas"]["InstrumentSummary"];
type InstrumentList = components["schemas"]["InstrumentList"];

const periods = ["1D", "5D", "1M", "3M", "6M", "YTD", "1A", "5A", "MAX"] as const satisfies readonly HistoryPeriod[];
const modes = ["PRICE", "INDEX_100"] as const satisfies readonly SeriesMode[];

export function DataStateBadge({ dataLevel, freshness }: { dataLevel: DataLevel; freshness: Freshness }) {
  const label = dataLevel === "DEMO" ? "DADOS DE DEMONSTRAÇÃO" : `${dataLevel} · ${freshness}`;
  return (
    <span className={`data-badge data-badge-${freshness.toLowerCase()}`} aria-label={`Estado ${freshness}, nível ${dataLevel}`}>
      <span aria-hidden="true" className="badge-mark" />
      {label}{dataLevel === "DEMO" && <span className="sr-only">DEMO · {freshness}</span>}
    </span>
  );
}

export function ProvenancePanel({ data }: { data: PublicQuote | PublicHistorySeries }) {
  return (
    <section className="provenance-panel" aria-labelledby="provenance-title">
      <div className="section-heading"><p className="eyebrow">PROVENANCE</p><h2 id="provenance-title">Origem e estado</h2></div>
      <dl className="meta-grid">
        <div><dt>Provider</dt><dd>{data.provider}</dd></div>
        <div><dt>Dataset</dt><dd>{data.dataset}</dd></div>
        <div><dt>Data level</dt><dd>{data.data_level}</dd></div>
        <div><dt>Freshness</dt><dd>{data.freshness}</dd></div>
        <div><dt>Horário oficial</dt><dd>{data.timestamp_official ?? (data.session_date ? `Só a data do pregão: ${data.session_date}` : "Indisponível")}</dd></div>
        <div><dt>Coletado em</dt><dd>{data.timestamp_collected}</dd></div>
        {data.observed_at && <div><dt>Observado em</dt><dd>{data.observed_at}</dd></div>}
        <div><dt>Latência</dt><dd>{data.latency_ms == null ? "Indisponível" : `${data.latency_ms} ms`}</dd></div>
        {data.timezone && <div><dt>Fuso do mercado</dt><dd>{data.timezone}</dd></div>}
        {data.quality_status && <div><dt>Qualidade</dt><dd>{data.quality_status}</dd></div>}
        {data.license_status && <div><dt>Licença</dt><dd>{data.license_status}</dd></div>}
        <div><dt>Fonte reserva</dt><dd>{data.fallback_used ? "Sim: a fonte principal não respondeu" : "Não"}</dd></div>
        <div><dt>DEMO</dt><dd>{data.is_demo ? "Sim, dado sintético" : "Não"}</dd></div>
      </dl>
      {data.limitations.length > 0 && <p className="limitation-note">Limitações: {data.limitations.join("; ")}</p>}
      {data.unavailable_reason && <p className="state-note">Motivo: {formatReason(data.unavailable_reason)}</p>}
    </section>
  );
}

export function MarketStatusBar({ data }: { data?: PublicQuote | PublicHistorySeries }) {
  return (
    <div className="status-bar" role="status">
      <span>{data ? <DataStateBadge dataLevel={data.data_level} freshness={data.freshness} /> : "BACKEND / AGUARDANDO"}</span>
      <span>{data?.latency_ms == null ? "latência indisponível" : `${data.latency_ms} ms`}</span>
      <span>{data?.timestamp_collected ? `coletado ${data.timestamp_collected}` : "sem coleta"}</span>
    </div>
  );
}

export function PriceChange({ quote }: { quote: PublicQuote }) {
  const change = describeChange(quote.change, quote.change_percent, quote.currency);
  if (!change) return <p className="asset-change">Variação indisponível</p>;
  const { cue } = change;
  return (
    <p className={`asset-change direction-${change.direction.toLowerCase()}`}>
      <span aria-hidden="true">{cue.glyph}</span> {change.text} · {cue.word} · base: fechamento anterior
    </p>
  );
}

export function AssetContextPanel({ quote, loading, error, selectedId }: { quote?: PublicQuote; loading: boolean; error?: string; selectedId: string }) {
  return (
    <aside className="asset-context" aria-labelledby="asset-context-title">
      <div className="section-heading"><p className="eyebrow">ATIVO SELECIONADO</p><h2 id="asset-context-title">{quote?.symbol ?? (selectedId || "Ativo indisponível")}</h2></div>
      {loading && <p className="muted">Carregando contrato…</p>}
      {error && <p className="state-note" role="alert">Dados indisponíveis: {error}</p>}
      {!loading && !error && quote && (
        <>
          <p className="asset-name">{quote.name}</p>
          <p className="asset-price">{quote.price == null ? "Indisponível" : `${quote.currency} ${quote.price}`}</p>
          <PriceChange quote={quote} />
          <dl className="meta-grid compact">
            <div><dt>Moeda</dt><dd>{quote.currency}</dd></div>
            <div><dt>Bolsa</dt><dd>{quote.exchange ?? "Indisponível"}</dd></div>
          </dl>
          <ProvenancePanel data={quote} />
          <p><Link href={`/assets?id=${encodeURIComponent(quote.canonical_id)}`}>Abrir página do ativo</Link></p>
        </>
      )}
      {!loading && !error && !quote && <p className="muted">Nenhum dado disponível.</p>}
    </aside>
  );
}

export function PeriodSelector({ value, onChange }: { value: HistoryPeriod; onChange: (period: HistoryPeriod) => void }) {
  return <fieldset className="control-group"><legend>Período</legend><div className="control-row">{periods.map((period) => <button type="button" className={period === value ? "control active" : "control"} aria-pressed={period === value} key={period} onClick={() => onChange(period)}>{period}</button>)}</div></fieldset>;
}

export function SeriesModeToggle({ value, onChange }: { value: SeriesMode; onChange: (mode: SeriesMode) => void }) {
  return <fieldset className="control-group"><legend>Modo de comparação</legend><div className="control-row">{modes.map((mode) => <button type="button" className={mode === value ? "control active" : "control"} aria-pressed={mode === value} key={mode} onClick={() => onChange(mode)}>{mode}</button>)}</div></fieldset>;
}

export function AccessibleDataTable({ points, reducedFrom, ohlc = false }: { points: PublicHistoryPoint[]; reducedFrom?: number; ohlc?: boolean }) {
  const caption = reducedFrom ? `Fallback tabular da série histórica (${points.length} de ${reducedFrom} pontos, redução M4 declarada)` : "Fallback tabular da série histórica";
  // With candles on screen, the equivalent table carries the same OHLC and volume.
  return (
    <div className="table-wrap"><table><caption>{caption}</caption><thead><tr><th scope="col">Sessão</th>{ohlc && <><th scope="col">Abertura</th><th scope="col">Máxima</th><th scope="col">Mínima</th></>}<th scope="col">Fechamento</th>{ohlc && <th scope="col">Volume</th>}<th scope="col">Índice 100</th><th scope="col">Gap</th></tr></thead><tbody>{points.map((point) => <tr key={`${point.timestamp}-${point.session_date}`}><th scope="row">{point.session_date}</th>{ohlc && <><td>{point.open ?? "—"}</td><td>{point.high ?? "—"}</td><td>{point.low ?? "—"}</td></>}<td>{point.close ?? "—"}</td>{ohlc && <td>{point.volume ?? "—"}</td>}<td>{point.index_100 ?? "—"}</td><td>{point.is_gap ? "Sim" : "Não"}</td></tr>)}</tbody></table></div>
  );
}

async function fetchJson<T>(url: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal, headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json() as Promise<T>;
}

export function InstrumentSearch({ onSelect }: { onSelect: (canonicalId: string) => void }) {
  const [query, setQuery] = useState("");
  const [state, setState] = useState<{ key: string; data?: InstrumentList }>({ key: "" });
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  useEffect(() => {
    const normalized = query.trim();
    if (normalized.length < 2) return;
    const controller = new AbortController();
    fetchJson<InstrumentList>(`${apiBase}/api/v1/instruments/search?q=${encodeURIComponent(normalized)}`, controller.signal).then((data) => setState({ key: normalized, data })).catch(() => undefined);
    return () => controller.abort();
  }, [apiBase, query]);
  const items: InstrumentSummary[] = state.key === query.trim() ? state.data?.items ?? [] : [];
  return <div className="search-wrap"><label className="search"><span className="sr-only">Buscar instrumento</span><input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar símbolo ou nome" /></label>{items.length > 0 && <ul id="instrument-results" className="search-results" role="listbox">{items.map((item) => <li key={item.canonical_id}><button type="button" role="option" aria-selected={false} onClick={() => { onSelect(item.canonical_id); setQuery(item.display_symbol); }}>{item.display_symbol} · {item.name}<small>{item.support_state}</small></button></li>)}</ul>}{query.trim().length >= 2 && state.key === query.trim() && items.length === 0 && <p className="search-empty">Nenhum instrumento no catálogo.</p>}</div>;
}

export function TerminalShell() {
  const [period, setPeriod] = useState<HistoryPeriod>("1M");
  const [mode, setMode] = useState<SeriesMode>("PRICE");
  const [chartKind, setChartKind] = useState<ChartKind>("line");
  const [selectedCanonicalId, setSelectedCanonicalId] = useState("");
  const [quoteState, setQuoteState] = useState<{ key: string; data?: PublicQuote; error?: string }>({ key: "" });
  const [historyState, setHistoryState] = useState<{ key: string; data?: PublicHistorySeries; error?: string }>({ key: "" });
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  const quoteKey = `${apiBase}|${selectedCanonicalId}`;
  const historyKey = `${quoteKey}|${period}|${mode}`;
  const quote = quoteState.key === quoteKey ? quoteState.data : undefined;
  const quoteError = quoteState.key === quoteKey ? quoteState.error : undefined;
  const quoteLoading = quoteState.key !== quoteKey;
  const history = historyState.key === historyKey ? historyState.data : undefined;
  const historyError = historyState.key === historyKey ? historyState.error : undefined;
  const historyLoading = historyState.key !== historyKey;

  useEffect(() => {
    if (selectedCanonicalId) return;
    const controller = new AbortController();
    fetchJson<InstrumentList>(`${apiBase}/api/v1/instruments/search?q=.&limit=1`, controller.signal)
      .then((data) => setSelectedCanonicalId((current) => current || data.items[0]?.canonical_id || ""))
      .catch(() => undefined);
    return () => controller.abort();
  }, [apiBase, selectedCanonicalId]);

  useEffect(() => {
    if (!selectedCanonicalId) return;
    const controller = new AbortController();
    fetchJson<PublicQuote>(`${apiBase}/api/v1/market-data/quotes/${encodeURIComponent(selectedCanonicalId)}`, controller.signal).then((data) => setQuoteState({ key: `${apiBase}|${selectedCanonicalId}`, data })).catch((error: unknown) => { if (error instanceof Error && error.name !== "AbortError") setQuoteState({ key: `${apiBase}|${selectedCanonicalId}`, error: error.message }); });
    return () => controller.abort();
  }, [apiBase, selectedCanonicalId]);

  useEffect(() => {
    if (!selectedCanonicalId) return;
    const controller = new AbortController();
    fetchJson<PublicHistorySeries>(`${apiBase}/api/v1/market-data/history/${encodeURIComponent(selectedCanonicalId)}?period=${period}&mode=${mode}&adjustment_type=UNADJUSTED&max_points=${DISPLAY_MAX_POINTS}`, controller.signal).then((data) => setHistoryState({ key: historyKey, data })).catch((error: unknown) => { if (error instanceof Error && error.name !== "AbortError") setHistoryState({ key: historyKey, error: error.message }); });
    return () => controller.abort();
  }, [historyKey, apiBase, mode, period, selectedCanonicalId]);

  return <div className="terminal-root">
    <SiteHeader search={<InstrumentSearch onSelect={setSelectedCanonicalId} />} extraLinks={<a href="#morning-call">Morning Call</a>} />
    <div className="terminal-grid">
      <aside className="left-rail" aria-label="Contexto operacional"><MorningCallPanel /><section><p className="eyebrow">AGENDA / EVENTOS</p><p className="muted">Nenhum evento carregado. Sem notícia inventada.</p><span className="state-label">UNAVAILABLE · DEMO</span></section></aside>
      <main id="main-content" className="main-panel"><div className="panel-heading"><div><p className="eyebrow">DASHBOARD / MERCADO</p><h1>Observatório de mercado</h1></div><span className="state-label">P0 · INFORMATIVO</span></div><section className="series-panel" aria-labelledby="series-title"><div className="series-heading"><div><p className="eyebrow">SÉRIE HISTÓRICA</p><h2 id="series-title">{quote?.symbol ?? selectedCanonicalId} · {period}</h2></div><span className="series-note">Sem suavização</span></div><div className="controls"><PeriodSelector value={period} onChange={setPeriod} /><SeriesModeToggle value={mode} onChange={setMode} />{history && <ChartTypeToggle value={chartKind} onChange={setChartKind} availability={candleAvailability(history)} />}</div>{historyLoading && <p className="loading-state">Carregando série tipada…</p>}{historyError && <p className="state-note" role="alert">Série indisponível: {historyError}</p>}{history && !historyLoading && <>{downsamplingSummary(history.downsampling) && <p className="muted" role="note">{downsamplingSummary(history.downsampling)}</p>}<ParticleChart series={history} kind={effectiveChartKind(chartKind, candleAvailability(history))} /><AccessibleDataTable points={history.points} reducedFrom={history.downsampling?.original_points} ohlc={effectiveChartKind(chartKind, candleAvailability(history)) === "candles"} /></>}{!historyLoading && !historyError && !history && <p className="muted">Nenhuma série disponível.</p>}{selectedCanonicalId && <p className="comparison-note"><Link href={`/compare?ids=${encodeURIComponent(`${selectedCanonicalId},${DEFAULT_BENCHMARK_ID}`)}`}>Comparar com o Ibovespa</Link> em INDEX_100, com tabela equivalente.</p>}</section></main>
      <AssetContextPanel quote={quote} loading={quoteLoading} error={quoteError} selectedId={selectedCanonicalId} />
    </div>
    <footer><MarketStatusBar data={history ?? quote} /><span>{FINANCIAL_DISCLAIMER}</span></footer>
  </div>;
}
