"use client";

import dynamic from "next/dynamic";
import { OnView } from "./on-view";

// The report and its CSS load after the page, so first-load CSS stays in budget.
const WorldReport = dynamic(() => import("./world-report").then((module) => module.WorldReport), {
  ssr: false,
  loading: () => <p className="muted">Carregando o relatório…</p>,
});
const MarketWorkspace = dynamic(() => import("./market-data").then((module) => module.MarketWorkspace), {
  ssr: false,
  loading: () => <p className="muted">Carregando o gráfico…</p>,
});

export function WorldReportPage() {
  return (
    <main id="main-content" className="page home-page">
      <h1 className="sr-only">Como o mundo fechou</h1>
      <WorldReport />
      <OnView label="Gráfico e análise logo abaixo."><MarketWorkspace /></OnView>
    </main>
  );
}
