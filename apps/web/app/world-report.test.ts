import assert from "node:assert/strict";
import test from "node:test";
import { regionChange, worldHeadline } from "../src/lib/world-report";

test("a region's number carries sign, glyph and word; unknown stays unknown", () => {
  assert.deepEqual(regionChange("-0.5"), { direction: "DOWN", value: "−0,50%", word: "queda", glyph: "▼" });
  assert.equal(regionChange("1.234")?.value, "+1,23%");
  assert.equal(regionChange(null), null);
});

test("the headline counts only regions with a measure", () => {
  assert.equal(worldHeadline([{ title: "A", change_percent: "1" }, { title: "B", change_percent: "-1" }, { title: "C", change_percent: null }]), "1 de 2 regiões em alta, 1 em queda");
  assert.equal(worldHeadline([{ title: "C", change_percent: null }]), "Ainda sem fechamentos para mostrar");
});
