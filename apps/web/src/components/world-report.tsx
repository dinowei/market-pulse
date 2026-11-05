"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { components } from "../generated/api";
import { apiRequest, isAbort } from "../lib/api-client";
import { formatAmount, percentCue, shortReason } from "../lib/panorama";
import { regionChange, worldHeadline } from "../lib/world-report";
import { DataStateBadge } from "./data-table";
import styles from "./world-report.module.css";

type WorldReportResponse = components["schemas"]["WorldReportResponse"];
type WorldRegion = components["schemas"]["WorldRegion"];

const formatDay = (day: string) => day.split("-").reverse().join("/");

function RegionSquare({ region }: { region: WorldRegion }) {
  const change = regionChange(region.change_percent);
  return (
    <li id={region.id} className={`${styles.square} ${change ? styles[change.direction] : ""}`}>
      <span className={styles.tag}>{region.title}</span>
      {change
        ? <p className={`${styles.big} direction-${change.direction.toLowerCase()}`}><span aria-hidden="true">{change.glyph}</span> {change.value} <small>{change.word}</small></p>
        : <p className={styles.noValue}>{region.members_with_data > 0 ? "Veja cada ativo" : `Sem valor: ${shortReason(region.unavailable_reason)}`}</p>}
      <p className={styles.basis}>{region.basis_label}{region.session_date ? `, pregão de ${formatDay(region.session_date)}` : ""}</p>
      <p className={styles.summary}>{region.summary}</p>
      {region.news.length > 0 && (
        <div className={styles.news}>
          <h3>Notícias do período</h3>
          <ul>{region.news.map((item) => <li key={item.url}><a href={item.url} target="_blank" rel="noopener noreferrer">{item.title}</a> <small>{item.publisher}</small></li>)}</ul>
        </div>
      )}
      <details className={styles.details}>
        <summary>Ver os {region.members.length} ativos</summary>
        <div className={styles.tableWrap}>
          <table>
            <caption className="sr-only">Ativos acompanhados em {region.title}</caption>
            <thead><tr><th scope="col">Ativo</th><th scope="col">Valor</th><th scope="col">Dia</th><th scope="col">Estado</th></tr></thead>
            <tbody>
              {region.members.map((quote) => {
                const cue = quote.freshness === "UNAVAILABLE" ? null : percentCue(quote.change_percent ?? null);
                return (
                  <tr key={quote.canonical_id}>
                    <th scope="row"><Link href={`/assets?id=${encodeURIComponent(quote.canonical_id)}`}>{quote.symbol}</Link></th>
                    <td>{quote.price == null ? "—" : `${formatAmount(quote.price)} ${quote.currency}`}</td>
                    <td className={cue ? `direction-${cue.direction.toLowerCase()}` : ""}>{cue?.text ?? "—"}</td>
                    <td><DataStateBadge dataLevel={quote.data_level} freshness={quote.freshness} /></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </details>
    </li>
  );
}

export function WorldReport() {
  const [report, setReport] = useState<WorldReportResponse | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    apiRequest<WorldReportResponse>("/api/v1/market-data/world-report", { signal: controller.signal })
      .then(setReport)
      .catch((error: unknown) => { if (!isAbort(error)) setFailed(true); });
    return () => controller.abort();
  }, []);

  if (failed) return <p className="state-note" role="alert">Não foi possível carregar o relatório. A API pode estar iniciando; tente de novo em um minuto.</p>;
  if (!report) return <p className="muted">Carregando o relatório…</p>;
  const needsSession = report.regions.some((region) => region.unavailable_reason === "SESSION_REQUIRED");
  return (
    <div className={styles.stage}>
      <section className={styles.hero} aria-label="Resumo mundial">
        <p className={styles.heroLine}>{worldHeadline(report.regions)}</p>
        {needsSession && <p><Link href="/login">Entre</Link> para ver os fechamentos reais.</p>}
        <ul className={styles.heroList}>
          {report.regions.map((region) => {
            const change = regionChange(region.change_percent);
            return <li key={region.id}><a href={`#${region.id}`}>{region.title}</a> <span className={change ? `direction-${change.direction.toLowerCase()}` : ""}>{change ? `${change.glyph} ${change.value}` : "—"}</span></li>;
          })}
        </ul>
      </section>
      <ul className={styles.grid}>{report.regions.map((region) => <RegionSquare key={region.id} region={region} />)}</ul>
      <ul className={styles.limits}>{report.limitations.map((text) => <li key={text}>{text}</li>)}</ul>
    </div>
  );
}
