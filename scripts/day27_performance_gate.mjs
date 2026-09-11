import { readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";

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

console.log("Day 27 performance gate passed: P95 LCP/INP/CLS budgets and P0 bundle policy.");
