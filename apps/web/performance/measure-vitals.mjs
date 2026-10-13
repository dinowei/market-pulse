// Day 38 lab measurement of Core Web Vitals against a real deployment.
// Usage: BASE_URL=https://... RUNS=5 [PROFILE=mobile] node performance/measure-vitals.mjs
// Each run uses a fresh browser context (cold HTTP cache). INP here is a lab proxy: the
// longest interaction after one synthetic click or key press; field INP needs real users.
import { chromium } from "@playwright/test";

const BASE_URL = process.env.BASE_URL;
const RUNS = Number(process.env.RUNS ?? 5);
const ROUTES = (process.env.ROUTES ?? "/,/portfolios,/compare,/calendar,/login").split(",");
// "mobile": 390x844, CPU 4x slower and a 1.6 Mbit/s link with 150 ms latency (CDP).
const MOBILE = process.env.PROFILE === "mobile";
if (!BASE_URL) {
  console.error("Set BASE_URL to the deployment to measure.");
  process.exit(1);
}

const OBSERVERS = () => {
  const store = { lcp: null, cls: 0, inp: null, longTasks: 0, longTaskMs: 0, frames: [] };
  window.__mpVitals = store;
  const observe = (type, callback, extra = {}) => {
    try { new PerformanceObserver((list) => list.getEntries().forEach(callback)).observe({ type, buffered: true, ...extra }); } catch { /* unsupported */ }
  };
  observe("largest-contentful-paint", (entry) => { store.lcp = entry.startTime; });
  observe("layout-shift", (entry) => { if (!entry.hadRecentInput) store.cls += entry.value; });
  observe("longtask", (entry) => { store.longTasks += 1; store.longTaskMs += entry.duration; });
  observe("event", (entry) => { if (entry.interactionId) store.inp = Math.max(store.inp ?? 0, entry.duration); }, { durationThreshold: 16 });
};

const percentile = (values, p) => {
  const sorted = values.filter((v) => v != null).sort((a, b) => a - b);
  if (!sorted.length) return null;
  return sorted[Math.min(sorted.length - 1, Math.ceil((p / 100) * sorted.length) - 1)];
};
const round = (value, digits = 0) => (value == null ? null : Number(value.toFixed(digits)));

async function measure(browser, route) {
  const context = await browser.newContext({ viewport: MOBILE ? { width: 390, height: 844 } : { width: 1366, height: 900 }, isMobile: MOBILE, hasTouch: MOBILE });
  const page = await context.newPage();
  if (MOBILE) {
    const cdp = await context.newCDPSession(page);
    await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
    await cdp.send("Network.emulateNetworkConditions", { offline: false, latency: 150, downloadThroughput: (1.6 * 1024 * 1024) / 8, uploadThroughput: (750 * 1024) / 8 });
  }
  await page.addInitScript(OBSERVERS);
  const started = Date.now();
  await page.goto(new URL(route, BASE_URL).toString(), { waitUntil: "load", timeout: 120_000 });
  let dataReadyMs = null;
  for (let waited = 0; waited < 90_000; waited += 250) {
    if ((await page.getByText(/^Carregando/).count()) === 0) { dataReadyMs = Date.now() - started; break; }
    await page.waitForTimeout(250);
  }
  const frames = await page.evaluate(() => new Promise((resolve) => {
    const stamps = [];
    const tick = (time) => { stamps.push(time); if (stamps.length < 120) requestAnimationFrame(tick); else resolve(stamps.slice(1).map((t, i) => t - stamps[i])); };
    requestAnimationFrame(tick);
  }));
  const target = page.locator("main button:visible, header button:visible").first();
  if (await target.count()) await target.click().catch(() => page.keyboard.press("Tab"));
  else await page.keyboard.press("Tab");
  await page.waitForTimeout(800);
  const vitals = await page.evaluate(() => ({ ...window.__mpVitals, ttfb: performance.getEntriesByType("navigation")[0]?.responseStart ?? null }));
  await context.close();
  return { ...vitals, dataReadyMs, frameP95: percentile(frames, 95) };
}

const browser = await chromium.launch();
const results = {};
for (const route of ROUTES) {
  const runs = [];
  for (let run = 0; run < RUNS; run += 1) runs.push(await measure(browser, route));
  const metric = (key) => runs.map((r) => r[key]);
  results[route] = {
    runs: RUNS,
    LCP_p95: round(percentile(metric("lcp"), 95)),
    LCP_p50: round(percentile(metric("lcp"), 50)),
    CLS_p95: round(percentile(metric("cls"), 95), 3),
    INP_lab_p95: round(percentile(metric("inp"), 95)),
    TTFB_p50: round(percentile(metric("ttfb"), 50)),
    dataReady_p95_ms: round(percentile(metric("dataReadyMs"), 95)),
    longTasks_total_ms_p95: round(percentile(metric("longTaskMs"), 95)),
    frame_p95_ms: round(percentile(metric("frameP95"), 95), 1),
  };
  console.error(`measured ${route}`);
}
await browser.close();
console.log(JSON.stringify({ baseUrl: BASE_URL, profile: MOBILE ? "mobile" : "desktop", measuredAt: new Date().toISOString(), results }, null, 2));
