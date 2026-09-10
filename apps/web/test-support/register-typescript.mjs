import { existsSync, readFileSync } from "node:fs";
import { createRequire, registerHooks } from "node:module";
import { extname } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

// Initialize Next's CommonJS entry before the TS hook (Node 22 CJS/ESM interop).
createRequire(import.meta.url)("next/link");

// Node's test runner cannot load TSX. Compile local TypeScript with the same
// JSX runtime as the app, while keeping React and all components real.
registerHooks({
  resolve(specifier, context, nextResolve) {
    if (specifier === "next/link") return nextResolve("next/link.js", context);
    if (specifier === "next/navigation") return nextResolve(new URL("./next-navigation.mjs", import.meta.url).href, context);
    if (specifier.startsWith(".") && context.parentURL && !extname(specifier)) {
      for (const extension of [".ts", ".tsx"]) {
        const candidate = new URL(`${specifier}${extension}`, context.parentURL);
        if (existsSync(candidate)) return nextResolve(candidate.href, context);
      }
    }
    return nextResolve(specifier, context);
  },
  load(url, context, nextLoad) {
    if (url.startsWith("file:") && /\.(ts|tsx)$/.test(url) && !url.includes("/node_modules/")) {
      const { outputText } = ts.transpileModule(readFileSync(new URL(url), "utf8"), {
        fileName: fileURLToPath(url),
        compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020, jsx: ts.JsxEmit.ReactJSX },
      });
      return { format: "module", source: outputText, shortCircuit: true };
    }
    return nextLoad(url, context);
  },
});
