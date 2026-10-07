import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

import { EDITORIAL_DISCLAIMER, FINANCIAL_DISCLAIMER } from "../src/lib/disclaimers";

const root = process.cwd();
const read = (...parts: string[]) => readFileSync(join(root, ...parts), "utf8");
const component = (name: string) => read("src", "components", `${name}.tsx`);

function policyDisclaimers(): string[] {
  const policy = read("..", "..", "docs", "policies", "FINANCIAL_CONTENT_POLICY.md");
  const section = policy.slice(policy.indexOf("## 11. Disclaimer"), policy.indexOf("## 12."));
  return [...section.matchAll(/^> \*\*(.+)\*\*\r?$/gm)].map((match) => match[1]);
}

test("H-13: the disclaimers are the verbatim text of policy section 11", () => {
  assert.deepEqual(policyDisclaimers(), [FINANCIAL_DISCLAIMER, EDITORIAL_DISCLAIMER]);
});

test("H-13: Morning Call shows the full editorial disclaimer next to the content", () => {
  const panel = component("morning-call");
  assert.match(panel, /<p className="editorial-disclaimer">\{EDITORIAL_DISCLAIMER\}<\/p>/);
  assert.doesNotMatch(panel, /orientação de investimento|solicitação de ordem/);
  assert.doesNotMatch(panel, /aria-hidden="true">Indisponível/, "no hidden text written only for tests");
  for (const unaccented of ["conteudo", "Indisponivel", "versao", "Historico", "servico"]) {
    assert.doesNotMatch(panel, new RegExp(`\\b${unaccented}\\b`), unaccented);
  }
});

test("H-13: every financial area renders the minimum disclaimer", () => {
  for (const name of ["market-data", "watchlists", "portfolios", "economic-calendar", "multi-asset-comparison"]) {
    assert.match(component(name), /\{FINANCIAL_DISCLAIMER\}/, name);
  }
  assert.doesNotMatch(component("market-data"), /Dados informativos; não constituem/);
});
