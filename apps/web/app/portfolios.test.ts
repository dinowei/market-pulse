import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

const root = process.cwd();
const source = readFileSync(join(root, "src", "components", "portfolios.tsx"), "utf8");
const page = readFileSync(join(root, "app", "portfolios", "page.tsx"), "utf8");

test("portfolio page uses generated contracts and exposes the informational boundary", () => {
  assert.match(page, /PortfoliosPanel/);
  assert.match(source, /generated\/api/);
  assert.match(source, /credentials:\s*["']include["']/);
  assert.match(source, /Performance[\s\S]*(P&L|P&amp;L)[\s\S]*valuation[\s\S]*TWR/);
  assert.doesNotMatch(source, /localStorage|sessionStorage/);
});

test("portfolio UI exposes ledger, cash and positions with accessible controls", () => {
  for (const marker of ["portfolios", "Idempotency-Key", "CASH_DEPOSIT", "BUY", "SELL", "cash_balances", "weighted_average_cost", "aria-label", "loading"]) {
    assert.match(source, new RegExp(marker, "i"));
  }
  assert.doesNotMatch(source, /Canvas|WebGL|ParticleChart/);
});
