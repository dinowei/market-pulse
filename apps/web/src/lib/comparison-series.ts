// Comparison over one shared window: sources have different history depths (brapi caps B3 at
// three months), so a base of 100 only compares like with like from the first date all series
// share. Rebasing here keeps each series' own values and never fills a gap.
import type { components } from "../generated/api";

type Series = components["schemas"]["PublicHistorySeries"];
export type SeriesMode = components["schemas"]["SeriesMode"];

export type ChartPoint = { time: number; value: number };
export type ChartLine = { id: string; symbol: string; currency: string; points: ChartPoint[]; changePercent: number | null; firstDate: string | null };

function raw(point: Series["points"][number], mode: SeriesMode): number | null {
  if (point.is_gap) return null;
  const value = mode === "INDEX_100" ? point.index_100 : point.close ?? point.value;
  if (value == null) return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function usable(series: Series, mode: SeriesMode): ChartPoint[] {
  return series.points.flatMap((point) => {
    const value = raw(point, mode);
    const time = Date.parse(point.timestamp);
    return value === null || !Number.isFinite(time) ? [] : [{ time, value }];
  });
}

/** The latest first date among the series with data: where every line can start together. */
export function commonStart(series: readonly Series[], mode: SeriesMode): number | null {
  const firsts = series.map((item) => usable(item, mode)[0]?.time).filter((time): time is number => time !== undefined);
  return firsts.length > 0 ? Math.max(...firsts) : null;
}

export function comparisonLines(series: readonly Series[], mode: SeriesMode): ChartLine[] {
  const start = commonStart(series, mode);
  return series.map((item) => {
    const all = usable(item, mode);
    const inWindow = mode === "INDEX_100" && start !== null ? all.filter((point) => point.time >= start) : all;
    const base = inWindow[0]?.value;
    const points = mode === "INDEX_100" && base ? inWindow.map((point) => ({ time: point.time, value: (point.value / base) * 100 })) : inWindow;
    const first = points[0]?.value;
    const last = points[points.length - 1]?.value;
    return {
      id: item.canonical_id,
      symbol: item.symbol,
      currency: item.currency,
      points,
      changePercent: first && last && points.length > 1 ? (last / first - 1) * 100 : null,
      firstDate: all[0] ? new Date(all[0].time).toISOString().slice(0, 10) : null,
    };
  });
}

/** The point of a line closest in time to the cursor. */
export function nearestPoint(points: readonly ChartPoint[], time: number): ChartPoint | null {
  let best: ChartPoint | null = null;
  for (const point of points) if (!best || Math.abs(point.time - time) < Math.abs(best.time - time)) best = point;
  return best;
}
