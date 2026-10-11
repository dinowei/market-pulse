import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

import { classLabel, presentClasses, UNAVAILABLE_CLASSES } from "../src/lib/asset-classes";
import { CANONICAL_ID } from "../src/lib/canonical-id";
import { MAX_COMPARED_SERIES } from "../src/lib/comparison-defaults";

const read = (...parts: string[]) => readFileSync(join(process.cwd(), ...parts), "utf8");
const component = (name: string) => read("src", "components", `${name}.tsx`);
const asset = component("asset-detail");
const events = component("asset-events");
const portfolios = component("portfolios");
const comparison = component("multi-asset-comparison");
const account = component("account-panel");
const dashboard = component("market-data");
const e2e = read("e2e", "day36-wcag.spec.ts");

test("T2: the asset page reuses the dashboard contracts and offers only real actions", () => {
  assert.match(asset, /if \(!CANONICAL_ID\.test\(id\)\)/);
  for (const page of [["app", "assets", "page.tsx"], ["app", "compare", "page.tsx"], ["app", "portfolios", "page.tsx"]]) {
    assert.match(read(...page), /<Suspense fallback=/, `${page.join("/")} stays static with a Suspense boundary`);
    assert.doesNotMatch(read(...page), /searchParams/, `${page.join("/")} does not read the query on the server`);
  }
  assert.match(component("global-atlas"), /\/assets\?id=/);
  for (const piece of ["PeriodSelector", "SeriesModeToggle", "ParticleChart", "AccessibleDataTable", "ProvenancePanel", "PriceChange", "DataStateBadge"]) {
    assert.match(asset, new RegExp(`<${piece}\\b`), piece);
  }
  assert.match(asset, /\/api\/v1\/watchlists\/favorites\/\$\{encodeURIComponent\(canonicalId\)\}/);
  assert.match(asset, /\/api\/v1\/watchlists\/\$\{encodeURIComponent\(target\)\}\/items/);
  assert.match(asset, /\/portfolios\?canonical_id=/);
  assert.match(asset, /\/compare\?ids=/);
  assert.match(asset, /Ativo não encontrado/);
  assert.match(asset, /\{FINANCIAL_DISCLAIMER\}/);
  assert.doesNotMatch(asset, /equity\.br\.b3\.\w+/, "no hardcoded asset id");
  assert.match(dashboard, /Abrir página do ativo/);
  assert.doesNotMatch(dashboard, /aguardando contrato com benchmark/, "stale note removed");
});

test("canonical ids accepted by the routes match the catalog identity", () => {
  assert.ok(CANONICAL_ID.test("equity.br.b3.petr4"));
  assert.ok(CANONICAL_ID.test("demo.equity.mpxa3"));
  for (const bad of ["", "PETR4", "equity", "../admin", "equity.br.b3.petr4;drop", "Equity.br"]) assert.ok(!CANONICAL_ID.test(bad), bad);
});

test("T7: proventos show UNAVAILABLE with its reason, never as an empty list", () => {
  assert.match(events, /\/api\/v1\/market-data\/corporate-actions\//);
  assert.match(events, /availability === "UNAVAILABLE"/);
  assert.match(events, /unavailable_reason/);
  assert.match(events, /provenance\.data_level/);
});

test("T7: the portfolio drawdown comes from the API with methodology and table", () => {
  assert.match(portfolios, /setDrawdown\(overview\.drawdown\)/);
  assert.match(portfolios, /Drawdown máximo \(fração do pico\)/);
  assert.match(portfolios, /drawdown\?\.missing_inputs/);
  assert.match(portfolios, /drawdown\?\.methodology/);
  assert.doesNotMatch(portfolios, /\/api\/v1\/portfolios\/\$\{[^}]+\}\/drawdown/, "arrives in the single /overview request");
  assert.match(portfolios, /CANONICAL_ID\.test\(requested\)/);
});

test("T4: the comparison picks up to ten series from the catalog and the API benchmarks", () => {
  assert.equal(MAX_COMPARED_SERIES, 10, "same as BatchHistoryRequest.canonical_ids max_length");
  assert.match(comparison, /<InstrumentSearch onSelect=\{addSeries\} \/>/);
  assert.match(comparison, /\/api\/v1\/market-data\/benchmarks/);
  assert.match(comparison, /disabled=\{ids\.length === 1\}/, "at least one series stays");
  assert.match(comparison, /filter\(\(id\) => CANONICAL_ID\.test\(id\)\)/);
});

test("T5: asset classes come from the data; unserved classes are shown as unavailable", () => {
  assert.deepEqual(presentClasses(["FII", "EQUITY", "CRYPTO", "equity", "WARRANT"]), ["EQUITY", "FII", "CRYPTO", "WARRANT"]);
  assert.equal(classLabel("fii"), "FIIs");
  assert.equal(classLabel("WARRANT"), "WARRANT", "unknown types keep the API name");
  assert.deepEqual(UNAVAILABLE_CLASSES.map((item) => item.label), ["Fundos", "Renda fixa"]);
  for (const name of ["global-atlas", "market-heatmap"]) assert.match(component(name), /<AssetClassFilter /, name);
  assert.match(component("asset-class-filter"), /indisponível — \{item\.reason\}/);
});

test("T3: account deletion needs the typed word and the acknowledgement", () => {
  assert.match(account, /DELETE_CONFIRMATION = "EXCLUIR"/);
  assert.match(account, /confirmation === DELETE_CONFIRMATION && acknowledged/);
  assert.match(account, /\/api\/v1\/account", \{ method: "DELETE" \}/);
  assert.match(account, /\/api\/v1\/account\/data-export/);
  assert.match(account, /irreversível/);
  assert.doesNotMatch(read("app", "globals.css"), /account-delete/, "red stays reserved for DOWN");
  assert.match(dashboard, /<Link href="\/account">Conta<\/Link>/);
});

test("the new pages are inside the WCAG gate", () => {
  assert.match(e2e, /"\/account"/);
  assert.match(e2e, /"\/assets\?id=equity\.br\.b3\.petr4"/);
});
