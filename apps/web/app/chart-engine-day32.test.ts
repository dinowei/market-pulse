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

test("ADR-028 (superseding ADR-014 for the workspace): one pinned canvas library, loaded on demand, with attribution and a table", () => {
  const dependencies = { ...manifest.dependencies, ...manifest.devDependencies };
  assert.equal(dependencies["lightweight-charts"], "5.2.1", "exact version, checked on npm (Apache-2.0)");
  for (const name of ["chart.js", "echarts", "highcharts", "three"]) {
    assert.equal(dependencies[name], undefined, `${name} requires a new ADR before entering the bundle`);
  }
  const workspace = readFileSync(join(root, "src", "components", "chart-workspace.tsx"), "utf8");
  assert.match(workspace, /import\("lightweight-charts"\)/, "the library is fetched after the page, not in the first load");
  assert.doesNotMatch(workspace.replace(/import type [^;]+;/g, ""), /from "lightweight-charts"/, "only types are imported statically");
  assert.match(workspace, /attributionLogo: true/, "TradingView attribution stays on (Apache-2.0 NOTICE)");
  assert.match(workspace, /<AccessibleDataTable /, "the same series is always available as a table");
  for (const file of ["market-data.tsx", "asset-detail.tsx"]) {
    const page = readFileSync(join(root, "src", "components", file), "utf8");
    assert.match(page, /dynamic\(\(\) => import\("\.\/chart-workspace"\)[\s\S]{0,120}ssr: false/, file);
  }
  assert.match(chart, /<svg viewBox/, "the SVG renderer remains for comparison and static views");
});
