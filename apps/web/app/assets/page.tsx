import { Suspense } from "react";

import { AssetFromQuery } from "../../src/components/asset-detail";

export default function AssetPage() {
  return <main id="main-content" className="standalone-page asset-page"><Suspense fallback={<><h1 className="sr-only">Página de ativo</h1><p className="loading-state">Carregando ativo…</p></>}><AssetFromQuery /></Suspense></main>;
}
