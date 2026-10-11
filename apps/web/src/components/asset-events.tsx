"use client";

import { useEffect, useState } from "react";

import type { components } from "../generated/api";
import { apiRequest, isAbort } from "../lib/api-client";

type CorporateActions = components["schemas"]["InstrumentCorporateActionsResponse"];

const ACTION_LABEL: Record<string, string> = {
  CASH_DIVIDEND: "Dividendo",
  JCP: "Juros sobre capital próprio",
  SPLIT: "Desdobramento",
  REVERSE_SPLIT: "Grupamento",
};

// Proventos and corporate events exactly as the API returns them: UNAVAILABLE is shown
// with its reason, never as "no events".
export function AssetEvents({ canonicalId }: { canonicalId: string }) {
  const [state, setState] = useState<{ id: string; data?: CorporateActions; error?: string }>({ id: "" });

  useEffect(() => {
    const controller = new AbortController();
    apiRequest<CorporateActions>(`/api/v1/market-data/corporate-actions/${encodeURIComponent(canonicalId)}`, { signal: controller.signal })
      .then((data) => setState({ id: canonicalId, data }))
      .catch((error: unknown) => { if (!isAbort(error)) setState({ id: canonicalId, error: (error as Error).message }); });
    return () => controller.abort();
  }, [canonicalId]);

  const current = state.id === canonicalId ? state : undefined;
  const data = current?.data;
  return (
    <section className="asset-events" aria-labelledby="asset-events-title">
      <div className="section-heading"><p className="eyebrow">PROVENTOS E EVENTOS</p><h2 id="asset-events-title">Proventos e eventos corporativos</h2></div>
      {!current && <p className="loading-state">Carregando eventos…</p>}
      {current?.error && <p className="state-note" role="alert">Eventos indisponíveis: {current.error}</p>}
      {data?.availability === "UNAVAILABLE" && <p className="muted">Indisponível ({data.unavailable_reason}). {data.limitations.join(" ")}</p>}
      {data?.availability === "AVAILABLE" && data.items.length === 0 && <p className="muted">Nenhum evento no dataset aprovado para este ativo.</p>}
      {data?.availability === "AVAILABLE" && data.items.length > 0 && (
        <div className="table-wrap"><table><caption>Proventos e eventos corporativos do ativo, com origem</caption>
          <thead><tr><th scope="col">Evento</th><th scope="col">Data ex</th><th scope="col">Pagamento ou vigência</th><th scope="col">Valor por ação ou proporção</th><th scope="col">Situação</th><th scope="col">Origem</th></tr></thead>
          <tbody>{data.items.map((item, index) => (
            <tr key={`${item.action_type}-${item.ex_date ?? index}`}>
              <th scope="row">{ACTION_LABEL[item.action_type] ?? item.action_type}<br /><small>{item.action_type}</small></th>
              <td>{item.ex_date ?? "—"}</td>
              <td>{item.payment_date ?? item.effective_date ?? "—"}</td>
              <td>{item.split_ratio_from && item.split_ratio_to ? `${item.split_ratio_from} : ${item.split_ratio_to}` : item.gross_amount_per_share ? `${item.currency ?? ""} ${item.gross_amount_per_share} bruto${item.net_amount_per_share ? ` · ${item.net_amount_per_share} líquido` : ""}` : "—"}</td>
              <td>{item.status}</td>
              <td>{item.provenance.dataset}<br /><small>{item.provenance.data_level} · {item.provenance.freshness} · {item.provenance.source_timestamp}</small></td>
            </tr>
          ))}</tbody>
        </table></div>
      )}
      {data && data.limitations.length > 0 && data.availability === "AVAILABLE" && <p className="limitation-note">Limitações: {data.limitations.join("; ")}</p>}
    </section>
  );
}
