// Global theme (ADR-016) and the optional color-vision palette (ADR-021). Both live on
// <html> so every page shares them. Only these two display preferences are stored: never a
// session, token or personal data.

export type Theme = "dark" | "light";

export const THEME_STORAGE_KEY = "market-pulse.theme";
export const PALETTE_STORAGE_KEY = "market-pulse.palette";

export type Palette = "default" | "cvd";

function savePreference(key: typeof THEME_STORAGE_KEY | typeof PALETTE_STORAGE_KEY, value: string): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Storage blocked (private mode, policy): the preference still applies for this page view.
  }
}

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
export const THEME_INIT_SCRIPT = `(function(){var t="dark";try{var s=window.localStorage.getItem("${THEME_STORAGE_KEY}");var l=!!(window.matchMedia&&window.matchMedia("(prefers-color-scheme: light)").matches);t=(s==="dark"||s==="light")?s:(l?"light":"dark");}catch(e){}document.documentElement.setAttribute("data-theme",t);try{if(window.localStorage.getItem("${PALETTE_STORAGE_KEY}")==="cvd"){document.documentElement.setAttribute("data-palette","cvd");}}catch(e){}})();`;

export function currentTheme(): Theme {
  if (typeof document === "undefined") return "dark";
  const value = document.documentElement.getAttribute("data-theme");
  return isTheme(value) ? value : "dark";
}

export function applyTheme(theme: Theme): void {
  document.documentElement.setAttribute("data-theme", theme);
  savePreference(THEME_STORAGE_KEY, theme);
}

export function currentPalette(): Palette {
  if (typeof document === "undefined") return "default";
  return document.documentElement.getAttribute("data-palette") === "cvd" ? "cvd" : "default";
}

export function applyPalette(palette: Palette): void {
  if (palette === "cvd") document.documentElement.setAttribute("data-palette", "cvd");
  else document.documentElement.removeAttribute("data-palette");
  savePreference(PALETTE_STORAGE_KEY, palette);
}

/** Notifies when <html data-palette> changes (for useSyncExternalStore). */
export function subscribePalette(onChange: () => void): () => void {
  if (typeof MutationObserver === "undefined") return () => undefined;
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-palette"] });
  return () => observer.disconnect();
}

/** Notifies when <html data-theme> changes (for useSyncExternalStore). */
export function subscribeTheme(onChange: () => void): () => void {
  if (typeof MutationObserver === "undefined") return () => undefined;
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => observer.disconnect();
}
