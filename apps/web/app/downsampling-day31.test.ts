import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

import { DISPLAY_MAX_POINTS, downsamplingSummary } from "../src/lib/downsampling-note";

const component = readFileSync(join(process.cwd(), "src", "components", "multi-asset-comparison.tsx"), "utf8");
const workspace = readFileSync(join(process.cwd(), "src", "components", "chart-workspace.tsx"), "utf8");
const chart = readFileSync(join(process.cwd(), "src", "components", "particle-chart.tsx"), "utf8");

test("no disclosure when the API returned the full series", () => {
  assert.equal(downsamplingSummary(undefined), undefined);
  assert.equal(downsamplingSummary(null), undefined);
});

test("a reduced series discloses counts and what was preserved", () => {
  const text = downsamplingSummary({
    method: "M4",
    max_points: 500,
    original_points: 2600,
    returned_points: 498,
    preserved: ["FIRST", "LAST", "MIN", "MAX", "GAPS"],
    basis: "value",
  });
  assert.match(text ?? "", /Exibindo 498 de 2600 pontos/);
  assert.match(text ?? "", /mínimo e máximo/);
  assert.match(text ?? "", /gaps/);
  assert.match(text ?? "", /nenhum ponto foi criado ou suavizado/);
});

// ADR-028: the canvas workspace draws the full series (no display reduction) and keeps the
// table; the SVG comparison still asks for a bounded, aligned series and says so.
test("the SVG comparison requests a bounded series and discloses the reduction", () => {
  assert.ok(DISPLAY_MAX_POINTS >= 64 && DISPLAY_MAX_POINTS <= 5000);
  assert.match(component, /max_points: DISPLAY_MAX_POINTS/);
  assert.match(component, /role="note">Séries reduzidas para exibição pelo método M4 alinhado/);
  assert.match(workspace, /period=MAX&mode=PRICE&adjustment_type=UNADJUSTED`/);
  assert.doesNotMatch(workspace, /max_points/);
});

test("the chart places points by real timestamps, so uneven reduced spacing is not distorted", () => {
  assert.match(chart, /timestamps\[index\] - minTime/);
});
