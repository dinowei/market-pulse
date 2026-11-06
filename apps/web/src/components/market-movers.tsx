"use client";

import Link from "next/link";
import { useState } from "react";

import type { components } from "../generated/api";
import { formatAmount, percentCue, shortReason } from "../lib/panorama";
import { useCachedApi } from "../lib/use-cached-api";
import { DataStateBadge } from "./data-table";
import styles from "./private-pages.module.css";

type Movers = components["schemas"]["MarketMoversResponse"];
type Mover = components["schemas"]["MarketMover"];
type Market = Movers["market"];

const volume = new Intl.NumberFormat("pt-BR", { notation: "compact", maximumFractionDigits: 1 });

function MoverList({ title, items }: { title: string; items: readonly Mover[] }) {
  return (
    <section>
      <h3>{title}</h3>
      {items.length === 0 ? <p className="muted">Nenhum ativo nesta lista.</p> : (
        <ul className={styles.counts}>{items.map((item) => {
          const cue = percentCue(item.change_percent ?? null);
          return <li key={item.symbol}>
            <span>{item.canonical_id ? <Link href={`/assets?id=${encodeURIComponent(item.canonical_id)}`}>{item.symbol}</Link> : item.symbol} <small>{item.price == null ? "" : `${item.currency} ${formatAmount(item.price)}`}{item.volume == null ? "" : ` · vol. ${volume.format(Number(item.volume))}`}</small></span>
            <strong className={cue ? `direction-${cue.direction.toLowerCase()}` : ""}>{cue?.text ?? "—"}</strong>
          </li>;
        })}</ul>
      )}
    </section>
  );
}

export function MarketMovers() {
  const [market, setMarket] = useState<Market>("BR");
  const { data, failed } = useCachedApi<Movers>(`/api/v1/market-data/movers?market=${market}`, 10 * 60_000);
  const current = data?.market === market ? data : undefined;
  return (
    <section className={styles.glass} aria-labelledby="movers-title">
      <div className="section-heading">
        <h2 id="movers-title">Maiores variações do dia</h2>
        <div className={styles.pills} role="group" aria-label="Mercado do ranking">
          {(["BR", "US"] as const).map((item) => <button key={item} type="button" aria-pressed={market === item} onClick={() => setMarket(item)}>{item === "BR" ? "B3" : "EUA"}</button>)}
          {current && current.provider !== "none" && <DataStateBadge dataLevel={current.data_level} freshness={current.freshness} />}
        </div>
      </div>
      {failed && !current && <p className="state-note" role="alert">Não foi possível carregar o ranking.</p>}
      {!failed && !current && <p className="loading-state">Carregando o ranking…</p>}
      {current?.unavailable_reason && (current.unavailable_reason === "SESSION_REQUIRED"
        ? <p className="muted"><Link href="/login">Entre</Link> para ver as maiores variações reais.</p>
        : <p className="muted">Ranking indisponível: {shortReason(current.unavailable_reason)}</p>)}
      {current && !current.unavailable_reason && <>
        <div className={styles.tools}>
          <MoverList title="Maiores altas" items={current.gainers} />
          <MoverList title="Maiores quedas" items={current.losers} />
          <MoverList title="Mais negociados" items={current.most_active} />
        </div>
        <p className={styles.note}>Fonte: {current.provider}{current.session_date ? `, pregão de ${current.session_date.split("-").reverse().join("/")}` : ""}. {current.limitations.join(" ")}</p>
      </>}
    </section>
  );
}
