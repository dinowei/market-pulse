"use client";

import type { components } from "../generated/api";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { MorningCallPanel } from "./morning-call";
import { FINANCIAL_DISCLAIMER } from "../lib/disclaimers";
import { describeChange } from "../lib/price-direction";
import { formatReason } from "../lib/unavailable-reasons";
import { apiRequest, isAbort } from "../lib/api-client";
import { DataStateBadge } from "./data-table";

// Shared pieces keep their historical import path (asset page, comparison and tests).
export { AccessibleDataTable, DataStateBadge } from "./data-table";
export { InstrumentSearch } from "./instrument-search";

type PublicQuote = components["schemas"]["PublicQuote"];
type PublicHistorySeries = components["schemas"]["PublicHistorySeries"];
type HistoryPeriod = components["schemas"]["HistoryPeriod"];
type SeriesMode = components["schemas"]["SeriesMode"];
type InstrumentSummary = components["schemas"]["InstrumentSummary"];
type InstrumentList = components["schemas"]["InstrumentList"];
type BenchmarkItem = components["schemas"]["BenchmarkItem"];
// DataLevel and Freshness reach the screen through DataStateBadge on every number.

const periods = ["1D", "5D", "1M", "3M", "6M", "YTD", "1A", "5A", "MAX"] as const satisfies readonly HistoryPeriod[];
const modes = ["PRICE", "INDEX_100"] as const satisfies readonly SeriesMode[];

// Canvas chart workspace, loaded after the page (ADR-028). Fallback tabular: the same series
// as a table lives inside it, so the chart is never the only way to read the data.
const ChartWorkspace = dynamic(() => import("./chart-workspace").then((module) => module.ChartWorkspace), {
  ssr: false,
  loading: () => <div className="card loading-state">Carregando o gráfico…</div>,
});

