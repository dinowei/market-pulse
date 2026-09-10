import assert from "node:assert/strict";
import test from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { ParticleChart } from "../src/components/particle-chart";
import { AccessibleDataTable, ProvenancePanel, TerminalShell } from "../src/components/market-data";
import { coordinates, elements, historyPoint, historySeries, tableRows } from "../test-support/chart-fixtures";


test("ParticleChart preserves a missing value as a break in the financial line", () => {
  const series = historySeries([historyPoint("2026-09-01", "100"), historyPoint("2026-09-02", null), historyPoint("2026-09-03", "200")]);
  const markup = renderToStaticMarkup(createElement(ParticleChart, { series }));
  assert.deepEqual(coordinates(markup), [[0, 46], [100, 4]]);
  assert.equal(elements(markup, "path")[0]?.d, "M 0 46 M 100 4");
});

test("ParticleChart treats is_gap as a break even when the payload retains values", () => {
  const series = historySeries([historyPoint("2026-09-01", "100"), historyPoint("2026-09-02", "999", { is_gap: true }), historyPoint("2026-09-03", "200")]);
  const markup = renderToStaticMarkup(createElement(ParticleChart, { series }));
  assert.deepEqual(coordinates(markup), [[0, 46], [100, 4]]);
  assert.equal(elements(markup, "path")[0]?.d, "M 0 46 M 100 4");
});

test("ParticleChart plots real timestamps and prices proportionally", () => {
  const series = historySeries([historyPoint("2026-09-01", "300"), historyPoint("2026-09-02", "200"), historyPoint("2026-09-05", "100")]);
  const markup = renderToStaticMarkup(createElement(ParticleChart, { series }));
  assert.deepEqual(coordinates(markup), [[0, 4], [25, 25], [100, 46]]);
  assert.equal(elements(markup, "path")[0]?.d, "M 0 4 L 25 25 L 100 46");
});

test("INDEX_100 uses contract values while its table retains actual closing prices", () => {
  const series = historySeries([historyPoint("2026-09-01", "150.00", { index_100: "100", value: "100" }), historyPoint("2026-09-02", "220.00", { index_100: "146.67", value: "146.67" })], { mode: "INDEX_100", freshness: "STALE" });
  const markup = renderToStaticMarkup(createElement(ParticleChart, { series }));
  assert.deepEqual(coordinates(markup), [[0, 46], [100, 4]]);
  assert.equal(elements(markup, "path").length, 1);
  assert.match(elements(markup, "svg")[0]["aria-label"], /DEMO INDEX_100 1M.*DEMO STALE/);
  const table = renderToStaticMarkup(createElement(AccessibleDataTable, { points: series.points }));
  assert.deepEqual(tableRows(table), [["2026-09-01", "150.00", "100", "Não"], ["2026-09-02", "220.00", "146.67", "Não"]]);
  const provenance = renderToStaticMarkup(createElement(ProvenancePanel, { data: series }));
  for (const value of [series.provider, series.dataset, series.timestamp_collected, "2026-09-01T00:00:00Z", "DEMO", "STALE", series.limitations[0]]) assert.ok(provenance.includes(value));
});

test("a missing normalized point never falls back to a nominal close", () => {
  const series = historySeries([historyPoint("2026-09-01", "150", { index_100: "100", value: "150" }), historyPoint("2026-09-02", "170", { index_100: null, value: "170" }), historyPoint("2026-09-03", "180", { index_100: "120", value: "180" })], { mode: "INDEX_100" });
  const markup = renderToStaticMarkup(createElement(ParticleChart, { series }));
  assert.equal(elements(markup, "path")[0]?.d, "M 0 46 M 100 4");
  assert.deepEqual(tableRows(renderToStaticMarkup(createElement(AccessibleDataTable, { points: series.points })))[1], ["2026-09-02", "170", "—", "Não"]);
});

test("empty and unavailable series do not draw financial values", () => {
  for (const points of [[], [historyPoint("2026-09-01", null)], [historyPoint("2026-09-01", "100")]]) {
    const markup = renderToStaticMarkup(createElement(ParticleChart, { series: historySeries(points, { freshness: "UNAVAILABLE" }) }));
    assert.deepEqual(coordinates(markup), []);
    assert.equal(elements(markup, "path").length, 0);
    assert.match(elements(markup, "svg")[0]["aria-label"], /UNAVAILABLE/);
  }
});

test("constant prices stay horizontal, zero is valid, and a single point is centered", () => {
  const flat = historySeries([historyPoint("2026-09-01", "0"), historyPoint("2026-09-03", "0")]);
  assert.deepEqual(coordinates(renderToStaticMarkup(createElement(ParticleChart, { series: flat }))), [[0, 25], [100, 25]]);
  const single = historySeries([historyPoint("2026-09-01", "150")]);
  assert.deepEqual(coordinates(renderToStaticMarkup(createElement(ParticleChart, { series: single }))), [[50, 25]]);
});

// Canonical selection and contract integration are exercised by e2e/demo.spec.ts.
test("terminal navigation reaches the existing private routes and logout control", () => {
  const markup = renderToStaticMarkup(createElement(TerminalShell));
  const links = elements(markup, "a").map((link) => link.href);
  assert.ok(links.includes("/watchlists"));
  assert.ok(links.includes("/portfolios"));
  assert.ok(links.includes("/login"));
  assert.ok(elements(markup, "button").some((button) => button["aria-label"] === "Sair"));
});
