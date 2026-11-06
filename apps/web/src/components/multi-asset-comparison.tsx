"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState, type PointerEvent } from "react";

import type { components } from "../generated/api";
import { apiRequest, isAbort } from "../lib/api-client";
import { defaultComparisonIds, MAX_COMPARED_SERIES } from "../lib/comparison-defaults";
import { CANONICAL_ID } from "../lib/canonical-id";
import { comparisonLines, commonStart, nearestPoint, type SeriesMode } from "../lib/comparison-series";
import { comparisonRows } from "../lib/comparison-table";
import { InstrumentSearch } from "./market-data";
import { DISPLAY_MAX_POINTS } from "../lib/downsampling-note";
import { FINANCIAL_DISCLAIMER } from "../lib/disclaimers";
import { seriesRole, seriesRoleLabel } from "../lib/series-role";
import { formatReason } from "../lib/unavailable-reasons";

type PublicHistorySeries = components["schemas"]["PublicHistorySeries"];
type BatchHistoryResponse = components["schemas"]["BatchHistoryResponse"];
type HistoryPeriod = components["schemas"]["HistoryPeriod"];
type InstrumentList = components["schemas"]["InstrumentList"];
type BenchmarkList = components["schemas"]["BenchmarkListResponse"];

const PERIODS = ["1M", "3M", "6M", "1A", "5A"] as const satisfies readonly HistoryPeriod[];
// Distinct by hue and by dash, so a line is never told apart by color alone.
const LINE_STYLES = [
  { color: "var(--pa-text-primary)", dash: "" }, { color: "var(--pa-market-up)", dash: "3 1.5" }, { color: "var(--pa-cyan)", dash: "" }, { color: "var(--pa-violet)", dash: "1 1" },
  { color: "var(--pa-state-stale)", dash: "" }, { color: "var(--pa-market-down)", dash: "3 1.5" }, { color: "var(--pa-market-flat)", dash: "" }, { color: "var(--pa-text-secondary)", dash: "1 1" },
  { color: "var(--pa-cyan)", dash: "4 1" }, { color: "var(--pa-violet)", dash: "" },
];
// Declares the auto-fitted vertical scale, so a tiny move is not read as a large one.
const AXIS_FORMAT = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
// References are always dashed blue, as everywhere else in the site.
const lineStyle = (id: string, index: number) => (seriesRole(id) === "benchmark" ? { color: "var(--pa-market-flat)", dash: "3 1.5" } : LINE_STYLES[index % LINE_STYLES.length]);
const formatDay = (time: number) => new Date(time).toISOString().slice(0, 10).split("-").reverse().join("/");
const percentText = (value: number | null) => (value === null ? "—" : `${value > 0 ? "+" : value < 0 ? "−" : ""}${AXIS_FORMAT.format(Math.abs(value))}%`);
const tone = (value: number | null) => (value === null ? "" : value > 0 ? "direction-up" : value < 0 ? "direction-down" : "direction-flat");
const glyph = (value: number | null) => (value === null ? "" : value > 0 ? "▲ " : value < 0 ? "▼ " : "▬ ");

