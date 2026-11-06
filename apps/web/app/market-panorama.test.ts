import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { fallbackLabel, formatAmount, PANORAMA_GROUPS, percentCue, shortReason, windowChange } from "../src/lib/panorama";

// ADR-029: the dashboard's markets overview. It shows only ids the API names, formats what
// the API sends and never turns an unknown change into a number.
const catalog = readFileSync(new URL("../../api/app/instruments/catalog.py", import.meta.url), "utf8");
const benchmarks = readFileSync(new URL("../../api/app/market_data/benchmarks.py", import.meta.url), "utf8");

test("every panorama card points to an id the API catalog or the benchmarks declare", () => {
  for (const group of PANORAMA_GROUPS) {
    for (const entry of group.entries) {
      const source = entry.kind === "instrument" ? catalog : benchmarks;
      assert.ok(source.includes(`"${entry.id}"`), `${entry.id} is not declared by the API`);
    }
  }
  const ids = PANORAMA_GROUPS.flatMap((group) => group.entries.map((entry) => entry.id));
  assert.equal(new Set(ids).size, ids.length, "no card is repeated");
});

test("amounts keep their magnitude and an unknown value stays a dash", () => {
  assert.equal(formatAmount(null), "—");
  assert.equal(formatAmount("81553.68"), "81.553,68");
  assert.equal(formatAmount("5.4321"), "5,4321");
  assert.equal(formatAmount("0.000123"), "0,000123");
});

test("a change carries sign, glyph and word; unknown or malformed stays unknown", () => {
  assert.equal(percentCue("-0.36202810")?.text, "▼ −0,36% queda");
  assert.equal(percentCue("1.5")?.text, "▲ +1,50% alta");
  assert.equal(percentCue("0")?.direction, "FLAT");
  assert.equal(percentCue(null), null);
  assert.equal(percentCue("n/a"), null);
});

test("the line's change compares its own first and last close", () => {
  assert.deepEqual(windowChange([100, 90, 110]), { direction: "UP", percent: "10.00" });
  assert.deepEqual(windowChange([100, 100]), { direction: "FLAT", percent: "0.00" });
  assert.equal(windowChange([100]), null, "one close has no change");
});

test("a card names why it is empty and keeps the code; unknown codes stay as they came", () => {
  assert.equal(shortReason("LICENSE_BLOCKED"), "fora do plano ou da licença (LICENSE_BLOCKED)");
  assert.equal(shortReason("SESSION_REQUIRED"), "entre para ver (SESSION_REQUIRED)");
  assert.equal(shortReason("NEW_CODE"), "NEW_CODE");
  assert.equal(shortReason(null), "indisponível");
  assert.equal(fallbackLabel("crypto.global.btc-usd"), "BTC-USD");
});
