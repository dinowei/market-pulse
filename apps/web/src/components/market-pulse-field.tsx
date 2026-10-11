import type { CSSProperties } from "react";

import { motionClass } from "../lib/atlas-motion";
import { pulseLayout, pulseSentence, pulseSummary, type MarketRow, type MarketTabId } from "../lib/markets";
import { DIRECTION_CUE, type PriceDirection } from "../lib/price-direction";

const WIDTH = 320;
const SIZE = 3.2;

// Each direction has its own shape (WCAG 1.4.1): triangle up, triangle down, bar, ring.
function glyphPath(x: number, y: number, direction: PriceDirection): string {
  if (direction === "UP") return `M ${x} ${y - SIZE} L ${x + SIZE} ${y + SIZE * 0.8} L ${x - SIZE} ${y + SIZE * 0.8} Z`;
  if (direction === "DOWN") return `M ${x} ${y + SIZE} L ${x + SIZE} ${y - SIZE * 0.8} L ${x - SIZE} ${y - SIZE * 0.8} Z`;
  return `M ${x - SIZE} ${y - 1} H ${x + SIZE} V ${y + 1} H ${x - SIZE} Z`;
}

// Particle Atlas "pulso do mercado" (P1 art, ADR-023): aggregate panorama derived only from
// the rows on the page. The SVG is decorative (aria-hidden); the caption states the same
// counts in text, and the table below is the source of truth. Motion plays once per
// refresh or tab change and then stops.
export function MarketPulseField({ rows, activeTab, refreshKey }: { rows: readonly MarketRow[]; activeTab: MarketTabId; refreshKey: number }) {
  const { clusters, particles, height } = pulseLayout(rows, WIDTH);
  const summary = pulseSummary(rows);
  return (
    <figure className={`pulse-field${motionClass()}`}>
      <svg key={`${refreshKey}-${activeTab}`} viewBox={`0 0 ${WIDTH} ${height}`} aria-hidden="true" focusable="false">
        {clusters.map((cluster) => {
          const active = activeTab === "overview" || activeTab === cluster.tab;
          return <g key={cluster.tab} className={active ? "pulse-cluster active" : "pulse-cluster"}>
            <circle cx={cluster.cx} cy={cluster.cy} r={cluster.radius} className="pulse-orbit" />
            <text x={cluster.cx} y={cluster.labelY} textAnchor="middle" className="pulse-label">{cluster.label}</text>
          </g>;
        })}
        {particles.map((particle) => {
          const active = activeTab === "overview" || activeTab === particle.tab;
          const style = { "--dx": `${particle.dx}px`, "--dy": `${particle.dy}px`, "--i": particle.order } as CSSProperties;
          const tone = particle.direction ? particle.direction.toLowerCase() : "unknown";
          return particle.direction
            ? <path key={particle.key} d={glyphPath(particle.x, particle.y, particle.direction)} className={`pulse-particle pulse-${tone}${active ? "" : " dim"}`} style={style} />
            : <circle key={particle.key} cx={particle.x} cy={particle.y} r={SIZE * 0.8} className={`pulse-particle pulse-unknown${active ? "" : " dim"}`} style={style} />;
        })}
      </svg>
      <figcaption>
        <span>{pulseSentence(summary)}</span>
        <span className="pulse-legend">
          {(["UP", "DOWN", "FLAT"] as const).map((direction) => <span key={direction} className={`direction-${direction.toLowerCase()}`}><span aria-hidden="true">{DIRECTION_CUE[direction].glyph}</span> {DIRECTION_CUE[direction].word}</span>)}
          <span><span aria-hidden="true">○</span> sem variação conhecida</span>
        </span>
        <span className="muted">Uma partícula por série; tamanho igual para todas. A arte não mede preço nem relação entre ativos.</span>
      </figcaption>
    </figure>
  );
}
