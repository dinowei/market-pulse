import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

const root = process.cwd();
const source = readFileSync(join(root, "src", "components", "watchlists.tsx"), "utf8");
const page = readFileSync(join(root, "app", "watchlists", "page.tsx"), "utf8");

test("watchlists page uses generated contracts and treats signed-out state", () => {
  assert.match(page, /WatchlistsPanel/);
  assert.match(source, /generated\/api/);
  assert.match(source, /credentials:\s*["']include["']/);
  assert.match(source, /401|signed-out|login/);
  assert.doesNotMatch(source, /localStorage|sessionStorage/);
});

test("watchlists controls use canonical ids and accessible reorder actions", () => {
  assert.match(source, /canonical_id/);
  assert.match(source, /aria-label/);
  assert.match(source, /Subir|Descer/);
  assert.match(source, /DEMO|UNAVAILABLE|support_state/);
});
