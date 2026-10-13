import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { AppShell, SITE_NAV, isActiveRoute } from "../src/components/site-header";
import { elements } from "../test-support/chart-fixtures";

const shell = () => renderToStaticMarkup(createElement(AppShell, null, createElement("main", { id: "main-content" }, "page")));

test("ADR-028: one app shell lists every section and marks the current route without relying on color", () => {
  const markup = shell();
  const nav = markup.slice(markup.indexOf("<nav"), markup.indexOf("</nav>"));
  const links = elements(nav, "a");
  assert.deepEqual(links.map((link) => link.href).sort(), SITE_NAV.map((item) => item.href).sort());
  assert.deepEqual(links.filter((link) => link["aria-current"] === "page").map((link) => link.href), ["/"]);
  assert.equal(elements(markup, "a")[0].href, "#main-content", "the skip link comes first");
  assert.ok(elements(markup, "button").some((button) => button["aria-label"] === "Sair"));
  assert.match(markup, /<main id="main-content">page<\/main>/, "the page renders inside the shell");
  assert.match(markup, /Buscar instrumento/, "the global search has an accessible name");
  assert.match(markup, /aria-label="Referências de mercado"/, "the ticker is a named list");
});

test("route matching keeps the dashboard exact and sections by prefix", () => {
  assert.equal(isActiveRoute("/", "/"), true);
  assert.equal(isActiveRoute("/markets", "/"), false);
  assert.equal(isActiveRoute("/markets", "/markets"), true);
  assert.equal(isActiveRoute("/assets", "/atlas"), false);
});

test("below desktop width the sidebar becomes a top strip and nothing stays sticky", () => {
  const css = readFileSync(join(process.cwd(), "app", "globals.css"), "utf8");
  const narrow = css.slice(css.indexOf("@media (max-width: 1023px)"));
  assert.match(narrow, /\.sidebar \{[^}]*position: static;/, "a tall sticky sidebar would cover focused content");
  assert.match(narrow, /\.side-nav \{[^}]*overflow-x: auto;/, "the menu scrolls sideways instead of wrapping");
  assert.match(narrow, /\.app-topbar \{[^}]*position: static;/);
  assert.match(css, /scroll-padding-top: 6rem;/, "focus and the skip link clear the sticky desktop top bar");
});
