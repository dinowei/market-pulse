"use client";

import { useMemo, useState } from "react";

import type { components } from "../generated/api";
import { FINANCIAL_DISCLAIMER } from "../lib/disclaimers";
import { useCachedApi } from "../lib/use-cached-api";
import styles from "./private-pages.module.css";

type EconomicCalendarResponse = components["schemas"]["EconomicCalendarResponse"];
type Event = components["schemas"]["EconomicCalendarEvent"];
type Importance = components["schemas"]["EconomicEventImportance"];

const IMPORTANCE: Record<Importance, string> = { HIGH: "Alto impacto", MEDIUM: "Médio impacto", LOW: "Baixo impacto" };
const STATUS: Record<Event["status"], string> = { SCHEDULED: "Agendado", RELEASED: "Divulgado", CANCELLED: "Cancelado", UNAVAILABLE: "Indisponível" };
const formatDay = (day: string) => day.split("-").reverse().join("/");

function surprise(event: Event): "ABOVE" | "BELOW" | "EQUAL" | null {
  if (event.actual == null || event.forecast == null) return null;
  const actual = Number(event.actual);
  const forecast = Number(event.forecast);
  if (!Number.isFinite(actual) || !Number.isFinite(forecast)) return null;
  return actual > forecast ? "ABOVE" : actual < forecast ? "BELOW" : "EQUAL";
}

function Value({ label, value, unit }: { label: string; value?: string | null; unit?: string | null }) {
  if (value == null) return null;
  return <li><span>{label}</span><strong>{value}{unit ? ` ${unit}` : ""}</strong></li>;
}

