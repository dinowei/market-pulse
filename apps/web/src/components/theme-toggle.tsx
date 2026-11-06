"use client";

import { useSyncExternalStore } from "react";
import { applyTheme, currentTheme, subscribeTheme } from "../lib/theme";

export function ThemeToggle() {
  const theme = useSyncExternalStore(subscribeTheme, currentTheme, () => "dark" as const);
  const next = theme === "dark" ? "light" : "dark";
  const label = next === "light" ? "claro" : "escuro";
  return (
    <button type="button" className="theme-toggle" aria-label={`Mudar para tema ${label}`} onClick={() => applyTheme(next)}>
      Tema {label}
    </button>
  );
}
