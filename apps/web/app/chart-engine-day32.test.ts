import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

const root = process.cwd();
const chart = readFileSync(join(root, "src", "components", "particle-chart.tsx"), "utf8");
const manifest = JSON.parse(readFileSync(join(root, "package.json"), "utf8"));

test("INDEX_100 is labeled as rebased price, never as return or TWR (ADR-006, ADR-007)", () => {
  assert.match(chart, /Índice 100 — preço rebaseado a 100 no início do período; não é rentabilidade \(TWR\)/);
});

test("ADR-014 keeps the P0 SVG renderer: no canvas charting library in the web bundle", () => {
  const dependencies = { ...manifest.dependencies, ...manifest.devDependencies };
  for (const name of ["lightweight-charts", "chart.js", "echarts", "highcharts", "three"]) {
    assert.equal(dependencies[name], undefined, `${name} requires a new ADR before entering the bundle`);
  }
  assert.match(chart, /<svg viewBox/);
});
