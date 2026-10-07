import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

import { COLOR_VISIONS, contrast, deltaEOk, simulateColorVision } from "../src/lib/color";
import { DIRECTION_CUE, priceDirection, signedDecimal } from "../src/lib/price-direction";

const root = process.cwd();
const css = readFileSync(join(root, "app", "globals.css"), "utf8");
const dashboard = readFileSync(join(root, "src", "components", "market-data.tsx"), "utf8");

function token(selector: string, name: string): string {
  const start = css.indexOf(`${selector} {`);
  const block = css.slice(start, css.indexOf("}", start));
  const match = new RegExp(`${name}:\\s*(#[0-9a-fA-F]{6})`).exec(block);
  assert.ok(match, `${name} missing in ${selector}`);
  return match[1];
}

const THEMES = [":root", '[data-theme="light"]'];
const DIRECTIONS = ["--pa-market-up", "--pa-market-down", "--pa-market-flat"];
const BACKGROUNDS = ["--pa-bg-canvas", "--pa-bg-surface", "--pa-bg-elevated"];

test("direction comes from the exact Decimal sign, without epsilon or float parsing", () => {
  assert.equal(priceDirection("0.53"), "UP");
  assert.equal(priceDirection("+1"), "UP");
  assert.equal(priceDirection("-0.0001"), "DOWN");
  assert.equal(priceDirection("0.00"), "FLAT");
  assert.equal(priceDirection("-0"), "FLAT");
  assert.equal(priceDirection("0.000000000000000000000000001"), "UP", "no epsilon");
  for (const invalid of [null, undefined, "", "abc", "1e-5", "NaN"]) assert.equal(priceDirection(invalid), null);
  assert.equal(signedDecimal("1.230", "UP"), "+1.230", "digits are not reformatted");
  assert.equal(signedDecimal("-4.5", "DOWN"), "-4.5");
  assert.equal(signedDecimal("-0.00", "FLAT"), "0.00");
});

test("every direction has its own glyph and word, so color is never the only cue", () => {
  const cues = Object.values(DIRECTION_CUE);
  assert.equal(new Set(cues.map((cue) => cue.glyph)).size, 3);
  assert.equal(new Set(cues.map((cue) => cue.word)).size, 3);
  assert.match(dashboard, /<span aria-hidden="true">\{cue\.glyph\}<\/span>/);
  assert.match(dashboard, /\{cue\.word\}/);
  assert.match(dashboard, /base: fechamento anterior/);
  assert.match(css, /\.direction-up \{ color: var\(--pa-market-up\); \}/);
  assert.match(css, /\.direction-down \{ color: var\(--pa-market-down\); \}/);
  assert.match(css, /\.direction-flat \{ color: var\(--pa-market-flat\); \}/);
});

test("FRESH is neutral: the freshness mark no longer borrows the UP green (directive section 8)", () => {
  assert.match(css, /\.data-badge-fresh \.badge-mark \{ background: var\(--pa-accent-neutral\); \}/);
  assert.doesNotMatch(css, /data-badge-fresh[^}]*market-up/);
});

test("direction text is AA (4.5:1) and stays above 3:1 under every simulated color vision", () => {
  // WCAG measures the real colors; the simulated floor guards legibility for dichromats.
  // Lowest measured on 2026-10-07: light UP on elevated, 4.60 normal and 4.30 protanopia.
  for (const theme of THEMES) {
    for (const vision of ["normal", ...COLOR_VISIONS] as const) {
      const sim = (hex: string) => (vision === "normal" ? hex : simulateColorVision(hex, vision));
      const floor = vision === "normal" ? 4.5 : 3;
      for (const direction of DIRECTIONS) {
        for (const background of BACKGROUNDS) {
          const ratio = contrast(sim(token(theme, direction)), sim(token(theme, background)));
          assert.ok(ratio >= floor, `${theme} ${vision} ${direction} on ${background}: ${ratio.toFixed(2)}`);
        }
      }
    }
  }
});

test("the simulation confirms why the non-color cues are mandatory", () => {
  // Measured on 2026-10-07: some directions collapse for some visions. If a palette
  // change ever separated them, this test fails so the report can be revisited.
  const light = (name: string, vision: (typeof COLOR_VISIONS)[number]) => simulateColorVision(token('[data-theme="light"]', name), vision);
  assert.ok(deltaEOk(light("--pa-market-up", "deuteranopia"), light("--pa-market-down", "deuteranopia")) < 0.05);
  assert.ok(deltaEOk(light("--pa-market-down", "achromatopsia"), light("--pa-market-flat", "achromatopsia")) < 0.02);
  assert.ok(deltaEOk(token(":root", "--pa-market-up"), token(":root", "--pa-market-down")) > 0.2, "normal vision separates them");
});

test("A-4/A-5/A-6: focus on every control, underlined in-text links, a heading while loading", () => {
  assert.match(css, /:is\(button, a, input, select, textarea, summary, \[tabindex\]\):focus-visible \{ outline: 2px solid var\(--pa-focus\); \}/);
  assert.match(css, /\.auth-switch a \{[^}]*text-decoration: underline;/);
  const watchlists = readFileSync(join(root, "src", "components", "watchlists.tsx"), "utf8");
  assert.match(watchlists, /if \(loading\) return <main[^>]*><h1 className="sr-only">/);
});
