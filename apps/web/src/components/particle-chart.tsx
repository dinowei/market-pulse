import type { components } from "../generated/api";

type PublicHistorySeries = components["schemas"]["PublicHistorySeries"];
type PublicHistoryPoint = components["schemas"]["PublicHistoryPoint"];
type SeriesMode = components["schemas"]["SeriesMode"];

function pointValue(point: PublicHistoryPoint, mode: SeriesMode): number | null {
  if (point.is_gap || !Number.isFinite(Date.parse(point.timestamp))) return null;
  const raw = mode === "INDEX_100" ? point.index_100 ?? null : point.close ?? point.value ?? null;
  if (raw == null) return null;
  const numeric = Number(raw);
  return Number.isFinite(numeric) ? numeric : null;
}

export function ParticleChart({ series }: { series: PublicHistorySeries }) {
  const values = series.points.map((point) => pointValue(point, series.mode));
  const validValues = values.filter((value): value is number => value !== null);

  if (validValues.length === 0 || series.freshness === "UNAVAILABLE") {
    return (
      <figure className="particle-chart">
        <svg viewBox="0 0 100 48" role="img" aria-label={`UNAVAILABLE ${series.symbol}`} preserveAspectRatio="none">
          <line x1="0" y1="46" x2="100" y2="46" className="chart-axis" />
        </svg>
      </figure>
    );
  }

  const minimum = Math.min(...validValues);
  const maximum = Math.max(...validValues);
  const range = maximum - minimum || 1;

  const timestamps = series.points.map(p => Date.parse(p.timestamp));
  const minTime = Math.min(...timestamps.filter(Number.isFinite));
  const maxTime = Math.max(...timestamps.filter(Number.isFinite));
  const timeRange = maxTime - minTime || 1;

  const scaleX = (index: number) => {
    if (minTime === maxTime) return 50;
    return ((timestamps[index] - minTime) / timeRange) * 100;
  };
  const scaleY = (value: number) => {
    if (minimum === maximum) return 25;
    return 46 - ((value - minimum) / range) * 42;
  };

  let pathD = "";
  for (let i = 0; i < values.length; i++) {
    const val = values[i];
    if (val !== null) {
      const x = scaleX(i);
      const y = scaleY(val);
      if (i === 0 || values[i - 1] === null) {
        pathD += `M ${x} ${y} `;
      } else {
        pathD += `L ${x} ${y} `;
      }
    }
  }
  pathD = pathD.trim();

  const label = `${series.symbol} ${series.mode} ${series.period}; ${series.points.length} pontos; ${series.data_level} ${series.freshness}`;

  return (
    <figure className="particle-chart">
      <svg viewBox="0 0 100 48" role="img" aria-label={label} preserveAspectRatio="none">
        <line x1="0" y1="46" x2="100" y2="46" className="chart-axis" />
        {pathD && <path d={pathD} className="chart-line" fill="none" />}
        {values.map((value, index) => value === null ? null : <circle key={`${series.points[index].timestamp}-${index}`} cx={scaleX(index)} cy={scaleY(value)} r="1.1" className="chart-point" />)}
      </svg>
      <figcaption>{series.mode === "INDEX_100" ? "Índice 100" : "Preço nominal"} — {series.data_level}; valores contratuais preservados</figcaption>
    </figure>
  );
}
