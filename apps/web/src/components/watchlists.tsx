"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import type { components } from "../generated/api";
import { isRateLimited, parseRetryAfter, RateLimitNotice, retryAfterSeconds } from "./rate-limit-notice";
import { apiRequest, isAbort } from "../lib/api-client";
import { FINANCIAL_DISCLAIMER } from "../lib/disclaimers";
import { formatAmount, percentCue, shortReason } from "../lib/panorama";
import { describeChange, signedDecimal } from "../lib/price-direction";
import { annualizationDays, seriesStats } from "../lib/series-stats";
import { DataStateBadge } from "./data-table";
import { InstrumentSearch } from "./instrument-search";
import styles from "./private-pages.module.css";
import { ADD_ITEM_ERROR, withAddedItem, withoutItem, withoutList, withReplacedList } from "../lib/watchlist-state";

type Watchlist = components["schemas"]["WatchlistResponse"];
type WatchlistList = components["schemas"]["WatchlistListResponse"];
type WatchlistItem = components["schemas"]["WatchlistItemResponse"];
type WatchlistCreate = components["schemas"]["WatchlistCreateRequest"];
type WatchlistItemCreate = components["schemas"]["WatchlistItemCreateRequest"];
type WatchlistReorder = components["schemas"]["WatchlistReorderRequest"];
type PublicQuote = components["schemas"]["PublicQuote"];
type PublicHistorySeries = components["schemas"]["PublicHistorySeries"];

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", Accept: "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const error = new Error(`HTTP ${response.status}`);
    (error as Error & { status?: number }).status = response.status;
    (error as Error & { retryAfter?: number }).retryAfter = parseRetryAfter(response.headers.get("Retry-After"));
    throw error;
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function isSignedOut(error: unknown): boolean {
  return error instanceof Error && (error as Error & { status?: number }).status === 401;
}

const formatNumber = (value: number) => value.toLocaleString("pt-BR", { maximumFractionDigits: 2 });
const LINE_PERIOD = "3M";
const BATCH = 10;
const PARALLEL = 3;

function Sparkline({ closes, up }: { closes: readonly number[]; up: boolean }) {
  const min = Math.min(...closes);
  const span = Math.max(...closes) - min || 1;
  const points = closes.map((close, index) => `${(index / (closes.length - 1)) * 100},${38 - ((close - min) / span) * 36}`).join(" ");
  return <svg className={`${styles.spark} ${up ? "direction-up" : "direction-down"}`} viewBox="0 0 100 40" preserveAspectRatio="none" aria-hidden="true" focusable="false"><polyline points={points} /></svg>;
}

