"use client";

import dynamic from "next/dynamic";

// The report and its CSS load after the page, so first-load CSS stays in budget.
const WorldReport = dynamic(() => import("./world-report").then((module) => module.WorldReport), {
  ssr: false,
  loading: () => <p className="muted">Carregando o relatório…</p>,
});
const RegionsView = dynamic(() => import("./world-report").then((module) => module.RegionsView), {
  ssr: false,
  loading: () => <p className="muted">Carregando as regiões…</p>,
});

export function WorldReportPage() {
  return (
    <main id="main-content" className="page">
      <h1 className="sr-only">Como o mundo fechou</h1>
      <WorldReport />
    </main>
  );
}

export function RegionsPage() {
  return (
    <main id="main-content" className="page">
      <RegionsView />
    </main>
  );
}
