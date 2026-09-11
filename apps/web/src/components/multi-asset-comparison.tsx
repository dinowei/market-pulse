"use client";

import { useEffect, useMemo, useState } from "react";

import type { components } from "../generated/api";

type PublicHistorySeries = components["schemas"]["PublicHistorySeries"];
type BatchHistoryResponse = components["schemas"]["BatchHistoryResponse"];
type SeriesMode = components["schemas"]["SeriesMode"];

const DEFAULT_IDS = ["equity.br.b3.petr4", "index.br.b3.ibovespa"];

function pointValue(point: PublicHistorySeries["points"][number], mode: SeriesMode): number | null {
  if (point.is_gap) return null;
  const value = mode === "INDEX_100" ? point.index_100 : point.close ?? point.value;
  if (value == null) return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function linePath(series: PublicHistorySeries, mode: SeriesMode, minTime: number, timeRange: number, minValue: number, valueRange: number): string {
  let path = "";
  let previousWasGap = true;
  series.points.forEach((point) => {
    const value = pointValue(point, mode);
    const timestamp = Date.parse(point.timestamp);
    if (value == null || !Number.isFinite(timestamp)) {
      previousWasGap = true;
      return;
    }
    const x = ((timestamp - minTime) / timeRange) * 100;
    const y = 46 - ((value - minValue) / valueRange) * 42;
    path += `${previousWasGap ? "M" : "L"} ${x} ${y} `;
    previousWasGap = false;
  });
  return path.trim();
}

export function MultiAssetComparison({ initialIds = DEFAULT_IDS }: { initialIds?: string[] }) {
  const [mode, setMode] = useState<SeriesMode>("INDEX_100");
  const [series, setSeries] = useState<PublicHistorySeries[]>([]);
  const [error, setError] = useState<string | null>(null);
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${apiBase}/api/v1/market-data/history/batch`, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ canonical_ids: initialIds.slice(0, 10), period: "1M", mode }),
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return (await response.json()) as BatchHistoryResponse;
      })
      .then((payload) => setSeries(payload.items))
      .catch((reason: unknown) => {
        if (reason instanceof Error && reason.name !== "AbortError") setError(reason.message);
      });
    return () => controller.abort();
  }, [apiBase, initialIds, mode]);

  const geometry = useMemo(() => {
    const values = series.flatMap((item) => item.points.map((point) => pointValue(point, mode)).filter((value): value is number => value !== null));
    const timestamps = series.flatMap((item) => item.points.map((point) => Date.parse(point.timestamp)).filter(Number.isFinite));
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const minTime = Math.min(...timestamps);
    const maxTime = Math.max(...timestamps);
    return {
      minValue,
      valueRange: maxValue - minValue || 1,
      minTime,
      timeRange: maxTime - minTime || 1,
    };
  }, [mode, series]);

  return (
    <section className="comparison-panel" aria-labelledby="comparison-title">
      <div className="section-heading">
        <div><p className="eyebrow">PARTICLE ATLAS / COMPARAÇÃO</p><h2 id="comparison-title">Ativo e benchmark</h2></div>
        <div className="control-row" role="group" aria-label="Modo de comparação">
          {(["PRICE", "INDEX_100"] as const).map((candidate) => <button type="button" className={mode === candidate ? "control active" : "control"} aria-pressed={mode === candidate} key={candidate} onClick={() => setMode(candidate)}>{candidate}</button>)}
        </div>
      </div>
      {error && <p className="state-note" role="alert">Comparação indisponível: {error}</p>}
      {!error && series.length === 0 && <p className="loading-state">Carregando séries…</p>}
      {series.length > 0 && <>
        <p className="sr-only">reduced_motion: sem animação de dados financeiros</p>
        <figure className="particle-chart comparison-chart">
          <svg viewBox="0 0 100 48" role="img" aria-label={`Comparação ${mode} com ${series.length} séries`} preserveAspectRatio="none">
            <line x1="0" y1="46" x2="100" y2="46" className="chart-axis" />
            {series.map((item) => <path key={item.canonical_id} d={linePath(item, mode, geometry.minTime, geometry.timeRange, geometry.minValue, geometry.valueRange)} className={item.canonical_id.startsWith("index.") || item.canonical_id.startsWith("rate.") || item.canonical_id.startsWith("fx.") ? "chart-line chart-benchmark" : "chart-line"} fill="none" />)}
          </svg>
          <figcaption>{mode === "INDEX_100" ? "Todas as séries rebaseadas para 100 no início do período." : "Valores nominais; moeda e unidade preservadas na tabela."}</figcaption>
        </figure>
        <div className="table-wrap"><table><caption>Fallback tabular sincronizado com as séries exibidas</caption><thead><tr><th scope="col">Data</th>{series.map((item) => <th scope="col" key={item.canonical_id}>{item.symbol} · {item.currency}</th>)}</tr></thead><tbody>{series[0].points.map((point, index) => <tr key={point.timestamp}><th scope="row">{point.session_date}</th>{series.map((item) => { const current = item.points[index]; const value = current ? pointValue(current, mode) : null; return <td key={item.canonical_id}>{value == null ? "—" : value}</td>; })}</tr>)}</tbody></table></div>
        <p className="comparison-provenance">Fonte sintética DEMO; cada série mantém `DataLevel`, `Freshness`, timestamps e limitações no contrato.</p>
      </>}
    </section>
  );
}
