import type { components } from "../generated/api";

type Watchlist = components["schemas"]["WatchlistResponse"];
type WatchlistItem = components["schemas"]["WatchlistItemResponse"];

// H-21: apply each mutation's own response instead of reloading every list (one request
// per action instead of two). The server stays the source of truth: these only mirror
// what it just returned or confirmed with 204.

export function withAddedItem(lists: Watchlist[], listId: string, item: WatchlistItem): Watchlist[] {
  return lists.map((list) =>
    list.id === listId
      ? { ...list, items: [...list.items.filter((current) => current.canonical_id !== item.canonical_id), item].sort((a, b) => a.position - b.position) }
      : list,
  );
}

export function withoutItem(lists: Watchlist[], listId: string, canonicalId: string): Watchlist[] {
  return lists.map((list) => (list.id === listId ? { ...list, items: list.items.filter((item) => item.canonical_id !== canonicalId) } : list));
}

export function withReplacedList(lists: Watchlist[], updated: Watchlist): Watchlist[] {
  return lists.map((list) => (list.id === updated.id ? updated : list));
}

export function withoutList(lists: Watchlist[], listId: string): Watchlist[] {
  return lists.filter((list) => list.id !== listId);
}

export const ADD_ITEM_ERROR =
  "Instrumento indisponível ou fora do universo suportado. Use o identificador do catálogo, por exemplo equity.br.b3.petr4.";
