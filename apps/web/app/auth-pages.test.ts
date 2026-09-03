import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

const root = process.cwd();
const source = (name: string) => readFileSync(join(root, "src", "components", name), "utf8");
const page = (name: string) => readFileSync(join(root, "app", name, "page.tsx"), "utf8");

test("login and register pages provide labeled forms", () => {
  for (const name of ["login", "register"]) {
    const content = page(name);
    assert.match(content, /AuthForm/);
  }
  const form = source("auth-form.tsx");
  assert.match(form, /type="email"/);
  assert.match(form, /type="password"/);
  assert.match(form, /label/);
  assert.match(form, /credentials: "include"/);
  assert.doesNotMatch(form, /localStorage|sessionStorage/);
  assert.match(form, /LoginRequest|RegisterRequest|AuthUserResponse|generated\/api/);
});
