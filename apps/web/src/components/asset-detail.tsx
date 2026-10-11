"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import type { components } from "../generated/api";
import { apiRequest, httpStatus, isAbort } from "../lib/api-client";
import { CANONICAL_ID } from "../lib/canonical-id";
import { DEFAULT_BENCHMARK_ID } from "../lib/comparison-defaults";
import { FINANCIAL_DISCLAIMER } from "../lib/disclaimers";
import { DISPLAY_MAX_POINTS, downsamplingSummary } from "../lib/downsampling-note";
import { AssetEvents } from "./asset-events";
import { AccessibleDataTable, DataStateBadge, PeriodSelector, PriceChange, ProvenancePanel, SeriesModeToggle } from "./market-data";
import { ParticleChart } from "./particle-chart";
import { ChartTypeToggle, effectiveChartKind } from "./chart-type-toggle";
import { candleAvailability, type ChartKind } from "../lib/chart-geometry";

type PublicQuote = components["schemas"]["PublicQuote"];
type PublicHistorySeries = components["schemas"]["PublicHistorySeries"];
type HistoryPeriod = components["schemas"]["HistoryPeriod"];
type SeriesMode = components["schemas"]["SeriesMode"];
type InstrumentSummary = components["schemas"]["InstrumentSummary"];
type InstrumentList = components["schemas"]["InstrumentList"];
type Watchlist = components["schemas"]["WatchlistResponse"];
type WatchlistList = components["schemas"]["WatchlistListResponse"];

// Classes the catalog cannot serve: the page says so instead of offering actions.
const UNSERVED = new Set(["BLOCKED_SCOPE", "UNSUPPORTED"]);

function useAssetData(canonicalId: string, period: HistoryPeriod, mode: SeriesMode) {
  const [instrument, setInstrument] = useState<{ id: string; value?: InstrumentSummary | null }>({ id: "" });
  const [quote, setQuote] = useState<{ id: string; value?: PublicQuote; error?: string }>({ id: "" });
  const [history, setHistory] = useState<{ key: string; value?: PublicHistorySeries; error?: string }>({ key: "" });
  const historyKey = `${canonicalId}|${period}|${mode}`;

  useEffect(() => {
    const controller = new AbortController();
    apiRequest<InstrumentList>(`/api/v1/instruments/search?q=${encodeURIComponent(canonicalId)}&limit=20`, { signal: controller.signal })
      .then((list) => setInstrument({ id: canonicalId, value: list.items.find((item) => item.canonical_id === canonicalId) ?? null }))
      .catch((error: unknown) => { if (!isAbort(error)) setInstrument({ id: canonicalId, value: null }); });
    apiRequest<PublicQuote>(`/api/v1/market-data/quotes/${encodeURIComponent(canonicalId)}`, { signal: controller.signal })
      .then((value) => setQuote({ id: canonicalId, value }))
      .catch((error: unknown) => { if (!isAbort(error)) setQuote({ id: canonicalId, error: (error as Error).message }); });
    return () => controller.abort();
  }, [canonicalId]);

  useEffect(() => {
    const controller = new AbortController();
    apiRequest<PublicHistorySeries>(`/api/v1/market-data/history/${encodeURIComponent(canonicalId)}?period=${period}&mode=${mode}&adjustment_type=UNADJUSTED&max_points=${DISPLAY_MAX_POINTS}`, { signal: controller.signal })
      .then((value) => setHistory({ key: historyKey, value }))
      .catch((error: unknown) => { if (!isAbort(error)) setHistory({ key: historyKey, error: (error as Error).message }); });
    return () => controller.abort();
  }, [canonicalId, historyKey, mode, period]);

  return {
    instrument: instrument.id === canonicalId ? instrument.value : undefined,
    quote: quote.id === canonicalId ? quote : undefined,
    history: history.key === historyKey ? history : undefined,
  };
}

