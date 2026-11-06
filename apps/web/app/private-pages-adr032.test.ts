import assert from "node:assert/strict";
import test from "node:test";

import { decimalSign, formatDecimal, fractionToPercent } from "../src/lib/decimal-text";
import { allocation, assetClassLabel, seriesStats, symbolOf } from "../src/lib/series-stats";

test("amounts are formatted on the digits, without a float changing a cent", () => {
  assert.equal(formatDecimal("10100"), "10.100,00");
  assert.equal(formatDecimal("1234567.895"), "1.234.567,90");
  assert.equal(formatDecimal("-0.004"), "0,00");
  assert.equal(formatDecimal("-12.5"), "−12,50");
  assert.equal(formatDecimal("90071992547409931.12"), "90.071.992.547.409.931,12");
  assert.equal(formatDecimal("não é número"), "não é número");
  assert.equal(formatDecimal("999.999"), "1.000,00");
});

test("a fraction becomes a percent by moving the point", () => {
  assert.equal(fractionToPercent("0.01"), "1,00%");
  assert.equal(fractionToPercent("-0.1234"), "−12,34%");
  assert.equal(fractionToPercent("1"), "100,00%");
  assert.deepEqual(["1.5", "-2", "0.00", null, "x"].map(decimalSign), [1, -1, 0, null, null]);
});

test("window statistics describe the closes and need enough returns for volatility", () => {
  const stats = seriesStats([100, 110, 99]);
  assert.ok(stats);
  assert.equal(stats.returnPercent.toFixed(2), "-1.00");
  assert.equal(stats.max, 110);
  assert.equal(stats.volatility, null);
  assert.equal(seriesStats([100]), null);
  assert.equal(seriesStats([100, 0]), null);
  const long = seriesStats(Array.from({ length: 30 }, (_, index) => 100 + (index % 2)));
  assert.ok(long && long.volatility !== null && long.volatility > 0);
});

test("allocation weighs what is priced, reports what is not and draws slices end to end", () => {
  const { slices, unpriced } = allocation([
    { canonical_id: "equity.br.b3.petr4", market_value_base: "300" },
    { canonical_id: "etf.br.b3.bova11", market_value_base: "100" },
    { canonical_id: "fii.br.b3.mxrf11", market_value_base: null },
  ], "100");
  assert.equal(unpriced, 1);
  assert.deepEqual(slices.map((slice) => [slice.label, slice.percent, slice.start]), [["Ações", 60, 0], ["ETFs", 20, 60], ["Caixa", 20, 80]]);
  assert.equal(assetClassLabel("warrant.x"), "warrant");
  assert.equal(symbolOf("equity.br.b3.petr4"), "PETR4");
});
