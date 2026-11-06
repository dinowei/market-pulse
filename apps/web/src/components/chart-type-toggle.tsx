import { CHART_KINDS, type CandleAvailability, type ChartKind } from "../lib/chart-geometry";

// Same control grammar as PeriodSelector/SeriesModeToggle. Candles stay disabled, with the
// reason in visible text, whenever the series lacks complete OHLC (ADR-023).
export function ChartTypeToggle({ value, onChange, availability }: { value: ChartKind; onChange: (kind: ChartKind) => void; availability: CandleAvailability }) {
  const effective: ChartKind = value === "candles" && !availability.available ? "line" : value;
  return (
    <fieldset className="control-group">
      <legend>Tipo de gráfico</legend>
      <div className="control-row">
        {CHART_KINDS.map((kind) => {
          const disabled = kind.id === "candles" && !availability.available;
          return <button type="button" key={kind.id} className={kind.id === effective ? "control active" : "control"} aria-pressed={kind.id === effective} disabled={disabled} aria-describedby={disabled ? "chart-kind-reason" : undefined} onClick={() => onChange(kind.id)}>{kind.label}</button>;
        })}
      </div>
      {!availability.available && <p id="chart-kind-reason" className="control-note">{availability.reason}</p>}
    </fieldset>
  );
}

export function effectiveChartKind(value: ChartKind, availability: CandleAvailability): ChartKind {
  return value === "candles" && availability.available ? "candles" : "line";
}
