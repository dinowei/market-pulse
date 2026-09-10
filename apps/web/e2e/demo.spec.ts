import { test, expect, type Page } from "@playwright/test";
import type { components } from "../src/generated/api";

const api = "http://localhost:8000";
const localPassword = "MarketPulseDemo2026!"; // deliberately fictional, local DEMO only
type PortfolioList = components["schemas"]["PortfolioListResponse"];
type WatchlistList = components["schemas"]["WatchlistListResponse"];

test.beforeEach(async ({ context, request }) => {
  const allowed = new Set(["http://localhost:3000", api]);
  await context.route("**/*", (route) => {
    const url = new URL(route.request().url());
    return allowed.has(url.origin) ? route.continue() : route.abort("blockedbyclient");
  });
  const readiness = await request.get(`${api}/health/ready`);
  expect(readiness.status()).toBe(200);
  const quote = await request.get(`${api}/api/v1/market-data/quotes/demo.equity.mpxa3`);
  expect(quote.status()).toBe(200);
  expect(await quote.json()).toMatchObject({ data_level: "DEMO", provider: "demo", price: expect.stringMatching(/^108(?:\.0+)?$/) });
});

async function login(page: Page, owner: "a" | "b") {
  await page.goto("/login");
  await page.getByLabel("E-mail").fill(`demo.${owner}@market-pulse.local`);
  await page.getByLabel("Senha", { exact: true }).fill(localPassword);
  const loginResponse = page.waitForResponse((response) => new URL(response.url()).pathname === "/api/v1/auth/login" && response.request().method() === "POST");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  expect((await loginResponse).status()).toBe(200);
  await expect(page.getByRole("heading", { name: "Observatório de mercado" })).toBeVisible();
  const cookies = await page.context().cookies(api);
  expect(cookies.some((cookie) => cookie.name === "market_pulse_session" && cookie.httpOnly)).toBe(true);
}

