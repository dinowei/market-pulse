import type { components } from "../generated/api";
import { MAX_COMPARED_SERIES } from "./comparison-defaults";
import { priceDirection, type PriceDirection } from "./price-direction";

type InstrumentSummary = components["schemas"]["InstrumentSummary"];
type BenchmarkItem = components["schemas"]["BenchmarkItem"];
type PublicQuote = components["schemas"]["PublicQuote"];
type DataLevel = components["schemas"]["DataLevel"];
type Freshness = components["schemas"]["Freshness"];

// Markets hub (ADR-023): one tab per logical market family. Rows come only from
// /instruments + /market-data/quotes/batch and /market-data/benchmarks. Families with no
// approved dataset are named with the reason and never receive a value.
export type MarketTabId =
  | "overview" | "acoes-br" | "acoes-int" | "indices" | "juros-inflacao" | "cambio"
  | "fiis" | "etfs-bdrs" | "cripto" | "tesouro" | "credito-privado" | "fundos" | "outros";

export type UnavailableFamily = { reason: string; items: readonly { label: string; detail: string }[] };

export type MarketTab = { id: MarketTabId; label: string; short: string; description: string; unavailable?: UnavailableFamily };

export const MARKET_TABS: readonly MarketTab[] = [
  { id: "overview", label: "Visão geral", short: "Geral", description: "Todas as famílias de mercado, com o estado de cada uma." },
  { id: "acoes-br", label: "Ações Brasil", short: "Ações BR", description: "Ações listadas na B3 presentes no catálogo." },
  { id: "acoes-int", label: "Ações internacionais", short: "Ações int.", description: "Ações listadas fora do Brasil presentes no catálogo." },
  { id: "indices", label: "Índices", short: "Índices", description: "Índices de referência e índices do catálogo." },
  { id: "juros-inflacao", label: "Juros e inflação", short: "Juros", description: "Taxas e índices de preço usados como referência." },
  { id: "cambio", label: "Câmbio", short: "Câmbio", description: "Pares de moedas usados como referência." },
  { id: "fiis", label: "FIIs", short: "FIIs", description: "Fundos imobiliários listados presentes no catálogo." },
  { id: "etfs-bdrs", label: "ETFs e BDRs", short: "ETF/BDR", description: "ETFs e recibos de ações estrangeiras presentes no catálogo." },
  { id: "cripto", label: "Cripto", short: "Cripto", description: "Criptoativos presentes no catálogo." },
  {
    id: "tesouro", label: "Tesouro Direto", short: "Tesouro", description: "Títulos públicos federais.",
    unavailable: {
      reason: "Renda fixa pública não faz parte do escopo P0 e nenhum provider tem dataset aprovado na matriz de licenças. Nenhum preço, taxa ou PU é exibido.",
      items: [
        { label: "Tesouro Selic (LFT)", detail: "pós-fixado" },
        { label: "Tesouro Prefixado (LTN)", detail: "prefixado" },
        { label: "Tesouro IPCA+ (NTN-B)", detail: "indexado à inflação" },
      ],
    },
  },
  {
    id: "credito-privado", label: "Crédito privado", short: "Crédito", description: "Títulos bancários e corporativos.",
    unavailable: {
      reason: "Cada emissão tem emissor, prazo e taxa próprios, e nenhuma fonte desses títulos foi aprovada. Sem dataset licenciado, nenhum valor é exibido.",
      items: [
        { label: "CDB", detail: "emissão bancária" },
        { label: "LCI", detail: "emissão bancária, lastro imobiliário" },
        { label: "CRA", detail: "securitização do agronegócio" },
        { label: "Debêntures", detail: "dívida corporativa" },
      ],
    },
  },
  {
    id: "fundos", label: "Fundos", short: "Fundos", description: "Fundos de investimento tradicionais.",
    unavailable: {
      reason: "Fundos tradicionais (MUTUAL_FUND) estão bloqueados no catálogo até existir cobertura licenciada aprovada (P1).",
      items: [
        { label: "Fundos de renda fixa", detail: "cota diária" },
        { label: "Fundos multimercado", detail: "cota diária" },
        { label: "Fundos de ações", detail: "cota diária" },
      ],
    },
  },
  { id: "outros", label: "Outros", short: "Outros", description: "Instrumentos do catálogo sem família definida." },
];

