import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import vm from "node:vm";

import { resolveTheme, THEME_INIT_SCRIPT, THEME_STORAGE_KEY } from "../src/lib/theme";

const root = process.cwd();

function runInitScript({ stored, prefersLight, storageThrows = false }: { stored?: string | null; prefersLight: boolean; storageThrows?: boolean }): string | undefined {
  let applied: string | undefined;
  const sandbox = {
    window: {
      localStorage: {
        getItem: (key: string) => {
          if (storageThrows) throw new Error("blocked");
          return key === THEME_STORAGE_KEY ? stored ?? null : null;
        },
      },
      matchMedia: (query: string) => ({ matches: query === "(prefers-color-scheme: light)" && prefersLight }),
    },
    document: { documentElement: { setAttribute: (name: string, value: string) => { if (name === "data-theme") applied = value; } } },
  };
  vm.runInNewContext(THEME_INIT_SCRIPT, sandbox);
  return applied;
}

test("saved choice wins, then the operating system, then dark", () => {
  assert.equal(resolveTheme("light", false), "light");
  assert.equal(resolveTheme("dark", true), "dark");
  assert.equal(resolveTheme(null, true), "light");
  assert.equal(resolveTheme("unexpected", false), "dark");
});

test("the pre-hydration script applies the same rule and fails closed to dark", () => {
  assert.equal(runInitScript({ stored: "light", prefersLight: false }), "light");
  assert.equal(runInitScript({ stored: "dark", prefersLight: true }), "dark");
  assert.equal(runInitScript({ stored: null, prefersLight: true }), "light");
  assert.equal(runInitScript({ stored: "<script>", prefersLight: false }), "dark");
  assert.equal(runInitScript({ prefersLight: true, storageThrows: true }), "dark");
});

test("the root layout runs the init script before hydration on <html>", () => {
  const layout = readFileSync(join(root, "app", "layout.tsx"), "utf8");
  assert.match(layout, /<html lang="pt-BR" suppressHydrationWarning>/);
  assert.match(layout, /<Script id="mp-theme-init" strategy="beforeInteractive">\{THEME_INIT_SCRIPT\}<\/Script>/);
});

test("no page pins its own theme and only the theme module touches browser storage", () => {
  const dir = join(root, "src", "components");
  for (const file of readdirSync(dir).filter((name) => name.endsWith(".tsx"))) {
    const source = readFileSync(join(dir, file), "utf8");
    assert.doesNotMatch(source, /data-theme=/, `${file} pins a theme`);
    assert.doesNotMatch(source, /localStorage|sessionStorage/, `${file} touches browser storage`);
  }
  const themeCode = readFileSync(join(root, "src", "lib", "theme.ts"), "utf8")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");
  assert.doesNotMatch(themeCode, /sessionStorage|document\.cookie|token|session/i);
  assert.equal((themeCode.match(/localStorage\.setItem\(/g) ?? []).length, 1, "only the theme preference is written");
});
