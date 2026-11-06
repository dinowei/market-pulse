"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState, type CSSProperties, type PointerEvent } from "react";

import type { components } from "../generated/api";
import { FINANCIAL_DISCLAIMER } from "../lib/disclaimers";
import { formatAmount, shortReason } from "../lib/panorama";
import { DIRECTION_CUE, priceDirection } from "../lib/price-direction";
import { blockHeight, changeStep, squarify, type Rect } from "../lib/treemap";
import { useCachedApi } from "../lib/use-cached-api";
import { Logo } from "./asset-facts";
import { DataStateBadge } from "./data-table";
import styles from "./market-heatmap.module.css";

type MarketMap = components["schemas"]["MarketMapResponse"];
type Tile = components["schemas"]["MarketMapTile"];
type Market = MarketMap["market"];

// The real market as a treemap in perspective (ADR-032): area from the source's size, color and
// height from the day's change, the number written on the block. Plain CSS 3D, so it stays
// light; the sliders and the table below give the same control and data without a pointer.
const SIZING: Record<MarketMap["sizing"], string> = {
  MARKET_CAP: "Área pelo valor de mercado",
  TRADED_VALUE: "Área pelo valor negociado no pregão",
  EQUAL: "Blocos de mesma área",
};
const HEADER = 20;
const GAP = 3;
const DEFAULT_ANGLE = { tilt: 48, turn: -16 };
const FLAT_ANGLE = { tilt: 0, turn: 0 };

type Placed = { tile: Tile; sector: string; rect: Rect };
type Group = { sector: string; rect: Rect };

function layout(map: MarketMap, only: string | null, width: number, height: number) {
  const sectors = map.sectors.filter((sector) => only === null || sector.sector === only);
  const totals = sectors.map((sector) => sector.tiles.reduce((sum, tile) => sum + Number(tile.size_value), 0));
  const boxes = squarify(totals, { x: 0, y: 0, width, height });
  const groups: Group[] = [];
  const placed: Placed[] = [];
  sectors.forEach((sector, index) => {
    const box = boxes[index];
    groups.push({ sector: sector.sector, rect: box });
    const inner = { x: box.x + GAP, y: box.y + HEADER, width: box.width - GAP * 2, height: box.height - HEADER - GAP };
    const rects = squarify(sector.tiles.map((tile) => Number(tile.size_value)), inner);
    sector.tiles.forEach((tile, position) => placed.push({ tile, sector: sector.sector, rect: rects[position] }));
  });
  return { groups, placed };
}

function percentText(value: string | null | undefined): string {
  const direction = priceDirection(value);
  if (!direction || value == null) return "sem variação";
  const number = Math.abs(Number(value)).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `${direction === "UP" ? "+" : direction === "DOWN" ? "−" : ""}${number}%`;
}

function tone(value: string | null | undefined): string {
  const direction = priceDirection(value);
  if (!direction || value == null) return styles.none;
  if (direction === "FLAT") return styles.flat;
  return styles[`${direction === "UP" ? "up" : "down"}${changeStep(Number(value))}`];
}

const compact = new Intl.NumberFormat("pt-BR", { notation: "compact", maximumFractionDigits: 1 });
const amount = (value: string | null | undefined, currency?: string) => (value == null ? "—" : `${currency ? `${currency} ` : ""}${compact.format(Number(value))}`);

function TileDetail({ placed }: { placed: Placed | null }) {
  if (!placed) return <p className={styles.hint}>Passe o mouse ou o foco em um bloco para ver os detalhes. Clique para abrir o ativo.</p>;
  const { tile, sector } = placed;
  const direction = priceDirection(tile.change_percent);
  return (
    <dl className={styles.detail}>
      <div><dt>Ativo</dt><dd>{tile.logo_url && <Logo key={tile.logo_url} src={tile.logo_url} />} <strong>{tile.symbol}</strong> {tile.name !== tile.symbol && tile.name}</dd></div>
      <div><dt>Setor</dt><dd>{sector}</dd></div>
      <div><dt>Preço</dt><dd>{tile.currency} {formatAmount(tile.price)}</dd></div>
      <div><dt>Dia</dt><dd className={direction ? `direction-${direction.toLowerCase()}` : ""}>{direction && <span aria-hidden="true">{DIRECTION_CUE[direction].glyph} </span>}{percentText(tile.change_percent)}{direction && ` ${DIRECTION_CUE[direction].word}`}</dd></div>
      <div><dt>Volume</dt><dd>{amount(tile.volume)}</dd></div>
      {tile.market_cap != null && <div><dt>Valor de mercado</dt><dd>{amount(tile.market_cap, tile.currency)}</dd></div>}
    </dl>
  );
}