export function EconomicCalendarPanel() {
  const { data: payload, failed } = useCachedApi<EconomicCalendarResponse>("/api/v1/economic-calendar", 10 * 60_000);
  const [importance, setImportance] = useState<Importance | null>(null);
  const [country, setCountry] = useState<string | null>(null);
  const items = useMemo(() => payload?.items ?? [], [payload]);
  const countries = useMemo(() => [...new Set(items.map((event) => event.country))].sort(), [items]);
  const shown = items.filter((event) => (importance === null || event.importance === importance) && (country === null || event.country === country));
  const days = [...new Set(shown.map((event) => event.event_date))];
  const isDemo = items.some((event) => event.provenance.data_level === "DEMO");
  const count = (test: (event: Event) => boolean) => shown.filter(test).length;

  return <section className={styles.page} aria-labelledby="calendar-title">
    <div className={styles.hero}>
      <div>
        <span className={styles.chip}>{isDemo ? "DEMO · informativo" : "Informativo"}</span>
        <h2 id="calendar-title">Calendário econômico</h2>
        <p>Divulgações ordenadas por data, com a fonte e o fuso de cada evento.</p>
      </div>
      {payload && <ul className={styles.heroStats} aria-label="Período"><li>De<strong>{formatDay(payload.date_from)}</strong></li><li>Até<strong>{formatDay(payload.date_to)}</strong></li></ul>}
    </div>
    {failed && !payload && <p className="state-note" role="alert">Calendário indisponível. A API pode estar iniciando; tente de novo em um minuto.</p>}
    {!failed && !payload && <p className="loading-state">Carregando eventos…</p>}
    {isDemo && <p className="state-note">Eventos sintéticos de demonstração: nenhuma fonte aprovada de calendário econômico está ligada, então estas datas e valores não são reais.</p>}
    {payload && <>
      <div className={styles.pills} role="group" aria-label="Filtrar por impacto">
        <button type="button" aria-pressed={importance === null} onClick={() => setImportance(null)}>Todos os impactos</button>
        {(["HIGH", "MEDIUM", "LOW"] as const).map((level) => <button key={level} type="button" aria-pressed={importance === level} onClick={() => setImportance(importance === level ? null : level)}>{IMPORTANCE[level]}</button>)}
      </div>
      {countries.length > 1 && <div className={styles.pills} role="group" aria-label="Filtrar por país">
        <button type="button" aria-pressed={country === null} onClick={() => setCountry(null)}>Todos os países</button>
        {countries.map((item) => <button key={item} type="button" aria-pressed={country === item} onClick={() => setCountry(country === item ? null : item)}>{item}</button>)}
      </div>}
      <div className={styles.splitWide}>
        <div className={styles.glass}>
          {shown.length === 0 && <p className="muted">Nenhum evento com estes filtros.</p>}
          {days.map((day) => <section key={day} aria-labelledby={`day-${day}`}>
            <h3 id={`day-${day}`}>{formatDay(day)}</h3>
            <ul className={styles.events}>{shown.filter((event) => event.event_date === day).map((event) => <li key={event.event_id} className={styles.event}>
              <div className={styles.when}>{event.event_time?.slice(0, 5) ?? "—"}<small>{event.timezone}</small></div>
              <div>
                <div className={styles.eventTags}><strong>{event.country}</strong><span className={`importance importance-${event.importance.toLowerCase()}`}>{IMPORTANCE[event.importance]}</span><span>{STATUS[event.status]}</span></div>
                <h3>{event.title}</h3>
                <p>{event.description}</p>
                <p><small>{event.provenance.source} · {event.provenance.data_level} · {event.provenance.freshness}{event.provenance.limitations.length > 0 && ` · ${event.provenance.limitations.join("; ")}`}</small></p>
              </div>
              {event.actual == null && event.forecast == null && event.previous == null
                ? <span className={styles.tag}>{event.value_status === "PENDING" ? "Aguardando divulgação" : "Sem valor"}</span>
                : <ul className={styles.values}><Value label="Divulgado" value={event.actual} unit={event.unit} /><Value label="Projetado" value={event.forecast} unit={event.unit} /><Value label="Anterior" value={event.previous} unit={event.unit} /></ul>}
            </li>)}</ul>
          </section>)}
        </div>
        <aside className={styles.side}>
          <section className={styles.glass} aria-labelledby="calendar-counts">
            <h2 id="calendar-counts">Neste período</h2>
            <ul className={styles.counts}>
              <li>Agendados<strong>{count((event) => event.status === "SCHEDULED")}</strong></li>
              <li>Divulgados<strong>{count((event) => event.status === "RELEASED")}</strong></li>
              <li>Alto impacto<strong>{count((event) => event.importance === "HIGH")}</strong></li>
            </ul>
          </section>
          <section className={styles.glass} aria-labelledby="calendar-surprise">
            <h2 id="calendar-surprise">Divulgado contra projetado</h2>
            <ul className={styles.counts}>
              <li>Acima da projeção<strong>{count((event) => surprise(event) === "ABOVE")}</strong></li>
              <li>Abaixo da projeção<strong>{count((event) => surprise(event) === "BELOW")}</strong></li>
              <li>Igual à projeção<strong>{count((event) => surprise(event) === "EQUAL")}</strong></li>
            </ul>
            <p className={styles.note}>Contagem simples dos eventos com os dois valores. Não diz se o resultado é bom ou ruim.</p>
          </section>
        </aside>
      </div>
      <details className={styles.more}><summary>Ver todos os eventos em tabela</summary><div className="table-wrap"><table><caption>Eventos econômicos, ordenados por data e hora</caption><thead><tr><th scope="col">Data / fuso</th><th scope="col">Evento</th><th scope="col">Importância</th><th scope="col">Valor</th><th scope="col">Estado e fonte</th></tr></thead><tbody>{shown.map((event) => <tr key={event.event_id}><th scope="row">{event.event_date}<br /><small>{event.timezone}</small></th><td>{event.title}</td><td>{event.importance}</td><td>{event.actual ?? event.forecast ?? event.previous ?? "—"} {event.unit ?? ""}</td><td>{event.status} · {event.value_status}<br /><small>{event.provenance.source} · {event.provenance.data_level} · {event.provenance.freshness}</small></td></tr>)}</tbody></table></div></details>
    </>}
    <p className="financial-disclaimer">{FINANCIAL_DISCLAIMER}</p>
  </section>;
}
