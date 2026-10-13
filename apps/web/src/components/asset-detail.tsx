"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import type { components } from "../generated/api";
import { apiRequest, httpStatus, isAbort } from "../lib/api-client";
import { CANONICAL_ID } from "../lib/canonical-id";
import { DEFAULT_BENCHMARK_ID } from "../lib/comparison-defaults";
import { FINANCIAL_DISCLAIMER } from "../lib/disclaimers";
import { AssetEvents } from "./asset-events";
import { DataStateBadge, PriceChange, ProvenancePanel } from "./market-data";

// The canvas chart workspace (ADR-028) loads after the page; it carries its own table view.
const ChartWorkspace = dynamic(() => import("./chart-workspace").then((module) => module.ChartWorkspace), {
  ssr: false,
  loading: () => <div className="card loading-state">Carregando o gráfico…</div>,
});

type PublicQuote = components["schemas"]["PublicQuote"];
type BenchmarkItem = components["schemas"]["BenchmarkItem"];
type InstrumentSummary = components["schemas"]["InstrumentSummary"];
type InstrumentList = components["schemas"]["InstrumentList"];
type Watchlist = components["schemas"]["WatchlistResponse"];
type WatchlistList = components["schemas"]["WatchlistListResponse"];

// Classes the catalog cannot serve: the page says so instead of offering actions.
const UNSERVED = new Set(["BLOCKED_SCOPE", "UNSUPPORTED"]);

function useAssetData(canonicalId: string) {
  const [instrument, setInstrument] = useState<{ id: string; value?: InstrumentSummary | null }>({ id: "" });
  const [quote, setQuote] = useState<{ id: string; value?: PublicQuote; error?: string }>({ id: "" });
  const [options, setOptions] = useState<{ id: string; label: string }[]>([]);

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

  // Comparison candidates: the operational catalog and the benchmarks, as the API lists them.
  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      apiRequest<InstrumentList>("/api/v1/instruments/search?q=.&limit=50", { signal: controller.signal }).catch(() => ({ items: [] as InstrumentSummary[] })),
      apiRequest<{ items: BenchmarkItem[] }>("/api/v1/market-data/benchmarks", { signal: controller.signal }).catch(() => ({ items: [] as BenchmarkItem[] })),
    ]).then(([list, benchmarks]) => setOptions([
      ...list.items.filter((item) => item.support_state === "P0_OPERATIONAL").map((item) => ({ id: item.canonical_id, label: `${item.display_symbol} · ${item.name}` })),
      ...benchmarks.items.map((item) => ({ id: item.canonical_id, label: `${item.symbol} · ${item.name}` })),
    ]));
    return () => controller.abort();
  }, []);

  return {
    instrument: instrument.id === canonicalId ? instrument.value : undefined,
    quote: quote.id === canonicalId ? quote : undefined,
    options,
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
  const { instrument, quote, options } = useAssetData(canonicalId);
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
        <h1 id="asset-title">{instrument ? `${instrument.display_symbol} · ${instrument.name}` : canonicalId}</h1>
        {instrument && (
          <dl className="meta-grid compact">
            <div><dt>Tipo</dt><dd>{instrument.instrument_type}</dd></div>
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
        <ChartWorkspace key={canonicalId} canonicalId={canonicalId} symbol={instrument?.display_symbol ?? canonicalId} compareOptions={options} />

        <aside className="asset-context" aria-labelledby="asset-quote-title">
          <div className="section-heading"><h2 id="asset-quote-title">Último valor</h2>{quote?.value && <DataStateBadge dataLevel={quote.value.data_level} freshness={quote.value.freshness} />}</div>
          {!quote && <p className="loading-state">Carregando cotação…</p>}
          {quote?.error && <p className="state-note" role="alert">Cotação indisponível: {quote.error}</p>}
          {quote?.value && <>
            <p className="asset-price">{quote.value.price == null ? "Indisponível" : `${quote.value.currency} ${Number(quote.value.price).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`}</p>
            <PriceChange quote={quote.value} />
            {quote.value.unavailable_reason === "SESSION_REQUIRED" && <p><Link href="/login">Entre</Link> para ver a cotação real.</p>}
          </>}
          <section aria-labelledby="asset-actions-title">
            <h2 id="asset-actions-title">Acompanhar</h2>
            <WatchlistActions canonicalId={canonicalId} servable={servable} />
            {servable && <p className="muted"><Link href={`/portfolios?canonical_id=${encodeURIComponent(canonicalId)}`}>Registrar evento na carteira</Link> com este ativo.</p>}
            <p className="muted"><Link href={`/compare?ids=${encodeURIComponent(`${canonicalId},${DEFAULT_BENCHMARK_ID}`)}`}>Comparar com o Ibovespa</Link> em INDEX_100.</p>
          </section>
          {quote?.value && <ProvenancePanel data={quote.value} />}
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
