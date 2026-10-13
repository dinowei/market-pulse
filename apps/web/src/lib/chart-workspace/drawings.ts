// Drawing tools of the chart workspace (ADR-028). Anchors are stored in time and price, so a
// drawing survives zoom, interval changes and reloads; nothing here touches market data.
import { CHART_STORAGE_PREFIX, readStored, writeStored } from "./preferences";

export type DrawingTool =
  | "trend" | "ray" | "extended" | "info" | "angle"
  | "hline" | "hray" | "vline" | "cross"
  | "channel" | "regression" | "fib" | "rect" | "text" | "measure";

export type Anchor = { time: number; price: number };
export type Drawing = { id: string; tool: DrawingTool; anchors: Anchor[]; text?: string };

export type ToolSpec = { tool: DrawingTool; label: string; anchors: 1 | 2 | 3; shortcut?: string };

export const TOOL_GROUPS: { id: string; label: string; tools: ToolSpec[] }[] = [
  {
    id: "lines",
    label: "Linhas",
    tools: [
      { tool: "trend", label: "Linha de tendência", anchors: 2, shortcut: "Alt+T" },
      { tool: "ray", label: "Raio", anchors: 2 },
      { tool: "info", label: "Linha de informação", anchors: 2 },
      { tool: "extended", label: "Linha estendida", anchors: 2 },
      { tool: "angle", label: "Ângulo de tendência", anchors: 2 },
      { tool: "hline", label: "Linha horizontal", anchors: 1, shortcut: "Alt+H" },
      { tool: "hray", label: "Raio horizontal", anchors: 1, shortcut: "Alt+J" },
      { tool: "vline", label: "Linha vertical", anchors: 1, shortcut: "Alt+V" },
      { tool: "cross", label: "Linha de cruzamento", anchors: 1, shortcut: "Alt+C" },
    ],
  },
  {
    id: "channels",
    label: "Canais",
    tools: [
      { tool: "channel", label: "Canal paralelo", anchors: 3 },
      { tool: "regression", label: "Tendência de regressão", anchors: 2 },
    ],
  },
  {
    id: "fib",
    label: "Fibonacci",
    tools: [{ tool: "fib", label: "Retração de Fibonacci", anchors: 2 }],
  },
  {
    id: "shapes",
    label: "Formas e anotações",
    tools: [
      { tool: "rect", label: "Retângulo", anchors: 2 },
      { tool: "text", label: "Texto", anchors: 1 },
      { tool: "measure", label: "Medir", anchors: 2 },
    ],
  },
];

export const TOOL_SPECS: Record<DrawingTool, ToolSpec> = Object.fromEntries(
  TOOL_GROUPS.flatMap((group) => group.tools).map((spec) => [spec.tool, spec]),
) as Record<DrawingTool, ToolSpec>;

export const SHORTCUTS: Record<string, DrawingTool> = Object.fromEntries(
  Object.values(TOOL_SPECS)
    .filter((spec) => spec.shortcut)
    .map((spec) => [(spec.shortcut as string).slice(-1).toLowerCase(), spec.tool]),
);

export const FIB_LEVELS = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1] as const;

type Point = { x: number; y: number };

/** The segment p1→p2 extended to the box edges: forward only (ray) or both ways. */
export function extendLine(p1: Point, p2: Point, width: number, height: number, both: boolean): [Point, Point] {
  const dx = p2.x - p1.x;
  const dy = p2.y - p1.y;
  if (dx === 0 && dy === 0) return [p1, p2];
  const limits: number[] = [];
  for (const [delta, origin, size] of [[dx, p1.x, width], [dy, p1.y, height]] as const) {
    if (delta === 0) continue;
    limits.push((0 - origin) / delta, (size - origin) / delta);
  }
  const forward = Math.max(...limits.filter((t) => t > 0), 1);
  const backward = both ? Math.min(...limits.filter((t) => t < 0), 0) : 0;
  return [
    { x: p1.x + dx * backward, y: p1.y + dy * backward },
    { x: p1.x + dx * forward, y: p1.y + dy * forward },
  ];
}

/** Price change, percent and bar count between two anchors (info line and measure). */
export function describeMove(a: Anchor, b: Anchor, bars: number, currency: string): string {
  const change = b.price - a.price;
  const percent = a.price !== 0 ? (change / a.price) * 100 : null;
  const sign = change > 0 ? "+" : change < 0 ? "−" : "";
  const magnitude = Math.abs(change).toLocaleString("pt-BR", { maximumFractionDigits: 2 });
  const pct = percent === null ? "" : ` (${sign}${Math.abs(percent).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}%)`;
  return `${sign}${magnitude} ${currency}${pct} · ${bars} ${bars === 1 ? "barra" : "barras"}`;
}

/** On-screen angle of a segment in degrees, up positive. */
export function screenAngle(p1: Point, p2: Point): number {
  return (Math.atan2(p1.y - p2.y, p2.x - p1.x) * 180) / Math.PI;
}

const STORAGE_PREFIX = `${CHART_STORAGE_PREFIX}drawings.v1:`;

function isAnchor(value: unknown): value is Anchor {
  return Boolean(value) && Number.isFinite((value as Anchor).time) && Number.isFinite((value as Anchor).price);
}

/** Drawings saved for this instrument in this browser; anything malformed is dropped. */
export function loadDrawings(canonicalId: string): Drawing[] {
  const parsed = readStored(STORAGE_PREFIX + canonicalId);
  if (!Array.isArray(parsed)) return [];
  return parsed.filter((item): item is Drawing =>
    Boolean(item) && typeof item.id === "string" && item.tool in TOOL_SPECS && Array.isArray(item.anchors) && item.anchors.every(isAnchor),
  );
}

/** The temporary measure is never kept. */
export function saveDrawings(canonicalId: string, drawings: Drawing[]): void {
  writeStored(STORAGE_PREFIX + canonicalId, drawings.filter((item) => item.tool !== "measure"));
}
