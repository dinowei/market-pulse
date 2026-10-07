// Global theme (ADR-016). The preference lives on <html data-theme> so every page shares it.
// Only the "dark" | "light" preference is stored: never a session, token or personal data.

export type Theme = "dark" | "light";

export const THEME_STORAGE_KEY = "market-pulse.theme";

export function isTheme(value: unknown): value is Theme {
  return value === "dark" || value === "light";
}

/** Saved choice wins; otherwise follow the operating system; dark is the product default. */
export function resolveTheme(stored: string | null | undefined, prefersLight: boolean): Theme {
  if (isTheme(stored)) return stored;
  return prefersLight ? "light" : "dark";
}

/**
 * Runs before hydration (next/script beforeInteractive in the root layout) so the first paint
 * already uses the right theme. Kept dependency-free and fails closed to the default theme
 * when storage or matchMedia is unavailable.
 */
export const THEME_INIT_SCRIPT = `(function(){var t="dark";try{var s=window.localStorage.getItem("${THEME_STORAGE_KEY}");var l=!!(window.matchMedia&&window.matchMedia("(prefers-color-scheme: light)").matches);t=(s==="dark"||s==="light")?s:(l?"light":"dark");}catch(e){}document.documentElement.setAttribute("data-theme",t);})();`;

export function currentTheme(): Theme {
  if (typeof document === "undefined") return "dark";
  const value = document.documentElement.getAttribute("data-theme");
  return isTheme(value) ? value : "dark";
}

export function applyTheme(theme: Theme): void {
  document.documentElement.setAttribute("data-theme", theme);
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // Storage blocked (private mode, policy): the theme still applies for this page view.
  }
}

/** Notifies when <html data-theme> changes (for useSyncExternalStore). */
export function subscribeTheme(onChange: () => void): () => void {
  if (typeof MutationObserver === "undefined") return () => undefined;
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => observer.disconnect();
}
