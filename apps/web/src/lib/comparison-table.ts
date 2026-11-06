// Rows of the comparison's equivalent table, aligned by instant. Each cell holds the point
// a series has at that exact timestamp, or null: a value is never shown next to a date it
// does not belong to, and missing instants are not filled.
import type { components } from "../generated/api";

type PublicHistorySeries = components["schemas"]["PublicHistorySeries"];
type HistoryPoint = PublicHistorySeries["points"][number];

export type ComparisonRow = { timestamp: string; sessionDate: string; points: (HistoryPoint | null)[] };

export function comparisonRows(series: PublicHistorySeries[]): ComparisonRow[] {
  const byInstant = new Map<string, ComparisonRow>();
  series.forEach((item, column) => {
    for (const point of item.points) {
      const row = byInstant.get(point.timestamp) ?? { timestamp: point.timestamp, sessionDate: point.session_date, points: series.map(() => null) };
      row.points[column] = point;
      byInstant.set(point.timestamp, row);
    }
  });
  return [...byInstant.values()].sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp));
}
