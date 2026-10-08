import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

import { authErrorMessage, PASSWORD_RULE_HINT, validateCredentials } from "../src/lib/auth-validation";

test("register mirrors the API password policy before sending", () => {
  assert.equal(validateCredentials("register", "pessoa@example.test", "senhaforte123"), undefined);
  assert.equal(validateCredentials("register", " pessoa@example.test ", "Ácentuada1234"), undefined);
  for (const password of ["curta1", "somenteletrasaqui", "123456789012", ""]) {
    assert.match(validateCredentials("register", "pessoa@example.test", password) ?? "", /Senha|Informe a senha/, password);
  }
});

test("login only requires a valid e-mail and a non-empty password", () => {
  assert.equal(validateCredentials("login", "pessoa@example.test", "x"), undefined);
  assert.equal(validateCredentials("login", "pessoa@example.test", ""), "Informe a senha.");
  for (const email of ["", "semarroba", "@example.test", "pessoa@"]) {
    assert.equal(validateCredentials("login", email, "x"), "Informe um e-mail válido.", email);
  }
});

test("API refusals become specific messages without revealing whether an account exists", () => {
  assert.match(authErrorMessage("register", 422), /12 caracteres/);
  assert.equal(authErrorMessage("login", 401), "E-mail ou senha incorretos.");
  assert.match(authErrorMessage("register", 404), /cadastro não está aberto/);
  assert.match(authErrorMessage("login", 429), /Aguarde/);
  assert.match(authErrorMessage("login", 503), /indisponível/);
  assert.doesNotMatch(authErrorMessage("register", 409), /já|existe|cadastrad/i);
});

test("the register form shows the password rule and links it to the field", () => {
  const form = readFileSync(join(process.cwd(), "src", "components", "auth-form.tsx"), "utf8");
  assert.match(form, /aria-describedby=\{isRegister \? "password-hint"/);
  assert.match(form, /id="password-hint"/);
  assert.match(form, /authErrorMessage\(mode, response\.status\)/);
  assert.ok(PASSWORD_RULE_HINT.includes("12"));
});
