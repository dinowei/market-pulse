"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import type { components } from "../generated/api";
import { isRateLimited, parseRetryAfter, RateLimitNotice, retryAfterSeconds } from "./rate-limit-notice";
import { FINANCIAL_DISCLAIMER } from "../lib/disclaimers";
import { ADD_ITEM_ERROR, withAddedItem, withoutItem, withoutList, withReplacedList } from "../lib/watchlist-state";

type Watchlist = components["schemas"]["WatchlistResponse"];
type WatchlistList = components["schemas"]["WatchlistListResponse"];
type WatchlistItem = components["schemas"]["WatchlistItemResponse"];
type WatchlistCreate = components["schemas"]["WatchlistCreateRequest"];
type WatchlistItemCreate = components["schemas"]["WatchlistItemCreateRequest"];
type WatchlistReorder = components["schemas"]["WatchlistReorderRequest"];

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

export function WatchlistsPanel() {
  const [watchlists, setWatchlists] = useState<Watchlist[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [name, setName] = useState("");
  const [canonicalId, setCanonicalId] = useState("");
  const [loading, setLoading] = useState(true);
  const [signedOut, setSignedOut] = useState(false);
  const [error, setError] = useState<string | undefined>();
  const [rateLimit, setRateLimit] = useState<{ retryAfter?: number } | undefined>();

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

  if (loading) return <main className="watchlists-page terminal-root"><p className="loading-state">Carregando watchlists…</p></main>;
  if (signedOut) {
    return (
      <main className="watchlists-page terminal-root">
        <section className="watchlists-card" aria-labelledby="watchlists-title">
          <p className="eyebrow">ÁREA PRIVADA</p>
          <h1 id="watchlists-title">Watchlists</h1>
          <p className="muted">Entre para acessar suas listas privadas e favoritos.</p>
          <Link className="auth-submit watchlists-link" href="/login">Ir para login</Link>
        </section>
      </main>
    );
  }

  return (
    <main className="watchlists-page terminal-root">
      <header className="watchlists-header">
        <div><p className="eyebrow">PARTICLE ATLAS / ÁREA PRIVADA</p><h1 id="watchlists-title">Watchlists e favoritos</h1></div>
        <Link href="/" className="watchlists-back">Voltar ao terminal</Link>
      </header>
      <p className="watchlists-disclaimer">{FINANCIAL_DISCLAIMER} Uma watchlist apenas registra a identidade dos instrumentos acompanhados.</p>
      <section className="watchlists-toolbar" aria-label="Controles de watchlist">
        <form onSubmit={createWatchlist} className="watchlist-form">
          <label htmlFor="watchlist-name">Nova lista</label>
          <div className="watchlist-form-row"><input id="watchlist-name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Nome da lista" /><button type="submit">Criar lista</button></div>
        </form>
        <form onSubmit={addItem} className="watchlist-form">
          <label htmlFor="watchlist-canonical-id">Adicionar por canonical_id</label>
          <div className="watchlist-form-row"><input id="watchlist-canonical-id" value={canonicalId} onChange={(event) => setCanonicalId(event.target.value)} placeholder="equity.br.b3.petr4" disabled={!selectedId} /><button type="submit" disabled={!selectedId}>Adicionar</button></div>
        </form>
      </section>
      {rateLimit && <RateLimitNotice retryAfter={rateLimit.retryAfter} onRetry={() => void load()} />}
      {error && <p className="state-note" role="alert">{error}</p>}
      {watchlists.length === 0 && !rateLimit && <section className="watchlists-card"><p className="muted">Nenhuma lista criada ainda. O estado vazio não contém dados inventados.</p></section>}
      <div className="watchlists-grid">
        {watchlists.map((list) => (
          <section className="watchlists-card" key={list.id} aria-labelledby={`watchlist-${list.id}`}>
            <div className="watchlist-card-heading"><div><p className="eyebrow">{list.is_system ? "SISTEMA" : "LISTA PRIVADA"}</p><h2 id={`watchlist-${list.id}`}>{list.name}</h2></div>{!list.is_system && <button type="button" className="watchlist-danger" onClick={() => void deleteList(list)} aria-label={`Excluir watchlist ${list.name}`}>Excluir</button>}</div>
            <button type="button" className="watchlist-select" onClick={() => setSelectedId(list.id)} aria-pressed={selectedId === list.id}>{selectedId === list.id ? "Lista selecionada" : "Selecionar lista"}</button>
            {list.items.length === 0 ? <p className="muted">Lista vazia.</p> : <ol className="watchlist-items">{list.items.map((item, index) => <li key={item.id}><div><strong>{item.display_symbol}</strong><span>{item.name} · {item.instrument_type}</span><small>{item.canonical_id} · {item.exchange ?? "GLOBAL"} · {item.currency} · {item.timezone}</small><small>Status: {item.support_state} · preço: UNAVAILABLE até fonte aprovada</small></div><div className="watchlist-item-actions"><button type="button" onClick={() => void moveItem(list, index, -1)} disabled={index === 0} aria-label={`Subir ${item.display_symbol}`}>Subir</button><button type="button" onClick={() => void moveItem(list, index, 1)} disabled={index === list.items.length - 1} aria-label={`Descer ${item.display_symbol}`}>Descer</button><button type="button" onClick={() => void removeItem(list.id, item)} aria-label={`Remover ${item.display_symbol}`}>Remover</button></div></li>)}</ol>}
          </section>
        ))}
      </div>
    </main>
  );
}
