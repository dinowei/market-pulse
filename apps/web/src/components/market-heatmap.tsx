"use client";

import { useEffect, useState } from "react";

import type { components } from "../generated/api";
import { FINANCIAL_DISCLAIMER } from "../lib/disclaimers";
import { describeChange } from "../lib/price-direction";

type HeatmapResponse = components["schemas"]["HeatmapResponse"];
type PublicQuote = components["schemas"]["PublicQuote"];

// Basic P0 heatmap (ADR-019): equal-area tiles grouped as the API declares, color by
// direction only, and an equivalent table with every tile's provenance.
const GROUP_LABEL: Record<string, string> = { EQUITY: "Ações", ETF: "ETFs", FII: "Fundos imobiliários", BDR: "BDRs" };
const METHOD_LABEL: Record<string, string> = {
  INSTRUMENT_TYPE: "agrupamento por tipo de instrumento",
  EQUAL_AREA: "blocos de mesma área",
  DIRECTION_VS_PREVIOUS_CLOSE: "cor pela direção contra o fechamento anterior",
};

function Tile({ quote }: { quote: PublicQuote }) {
  const change = describeChange(quote.change, quote.change_percent, quote.currency);
  const unavailable = quote.freshness === "UNAVAILABLE";
  const tone = unavailable ? "unavailable" : change ? change.direction.toLowerCase() : "unknown";
  return (
    <li className={`heatmap-tile heatmap-tile-${tone}`}>
      <strong>{quote.symbol}</strong>
      {unavailable && <span>Indisponível</span>}
      {!unavailable && !change && <span>Variação indisponível</span>}
      {change && <span className={`direction-${change.direction.toLowerCase()}`}><span aria-hidden="true">{change.cue.glyph}</span> {change.text} · {change.cue.word}</span>}
      <small>{quote.data_level} · {quote.freshness}</small>
    </li>
  );
}

export function MarketHeatmap() {
  const [payload, setPayload] = useState<HeatmapResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${apiBase}/api/v1/market-data/heatmap`, { headers: { Accept: "application/json" }, signal: controller.signal })
      .then(async (response) => { if (!response.ok) throw new Error(`HTTP ${response.status}`); return (await response.json()) as HeatmapResponse; })
      .then(setPayload)
      .catch((reason: unknown) => { if (reason instanceof Error && reason.name !== "AbortError") setError(reason.message); });
    return () => controller.abort();
  }, [apiBase]);

  const tiles = payload?.groups.flatMap((group) => group.tiles.map((quote) => ({ group: group.group, quote }))) ?? [];
  return (
    <section className="heatmap-panel" aria-labelledby="heatmap-title">
      <div className="section-heading"><div><p className="eyebrow">MERCADO / HEATMAP</p><h2 id="heatmap-title">Heatmap básico</h2></div><span className="state-label">INFORMATIVO</span></div>
      {error && <p className="state-note" role="alert">Heatmap indisponível: {error}</p>}
      {!error && !payload && <p className="loading-state">Carregando heatmap…</p>}
      {payload && <>
        <p className="muted">Método: {[payload.grouping, payload.sizing, payload.color_basis].map((key) => METHOD_LABEL[key] ?? key).join("; ")}.</p>
        {payload.groups.length === 0 && <p className="muted">Nenhum instrumento elegível no catálogo.</p>}
        {payload.groups.map((group) => (
          <section key={group.group} className="heatmap-group" aria-labelledby={`heatmap-${group.group}`}>
            <h3 id={`heatmap-${group.group}`}>{GROUP_LABEL[group.group] ?? group.group} <small>({group.group})</small></h3>
            <ul className="heatmap-grid">{group.tiles.map((quote) => <Tile key={quote.canonical_id} quote={quote} />)}</ul>
          </section>
        ))}
        <div className="table-wrap"><table><caption>Tabela equivalente ao heatmap, com a origem de cada bloco</caption><thead><tr><th scope="col">Instrumento</th><th scope="col">Grupo</th><th scope="col">Preço</th><th scope="col">Variação</th><th scope="col">Estado</th><th scope="col">Fonte e horário oficial</th><th scope="col">Limitações</th></tr></thead><tbody>{tiles.map(({ group, quote }) => {
          const change = describeChange(quote.change, quote.change_percent, quote.currency);
          return <tr key={quote.canonical_id}><th scope="row">{quote.symbol}<br /><small>{quote.canonical_id}</small></th><td>{group}</td><td>{quote.price == null ? "Indisponível" : `${quote.currency} ${quote.price}`}</td><td>{change ? `${change.text} (${change.cue.word})` : "Indisponível"}</td><td>{quote.data_level} · {quote.freshness}{quote.unavailable_reason ? ` · ${quote.unavailable_reason}` : ""}</td><td>{quote.provider} · {quote.dataset}<br /><small>{quote.timestamp_official ?? "sem horário oficial"}</small></td><td><small>{quote.limitations.join("; ") || "—"}</small></td></tr>;
        })}</tbody></table></div>
        <ul className="heatmap-limitations" aria-label="Limitações do heatmap">{payload.limitations.map((text) => <li key={text}>{text}</li>)}</ul>
      </>}
      <p className="financial-disclaimer">{FINANCIAL_DISCLAIMER}</p>
    </section>
  );
}
