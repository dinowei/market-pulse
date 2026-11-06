// Formats API Decimal strings as text, without passing through a float: portfolio amounts must
// not change a cent on the way to the screen.
const DECIMAL = /^([+-]?)(\d+)(?:\.(\d+))?$/;

/** pt-BR grouping, rounded half up on the digits themselves. Non-decimal input comes back as is. */
export function formatDecimal(value: string, places = 2): string {
  const match = DECIMAL.exec(value.trim());
  if (!match) return value;
  const [, sign, integer, fraction = ""] = match;
  const digits = BigInt(integer + fraction.padEnd(places, "0").slice(0, places)) + (Number(fraction[places] ?? "0") >= 5 ? BigInt(1) : BigInt(0));
  const text = digits.toString().padStart(places + 1, "0");
  const whole = text.slice(0, text.length - places).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  const cents = places > 0 ? `,${text.slice(-places)}` : "";
  const isZero = /^0*$/.test(text);
  return `${sign === "-" && !isZero ? "−" : ""}${whole}${cents}`;
}

/** A fraction such as "0.1234" as a percent, moving the decimal point instead of multiplying. */
export function fractionToPercent(value: string, places = 2): string {
  const match = DECIMAL.exec(value.trim());
  if (!match) return value;
  const [, sign, integer, fraction = ""] = match;
  const padded = fraction.padEnd(2, "0");
  return `${formatDecimal(`${sign}${integer}${padded.slice(0, 2)}.${padded.slice(2) || "0"}`, places)}%`;
}

export function decimalSign(value: string | null | undefined): -1 | 0 | 1 | null {
  const match = value == null ? null : DECIMAL.exec(value.trim());
  if (!match) return null;
  if (/^0*$/.test(match[2] + (match[3] ?? ""))) return 0;
  return match[1] === "-" ? -1 : 1;
}
