import { DIRECTION_CUE, type PriceDirection, priceDirection } from "./price-direction";

export type Source = { id: string; kind: "instrument" | "benchmark" };
const instrument = (id: string): Source => ({ id, kind: "instrument" });
const benchmark = (id: string): Source => ({ id, kind: "benchmark" });

// Markets overview by family (ADR-029). Each card shows exactly what the API serves for that
// id: a quote or a benchmark, plus its daily closes for the line. Nothing is filled in: a
// card without data names the reason, and the same holds for a missing line.
export const PANORAMA_GROUPS = [
  { id: "br", title: "Brasil", entries: [benchmark("index.br.b3.ibovespa"), instrument("equity.br.b3.petr4"), instrument("equity.br.b3.vale3"), instrument("equity.br.b3.itub4"), instrument("equity.br.b3.wege3"), instrument("etf.br.b3.bova11"), instrument("fii.br.b3.mxrf11")] },
  { id: "us", title: "Estados Unidos", entries: [instrument("etf.us.nysearca.spy"), instrument("equity.us.nasdaq.aapl"), instrument("equity.us.nasdaq.msft"), instrument("equity.us.nasdaq.nvda")] },
  { id: "fx", title: "Câmbio", entries: [instrument("fx.global.usd-brl"), instrument("fx.global.eur-usd")] },
  { id: "crypto", title: "Cripto", entries: [instrument("crypto.global.btc-usd"), instrument("crypto.global.eth-usd")] },
  { id: "commodities", title: "Commodities", entries: [instrument("commodity.global.xau-usd")] },
  { id: "rates", title: "Juros e inflação", entries: [benchmark("rate.br.cdi"), benchmark("index.br.ipca")] },
] as const satisfies readonly { id: string; title: string; entries: readonly Source[] }[];

export function formatAmount(value: string | null): string {
  if (value == null) return "—";
  const number = Number(value);
  if (!Number.isFinite(number)) return value;
  const digits = Math.abs(number) >= 1000 ? 2 : Math.abs(number) >= 1 ? 4 : 6;
  return number.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: digits });
}

/** Rounded percent with sign, glyph and word, or null when the change is unknown. */
export function percentCue(percent: string | null): { direction: PriceDirection; text: string } | null {
  const direction = priceDirection(percent);
  if (!direction || percent == null) return null;
  const rounded = Math.abs(Number(percent)).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const sign = direction === "UP" ? "+" : direction === "DOWN" ? "−" : "";
  return { direction, text: `${DIRECTION_CUE[direction].glyph} ${sign}${rounded}% ${DIRECTION_CUE[direction].word}` };
}

/** Direction and change of the window, from its first and last close (same source). */
export function windowChange(closes: readonly number[]): { direction: PriceDirection; percent: string } | null {
  if (closes.length < 2 || closes[0] <= 0) return null;
  const change = closes[closes.length - 1] - closes[0];
  const direction: PriceDirection = change > 0 ? "UP" : change < 0 ? "DOWN" : "FLAT";
  return { direction, percent: ((change / closes[0]) * 100).toFixed(2) };
}

// Short words for a card; the code stays visible next to them (unknown codes as they came).
const SHORT_REASONS: Record<string, string> = {
  LICENSE_BLOCKED: "fora do plano ou da licença",
  SESSION_REQUIRED: "entre para ver",
  DATASET_NOT_APPROVED: "sem fonte aprovada",
  PROVIDER_NOT_CONFIGURED: "fonte não configurada",
  RATE_LIMITED: "limite da fonte, volta em instantes",
  SOURCE_ERROR: "a fonte não respondeu",
  SOURCE_UNAVAILABLE: "a fonte não respondeu",
  UNAVAILABLE: "indisponível agora",
};

export function shortReason(code: string | null | undefined): string {
  if (!code) return "indisponível";
  return SHORT_REASONS[code] ? `${SHORT_REASONS[code]} (${code})` : code;
}

/** A readable label while the catalog has not answered: the last part of the id. */
export function fallbackLabel(id: string): string {
  return (id.split(".").pop() ?? id).toUpperCase();
}
