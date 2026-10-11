import assert from "node:assert/strict";
import test from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { MarketPulseField } from "../src/components/market-pulse-field";
import { MarketsHub } from "../src/components/markets-hub";
import {
  chunk, compareHref, coverageLabel, displayValue, formatUtc, MARKET_TABS, parseMarketTab, pulseLayout, pulseSentence, pulseSummary,
  rowDirection, rowFromBenchmark, rowFromInstrument, tabForBenchmark, tabForInstrument, type MarketRow,
} from "../src/lib/markets";
import { elements } from "../test-support/chart-fixtures";

function instrument(canonical_id: string, instrument_type: string, country: string | null) {
  return { id: canonical_id, canonical_id, symbol: canonical_id.split(".").at(-1)!.toUpperCase(), display_symbol: canonical_id.split(".").at(-1)!.toUpperCase(), name: canonical_id, instrument_type, currency: "BRL", aliases: [], catalog_status: "CANDIDATE", coverage_tier: "FUTURE_REVIEW", data_support_status: "METADATA_ONLY", support_state: "CANDIDATE_FUTURE", country, region: country, exchange: null, timezone: null } as unknown as Parameters<typeof rowFromInstrument>[0];
}

function benchmark(canonical_id: string, change_percent: string | null = null) {
  return { canonical_id, symbol: canonical_id, name: canonical_id, currency: "BRL", value: "10.50", change_percent, data_level: "DEMO", freshness: "STALE", source: "market-pulse-demo", dataset: "demo-benchmarks", timestamp_official: "2026-10-09T00:00:00Z", timestamp_collected: "2026-10-10T00:00:00Z", limitations: ["Benchmark sintético DEMO."], unavailable_reason: null } as Parameters<typeof rowFromBenchmark>[0];
}

test("every family in the user's list has its own logical tab", () => {
  for (const id of ["equity.br.b3.vale3", "equity.br.b3.petr4", "equity.br.b3.cmin3"]) assert.equal(tabForInstrument(instrument(id, "EQUITY", "BR")), "acoes-br");
  assert.equal(tabForInstrument(instrument("equity.us.nasdaq.aapl", "EQUITY", "US")), "acoes-int");
  for (const id of ["index.br.b3.ibovespa", "index.br.ifix", "index.us.sp500", "index.us.nasdaq"]) assert.equal(tabForBenchmark(id), "indices");
  for (const id of ["rate.br.cdi", "index.br.ipca"]) assert.equal(tabForBenchmark(id), "juros-inflacao", id);
  assert.equal(tabForBenchmark("fx.global.usd-brl"), "cambio");
  const named = (id: string) => MARKET_TABS.find((tab) => tab.id === id)?.unavailable?.items.map((item) => item.label).join(" ") ?? "";
  for (const bond of ["LFT", "LTN", "NTN-B"]) assert.match(named("tesouro"), new RegExp(bond));
  for (const credit of ["CDB", "LCI", "CRA", "Debêntures"]) assert.match(named("credito-privado"), new RegExp(credit));
  assert.match(MARKET_TABS.find((tab) => tab.id === "fundos")?.unavailable?.reason ?? "", /MUTUAL_FUND/);
});

test("catalog classes map to tabs and unknown types never disappear", () => {
  const cases: [string, string | null, string][] = [["FII", "BR", "fiis"], ["ETF", "BR", "etfs-bdrs"], ["BDR", "BR", "etfs-bdrs"], ["CRYPTO", "GLOBAL", "cripto"], ["INDEX", "BR", "indices"], ["MUTUAL_FUND", "BR", "fundos"], ["FUTURE", "BR", "outros"]];
  for (const [type, country, tab] of cases) assert.equal(tabForInstrument(instrument("x.y.z", type, country)), tab, type);
  assert.equal(parseMarketTab("cambio"), "cambio");
  assert.equal(parseMarketTab("<script>"), "overview");
  assert.equal(parseMarketTab(null), "overview");
});

test("a synthetic benchmark without a previous value has an unknown change, never FLAT", () => {
  const row = rowFromBenchmark(benchmark("rate.br.cdi"));
  assert.equal(rowDirection(row), null);
  assert.deepEqual(pulseSummary([row]), { UP: 0, DOWN: 0, FLAT: 0, UNKNOWN: 1, total: 1 });
  assert.equal(rowDirection(rowFromBenchmark(benchmark("rate.br.cdi", "0.00"))), "FLAT", "an explicit zero is FLAT");
  assert.equal(pulseSentence(pulseSummary([row])), "1 séries: 0 em alta, 0 em queda, 0 estáveis, 1 sem variação conhecida.");
});

test("an unavailable quote shows no value and no direction, and a missing quote is marked", () => {
  const quote = { canonical_id: "equity.br.b3.vale3", symbol: "VALE3", name: "Vale ON", asset_type: "EQUITY", exchange: "B3", currency: "BRL", price: "61.20", change: "1.00", change_percent: "1.66", data_level: "DEMO", freshness: "UNAVAILABLE", provider: "none", dataset: "none", timestamp_official: null, timestamp_collected: "2026-10-10T00:00:00Z", latency_ms: null, limitations: [], unavailable_reason: "DATASET_NOT_APPROVED", request_id: "t" } as unknown as Parameters<typeof rowFromInstrument>[1];
  const row = rowFromInstrument(instrument("equity.br.b3.vale3", "EQUITY", "BR"), quote);
  assert.equal(displayValue(row), null);
  assert.equal(rowDirection(row), null);
  assert.equal(row.reason, "DATASET_NOT_APPROVED");
  assert.equal(rowFromInstrument(instrument("equity.br.b3.cmin3", "EQUITY", "BR"), undefined).reason, "QUOTE_NOT_LOADED");
});

