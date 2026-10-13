import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import vm from "node:vm";

import { contrast, deltaEOk, simulateColorVision } from "../src/lib/color";
import { PALETTE_STORAGE_KEY, THEME_INIT_SCRIPT } from "../src/lib/theme";

const css = readFileSync(join(process.cwd(), "app", "globals.css"), "utf8");

function block(selector: string): string {
  const start = css.indexOf(`${selector} {`);
  assert.ok(start >= 0, `${selector} missing`);
  return css.slice(start, css.indexOf("}", start));
}
function token(selector: string, name: string): string {
  const match = new RegExp(`${name}:\\s*(#[0-9a-fA-F]{6})`).exec(block(selector));
  assert.ok(match, `${name} missing in ${selector}`);
  return match[1];
}

const THEMES = [
  { base: ":root", cvd: ':root[data-palette="cvd"]' },
  { base: '[data-theme="light"]', cvd: '[data-theme="light"][data-palette="cvd"]' },
];
const DIRECTIONS = ["--pa-market-up", "--pa-market-down", "--pa-market-flat"];
const BACKGROUNDS = ["--pa-bg-canvas", "--pa-bg-surface", "--pa-bg-elevated"];
const VISIONS = ["protanopia", "deuteranopia", "tritanopia"] as const;

function minimumDistance(colors: string[]): number {
  let minimum = Infinity;
  for (const vision of VISIONS) {
    const simulated = colors.map((hex) => simulateColorVision(hex, vision));
    for (let a = 0; a < simulated.length; a += 1) {
      for (let b = a + 1; b < simulated.length; b += 1) minimum = Math.min(minimum, deltaEOk(simulated[a], simulated[b]));
    }
  }
  return minimum;
}

test("ADR-021: the color-vision palette keeps AA contrast on every background", () => {
  for (const { base, cvd } of THEMES) {
    for (const direction of DIRECTIONS) {
      for (const background of BACKGROUNDS) {
        const ratio = contrast(token(cvd, direction), token(base, background));
        assert.ok(ratio >= 4.5, `${cvd} ${direction} on ${background}: ${ratio.toFixed(2)}`);
      }
    }
  }
});

test("ADR-021: directions are at least twice as far apart for dichromats as in the default palette", () => {
  for (const { base, cvd } of THEMES) {
    const standard = minimumDistance(DIRECTIONS.map((name) => token(base, name)));
    const optional = minimumDistance(DIRECTIONS.map((name) => token(cvd, name)));
    assert.ok(optional >= 2 * standard, `${cvd}: ${optional.toFixed(3)} vs ${standard.toFixed(3)}`);
  }
});

test("ADR-021: the palette is off by default and applied before hydration when saved", () => {
  const run = (stored: string | null) => {
    const attributes: Record<string, string> = {};
    vm.runInNewContext(THEME_INIT_SCRIPT, {
      window: { localStorage: { getItem: (key: string) => (key === PALETTE_STORAGE_KEY ? stored : null) }, matchMedia: () => ({ matches: false }) },
      document: { documentElement: { setAttribute: (name: string, value: string) => { attributes[name] = value; } } },
    });
    return attributes;
  };
  assert.equal(run(null)["data-palette"], undefined);
  assert.equal(run("default")["data-palette"], undefined);
  assert.equal(run("cvd")["data-palette"], "cvd");
  assert.equal(run("cvd")["data-theme"], "dark", "the theme rule is unchanged");
});
