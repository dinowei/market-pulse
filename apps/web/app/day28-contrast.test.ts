import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

const css = readFileSync(join(process.cwd(), "app", "globals.css"), "utf8");

function block(selector: string): string {
  const start = css.indexOf(`${selector} {`);
  assert.ok(start >= 0, `selector ${selector} not found`);
  return css.slice(start, css.indexOf("}", start));
}

function tokens(selector: string): Record<string, string> {
  const found: Record<string, string> = {};
  for (const [, name, value] of block(selector).matchAll(/(--pa-[\w-]+):\s*(#[0-9a-fA-F]{6})/g)) found[name] = value;
  return found;
}

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const channel = parseInt(hex.slice(i, i + 2), 16) / 255;
    return channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

const themes = { dark: tokens(":root"), light: tokens('[data-theme="light"]') };

for (const [name, t] of Object.entries(themes)) {
  test(`WCAG 2.2 AA contrast in the ${name} theme`, () => {
    assert.ok(contrast(t["--pa-text-primary"], t["--pa-bg-canvas"]) >= 4.5, "primary text on canvas");
    assert.ok(contrast(t["--pa-text-secondary"], t["--pa-bg-surface"]) >= 4.5, "secondary text on surface");
    // Links and flat markers sit on canvas and on surface.
    for (const bg of ["--pa-bg-canvas", "--pa-bg-surface"]) {
      assert.ok(contrast(t["--pa-market-flat"], t[bg]) >= 4.5, `market-flat on ${bg}`);
    }
    // .auth-submit inverts the theme: canvas-colored text on a text-primary background.
    assert.ok(contrast(t["--pa-bg-canvas"], t["--pa-text-primary"]) >= 4.5, "auth-submit label");
  });
}

test("a link that carries .auth-submit never overrides the inverted label color", () => {
  // Regression found by the E2E on 2026-10-01: .portfolios-link set the blue FLAT color
  // on the light .auth-submit background (1.97:1).
  for (const selector of [".portfolios-link", ".watchlists-link"]) {
    assert.doesNotMatch(block(selector), /(^|[;{\s])color\s*:/, `${selector} must not set color`);
  }
  assert.match(block(".auth-submit"), /color:\s*var\(--pa-bg-canvas\)/);
});
