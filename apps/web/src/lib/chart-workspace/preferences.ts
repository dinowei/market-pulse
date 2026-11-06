// Chart preferences kept in this browser (ADR-028): display settings and drawings only, under
// the "market-pulse.chart." prefix. Never a session, token or personal data.
export const CHART_STORAGE_PREFIX = "market-pulse.chart.";

export function readStored(key: string): unknown {
  if (!key.startsWith(CHART_STORAGE_PREFIX)) return null;
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function writeStored(key: string, value: unknown): void {
  if (!key.startsWith(CHART_STORAGE_PREFIX)) return;
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Storage blocked or full: the choice still applies for this visit.
  }
}
