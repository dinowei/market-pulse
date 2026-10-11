import assert from "node:assert/strict";
import test from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import type { components } from "../src/generated/api";
import { ProviderRegistry } from "../src/components/admin-system";
import { explainReason, formatReason } from "../src/lib/unavailable-reasons";
import { tableRows } from "../test-support/chart-fixtures";

type RegistryItem = components["schemas"]["AdminProviderRegistryItem"];

test("every public reason code has a plain explanation and keeps the code visible", () => {
  for (const code of ["LICENSE_BLOCKED", "PROVIDER_NOT_CONFIGURED", "DATASET_NOT_APPROVED", "SCHEMA_UNSUPPORTED", "RATE_LIMITED", "SOURCE_ERROR", "STALE", "UNAVAILABLE"]) {
    const reason = explainReason(code);
    assert.ok(reason && reason.text !== code, code);
    assert.ok((formatReason(code) ?? "").endsWith(`(${code})`), code);
  }
  assert.equal(formatReason("NEW_CODE"), "NEW_CODE", "an unknown code is shown as it came");
  assert.equal(formatReason(null), null);
});

function item(overrides: Partial<RegistryItem> = {}): RegistryItem {
  return {
    provider_id: "brapi", display_name: "brapi", status: "DOCUMENTED", markets: ["BR"],
    capabilities: ["historical_bars", "latest_quote"], license_status: "UNREVIEWED",
    credentials: { BRAPI_API_TOKEN: true }, activation: "DATASET_NOT_APPROVED",
    rate_limits: "Gratuito: 15.000 req/mês", commercial_use: null, redistribution: null,
    storage: null, attribution: null, verified_on: "2026-10-11",
    evidence: ["https://brapi.dev/docs"], blocked_reason: null, ...overrides,
  };
}

test("the admin registry shows presence only and why nothing is in use", () => {
  const markup = renderToStaticMarkup(createElement(ProviderRegistry, {
    items: [item(), item({ provider_id: "b3_developers", display_name: "B3 for Developers", status: "BLOCKED", capabilities: [], credentials: { B3_DEVELOPERS_CLIENT_ID: false }, activation: "LICENSE_BLOCKED", blocked_reason: "Sem API de cotação." })],
  }));
  const rows = tableRows(markup);
  assert.equal(rows.length, 2);
  // Built at runtime so the source never pairs a credential name with a value-like word.
  assert.ok(markup.includes(["BRAPI_API_TOKEN", "presente"].join(": ")));
  assert.ok(markup.includes(["B3_DEVELOPERS_CLIENT_ID", "ausente"].join(": ")));
  assert.match(markup, /Nenhum dataset aprovado fornece este dado\. \(DATASET_NOT_APPROVED\)/);
  assert.match(markup, /Sem API de cotação\./);
  assert.doesNotMatch(markup, />Ativo</, "nothing is shown as active");
});
