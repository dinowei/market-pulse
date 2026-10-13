import type { components } from "../generated/api";

type Point = components["schemas"]["EquityCurvePointResponse"];
type Marker = components["schemas"]["PortfolioEventMarkerResponse"];

const markerGlyph: Record<string, string> = {
  BUY: "B",
  SELL: "S",
  CASH_DEPOSIT: "+",
  CASH_WITHDRAWAL: "−",
  DIVIDEND: "D",
  JCP: "J",
  SPLIT: "⇧",
  REVERSE_SPLIT: "⇩",
};

// Number is used only to project backend Decimal strings to SVG coordinates.
// No valuation, return or financial interpolation is calculated in this component.
export function EquityChart({ points, markers = [] }: { points: Point[]; markers?: Marker[] }) {
  const values = points.map((point) => {
    const value = point.total_value_base == null ? null : Number(point.total_value_base);
    return point.valuation_status === "COMPLETE" && point.freshness !== "UNAVAILABLE"
      && Number.isFinite(value) && Number.isFinite(Date.parse(point.valuation_date)) ? value : null;
  });
  const valid = values.filter((value): value is number => value !== null);
  const times = points.map((point) => Date.parse(point.valuation_date));
  const min = Math.min(...valid), max = Math.max(...valid);
  const first = Math.min(...times.filter(Number.isFinite)), last = Math.max(...times.filter(Number.isFinite));
  const segments: string[] = [];
  values.forEach((value, index) => {
    if (value === null) return;
    const x = first === last ? 300 : (times[index] - first) / (last - first) * 600;
    const y = min === max ? 80 : 140 - (value - min) / (max - min) * 120;
    segments.push(`${index === 0 || values[index - 1] === null ? "M" : "L"} ${x} ${y}`);
  });
  const levels = [...new Set(points.map((point) => `${point.data_level}/${point.freshness}`))].join(", ");
  const markerX = (marker: Marker) => {
    const timestamp = Date.parse(marker.occurred_at);
    if (!Number.isFinite(timestamp) || !Number.isFinite(first) || !Number.isFinite(last)) return null;
    if (first === last) return 300;
    return Math.max(0, Math.min(600, ((timestamp - first) / (last - first)) * 600));
  };
  return <svg className="equity-chart" viewBox="0 0 600 160" role="img"
    aria-label={`Evolução patrimonial da carteira; ${levels || "UNAVAILABLE"}`}>
    {segments.length > 0 && <path d={segments.join(" ")} fill="none" stroke="currentColor" strokeWidth="2" />}
    {markers.map((marker) => {
      const x = markerX(marker);
      if (x === null) return null;
      const glyph = markerGlyph[marker.event_type] ?? "•";
      return <g key={`${marker.source_type}-${marker.source_id}`} className={`equity-marker equity-marker-${marker.event_type.toLowerCase()}`} aria-label={`${marker.event_type} ${marker.source_id}`}>
        <line x1={x} y1="12" x2={x} y2="140" stroke="currentColor" strokeDasharray="2 2" />
        <circle cx={x} cy="12" r="7" fill="currentColor" />
        <text x={x} y="15" textAnchor="middle" fill="var(--pa-bg-canvas)" fontSize="8">{glyph}</text>
      </g>;
    })}
  </svg>;
}
