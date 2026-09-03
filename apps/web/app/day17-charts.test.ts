import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

const root = process.cwd();
const chart = () => readFileSync(join(root, "src", "components", "particle-chart.tsx"), "utf8");
const shell = () => readFileSync(join(root, "src", "components", "market-data.tsx"), "utf8");

test("Particle chart keeps contract points, index mode and an accessible fallback", () => {
  const source = `${chart()}\n${shell()}`;
  for (const marker of ["ParticleChart", "PublicHistorySeries", "INDEX_100", "svg", "aria-label", "value", "table"]) {
    assert.match(source, new RegExp(marker));
  }
  assert.match(source, /is_gap/);
  assert.doesNotMatch(source, /smooth|interpolat|WebGL|Three\.js/);
});

test("asset selection is canonical-id based and uses generated contracts", () => {
  const source = shell();
  assert.match(source, /InstrumentSummary/);
  assert.match(source, /canonical_id/);
  assert.match(source, /generated\/api/);
  assert.doesNotMatch(source, /interface\s+(Quote|Asset|HistoryResponse)/);
});
