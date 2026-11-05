"use client";

import dynamic from "next/dynamic";

// The report and its glass CSS load after the page, so first-load CSS stays in budget.
const WorldReport = dynamic(() => import("./world-report").then((module) => module.WorldReport), {
  ssr: false,
  loading: () => <p className="muted">Carregando o relatório…</p>,
});

export function WorldReportPage() {
  return (
    <main id="main-content" className="page">
      <h1>Como o mundo fechou</h1>
      <WorldReport />
    </main>
  );
}
