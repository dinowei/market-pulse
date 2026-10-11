// Asset classes as the catalog reports them (`instrument_type`). Classes the plan mentions
// but the catalog cannot serve are listed separately, always as unavailable with a reason,
// never as a working filter (NotebookLM "Páginas por classe de ativo"; spec scope).

const LABELS: Record<string, string> = {
  EQUITY: "Ações",
  ETF: "ETFs",
  FII: "FIIs",
  BDR: "BDRs",
  INDEX: "Índices",
  CRYPTO: "Cripto",
};
const ORDER = Object.keys(LABELS);

export const UNAVAILABLE_CLASSES = [
  { label: "Fundos", reason: "fundos tradicionais ficam bloqueados até licença e cobertura aprovadas" },
  { label: "Renda fixa", reason: "nenhum dataset aprovado de renda fixa no catálogo" },
] as const;

export function classLabel(instrumentType: string): string {
  return LABELS[instrumentType.toUpperCase()] ?? instrumentType;
}

/** Distinct classes present in the data, in a stable order; unknown types come last. */
export function presentClasses(instrumentTypes: string[]): string[] {
  const present = [...new Set(instrumentTypes.map((type) => type.toUpperCase()))];
  const rank = (type: string) => (ORDER.includes(type) ? ORDER.indexOf(type) : ORDER.length);
  return present.sort((a, b) => rank(a) - rank(b) || a.localeCompare(b));
}
