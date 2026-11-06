"use client";

import { useEffect, useState } from "react";

import type { components } from "../generated/api";
import { API_BASE } from "../lib/api-client";

type InstrumentSummary = components["schemas"]["InstrumentSummary"];
type InstrumentList = components["schemas"]["InstrumentList"];

export function InstrumentSearch({ onSelect, placeholder = "Buscar ativo, índice ou moeda" }: { onSelect: (canonicalId: string) => void; placeholder?: string }) {
  const [query, setQuery] = useState("");
  const [state, setState] = useState<{ key: string; data?: InstrumentList }>({ key: "" });
  useEffect(() => {
    const normalized = query.trim();
    if (normalized.length < 2) return;
    const controller = new AbortController();
    fetch(`${API_BASE}/api/v1/instruments/search?q=${encodeURIComponent(normalized)}`, { signal: controller.signal, headers: { Accept: "application/json" } })
      .then((response) => (response.ok ? (response.json() as Promise<InstrumentList>) : Promise.reject(new Error(`HTTP ${response.status}`))))
      .then((data) => setState({ key: normalized, data }))
      .catch(() => undefined);
    return () => controller.abort();
  }, [query]);
  const items: InstrumentSummary[] = state.key === query.trim() ? state.data?.items ?? [] : [];
  return (
    <div className="search-wrap">
      <label className="search"><span className="sr-only">Buscar instrumento</span><input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder={placeholder} /></label>
      {items.length > 0 && <ul id="instrument-results" className="search-results" role="listbox">{items.map((item) => <li key={item.canonical_id}><button type="button" role="option" aria-selected={false} onClick={() => { onSelect(item.canonical_id); setQuery(""); }}>{item.display_symbol} · {item.name}<small>{item.support_state}</small></button></li>)}</ul>}
      {query.trim().length >= 2 && state.key === query.trim() && items.length === 0 && <p className="search-empty">Nenhum instrumento no catálogo.</p>}
    </div>
  );
}
