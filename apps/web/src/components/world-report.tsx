"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { components } from "../generated/api";
import { useCachedApi } from "../lib/use-cached-api";
import { formatAmount, percentCue, shortReason } from "../lib/panorama";
import { regionChange, worldHeadline } from "../lib/world-report";
import { DataStateBadge } from "./data-table";
import styles from "./world-report.module.css";

type WorldReportResponse = components["schemas"]["WorldReportResponse"];
type WorldRegion = components["schemas"]["WorldRegion"];

const formatDay = (day: string) => day.split("-").reverse().join("/");
const IMAGE_IDS = new Set(["brasil", "america-do-sul", "america-do-norte", "estados-unidos", "europa", "asia", "moedas"]);
const regionImage = (id: string) => `/market/${IMAGE_IDS.has(id) ? id : "hero"}.webp`;

// Lights the glass with the region's colors; the attribute only selects CSS tokens.
function setAmbient(id: string | null) {
  if (id) document.documentElement.dataset.ambient = id;
  else delete document.documentElement.dataset.ambient;
}

function useWorldReport() {
  const { data, failed, refresh } = useCachedApi<WorldReportResponse>("/api/v1/market-data/world-report", 5 * 60_000);
  // Headlines share a small per-minute quota: a first load may bring only some; ask once more.
  const incomplete = Boolean(data?.regions.some((region) => region.id !== "moedas" && region.news.length === 0));
  useEffect(() => {
    if (!incomplete) return undefined;
    const timer = setTimeout(refresh, 75_000);
    return () => clearTimeout(timer);
  }, [incomplete, refresh]);
  return { report: data ?? null, failed };
}

const FAILED = "Não foi possível carregar o relatório. A API pode estar iniciando; tente de novo em um minuto.";

function ChangeLine({ region }: { region: WorldRegion }) {
  const change = regionChange(region.change_percent);
  if (change) return <p className={`${styles.big} direction-${change.direction.toLowerCase()}`}><span aria-hidden="true">{change.glyph}</span> {change.value} <span className="sr-only">{change.word}</span></p>;
  return <p className={styles.noValue}>{region.members_with_data > 0 ? "Veja cada ativo" : `Sem valor: ${shortReason(region.unavailable_reason)}`}</p>;
}

function RegionCard({ region, open, onToggle }: { region: WorldRegion; open: boolean; onToggle: () => void }) {
  return (
    <li className={open ? `${styles.card} ${styles.open}` : styles.card} onMouseEnter={() => setAmbient(region.id)} onMouseLeave={() => setAmbient(null)} onFocus={() => setAmbient(region.id)} onBlur={() => setAmbient(null)}>
      {/* eslint-disable-next-line @next/next/no-img-element -- decorative, small local webp */}
      <img className={styles.photo} src={regionImage(region.id)} alt="" loading="lazy" />
      <div className={styles.cardBody}>
        <h3><button type="button" className={styles.cardLink} aria-expanded={open} aria-controls="region-detail" onClick={onToggle}>{region.title}</button></h3>
        <ChangeLine region={region} />
        <p className={styles.clamp}>{region.summary}</p>
        <p className={styles.basis}>{region.basis_label}</p>
      </div>
    </li>
  );
}

function Limits({ report }: { report: WorldReportResponse }) {
  return <ul className={styles.limits}>{report.limitations.map((text) => <li key={text}>{text}</li>)}</ul>;
}

function SessionNote({ report }: { report: WorldReportResponse }) {
  return report.regions.some((region) => region.unavailable_reason === "SESSION_REQUIRED") ? <p className={styles.note}><Link href="/login">Entre</Link> para ver os fechamentos reais.</p> : null;
}