export function MultiAssetComparison({ initialIds }: { initialIds?: string[] }) {
  const [mode, setMode] = useState<SeriesMode>("INDEX_100");
  const [period, setPeriod] = useState<HistoryPeriod>("3M");
  const [catalogIds, setCatalogIds] = useState<string[] | null>(null);
  const [chosen, setChosen] = useState<string[] | null>(null);
  const [benchmarks, setBenchmarks] = useState<BenchmarkList["items"]>([]);
  const [series, setSeries] = useState<PublicHistorySeries[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cursor, setCursor] = useState<number | null>(null);
  const ids = chosen ?? initialIds ?? catalogIds;

  function choose(next: string[]) {
    setError(null);
    setLoading(true);
    setChosen(next);
  }
  const addSeries = (canonicalId: string) => {
    if (ids && !ids.includes(canonicalId) && ids.length < MAX_COMPARED_SERIES) choose([...ids, canonicalId]);
  };
  const removeSeries = (canonicalId: string) => {
    if (ids && ids.length > 1) choose(ids.filter((id) => id !== canonicalId));
  };

  useEffect(() => {
    const controller = new AbortController();
    apiRequest<BenchmarkList>("/api/v1/market-data/benchmarks", { signal: controller.signal })
      .then((payload) => setBenchmarks(payload.items))
      .catch(() => undefined);
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (initialIds) return undefined;
    const controller = new AbortController();
    apiRequest<InstrumentList>("/api/v1/instruments?limit=100&sort=created_at&order=asc", { signal: controller.signal })
      .then((payload) => setCatalogIds(defaultComparisonIds(payload.items)))
      .catch((reason: unknown) => { if (!isAbort(reason)) setError((reason as Error).message); });
    return () => controller.abort();
  }, [initialIds]);

  useEffect(() => {
    if (!ids) return undefined;
    const controller = new AbortController();
    apiRequest<BatchHistoryResponse>("/api/v1/market-data/history/batch", {
      method: "POST",
      body: JSON.stringify({ canonical_ids: ids.slice(0, 10), period, mode, max_points: DISPLAY_MAX_POINTS }),
      signal: controller.signal,
    })
      .then((payload) => { setSeries(payload.items); setLoading(false); })
      .catch((reason: unknown) => { if (!isAbort(reason)) { setError((reason as Error).message); setLoading(false); } });
    return () => controller.abort();
  }, [ids, mode, period]);

  const lines = useMemo(() => comparisonLines(series, mode), [series, mode]);
  const start = useMemo(() => commonStart(series, mode), [series, mode]);
  const drawn = lines.filter((line) => line.points.length > 1);
  const geometry = useMemo(() => {
    const values = drawn.flatMap((line) => line.points.map((point) => point.value));
    const times = drawn.flatMap((line) => line.points.map((point) => point.time));
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const minTime = Math.min(...times);
    const maxTime = Math.max(...times);
    return { minValue, maxValue, valueRange: maxValue - minValue || 1, minTime, maxTime, timeRange: maxTime - minTime || 1 };
  }, [drawn]);
  const x = (time: number) => ((time - geometry.minTime) / geometry.timeRange) * 100;
  const y = (value: number) => 46 - ((value - geometry.minValue) / geometry.valueRange) * 42;

  function moveCursor(event: PointerEvent<SVGSVGElement>) {
    const box = event.currentTarget.getBoundingClientRect();
    setCursor(geometry.minTime + ((event.clientX - box.left) / box.width) * geometry.timeRange);
  }

  const missing = series.filter((item) => item.points.every((point) => point.is_gap));
  const shorter = lines.filter((line) => line.firstDate && start !== null && line.points.length > 1 && Date.parse(line.firstDate) === start && lines.some((other) => other.firstDate && Date.parse(other.firstDate) < start));
  const sources = [...new Set(series.filter((item) => item.points.length > 0).map((item) => item.provider))];

  return (
    <section className="comparison-panel" aria-labelledby="comparison-title">
      <div className="section-heading">
        <div><p className="eyebrow">Comparação</p><h2 id="comparison-title">Compare ativos, moedas e referências</h2></div>
        <div className="control-row">
          <div className="control-row" role="group" aria-label="Período">{PERIODS.map((candidate) => <button type="button" className={period === candidate ? "control active" : "control"} aria-pressed={period === candidate} key={candidate} onClick={() => { setLoading(true); setPeriod(candidate); }}>{candidate}</button>)}</div>
          <div className="control-row" role="group" aria-label="Modo de comparação">{(["INDEX_100", "PRICE"] as const).map((candidate) => <button type="button" className={mode === candidate ? "control active" : "control"} aria-pressed={mode === candidate} key={candidate} onClick={() => { setLoading(true); setMode(candidate); }}>{candidate === "INDEX_100" ? "Base 100" : "Preço"}</button>)}</div>
        </div>
      </div>
      {ids && <fieldset className="control-group compare-picker">
        <legend>Séries comparadas ({ids.length} de {MAX_COMPARED_SERIES})</legend>
        <ul className="compare-chips">{ids.map((id) => <li key={id}><span>{series.find((item) => item.canonical_id === id)?.symbol ?? id}</span><button type="button" className="control" aria-label={`Remover ${id} da comparação`} disabled={ids.length === 1} onClick={() => removeSeries(id)}>Remover</button></li>)}</ul>
        {ids.length < MAX_COMPARED_SERIES && <div className="compare-add">
          <InstrumentSearch onSelect={addSeries} />
          {benchmarks.length > 0 && <label>Referência <select value="" onChange={(event) => { if (event.target.value) addSeries(event.target.value); }}><option value="">Adicionar benchmark</option>{benchmarks.filter((item) => !ids.includes(item.canonical_id)).map((item) => <option key={item.canonical_id} value={item.canonical_id}>{item.symbol} · {item.name}</option>)}</select></label>}
        </div>}
      </fieldset>}
      {error && <p className="state-note" role="alert">Comparação indisponível: {error}</p>}
      {!error && loading && series.length === 0 && <p className="loading-state">Carregando séries…</p>}
      {missing.map((item) => <p className="state-note" key={item.canonical_id}>{item.symbol}: sem histórico. {formatReason(item.unavailable_reason)}</p>)}
      {shorter.length > 0 && mode === "INDEX_100" && start !== null && <p className="muted" role="note">Base 100 na primeira data comum, {formatDay(start)}: {shorter.map((line) => line.symbol).join(", ")} não {shorter.length === 1 ? "tem" : "têm"} histórico anterior no plano da fonte.</p>}
      {drawn.length > 0 && <>
        <p className="sr-only">reduced_motion: sem animação de dados financeiros</p>
        <figure className="particle-chart comparison-chart" aria-busy={loading}>
          <svg viewBox="0 0 100 48" role="img" aria-label={`Comparação ${mode} com ${drawn.length} séries`} preserveAspectRatio="none" onPointerMove={moveCursor} onPointerLeave={() => setCursor(null)}>
            <line x1="0" y1="46" x2="100" y2="46" className="chart-axis" />
            {mode === "INDEX_100" && geometry.minValue < 100 && geometry.maxValue > 100 && <line x1="0" x2="100" y1={y(100)} y2={y(100)} className="chart-axis" strokeDasharray="1 1" />}
            {lines.map((line, index) => line.points.length > 1 && <polyline key={line.id} points={line.points.map((point) => `${x(point.time)},${y(point.value)}`).join(" ")} fill="none" vectorEffect="non-scaling-stroke" strokeWidth="2" style={{ stroke: lineStyle(line.id, index).color }} strokeDasharray={lineStyle(line.id, index).dash} />)}
            {cursor !== null && <line x1={x(cursor)} x2={x(cursor)} y1="0" y2="46" className="chart-axis" vectorEffect="non-scaling-stroke" />}
          </svg>
          <figcaption>{mode === "INDEX_100" ? "Todas as séries valem 100 na mesma data inicial." : "Valores nominais; moeda e unidade preservadas na tabela."}{` De ${formatDay(geometry.minTime)} a ${formatDay(geometry.maxTime)}. Eixo vertical de ${AXIS_FORMAT.format(geometry.minValue)} a ${AXIS_FORMAT.format(geometry.maxValue)}; a escala se ajusta às séries exibidas.`}</figcaption>
        </figure>
        <ul className="compare-summary" aria-label="Resultado de cada série no período">
          {lines.map((line, index) => {
            const role = seriesRole(line.id);
            const style = lineStyle(line.id, index);
            const near = cursor === null ? null : nearestPoint(line.points, cursor);
            return <li key={line.id}>
              <svg viewBox="0 0 24 6" aria-hidden="true" className="legend-swatch"><line x1="1" y1="3" x2="23" y2="3" strokeWidth="2" style={{ stroke: style.color }} strokeDasharray={style.dash} /></svg>
              <span><strong>{line.symbol}</strong> <small>{line.currency} · {seriesRoleLabel(role)}{role === "benchmark" ? " — linha tracejada" : ""}</small></span>
              {near
                ? <span>{AXIS_FORMAT.format(near.value)} <small>em {formatDay(near.time)}</small></span>
                : <span className={tone(line.changePercent)}><span aria-hidden="true">{glyph(line.changePercent)}</span>{percentText(line.changePercent)}</span>}
            </li>;
          })}
        </ul>
        {series.some((item) => item.downsampling) && <p className="muted" role="note">Séries reduzidas para exibição pelo método M4 alinhado: as mesmas datas em todas as séries; primeiro, último, mínimo, máximo e gaps de cada uma preservados.</p>}
        <details><summary>Ver os valores em tabela</summary><div className="table-wrap"><table><caption>Fallback tabular sincronizado com as séries exibidas</caption><thead><tr><th scope="col">Data</th>{series.map((item) => <th scope="col" key={item.canonical_id}>{item.symbol} · {item.currency}</th>)}</tr></thead><tbody>{comparisonRows(series).map((row) => <tr key={row.timestamp}><th scope="row">{row.sessionDate}<br /><small>{row.timestamp}</small></th>{row.points.map((current, column) => { const value = current && !current.is_gap ? (mode === "INDEX_100" ? current.index_100 : current.close ?? current.value) : null; return <td key={series[column].canonical_id}>{value == null ? "—" : value}</td>; })}</tr>)}</tbody></table></div></details>
        <p className="comparison-provenance">{series.some((item) => item.is_demo) ? "Fonte sintética DEMO" : `Fontes: ${sources.join(", ")}`}; cada série mantém `DataLevel`, `Freshness`, timestamps e limitações no contrato. Comparar o passado não indica resultado futuro.</p>
      </>}
      <p className="financial-disclaimer">{FINANCIAL_DISCLAIMER}</p>
    </section>
  );
}

// Static page (ADR-005): `?ids=` is read on the client, inside the page's Suspense boundary.
export function CompareFromQuery() {
  const raw = useSearchParams().get("ids") ?? "";
  const ids = [...new Set(raw.split(",").filter((id) => CANONICAL_ID.test(id)))].slice(0, MAX_COMPARED_SERIES);
  return <MultiAssetComparison initialIds={ids.length ? ids : undefined} />;
}
