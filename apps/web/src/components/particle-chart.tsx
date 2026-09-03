import type { components } from "../generated/api";

type PublicHistorySeries = components["schemas"]["PublicHistorySeries"];
type PublicHistoryPoint = components["schemas"]["PublicHistoryPoint"];
type SeriesMode = components["schemas"]["SeriesMode"];

function pointValue(point: PublicHistoryPoint, mode: SeriesMode): string | null {
  return mode === "INDEX_100" ? point.index_100 ?? point.value ?? null : point.close ?? point.value ?? null;
}

function toDrawingValue(raw: string | null): number | null {
  if (raw == null) return null;
  const numeric = Number(raw);
  return Number.isFinite(numeric) ? numeric : null;
}

export function ParticleChart({ series }: { series: PublicHistorySeries }) {
  const values = series.points.map((point) => toDrawingValue(pointValue(point, series.mode)));
  const validValues = values.filter((value): value is number => value !== null);
  const minimum = validValues.length > 0 ? Math.min(...validValues) : 0;
  const maximum = validValues.length > 0 ? Math.max(...validValues) : 1;
  const range = maximum - minimum || 1;
  const plotted = values.map((value, index) => value === null ? null : `${(index / Math.max(values.length - 1, 1)) * 100},${46 - ((value - minimum) / range) * 42}`);
  const line = plotted.filter((point): point is string => point !== null).join(" ");
  const label = `${series.symbol} ${series.mode} ${series.period}; ${series.points.length} pontos; ${series.data_level} ${series.freshness}`;

  return (
    <figure className="particle-chart">
      <svg viewBox="0 0 100 48" role="img" aria-label={label} preserveAspectRatio="none">
        <line x1="0" y1="46" x2="100" y2="46" className="chart-axis" />
        {line && <polyline points={line} className="chart-line" fill="none" />}
        {values.map((value, index) => value === null ? null : <circle key={`${series.points[index].timestamp}-${index}`} cx={(index / Math.max(values.length - 1, 1)) * 100} cy={46 - ((value - minimum) / range) * 42} r="1.1" className="chart-point" />)}
      </svg>
      <figcaption>{series.mode === "INDEX_100" ? "Índice 100" : "Preço real"} · linha neutra com valores contratuais preservados</figcaption>
    </figure>
  );
}
