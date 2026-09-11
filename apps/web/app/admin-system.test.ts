import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

test("admin system route is an internal operational panel using generated contracts", async () => {
  const source = await readFile(new URL("./admin/system/page.tsx", import.meta.url), "utf8");
  const component = await readFile(new URL("../src/components/admin-system.tsx", import.meta.url), "utf8");
  assert.match(source, /AdminSystemPanel/);
  assert.match(component, /components\["schemas"\]\["AdminSystemResponse"\]/);
  assert.match(component, /X-Request-ID/);
  assert.match(component, /Acesso restrito a administradores/);
  assert.match(component, /section.checkedAt/);
});
