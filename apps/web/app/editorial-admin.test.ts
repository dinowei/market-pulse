import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

const root = process.cwd();
const panel = readFileSync(join(root, "src", "components", "editorial-admin.tsx"), "utf8");
const page = readFileSync(join(root, "app", "editorial", "admin", "page.tsx"), "utf8");

test("admin CMS uses generated contracts and protected workflow", () => {
  for (const marker of ["EditorialAdminPanel", "EditorialAdminPostResponse", "/api/v1/editorial/admin", "credentials: \"include\"", "validate", "submit-review", "approve", "publish", "archive", "FACT", "RISK", "LIMITATION"]) assert.match(`${panel}\n${page}`, new RegExp(marker.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i"));
  assert.doesNotMatch(panel, /localStorage|sessionStorage|\bcompre\b|\bvenda\b|\bIA\b|OpenAI/i);
});
