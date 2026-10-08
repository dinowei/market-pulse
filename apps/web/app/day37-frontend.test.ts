import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

import { describeChange } from "../src/lib/price-direction";

const root = process.cwd();
const read = (...parts: string[]) => readFileSync(join(root, ...parts), "utf8");
const heatmap = read("src", "components", "market-heatmap.tsx");
const atlas = read("src", "components", "global-atlas.tsx");
const dashboard = read("src", "components", "market-data.tsx");
const e2e = read("e2e", "day36-wcag.spec.ts");

test("describeChange keeps the exact Decimal digits and the cue, or reports unknown", () => {
  assert.deepEqual(describeChange("2", "1.886792452830188679245283019", "BRL"), {
    direction: "UP",
    cue: { glyph: "▲", word: "alta" },
    text: "+2 BRL | +1.886792452830188679245283019%",
  });
  assert.equal(describeChange("-0.5", "-0.85", "BRL")?.direction, "DOWN");
  assert.equal(describeChange(null, "0.00", "BRL")?.text, "0.00%");
  assert.equal(describeChange(null, null, "BRL"), null);
  assert.equal(describeChange("1", null, "BRL"), null, "no percent, no claim");
});

test("heatmap: generated contract, direction cues, equivalent table and visible method", () => {
  assert.match(heatmap, /components\["schemas"\]\["HeatmapResponse"\]/);
  assert.match(heatmap, /\/api\/v1\/market-data\/heatmap/);
  assert.match(heatmap, /<span aria-hidden="true">\{change\.cue\.glyph\}<\/span>/);
  assert.match(heatmap, /change\.cue\.word/);
  assert.match(heatmap, /Tabela equivalente ao heatmap/);
  assert.match(heatmap, /payload\.limitations\.map/);
  assert.match(heatmap, /payload\.grouping, payload\.sizing, payload\.color_basis/);
  assert.match(heatmap, /\{FINANCIAL_DISCLAIMER\}/);
  assert.doesNotMatch(heatmap, /parseFloat|Number\(|toFixed|Math\./, "values are shown, never recomputed");
});

test("Global Atlas: catalog metadata in an accessible table, never a price", () => {
  assert.match(atlas, /components\["schemas"\]\["InstrumentList"\]/);
  assert.match(atlas, /\/api\/v1\/instruments\?limit=\$\{ATLAS_LIMIT\}&sort=symbol&order=asc/);
  assert.match(atlas, /<th scope="rowgroup" colSpan=\{COLUMNS\}>/);
  assert.equal((atlas.match(/<th scope="col">/g) ?? []).length, 8, "COLUMNS matches the header");
  assert.doesNotMatch(atlas, /\.price\b|quotes/);
  assert.match(atlas, /\{FINANCIAL_DISCLAIMER\}/);
  assert.doesNotMatch(atlas, /className="state-note" role="note"/, "amber is reserved for STALE");
});

test("both pages are reachable and inside the WCAG gate", () => {
  assert.match(dashboard, /<Link href="\/heatmap">Heatmap<\/Link><Link href="\/atlas">Global Atlas<\/Link>/);
  for (const page of [["app", "atlas", "page.tsx"], ["app", "heatmap", "page.tsx"]]) {
    assert.match(read(...page), /<h1 className="sr-only">/);
  }
  assert.match(e2e, /"\/atlas"/);
  assert.match(e2e, /"\/heatmap"/);
});