function WatchlistActions({ canonicalId, servable }: { canonicalId: string; servable: boolean }) {
  const [lists, setLists] = useState<Watchlist[] | null>(null);
  const [signedOut, setSignedOut] = useState(false);
  const [target, setTarget] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    apiRequest<WatchlistList>("/api/v1/watchlists", { signal: controller.signal })
      .then((data) => setLists(data.items))
      .catch((error: unknown) => { if (!isAbort(error)) { if (httpStatus(error) === 401) setSignedOut(true); else setMessage("Watchlists indisponíveis no momento."); } });
    return () => controller.abort();
  }, []);

  const favorites = lists?.find((list) => list.is_system);
  const isFavorite = Boolean(favorites?.items.some((item) => item.canonical_id === canonicalId));
  const ownLists = lists?.filter((list) => !list.is_system) ?? [];

  async function toggleFavorite() {
    setBusy(true);
    setMessage("");
    try {
      await apiRequest(`/api/v1/watchlists/favorites/${encodeURIComponent(canonicalId)}`, { method: isFavorite ? "DELETE" : "POST" });
      setLists(await apiRequest<WatchlistList>("/api/v1/watchlists").then((data) => data.items));
      setMessage(isFavorite ? "Removido dos favoritos." : "Adicionado aos favoritos.");
    } catch (error) {
      setMessage(httpStatus(error) === 429 ? "Muitas requisições; aguarde alguns segundos." : "Não foi possível atualizar os favoritos.");
    } finally {
      setBusy(false);
    }
  }

  async function addToWatchlist(event: FormEvent) {
    event.preventDefault();
    if (!target) return;
    setBusy(true);
    setMessage("");
    try {
      await apiRequest(`/api/v1/watchlists/${encodeURIComponent(target)}/items`, { method: "POST", body: JSON.stringify({ canonical_id: canonicalId }) });
      setMessage("Adicionado à watchlist.");
    } catch (error) {
      setMessage(httpStatus(error) === 409 ? "Este ativo já está nessa watchlist." : "Não foi possível adicionar à watchlist.");
    } finally {
      setBusy(false);
    }
  }

  if (!servable) return <p className="muted">Este instrumento não é atendido pelo catálogo; ações de lista ficam indisponíveis.</p>;
  if (signedOut) return <p className="muted"><Link href="/login">Entre</Link> para favoritar ou adicionar a uma watchlist.</p>;
  if (!lists) return <p className="loading-state">Carregando suas listas…</p>;
  return (
    <div className="asset-actions">
      <button type="button" className="control" aria-pressed={isFavorite} disabled={busy} onClick={() => void toggleFavorite()}>
        {isFavorite ? "★ Remover dos favoritos" : "☆ Favoritar"}
      </button>
      {ownLists.length > 0 ? (
        <form onSubmit={addToWatchlist} className="asset-watchlist-form">
          <label htmlFor="asset-watchlist">Watchlist</label>
          <select id="asset-watchlist" value={target} onChange={(event) => setTarget(event.target.value)}>
            <option value="">Escolha uma lista</option>
            {ownLists.map((list) => <option key={list.id} value={list.id}>{list.name}</option>)}
          </select>
          <button type="submit" className="control" disabled={busy || !target}>Adicionar à watchlist</button>
        </form>
      ) : <p className="muted">Crie uma lista em <Link href="/watchlists">Watchlists</Link> para adicionar este ativo.</p>}
      <p role="status" aria-live="polite" className="muted">{message}</p>
    </div>
  );
}

