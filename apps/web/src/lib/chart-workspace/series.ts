// Pure helpers for the chart workspace (ADR-028). Every number shown comes from the API's
// real bars; indicators and Heikin Ashi are labelled as derived, never as traded prices.
import type { components } from "../../generated/api";

type PublicHistorySeries = components["schemas"]["PublicHistorySeries"];

export type Bar = {
  /** Session date, YYYY-MM-DD (business day for the chart). */
  time: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number;
  volume: number | null;
};

export type Interval = "D" | "W" | "M";

function numeric(value: string | null | undefined): number | null {
  if (value == null) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

/** Bars with a real close, oldest first; gaps and missing closes are left out, not filled. */
export function barsFromSeries(series: PublicHistorySeries): Bar[] {
  const bars: Bar[] = [];
  for (const point of series.points) {
    const close = numeric(point.close ?? point.value);
    if (point.is_gap || close === null) continue;
    bars.push({ time: point.session_date, open: numeric(point.open), high: numeric(point.high), low: numeric(point.low), close, volume: numeric(point.volume) });
  }
  bars.sort((a, b) => a.time.localeCompare(b.time));
  return bars.filter((bar, index) => index === 0 || bar.time !== bars[index - 1].time);
}

export function hasOhlc(bar: Bar): bar is Bar & { open: number; high: number; low: number } {
  return bar.open !== null && bar.high !== null && bar.low !== null;
}

/** Candle-type charts need full OHLC on every bar; otherwise only line types are offered. */
export function ohlcAvailable(bars: Bar[]): boolean {
  return bars.length > 0 && bars.every(hasOhlc);
}

function bucketKey(time: string, interval: Interval): string {
  if (interval === "M") return time.slice(0, 7);
  const date = new Date(`${time}T00:00:00Z`);
  const weekday = (date.getUTCDay() + 6) % 7; // Monday = 0
  date.setUTCDate(date.getUTCDate() - weekday);
  return date.toISOString().slice(0, 10);
}

/** Weekly or monthly bars aggregated from the daily ones (first open, max high, min low, last close). */
export function resample(bars: Bar[], interval: Interval): Bar[] {
  if (interval === "D") return bars;
  const out: Bar[] = [];
  let key = "";
  for (const bar of bars) {
    const next = bucketKey(bar.time, interval);
    const current = out[out.length - 1];
    if (!current || next !== key) {
      out.push({ ...bar });
      key = next;
      continue;
    }
    current.high = current.high !== null && bar.high !== null ? Math.max(current.high, bar.high) : null;
    current.low = current.low !== null && bar.low !== null ? Math.min(current.low, bar.low) : null;
    current.open = current.open !== null && bar.open !== null ? current.open : null;
    current.close = bar.close;
    current.volume = current.volume !== null && bar.volume !== null ? current.volume + bar.volume : null;
  }
  return out;
}

export function sma(values: number[], length: number): (number | null)[] {
  const out: (number | null)[] = [];
  let sum = 0;
  values.forEach((value, index) => {
    sum += value;
    if (index >= length) sum -= values[index - length];
    out.push(index >= length - 1 ? sum / length : null);
  });
  return out;
}

export function ema(values: number[], length: number): (number | null)[] {
  const out: (number | null)[] = [];
  const k = 2 / (length + 1);
  let previous: number | null = null;
  values.forEach((value, index) => {
    if (index < length - 1) return out.push(null);
    if (previous === null) previous = values.slice(0, length).reduce((a, b) => a + b, 0) / length;
    else previous = value * k + previous * (1 - k);
    out.push(previous);
  });
  return out;
}

export function bollinger(values: number[], length = 20, width = 2) {
  const middle = sma(values, length);
  const upper: (number | null)[] = [];
  const lower: (number | null)[] = [];
  middle.forEach((mean, index) => {
    if (mean === null) {
      upper.push(null);
      lower.push(null);
      return;
    }
    const window = values.slice(index - length + 1, index + 1);
    const deviation = Math.sqrt(window.reduce((total, value) => total + (value - mean) ** 2, 0) / length);
    upper.push(mean + width * deviation);
    lower.push(mean - width * deviation);
  });
  return { middle, upper, lower };
}

/** Wilder's RSI. */
export function rsi(values: number[], length = 14): (number | null)[] {
  const out: (number | null)[] = values.map(() => null);
  if (values.length <= length) return out;
  let gain = 0;
  let loss = 0;
  for (let index = 1; index <= length; index++) {
    const change = values[index] - values[index - 1];
    gain += Math.max(change, 0);
    loss += Math.max(-change, 0);
  }
  gain /= length;
  loss /= length;
  out[length] = loss === 0 ? 100 : 100 - 100 / (1 + gain / loss);
  for (let index = length + 1; index < values.length; index++) {
    const change = values[index] - values[index - 1];
    gain = (gain * (length - 1) + Math.max(change, 0)) / length;
    loss = (loss * (length - 1) + Math.max(-change, 0)) / length;
    out[index] = loss === 0 ? 100 : 100 - 100 / (1 + gain / loss);
  }
  return out;
}

export function macd(values: number[], fast = 12, slow = 26, signalLength = 9) {
  const fastLine = ema(values, fast);
  const slowLine = ema(values, slow);
  const line = values.map((_, index) => (fastLine[index] !== null && slowLine[index] !== null ? (fastLine[index] as number) - (slowLine[index] as number) : null));
  const defined = line.filter((value): value is number => value !== null);
  const offset = line.length - defined.length;
  const signalDefined = ema(defined, signalLength);
  const signal = line.map((_, index) => (index < offset ? null : signalDefined[index - offset]));
  const histogram = line.map((value, index) => (value !== null && signal[index] !== null ? value - (signal[index] as number) : null));
  return { line, signal, histogram };
}

/** Heikin Ashi bars computed from real OHLC; a derived view, labelled as such on screen. */
export function heikinAshi(bars: Bar[]): Bar[] {
  const out: Bar[] = [];
  for (const bar of bars) {
    if (!hasOhlc(bar)) return [];
    const close = (bar.open + bar.high + bar.low + bar.close) / 4;
    const previous = out[out.length - 1];
    const open = previous && previous.open !== null ? (previous.open + previous.close) / 2 : (bar.open + bar.close) / 2;
    out.push({ time: bar.time, open, high: Math.max(bar.high, open, close), low: Math.min(bar.low, open, close), close, volume: bar.volume });
  }
  return out;
}

/** Least-squares line through (index, close); used by the regression drawing tool. */
export function linearRegression(values: number[]): { slope: number; intercept: number; deviation: number } | null {
  const n = values.length;
  if (n < 2) return null;
  const meanX = (n - 1) / 2;
  const meanY = values.reduce((a, b) => a + b, 0) / n;
  let numerator = 0;
  let denominator = 0;
  values.forEach((value, index) => {
    numerator += (index - meanX) * (value - meanY);
    denominator += (index - meanX) ** 2;
  });
  const slope = numerator / denominator;
  const intercept = meanY - slope * meanX;
  const deviation = Math.sqrt(values.reduce((total, value, index) => total + (value - (intercept + slope * index)) ** 2, 0) / n);
  return { slope, intercept, deviation };
}

export function epochSeconds(time: string): number {
  return Date.parse(`${time}T00:00:00Z`) / 1000;
}

export function dateFromEpoch(seconds: number): string {
  return new Date(seconds * 1000).toISOString().slice(0, 10);
}
