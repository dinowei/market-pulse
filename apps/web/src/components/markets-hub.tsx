"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState, type KeyboardEvent } from "react";

import type { components } from "../generated/api";
import { apiRequest, isAbort } from "../lib/api-client";
import { MAX_COMPARED_SERIES } from "../lib/comparison-defaults";
import { FINANCIAL_DISCLAIMER } from "../lib/disclaimers";
import {
  chunk, compareHref, displayValue, formatUtc, groupByTab, MARKET_TABS, parseMarketTab, pulseSentence, pulseSummary,
  rowFromBenchmark, rowFromInstrument, type MarketRow, type MarketTab, type MarketTabId,
} from "../lib/markets";
import { describeChange } from "../lib/price-direction";
import { DataStateBadge } from "./market-data";
import { MarketPulseField } from "./market-pulse-field";

type InstrumentList = components["schemas"]["InstrumentList"];
type BatchQuoteResponse = components["schemas"]["BatchQuoteResponse"];
type BenchmarkListResponse = components["schemas"]["BenchmarkListResponse"];
type PublicQuote = components["schemas"]["PublicQuote"];

const CATALOG_LIMIT = 100;
const BATCH_LIMIT = 10;

async function loadRows(signal: AbortSignal): Promise<{ rows: MarketRow[]; partial: boolean }> {
  const [catalog, benchmarks] = await Promise.all([
    apiRequest<InstrumentList>(`/api/v1/instruments?limit=${CATALOG_LIMIT}&sort=symbol&order=asc`, { signal }),
    apiRequest<BenchmarkListResponse>("/api/v1/market-data/benchmarks", { signal }),
  ]);
  const quotes = new Map<string, PublicQuote>();
  let partial = false;
  // The batch accepts at most 10 ids; one failed chunk leaves those rows marked, not filled.
  await Promise.all(chunk(catalog.items.map((item) => item.canonical_id), BATCH_LIMIT).map(async (ids) => {
    try {
      const batch = await apiRequest<BatchQuoteResponse>("/api/v1/market-data/quotes/batch", { method: "POST", body: JSON.stringify({ canonical_ids: ids }), signal });
      for (const quote of batch.items) quotes.set(quote.canonical_id, quote);
    } catch (error) {
      if (isAbort(error)) throw error;
      partial = true;
    }
  }));
  return {
    rows: [...catalog.items.map((item) => rowFromInstrument(item, quotes.get(item.canonical_id))), ...benchmarks.items.map(rowFromBenchmark)],
    partial,
  };
}

function ChangeCell({ row }: { row: MarketRow }) {
  const change = row.freshness === "UNAVAILABLE" ? null : describeChange(row.change, row.changePercent, row.currency);
  if (!change) return <span className="muted">Sem variação conhecida</span>;
  return <span className={`direction-${change.direction.toLowerCase()}`}><span aria-hidden="true">{change.cue.glyph}</span> {change.text} · {change.cue.word}</span>;
}

function StateCell({ row }: { row: MarketRow }) {
  if (!row.dataLevel || !row.freshness) return <span className="muted">Cotação não carregada</span>;
  return <><DataStateBadge dataLevel={row.dataLevel} freshness={row.freshness} />{row.reason && <small className="row-reason">{row.reason}</small>}<small className="row-reason">{row.coverage}</small></>;
}

function MarketTable({ tab, rows, selected, onToggle }: { tab: MarketTab; rows: MarketRow[]; selected: ReadonlySet<string>; onToggle: (id: string) => void }) {
  const full = selected.size >= MAX_COMPARED_SERIES;
  return (
    <div className="table-wrap"><table className="markets-table">
      <caption>{tab.label}: {rows.length} {rows.length === 1 ? "série" : "séries"}, com fonte, estado e horário oficial</caption>
      <thead><tr><th scope="col">Comparar</th><th scope="col">Ativo</th><th scope="col">Último</th><th scope="col">Variação</th><th scope="col">Estado</th><th scope="col">Horário oficial</th><th scope="col">Fonte</th></tr></thead>
      <tbody>{rows.map((row) => {
        const value = displayValue(row);
        const checked = selected.has(row.canonicalId);
        return <tr key={row.canonicalId}>
          <td><input type="checkbox" checked={checked} disabled={!checked && full} onChange={() => onToggle(row.canonicalId)} aria-label={`Selecionar ${row.symbol} para comparar`} /></td>
          <th scope="row">{row.kind === "instrument"
            ? <Link href={`/assets?id=${encodeURIComponent(row.canonicalId)}`}>{row.symbol}</Link>
            : <Link href={compareHref([row.canonicalId])}>{row.symbol}</Link>}<br /><small>{row.name}{row.kind === "benchmark" && " · referência"}</small></th>
          <td className="numeric">{value === null ? <span className="muted">Indisponível</span> : <>{value} <small>{row.unitDeclared ? row.currency : "unidade não declarada"}</small></>}</td>
          <td><ChangeCell row={row} /></td>
          <td><StateCell row={row} /></td>
          <td>{formatUtc(row.officialAt)}</td>
          <td><small>{row.source ?? "—"}</small></td>
        </tr>;
      })}</tbody>
    </table></div>
  );
}

