import { Suspense } from "react";

import { CompareFromQuery } from "../../src/components/multi-asset-comparison";

export default function ComparePage() {
  return <main id="main-content" className="standalone-page"><h1 className="sr-only">Comparação de ativos</h1><Suspense fallback={<p className="loading-state">Carregando séries…</p>}><CompareFromQuery /></Suspense></main>;
}
