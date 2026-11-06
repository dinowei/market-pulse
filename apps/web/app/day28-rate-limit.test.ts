import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import {
  isRateLimited,
  parseRetryAfter,
  RateLimitNotice,
  rateLimitMessage,
  retryAfterSeconds,
} from "../src/components/rate-limit-notice";

const component = (name: string) => readFileSync(join(process.cwd(), "src", "components", name), "utf8");

test("the message uses Retry-After when the API sends it and degrades gracefully without it", () => {
  assert.equal(rateLimitMessage(), "Muitas requisições, aguarde alguns segundos.");
  assert.equal(rateLimitMessage(60), "Muitas requisições, aguarde 60 segundos.");
  assert.equal(parseRetryAfter("60"), 60);
  for (const bad of [null, "", "0", "-1", "abc", "1.5", "Wed, 21 Oct 2026 07:28:00 GMT", "999999"]) {
    assert.equal(parseRetryAfter(bad), undefined, `Retry-After ${String(bad)} must be ignored`);
  }
});

test("only HTTP 429 is treated as rate limiting", () => {
  const error = (status: number, retryAfter?: number) =>
    Object.assign(new Error(`HTTP ${status}`), { status, retryAfter });
  assert.equal(isRateLimited(error(429)), true);
  assert.equal(isRateLimited(error(401)), false);
  assert.equal(isRateLimited(error(500)), false);
  assert.equal(isRateLimited("429"), false);
  assert.equal(retryAfterSeconds(error(429, 60)), 60);
  assert.equal(retryAfterSeconds(error(429)), undefined);
});

test("the notice is an alert with a keyboard-reachable native retry button", () => {
  const markup = renderToStaticMarkup(createElement(RateLimitNotice, { retryAfter: 60, onRetry: () => undefined }));
  assert.match(markup, /role="alert"/);
  assert.match(markup, /Muitas requisições, aguarde 60 segundos\./);
  assert.match(markup, /<button type="button">Tentar novamente<\/button>/);
});

test("portfolios and watchlists route 429 to the notice instead of the generic error", () => {
  for (const file of ["portfolios.tsx", "watchlists.tsx"]) {
    const source = component(file);
    assert.match(source, /isRateLimited\(reason\)/, file);
    assert.match(source, /<RateLimitNotice/, file);
    assert.match(source, /Retry-After/, file);
  }
  // A failed load must not be presented as an empty list.
  assert.match(component("watchlists.tsx"), /watchlists\.length === 0 && !rateLimit/);
});