export function AssetDetail({ canonicalId }: { canonicalId: string }) {
  const [period, setPeriod] = useState<HistoryPeriod>("1M");
  const [mode, setMode] = useState<SeriesMode>("PRICE");
  const [chartKind, setChartKind] = useState<ChartKind>("line");
  const { instrument, quote, history } = useAssetData(canonicalId, period, mode);
  const servable = Boolean(instrument && !UNSERVED.has(instrument.support_state));

  if (instrument === null) {
    return (
      <section className="asset-page-panel" aria-labelledby="asset-title">
        <h1 id="asset-title">Ativo não encontrado</h1>
        <p className="muted">O identificador <code>{canonicalId}</code> não está no catálogo do Market Pulse.</p>
        <Link href="/">Voltar ao dashboard</Link>
      </section>
    );
  }

  return (
    <>
      <section className="asset-page-panel" aria-labelledby="asset-title">
        <p className="eyebrow">ATIVO / {instrument?.instrument_type ?? "…"}</p>
        <h1 id="asset-title">{instrument ? `${instrument.display_symbol} · ${instrument.name}` : canonicalId}</h1>
        {instrument && (
          <dl className="meta-grid compact">
            <div><dt>Identificador</dt><dd><code>{instrument.canonical_id}</code></dd></div>
            <div><dt>Bolsa</dt><dd>{instrument.exchange ?? "—"}</dd></div>
            <div><dt>País</dt><dd>{instrument.country ?? "—"}</dd></div>
            <div><dt>Moeda</dt><dd>{instrument.currency}</dd></div>
            <div><dt>Fuso</dt><dd>{instrument.timezone ?? "—"}</dd></div>
            <div><dt>Suporte</dt><dd>{instrument.support_state} · {instrument.data_support_status}</dd></div>
          </dl>
        )}
      </section>

      <div className="asset-page-grid">
        <section className="series-panel" aria-labelledby="asset-series-title">
          <div className="series-heading"><div><p className="eyebrow">SÉRIE HISTÓRICA</p><h2 id="asset-series-title">{instrument?.display_symbol ?? canonicalId} · {period}</h2></div><span className="series-note">Sem suavização</span></div>
          <div className="controls"><PeriodSelector value={period} onChange={setPeriod} /><SeriesModeToggle value={mode} onChange={setMode} />{history?.value && <ChartTypeToggle value={chartKind} onChange={setChartKind} availability={candleAvailability(history.value)} />}</div>
          {!history && <p className="loading-state">Carregando série tipada…</p>}
          {history?.error && <p className="state-note" role="alert">Série indisponível: {history.error}</p>}
          {history?.value && <>
            {downsamplingSummary(history.value.downsampling) && <p className="muted" role="note">{downsamplingSummary(history.value.downsampling)}</p>}
            <ParticleChart series={history.value} kind={effectiveChartKind(chartKind, candleAvailability(history.value))} />
            <AccessibleDataTable points={history.value.points} reducedFrom={history.value.downsampling?.original_points} ohlc={effectiveChartKind(chartKind, candleAvailability(history.value)) === "candles"} />
          </>}
          <p className="muted"><Link href={`/compare?ids=${encodeURIComponent(`${canonicalId},${DEFAULT_BENCHMARK_ID}`)}`}>Comparar com o Ibovespa</Link> em INDEX_100.</p>
        </section>

        <aside className="asset-context" aria-labelledby="asset-quote-title">
          <div className="section-heading"><p className="eyebrow">COTAÇÃO</p><h2 id="asset-quote-title">Último valor</h2></div>
          {!quote && <p className="loading-state">Carregando cotação…</p>}
          {quote?.error && <p className="state-note" role="alert">Cotação indisponível: {quote.error}</p>}
          {quote?.value && <>
            <DataStateBadge dataLevel={quote.value.data_level} freshness={quote.value.freshness} />
            <p className="asset-price">{quote.value.price == null ? "Indisponível" : `${quote.value.currency} ${quote.value.price}`}</p>
            <PriceChange quote={quote.value} />
            <ProvenancePanel data={quote.value} />
          </>}
          <section aria-labelledby="asset-actions-title">
            <h2 id="asset-actions-title">Acompanhar</h2>
            <WatchlistActions canonicalId={canonicalId} servable={servable} />
            {servable && <p className="muted"><Link href={`/portfolios?canonical_id=${encodeURIComponent(canonicalId)}`}>Registrar evento na carteira</Link> com este ativo.</p>}
          </section>
        </aside>
      </div>

      <AssetEvents canonicalId={canonicalId} />
      <p className="financial-disclaimer">{FINANCIAL_DISCLAIMER}</p>
    </>
  );
}

// The page stays statically prerendered (ADR-005): the id is read on the client, inside the
// page's Suspense boundary.
export function AssetFromQuery() {
  const id = useSearchParams().get("id") ?? "";
  if (!CANONICAL_ID.test(id)) {
    return (
      <section className="asset-page-panel" aria-labelledby="asset-title">
        <h1 id="asset-title">Página de ativo</h1>
        <p className="muted">Escolha um ativo pela busca do <Link href="/">dashboard</Link> ou pelo <Link href="/atlas">Global Atlas</Link>.</p>
      </section>
    );
  }
  return <AssetDetail canonicalId={id} />;
}
