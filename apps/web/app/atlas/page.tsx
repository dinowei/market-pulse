import { Suspense } from "react";

import { GlobalAtlas } from "../../src/components/global-atlas";
import { MarketsFromQuery } from "../../src/components/markets-hub";

export default function AtlasPage() {
  return <main id="main-content" className="standalone-page markets-page"><Suspense fallback={<><h1 className="sr-only">Ativos e mercados</h1><p className="loading-state">Carregando mercados…</p></>}><MarketsFromQuery /></Suspense><GlobalAtlas /></main>;
}
