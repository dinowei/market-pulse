import type { components } from "../generated/api";

type DataLevel = components["schemas"]["DataLevel"];
type Freshness = components["schemas"]["Freshness"];
type PublicHistoryPoint = components["schemas"]["PublicHistoryPoint"];

const FRESHNESS_LABEL: Record<Freshness, string> = { FRESH: "atual", STALE: "antigo", UNAVAILABLE: "indisponível" };
const LEVEL_LABEL: Record<DataLevel, string> = { REAL_TIME: "Tempo real", DELAYED: "Com atraso", EOD: "Fim do dia", DEMO: "Demonstração" };

export function DataStateBadge({ dataLevel, freshness }: { dataLevel: DataLevel; freshness: Freshness }) {
  const label = dataLevel === "DEMO" ? "DADOS DE DEMONSTRAÇÃO" : freshness === "UNAVAILABLE" ? "Indisponível" : `${LEVEL_LABEL[dataLevel]}, ${FRESHNESS_LABEL[freshness]}`;
  return (
    <span className={`data-badge data-badge-${freshness.toLowerCase()}`} aria-label={`Estado ${freshness}, nível ${dataLevel}`}>
      <span aria-hidden="true" className="badge-mark" />
      {label}{dataLevel === "DEMO" && <span className="sr-only">DEMO · {freshness}</span>}
    </span>
  );
}

export function AccessibleDataTable({ points, reducedFrom, ohlc = false }: { points: PublicHistoryPoint[]; reducedFrom?: number; ohlc?: boolean }) {
  const caption = reducedFrom ? `Fallback tabular da série histórica (${points.length} de ${reducedFrom} pontos, redução M4 declarada)` : "Fallback tabular da série histórica";
  // With candles on screen, the equivalent table carries the same OHLC and volume.
  return (
    <div className="table-wrap"><table><caption>{caption}</caption><thead><tr><th scope="col">Sessão</th>{ohlc && <><th scope="col">Abertura</th><th scope="col">Máxima</th><th scope="col">Mínima</th></>}<th scope="col">Fechamento</th>{ohlc && <th scope="col">Volume</th>}<th scope="col">Índice 100</th><th scope="col">Gap</th></tr></thead><tbody>{points.map((point) => <tr key={`${point.timestamp}-${point.session_date}`}><th scope="row">{point.session_date}</th>{ohlc && <><td>{point.open ?? "—"}</td><td>{point.high ?? "—"}</td><td>{point.low ?? "—"}</td></>}<td>{point.close ?? "—"}</td>{ohlc && <td>{point.volume ?? "—"}</td>}<td>{point.index_100 ?? "—"}</td><td>{point.is_gap ? "Sim" : "Não"}</td></tr>)}</tbody></table></div>
  );
}
