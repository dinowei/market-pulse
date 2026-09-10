import assert from "node:assert/strict";
import test from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { EquityChart } from "../src/components/equity-chart";
import type { components } from "../src/generated/api";
import { elements } from "../test-support/chart-fixtures";

type Point = components["schemas"]["EquityCurvePointResponse"];
const point = (date: string, value: string | null): Point => ({
  valuation_date: date, total_value_base: value, cash_value_base: null,
  positions_value_base: null, data_level: "DEMO", freshness: value === null ? "UNAVAILABLE" : "STALE",
  valuation_status: value === null ? "PARTIAL" : "COMPLETE", missing_inputs: [],
});
const render = (points: Point[]) => renderToStaticMarkup(createElement(EquityChart, { points }));

test("equity geometry uses money and elapsed dates, not ordinal index", () => {
  const markup = render([point("2026-01-01", "300"), point("2026-01-02", "100"), point("2026-01-05", "200")]);
  assert.equal(elements(markup, "path")[0]?.d, "M 0 20 L 150 140 L 600 80");
  assert.match(elements(markup, "svg")[0]["aria-label"], /DEMO/);
});
test("missing and partial valuations break the equity line", () => {
  const markup = render([point("2026-01-01", "100"), point("2026-01-02", null), point("2026-01-03", "200")]);
  assert.equal(elements(markup, "path")[0]?.d, "M 0 140 M 600 20");
  assert.equal(elements(render([{ ...point("2026-01-01", "100"), valuation_status: "PARTIAL" }]), "path").length, 0);
});
test("zero and constant equity remain valid, centered and horizontal", () => {
  assert.equal(elements(render([point("2026-01-01", "0"), point("2026-01-02", "0")]), "path")[0]?.d, "M 0 80 L 600 80");
  assert.equal(elements(render([point("2026-01-01", "100")]), "path")[0]?.d, "M 300 80");
  assert.equal(elements(render([]), "path").length, 0);
});
