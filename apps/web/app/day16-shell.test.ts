import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

const appRoot = join(process.cwd(), "app");
const componentSource = () => readFileSync(join(process.cwd(), "src", "components", "market-data.tsx"), "utf8");
const cssSource = () => readFileSync(join(appRoot, "globals.css"), "utf8");
const pageSource = () => readFileSync(join(appRoot, "page.tsx"), "utf8");

test("Particle Atlas shell exposes the semantic terminal regions", () => {
  const source = `${pageSource()}\n${componentSource()}`;
  for (const marker of ["Market Pulse", "Dashboard", "Morning Call", "search", "main", "aside", "footer"]) {
    assert.match(source, new RegExp(marker, "i"));
  }
});

test("Particle Atlas tokens cover both themes and financial state semantics", () => {
  const css = cssSource();
  for (const token of ["--pa-bg-canvas", "--pa-bg-surface", "--pa-text-primary", "--pa-market-up", "--pa-market-down", "--pa-market-flat", "--pa-state-stale", "--pa-state-unavailable", "--pa-state-demo"]) {
    assert.match(css, new RegExp(token));
  }
  assert.match(css, /data-theme="light"|\[data-theme='light'\]|:root\.light/);
  assert.match(css, /prefers-reduced-motion/);
});

test("state, provenance, period, mode and fallback contracts are represented", () => {
  const source = componentSource();
  for (const marker of ["DataStateBadge", "ProvenancePanel", "MarketStatusBar", "AssetContextPanel", "PeriodSelector", "SeriesModeToggle", "AccessibleDataTable", "TerminalShell", "DEMO", "UNAVAILABLE", "DataLevel", "Freshness", "INDEX_100", "1D", "MAX", "Fallback tabular"]) {
    assert.match(source, new RegExp(marker));
  }
  assert.match(cssSource(), /data-badge-stale/);
  assert.match(source, /generated\/api/);
  assert.doesNotMatch(source, /interface\s+(Quote|Asset|HistoryResponse)/);
});
