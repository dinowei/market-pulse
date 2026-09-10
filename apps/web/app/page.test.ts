import test from "node:test";
import assert from "node:assert/strict";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import HomePage from "./page";
import { elements } from "../test-support/chart-fixtures";

test("home renders the terminal without inventing a quote before loading", () => {
  const html = renderToStaticMarkup(createElement(HomePage));
  assert.equal(elements(html, "main").length, 1);
  assert.match(html, /Observatório de mercado/);
  assert.match(html, /Carregando série tipada/);
  assert.equal(elements(html, "path").length, 0);
  assert.doesNotMatch(html, /PETR4|108\.00/);
});
