"use client";

import Link from "next/link";
import { useState } from "react";

import type { components } from "../generated/api";
import { formatAmount, shortReason } from "../lib/panorama";
import { useCachedApi } from "../lib/use-cached-api";

type Profile = components["schemas"]["AssetProfileResponse"];
type Fact = components["schemas"]["AssetFact"];

// Everything the sources say about the asset (ADR-032), grouped and with the source of each fact.
const GROUP_ORDER = ["Faixa de preço", "Tamanho e negociação", "Indicadores da fonte", "Empresa"];
const compact = new Intl.NumberFormat("pt-BR", { notation: "compact", maximumFractionDigits: 2 });
const whole = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const decimal = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
const formatDay = (day: string) => day.split("-").reverse().join("/");

const TONE = { positive: "tom positivo na fonte", negative: "tom negativo na fonte", neutral: "tom neutro na fonte" } as const;

export function Logo({ src }: { src: string }) {
  const [failed, setFailed] = useState(false);
  if (failed) return null;
  // eslint-disable-next-line @next/next/no-img-element -- small logo from the source; no referrer is sent
  return <img className="asset-logo" src={src} alt="" width={32} height={32} loading="lazy" referrerPolicy="no-referrer" onError={() => setFailed(true)} />;
}

function factText(fact: Fact, currency: string): string {
  const number = Number(fact.value);
  switch (fact.kind) {
    case "MONEY": return `${currency} ${Math.abs(number) >= 1e6 ? compact.format(number) : decimal.format(number)}`;
    case "INTEGER": return Math.abs(number) >= 1e6 ? compact.format(number) : whole.format(number);
    case "NUMBER": return decimal.format(number);
    case "PERCENT": return `${decimal.format(number)}%`;
    case "DATE": return formatDay(fact.value);
    default: return fact.value;
  }
}

export function AssetFacts({ canonicalId, currency }: { canonicalId: string; currency: string }) {
  const { data, failed } = useCachedApi<Profile>(`/api/v1/market-data/profile/${encodeURIComponent(canonicalId)}`, 10 * 60_000);
  if (failed) return null;
  if (!data) return <p className="muted">Carregando os dados das fontes…</p>;
  if (data.unavailable_reason === "SESSION_REQUIRED") return <p className="muted"><Link href="/login">Entre</Link> para ver os dados completos deste ativo.</p>;
  if (data.unavailable_reason) return <p className="muted">Dados complementares indisponíveis: {shortReason(data.unavailable_reason)}</p>;
  const groups = GROUP_ORDER.map((name) => [name, data.facts.filter((fact) => fact.group === name)] as const).filter(([, facts]) => facts.length > 0);
  return (
    <section className="asset-page-panel asset-facts" aria-labelledby="asset-facts-title">
      <h2 id="asset-facts-title" className="asset-facts-title">{data.logo_url && <Logo src={data.logo_url} />}Dados das fontes</h2>
      {groups.map(([name, facts]) => (
        <div key={name}>
          <h3>{name}</h3>
          <dl className="meta-grid compact">{facts.map((fact) => <div key={`${fact.source}-${fact.key}`}><dt>{fact.label}</dt><dd>{factText(fact, currency)} <small>{fact.source}</small></dd></div>)}</dl>
        </div>
      ))}
      {data.summary && <details><summary>Sobre a empresa <small>(fonte: {data.summary_source}, no idioma original)</small></summary><p>{data.summary}</p>{data.website && <p><a href={data.website} target="_blank" rel="noopener noreferrer">Site da empresa</a></p>}</details>}
      {data.dividends.length > 0 && (
        <details>
          <summary>Proventos declarados pela fonte ({data.dividends.length})</summary>
          <div className="table-wrap"><table>
            <caption className="sr-only">Proventos por ação informados pela fonte</caption>
            <thead><tr><th scope="col">Tipo</th><th scope="col">Por ação</th><th scope="col">Data ex</th><th scope="col">Pagamento</th><th scope="col">Fonte</th></tr></thead>
            <tbody>{data.dividends.map((item) => <tr key={`${item.label}-${item.ex_date}-${item.amount}`}><th scope="row">{item.label}</th><td>{item.currency} {formatAmount(item.amount)}</td><td>{item.ex_date ? formatDay(item.ex_date) : "—"}</td><td>{item.pay_date ? formatDay(item.pay_date) : "—"}</td><td>{item.source}</td></tr>)}</tbody>
          </table></div>
        </details>
      )}
      {data.news.length > 0 && (
        <div>
          <h3>Notícias recentes</h3>
          <ul className="asset-news">{data.news.map((item) => <li key={item.url}><a href={item.url} target="_blank" rel="noopener noreferrer">{item.title}</a> <small>{item.publisher}{item.sentiment && ` · ${TONE[item.sentiment]}`}</small>{item.description && <p>{item.description}</p>}</li>)}</ul>
        </div>
      )}
      <ul className="limitation-note">{data.limitations.map((text) => <li key={text}>{text}</li>)}</ul>
    </section>
  );
}
