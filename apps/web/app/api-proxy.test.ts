import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

import { apiProxyRewrites } from "../src/lib/api-proxy";

test("api proxy is disabled when the origin is unset (local development)", () => {
  assert.deepEqual(apiProxyRewrites(undefined), []);
  assert.deepEqual(apiProxyRewrites("   "), []);
});

test("api proxy forwards only /api/v1 to the configured https origin", () => {
  assert.deepEqual(apiProxyRewrites("https://api.example.test"), [
    { source: "/api/v1/:path*", destination: "https://api.example.test/api/v1/:path*" },
  ]);
  assert.deepEqual(apiProxyRewrites("https://api.example.test/"), [
    { source: "/api/v1/:path*", destination: "https://api.example.test/api/v1/:path*" },
  ]);
});

test("api proxy rejects origins that could leak the session cookie", () => {
  for (const value of [
    "http://api.example.test",
    "api.example.test",
    "https://user:pass@api.example.test",
    "https://api.example.test/api/v1",
    "https://api.example.test?x=1",
  ]) {
    assert.throws(() => apiProxyRewrites(value), /MARKET_PULSE_API_PROXY_ORIGIN/, value);
  }
});

test("next config wires the proxy from the server-only environment variable", () => {
  const config = readFileSync(join(process.cwd(), "next.config.ts"), "utf8");
  assert.match(config, /apiProxyRewrites\(process\.env\.MARKET_PULSE_API_PROXY_ORIGIN\)/);
  assert.doesNotMatch(config, /NEXT_PUBLIC_[A-Z_]*PROXY/);
});