test("principal: login, chart, watchlist, portfolio, Morning Call and logout", async ({ page }) => {
  const marketRequests: string[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname.includes("/api/v1/market-data/")) {
      marketRequests.push(request.url());
    }
  });
  await login(page, "a");
  await expect(page.getByRole("img", { name: /MPXA3 PRICE 1M/ })).toBeVisible();
  await page.getByLabel("Buscar instrumento").fill("MPXA3");
  await page.getByRole("option", { name: /MPXA3/ }).click();
  await expect(page.getByRole("img", { name: /MPXA3 PRICE 1M/ })).toBeVisible();
  expect(marketRequests.some((url) => /\/market-data\/quotes\/$/.test(new URL(url).pathname))).toBe(false);
  expect(marketRequests.some((url) => /\/market-data\/history\/$/.test(new URL(url).pathname))).toBe(false);
  await expect(page.getByLabel("Estado STALE, nível DEMO")).toBeVisible();
  await expect(page.getByText(/DEMO sintético e fictício/).first()).toBeVisible();
  await page.getByRole("button", { name: "5D", exact: true }).click();
  await expect(page.getByRole("img", { name: /MPXA3 PRICE 5D/ })).toBeVisible();
  await page.getByRole("button", { name: "INDEX_100", exact: true }).click();
  await expect(page.getByRole("img", { name: /MPXA3 INDEX_100 5D/ })).toBeVisible();
  await expect(page.getByRole("table", { name: "Fallback tabular da série histórica" }).locator("tbody tr")).toHaveCount(35);
  await expect(page.locator(".particle-chart path")).toHaveCount(1);
  await page.getByRole("button", { name: "PRICE", exact: true }).click();

  await page.getByRole("link", { name: "Watchlists", exact: true }).click();
  const growth = page.getByRole("region", { name: "Growth Demo" });
  await growth.getByRole("button", { name: /Lista selecionada|Selecionar lista/ }).click();
  await page.getByLabel("Adicionar por canonical_id").fill("demo.equity.mpxd3");
  await page.getByRole("button", { name: "Adicionar", exact: true }).click();
  await expect(growth.getByText("MPXD3", { exact: true })).toBeVisible();
  const favorites = page.getByRole("region", { name: "Favoritos" });
  await favorites.getByRole("button", { name: /Lista selecionada|Selecionar lista/ }).click();
  await page.getByLabel("Adicionar por canonical_id").fill("demo.equity.mpxc3");
  await page.getByRole("button", { name: "Adicionar", exact: true }).click();
  await expect(favorites.getByText("MPXC3", { exact: true })).toBeVisible();
  // Restore mutable user preferences; the append-only ledger is never cleaned here.
  await favorites.getByRole("button", { name: "Remover MPXC3", exact: true }).click();
  await growth.getByRole("button", { name: "Remover MPXD3", exact: true }).click();

  await page.getByRole("link", { name: "Voltar ao terminal" }).click();
  await page.getByRole("link", { name: "Carteiras", exact: true }).click();
  await expect(page.getByLabel("Carteira", { exact: true })).toContainText("Alpha Demo");
  await expect(page.getByRole("table", { name: "Saldos reconstruídos do ledger" })).toContainText("8020");
  await expect(page.getByRole("table", { name: "Quantidade, custo médio, valor e P&L" })).toContainText("demo.equity.mpxa3");
  await expect(page.getByRole("table", { name: "Quantidade, custo médio, valor e P&L" })).toContainText("1620");
  await expect(page.locator(".portfolio-metrics").first()).toContainText("10100");
  await expect(page.locator(".portfolio-metrics").first()).toContainText("0.01");
  await expect(page.getByRole("img", { name: /Evolução patrimonial.*DEMO/ })).toBeVisible();
  await expect(page.getByRole("table", { name: "Fallback tabular da equity curve" }).locator("tbody tr")).toHaveCount(5);

  await page.getByRole("link", { name: "Voltar ao terminal" }).click();
  await page.getByRole("link", { name: "Morning Call", exact: true }).click();
  const editorial = page.getByRole("region", { name: "Resumo operacional" });
  await expect(editorial.getByRole("heading", { name: /Morning Call DEMO/ })).toBeVisible();
  await expect(editorial).toContainText("PUBLISHED");
  await expect(editorial).toContainText("Publicado em BRT");
  await expect(editorial.getByRole("list", { name: "Fontes do bloco" }).first()).toBeVisible();
  await expect(editorial).toContainText("Não constitui recomendação de investimento");
  await page.getByRole("button", { name: "Sair", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Entrar no terminal" })).toBeVisible();
  expect((await page.request.get(`${api}/api/v1/auth/me`)).status()).toBe(401);
});

test("isolation: B cannot read A's watchlists, ledger, positions or performance", async ({ page }) => {
  await login(page, "a");
  const aLists = await (await page.request.get(`${api}/api/v1/watchlists`)).json() as WatchlistList;
  const aPortfolios = await (await page.request.get(`${api}/api/v1/portfolios`)).json() as PortfolioList;
  expect(aPortfolios.items).toHaveLength(1);
  await page.getByRole("button", { name: "Sair", exact: true }).click();
  await login(page, "b");
  const bLists = await (await page.request.get(`${api}/api/v1/watchlists`)).json() as WatchlistList;
  expect(bLists.items.some((list) => list.name === "Income Demo")).toBe(true);
  expect(bLists.items.some((list) => list.name === "Growth Demo")).toBe(false);
  for (const list of aLists.items) {
    expect([403, 404]).toContain((await page.request.get(`${api}/api/v1/watchlists/${list.id}`)).status());
  }
  for (const suffix of [
    "",
    "/events",
    "/summary",
    "/positions",
    "/cash-balances",
    "/valuation",
    "/performance",
    "/performance/decomposition",
    "/equity-curve",
  ]) {
    expect([403, 404]).toContain((await page.request.get(`${api}/api/v1/portfolios/${aPortfolios.items[0].id}${suffix}`)).status());
  }
  await page.getByRole("button", { name: "Sair", exact: true }).click();
});