function UnavailablePanel({ tab }: { tab: MarketTab }) {
  if (!tab.unavailable) return null;
  return (
    <div className="markets-unavailable">
      <p className="state-note">{tab.unavailable.reason}</p>
      <ul>{tab.unavailable.items.map((item) => <li key={item.label}><strong>{item.label}</strong><span>{item.detail}</span><span className="state-label">UNAVAILABLE · sem dataset aprovado</span></li>)}</ul>
    </div>
  );
}

function Overview({ groups, onOpen }: { groups: Map<MarketTabId, MarketRow[]>; onOpen: (id: MarketTabId) => void }) {
  return (
    <ul className="markets-overview">{MARKET_TABS.filter((tab) => tab.id !== "overview" && (tab.unavailable || groups.has(tab.id))).map((tab) => {
      const rows = groups.get(tab.id) ?? [];
      return <li key={tab.id}><button type="button" className="markets-card" onClick={() => onOpen(tab.id)}>
        <span className="eyebrow">{tab.label.toUpperCase()}</span>
        <strong>{tab.unavailable ? "Indisponível" : `${rows.length} ${rows.length === 1 ? "série" : "séries"}`}</strong>
        <span className="muted">{tab.unavailable ? "Sem dataset aprovado" : pulseSentence(pulseSummary(rows))}</span>
        {rows.length > 0 && <span className="markets-card-symbols">{rows.map((row) => row.symbol).join(" · ")}</span>}
      </button></li>;
    })}</ul>
  );
}

