import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

import { contrast } from "../src/lib/color";
import { seriesRole, seriesRoleLabel } from "../src/lib/series-role";
import { ADD_ITEM_ERROR, withAddedItem, withoutItem, withoutList, withReplacedList } from "../src/lib/watchlist-state";

const root = process.cwd();
const read = (...parts: string[]) => readFileSync(join(root, ...parts), "utf8");
const css = read("app", "globals.css");
const comparison = read("src", "components", "multi-asset-comparison.tsx");
const portfolios = read("src", "components", "portfolios.tsx");
const watchlists = read("src", "components", "watchlists.tsx");

function token(selector: string, name: string): string {
  const start = css.indexOf(`${selector} {`);
  const block = css.slice(start, css.indexOf("}", start));
  const match = new RegExp(`${name}:\\s*(#[0-9a-fA-F]{6})`).exec(block);
  assert.ok(match, `${name} missing in ${selector}`);
  return match[1];
}

test("benchmarks are references: blue plus a dashed stroke and a text label, never color alone", () => {
  assert.equal(seriesRole("index.br.b3.ibovespa"), "benchmark");
  assert.equal(seriesRole("rate.br.cdi"), "benchmark");
  assert.equal(seriesRole("index.br.ipca"), "benchmark");
  assert.equal(seriesRole("equity.br.b3.petr4"), "asset");
  assert.match(seriesRoleLabel("benchmark"), /benchmark/);
  assert.match(css, /\.chart-benchmark \{ stroke: var\(--pa-market-flat\); stroke-dasharray:/);
  assert.match(comparison, /className="series-legend"/);
  assert.match(comparison, /linha tracejada/);
  assert.match(comparison, /max_points: DISPLAY_MAX_POINTS/);
});

test("the main series is neutral: chart points no longer use the FLAT blue", () => {
  assert.match(css, /\.chart-point \{ fill: var\(--pa-accent-neutral\); \}/);
  for (const selector of [":root", '[data-theme="light"]']) {
    const accent = token(selector, "--pa-accent-neutral");
    for (const background of ["--pa-bg-canvas", "--pa-bg-surface", "--pa-bg-elevated"]) {
      assert.ok(contrast(accent, token(selector, background)) >= 3, `${selector} accent on ${background}`);
    }
  }
});

test("H-21: the portfolio page loads its details with one /overview request", () => {
  assert.match(portfolios, /\/overview/);
  for (const path of ["/summary", "/valuation", "/equity-curve", "/performance/decomposition", "/income", "/event-markers"]) {
    assert.doesNotMatch(portfolios, new RegExp(`requestJson<[^>]+>\\(\`/api/v1/portfolios/\\$\\{[^}]+\\}${path.replace("/", "\\/")}`), path);
  }
});

const item = (canonical_id: string, position: number) => ({
  id: canonical_id, canonical_id, symbol: canonical_id, display_symbol: canonical_id, name: canonical_id,
  instrument_type: "EQUITY", currency: "BRL", timezone: "America/Sao_Paulo", support_state: "SUPPORTED", position,
});
const list = (id: string, items: ReturnType<typeof item>[]) => ({ id, name: id, is_system: false, items, created_at: "", updated_at: "" });

test("H-21: watchlist mutations update local state from the server response", () => {
  const lists = [list("a", [item("x", 0)]), list("b", [])];
  const added = withAddedItem(lists, "a", item("y", 1));
  assert.deepEqual(added[0].items.map((i) => i.canonical_id), ["x", "y"]);
  assert.equal(added[1], lists[1], "other lists keep identity");
  assert.deepEqual(withoutItem(added, "a", "x")[0].items.map((i) => i.canonical_id), ["y"]);
  const reordered = list("a", [item("y", 0), item("x", 1)]);
  assert.equal(withReplacedList(added, reordered)[0], reordered);
  assert.deepEqual(withoutList(added, "a").map((l) => l.id), ["b"]);
  for (const call of ["await load();"]) {
    const mutations = watchlists.slice(watchlists.indexOf("async function addItem"), watchlists.indexOf("if (loading)"));
    assert.ok(!mutations.includes(call), "mutations must not reload every list");
  }
  assert.match(ADD_ITEM_ERROR, /equity\.br\.b3\.petr4/);
});
