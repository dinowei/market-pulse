import { Suspense } from "react";

import { PortfoliosFromQuery } from "../../src/components/portfolios";

export default function PortfoliosPage() {
  return <Suspense fallback={<main id="main-content" className="portfolios-page terminal-root"><h1 className="sr-only">Carteiras informativas</h1><p className="loading-state">Carregando carteiras…</p></main>}><PortfoliosFromQuery /></Suspense>;
}
