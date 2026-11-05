// Chart colors per theme. The canvas cannot read CSS custom properties written in oklch(), so
// these are the hex values of the same tokens in globals.css (a test keeps them equal).
export type ChartTheme = {
  background: string;
  text: string;
  muted: string;
  grid: string;
  border: string;
  up: string;
  down: string;
  accent: string;
  violet: string;
  cyan: string;
  amber: string;
  pink: string;
};

export const CHART_THEMES: Record<"dark" | "light", ChartTheme> = {
  dark: {
    background: "#202226",
    text: "#f4f5f7",
    muted: "#b4b8c0",
    grid: "#3b3e44",
    border: "#3b3e44",
    up: "#34d399",
    down: "#f87171",
    accent: "#e6e8ec",
    violet: "#b9a0ff",
    cyan: "#4cc9f0",
    amber: "#f5a524",
    pink: "#f472b6",
  },
  light: {
    background: "#ffffff",
    text: "#16171a",
    muted: "#4c5058",
    grid: "#d0d3d8",
    border: "#d0d3d8",
    up: "#08784a",
    down: "#c22d2d",
    accent: "#26282c",
    violet: "#6a45d6",
    cyan: "#0a6d91",
    amber: "#8c5a00",
    pink: "#be185d",
  },
};

// ADR-021 color-vision palette: the same overrides globals.css applies to up and down.
const CVD: Record<"dark" | "light", Pick<ChartTheme, "up" | "down">> = {
  dark: { up: "#bddbb6", down: "#d27668" },
  light: { up: "#007d1e", down: "#5e3532" },
};

/** `display` is "<theme>|<palette>", as read from <html data-theme data-palette>. */
export function currentChartTheme(display: string): ChartTheme {
  const [theme, palette] = display.split("|");
  const mode = theme === "light" ? "light" : "dark";
  const base = CHART_THEMES[mode];
  return palette === "cvd" ? { ...base, ...CVD[mode] } : base;
}

/** #rrggbb plus an alpha byte, for translucent fills on the canvas. */
export function withAlpha(hex: string, alpha: number): string {
  return `${hex}${Math.round(Math.min(Math.max(alpha, 0), 1) * 255).toString(16).padStart(2, "0")}`;
}
