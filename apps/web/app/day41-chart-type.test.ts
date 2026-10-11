import assert from "node:assert/strict";
import test from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { ChartTypeToggle } from "../src/components/chart-type-toggle";
import { AccessibleDataTable } from "../src/components/market-data";
import { ParticleChart } from "../src/components/particle-chart";
import { candleAvailability, candleLayout, hasCompleteVolume } from "../src/lib/chart-geometry";
import { elements, historyPoint, historySeries, tableRows } from "../test-support/chart-fixtures";

test("candles need PRICE mode and complete OHLC; otherwise the reason is given", () => {
  const ohlc = (day: string, open: string, high: string, low: string, close: string, volume: string | null = "1000") => historyPoint(day, close, { open, high, low, volume });
  const series = historySeries([ohlc("2026-09-01", "10", "12", "9", "11"), ohlc("2026-09-02", "11", "11.5", "9.5", "10"), ohlc("2026-09-03", "10", "10.5", "9.8", "10", "0")]);
  assert.deepEqual(candleAvailability(series), { available: true });
  assert.equal(candleAvailability({ ...series, mode: "INDEX_100" }).available, false);
  assert.equal(candleAvailability({ ...series, freshness: "UNAVAILABLE" }).available, false);
  const partial = historySeries([ohlc("2026-09-01", "10", "12", "9", "11"), historyPoint("2026-09-02", "10", { open: null })]);
  assert.match((candleAvailability(partial) as { reason: string }).reason, /abertura, máxima, mínima e fechamento/);
  const layout = candleLayout(series);
  assert.deepEqual(layout.candles.map((candle) => candle.direction), ["UP", "DOWN", "FLAT"]);
  for (const candle of layout.candles) assert.ok(candle.wickTop <= candle.bodyTop && candle.bodyTop + candle.bodyHeight <= candle.wickBottom + 0.4 + 1e-9);
  assert.equal(layout.volume.length, 3);
  assert.ok(layout.priceBottom < 37, "volume has its own band");
  assert.equal(layout.volume[2].height, 0, "zero volume is drawn as zero");
  const noVolume = historySeries([ohlc("2026-09-01", "10", "12", "9", "11", null), ohlc("2026-09-02", "11", "12", "10", "12")]);
  assert.equal(hasCompleteVolume(noVolume), false, "partial volume is not drawn");
  assert.equal(candleLayout(noVolume).volume.length, 0);
});

test("ParticleChart draws candles only when allowed and keeps the line otherwise", () => {
  const series = historySeries([historyPoint("2026-09-01", "11", { open: "10", high: "12", low: "9", volume: "5" }), historyPoint("2026-09-02", "9", { open: "10", high: "10.5", low: "8", volume: "7" })]);
  const candles = renderToStaticMarkup(createElement(ParticleChart, { series, kind: "candles" }));
  assert.equal(elements(candles, "circle").length, 0);
  assert.ok(elements(candles, "rect").length >= 2);
  assert.match(elements(candles, "svg")[0]["aria-label"], /candles OHLC 1M; 2 barras com volume/);
  const indexed = { ...series, mode: "INDEX_100" as const, points: series.points.map((point, index) => ({ ...point, index_100: index === 0 ? "100" : "81.82" })) };
  const fallback = renderToStaticMarkup(createElement(ParticleChart, { series: indexed, kind: "candles" }));
  assert.equal(elements(fallback, "path").length, 1, "INDEX_100 keeps the line");
  const table = renderToStaticMarkup(createElement(AccessibleDataTable, { points: series.points, ohlc: true }));
  assert.deepEqual(tableRows(table)[0], ["2026-09-01", "10", "12", "9", "11", "5", "—", "Não"]);
  const toggle = renderToStaticMarkup(createElement(ChartTypeToggle, { value: "candles", onChange: () => undefined, availability: { available: false, reason: "Candles exigem o modo PRICE." } }));
  const buttons = elements(toggle, "button");
  assert.equal(buttons[0]["aria-pressed"], "true", "the line stays selected when candles are unavailable");
  assert.ok("disabled" in buttons[1]);
  assert.match(toggle, /Candles exigem o modo PRICE\./);
});
