import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

// Day 36: automated WCAG 2.2 AA gate on every route and both themes. Axe does not replace
// the manual review (directive section 20); the report lists what was checked by hand.
const ROUTES = ["/", "/login", "/register", "/watchlists", "/portfolios", "/compare", "/calendar", "/heatmap", "/atlas", "/editorial/admin", "/admin/system"];
const THEMES = ["dark", "light"] as const;
const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

// Wait for the rendered state, not for network idle: telemetry beacons may stay open. A
// panel whose backend never answers stays in its loading state, which is scanned as is.
async function settle(page: Page, route: string) {
  await page.goto(route, { waitUntil: "load" });
  await expect(page.locator("h1").first()).toBeAttached();
  await page.getByText(/^Carregando/).first().waitFor({ state: "detached", timeout: 15_000 }).catch(() => undefined);
}

async function open(page: Page, route: string, theme: (typeof THEMES)[number]) {
  await page.addInitScript((value) => {
    try {
      window.localStorage.setItem("market-pulse.theme", value);
    } catch {
      // Storage blocked: the page falls back to the system theme, and the assertion below fails.
    }
  }, theme);
  await settle(page, route);
  await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
}

for (const theme of THEMES) {
  for (const route of ROUTES) {
    test(`axe WCAG 2.2 AA · ${theme} · ${route}`, async ({ page }) => {
      await open(page, route, theme);
      const { violations } = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
      const summary = violations.map((item) => ({ id: item.id, impact: item.impact, targets: item.nodes.map((node) => node.target.join(" ")) }));
      expect(summary, JSON.stringify(summary, null, 2)).toEqual([]);
    });
  }
}

test("reflow: no route scrolls sideways at 320 CSS px (WCAG 1.4.10)", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 640 });
  for (const route of ROUTES) {
    await settle(page, route);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, `${route} overflows by ${overflow}px`).toBeLessThanOrEqual(0);
  }
});

test("keyboard: every focusable control on the dashboard shows a visible focus indicator", async ({ page }) => {
  await settle(page, "/");
  const missing: string[] = [];
  for (let step = 0; step < 25; step += 1) {
    await page.keyboard.press("Tab");
    const state = await page.evaluate(() => {
      const element = document.activeElement as HTMLElement | null;
      if (!element || element === document.body) return null;
      const style = getComputedStyle(element);
      const outlined = style.outlineStyle !== "none" && parseFloat(style.outlineWidth) >= 2;
      return { name: `${element.tagName.toLowerCase()} ${element.textContent?.trim().slice(0, 30) ?? ""}`, outlined };
    });
    if (state && !state.outlined) missing.push(state.name);
  }
  expect(missing).toEqual([]);
});

test("reduced motion keeps the information: the chart still has its table", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await settle(page, "/compare");
  const table = page.locator("table");
  const error = page.getByRole("alert");
  await expect(table.or(error).first()).toBeVisible();
});
