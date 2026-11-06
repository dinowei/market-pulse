"use client";

import dynamic from "next/dynamic";

const MarketHeatmap = dynamic(() => import("../../src/components/market-heatmap").then((module) => module.MarketHeatmap), {
  ssr: false,
  loading: () => <p className="muted">Carregando o mapa…</p>,
});

export default function HeatmapPage() {
  return <main id="main-content" className="standalone-page"><h1 className="sr-only">Heatmap de mercado</h1><MarketHeatmap /></main>;
}
