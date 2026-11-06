import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

import { comparisonLines, commonStart, nearestPoint } from "../src/lib/comparison-series";
import { blockHeight, changeStep, squarify } from "../src/lib/treemap";

const read = (...parts: string[]) => readFileSync(join(process.cwd(), ...parts), "utf8");

test("treemap: areas follow the values and everything stays inside the box", () => {
  const box = { x: 0, y: 0, width: 600, height: 400 };
  const values = [50, 25, 15, 10];
  const rects = squarify(values, box);
  const total = values.reduce((sum, value) => sum + value, 0);
  rects.forEach((rect, index) => {
    assert.ok(Math.abs(rect.width * rect.height - (values[index] / total) * 240000) < 1, "area");
    assert.ok(rect.x >= -0.01 && rect.y >= -0.01 && rect.x + rect.width <= 600.01 && rect.y + rect.height <= 400.01, "inside");
  });
  for (let a = 0; a < rects.length; a += 1) for (let b = a + 1; b < rects.length; b += 1) {
    const overlap = Math.max(0, Math.min(rects[a].x + rects[a].width, rects[b].x + rects[b].width) - Math.max(rects[a].x, rects[b].x)) * Math.max(0, Math.min(rects[a].y + rects[a].height, rects[b].y + rects[b].height) - Math.max(rects[a].y, rects[b].y));
    assert.ok(overlap < 0.01, "no overlap");
  }
});

test("treemap: empty or non-positive input draws nothing", () => {
  assert.deepEqual(squarify([], { x: 0, y: 0, width: 10, height: 10 }), []);
  assert.equal(squarify([0, -1], { x: 0, y: 0, width: 10, height: 10 })[0].width, 0);
});

test("color step and block height grow with the move; unknown is not a move", () => {
  assert.deepEqual([0, 0.2, -1, 2, -5].map(changeStep), [0, 1, 2, 3, 4]);
  assert.ok(blockHeight(-5) > blockHeight(1));
  assert.equal(blockHeight(50), 38);
  assert.equal(blockHeight(null), 4);
});

const point = (day: string, index: string | null, close = "10") => ({ timestamp: `${day}T00:00:00Z`, index_100: index, close, value: null, is_gap: index === null });
const series = (id: string, points: ReturnType<typeof point>[]) => ({ canonical_id: id, symbol: id, currency: "BRL", points }) as never;

test("comparison: different history depths are rebased on the first shared date", () => {
  const long = series("US", [point("2026-01-01", "100"), point("2026-02-01", "110"), point("2026-03-01", "121")]);
  const short = series("BR", [point("2026-02-01", "100"), point("2026-03-01", "90")]);
  assert.equal(commonStart([long, short], "INDEX_100"), Date.parse("2026-02-01T00:00:00Z"));
  const [us, br] = comparisonLines([long, short], "INDEX_100");
  assert.equal(us.points[0].value, 100);
  assert.ok(Math.abs((us.changePercent ?? 0) - 10) < 1e-9, "the long series counts only the shared window");
  assert.ok(Math.abs((br.changePercent ?? 0) + 10) < 1e-9);
});

test("comparison: a gap is never filled and no data means no result", () => {
  const [line] = comparisonLines([series("X", [point("2026-01-01", "100"), point("2026-02-01", null), point("2026-03-01", "105")])], "INDEX_100");
  assert.equal(line.points.length, 2);
  const [none] = comparisonLines([series("Y", [])], "INDEX_100");
  assert.equal(none.changePercent, null);
  assert.equal(nearestPoint([], 1), null);
});

test("pages folded into others keep working as redirects and sections", () => {
  const config = read("next.config.ts");
  for (const route of ["/regions", "/terminal", "/markets"]) assert.ok(config.includes(`source: "${route}"`), route);
  assert.match(read("app", "atlas", "page.tsx"), /MarketsFromQuery/);
  assert.match(read("app", "atlas", "page.tsx"), /GlobalAtlas/);
  const home = read("src", "components", "world-report-page.tsx");
  assert.match(home, /MarketWorkspace/);
  assert.match(read("src", "components", "market-data.tsx"), /MarketPanorama/);
  assert.match(read("src", "components", "market-data.tsx"), /MorningCallPanel/);
  assert.match(read("src", "components", "world-report.tsx"), /RegionDetail/);
});

test("owner data stays in memory: the cache never touches browser storage and login clears it", () => {
  const cache = read("src", "lib", "use-cached-api.ts");
  assert.doesNotMatch(cache, /localStorage|sessionStorage|indexedDB/);
  assert.match(read("src", "components", "auth-form.tsx"), /clearApiCache\(\)/);
  assert.match(read("src", "components", "site-header.tsx"), /clearApiCache\(\)/);
});

test("the map sends the session and every block states its number, not only a color", () => {
  const map = read("src", "components", "market-heatmap.tsx");
  assert.match(map, /useCachedApi<MarketMap>/);
  assert.match(map, /percentText\(tile\.change_percent\)/);
  assert.match(map, /aria-label=\{label\}/);
  assert.match(map, /Tabela equivalente ao mapa/);
  assert.match(map, /\{FINANCIAL_DISCLAIMER\}/);
  assert.match(read("src", "components", "multi-asset-comparison.tsx"), /apiRequest<BatchHistoryResponse>/);
});