export function ProvenancePanel({ data }: { data: PublicQuote | PublicHistorySeries }) {
  return (
    <section className="provenance-panel" aria-labelledby="provenance-title">
      <h2 id="provenance-title">Origem e estado</h2>
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
      <span>{data ? <DataStateBadge dataLevel={data.data_level} freshness={data.freshness} /> : "Aguardando a API"}</span>
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
      <div className="section-heading"><h2 id="asset-context-title">{quote?.symbol ?? (selectedId || "Ativo indisponível")}</h2>{quote && <DataStateBadge dataLevel={quote.data_level} freshness={quote.freshness} />}</div>
      {loading && <p className="muted">Carregando cotação…</p>}
      {error && <p className="state-note" role="alert">Dados indisponíveis: {error}</p>}
      {!loading && !error && quote && (
        <>
          <p className="asset-name">{quote.name}</p>
          <p className="asset-price">{quote.price == null ? "Indisponível" : `${quote.currency} ${Number(quote.price).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`}</p>
          <PriceChange quote={quote} />
          {quote.unavailable_reason === "SESSION_REQUIRED" && <p><Link href="/login">Entre</Link> para ver a cotação real.</p>}
          <dl className="meta-grid compact">
            <div><dt>Moeda</dt><dd>{quote.currency}</dd></div>
            <div><dt>Bolsa</dt><dd>{quote.exchange ?? "Indisponível"}</dd></div>
          </dl>
          <p><Link href={`/assets?id=${encodeURIComponent(quote.canonical_id)}`}>Abrir página do ativo</Link></p>
          <ProvenancePanel data={quote} />
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

function changeCue(percent: string | null | undefined) {
  if (percent == null) return null;
  const value = Number(percent);
  if (!Number.isFinite(value)) return null;
  return { value, tone: value > 0 ? "direction-up" : value < 0 ? "direction-down" : "direction-flat", glyph: value > 0 ? "▲" : value < 0 ? "▼" : "▬", word: value > 0 ? "alta" : value < 0 ? "queda" : "estável" };
}

/** Cards for the benchmarks and the operational instruments, exactly as the API serves them. */
function MarketOverview({ benchmarks, quotes }: { benchmarks: BenchmarkItem[]; quotes: PublicQuote[] }) {
  const cards = [
    ...quotes.map((quote) => ({ id: quote.canonical_id, title: quote.name, symbol: quote.symbol, value: quote.price, currency: quote.currency, change: quote.change_percent, level: quote.data_level, freshness: quote.freshness, reason: quote.unavailable_reason, source: quote.provider, href: `/assets?id=${encodeURIComponent(quote.canonical_id)}` })),
    ...benchmarks.map((item) => ({ id: item.canonical_id, title: item.name, symbol: item.symbol, value: item.value, currency: item.currency, change: item.change_percent, level: item.data_level, freshness: item.freshness, reason: item.unavailable_reason, source: item.source, href: `/compare?ids=${encodeURIComponent(item.canonical_id)}` })),
  ];
  if (cards.length === 0) return <p className="muted">Carregando o panorama…</p>;
  return (
    <ul className="overview-grid">
      {cards.map((card) => {
        const cue = changeCue(card.change);
        return (
          <li key={card.id} className="card overview-card">
            <h3>{card.title}</h3>
            <span className="value">{card.value == null ? "—" : Number(card.value).toLocaleString("pt-BR", { maximumFractionDigits: Number(card.value) >= 1000 ? 0 : 4 })} <small>{card.value == null ? "" : card.currency}</small></span>
            {cue ? <span className={cue.tone}>{cue.glyph} {Math.abs(cue.value).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}% · {cue.word}</span> : <small>Variação indisponível</small>}
            <DataStateBadge dataLevel={card.level} freshness={card.freshness} />
            <small>{card.reason ? formatReason(card.reason) : `Fonte: ${card.source}`}</small>
            <Link href={card.href}>{card.href.startsWith("/assets") ? `Abrir ${card.symbol}` : `Comparar ${card.symbol}`}</Link>
          </li>
        );
      })}
    </ul>
  );
}

export function TerminalShell() {
  const [selectedCanonicalId, setSelectedCanonicalId] = useState("");
  const [instruments, setInstruments] = useState<InstrumentSummary[]>([]);
  const [benchmarks, setBenchmarks] = useState<BenchmarkItem[]>([]);
  const [quotes, setQuotes] = useState<Record<string, PublicQuote>>({});
  const [quoteError, setQuoteError] = useState<Record<string, string>>({});

  useEffect(() => {
    const controller = new AbortController();
    apiRequest<InstrumentList>("/api/v1/instruments/search?q=.&limit=50", { signal: controller.signal })
      .then((data) => {
        setInstruments(data.items);
        setSelectedCanonicalId((current) => current || data.items.find((item) => item.support_state === "P0_OPERATIONAL")?.canonical_id || data.items[0]?.canonical_id || "");
      })
      .catch(() => undefined);
    apiRequest<{ items: BenchmarkItem[] }>("/api/v1/market-data/benchmarks", { signal: controller.signal })
      .then((data) => setBenchmarks(data.items))
      .catch(() => undefined);
    return () => controller.abort();
  }, []);

  const operational = useMemo(() => instruments.filter((item) => item.support_state === "P0_OPERATIONAL"), [instruments]);
  useEffect(() => {
    const controller = new AbortController();
    for (const item of operational) {
      apiRequest<PublicQuote>(`/api/v1/market-data/quotes/${encodeURIComponent(item.canonical_id)}`, { signal: controller.signal })
        .then((quote) => setQuotes((current) => ({ ...current, [item.canonical_id]: quote })))
        .catch((error: unknown) => { if (!isAbort(error)) setQuoteError((current) => ({ ...current, [item.canonical_id]: (error as Error).message })); });
    }
    return () => controller.abort();
  }, [operational]);

  const quote = quotes[selectedCanonicalId];
  const selected = instruments.find((item) => item.canonical_id === selectedCanonicalId);
  const compareOptions = [
    ...operational.map((item) => ({ id: item.canonical_id, label: `${item.display_symbol} · ${item.name}` })),
    ...benchmarks.map((item) => ({ id: item.canonical_id, label: `${item.symbol} · ${item.name}` })),
  ];

  return <div className="terminal-root">
    <main id="main-content" className="page">
      <div className="page-head">
        <div>
          <h1>Observatório de mercado</h1>
          <p className="muted">Gráfico com ferramentas de análise, cotações com procedência e o panorama das referências. Conteúdo informativo; DEMO e UNAVAILABLE sempre identificados.</p>
        </div>
        {operational.length > 0 && (
          <label className="control-group">
            <span className="sr-only">Ativo no gráfico</span>
            <select className="control" value={selectedCanonicalId} onChange={(event) => setSelectedCanonicalId(event.target.value)} aria-label="Ativo no gráfico">
              {operational.map((item) => <option key={item.canonical_id} value={item.canonical_id}>{item.display_symbol} · {item.name}</option>)}
            </select>
          </label>
        )}
      </div>
      <div className="dashboard-grid">
        {selectedCanonicalId ? <ChartWorkspace key={selectedCanonicalId} canonicalId={selectedCanonicalId} symbol={selected?.display_symbol ?? selectedCanonicalId} compareOptions={compareOptions} /> : <div className="card loading-state">Carregando o catálogo…</div>}
        <div className="dashboard-side">
          <AssetContextPanel quote={quote} loading={Boolean(selectedCanonicalId) && !quote && !quoteError[selectedCanonicalId]} error={quoteError[selectedCanonicalId]} selectedId={selectedCanonicalId} />
          {/* Morning Call: the latest published summary, reviewed by a human before it appears. */}
          <div className="card" id="morning-call"><MorningCallPanel /></div>
          <section className="card" aria-labelledby="agenda-title"><h2 id="agenda-title">Agenda e eventos</h2><p className="muted">Nenhum evento carregado. Sem notícia inventada.</p><span className="state-label">UNAVAILABLE</span></section>
        </div>
      </div>
      <section aria-labelledby="overview-title">
        <h2 id="overview-title" style={{ marginTop: "2rem" }}>Panorama</h2>
        <MarketOverview benchmarks={benchmarks} quotes={operational.map((item) => quotes[item.canonical_id]).filter((item): item is PublicQuote => Boolean(item))} />
      </section>
    </main>
    <footer><MarketStatusBar data={quote} /><span>{FINANCIAL_DISCLAIMER}</span></footer>
  </div>;
}
