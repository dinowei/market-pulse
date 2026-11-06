// Day 38 bundle audit: what the browser downloads on first load of each prerendered route.
// Reads the built HTML, sums the referenced /_next/static scripts and stylesheets and
// reports raw and gzip sizes. Run after `npm run build`; no network, no dependencies.
// Also imported by scripts/day27_performance_gate.mjs to enforce the bundle budget.
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { gzipSync } from "node:zlib";

const kb = (bytes) => Math.round((bytes / 1024) * 10) / 10;

function asset(assetCache, staticRoot, url) {
  if (!assetCache.has(url)) {
    const file = join(staticRoot, decodeURIComponent(url.replace(/^\/_next\//, "")));
    const body = readFileSync(file);
    assetCache.set(url, { raw: body.length, gzip: gzipSync(body, { level: 9 }).length });
  }
  return assetCache.get(url);
}

function routes(dir, prefix = "") {
  const found = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.isDirectory()) found.push(...routes(join(dir, entry.name), `${prefix}/${entry.name}`));
    else if (entry.name.endsWith(".html") && !entry.name.startsWith("_")) {
      const name = entry.name.replace(/\.html$/, "");
      found.push({ route: name === "index" ? prefix || "/" : `${prefix}/${name}`, file: join(dir, entry.name) });
    }
  }
  return found;
}

/** First-load JS/CSS per prerendered route of the build in `web/.next`, or null if unbuilt. */
export function auditBundle(web) {
  const appDir = join(web, ".next", "server", "app");
  const staticRoot = join(web, ".next");
  if (!existsSync(appDir)) return null;
  const assetCache = new Map();
  return routes(appDir)
    .map(({ route, file }) => {
      const html = readFileSync(file, "utf8");
      const scripts = [...new Set([...html.matchAll(/<script[^>]+src="(\/_next\/static\/[^"]+\.js)"/g)].map((m) => m[1]))];
      const styles = [...new Set([...html.matchAll(/<link[^>]+href="(\/_next\/static\/[^"]+\.css)"/g)].map((m) => m[1]))];
      const sum = (urls, key) => urls.reduce((total, url) => total + asset(assetCache, staticRoot, url)[key], 0);
      return {
        route,
        scripts: scripts.length,
        jsRawKb: kb(sum(scripts, "raw")),
        jsGzipKb: kb(sum(scripts, "gzip")),
        cssGzipKb: kb(sum(styles, "gzip")),
        htmlGzipKb: kb(gzipSync(Buffer.from(html), { level: 9 }).length),
      };
    })
    .sort((a, b) => a.route.localeCompare(b.route));
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const report = auditBundle(process.cwd());
  if (!report) {
    console.error("Run `npm run build` first: .next/server/app is missing.");
    process.exit(1);
  }
  console.log(JSON.stringify(report, null, 2));
}