test("quotes are requested in batches of at most ten and comparison links are capped", () => {
  const ids = Array.from({ length: 23 }, (_, index) => `equity.br.b3.x${index}`);
  assert.deepEqual(chunk(ids, 10).map((group) => group.length), [10, 10, 3]);
  const href = compareHref(ids);
  assert.ok(href.startsWith("/compare?ids="));
  assert.equal(decodeURIComponent(href.slice("/compare?ids=".length)).split(",").length, 10);
  assert.equal(formatUtc("2026-10-09T13:05:00Z"), "09/10/2026, 13:05 UTC");
  assert.equal(formatUtc(null), "Indisponível");
});

test("the particle layout is one equal particle per row, clustered by family only", () => {
  const rows: MarketRow[] = [
    rowFromBenchmark(benchmark("index.br.b3.ibovespa", "1.20")),
    rowFromBenchmark(benchmark("index.us.sp500", "-0.40")),
    rowFromBenchmark(benchmark("rate.br.cdi")),
    rowFromBenchmark(benchmark("fx.global.usd-brl", "0")),
  ];
  const first = pulseLayout(rows);
  assert.deepEqual(first, pulseLayout(rows), "deterministic");
  assert.equal(first.particles.length, rows.length);
  assert.deepEqual(first.clusters.map((cluster) => cluster.tab), ["indices", "juros-inflacao", "cambio"]);
  assert.deepEqual(first.particles.map((particle) => particle.direction), ["UP", "DOWN", null, "FLAT"]);
  for (const particle of first.particles) {
    const cluster = first.clusters.find((item) => item.tab === particle.tab)!;
    assert.ok(Math.abs(particle.x + particle.dx - cluster.cx) < 1e-9 && Math.abs(particle.y + particle.dy - cluster.cy) < 1e-9, "motion starts at the family center");
  }
  const markup = renderToStaticMarkup(createElement(MarketPulseField, { rows, activeTab: "overview", refreshKey: 0 }));
  assert.equal(elements(markup, "svg")[0]["aria-hidden"], "true");
  assert.match(markup, /4 séries: 1 em alta, 1 em queda, 1 estáveis, 1 sem variação conhecida/);
});

test("the markets hub renders accessible tabs before any data arrives", () => {
  const markup = renderToStaticMarkup(createElement(MarketsHub, { initialTab: "tesouro" }));
  const tabs = elements(markup, "button").filter((button) => button.role === "tab");
  assert.ok(tabs.length >= 11);
  const selected = tabs.filter((tab) => tab["aria-selected"] === "true");
  assert.equal(selected.length, 1);
  assert.equal(selected[0].id, "markets-tab-tesouro");
  assert.equal(elements(markup, "div").find((div) => div.role === "tabpanel")?.["aria-labelledby"], "markets-tab-tesouro");
  assert.match(markup, /Tesouro IPCA\+ \(NTN-B\)/);
  assert.doesNotMatch(markup, /\d+,\d{2} BRL/, "no value is shown for an unavailable family");
});

test("catalog coverage is shown in words and benchmarks never borrow the currency as a unit", () => {
  assert.equal(coverageLabel({ support_state: "CANDIDATE_FUTURE", data_support_status: "METADATA_ONLY" }), "Candidato · só metadados");
  assert.equal(coverageLabel({ support_state: "P0_OPERATIONAL", data_support_status: "PROVIDER_PENDING" }), "Universo operacional · provider pendente");
  assert.equal(coverageLabel({ support_state: "NEW_STATE", data_support_status: "NEW_STATUS" }), "NEW_STATE · NEW_STATUS", "unknown states pass through unchanged");
  const equity = rowFromInstrument(instrument("equity.br.b3.vale3", "EQUITY", "BR"), undefined);
  assert.equal(equity.coverage, "Candidato · só metadados");
  assert.equal(equity.unitDeclared, true);
  const cdi = rowFromBenchmark(benchmark("rate.br.cdi"));
  assert.equal(cdi.unitDeclared, false, "H-30: no unit is declared for benchmark levels");
  assert.match(cdi.coverage, /sintética/);
});

test("pulse labels are HTML columns, one per family, and the drawing carries no text", () => {
  const rows = [rowFromBenchmark(benchmark("index.br.b3.ibovespa", "1")), rowFromBenchmark(benchmark("rate.br.cdi"))];
  const markup = renderToStaticMarkup(createElement(MarketPulseField, { rows, activeTab: "indices", refreshKey: 0 }));
  const svg = markup.match(/<svg[\s\S]*?<\/svg>/)?.[0] ?? "";
  assert.doesNotMatch(svg, /<text/);
  const labels = [...markup.matchAll(/<li( class="active")?>([^<]+)<span>(\d+)<\/span><\/li>/g)].map((match) => [match[2], match[3], Boolean(match[1])]);
  assert.deepEqual(labels, [["Índices", "1", true], ["Juros", "1", false]]);
  assert.match(markup, /grid-template-columns:repeat\(2, minmax\(0, 1fr\)\)/);
});