export function MarketHeatmap() {
  const [market, setMarket] = useState<Market>("BR");
  const [sector, setSector] = useState<string | null>(null);
  const [angle, setAngle] = useState(DEFAULT_ANGLE);
  const [active, setActive] = useState<Placed | null>(null);
  const [width, setWidth] = useState(0);
  const stage = useRef<HTMLDivElement>(null);
  const drag = useRef<{ x: number; y: number; tilt: number; turn: number; moved: boolean } | null>(null);
  const { data, failed } = useCachedApi<MarketMap>(`/api/v1/market-data/market-map?market=${market}`, 5 * 60_000);

  useEffect(() => {
    const node = stage.current;
    if (!node) return undefined;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.floor(entry.contentRect.width)));
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  // The perspective costs too much legibility on a phone: there the map opens flat.
  useEffect(() => {
    if (window.matchMedia("(max-width: 700px)").matches) {
      const timer = setTimeout(() => setAngle(FLAT_ANGLE));
      return () => clearTimeout(timer);
    }
    return undefined;
  }, []);

  const flat = angle.tilt === 0 && angle.turn === 0;
  const height = Math.max(420, Math.round(width * 0.54));
  const map = data?.market === market ? data : undefined;
  const { groups, placed } = useMemo(() => (map && width > 0 ? layout(map, sector, width, height) : { groups: [], placed: [] }), [map, sector, width, height]);
  const breadth = useMemo(() => {
    const known = placed.filter((item) => item.tile.change_percent != null);
    return { up: known.filter((item) => Number(item.tile.change_percent) > 0).length, down: known.filter((item) => Number(item.tile.change_percent) < 0).length, total: placed.length };
  }, [placed]);

  function startDrag(event: PointerEvent<HTMLDivElement>) {
    drag.current = { x: event.clientX, y: event.clientY, ...angle, moved: false };
  }
  function moveDrag(event: PointerEvent<HTMLDivElement>) {
    const from = drag.current;
    if (!from || event.pointerType === "touch") return;
    const dx = event.clientX - from.x;
    const dy = event.clientY - from.y;
    if (!from.moved && Math.abs(dx) + Math.abs(dy) < 6) return;
    from.moved = true;
    setAngle({ tilt: Math.max(0, Math.min(65, from.tilt - dy * 0.25)), turn: Math.max(-40, Math.min(40, from.turn + dx * 0.25)) });
  }
  function endDrag() {
    // Keep `moved` until the click that follows the release can read it.
    const current = drag.current;
    setTimeout(() => { if (drag.current === current) drag.current = null; });
  }

  const sceneStyle = { "--tilt": `${angle.tilt}deg`, "--turn": `${angle.turn}deg`, height } as CSSProperties;

  return (
    <section className={styles.panel} aria-labelledby="heatmap-title">
      <div className={styles.head}>
        <div>
          <h2 id="heatmap-title">Mapa do mercado</h2>
          {map && <p className={styles.sub}>
            {map.sectors.length > 0 && `${breadth.total} ativos: ${breadth.up} em alta, ${breadth.down} em queda. ${SIZING[map.sizing]}. `}
            {map.session_date && `Pregão de ${map.session_date.split("-").reverse().join("/")}. `}
            Fonte: {map.provider}.
          </p>}
        </div>
        <div className={styles.controls}>
          <div className={styles.segment} role="group" aria-label="Mercado">
            {(["BR", "US"] as const).map((item) => <button key={item} type="button" aria-pressed={market === item} onClick={() => { setMarket(item); setSector(null); setActive(null); }}>{item === "BR" ? "B3" : "EUA"}</button>)}
          </div>
          <div className={styles.segment} role="group" aria-label="Visualização">
            <button type="button" aria-pressed={!flat} onClick={() => setAngle(DEFAULT_ANGLE)}>3D</button>
            <button type="button" aria-pressed={flat} onClick={() => setAngle(FLAT_ANGLE)}>Plano</button>
          </div>
          {map && <DataStateBadge dataLevel={map.data_level} freshness={map.freshness} />}
        </div>
      </div>

      {failed && !map && <p className="state-note" role="alert">Não foi possível carregar o mapa. A API pode estar iniciando; tente de novo em um minuto.</p>}
      {map?.unavailable_reason === "SESSION_REQUIRED" && <p className="state-note"><Link href="/login">Entre</Link> para ver o mapa com dados reais.</p>}
      {map?.unavailable_reason && map.unavailable_reason !== "SESSION_REQUIRED" && <p className="state-note">Mapa indisponível: {shortReason(map.unavailable_reason)}</p>}
      {map?.is_demo && <p className="state-note">Demonstração: valores sintéticos, não são cotações reais.</p>}

      {map && map.sectors.length > 1 && (
        <div className={styles.chips} role="group" aria-label="Filtrar por setor">
          <button type="button" aria-pressed={sector === null} onClick={() => setSector(null)}>Todos</button>
          {map.sectors.map((item) => <button key={item.sector} type="button" aria-pressed={sector === item.sector} onClick={() => setSector(sector === item.sector ? null : item.sector)}>{item.sector}</button>)}
        </div>
      )}

      <div ref={stage} className={styles.scene} style={sceneStyle} onPointerDown={startDrag} onPointerMove={moveDrag} onPointerUp={endDrag} onPointerCancel={endDrag} data-flat={flat || undefined}>
        {!map && !failed && <p className={styles.loading}>Carregando o mapa…</p>}
        <div className={styles.plane} style={{ width, height }}>
          {groups.map(({ sector: name, rect }) => (
            <div key={name} className={styles.sector} style={{ left: rect.x, top: rect.y, width: rect.width, height: rect.height }}>
              {rect.width > 70 && <span title={name}>{name}</span>}
            </div>
          ))}
          {placed.map((item) => {
            const { tile, rect } = item;
            if (rect.width < 2 || rect.height < 2) return null;
            const side = Math.min(rect.width, rect.height);
            const font = Math.max(9, Math.min(30, side / 3.6));
            const percent = tile.change_percent == null ? null : Number(tile.change_percent);
            const style = { left: rect.x + 1, top: rect.y + 1, width: rect.width - 2, height: rect.height - 2, "--rise": `${flat ? 0 : blockHeight(percent)}px`, "--font": `${font}px` } as CSSProperties;
            const body = (
              <>
                <span className={styles.front} aria-hidden="true" />
                <span className={styles.left} aria-hidden="true" />
                <span className={styles.right} aria-hidden="true" />
                <span className={styles.top}>
                  {rect.width >= 34 && rect.height >= 18 && <strong>{tile.symbol}</strong>}
                  {rect.width >= 42 && rect.height >= 32 && <small>{percentText(tile.change_percent)}</small>}
                </span>
              </>
            );
            const label = `${tile.symbol}: ${percentText(tile.change_percent)}, ${item.sector}`;
            const focus = { onMouseEnter: () => setActive(item), onFocus: () => setActive(item) };
            return tile.canonical_id
              ? <Link key={tile.symbol} href={`/assets?id=${encodeURIComponent(tile.canonical_id)}`} className={`${styles.tile} ${tone(tile.change_percent)}`} style={style} aria-label={label} onClick={(event) => { if (drag.current?.moved) event.preventDefault(); }} {...focus}>{body}</Link>
              : <button key={tile.symbol} type="button" className={`${styles.tile} ${tone(tile.change_percent)}`} style={style} aria-label={label} {...focus}>{body}</button>;
          })}
        </div>
      </div>

      <div className={styles.below}>
        <TileDetail placed={active} />
        <div className={styles.legend} aria-hidden="true">
          <span>−3%</span>{[4, 3, 2, 1].map((step) => <i key={`d${step}`} className={styles[`down${step}`]} />)}<i className={styles.flat} />{[1, 2, 3, 4].map((step) => <i key={`u${step}`} className={styles[`up${step}`]} />)}<span>+3%</span>
        </div>
        {!flat && (
          <div className={styles.sliders}>
            <label>Inclinação <input type="range" min={0} max={65} value={angle.tilt} onChange={(event) => setAngle({ ...angle, tilt: Number(event.target.value) })} /></label>
            <label>Giro <input type="range" min={-40} max={40} value={angle.turn} onChange={(event) => setAngle({ ...angle, turn: Number(event.target.value) })} /></label>
          </div>
        )}
      </div>

      {map && placed.length > 0 && (
        <details className={styles.tableBox}>
          <summary>Ver todos os {placed.length} ativos em tabela</summary>
          <div className="table-wrap"><table>
            <caption>Tabela equivalente ao mapa, com a origem de cada bloco</caption>
            <thead><tr><th scope="col">Ativo</th><th scope="col">Setor</th><th scope="col">Preço</th><th scope="col">Variação</th><th scope="col">Volume</th><th scope="col">Valor de mercado</th></tr></thead>
            <tbody>{placed.map(({ tile, sector: name }) => (
              <tr key={tile.symbol}>
                <th scope="row">{tile.canonical_id ? <Link href={`/assets?id=${encodeURIComponent(tile.canonical_id)}`}>{tile.symbol}</Link> : tile.symbol}<br /><small>{tile.name}</small></th>
                <td>{name}</td><td>{tile.currency} {formatAmount(tile.price)}</td><td>{percentText(tile.change_percent)}</td><td>{amount(tile.volume)}</td><td>{amount(tile.market_cap, tile.currency)}</td>
              </tr>
            ))}</tbody>
          </table></div>
        </details>
      )}
      {map && <ul className={styles.limits} aria-label="Limitações do mapa">{map.limitations.map((text) => <li key={text}>{text}</li>)}</ul>}
      <p className="financial-disclaimer">{FINANCIAL_DISCLAIMER}</p>
    </section>
  );
}
