import { readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const root = process.cwd();
const fixturePath = path.join(root, "apps", "web", "performance", "day27-fixtures.json");
const fixture = JSON.parse(await readFile(fixturePath, "utf8"));
const failures = [];

for (const [route, metrics] of Object.entries(fixture.samples)) {
  for (const [metric, value] of Object.entries(metrics)) {
    const budget = fixture.budgets[metric];
    if (budget === undefined || Number(value) > Number(budget)) {
      failures.push(`${route} ${metric}=${value} exceeds ${budget}`);
    }
  }
}

// Day 38: the real staging measurements recorded with measure-vitals.mjs must also stay
// within the same budgets, for every profile and route.
const measured = JSON.parse(await readFile(path.join(root, "apps", "web", "performance", "day38-staging.json"), "utf8"));
const measuredKeys = { LCP: "LCP_p95", INP: "INP_lab_p95", CLS: "CLS_p95" };
for (const [profile, data] of Object.entries(measured.profiles)) {
  for (const [route, metrics] of Object.entries(data.results)) {
    for (const [budgetKey, key] of Object.entries(measuredKeys)) {
      const value = metrics[key];
      if (value == null || Number(value) > Number(fixture.budgets[budgetKey])) {
        failures.push(`staging ${profile} ${route} ${key}=${value} exceeds ${fixture.budgets[budgetKey]}`);
      }
    }
  }
}

// Day 38: first-load bundle budget per prerendered route, measured on the current build.
const { auditBundle } = await import(pathToFileURL(path.join(root, "apps", "web", "scripts", "bundle-audit.mjs")).href);
const bundleBudget = JSON.parse(await readFile(path.join(root, "apps", "web", "performance", "bundle-budget.json"), "utf8"));
for (const entry of auditBundle(path.join(root, "apps", "web")) ?? []) {
  if (entry.jsGzipKb > bundleBudget.firstLoadJsGzipKb) failures.push(`${entry.route} first-load JS ${entry.jsGzipKb} KB gzip exceeds ${bundleBudget.firstLoadJsGzipKb} KB`);
  if (entry.cssGzipKb > bundleBudget.firstLoadCssGzipKb) failures.push(`${entry.route} first-load CSS ${entry.cssGzipKb} KB gzip exceeds ${bundleBudget.firstLoadCssGzipKb} KB`);
}

const bundleRoot = path.join(root, "apps", "web", ".next", "static");
if (existsSync(bundleRoot)) {
  const forbidden = /(?:three(?:\.js)?|babylon(?:\.js)?|webgl)/i;
  const { glob } = await import("node:fs/promises");
  for await (const file of glob("**/*.{js,mjs,css}", { cwd: bundleRoot, withFileTypes: false })) {
    const text = await readFile(path.join(bundleRoot, file), "utf8");
    if (forbidden.test(text)) failures.push(`forbidden 3D/WebGL token in ${file}`);
  }
}

if (failures.length) {
  console.error("Day 27 performance gate failed:");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log("Performance gate passed: P95 LCP/INP/CLS budgets (fixtures and recorded staging), bundle budget and P0 bundle policy.");
