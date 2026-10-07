// Day 32 measurement (ADR-014): server render cost and SVG weight of the P0 ParticleChart
// for growing series sizes. Synthetic points only; no provider, no network.
// Run from apps/web: node --import ./test-support/register-typescript.mjs scripts/chart-benchmark.tsx
import { performance } from "node:perf_hooks";
import { renderToStaticMarkup } from "react-dom/server";
import type { components } from "../src/generated/api";
import { ParticleChart } from "../src/components/particle-chart";

type PublicHistorySeries = components["schemas"]["PublicHistorySeries"];

function series(count: number): PublicHistorySeries {
  const start = Date.UTC(2016, 0, 4, 20);
  const points = Array.from({ length: count }, (_, index) => {
    const value = (50 + ((index * 37) % 23) / 10).toFixed(2);
    const timestamp = new Date(start + index * 86_400_000).toISOString();
    return { timestamp, session_date: timestamp.slice(0, 10), close: value, value, index_100: null, is_gap: false };
  });
  return {
    canonical_id: "equity.br.b3.petr4", symbol: "PETR4", period: "MAX", mode: "PRICE", adjustment_type: "UNADJUSTED",
    currency: "BRL", data_level: "DEMO", freshness: "STALE", provider: "demo", dataset: "demo-history",
    timestamp_official: new Date(start).toISOString(), timestamp_collected: new Date(start).toISOString(), latency_ms: 0,
    limitations: [], points, tabular_fallback: true, accessibility: { reduced_motion: true, smoothed: false }, request_id: "bench",
  } as PublicHistorySeries;
}

const sizes = [440, 500, 1250, 2600, 10000];
const runs = 15;
const rows = [];
for (const size of sizes) {
  const data = series(size);
  renderToStaticMarkup(<ParticleChart series={data} />); // warm-up
  const timings: number[] = [];
  let bytes = 0;
  let elements = 0;
  for (let run = 0; run < runs; run += 1) {
    const started = performance.now();
    const markup = renderToStaticMarkup(<ParticleChart series={data} />);
    timings.push(performance.now() - started);
    bytes = Buffer.byteLength(markup);
    elements = (markup.match(/<(circle|path|line)\b/g) ?? []).length;
  }
  timings.sort((a, b) => a - b);
  rows.push({ points: size, svg_elements: elements, markup_kb: +(bytes / 1024).toFixed(1), median_ms: +timings[Math.floor(runs / 2)].toFixed(2), p95_ms: +timings[Math.floor(runs * 0.95) - 1].toFixed(2) });
}
console.log(JSON.stringify({ node: process.version, runs, rows }, null, 2));