const TAB_IDS = new Set<string>(MARKET_TABS.map((tab) => tab.id));

export function parseMarketTab(raw: string | null | undefined): MarketTabId {
  return raw && TAB_IDS.has(raw) ? (raw as MarketTabId) : "overview";
}

export function tabForInstrument(item: Pick<InstrumentSummary, "instrument_type" | "country">): MarketTabId {
  switch (item.instrument_type.toUpperCase()) {
    case "EQUITY": return item.country === "BR" ? "acoes-br" : "acoes-int";
    case "INDEX": return "indices";
    case "FII": return "fiis";
    case "ETF":
    case "BDR": return "etfs-bdrs";
    case "CRYPTO": return "cripto";
    case "MUTUAL_FUND": return "fundos";
    default: return "outros";
  }
}

// IPCA is published as an index but read as inflation, so the map is explicit first.
const BENCHMARK_TABS: Record<string, MarketTabId> = { "index.br.ipca": "juros-inflacao" };

export function tabForBenchmark(canonicalId: string): MarketTabId {
  if (BENCHMARK_TABS[canonicalId]) return BENCHMARK_TABS[canonicalId];
  if (canonicalId.startsWith("rate.")) return "juros-inflacao";
  if (canonicalId.startsWith("fx.")) return "cambio";
  if (canonicalId.startsWith("index.")) return "indices";
  return "outros";
}

export type MarketRow = {
  canonicalId: string;
  symbol: string;
  name: string;
  tab: MarketTabId;
  kind: "instrument" | "benchmark";
  currency: string;
  value: string | null;
  change: string | null;
  changePercent: string | null;
  dataLevel: DataLevel | null;
  freshness: Freshness | null;
  source: string | null;
  officialAt: string | null;
  reason: string | null;
  limitations: readonly string[];
  /** Catalog coverage in words (H-31); benchmarks are synthetic references. */
  coverage: string;
  /** H-30: the contract declares no unit for benchmark levels. */
  unitDeclared: boolean;
};

const SUPPORT_LABEL: Record<string, string> = {
  P0_OPERATIONAL: "Universo operacional",
  CANDIDATE_FUTURE: "Candidato",
  UNSUPPORTED: "Sem suporte de dados",
  BLOCKED_SCOPE: "Fora do escopo",
};

const DATA_SUPPORT_LABEL: Record<string, string> = {
  METADATA_ONLY: "só metadados",
  PROVIDER_PENDING: "provider pendente",
  LICENSE_PENDING: "licença pendente",
  DATA_AVAILABLE_APPROVED: "dado aprovado",
  UNAVAILABLE: "sem dado",
};

/** Unknown states are shown as they come, never mapped to a friendlier one. */
export function coverageLabel(item: Pick<InstrumentSummary, "support_state" | "data_support_status">): string {
  return `${SUPPORT_LABEL[item.support_state] ?? item.support_state} · ${DATA_SUPPORT_LABEL[item.data_support_status] ?? item.data_support_status}`;
}

export function rowFromInstrument(item: InstrumentSummary, quote: PublicQuote | undefined): MarketRow {
  return {
    canonicalId: item.canonical_id,
    symbol: item.display_symbol || item.symbol,
    name: item.name,
    tab: tabForInstrument(item),
    kind: "instrument",
    currency: quote?.currency ?? item.currency,
    value: quote?.price ?? null,
    change: quote?.change ?? null,
    changePercent: quote?.change_percent ?? null,
    dataLevel: quote?.data_level ?? null,
    freshness: quote?.freshness ?? null,
    // The API names a missing source "none"; that is the absence of a source, shown as "—".
    source: quote && quote.provider !== "none" ? `${quote.provider} · ${quote.dataset}` : null,
    officialAt: quote?.timestamp_official ?? null,
    reason: quote ? quote.unavailable_reason ?? null : "QUOTE_NOT_LOADED",
    limitations: quote?.limitations ?? [],
    coverage: coverageLabel(item),
    unitDeclared: true,
  };
}

export function rowFromBenchmark(item: BenchmarkItem): MarketRow {
  return {
    canonicalId: item.canonical_id,
    symbol: item.symbol,
    name: item.name,
    tab: tabForBenchmark(item.canonical_id),
    kind: "benchmark",
    currency: item.currency,
    value: item.value ?? null,
    change: null,
    changePercent: item.change_percent ?? null,
    dataLevel: item.data_level,
    freshness: item.freshness,
    source: `${item.source} · ${item.dataset}`,
    officialAt: item.timestamp_official ?? null,
    reason: item.unavailable_reason ?? null,
    limitations: item.limitations,
    coverage: "Referência sintética · DEMO",
    unitDeclared: false,
  };
}

