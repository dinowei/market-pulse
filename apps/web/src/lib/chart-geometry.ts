import type { components } from "../generated/api";
import type { PriceDirection } from "./price-direction";

type PublicHistorySeries = components["schemas"]["PublicHistorySeries"];
type PublicHistoryPoint = components["schemas"]["PublicHistoryPoint"];

// Chart type (ADR-023). A candle is drawn only from contract OHLC: nothing is derived,
// filled or smoothed. When any bar lacks a field, the line stays the only view and the
// reason is shown, so the choice never hides that data is missing.
export type ChartKind = "line" | "candles";

export const CHART_KINDS: readonly { id: ChartKind; label: string }[] = [
  { id: "line", label: "Linha" },
  { id: "candles", label: "Candles" },
];

export type CandleAvailability = { available: true } | { available: false; reason: string };

// Same viewBox as the line chart (0 0 100 48). With volume, the price band ends above
// a separate volume band so the two scales never overlap.
const LEFT = 3;
const PLOT_WIDTH = 94;
const PRICE_TOP = 2;
const AXIS = 46;
const PRICE_BOTTOM_WITH_VOLUME = 34;
export const VOLUME_TOP = 37;
const MIN_BODY = 0.4;

function finite(value: string | number | null | undefined): number | null {
  if (value == null) return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function bars(series: PublicHistorySeries): PublicHistoryPoint[] {
  return series.points.filter((point) => !point.is_gap && Number.isFinite(Date.parse(point.timestamp)));
}

function hasOhlc(point: PublicHistoryPoint): boolean {
  return [point.open, point.high, point.low, point.close].every((value) => finite(value) !== null);
}

export function candleAvailability(series: PublicHistorySeries): CandleAvailability {
  if (series.freshness === "UNAVAILABLE") return { available: false, reason: "Série indisponível: não há barras para desenhar." };
  if (series.mode !== "PRICE") return { available: false, reason: "Candles exigem o modo PRICE: o INDEX_100 rebaseia apenas o fechamento." };
  const valid = bars(series);
  if (valid.length === 0) return { available: false, reason: "A série não tem barras válidas." };
  if (!valid.every(hasOhlc)) return { available: false, reason: "A série não traz abertura, máxima, mínima e fechamento em todas as barras." };
  return { available: true };
}

/** Volume is drawn only when every bar carries it: a partial band would read as zero. */
export function hasCompleteVolume(series: PublicHistorySeries): boolean {
  const valid = bars(series);
  return valid.length > 0 && valid.every((point) => finite(point.volume) !== null);
}

export type Candle = {
  key: string;
  x: number;
  width: number;
  bodyTop: number;
  bodyHeight: number;
  wickTop: number;
  wickBottom: number;
  direction: PriceDirection;
};

export type VolumeBar = { key: string; x: number; width: number; y: number; height: number };

export type CandleLayout = { candles: Candle[]; volume: VolumeBar[]; priceBottom: number };

// Direction compares the bar's own close with its own open. Both are contract decimals
// with far fewer than 15 significant digits, so Number() keeps their order exactly.
function candleDirection(open: number, close: number): PriceDirection {
  if (close > open) return "UP";
  if (close < open) return "DOWN";
  return "FLAT";
}

export function candleLayout(series: PublicHistorySeries): CandleLayout {
  if (!candleAvailability(series).available) return { candles: [], volume: [], priceBottom: AXIS };
  const valid = bars(series);
  const withVolume = hasCompleteVolume(series);
  const priceBottom = withVolume ? PRICE_BOTTOM_WITH_VOLUME : AXIS;
  const lows = valid.map((point) => finite(point.low) as number);
  const highs = valid.map((point) => finite(point.high) as number);
  const minimum = Math.min(...lows);
  const maximum = Math.max(...highs);
  const range = maximum - minimum;
  const scaleY = (value: number) => (range === 0 ? (PRICE_TOP + priceBottom) / 2 : priceBottom - ((value - minimum) / range) * (priceBottom - PRICE_TOP));
  const times = valid.map((point) => Date.parse(point.timestamp));
  const minTime = Math.min(...times);
  const timeRange = Math.max(...times) - minTime;
  const scaleX = (time: number) => (timeRange === 0 ? LEFT + PLOT_WIDTH / 2 : LEFT + ((time - minTime) / timeRange) * PLOT_WIDTH);
  const width = Math.min(5, (PLOT_WIDTH / valid.length) * 0.6);
  const volumes = withVolume ? valid.map((point) => finite(point.volume) as number) : [];
  const maxVolume = Math.max(0, ...volumes);
  const candles: Candle[] = [];
  const volume: VolumeBar[] = [];
  valid.forEach((point, index) => {
    const open = finite(point.open) as number;
    const close = finite(point.close) as number;
    const center = scaleX(times[index]);
    const top = scaleY(Math.max(open, close));
    const key = `${point.timestamp}-${index}`;
    candles.push({
      key,
      x: center - width / 2,
      width,
      bodyTop: top,
      bodyHeight: Math.max(scaleY(Math.min(open, close)) - top, MIN_BODY),
      wickTop: scaleY(finite(point.high) as number),
      wickBottom: scaleY(finite(point.low) as number),
      direction: candleDirection(open, close),
    });
    if (withVolume) {
      const height = maxVolume === 0 ? 0 : (volumes[index] / maxVolume) * (AXIS - VOLUME_TOP);
      volume.push({ key, x: center - width / 2, width, y: AXIS - height, height });
    }
  });
  return { candles, volume, priceBottom };
}
