"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { components } from "../generated/api";
import { apiRequest, isAbort } from "../lib/api-client";
import { PANORAMA_GROUPS, type Source, fallbackLabel, formatAmount, percentCue, shortReason, windowChange } from "../lib/panorama";
import type { PriceDirection } from "../lib/price-direction";
import { DataStateBadge } from "./data-table";
import styles from "./market-panorama.module.css";

type PublicQuote = components["schemas"]["PublicQuote"];
type PublicHistorySeries = components["schemas"]["PublicHistorySeries"];
type BenchmarkItem = components["schemas"]["BenchmarkItem"];
type BatchQuoteResponse = components["schemas"]["BatchQuoteResponse"];
type DataLevel = components["schemas"]["DataLevel"];
type Freshness = components["schemas"]["Freshness"];

const LINE_PERIOD = "3M";
const PARALLEL = 3;
const BATCH = 10;

type Card = {
  id: string;
  symbol: string;
  name: string;
  /** Currency of a quote; null for a benchmark, whose unit the contract does not declare (H-30). */
  unit: string | null;
  value: string | null;
  changePercent: string | null;
  dataLevel: DataLevel;
  freshness: Freshness;
  source: string;
  reason: string | null;
  href: string;
};

type Line = { closes: number[]; provider: string } | { reason: string | null };

function fromQuote(quote: PublicQuote, display?: string): Card {
  return {
    id: quote.canonical_id, symbol: display ?? quote.symbol, name: quote.name, unit: quote.currency,
    value: quote.price ?? null, changePercent: quote.change_percent ?? null, dataLevel: quote.data_level,
    freshness: quote.freshness, source: quote.provider, reason: quote.unavailable_reason ?? null,
    href: `/assets?id=${encodeURIComponent(quote.canonical_id)}`,
  };
}

function fromBenchmark(item: BenchmarkItem): Card {
  return {
    id: item.canonical_id, symbol: item.symbol, name: item.name, unit: null,
    value: item.value ?? null, changePercent: item.change_percent ?? null, dataLevel: item.data_level,
    freshness: item.freshness, source: item.source, reason: item.unavailable_reason ?? null,
    href: `/compare?ids=${encodeURIComponent(item.canonical_id)}`,
  };
}

/** Runs the jobs a few at a time, so a cold cache does not burst the providers' quotas. */
async function limited(jobs: (() => Promise<void>)[], width: number): Promise<void> {
  let next = 0;
  async function worker() {
    while (next < jobs.length) await jobs[next++]();
  }
  await Promise.all(Array.from({ length: Math.min(width, jobs.length) }, worker));
}

