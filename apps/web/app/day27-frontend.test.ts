import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

test("portfolio UI consumes Day 27 generated contracts and preserves Decimal strings", async () => {
  const source = await readFile(new URL("../src/components/portfolios.tsx", import.meta.url), "utf8");
  const chart = await readFile(new URL("../src/components/equity-chart.tsx", import.meta.url), "utf8");
  const generated = await readFile(new URL("../src/generated/api.ts", import.meta.url), "utf8");
  assert.match(generated, /PortfolioIncomeResponse/);
  assert.match(generated, /PortfolioEventMarkersResponse/);
  // Since H-21 income and markers arrive in the single /overview response.
  assert.match(source, /\/overview/);
  assert.match(source, /setIncome\(overview\.income\)/);
  assert.match(source, /setMarkers\(overview\.event_markers\)/);
  assert.match(source, /Proventos e eventos corporativos/);
  assert.match(source, /Fallback tabular dos marcadores/);
  assert.match(source, /markers=\{markers\?\.items \?\? \[\]\}/);
  assert.doesNotMatch(source, /parseFloat|Number\(|toFixed\(/);
  assert.match(chart, /PortfolioEventMarkerResponse/);
  assert.match(chart, /aria-label/);
  const reporter = await readFile(new URL("../src/components/web-vitals-reporter.tsx", import.meta.url), "utf8");
  assert.match(reporter, /LCP|INP|CLS/);
  assert.match(reporter, /sendBeacon|keepalive/);
  assert.doesNotMatch(reporter, /cookie|email|token|session/);
});
