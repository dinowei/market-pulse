"use client";

import { classLabel, UNAVAILABLE_CLASSES } from "../lib/asset-classes";

export function AssetClassFilter({ classes, value, onChange }: { classes: string[]; value: string | null; onChange: (value: string | null) => void }) {
  return (
    <fieldset className="control-group class-filter">
      <legend>Classe de ativo</legend>
      <div className="control-row">
        <button type="button" className={value === null ? "control active" : "control"} aria-pressed={value === null} onClick={() => onChange(null)}>Todas</button>
        {classes.map((type) => <button type="button" key={type} className={value === type ? "control active" : "control"} aria-pressed={value === type} onClick={() => onChange(type)}>{classLabel(type)}</button>)}
      </div>
      <ul className="class-unavailable">
        {UNAVAILABLE_CLASSES.map((item) => <li key={item.label}><strong>{item.label}</strong>: indisponível — {item.reason}.</li>)}
      </ul>
    </fieldset>
  );
}
