import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

import { describeMove, extendLine, loadDrawings, saveDrawings, SHORTCUTS, TOOL_SPECS, type Drawing } from "../src/lib/chart-workspace/drawings";
import { barsFromSeries, bollinger, ema, heikinAshi, linearRegression, macd, ohlcAvailable, resample, rsi, sma, type Bar } from "../src/lib/chart-workspace/series";
import { CHART_THEMES, currentChartTheme, withAlpha } from "../src/lib/chart-workspace/theme";
import { historyPoint, historySeries } from "../test-support/chart-fixtures";

const close = (time: string, value: number, extra: Partial<Bar> = {}): Bar => ({ time, open: value, high: value, low: value, close: value, volume: 10, ...extra });

test("bars come only from real closes, oldest first, without gaps or duplicates", () => {
  const series = historySeries([
    historyPoint("2026-09-03", "12"),
    historyPoint("2026-09-01", "10"),
    historyPoint("2026-09-02", null),
    historyPoint("2026-09-04", "13", { is_gap: true }),
    historyPoint("2026-09-01", "10"),
  ]);
  const bars = barsFromSeries(series);
  assert.deepEqual(bars.map((bar) => [bar.time, bar.close]), [["2026-09-01", 10], ["2026-09-03", 12]]);
  assert.equal(ohlcAvailable(bars), true);
  assert.equal(ohlcAvailable([{ ...bars[0], open: null }]), false, "candles need OHLC on every bar");
});

test("weekly bars aggregate the sessions of each week (first open, max high, min low, last close, summed volume)", () => {
  const days = [
    close("2026-09-07", 10, { open: 9, high: 11, low: 8 }), // Monday
    close("2026-09-09", 12, { open: 10, high: 14, low: 9 }),
    close("2026-09-11", 11, { open: 12, high: 12, low: 7 }), // Friday
    close("2026-09-14", 15, { open: 14, high: 16, low: 13 }), // next Monday
  ];
  const weeks = resample(days, "W");
  assert.equal(weeks.length, 2);
  assert.deepEqual(weeks[0], { time: "2026-09-07", open: 9, high: 14, low: 7, close: 11, volume: 30 });
  assert.equal(resample(days, "M").length, 1);
  assert.equal(resample(days, "D"), days);
});

test("moving averages, RSI, MACD and Bollinger match hand-computed values", () => {
  assert.deepEqual(sma([1, 2, 3, 4, 5], 3), [null, null, 2, 3, 4]);
  assert.deepEqual(ema([1, 2, 3, 4, 5], 3), [null, null, 2, 3, 4]);
  assert.equal(rsi([1, 2, 3, 4, 5, 6], 3).at(-1), 100, "only gains: RSI is 100");
  const flat = macd(Array.from({ length: 40 }, () => 10));
  assert.equal(flat.histogram.at(-1), 0);
  const bands = bollinger([5, 5, 5, 5], 4, 2);
  assert.deepEqual([bands.lower.at(-1), bands.middle.at(-1), bands.upper.at(-1)], [5, 5, 5]);
  assert.deepEqual(linearRegression([1, 2, 3]), { slope: 1, intercept: 1, deviation: 0 });
});

test("Heikin Ashi is derived from real OHLC and refuses bars without it", () => {
  const [first] = heikinAshi([close("2026-09-01", 11, { open: 10, high: 12, low: 9 })]);
  assert.deepEqual([first.open, first.high, first.low, first.close], [10.5, 12, 9, 10.5]);
  assert.deepEqual(heikinAshi([close("2026-09-01", 11, { open: null })]), []);
});

test("rays and extended lines reach the edges; moves describe price, percent and bars", () => {
  assert.deepEqual(extendLine({ x: 0, y: 0 }, { x: 1, y: 1 }, 10, 10, false)[1], { x: 10, y: 10 });
  const [start, end] = extendLine({ x: 4, y: 5 }, { x: 6, y: 5 }, 10, 10, true);
  assert.deepEqual([start.x, end.x], [0, 10]);
  assert.equal(describeMove({ time: 0, price: 100 }, { time: 1, price: 110 }, 5, "BRL"), "+10 BRL (+10%) · 5 barras");
  assert.equal(describeMove({ time: 0, price: 100 }, { time: 1, price: 95 }, 1, "USD"), "−5 USD (−5%) · 1 barra");
});

test("every tool declares its anchors, and the documented shortcuts are wired", () => {
  for (const spec of Object.values(TOOL_SPECS)) assert.ok([1, 2, 3].includes(spec.anchors), spec.tool);
  assert.deepEqual(SHORTCUTS, { t: "trend", h: "hline", j: "hray", v: "vline", c: "cross" });
});

test("drawings persist per instrument, the temporary measure is dropped, malformed entries are ignored", () => {
  const store = new Map<string, string>();
  (globalThis as { window?: unknown }).window = { localStorage: { getItem: (key: string) => store.get(key) ?? null, setItem: (key: string, value: string) => store.set(key, value) } };
  try {
    const drawings: Drawing[] = [
      { id: "a", tool: "trend", anchors: [{ time: 1, price: 2 }, { time: 3, price: 4 }] },
      { id: "m", tool: "measure", anchors: [{ time: 1, price: 2 }, { time: 3, price: 4 }] },
    ];
    saveDrawings("equity.test.one", drawings);
    assert.deepEqual(loadDrawings("equity.test.one").map((item) => item.id), ["a"]);
    assert.deepEqual(loadDrawings("equity.test.two"), []);
    store.set("market-pulse.chart.drawings.v1:equity.test.one", JSON.stringify([{ id: "x", tool: "laser", anchors: [] }, { id: "y", tool: "trend", anchors: [{ time: "a" }] }]));
    assert.deepEqual(loadDrawings("equity.test.one"), []);
  } finally {
    delete (globalThis as { window?: unknown }).window;
  }
});

test("the chart theme uses the same hex values as the CSS tokens, and the CVD palette when chosen", () => {
  const css = readFileSync(join(process.cwd(), "app", "globals.css"), "utf8");
  const token = (selector: string, name: string) => new RegExp(`${name}:\\s*(#[0-9a-f]{6})`).exec(css.slice(css.indexOf(`${selector} {`)))?.[1];
  for (const [mode, selector] of [["dark", ":root"], ["light", '[data-theme="light"]']] as const) {
    const theme = CHART_THEMES[mode];
    assert.equal(theme.background, token(selector, "--pa-bg-surface"));
    assert.equal(theme.text, token(selector, "--pa-text-primary"));
    assert.equal(theme.up, token(selector, "--pa-market-up"));
    assert.equal(theme.down, token(selector, "--pa-market-down"));
    assert.equal(theme.accent, token(selector, "--pa-accent"));
  }
  assert.equal(currentChartTheme("dark|cvd").down, token(':root[data-palette="cvd"]', "--pa-market-down"));
  assert.equal(currentChartTheme("light|").up, CHART_THEMES.light.up);
  assert.equal(withAlpha("#112233", 0.5), "#11223380");
});