function Sparkline({ closes, direction }: { closes: readonly number[]; direction: PriceDirection }) {
  const width = 160;
  const height = 42;
  const min = Math.min(...closes);
  const span = Math.max(...closes) - min;
  const points = closes.map((close, index) => {
    const x = (index / (closes.length - 1)) * width;
    const y = span === 0 ? height / 2 : height - 3 - ((close - min) / span) * (height - 6);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  return <svg className={styles.spark} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" aria-hidden="true" focusable="false"><polyline className={styles[direction]} points={points} /></svg>;
}

function PanoramaCard({ card, line }: { card: Card; line?: Line }) {
  const cue = card.freshness === "UNAVAILABLE" ? null : percentCue(card.changePercent);
  const trend = line && "closes" in line ? windowChange(line.closes) : null;
  const trendCue = trend ? percentCue(trend.percent) : null;
  return (
    <li className={styles.card}>
      <div className={styles.top}>
        <Link className={styles.symbol} href={card.href} aria-label={`${card.symbol}, ${card.name}: abrir`}>{card.symbol}</Link>
        {cue && <span className={`${styles.change} direction-${cue.direction.toLowerCase()}`}>{cue.text}</span>}
      </div>
      <span className={styles.name} title={card.name}>{card.name}</span>
      {card.value == null
        ? <span className={styles.reason}>Sem valor: {shortReason(card.reason)}</span>
        : <span className={styles.value}>{formatAmount(card.value)}{card.unit && <small>{card.unit}</small>}</span>}
      {line && "closes" in line && trend
        ? <Sparkline closes={line.closes} direction={trend.direction} />
        : <p className={styles.empty}>{line === undefined ? "Carregando a linha…" : `Sem linha de ${LINE_PERIOD}: ${shortReason("reason" in line ? line.reason : null)}`}</p>}
      <div className={styles.meta}>
        {trendCue && <span>{LINE_PERIOD}: {trendCue.text}</span>}
        {card.source !== "none" && <span>Fonte: {card.source}</span>}
        <DataStateBadge dataLevel={card.dataLevel} freshness={card.freshness} />
      </div>
    </li>
  );
}

export function MarketPanorama({ benchmarks, benchmarksFailed, displays }: { benchmarks: readonly BenchmarkItem[]; benchmarksFailed: boolean; displays: Readonly<Record<string, string>> }) {
  const [quotes, setQuotes] = useState<Record<string, PublicQuote | { failed: string }>>({});
  const [lines, setLines] = useState<Record<string, Line>>({});

  useEffect(() => {
    const controller = new AbortController();
    const signal = controller.signal;
    const entries: Source[] = PANORAMA_GROUPS.flatMap((group) => [...group.entries]);
    const single = async (id: string) => {
      try {
        const quote = await apiRequest<PublicQuote>(`/api/v1/market-data/quotes/${encodeURIComponent(id)}`, { signal });
        setQuotes((current) => ({ ...current, [id]: quote }));
      } catch (error) {
        if (!isAbort(error)) setQuotes((current) => ({ ...current, [id]: { failed: (error as Error).message } }));
      }
    };
    // One batch per 10 ids (the endpoint's limit). A batch fails whole when one id is
    // unknown to this environment, so that chunk falls back to one request per id.
    const ids = entries.filter((entry) => entry.kind === "instrument").map((entry) => entry.id);
    const quoteJobs = Array.from({ length: Math.ceil(ids.length / BATCH) }, (_, index) => ids.slice(index * BATCH, (index + 1) * BATCH)).map((chunk) => async () => {
      try {
        const batch = await apiRequest<BatchQuoteResponse>("/api/v1/market-data/quotes/batch", { method: "POST", body: JSON.stringify({ canonical_ids: chunk }), signal });
        setQuotes((current) => ({ ...current, ...Object.fromEntries(batch.items.map((quote) => [quote.canonical_id, quote])) }));
      } catch (error) {
        if (!isAbort(error)) await limited(chunk.map((id) => () => single(id)), PARALLEL);
      }
    });
    const lineJobs = entries.map((entry) => async () => {
      try {
        const series = await apiRequest<PublicHistorySeries>(`/api/v1/market-data/history/${encodeURIComponent(entry.id)}?period=${LINE_PERIOD}&mode=PRICE&adjustment_type=UNADJUSTED`, { signal });
        const closes = series.points.map((point) => Number(point.close ?? point.value)).filter((value) => Number.isFinite(value) && value > 0);
        setLines((current) => ({ ...current, [entry.id]: closes.length >= 2 ? { closes, provider: series.provider } : { reason: series.unavailable_reason ?? null } }));
      } catch (error) {
        if (!isAbort(error)) setLines((current) => ({ ...current, [entry.id]: { reason: null } }));
      }
    });
    // Quotes first: the numbers matter more than the lines.
    limited(quoteJobs, PARALLEL).then(() => (signal.aborted ? undefined : limited(lineJobs, PARALLEL))).catch(() => undefined);
    return () => controller.abort();
  }, []);

  const benchmarkById = new Map(benchmarks.map((item) => [item.canonical_id, item]));
  return (
    <section className={styles.panorama} aria-labelledby="panorama-title">
      <div className={styles.head}>
        <h2 id="panorama-title">Mercados agora</h2>
        <p>Cotações e linhas de 3 meses com a fonte de cada uma. A variação ao lado do símbolo é a do dia; a de {LINE_PERIOD} vem dos fechamentos diários da linha.</p>
      </div>
      {PANORAMA_GROUPS.map((group) => (
        <div key={group.id} className={`${styles.group} ${styles[group.id]}`}>
          <h3>{group.title}</h3>
          <ul className={styles.grid}>
            {group.entries.map((entry) => {
              const item = entry.kind === "benchmark" ? benchmarkById.get(entry.id) : quotes[entry.id];
              const label = displays[entry.id] ?? fallbackLabel(entry.id);
              const missing = entry.kind === "benchmark" && !item && (benchmarksFailed || benchmarks.length > 0);
              if (!item && !missing) return <li key={entry.id} className={styles.card}><span className={styles.symbol}>{label}</span><p className={styles.empty}>Carregando a cotação…</p></li>;
              if (!item || "failed" in item) return <li key={entry.id} className={styles.card}><span className={styles.symbol}>{label}</span><p className={styles.reason}>A consulta falhou ou este ambiente não tem o ativo.</p></li>;
              const card = entry.kind === "benchmark" ? fromBenchmark(item as BenchmarkItem) : fromQuote(item as PublicQuote, displays[entry.id]);
              return <PanoramaCard key={entry.id} card={card} line={lines[entry.id]} />;
            })}
          </ul>
        </div>
      ))}
    </section>
  );
}
