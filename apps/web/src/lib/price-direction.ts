// PriceDirection of a change against its comparison basis (directive sections 8 and 9).
// The direction comes from the exact sign of the API Decimal string: no epsilon, no
// float parsing. Every direction carries a sign, a glyph and a word, so color is never
// the only cue (WCAG 1.4.1).

export type PriceDirection = "UP" | "DOWN" | "FLAT";

const DECIMAL = /^[+-]?\d+(\.\d+)?$/;
const ZERO = /^[+-]?0+(\.0+)?$/;

export const DIRECTION_CUE: Record<PriceDirection, { glyph: string; word: string }> = {
  UP: { glyph: "▲", word: "alta" },
  DOWN: { glyph: "▼", word: "queda" },
  FLAT: { glyph: "▬", word: "estável" },
};

export function priceDirection(change: string | null | undefined): PriceDirection | null {
  const value = change?.trim();
  if (!value || !DECIMAL.test(value)) return null;
  if (ZERO.test(value)) return "FLAT";
  return value.startsWith("-") ? "DOWN" : "UP";
}

/** The Decimal string with an explicit sign; digits are never rounded or reformatted. */
export function signedDecimal(value: string, direction: PriceDirection): string {
  const digits = value.trim().replace(/^[+-]/, "");
  if (direction === "UP") return `+${digits}`;
  if (direction === "DOWN") return `-${digits}`;
  return digits;
}

/** Signed absolute and percent change with its cue, or null when the change is unknown. */
export function describeChange(change: string | null | undefined, percent: string | null | undefined, currency: string) {
  const direction = priceDirection(change ?? percent);
  if (!direction || percent == null) return null;
  const absolute = change == null ? "" : `${signedDecimal(change, direction)} ${currency} | `;
  return { direction, cue: DIRECTION_CUE[direction], text: `${absolute}${signedDecimal(percent, direction)}%` };
}
