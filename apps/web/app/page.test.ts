import test from "node:test";
import assert from "node:assert/strict";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MarketWorkspace } from "../src/components/market-data";
import WorldHome from "./page";
import { elements } from "../test-support/chart-fixtures";

test("the analysis section renders without inventing a quote before loading", () => {
  const html = renderToStaticMarkup(createElement(MarketWorkspace));
  assert.match(html, /Gráfico e análise/);
  assert.match(html, /Carregando o catálogo/);
  assert.equal(elements(html, "path").length, 0);
  assert.doesNotMatch(html, /PETR4|108\.00/);
});

test("home is the world report and shows no number before the API answers", () => {
  const html = renderToStaticMarkup(createElement(WorldHome));
  assert.equal(elements(html, "main").length, 1);
  assert.match(html, /Como o mundo fechou/);
  assert.doesNotMatch(html, /\d%/);
});
