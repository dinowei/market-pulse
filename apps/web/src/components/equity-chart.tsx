import type { components } from "../generated/api";

type Point = components["schemas"]["EquityCurvePointResponse"];

// Number is used only to project backend Decimal strings to SVG coordinates.
// No valuation, return or financial interpolation is calculated in this component.
export function EquityChart({ points }: { points: Point[] }) {
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
  return <svg className="equity-chart" viewBox="0 0 600 160" role="img"
    aria-label={`Evolução patrimonial da carteira; ${levels || "UNAVAILABLE"}`}>
    {segments.length > 0 && <path d={segments.join(" ")} fill="none" stroke="currentColor" strokeWidth="2" />}
  </svg>;
}
