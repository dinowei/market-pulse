import assert from "node:assert/strict";
import test from "node:test";

import { FRONTEND_CSP_REPORT_ONLY_RULE } from "../src/lib/security-headers";

test("frontend CSP stays in report-only mode with no collector endpoint", () => {
  assert.equal(FRONTEND_CSP_REPORT_ONLY_RULE.source, "/:path*");
  assert.deepEqual(FRONTEND_CSP_REPORT_ONLY_RULE.headers, [
    {
      key: "Content-Security-Policy-Report-Only",
      value: "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'",
    },
  ]);
  const policy = FRONTEND_CSP_REPORT_ONLY_RULE.headers[0].value;
  assert.doesNotMatch(policy, /unsafe-inline|unsafe-eval|report-uri|report-to/);
});