export function WorldReport() {
  const { report, failed } = useWorldReport();
  const [openId, setOpenId] = useState<string | null>(null);
  if (failed) return <p className="state-note" role="alert">{FAILED}</p>;
  if (!report) return <p className="muted">Carregando o relatório…</p>;
  const openRegion = report.regions.find((region) => region.id === openId);
  const news = report.regions.flatMap((region) => region.news.map((item) => ({ ...item, region: region.id }))).slice(0, 3);
  // Currencies and crypto trade around the clock: the close of the day is the markets' close.
  const session = report.regions.filter((region) => region.id !== "moedas").map((region) => region.session_date).filter(Boolean).sort().at(-1);
  const currencies = report.regions.find((region) => region.id === "moedas")?.members.slice(0, 4) ?? [];
  return (
    <div className={styles.stage}>
      <div className={styles.top}>
        <div className={styles.rail}>
          <section className={styles.panel} aria-labelledby="highlights">
            <h2 id="highlights">Destaques do dia</h2>
            {news.length === 0 && <p className="muted">Nenhuma manchete disponível agora.</p>}
            <ul className={styles.rows}>
              {news.map((item) => (
                <li key={item.url} className={styles.newsRow}>
                  {/* eslint-disable-next-line @next/next/no-img-element -- decorative, small local webp */}
                  <img src={regionImage(item.region)} alt="" loading="lazy" />
                  <div><a href={item.url} target="_blank" rel="noopener noreferrer">{item.title}</a><small>{item.publisher}</small></div>
                </li>
              ))}
            </ul>
          </section>
          <section className={styles.panel} aria-labelledby="fx">
            <h2 id="fx">Câmbio e cripto</h2>
            {currencies.length === 0 && <p className="muted">Sem cotações disponíveis agora.</p>}
            <ul className={styles.rows}>
              {currencies.map((quote) => {
                const cue = quote.freshness === "UNAVAILABLE" ? null : percentCue(quote.change_percent ?? null);
                return (
                  <li key={quote.canonical_id} className={styles.quoteRow}>
                    <Link href={`/assets?id=${encodeURIComponent(quote.canonical_id)}`}>{quote.symbol}</Link>
                    <span>{quote.price == null ? "—" : `${formatAmount(quote.price)} ${quote.currency}`}<small className={cue ? `direction-${cue.direction.toLowerCase()}` : ""}>{cue?.text ?? "—"}</small></span>
                  </li>
                );
              })}
            </ul>
          </section>
        </div>
        <section className={styles.hero} aria-label="Resumo mundial">
          <p className={styles.chip}>Fechamento global{session ? `, pregão de ${formatDay(session)}` : ""}</p>
          <p className={styles.heroTitle}>Como o mundo fechou</p>
          <p className={styles.heroLine}>{worldHeadline(report.regions)}</p>
          <SessionNote report={report} />
          <div className={styles.actions}><a className={styles.primary} href="#regioes">Ver regiões</a><a className={styles.secondary} href="#analise">Abrir análise</a></div>
        </section>
      </div>
      <section aria-labelledby="regioes" className={styles.regions}>
        <h2 id="regioes">Como o mundo fechou por região</h2>
        <ul className={styles.grid}>{report.regions.map((region) => <RegionCard key={region.id} region={region} open={region.id === openId} onToggle={() => setOpenId(region.id === openId ? null : region.id)} />)}</ul>
        <div id="region-detail" aria-live="polite">{openRegion && <RegionDetail key={openRegion.id} region={openRegion} />}</div>
      </section>
      <Limits report={report} />
    </div>
  );
}

function RegionDetail({ region }: { region: WorldRegion }) {
  useEffect(() => {
    setAmbient(region.id);
    return () => setAmbient(null);
  }, [region.id]);
  return (
    <div className={styles.detail}>
      <section className={styles.detailHero} style={{ backgroundImage: `linear-gradient(to top, #0f1012 22%, rgba(15, 16, 18, .55)), url(${regionImage(region.id)})` }}>
        <h3 className={styles.detailTitle}>{region.title}</h3>
        <ChangeLine region={region} />
        <p className={styles.basisHero}>{region.basis_label}{region.session_date ? `, pregão de ${formatDay(region.session_date)}` : ""}</p>
        <p>{region.summary}</p>
      </section>
      <div className={styles.detailGrid}>
        <section className={styles.panel} aria-labelledby="region-assets">
          <h4 id="region-assets">Ativos acompanhados</h4>
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
        </section>
        <section className={styles.panel} aria-labelledby="region-news">
          <h4 id="region-news">Notícias do período</h4>
          {region.news.length === 0 && <p className="muted">Nenhuma manchete disponível para esta região.</p>}
          <ul className={styles.rows}>{region.news.map((item) => <li key={item.url} className={styles.plainNews}><a href={item.url} target="_blank" rel="noopener noreferrer">{item.title}</a><small>{item.publisher}</small>{item.description && <p className={styles.newsText}>{item.description}</p>}</li>)}</ul>
        </section>
      </div>
      <p><Link href={`/compare?ids=${encodeURIComponent(region.members.slice(0, 10).map((quote) => quote.canonical_id).join(","))}`}>Comparar os ativos de {region.title}</Link></p>
    </div>
  );
}
