import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

const root = process.cwd();
const panel = readFileSync(join(root, "src", "components", "morning-call.tsx"), "utf8");
const shell = readFileSync(join(root, "src", "components", "market-data.tsx"), "utf8");

test("Morning Call uses generated editorial contracts and exposes factual states", () => {
  for (const marker of ["MorningCallPanel", "EditorialPostResponse", "editorial/morning-call/latest", "PUBLISHED", "FACT", "RISK", "LIMITATION", "source", "limitation"]) {
    assert.match(`${panel}\n${shell}`, new RegExp(marker, "i"));
  }
  assert.doesNotMatch(panel, /\b(recomend\w*|compre|venda|IA|OpenAI)\b/i);
});

test("Morning Call panel has loading, empty and error states", () => {
  for (const marker of ["Carregando", "Indisponível", "Nenhum conteúdo", "role=\"alert\""]) {
    assert.match(panel, new RegExp(marker, "i"));
  }
});
