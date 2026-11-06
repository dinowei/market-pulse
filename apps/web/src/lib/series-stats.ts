// Descriptive statistics of a closed window of daily closes. They describe the past only; the
// page states the window and the method next to every number.
export type SeriesStats = { returnPercent: number; min: number; max: number; volatility: number | null };

const MIN_RETURNS_FOR_VOLATILITY = 20;

/** Annualized by the market's calendar: crypto trades every day, the others about 252 days. */
export function annualizationDays(canonicalId: string): number {
  return canonicalId.startsWith("crypto.") ? 365 : 252;
}

export function seriesStats(closes: readonly number[], yearDays = 252): SeriesStats | null {
  if (closes.length < 2 || closes.some((close) => !(close > 0))) return null;
  const returns = closes.slice(1).map((close, index) => Math.log(close / closes[index]));
  const mean = returns.reduce((sum, value) => sum + value, 0) / returns.length;
  const variance = returns.reduce((sum, value) => sum + (value - mean) ** 2, 0) / (returns.length - 1 || 1);
  return {
    returnPercent: (closes[closes.length - 1] / closes[0] - 1) * 100,
    min: Math.min(...closes),
    max: Math.max(...closes),
    volatility: returns.length >= MIN_RETURNS_FOR_VOLATILITY ? Math.sqrt(variance * yearDays) * 100 : null,
  };
}

const CLASS_LABEL: Record<string, string> = { equity: "Ações", etf: "ETFs", fii: "FIIs", bdr: "BDRs", crypto: "Cripto", commodity: "Commodities", fx: "Câmbio" };

/** The class is the first segment of the canonical id; an unknown one keeps that segment. */
export function assetClassLabel(canonicalId: string): string {
  const prefix = canonicalId.split(".")[0];
  return CLASS_LABEL[prefix] ?? prefix;
}

export function symbolOf(canonicalId: string): string {
  return (canonicalId.split(".").pop() ?? canonicalId).toUpperCase();
}

export type AllocationSlice = { label: string; percent: number; percentText: string; start: number };

/** Weight per class from what the valuation states; an unpriced position is reported, not guessed. */
export function allocation(positions: readonly { canonical_id: string; market_value_base?: string | null }[], cash: string | null | undefined): { slices: AllocationSlice[]; unpriced: number } {
  const totals = new Map<string, number>();
  let unpriced = 0;
  for (const position of positions) {
    if (position.market_value_base == null) { unpriced += 1; continue; }
    const label = assetClassLabel(position.canonical_id);
    totals.set(label, (totals.get(label) ?? 0) + Number(position.market_value_base));
  }
  if (cash != null && Number(cash) > 0) totals.set("Caixa", Number(cash));
  const sum = [...totals.values()].reduce((total, value) => total + value, 0);
  let start = 0;
  const slices = [...totals].filter(([, value]) => value > 0).sort((a, b) => b[1] - a[1]).map(([label, value]) => {
    const percent = (value / sum) * 100;
    const slice = { label, percent, percentText: `${percent.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`, start };
    start += percent;
    return slice;
  });
  return { slices, unpriced };
}
