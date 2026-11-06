"use client";

import { useSyncExternalStore } from "react";
import { applyPalette, currentPalette, subscribePalette } from "../lib/theme";

// Optional color-vision palette (ADR-021). Off by default; direction keeps its sign, arrow
// and word in both palettes.
export function PaletteToggle() {
  const palette = useSyncExternalStore(subscribePalette, currentPalette, () => "default" as const);
  const enabled = palette === "cvd";
  return (
    <button type="button" className="theme-toggle" aria-pressed={enabled} onClick={() => applyPalette(enabled ? "default" : "cvd")}>
      Paleta para daltonismo
    </button>
  );
}
