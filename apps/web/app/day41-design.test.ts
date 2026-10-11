import assert from "node:assert/strict";
import test from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { SITE_NAV, SiteChrome, SiteHeader, isActiveRoute } from "../src/components/site-header";
import { elements } from "../test-support/chart-fixtures";

test("one header lists every section and marks the current route without relying on color", () => {
  const markup = renderToStaticMarkup(createElement(SiteHeader));
  const nav = markup.slice(markup.indexOf("<nav"), markup.indexOf("</nav>"));
  const links = elements(nav, "a").filter((link) => SITE_NAV.some((item) => item.href === link.href));
  assert.deepEqual(links.map((link) => link.href), SITE_NAV.map((item) => item.href));
  assert.deepEqual(links.filter((link) => link["aria-current"] === "page").map((link) => link.href), ["/"]);
  assert.ok(elements(markup, "button").some((button) => button["aria-label"] === "Sair"));
  assert.equal(elements(markup, "a")[0].href, "#main-content", "the skip link comes first");
  assert.match(markup, /class="topbar site-header site-header-plain"/);
});

test("route matching keeps the dashboard exact and sections by prefix", () => {
  assert.equal(isActiveRoute("/", "/"), true);
  assert.equal(isActiveRoute("/markets", "/"), false);
  assert.equal(isActiveRoute("/markets", "/markets"), true);
  assert.equal(isActiveRoute("/assets", "/atlas"), false);
});

test("the dashboard renders its own header with search, so the shared chrome stays out", () => {
  assert.equal(renderToStaticMarkup(createElement(SiteChrome)), "");
});
