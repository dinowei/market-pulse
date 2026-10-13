import type { CSSProperties } from "react";
import type { components } from "../generated/api";
import { motionClass } from "../lib/atlas-motion";
import { candleLayout, VOLUME_TOP, type CandleLayout, type ChartKind } from "../lib/chart-geometry";

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

const MODE_NOTE = {
  INDEX_100: "Índice 100 — preço rebaseado a 100 no início do período; não é rentabilidade (TWR)",
  PRICE: "Preço nominal",
} as const;

const CANDLE_NOTE = "Candles OHLC: corpo vazado = fechamento acima da abertura (alta); cheio = abaixo (queda); traço = igual (estável).";

// The key remounts the drawing on every transition (asset, period, mode, type, refresh),
// so the one-shot motion replays only then (directive §18).
function drawingKey(series: PublicHistorySeries, kind: ChartKind): string {
  return `${series.canonical_id}|${series.period}|${series.mode}|${kind}|${series.timestamp_collected}`;
}

// Reference grid (presentation only): quarter lines of the plot box, with no value label,
// so it never states a price the contract did not send.
function ChartGrid({ top, bottom }: { top: number; bottom: number }) {
  return <g className="chart-grid">{[1, 2, 3].map((step) => {
    const y = top + ((bottom - top) * step) / 4;
    return <line key={step} x1="0" y1={y} x2="100" y2={y} vectorEffect="non-scaling-stroke" />;
  })}</g>;
}

function CandleChart({ series, layout }: { series: PublicHistorySeries; layout: CandleLayout }) {
  const { candles, volume, priceBottom } = layout;
  const label = `${series.symbol} candles OHLC ${series.period}; ${candles.length} barras${volume.length ? " com volume" : ""}; ${series.data_level} ${series.freshness}`;
  return (
    <figure className={`particle-chart${motionClass()}`}>
      <svg key={drawingKey(series, "candles")} viewBox="0 0 100 48" role="img" aria-label={label} preserveAspectRatio="none">
        <ChartGrid top={2} bottom={priceBottom} />
        <line x1="0" y1="46" x2="100" y2="46" className="chart-axis" />
        {volume.length > 0 && <line x1="0" y1={(priceBottom + VOLUME_TOP) / 2} x2="100" y2={(priceBottom + VOLUME_TOP) / 2} className="chart-axis chart-axis-soft" />}
        {volume.map((bar, index) => <rect key={`v-${bar.key}`} x={bar.x} y={bar.y} width={bar.width} height={bar.height} className="chart-volume" style={{ "--i": index } as CSSProperties} />)}
        {candles.map((candle, index) => {
          const center = candle.x + candle.width / 2;
          const tone = candle.direction.toLowerCase();
          return <g key={candle.key} className={`chart-candle chart-candle-${tone}`} style={{ "--i": index } as CSSProperties}>
            <line x1={center} y1={candle.wickTop} x2={center} y2={candle.wickBottom} className="chart-wick" vectorEffect="non-scaling-stroke" />
            {candle.direction === "FLAT"
              ? <line x1={candle.x} y1={candle.bodyTop} x2={candle.x + candle.width} y2={candle.bodyTop} className="chart-body" vectorEffect="non-scaling-stroke" />
              : <rect x={candle.x} y={candle.bodyTop} width={candle.width} height={candle.bodyHeight} className="chart-body" vectorEffect="non-scaling-stroke" />}
          </g>;
        })}
      </svg>
      <figcaption>{CANDLE_NOTE}{volume.length > 0 && " Barras inferiores: volume de cada barra, em escala própria."} — {series.data_level}; valores contratuais preservados</figcaption>
    </figure>
  );
}

export function ParticleChart({ series, kind = "line" }: { series: PublicHistorySeries; kind?: ChartKind }) {
  const candles = kind === "candles" ? candleLayout(series) : null;
  if (candles && candles.candles.length > 0) return <CandleChart series={series} layout={candles} />;
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
    <figure className={`particle-chart${motionClass()}`}>
      <svg key={drawingKey(series, "line")} viewBox="0 0 100 48" role="img" aria-label={label} preserveAspectRatio="none">
        <ChartGrid top={4} bottom={46} />
        <line x1="0" y1="46" x2="100" y2="46" className="chart-axis" />
        {pathD && <path d={pathD} className="chart-line chart-draw" fill="none" pathLength={1} />}
        {values.map((value, index) => value === null ? null : <circle key={`${series.points[index].timestamp}-${index}`} cx={scaleX(index)} cy={scaleY(value)} r="1.1" className="chart-point" style={{ "--d": (index / Math.max(values.length - 1, 1)).toFixed(3) } as CSSProperties} />)}
      </svg>
      <figcaption>{MODE_NOTE[series.mode]} — {series.data_level}; valores contratuais preservados</figcaption>
    </figure>
  );
}
