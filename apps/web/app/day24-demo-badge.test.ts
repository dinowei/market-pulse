import assert from "node:assert/strict";
import test from "node:test";
import { createElement } from "react";
import { DataStateBadge } from "../src/components/market-data";
import { renderToStaticMarkup } from "react-dom/server";

test("DataStateBadge identifies DEMO data with an explicit human label", () => {
  const markup = renderToStaticMarkup(createElement(DataStateBadge, { dataLevel: "DEMO", freshness: "FRESH" }));
  assert.match(markup, /DADOS DE DEMONSTRAÇÃO/);
  assert.match(markup, /DEMO/);
});

test("DataStateBadge does not label real data as demonstration", () => {
  const markup = renderToStaticMarkup(createElement(DataStateBadge, { dataLevel: "REAL_TIME", freshness: "FRESH" }));
  assert.doesNotMatch(markup, /DADOS DE DEMONSTRAÇÃO/);
});
