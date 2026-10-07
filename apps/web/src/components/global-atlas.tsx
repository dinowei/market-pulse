"use client";

import { useEffect, useState } from "react";

import type { components } from "../generated/api";
import { FINANCIAL_DISCLAIMER } from "../lib/disclaimers";

type InstrumentList = components["schemas"]["InstrumentList"];
type InstrumentSummary = components["schemas"]["InstrumentSummary"];

const ATLAS_LIMIT = 100;
const COLUMNS = 8;

// Tabular Global Atlas (P0, ADR-019): verifiable relations between regions, exchanges and
// catalog instruments. Metadata only; it never shows a price.
function byRegion(items: InstrumentSummary[]): [string, InstrumentSummary[]][] {
  const groups = new Map<string, InstrumentSummary[]>();
  for (const item of items) {
    const region = item.region ?? "Sem região";
    groups.set(region, [...(groups.get(region) ?? []), item]);
  }
  return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b));
}

export function GlobalAtlas() {
  const [payload, setPayload] = useState<InstrumentList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${apiBase}/api/v1/instruments?limit=${ATLAS_LIMIT}&sort=symbol&order=asc`, { headers: { Accept: "application/json" }, signal: controller.signal })
      .then(async (response) => { if (!response.ok) throw new Error(`HTTP ${response.status}`); return (await response.json()) as InstrumentList; })
      .then(setPayload)
      .catch((reason: unknown) => { if (reason instanceof Error && reason.name !== "AbortError") setError(reason.message); });
    return () => controller.abort();
  }, [apiBase]);

  return (
    <section className="atlas-panel" aria-labelledby="atlas-title">
      <div className="section-heading"><div><p className="eyebrow">PARTICLE ATLAS / GLOBAL</p><h2 id="atlas-title">Global Atlas</h2></div><span className="state-label">CATÁLOGO · SEM PREÇOS</span></div>
      <p className="muted">Regiões, bolsas e instrumentos do catálogo do Market Pulse. O estado de cada linha diz se há dado aprovado; nenhuma linha é cotação.</p>
      {error && <p className="state-note" role="alert">Global Atlas indisponível: {error}</p>}
      {!error && !payload && <p className="loading-state">Carregando catálogo…</p>}
      {payload && payload.items.length === 0 && <p className="muted">Catálogo vazio.</p>}
      {payload && payload.items.length > 0 && <div className="table-wrap"><table><caption>Global Atlas em tabela: instrumentos agrupados por região</caption><thead><tr><th scope="col">Instrumento</th><th scope="col">Tipo</th><th scope="col">País</th><th scope="col">Bolsa</th><th scope="col">Moeda</th><th scope="col">Fuso</th><th scope="col">Cobertura</th><th scope="col">Estado do dado</th></tr></thead>
        {byRegion(payload.items).map(([region, items]) => <tbody key={region}>
          <tr className="atlas-region"><th scope="rowgroup" colSpan={COLUMNS}>Região {region} · {items.length} {items.length === 1 ? "instrumento" : "instrumentos"}</th></tr>
          {items.map((item) => <tr key={item.canonical_id}><th scope="row">{item.symbol}<br /><small>{item.name}</small></th><td>{item.instrument_type}</td><td>{item.country ?? "—"}</td><td>{item.exchange ?? "—"}</td><td>{item.currency}</td><td>{item.timezone ?? "—"}</td><td>{item.coverage_tier}<br /><small>{item.catalog_status}</small></td><td>{item.support_state}<br /><small>{item.data_support_status}</small></td></tr>)}
        </tbody>)}
      </table></div>}
      {payload?.meta.next_offset != null && <p className="muted" role="note">Mostrando os primeiros {ATLAS_LIMIT} instrumentos do catálogo.</p>}
      <p className="financial-disclaimer">{FINANCIAL_DISCLAIMER}</p>
    </section>
  );
}
