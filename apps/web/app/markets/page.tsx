import { Suspense } from "react";

import { MarketsFromQuery } from "../../src/components/markets-hub";

export default function MarketsPage() {
  return <main id="main-content" className="standalone-page markets-page"><Suspense fallback={<><h1 className="sr-only">Mercados</h1><p className="loading-state">Carregando mercados…</p></>}><MarketsFromQuery /></Suspense></main>;
}
