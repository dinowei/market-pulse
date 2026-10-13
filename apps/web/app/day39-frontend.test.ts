import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

import { DEFAULT_BENCHMARK_ID, defaultComparisonIds } from "../src/lib/comparison-defaults";
import { comparisonRows } from "../src/lib/comparison-table";

const comparison = readFileSync(join(process.cwd(), "src", "components", "multi-asset-comparison.tsx"), "utf8");

const instrument = (canonical_id: string, instrument_type: string, support_state: string) => ({
  id: canonical_id, canonical_id, symbol: canonical_id, display_symbol: canonical_id, name: canonical_id,
  instrument_type, currency: "BRL", aliases: [], catalog_status: "ACTIVE", coverage_tier: "P0_CATALOG",
  data_support_status: "METADATA_ONLY", support_state,
});

test("H-22: the default asset comes from the served catalog, DEMO or not", () => {
  const demo = [instrument("demo.index.mptech", "INDEX", "CANDIDATE_FUTURE"), instrument("demo.equity.mpxa3", "EQUITY", "CANDIDATE_FUTURE")];
  assert.deepEqual(defaultComparisonIds(demo), ["demo.equity.mpxa3", DEFAULT_BENCHMARK_ID]);
  const master = [instrument("equity.br.b3.petr4", "EQUITY", "P0_OPERATIONAL")];
  assert.deepEqual(defaultComparisonIds(master), ["equity.br.b3.petr4", DEFAULT_BENCHMARK_ID]);
  const blocked = [instrument("fund.br.x", "EQUITY", "BLOCKED_SCOPE"), instrument("x.y", "EQUITY", "UNSUPPORTED")];
  assert.deepEqual(defaultComparisonIds(blocked), [DEFAULT_BENCHMARK_ID], "never a blocked or unsupported id");
  assert.deepEqual(defaultComparisonIds([]), [DEFAULT_BENCHMARK_ID]);
});

test("H-22: /compare asks the catalog first and has no hardcoded asset id", () => {
  assert.match(comparison, /\/api\/v1\/instruments\?limit=100&sort=created_at&order=asc/);
  assert.match(comparison, /defaultComparisonIds\(payload\.items\)/);
  assert.doesNotMatch(comparison, /equity\.br\.b3\.petr4/);
});

const point = (timestamp: string, value: string) => ({
  timestamp, session_date: timestamp.slice(0, 10), close: value, value, index_100: value, is_gap: false,
});
const history = (canonical_id: string, points: ReturnType<typeof point>[]) => ({ canonical_id, points }) as unknown as Parameters<typeof comparisonRows>[0][number];

test("comparison table aligns every value with its own instant, never by position", () => {
  const asset = history("equity.br.b3.petr4", [point("2026-09-08T00:00:00Z", "100"), point("2026-09-09T00:00:00Z", "101")]);
  const benchmark = history("index.br.b3.ibovespa", [point("2026-09-09T00:00:00Z", "100"), point("2026-10-04T04:32:02Z", "100.002")]);
  const rows = comparisonRows([asset, benchmark]);
  assert.deepEqual(rows.map((row) => row.timestamp), ["2026-09-08T00:00:00Z", "2026-09-09T00:00:00Z", "2026-10-04T04:32:02Z"]);
  assert.deepEqual(rows.map((row) => row.points.map((p) => p?.value ?? null)), [["100", null], ["101", "100"], [null, "100.002"]]);
  assert.doesNotMatch(comparison, /item\.points\[index\]/, "no positional pairing left");
  assert.match(comparison, /Eixo vertical de/);
});
