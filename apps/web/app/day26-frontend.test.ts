import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

test("comparison and calendar use generated contracts and accessible fallbacks", async () => {
  const comparison = await readFile(new URL("../src/components/multi-asset-comparison.tsx", import.meta.url), "utf8");
  const calendar = await readFile(new URL("../src/components/economic-calendar.tsx", import.meta.url), "utf8");
  assert.match(comparison, /BatchHistoryResponse/);
  assert.match(comparison, /INDEX_100/);
  assert.match(comparison, /Fallback tabular sincronizado/);
  assert.match(comparison, /prefers-reduced-motion|reduced_motion/);
  assert.match(calendar, /EconomicCalendarResponse/);
  assert.match(calendar, /scope="col"/);
  assert.match(calendar, /timezone/);
  assert.match(calendar, /data_level/);
});