export function WatchlistsPanel() {
  const [watchlists, setWatchlists] = useState<Watchlist[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [name, setName] = useState("");
  const [canonicalId, setCanonicalId] = useState("");
  const [loading, setLoading] = useState(true);
  const [signedOut, setSignedOut] = useState(false);
  const [error, setError] = useState<string | undefined>();
  const [rateLimit, setRateLimit] = useState<{ retryAfter?: number } | undefined>();
  const [quotes, setQuotes] = useState<Record<string, PublicQuote>>({});
  const [lines, setLines] = useState<Record<string, number[]>>({});
  const idsKey = watchlists.find((list) => list.id === selectedId)?.items.map((item) => item.canonical_id).join(",") ?? "";

  // Quotes in batches first, then the 3-month lines a few at a time, to spare the sources' quotas.
  useEffect(() => {
    if (!idsKey) return undefined;
    const controller = new AbortController();
    const { signal } = controller;
    const ids = idsKey.split(",");
    const run = async () => {
      for (let start = 0; start < ids.length; start += BATCH) {
        const batch = await apiRequest<{ items: PublicQuote[] }>("/api/v1/market-data/quotes/batch", { method: "POST", body: JSON.stringify({ canonical_ids: ids.slice(start, start + BATCH) }), signal });
        setQuotes((current) => ({ ...current, ...Object.fromEntries(batch.items.map((quote) => [quote.canonical_id, quote])) }));
      }
      let next = 0;
      const worker = async () => {
        while (next < ids.length) {
          const id = ids[next++];
          const series = await apiRequest<PublicHistorySeries>(`/api/v1/market-data/history/${encodeURIComponent(id)}?period=${LINE_PERIOD}&mode=PRICE&adjustment_type=UNADJUSTED`, { signal });
          const closes = series.points.filter((point) => !point.is_gap).map((point) => Number(point.close ?? point.value)).filter((value) => Number.isFinite(value) && value > 0);
          setLines((current) => ({ ...current, [id]: closes }));
        }
      };
      await Promise.all(Array.from({ length: Math.min(PARALLEL, ids.length) }, worker));
    };
    run().catch((reason: unknown) => { if (!isAbort(reason)) setError("Parte das cotações não carregou."); });
    return () => controller.abort();
  }, [idsKey]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(undefined);
    setRateLimit(undefined);
    try {
      const data = await requestJson<WatchlistList>("/api/v1/watchlists");
      setWatchlists(data.items);
      setSelectedId((current) => current || data.items[0]?.id || "");
      setSignedOut(false);
    } catch (reason) {
      if (isSignedOut(reason)) setSignedOut(true);
      else if (isRateLimited(reason)) setRateLimit({ retryAfter: retryAfterSeconds(reason) });
      else setError("Não foi possível carregar suas listas.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    requestJson<WatchlistList>("/api/v1/watchlists")
      .then((data) => {
        if (!active) return;
        setWatchlists(data.items);
        setSelectedId((current) => current || data.items[0]?.id || "");
        setSignedOut(false);
      })
      .catch((reason) => {
        if (!active) return;
        if (isSignedOut(reason)) setSignedOut(true);
        else if (isRateLimited(reason)) setRateLimit({ retryAfter: retryAfterSeconds(reason) });
        else setError("Não foi possível carregar suas listas.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function createWatchlist(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload: WatchlistCreate = { name: name.trim() };
    if (!payload.name) return;
    try {
      const created = await requestJson<Watchlist>("/api/v1/watchlists", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setName("");
      setWatchlists((current) => [...current, created]);
      setSelectedId(created.id);
    } catch {
      setError("Não foi possível criar a lista.");
    }
  }

  async function addItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedId || !canonicalId.trim()) return;
    const payload: WatchlistItemCreate = { canonical_id: canonicalId.trim().toLowerCase() };
    try {
      const added = await requestJson<WatchlistItem>(`/api/v1/watchlists/${selectedId}/items`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setCanonicalId("");
      setError(undefined);
      setWatchlists((current) => withAddedItem(current, selectedId, added));
    } catch {
      setError(ADD_ITEM_ERROR);
    }
  }

  async function addInstrument(id: string) {
    if (!selectedId) return;
    try {
      const added = await requestJson<WatchlistItem>(`/api/v1/watchlists/${selectedId}/items`, { method: "POST", body: JSON.stringify({ canonical_id: id } satisfies WatchlistItemCreate) });
      setError(undefined);
      setWatchlists((current) => withAddedItem(current, selectedId, added));
    } catch {
      setError(ADD_ITEM_ERROR);
    }
  }

  async function removeItem(listId: string, item: WatchlistItem) {
    try {
      await requestJson(`/api/v1/watchlists/${listId}/items/${encodeURIComponent(item.canonical_id)}`, {
        method: "DELETE",
      });
      setWatchlists((current) => withoutItem(current, listId, item.canonical_id));
    } catch {
      setError("Não foi possível remover o instrumento.");
    }
  }

  async function moveItem(list: Watchlist, index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= list.items.length) return;
    const canonicalIds = list.items.map((item) => item.canonical_id);
    [canonicalIds[index], canonicalIds[target]] = [canonicalIds[target], canonicalIds[index]];
    const payload: WatchlistReorder = { canonical_ids: canonicalIds };
    try {
      const updated = await requestJson<Watchlist>(`/api/v1/watchlists/${list.id}/items/reorder`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      setWatchlists((current) => withReplacedList(current, updated));
    } catch {
      setError("Não foi possível reordenar a lista.");
    }
  }

  async function deleteList(list: Watchlist) {
    if (list.is_system) return;
    try {
      await requestJson(`/api/v1/watchlists/${list.id}`, { method: "DELETE" });
      const remaining = withoutList(watchlists, list.id);
      setWatchlists(remaining);
      if (selectedId === list.id) setSelectedId(remaining[0]?.id ?? "");
    } catch {
      setError("Não foi possível remover a lista.");
    }
  }

  const selected = watchlists.find((list) => list.id === selectedId);
  const known = selected?.items.map((item) => quotes[item.canonical_id]).filter((quote): quote is PublicQuote => quote?.change_percent != null && quote.freshness !== "UNAVAILABLE") ?? [];
  const up = known.filter((quote) => Number(quote.change_percent) > 0).length;
  const down = known.filter((quote) => Number(quote.change_percent) < 0).length;

  if (loading) return <main id="main-content" className={`${styles.page} terminal-root`}><h1 className="sr-only">Watchlists e favoritos</h1><p className="loading-state">Carregando watchlists…</p></main>;
  if (signedOut) {
    return (
      <main id="main-content" className={`${styles.page} terminal-root`}>
        <section className={styles.glass} aria-labelledby="watchlists-title">
          <h1 id="watchlists-title">Favoritos</h1>
          <p className="muted">Entre para acessar suas listas privadas e favoritos.</p>
          <Link className="auth-submit watchlists-link" href="/login">Ir para login</Link>
        </section>
      </main>
    );
  }

  return (
    <main id="main-content" className={`${styles.page} terminal-root`}>
      <section className={styles.hero}>
        <div>
          <span className={styles.chip}>Área privada</span>
          <h1 id="watchlists-title">Favoritos e listas</h1>
          <p>Acompanhe os ativos que você escolheu, com fonte e horário de cada número. {FINANCIAL_DISCLAIMER}</p>
        </div>
        {selected && <ul className={styles.heroStats} aria-label="Resumo da lista">
          <li>Ativos<strong>{selected.items.length}</strong></li>
          <li>Em alta<strong>{up}</strong></li>
          <li>Em queda<strong>{down}</strong></li>
        </ul>}
      </section>

      <div className={styles.pills} role="group" aria-label="Listas">
        {watchlists.map((list) => <button key={list.id} type="button" aria-pressed={selectedId === list.id} onClick={() => setSelectedId(list.id)}>{list.name}<small>{list.items.length}</small></button>)}
        {selected && !selected.is_system && <button type="button" onClick={() => void deleteList(selected)} aria-label={`Excluir watchlist ${selected.name}`}>Excluir esta lista</button>}
      </div>

      <section className={`${styles.glass} ${styles.tools}`} aria-label="Controles de watchlist">
        <div className={styles.tool}><span>Adicionar ativo à lista</span><InstrumentSearch onSelect={(id) => void addInstrument(id)} /></div>
        <form onSubmit={createWatchlist} className={styles.tool}>
          <label htmlFor="watchlist-name">Nova lista</label>
          <div className={styles.row}><input id="watchlist-name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Nome da lista" /><button type="submit" className={styles.button}>Criar lista</button></div>
        </form>
        <details className={styles.more}>
          <summary>Adicionar por identificador</summary>
          <form onSubmit={addItem} className={styles.tool}>
            <label htmlFor="watchlist-canonical-id">Adicionar por canonical_id</label>
            <div className={styles.row}><input id="watchlist-canonical-id" value={canonicalId} onChange={(event) => setCanonicalId(event.target.value)} placeholder="equity.br.b3.petr4" disabled={!selectedId} /><button type="submit" className={styles.button} disabled={!selectedId}>Adicionar</button></div>
          </form>
        </details>
      </section>

      {rateLimit && <RateLimitNotice retryAfter={rateLimit.retryAfter} onRetry={() => void load()} />}
      {error && <p className="state-note" role="alert">{error}</p>}
      {watchlists.length === 0 && !rateLimit && <section className={styles.glass}><p className="muted">Nenhuma lista criada ainda. O estado vazio não contém dados inventados.</p></section>}
      {selected && selected.items.length === 0 && <section className={styles.glass}><p className="muted">Lista vazia. Use a busca acima para adicionar um ativo.</p></section>}

      {selected && selected.items.length > 0 && <>
        <ul className={styles.cards} aria-label={`Ativos de ${selected.name}`}>
          {selected.items.map((item, index) => {
            const quote = quotes[item.canonical_id];
            const closes = lines[item.canonical_id];
            const stats = closes ? seriesStats(closes, annualizationDays(item.canonical_id)) : null;
            const change = quote && quote.freshness !== "UNAVAILABLE" ? describeChange(quote.change, quote.change_percent, quote.currency) : null;
            return (
              <li key={item.id} className={styles.card}>
                <div className={styles.cardHead}><Link href={`/assets?id=${encodeURIComponent(item.canonical_id)}`}>{item.display_symbol}</Link><span className={styles.tag}>{item.exchange ?? item.instrument_type}</span></div>
                <span className={styles.name} title={item.name}>{item.name}</span>
                <div className={styles.priceRow}>
                  <div className={styles.price}>
                    {quote?.price == null ? <small>{quote ? `Sem valor: ${shortReason(quote.unavailable_reason)}` : "Carregando…"}</small> : `${quote.currency} ${formatAmount(quote.price)}`}
                    {change && <small className={`direction-${change.direction.toLowerCase()}`}><span aria-hidden="true">{change.cue.glyph}</span> {signedDecimal(quote?.change_percent ?? "0", change.direction)}% {change.cue.word}</small>}
                  </div>
                  {closes && closes.length > 1 && stats && <Sparkline closes={closes} up={stats.returnPercent >= 0} />}
                </div>
                <div className={styles.meta}>
                  {stats && <><span>Mín. 3M {formatNumber(stats.min)}</span><span>Máx. 3M {formatNumber(stats.max)}</span></>}
                  {quote && <DataStateBadge dataLevel={quote.data_level} freshness={quote.freshness} />}
                </div>
                <div className={styles.actions}>
                  <button type="button" className={styles.ghost} onClick={() => void moveItem(selected, index, -1)} disabled={index === 0} aria-label={`Subir ${item.display_symbol}`}>Subir</button>
                  <button type="button" className={styles.ghost} onClick={() => void moveItem(selected, index, 1)} disabled={index === selected.items.length - 1} aria-label={`Descer ${item.display_symbol}`}>Descer</button>
                  <button type="button" className={styles.ghost} onClick={() => void removeItem(selected.id, item)} aria-label={`Remover ${item.display_symbol}`}>Remover</button>
                </div>
              </li>
            );
          })}
        </ul>

        <section className={styles.glass} aria-labelledby="watch-metrics">
          <h2 id="watch-metrics">Métricas dos últimos 3 meses</h2>
          <div className="table-wrap"><table>
            <caption className="sr-only">Último valor, variação do dia e estatísticas de 3 meses de cada ativo</caption>
            <thead><tr><th scope="col">Ativo</th><th scope="col">Tipo</th><th scope="col">Último</th><th scope="col">Dia</th><th scope="col">Retorno 3M</th><th scope="col">Mínimo</th><th scope="col">Máximo</th><th scope="col">Volatilidade</th><th scope="col">Estado</th></tr></thead>
            <tbody>{selected.items.map((item) => {
              const quote = quotes[item.canonical_id];
              const closes = lines[item.canonical_id];
              const stats = closes ? seriesStats(closes, annualizationDays(item.canonical_id)) : null;
              const cue = quote && quote.freshness !== "UNAVAILABLE" ? percentCue(quote.change_percent ?? null) : null;
              return <tr key={item.id}>
                <th scope="row">{item.display_symbol}<br /><small>{item.canonical_id}</small></th>
                <td>{item.instrument_type}</td>
                <td>{quote?.price == null ? "—" : `${quote.currency} ${formatAmount(quote.price)}`}</td>
                <td className={cue ? `direction-${cue.direction.toLowerCase()}` : ""}>{cue?.text ?? "—"}</td>
                <td>{stats ? `${stats.returnPercent > 0 ? "+" : ""}${formatNumber(stats.returnPercent)}%` : "—"}</td>
                <td>{stats ? formatNumber(stats.min) : "—"}</td>
                <td>{stats ? formatNumber(stats.max) : "—"}</td>
                <td>{stats?.volatility != null ? `${formatNumber(stats.volatility)}% a.a.` : "—"}</td>
                <td><small>{item.support_state}</small></td>
              </tr>;
            })}</tbody>
          </table></div>
          <p className={styles.note}>Calculado dos fechamentos diários de 3 meses, sem ajuste por proventos. Volatilidade: desvio-padrão dos retornos logarítmicos, anualizado por 252 pregões (365 em cripto). Descreve o passado e não indica o futuro.</p>
        </section>
      </>}
    </main>
  );
}
