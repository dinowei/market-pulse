import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

import { contrast, hexToOklch, oklchToHex, parseOklch } from "../src/lib/color";

const root = process.cwd();
const css = readFileSync(join(root, "app", "globals.css"), "utf8");
const marketData = readFileSync(join(root, "src", "components", "market-data.tsx"), "utf8");

function blockAt(source: string, selector: string, from = 0): string {
  const start = source.indexOf(`${selector} {`, from);
  assert.ok(start >= 0, `selector ${selector} not found`);
  return source.slice(start, source.indexOf("}", start));
}

function hexTokens(selector: string): Record<string, string> {
  return Object.fromEntries([...blockAt(css, selector).matchAll(/(--pa-[\w-]+):\s*(#[0-9a-fA-F]{6})/g)].map(([, name, value]) => [name, value.toLowerCase()]));
}

const supportsStart = css.indexOf("@supports (color: oklch(0% 0 0)) {");
function oklchTokens(selector: string): Record<string, string> {
  assert.ok(supportsStart >= 0, "oklch @supports block missing");
  return Object.fromEntries([...blockAt(css, selector, supportsStart).matchAll(/(--pa-[\w-]+):\s*(oklch\([^)]*\))/g)].map(([, name, value]) => [name, value]));
}

const themes = {
  dark: { hex: hexTokens(":root"), oklch: oklchTokens(":root") },
  light: { hex: hexTokens('[data-theme="light"]'), oklch: oklchTokens('[data-theme="light"]') },
};
const TEXT = ["--pa-text-primary", "--pa-text-secondary", "--pa-market-up", "--pa-market-down", "--pa-market-flat", "--pa-state-stale", "--pa-state-unavailable", "--pa-state-demo"];
const BACKGROUNDS = ["--pa-bg-canvas", "--pa-bg-surface", "--pa-bg-elevated"];

for (const [name, theme] of Object.entries(themes)) {
  test(`${name}: every color token is defined in oklch and its hex fallback is the same sRGB color`, () => {
    assert.deepEqual(Object.keys(theme.oklch).sort(), Object.keys(theme.hex).sort());
    for (const [token, hex] of Object.entries(theme.hex)) {
      assert.equal(oklchToHex(parseOklch(theme.oklch[token])), hex, `${token}: ${theme.oklch[token]} != ${hex}`);
    }
  });

  test(`${name}: WCAG 2.2 AA text contrast on every background`, () => {
    for (const foreground of TEXT) {
      for (const background of BACKGROUNDS) {
        const ratio = contrast(theme.hex[foreground], theme.hex[background]);
        assert.ok(ratio >= 4.5, `${foreground} on ${background} = ${ratio.toFixed(2)}`);
      }
    }
  });

  test(`${name}: focus ring and form-field borders reach 3:1 (WCAG 2.2 1.4.11)`, () => {
    for (const background of BACKGROUNDS) {
      assert.ok(contrast(theme.hex["--pa-focus"], theme.hex[background]) >= 3, `focus on ${background}`);
      assert.ok(contrast(theme.hex["--pa-border-control"], theme.hex[background]) >= 3, `control border on ${background}`);
    }
  });
}

test("both themes keep the same semantic hue family for market and state colors", () => {
  const families: Record<string, [number, number]> = {
    "--pa-market-up": [120, 170],
    "--pa-market-flat": [230, 270],
    "--pa-state-stale": [40, 80],
  };
  for (const [token, [low, high]] of Object.entries(families)) {
    for (const theme of Object.values(themes)) {
      const { h } = hexToOklch(theme.hex[token]);
      assert.ok(h >= low && h <= high, `${token} hue ${h.toFixed(1)} outside ${low}-${high}`);
    }
  }
  for (const theme of Object.values(themes)) {
    const { h } = hexToOklch(theme.hex["--pa-market-down"]);
    assert.ok(h <= 40 || h >= 340, `--pa-market-down hue ${h.toFixed(1)} is not red`);
  }
  for (const token of ["--pa-market-up", "--pa-market-down", "--pa-market-flat", "--pa-state-stale"]) {
    const drift = Math.abs(hexToOklch(themes.dark.hex[token]).h - hexToOklch(themes.light.hex[token]).h);
    assert.ok(Math.min(drift, 360 - drift) <= 8, `${token} hue drifts ${drift.toFixed(1)} degrees between themes`);
  }
});

test("form fields use the control border, never the decorative hairline", () => {
  for (const selector of [".form-field input", ".search input", ".watchlist-form input"]) {
    assert.match(blockAt(css, selector), /border: 1px solid var\(--pa-border-control\)/, selector);
  }
  assert.match(css, /\.portfolio-form input, \.portfolio-form select[^{]*\{[^}]*var\(--pa-border-control\)/);
  assert.match(css, /\.editorial-admin-form input[^{]*\{[^}]*var\(--pa-border-control\)/);
});

test("the downsampling disclosure is neutral text, not the amber STALE/alert color", () => {
  assert.match(marketData, /<p className="muted" role="note">\{downsamplingSummary/);
});
