// H-22: /compare opens with an asset taken from the catalog the API actually serves (DEMO
// or not), instead of a hardcoded id that may not exist. Benchmarks do not depend on the
// catalog, so the reference line stays the Ibovespa benchmark.
import type { components } from "../generated/api";

type InstrumentSummary = components["schemas"]["InstrumentSummary"];

export const DEFAULT_BENCHMARK_ID = "index.br.b3.ibovespa";
const COMPARABLE_TYPES = new Set(["EQUITY", "ETF", "FII", "BDR"]);
const UNSERVED_STATES = new Set(["BLOCKED_SCOPE", "UNSUPPORTED"]);

export function defaultComparisonIds(instruments: InstrumentSummary[]): string[] {
  const asset = instruments.find(
    (item) => COMPARABLE_TYPES.has(item.instrument_type.toUpperCase()) && !UNSERVED_STATES.has(item.support_state),
  );
  return asset ? [asset.canonical_id, DEFAULT_BENCHMARK_ID] : [DEFAULT_BENCHMARK_ID];
}
