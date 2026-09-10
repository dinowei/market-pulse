import type { components } from "../src/generated/api";

type HistoryPoint = components["schemas"]["PublicHistoryPoint"];
type HistorySeries = components["schemas"]["PublicHistorySeries"];
type EquityPoint = components["schemas"]["EquityCurvePointResponse"];
type EquityCurve = components["schemas"]["EquityCurveResponse"];

export function historyPoint(day: string, close: string | null, overrides: Partial<HistoryPoint> = {}): HistoryPoint {
  return { timestamp: `${day}T00:00:00Z`, session_date: day, open: close, high: close, low: close, close, volume: null, value: close, index_100: null, is_gap: false, ...overrides };
}

export function historySeries(points: HistoryPoint[], overrides: Partial<HistorySeries> = {}): HistorySeries {
  return {
    canonical_id: "synthetic.chart.fixture", symbol: "DEMO", period: "1M", mode: "PRICE",
    adjustment_type: "UNADJUSTED", currency: "BRL", data_level: "DEMO", freshness: "FRESH",
    provider: "synthetic-fixture", dataset: "offline-chart-tests", timestamp_official: "2026-09-01T00:00:00Z",
    timestamp_collected: "2026-09-01T00:01:00Z", latency_ms: null,
    limitations: ["Dados sintéticos para teste offline."], points, tabular_fallback: true,
    accessibility: { reduced_motion: true }, unavailable_reason: null, request_id: "offline-test", ...overrides,
  };
}

export function equityPoint(day: string, value: string | null, overrides: Partial<EquityPoint> = {}): EquityPoint {
  return { valuation_date: day, total_value_base: value, cash_value_base: value, positions_value_base: "0", data_level: "DEMO", freshness: value === null ? "UNAVAILABLE" : "FRESH", valuation_status: value === null ? "UNAVAILABLE" : "COMPLETE", missing_inputs: value === null ? ["approved-price"] : [], ...overrides };
}

export function equityCurve(points: EquityPoint[]): EquityCurve {
  return {
    portfolio_id: "synthetic-portfolio", base_currency: "BRL", methodology: "Snapshots factuais do ledger; sem interpolação.", points,
    provenance: [{ provider: "synthetic-fixture", dataset: "offline-equity-tests", source: "fixture local", data_level: "DEMO", freshness: "STALE", source_timestamp: "2026-09-01T00:00:00Z", collected_at: "2026-09-01T00:01:00Z", latency_ms: null, limitations: ["Dados sintéticos; não representam preços atuais."] }],
  };
}

// These helpers inspect rendered HTML/SVG output, never component source text.
export function elements(markup: string, tag: string): Record<string, string>[] {
  return [...markup.matchAll(new RegExp(`<${tag}\\b([^>]*)>`, "g"))].map((match) => Object.fromEntries([...match[1].matchAll(/([\w-]+)="([^"]*)"/g)].map((attribute) => [attribute[1], attribute[2]])));
}

export function coordinates(markup: string): number[][] {
  return elements(markup, "circle").map(({ cx, cy }) => [Number(cx), Number(cy)]);
}

export function tableRows(markup: string): string[][] {
  const body = markup.match(/<tbody>([\s\S]*?)<\/tbody>/)?.[1] ?? "";
  return [...body.matchAll(/<tr>([\s\S]*?)<\/tr>/g)].map((row) => [...row[1].matchAll(/<(?:th|td)\b[^>]*>([\s\S]*?)<\/(?:th|td)>/g)].map((cell) => cell[1]));
}