export function MarketsHub({ initialTab = "overview" }: { initialTab?: MarketTabId }) {
  const [tab, setTab] = useState<MarketTabId>(initialTab);
  const [state, setState] = useState<{ rows: MarketRow[]; partial: boolean } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);
  const [selected, setSelected] = useState<ReadonlySet<string>>(new Set());
  const [art, setArt] = useState(true);
  const tabRefs = useRef(new Map<MarketTabId, HTMLButtonElement>());

  useEffect(() => {
    const controller = new AbortController();
    loadRows(controller.signal)
      .then((result) => { setState(result); setError(null); })
      .catch((reason: unknown) => { if (!isAbort(reason)) setError(reason instanceof Error ? reason.message : "Falha ao carregar"); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [refreshKey]);

  const groups = groupByTab(state?.rows ?? []);
  const tabs = MARKET_TABS.filter((item) => item.id !== "outros" || groups.has("outros"));
  const current = tabs.find((item) => item.id === tab) ?? tabs[0];

  const openTab = useCallback((id: MarketTabId, focus = false) => {
    setTab(id);
    window.history.replaceState(null, "", id === "overview" ? "/markets" : `/markets?tab=${id}`);
    if (focus) tabRefs.current.get(id)?.focus();
  }, []);

  const onTabKey = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const last = tabs.length - 1;
    const target = { ArrowRight: index === last ? 0 : index + 1, ArrowLeft: index === 0 ? last : index - 1, Home: 0, End: last }[event.key];
    if (target === undefined) return;
    event.preventDefault();
    openTab(tabs[target].id, true);
  };

  const toggle = (id: string) => setSelected((previous) => {
    const next = new Set(previous);
    if (next.has(id)) next.delete(id); else if (next.size < MAX_COMPARED_SERIES) next.add(id);
    return next;
  });

  const rows = state?.rows ?? [];
  const tabRows = current.id === "overview" ? rows : groups.get(current.id) ?? [];
  const selectedIds = [...selected];

  return (
    <section className="markets-panel" aria-labelledby="markets-title">
      <div className="section-heading">
        <div><p className="eyebrow">PARTICLE ATLAS / MERCADOS</p><h1 id="markets-title">Mercados por família</h1></div>
        <div className="markets-actions">
          <Link href="/">Dashboard</Link>
          <button type="button" className="control" onClick={() => { setLoading(true); setRefreshKey((key) => key + 1); }} disabled={loading}>{loading ? "Atualizando…" : "Atualizar dados"}</button>
          <button type="button" className="control" aria-pressed={art} onClick={() => setArt((value) => !value)}>Arte do pulso: {art ? "ligada" : "desligada"}</button>
        </div>
      </div>
      <p className="muted">Cada aba reúne uma família de mercado. Os valores vêm do contrato da API com fonte, estado e horário; famílias sem dataset aprovado aparecem com o motivo, nunca com número.</p>
      {error && <p className="state-note" role="alert">Mercados indisponíveis: {error}</p>}
      {state?.partial && <p className="state-note" role="status">Parte das cotações não carregou; essas linhas aparecem como não carregadas.</p>}
      {art && state && <MarketPulseField rows={rows} activeTab={current.id} refreshKey={refreshKey} />}

      <div className="markets-tabs" role="tablist" aria-label="Famílias de mercado">
        {tabs.map((item, index) => {
          const count = item.id === "overview" ? rows.length : groups.get(item.id)?.length ?? 0;
          return <button key={item.id} ref={(node) => { if (node) tabRefs.current.set(item.id, node); else tabRefs.current.delete(item.id); }} type="button" role="tab" id={`markets-tab-${item.id}`} aria-selected={item.id === current.id} aria-controls={`markets-panel-${item.id}`} tabIndex={item.id === current.id ? 0 : -1} className={item.id === current.id ? "markets-tab active" : "markets-tab"} onClick={() => openTab(item.id)} onKeyDown={(event) => onTabKey(event, index)}>
            {item.label}<span className="tab-count">{item.unavailable ? "indisp." : count}</span>
          </button>;
        })}
      </div>

      <div className="markets-compare" role="region" aria-label="Seleção para comparar">
        <span>{selected.size} de {MAX_COMPARED_SERIES} selecionados{selected.size > 0 && `: ${selectedIds.map((id) => rows.find((row) => row.canonicalId === id)?.symbol ?? id).join(", ")}`}</span>
        {selected.size > 0
          ? <><Link className="markets-compare-link" href={compareHref(selectedIds)}>Comparar selecionados em INDEX_100</Link><button type="button" className="control" onClick={() => setSelected(new Set())}>Limpar</button></>
          : <span className="muted">Marque séries de qualquer aba — ações com CDI ou IPCA, por exemplo.</span>}
      </div>

      <div role="tabpanel" id={`markets-panel-${current.id}`} aria-labelledby={`markets-tab-${current.id}`} tabIndex={0} className="markets-tabpanel">
        <p className="muted">{current.description}</p>
        {loading && !state && <p className="loading-state">Carregando mercados…</p>}
        {current.id === "overview" && state && <Overview groups={groups} onOpen={(id) => openTab(id, true)} />}
        {current.unavailable && <UnavailablePanel tab={current} />}
        {!current.unavailable && current.id !== "overview" && state && (tabRows.length > 0
          ? <MarketTable tab={current} rows={tabRows} selected={selected} onToggle={toggle} />
          : <p className="muted">Nenhum instrumento desta família no catálogo atual.</p>)}
        {current.id !== "overview" && tabRows.some((row) => row.kind === "benchmark") && <p className="limitation-note">Referências sintéticas DEMO. O contrato não declara a unidade (taxa ao ano, pontos de índice ou cotação), por isso nenhuma é presumida; sem valor anterior oficial, a variação fica desconhecida, nunca zero (H-30).</p>}
      </div>
      <p className="financial-disclaimer">{FINANCIAL_DISCLAIMER}</p>
    </section>
  );
}

export function MarketsFromQuery() {
  return <MarketsHub initialTab={parseMarketTab(useSearchParams().get("tab"))} />;
}