/** UNAVAILABLE rows never carry a value, even if a payload ever did. */
export function displayValue(row: MarketRow): string | null {
  return row.freshness === "UNAVAILABLE" ? null : row.value;
}

export function rowDirection(row: MarketRow): PriceDirection | null {
  if (row.freshness === "UNAVAILABLE") return null;
  return priceDirection(row.change ?? row.changePercent);
}

export function groupByTab(rows: readonly MarketRow[]): Map<MarketTabId, MarketRow[]> {
  const groups = new Map<MarketTabId, MarketRow[]>();
  for (const row of rows) groups.set(row.tab, [...(groups.get(row.tab) ?? []), row]);
  return groups;
}

export function chunk<T>(items: readonly T[], size: number): T[][] {
  const out: T[][] = [];
  for (let index = 0; index < items.length; index += size) out.push(items.slice(index, index + size));
  return out;
}

export function compareHref(ids: readonly string[]): string {
  return `/compare?ids=${encodeURIComponent(ids.slice(0, MAX_COMPARED_SERIES).join(","))}`;
}

export type PulseSummary = Record<PriceDirection | "UNKNOWN", number> & { total: number };

export function pulseSummary(rows: readonly MarketRow[]): PulseSummary {
  const summary: PulseSummary = { UP: 0, DOWN: 0, FLAT: 0, UNKNOWN: 0, total: rows.length };
  for (const row of rows) summary[rowDirection(row) ?? "UNKNOWN"] += 1;
  return summary;
}

export function pulseSentence(summary: PulseSummary): string {
  if (summary.total === 0) return "Nenhuma série carregada.";
  const parts = [`${summary.UP} em alta`, `${summary.DOWN} em queda`, `${summary.FLAT} estáveis`, `${summary.UNKNOWN} sem variação conhecida`];
  return `${summary.total} séries: ${parts.join(", ")}.`;
}

// Particle field layout: one particle per row, one cluster per family that has rows.
// Positions are deterministic (sunflower spiral), sizes are equal: the art encodes only
// family membership and direction, never magnitude, price or a relation between rows.
export type PulseParticle = { key: string; tab: MarketTabId; x: number; y: number; dx: number; dy: number; direction: PriceDirection | null; order: number };
export type PulseCluster = { tab: MarketTabId; label: string; cx: number; cy: number; radius: number; count: number };

const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));

export function pulseLayout(rows: readonly MarketRow[], width = 320): { clusters: PulseCluster[]; particles: PulseParticle[]; width: number; height: number } {
  const groups = groupByTab(rows);
  const ordered = MARKET_TABS.filter((tab) => groups.has(tab.id));
  const step = width / Math.max(ordered.length, 1);
  const radius = Math.min(step * 0.4, 30);
  const cy = radius + 6;
  // Labels live in HTML under the drawing (equal columns), so text never scales with it.
  const height = 2 * cy;
  const clusters: PulseCluster[] = [];
  const particles: PulseParticle[] = [];
  let order = 0;
  ordered.forEach((tab, index) => {
    const members = groups.get(tab.id) ?? [];
    const cx = step * (index + 0.5);
    clusters.push({ tab: tab.id, label: tab.short, cx, cy, radius, count: members.length });
    members.forEach((row, position) => {
      const r = members.length === 1 ? 0 : radius * 0.78 * Math.sqrt((position + 0.5) / members.length);
      const angle = position * GOLDEN_ANGLE;
      const x = cx + r * Math.cos(angle);
      const y = cy + r * Math.sin(angle);
      particles.push({ key: row.canonicalId, tab: tab.id, x, y, dx: cx - x, dy: cy - y, direction: rowDirection(row), order: order++ });
    });
  });
  return { clusters, particles, width, height };
}

const UTC_FORMAT = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short", timeZone: "UTC" });

export function formatUtc(value: string | null): string {
  if (!value) return "Indisponível";
  const time = Date.parse(value);
  return Number.isFinite(time) ? `${UTC_FORMAT.format(time)} UTC` : "Indisponível";
}
