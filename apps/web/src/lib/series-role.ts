// A comparison line is either the asset being studied or a reference (benchmark). The
// role drives a non-color cue (dashed stroke + text label); blue alone never carries it
// (directive section 11, ADR-006).

const BENCHMARK_PREFIXES = ["index.", "rate.", "fx."] as const;

export type SeriesRole = "asset" | "benchmark";

export function seriesRole(canonicalId: string): SeriesRole {
  return BENCHMARK_PREFIXES.some((prefix) => canonicalId.startsWith(prefix)) ? "benchmark" : "asset";
}

export function seriesRoleLabel(role: SeriesRole): string {
  return role === "benchmark" ? "referência (benchmark)" : "ativo";
}
