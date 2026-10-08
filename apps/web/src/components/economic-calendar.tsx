"use client";

import { useEffect, useState } from "react";

import type { components } from "../generated/api";
import { FINANCIAL_DISCLAIMER } from "../lib/disclaimers";

type EconomicCalendarResponse = components["schemas"]["EconomicCalendarResponse"];

export function EconomicCalendarPanel() {
  const [payload, setPayload] = useState<EconomicCalendarResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${apiBase}/api/v1/economic-calendar`, { headers: { Accept: "application/json" }, signal: controller.signal })
      .then(async (response) => { if (!response.ok) throw new Error(`HTTP ${response.status}`); return (await response.json()) as EconomicCalendarResponse; })
      .then(setPayload)
      .catch((reason: unknown) => { if (reason instanceof Error && reason.name !== "AbortError") setError(reason.message); });
    return () => controller.abort();
  }, [apiBase]);

  return <section className="calendar-panel" aria-labelledby="calendar-title">
    <div className="section-heading"><div><p className="eyebrow">AGENDA / EVENTOS</p><h2 id="calendar-title">Calendário econômico</h2></div><span className="state-label">DEMO · INFORMATIVO</span></div>
    {error && <p className="state-note" role="alert">Calendário indisponível: {error}</p>}
    {!error && !payload && <p className="loading-state">Carregando eventos…</p>}
    {payload && <div className="table-wrap"><table><caption>Eventos econômicos sintéticos, ordenados por data e hora</caption><thead><tr><th scope="col">Data / fuso</th><th scope="col">Evento</th><th scope="col">Importância</th><th scope="col">Valor</th><th scope="col">Estado e fonte</th></tr></thead><tbody>{payload.items.map((event) => <tr key={event.event_id}><th scope="row">{event.event_date}<br /><small>{event.timezone}</small></th><td><strong>{event.title}</strong><br /><small>{event.description}</small></td><td><span className={`importance importance-${event.importance.toLowerCase()}`}>{event.importance}</span></td><td>{event.actual ?? event.forecast ?? event.previous ?? "—"} {event.unit ?? ""}</td><td><span>{event.status} · {event.value_status}</span><br /><small>{event.provenance.source} · {event.provenance.data_level} · {event.provenance.freshness}</small><br /><small>{event.provenance.limitations.join("; ")}</small></td></tr>)}</tbody></table></div>}
    <p className="financial-disclaimer">{FINANCIAL_DISCLAIMER}</p>
  </section>;
}
