"use client";

// Chart workspace (ADR-028): TradingView's open-source Lightweight Charts (Apache-2.0, the
// attribution logo stays on) on canvas, with chart types, indicators, comparison and drawing
// tools on top. Only real bars from the API are drawn; derived views say so on screen, and the
// same series is always available as a table.
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore, type PointerEvent as ReactPointerEvent, type ReactNode } from "react";
import type { IChartApi, ISeriesApi, Logical, MouseEventParams, SeriesType, Time } from "lightweight-charts";

import type { components } from "../generated/api";
import { apiRequest, isAbort } from "../lib/api-client";
import { type Anchor, type Drawing, type DrawingTool, FIB_LEVELS, SHORTCUTS, TOOL_GROUPS, TOOL_SPECS, describeMove, extendLine, loadDrawings, saveDrawings, screenAngle } from "../lib/chart-workspace/drawings";
import { type Bar, type Interval, barsFromSeries, bollinger, ema, epochSeconds, hasOhlc, heikinAshi, linearRegression, macd, ohlcAvailable, resample, rsi, sma } from "../lib/chart-workspace/series";
import { CHART_STORAGE_PREFIX, readStored, writeStored } from "../lib/chart-workspace/preferences";
import { type ChartTheme, currentChartTheme, withAlpha } from "../lib/chart-workspace/theme";
import { subscribePalette, subscribeTheme } from "../lib/theme";
import { formatReason } from "../lib/unavailable-reasons";
import { AccessibleDataTable, DataStateBadge } from "./data-table";
import { Icon, type IconName } from "./icons";
import styles from "./chart-workspace.module.css";

type PublicHistorySeries = components["schemas"]["PublicHistorySeries"];
type LW = typeof import("lightweight-charts");
type AnySeries = ISeriesApi<SeriesType>;

export type ChartType = "candles" | "hollow" | "bars" | "heikin" | "line" | "markers" | "step" | "area" | "baseline" | "columns";
export type IndicatorId = "volume" | "sma9" | "sma21" | "sma50" | "sma200" | "ema20" | "bb" | "rsi" | "macd";

export const CHART_TYPES: { id: ChartType; label: string; icon: IconName; ohlc: boolean }[] = [
  { id: "candles", label: "Velas", icon: "chart", ohlc: true },
  { id: "hollow", label: "Velas vazias", icon: "chart", ohlc: true },
  { id: "bars", label: "Barras", icon: "markets", ohlc: true },
  { id: "heikin", label: "Heikin Ashi", icon: "chart", ohlc: true },
  { id: "line", label: "Linha", icon: "compare", ohlc: false },
  { id: "markers", label: "Linha com marcadores", icon: "compare", ohlc: false },
  { id: "step", label: "Linha em degraus", icon: "compare", ohlc: false },
  { id: "area", label: "Área", icon: "compare", ohlc: false },
  { id: "baseline", label: "Linha base", icon: "compare", ohlc: false },
  { id: "columns", label: "Colunas", icon: "markets", ohlc: false },
];

export const INDICATORS: { id: IndicatorId; label: string }[] = [
  { id: "volume", label: "Volume" },
  { id: "sma9", label: "Média móvel 9" },
  { id: "sma21", label: "Média móvel 21" },
  { id: "sma50", label: "Média móvel 50" },
  { id: "sma200", label: "Média móvel 200" },
  { id: "ema20", label: "Média exponencial 20" },
  { id: "bb", label: "Bandas de Bollinger (20, 2)" },
  { id: "rsi", label: "IFR / RSI (14)" },
  { id: "macd", label: "MACD (12, 26, 9)" },
];

const INTERVALS: { id: Interval; label: string }[] = [
  { id: "D", label: "Diário" },
  { id: "W", label: "Semanal" },
  { id: "M", label: "Mensal" },
];

const RANGES: { id: string; label: string; months?: number; days?: number }[] = [
  { id: "5D", label: "5D", days: 7 },
  { id: "1M", label: "1M", months: 1 },
  { id: "3M", label: "3M", months: 3 },
  { id: "6M", label: "6M", months: 6 },
  { id: "YTD", label: "No ano" },
  { id: "1A", label: "1A", months: 12 },
  { id: "5A", label: "5A", months: 60 },
  { id: "ALL", label: "Tudo" },
];

type Settings = { type: ChartType; interval: Interval; indicators: IndicatorId[] };
const DEFAULT_SETTINGS: Settings = { type: "candles", interval: "D", indicators: ["volume", "sma21"] };
const SETTINGS_KEY = `${CHART_STORAGE_PREFIX}settings.v1`;

function loadSettings(): Settings {
  const parsed = readStored(SETTINGS_KEY) as Partial<Settings> | null;
  if (!parsed || typeof parsed !== "object") return DEFAULT_SETTINGS;
  return {
    type: CHART_TYPES.some((item) => item.id === parsed.type) ? (parsed.type as ChartType) : DEFAULT_SETTINGS.type,
    interval: INTERVALS.some((item) => item.id === parsed.interval) ? (parsed.interval as Interval) : "D",
    indicators: Array.isArray(parsed.indicators) ? parsed.indicators.filter((id): id is IndicatorId => INDICATORS.some((item) => item.id === id)) : DEFAULT_SETTINGS.indicators,
  };
}

function themeKey(): string {
  const root = document.documentElement;
  return `${root.dataset.theme ?? "dark"}|${root.dataset.palette ?? ""}`;
}

function subscribeDisplay(onChange: () => void): () => void {
  const a = subscribeTheme(onChange);
  const b = subscribePalette(onChange);
  return () => { a(); b(); };
}

function timeKey(time: Time | undefined): string | null {
  if (time === undefined) return null;
  if (typeof time === "string") return time;
  if (typeof time === "number") return new Date(time * 1000).toISOString().slice(0, 10);
  return `${time.year}-${String(time.month).padStart(2, "0")}-${String(time.day).padStart(2, "0")}`;
}

const formatPrice = (value: number) => value.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const newId = () => (typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`);

type CompareOption = { id: string; label: string };
type Legend = { time: string; bar: Bar; previous?: Bar } | null;
type Point = { x: number; y: number };
/** Snapshot of the chart geometry, refreshed on every scroll, zoom, resize or rebuild. */
type View = { width: number; height: number; project: (anchor: Anchor) => Point | null; priceY: (price: number) => number | null };
const EMPTY_VIEW: View = { width: 0, height: 0, project: () => null, priceY: () => null };

function Menu({ label, icon, children, open, onToggle }: { label: string; icon: IconName; children: ReactNode; open: boolean; onToggle: (open: boolean) => void }) {
  return (
    <div className={styles.menu} onKeyDown={(event) => { if (event.key === "Escape") { event.stopPropagation(); onToggle(false); } }}>
      <button type="button" className={styles.menuButton} aria-expanded={open} onClick={() => onToggle(!open)}>
        <Icon name={icon} /> <span>{label}</span>
      </button>
      {open && <div className={styles.menuPanel}>{children}</div>}
    </div>
  );
}

/** Remount per instrument (`key={canonicalId}`): drawings and view state belong to one asset. */
export function ChartWorkspace({ canonicalId, symbol, compareOptions = [] }: { canonicalId: string; symbol: string; compareOptions?: CompareOption[] }) {
  const [state, setState] = useState<{ key: string; series?: PublicHistorySeries; error?: string; status?: number }>({ key: "" });
  const [settings, setSettings] = useState<Settings>(loadSettings);
  const [openMenu, setOpenMenu] = useState<string | null>(null);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [compareData, setCompareData] = useState<Record<string, Bar[]>>({});
  const [drawings, setDrawings] = useState<Drawing[]>(() => loadDrawings(canonicalId));
  const [undoStack, setUndoStack] = useState<Drawing[][]>([]);
  const [tool, setTool] = useState<DrawingTool | null>(null);
  const [pending, setPending] = useState<Anchor[]>([]);
  const [hover, setHover] = useState<Anchor | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [magnet, setMagnet] = useState(true);
  const [keepDrawing, setKeepDrawing] = useState(false);
  const [locked, setLocked] = useState(false);
  const [hidden, setHidden] = useState(false);
  const [showObjects, setShowObjects] = useState(false);
  const [textDraft, setTextDraft] = useState<{ anchor: Anchor; value: string } | null>(null);
  const [legend, setLegend] = useState<Legend>(null);
  const [view, setView] = useState<View>(EMPTY_VIEW);
  const [engineReady, setEngineReady] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [activeRange, setActiveRange] = useState("ALL");

  const rootRef = useRef<HTMLElement>(null);
  const boxRef = useRef<HTMLDivElement>(null);
  const overlayRef = useRef<SVGSVGElement>(null);
  const libRef = useRef<LW | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const mainRef = useRef<AnySeries | null>(null);
  const extraRef = useRef<AnySeries[]>([]);
  const rafRef = useRef(0);
  const keyHandlerRef = useRef<(event: KeyboardEvent) => void>(() => undefined);
  const dragRef = useRef<{ id: string; index: number } | null>(null);
  const geometryRef = useRef<{ logicalFromTime: (time: number) => number }>({ logicalFromTime: () => 0 });

  const display = useSyncExternalStore(subscribeDisplay, themeKey, () => "dark|");
  const colors: ChartTheme = useMemo(() => currentChartTheme(display), [display]);

  // Settings and drawings live in this browser only.
  function updateSettings(next: Settings) {
    setSettings(next);
    writeStored(SETTINGS_KEY, next);
  }

  const bump = useCallback(() => {
    cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(() => {
      const chart = chartRef.current;
      const main = mainRef.current;
      if (!chart || !main) return setView(EMPTY_VIEW);
      const scale = chart.timeScale();
      const { logicalFromTime } = geometryRef.current;
      setView({
        width: scale.width(),
        height: chart.panes()[0]?.getHeight() ?? 0,
        project: (anchor) => {
          const x = scale.logicalToCoordinate(logicalFromTime(anchor.time) as Logical);
          const y = main.priceToCoordinate(anchor.price);
          return x === null || y === null ? null : { x, y };
        },
        priceY: (price) => main.priceToCoordinate(price),
      });
    });
  }, []);

  const updateDrawings = useCallback((next: Drawing[]) => {
    setUndoStack((stack) => [...stack.slice(-29), drawings]);
    setDrawings(next);
    saveDrawings(canonicalId, next);
  }, [canonicalId, drawings]);

  useEffect(() => {
    const controller = new AbortController();
    apiRequest<PublicHistorySeries>(`/api/v1/market-data/history/${encodeURIComponent(canonicalId)}?period=MAX&mode=PRICE&adjustment_type=UNADJUSTED`, { signal: controller.signal })
      .then((series) => setState({ key: canonicalId, series }))
      .catch((error: unknown) => { if (!isAbort(error)) setState({ key: canonicalId, error: (error as Error).message, status: (error as Error & { status?: number }).status }); });
    return () => controller.abort();
  }, [canonicalId]);

  useEffect(() => {
    const missing = compareIds.filter((id) => !compareData[id]);
    if (missing.length === 0) return;
    const controller = new AbortController();
    for (const id of missing) {
      apiRequest<PublicHistorySeries>(`/api/v1/market-data/history/${encodeURIComponent(id)}?period=MAX&mode=PRICE&adjustment_type=UNADJUSTED`, { signal: controller.signal })
        .then((series) => setCompareData((current) => ({ ...current, [id]: barsFromSeries(series) })))
        .catch(() => setCompareData((current) => ({ ...current, [id]: [] })));
    }
    return () => controller.abort();
  }, [compareData, compareIds]);

  const loaded = state.key === canonicalId ? state : undefined;
  const series = loaded?.series;
  const bars = useMemo(() => (series && series.freshness !== "UNAVAILABLE" ? barsFromSeries(series) : []), [series]);
  const baseBars = useMemo(() => resample(bars, settings.interval), [bars, settings.interval]);
  const ohlcOk = ohlcAvailable(baseBars);
  const effectiveType: ChartType = CHART_TYPES.find((item) => item.id === settings.type)?.ohlc && !ohlcOk ? "line" : settings.type;
  const hasData = baseBars.length > 0;
  const times = useMemo(() => baseBars.map((bar) => epochSeconds(bar.time)), [baseBars]);
  const indexByTime = useMemo(() => new Map(baseBars.map((bar, index) => [bar.time, index])), [baseBars]);
  const currency = series?.currency ?? "";

  const logicalFromTime = useCallback((time: number): number => {
    const n = times.length;
    if (n < 2) return 0;
    if (time <= times[0]) return (time - times[0]) / (times[1] - times[0]);
    if (time >= times[n - 1]) return n - 1 + (time - times[n - 1]) / (times[n - 1] - times[n - 2]);
    let low = 0;
    let high = n - 1;
    while (high - low > 1) {
      const middle = (low + high) >> 1;
      if (times[middle] <= time) low = middle; else high = middle;
    }
    return low + (time - times[low]) / (times[high] - times[low]);
  }, [times]);

  const timeFromLogical = useCallback((logical: number): number => {
    const n = times.length;
    if (n === 0) return 0;
    if (n === 1) return times[0];
    if (logical <= 0) return times[0] + logical * (times[1] - times[0]);
    if (logical >= n - 1) return times[n - 1] + (logical - (n - 1)) * (times[n - 1] - times[n - 2]);
    const index = Math.floor(logical);
    return times[index] + (logical - index) * (times[index + 1] - times[index]);
  }, [times]);

  useEffect(() => {
    geometryRef.current = { logicalFromTime };
    bump();
  }, [bump, logicalFromTime]);

  // Engine: created once per data set, after the canvas host exists.
  useEffect(() => {
    const box = boxRef.current;
    if (!hasData || !box) return;
    let disposed = false;
    void import("lightweight-charts").then((lw) => {
      if (disposed) return;
      libRef.current = lw;
      const chart = lw.createChart(box, {
        autoSize: true,
        layout: { fontFamily: getComputedStyle(document.body).fontFamily, attributionLogo: true },
        localization: { locale: "pt-BR", priceFormatter: formatPrice },
        crosshair: { mode: lw.CrosshairMode.Normal },
        rightPriceScale: { borderVisible: false },
        timeScale: { borderVisible: false, rightOffset: 8 },
      });
      chartRef.current = chart;
      chart.timeScale().subscribeVisibleLogicalRangeChange(bump);
      chart.timeScale().subscribeSizeChange(bump);
      setEngineReady(true);
    });
    return () => {
      disposed = true;
      chartRef.current?.remove();
      chartRef.current = null;
      mainRef.current = null;
      extraRef.current = [];
      setEngineReady(false);
    };
  }, [bump, hasData]);

  useEffect(() => {
    const chart = chartRef.current;
    const lw = libRef.current;
    if (!engineReady || !chart || !lw) return;
    chart.applyOptions({
      layout: { background: { type: lw.ColorType.Solid, color: colors.background }, textColor: colors.muted },
      grid: { vertLines: { color: withAlpha(colors.grid, 0.55) }, horzLines: { color: withAlpha(colors.grid, 0.55) } },
      crosshair: { vertLine: { color: colors.muted, labelBackgroundColor: colors.accent }, horzLine: { color: colors.muted, labelBackgroundColor: colors.accent } },
    });
  }, [colors, engineReady]);

  // Series: rebuilt when the data, type, interval, indicators, comparison or theme change.
  useEffect(() => {
    const chart = chartRef.current;
    const lw = libRef.current;
    if (!engineReady || !chart || !lw || baseBars.length === 0) return;
    for (const item of [mainRef.current, ...extraRef.current]) if (item) chart.removeSeries(item);
    extraRef.current = [];
    while (chart.panes().length > 1) chart.removePane(chart.panes().length - 1);

    const ohlcBars = (effectiveType === "heikin" ? heikinAshi(baseBars) : baseBars).filter(hasOhlc).map((bar) => ({ time: bar.time as Time, open: bar.open, high: bar.high, low: bar.low, close: bar.close }));
    const closes = baseBars.map((bar) => ({ time: bar.time as Time, value: bar.close }));
    let main: AnySeries;
    switch (effectiveType) {
      case "candles":
      case "heikin":
        main = chart.addSeries(lw.CandlestickSeries, { upColor: colors.up, downColor: colors.down, borderVisible: false, wickUpColor: colors.up, wickDownColor: colors.down });
        main.setData(ohlcBars);
        break;
      case "hollow":
        main = chart.addSeries(lw.CandlestickSeries, { upColor: "rgba(0,0,0,0)", downColor: colors.down, borderUpColor: colors.up, borderDownColor: colors.down, wickUpColor: colors.up, wickDownColor: colors.down });
        main.setData(ohlcBars);
        break;
      case "bars":
        main = chart.addSeries(lw.BarSeries, { upColor: colors.up, downColor: colors.down });
        main.setData(ohlcBars);
        break;
      case "area":
        main = chart.addSeries(lw.AreaSeries, { lineColor: colors.accent, topColor: withAlpha(colors.accent, 0.35), bottomColor: withAlpha(colors.accent, 0.02), lineWidth: 2 });
        main.setData(closes);
        break;
      case "baseline":
        main = chart.addSeries(lw.BaselineSeries, { baseValue: { type: "price", price: baseBars[0].close }, topLineColor: colors.up, bottomLineColor: colors.down, topFillColor1: withAlpha(colors.up, 0.28), topFillColor2: withAlpha(colors.up, 0.02), bottomFillColor1: withAlpha(colors.down, 0.02), bottomFillColor2: withAlpha(colors.down, 0.28) });
        main.setData(closes);
        break;
      case "columns":
        main = chart.addSeries(lw.HistogramSeries, { color: colors.accent });
        main.setData(closes);
        break;
      default:
        main = chart.addSeries(lw.LineSeries, { color: colors.accent, lineWidth: 2, lineType: effectiveType === "step" ? lw.LineType.WithSteps : lw.LineType.Simple, pointMarkersVisible: effectiveType === "markers" });
        main.setData(closes);
    }
    mainRef.current = main;

    const add = <T extends SeriesType>(definition: Parameters<IChartApi["addSeries"]>[0], options: object, pane = 0) => {
      const created = chart.addSeries(definition as never, { lastValueVisible: false, priceLineVisible: false, crosshairMarkerVisible: false, ...options } as never, pane) as ISeriesApi<T>;
      extraRef.current.push(created as unknown as AnySeries);
      return created;
    };
    const values = baseBars.map((bar) => bar.close);
    const line = (data: (number | null)[]) => data.flatMap((value, index) => (value === null ? [] : [{ time: baseBars[index].time as Time, value }]));
    const on = (id: IndicatorId) => settings.indicators.includes(id);

    if (on("volume") && baseBars.some((bar) => bar.volume !== null)) {
      const volume = add(lw.HistogramSeries, { priceScaleId: "volume", priceFormat: { type: "volume" } });
      volume.setData(baseBars.flatMap((bar) => (bar.volume === null ? [] : [{ time: bar.time as Time, value: bar.volume, color: withAlpha(bar.close >= (bar.open ?? bar.close) ? colors.up : colors.down, 0.42) }])));
      chart.priceScale("volume").applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    }
    const averages: [IndicatorId, (number | null)[], string][] = [
      ["sma9", sma(values, 9), colors.cyan],
      ["sma21", sma(values, 21), colors.violet],
      ["sma50", sma(values, 50), colors.amber],
      ["sma200", sma(values, 200), colors.pink],
      ["ema20", ema(values, 20), colors.text],
    ];
    for (const [id, data, color] of averages) if (on(id)) add(lw.LineSeries, { color, lineWidth: 1.5 }).setData(line(data));
    if (on("bb")) {
      const bands = bollinger(values);
      add(lw.LineSeries, { color: withAlpha(colors.violet, 0.9), lineWidth: 1 }).setData(line(bands.upper));
      add(lw.LineSeries, { color: withAlpha(colors.violet, 0.6), lineWidth: 1, lineStyle: lw.LineStyle.Dashed }).setData(line(bands.middle));
      add(lw.LineSeries, { color: withAlpha(colors.violet, 0.9), lineWidth: 1 }).setData(line(bands.lower));
    }
    let pane = 1;
    if (on("rsi")) {
      const rsiSeries = add(lw.LineSeries, { color: colors.violet, lineWidth: 1.5, lastValueVisible: true }, pane);
      rsiSeries.setData(line(rsi(values)));
      for (const level of [70, 30]) rsiSeries.createPriceLine({ price: level, color: withAlpha(colors.muted, 0.7), lineWidth: 1, lineStyle: lw.LineStyle.Dashed, axisLabelVisible: true, title: "" });
      pane += 1;
    }
    if (on("macd")) {
      const result = macd(values);
      add(lw.HistogramSeries, {}, pane).setData(result.histogram.flatMap((value, index) => (value === null ? [] : [{ time: baseBars[index].time as Time, value, color: withAlpha(value >= 0 ? colors.up : colors.down, 0.55) }])));
      add(lw.LineSeries, { color: colors.accent, lineWidth: 1.5 }, pane).setData(line(result.line));
      add(lw.LineSeries, { color: colors.amber, lineWidth: 1.5 }, pane).setData(line(result.signal));
    }
    chart.panes().forEach((item, index) => item.setStretchFactor(index === 0 ? 4 : 1));

    const palette = [colors.cyan, colors.violet, colors.amber];
    compareIds.forEach((id, index) => {
      const compare = resample(compareData[id] ?? [], settings.interval);
      if (compare.length > 0) add(lw.LineSeries, { color: palette[index % palette.length], lineWidth: 2, lastValueVisible: true }).setData(compare.map((bar) => ({ time: bar.time as Time, value: bar.close })));
    });
    chart.priceScale("right").applyOptions({
      mode: compareIds.length > 0 ? lw.PriceScaleMode.IndexedTo100 : lw.PriceScaleMode.Normal,
      scaleMargins: { top: 0.08, bottom: on("volume") ? 0.24 : 0.08 },
    });
    bump();
  }, [baseBars, bump, colors, compareData, compareIds, effectiveType, engineReady, settings.indicators, settings.interval]);

  // Legend follows the crosshair; with no crosshair it shows the last bar.
  useEffect(() => {
    const chart = chartRef.current;
    if (!engineReady || !chart) return;
    const handler = (param: MouseEventParams<Time>) => {
      const key = timeKey(param.time);
      const index = key ? indexByTime.get(key) : undefined;
      setLegend(index === undefined ? null : { time: baseBars[index].time, bar: baseBars[index], previous: baseBars[index - 1] });
      if (tool) bump();
    };
    const click = () => setSelected(null);
    chart.subscribeCrosshairMove(handler);
    chart.subscribeClick(click);
    return () => { chart.unsubscribeCrosshairMove(handler); chart.unsubscribeClick(click); };
  }, [baseBars, bump, engineReady, indexByTime, tool]);

  useEffect(() => {
    const listener = (event: KeyboardEvent) => keyHandlerRef.current(event);
    document.addEventListener("keydown", listener);
    return () => document.removeEventListener("keydown", listener);
  }, []);

  useEffect(() => {
    const onChange = () => setFullscreen(document.fullscreenElement === rootRef.current);
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  useEffect(() => {
    if (!openMenu) return;
    const close = (event: PointerEvent) => { if (!(event.target as Element).closest?.(`.${styles.menu}`)) setOpenMenu(null); };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, [openMenu]);

  const anchorAt = useCallback((clientX: number, clientY: number): Anchor | null => {
    const chart = chartRef.current;
    const main = mainRef.current;
    const svg = overlayRef.current;
    if (!chart || !main || !svg) return null;
    const rect = svg.getBoundingClientRect();
    const x = clientX - rect.left;
    const y = clientY - rect.top;
    const logical = chart.timeScale().coordinateToLogical(x);
    const price = main.coordinateToPrice(y);
    if (logical === null || price === null) return null;
    if (magnet && baseBars.length > 0) {
      const index = Math.min(Math.max(Math.round(logical), 0), baseBars.length - 1);
      const bar = baseBars[index];
      const candidates = [bar.open, bar.high, bar.low, bar.close].filter((value): value is number => value !== null);
      // Snap to the nearest of open, high, low or close within 24 px; farther away, keep the point.
      const nearest = candidates.reduce<{ value: number; distance: number }>((best, value) => {
        const distance = Math.abs((main.priceToCoordinate(value) ?? Infinity) - y);
        return distance < best.distance ? { value, distance } : best;
      }, { value: Number(price), distance: 24 });
      return { time: Math.abs(logical - index) < 0.5 ? times[index] : timeFromLogical(logical), price: nearest.value };
    }
    return { time: timeFromLogical(logical), price };
  }, [baseBars, magnet, timeFromLogical, times]);

  function commit(kind: DrawingTool, anchors: Anchor[], text?: string) {
    const drawing: Drawing = { id: newId(), tool: kind, anchors, ...(text ? { text } : {}) };
    updateDrawings([...drawings, drawing]);
    setPending([]);
    setHover(null);
    setSelected(drawing.id);
    if (!keepDrawing) setTool(null);
  }

  function onOverlayPointerDown(event: ReactPointerEvent<SVGSVGElement>) {
    const target = event.target as Element;
    const handle = target.closest("[data-handle]");
    if (handle && !locked) {
      const [id, index] = (handle.getAttribute("data-handle") ?? "").split(":");
      event.currentTarget.setPointerCapture(event.pointerId);
      dragRef.current = { id, index: Number(index) };
      setUndoStack((stack) => [...stack.slice(-29), drawings]);
      return;
    }
    const hit = target.closest("[data-drawing-id]");
    if (hit && !tool) {
      setSelected(hit.getAttribute("data-drawing-id"));
      return;
    }
    if (!tool || locked) return;
    const anchor = anchorAt(event.clientX, event.clientY);
    if (!anchor) return;
    if (tool === "text") {
      setTextDraft({ anchor, value: "" });
      return;
    }
    const next = [...pending, anchor];
    if (next.length >= TOOL_SPECS[tool].anchors) commit(tool, next); else setPending(next);
  }

  function onOverlayPointerMove(event: ReactPointerEvent<SVGSVGElement>) {
    const drag = dragRef.current;
    if (drag) {
      const anchor = anchorAt(event.clientX, event.clientY);
      if (anchor) setDrawings((current) => current.map((item) => (item.id === drag.id ? { ...item, anchors: item.anchors.map((point, index) => (index === drag.index ? anchor : point)) } : item)));
      return;
    }
    if (tool && pending.length > 0) setHover(anchorAt(event.clientX, event.clientY));
  }

  function onOverlayPointerUp(event: ReactPointerEvent<SVGSVGElement>) {
    if (!dragRef.current) return;
    dragRef.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
    saveDrawings(canonicalId, drawings);
  }

  function removeDrawing(id: string) {
    updateDrawings(drawings.filter((item) => item.id !== id));
    if (selected === id) setSelected(null);
  }

  function undo() {
    const previous = undoStack[undoStack.length - 1];
    if (!previous) return;
    setUndoStack((stack) => stack.slice(0, -1));
    setDrawings(previous);
    saveDrawings(canonicalId, previous);
  }

  function chooseTool(next: DrawingTool | null) {
    setTool(next);
    setPending([]);
    setHover(null);
    setOpenMenu(null);
    if (next) setHidden(false);
  }

  // Shortcuts work anywhere on the page (as in desktop charting tools), except while typing.
  function onKeyDown(event: KeyboardEvent) {
    const target = event.target as HTMLElement | null;
    if (target?.closest?.("input, select, textarea, [contenteditable]")) return;
    if (event.key === "Escape") {
      if (pending.length || tool) chooseTool(null); else setSelected(null);
      setTextDraft(null);
    } else if ((event.key === "Delete" || event.key === "Backspace") && selected && !locked) {
      event.preventDefault();
      removeDrawing(selected);
    } else if (event.altKey && SHORTCUTS[event.key.toLowerCase()]) {
      event.preventDefault();
      chooseTool(SHORTCUTS[event.key.toLowerCase()]);
    } else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") {
      event.preventDefault();
      undo();
    }
  }

  useEffect(() => {
    keyHandlerRef.current = onKeyDown;
  });

  function setRange(id: string) {
    const chart = chartRef.current;
    setActiveRange(id);
    if (!chart || baseBars.length === 0) return;
    const spec = RANGES.find((item) => item.id === id);
    if (!spec || id === "ALL") {
      chart.timeScale().fitContent();
      return;
    }
    const last = new Date(`${baseBars[baseBars.length - 1].time}T00:00:00Z`);
    const from = new Date(last);
    if (id === "YTD") from.setUTCMonth(0, 1);
    else if (spec.months) from.setUTCMonth(from.getUTCMonth() - spec.months);
    else if (spec.days) from.setUTCDate(from.getUTCDate() - spec.days);
    const first = baseBars.find((bar) => bar.time >= from.toISOString().slice(0, 10))?.time ?? baseBars[0].time;
    chart.timeScale().setVisibleRange({ from: first as Time, to: baseBars[baseBars.length - 1].time as Time });
  }

  async function screenshot() {
    const chart = chartRef.current;
    const svg = overlayRef.current;
    if (!chart) return;
    const canvas = chart.takeScreenshot(true);
    const context = canvas.getContext("2d");
    if (svg && context && drawings.length > 0 && !hidden) {
      const ratio = canvas.width / (boxRef.current?.clientWidth || canvas.width);
      const source = new XMLSerializer().serializeToString(svg);
      const image = new Image();
      const url = URL.createObjectURL(new Blob([source], { type: "image/svg+xml" }));
      await new Promise<void>((resolve) => { image.onload = () => resolve(); image.onerror = () => resolve(); image.src = url; });
      context.drawImage(image, 0, 0, svg.clientWidth * ratio, svg.clientHeight * ratio);
      URL.revokeObjectURL(url);
    }
    canvas.toBlob((blob) => {
      if (!blob) return;
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `market-pulse-${symbol}-${new Date().toISOString().slice(0, 10)}.png`;
      link.click();
      URL.revokeObjectURL(link.href);
    });
  }

  function toggleFullscreen() {
    if (document.fullscreenElement) void document.exitFullscreen();
    else void rootRef.current?.requestFullscreen?.();
  }

  // Overlay size: the main pane only (price axis and lower panes excluded).
  const { width: plotWidth, height: plotHeight, project, priceY } = view;

  function shapes(drawing: Drawing, preview = false): ReactNode {
    const points = drawing.anchors.map(project);
    if (points.some((point) => point === null)) return null;
    const [p1, p2, p3] = points as { x: number; y: number }[];
    const color = drawing.id === selected ? colors.violet : colors.accent;
    const common = { stroke: color, strokeWidth: 1.6, fill: "none", vectorEffect: "non-scaling-stroke" as const };
    const parts: ReactNode[] = [];
    const segment = (a: { x: number; y: number }, b: { x: number; y: number }, key: string, extra = {}) => parts.push(<line key={key} x1={a.x} y1={a.y} x2={b.x} y2={b.y} {...common} {...extra} />);
    const label = (x: number, y: number, text: string, key: string) => parts.push(<g key={key}><rect x={x + 6} y={y - 22} width={text.length * 6.6 + 12} height={20} rx={5} fill={colors.background} stroke={color} /><text x={x + 12} y={y - 8} fill={colors.text} fontSize={11.5}>{text}</text></g>);
    switch (drawing.tool) {
      case "trend":
        if (p2) segment(p1, p2, "s");
        break;
      case "ray":
      case "extended":
        if (p2) { const [a, b] = extendLine(p1, p2, plotWidth, plotHeight, drawing.tool === "extended"); segment(a, b, "s"); }
        break;
      case "info":
      case "measure":
        if (p2) {
          segment(p1, p2, "s", drawing.tool === "measure" ? { strokeDasharray: "4 3" } : {});
          const bars = Math.round(Math.abs(logicalFromTime(drawing.anchors[1].time) - logicalFromTime(drawing.anchors[0].time)));
          label(p2.x, p2.y, describeMove(drawing.anchors[0], drawing.anchors[1], bars, currency), "l");
        }
        break;
      case "angle":
        if (p2) { segment(p1, p2, "s"); segment(p1, { x: p1.x + 60, y: p1.y }, "b", { strokeDasharray: "3 3" }); label(p1.x + 30, p1.y, `${screenAngle(p1, p2).toFixed(1)}°`, "l"); }
        break;
      case "hline":
        segment({ x: 0, y: p1.y }, { x: plotWidth, y: p1.y }, "s");
        label(plotWidth - 96, p1.y, formatPrice(drawing.anchors[0].price), "l");
        break;
      case "hray":
        segment(p1, { x: plotWidth, y: p1.y }, "s");
        break;
      case "vline":
        segment({ x: p1.x, y: 0 }, { x: p1.x, y: plotHeight }, "s");
        break;
      case "cross":
        segment({ x: 0, y: p1.y }, { x: plotWidth, y: p1.y }, "h");
        segment({ x: p1.x, y: 0 }, { x: p1.x, y: plotHeight }, "v");
        break;
      case "channel":
        if (p2) {
          segment(p1, p2, "a");
          const offset = p3 ? p3.y - (p1.y + ((p2.y - p1.y) * (p3.x - p1.x)) / ((p2.x - p1.x) || 1)) : 0;
          if (p3) {
            segment({ x: p1.x, y: p1.y + offset }, { x: p2.x, y: p2.y + offset }, "b");
            parts.push(<polygon key="f" points={`${p1.x},${p1.y} ${p2.x},${p2.y} ${p2.x},${p2.y + offset} ${p1.x},${p1.y + offset}`} fill={withAlpha(color, 0.12)} stroke="none" />);
          }
        }
        break;
      case "regression":
        if (p2) {
          const [from, to] = [drawing.anchors[0].time, drawing.anchors[1].time].sort((a, b) => a - b);
          const window = baseBars.filter((bar) => { const t = epochSeconds(bar.time); return t >= from && t <= to; });
          const fit = linearRegression(window.map((bar) => bar.close));
          if (fit && window.length > 1) {
            const start = project({ time: epochSeconds(window[0].time), price: fit.intercept });
            const end = project({ time: epochSeconds(window[window.length - 1].time), price: fit.intercept + fit.slope * (window.length - 1) });
            if (start && end) {
              segment(start, end, "m");
              for (const [sign, key] of [[1, "u"], [-1, "d"]] as const) {
                const a = project({ time: epochSeconds(window[0].time), price: fit.intercept + sign * 2 * fit.deviation });
                const b = project({ time: epochSeconds(window[window.length - 1].time), price: fit.intercept + fit.slope * (window.length - 1) + sign * 2 * fit.deviation });
                if (a && b) segment(a, b, key, { strokeDasharray: "5 4" });
              }
            }
          } else segment(p1, p2, "s", { strokeDasharray: "2 3" });
        }
        break;
      case "fib":
        if (p2) {
          const left = Math.min(p1.x, p2.x);
          const right = Math.max(p1.x, p2.x, left + 40);
          FIB_LEVELS.forEach((level) => {
            const price = drawing.anchors[1].price + (drawing.anchors[0].price - drawing.anchors[1].price) * level;
            const y = priceY(price);
            if (y == null) return;
            parts.push(<line key={`l${level}`} x1={left} y1={y} x2={right} y2={y} {...common} strokeOpacity={level === 0 || level === 1 ? 1 : 0.75} />);
            parts.push(<text key={`t${level}`} x={left + 4} y={y - 4} fill={colors.muted} fontSize={10.5}>{`${level} (${formatPrice(price)})`}</text>);
          });
        }
        break;
      case "rect":
        if (p2) parts.push(<rect key="r" x={Math.min(p1.x, p2.x)} y={Math.min(p1.y, p2.y)} width={Math.abs(p2.x - p1.x)} height={Math.abs(p2.y - p1.y)} {...common} fill={withAlpha(color, 0.12)} />);
        break;
      case "text":
        parts.push(<text key="t" x={p1.x} y={p1.y} fill={colors.text} fontSize={13} fontWeight={600}>{drawing.text}</text>);
        break;
    }
    const hit = !preview && !tool ? (
      <g className={styles.hit} data-drawing-id={drawing.id}>
        {points.length > 1 && points[1] && <line x1={p1.x} y1={p1.y} x2={(points[1] as { x: number }).x} y2={(points[1] as { y: number }).y} />}
        {(drawing.tool === "hline" || drawing.tool === "cross") && <line x1={0} y1={p1.y} x2={plotWidth} y2={p1.y} />}
        {(drawing.tool === "vline" || drawing.tool === "cross") && <line x1={p1.x} y1={0} x2={p1.x} y2={plotHeight} />}
        <circle cx={p1.x} cy={p1.y} r={9} />
      </g>
    ) : null;
    const handles = drawing.id === selected && !preview && !locked ? (points as { x: number; y: number }[]).map((point, index) => (
      <circle key={`h${index}`} className={styles.handle} data-handle={`${drawing.id}:${index}`} cx={point.x} cy={point.y} r={5.5} fill={colors.background} stroke={colors.violet} strokeWidth={2} />
    )) : null;
    return <g key={drawing.id}>{parts}{hit}{handles}</g>;
  }

  const previewDrawing: Drawing | null = tool && pending.length > 0 && hover ? { id: "preview", tool, anchors: [...pending, hover] } : null;
  const typeLabel = CHART_TYPES.find((item) => item.id === effectiveType)?.label ?? "Linha";
  const last = baseBars[baseBars.length - 1];
  const shown = legend ?? (last ? { time: last.time, bar: last, previous: baseBars[baseBars.length - 2] } : null);
  const shownChange = shown?.previous ? shown.bar.close - shown.previous.close : null;
  const notes: string[] = [];
  if (effectiveType !== settings.type) notes.push("Velas e barras exigem abertura, máxima e mínima em todas as sessões; a fonte não trouxe, então o gráfico usa linha.");
  if (effectiveType === "heikin") notes.push("Heikin Ashi é calculado a partir do OHLC real; não é preço negociado.");
  if (effectiveType === "baseline") notes.push("Linha base: o primeiro fechamento carregado.");
  if (settings.indicators.some((id) => id !== "volume")) notes.push("Indicadores calculados no navegador a partir dos fechamentos reais.");
  if (settings.interval !== "D") notes.push("Barras semanais e mensais agregadas dos pregões diários.");
  if (compareIds.length > 0) notes.push("Comparação em escala indexada a 100 no primeiro ponto visível.");
  notes.push("Intradiário indisponível: as fontes aprovadas entregam barras diárias.");

  if (!loaded) return <section className={styles.workspace} aria-busy="true" aria-label={`Gráfico de ${symbol}`}><div className={styles.empty}><p>Carregando o gráfico de {symbol}…</p></div></section>;

  if (!hasData) {
    const reason = series?.unavailable_reason ?? (loaded.status === 401 ? "SESSION_REQUIRED" : null);
    return (
      <section className={styles.workspace} aria-label={`Gráfico de ${symbol}`}>
        <div className={styles.empty}>
          <Icon name="chart" width={40} height={40} />
          <h3>Gráfico indisponível para {symbol}</h3>
          <p>{reason ? formatReason(reason) : loaded.error ? `A série não carregou (${loaded.error}).` : "A fonte não trouxe pregões para este ativo."}</p>
          {reason === "SESSION_REQUIRED" && <Link className={styles.primary} href="/login">Entrar para ver dados reais</Link>}
          {series?.limitations.map((item) => <small key={item}>{item}</small>)}
        </div>
      </section>
    );
  }

  return (
    <section ref={rootRef} className={styles.workspace} data-fullscreen={fullscreen || undefined} aria-label={`Gráfico de ${symbol}`}>
      <div className={styles.topbar} role="toolbar" aria-label="Opções do gráfico">
        <strong className={styles.symbol}>{symbol}</strong>
        <div className={styles.segment} role="group" aria-label="Intervalo">
          {INTERVALS.map((item) => <button key={item.id} type="button" aria-pressed={settings.interval === item.id} onClick={() => updateSettings({ ...settings, interval: item.id })}>{item.label}</button>)}
        </div>
        <Menu label={typeLabel} icon={CHART_TYPES.find((item) => item.id === effectiveType)?.icon ?? "chart"} open={openMenu === "type"} onToggle={(open) => setOpenMenu(open ? "type" : null)}>
          {CHART_TYPES.map((item) => (
            <button key={item.id} type="button" className={styles.menuItem} aria-pressed={effectiveType === item.id} disabled={item.ohlc && !ohlcOk} onClick={() => { updateSettings({ ...settings, type: item.id }); setOpenMenu(null); }}>
              <Icon name={item.icon} /> {item.label}
            </button>
          ))}
        </Menu>
        <Menu label="Indicadores" icon="indicators" open={openMenu === "indicators"} onToggle={(open) => setOpenMenu(open ? "indicators" : null)}>
          {INDICATORS.map((item) => (
            <label key={item.id} className={styles.menuItem}>
              <input type="checkbox" checked={settings.indicators.includes(item.id)} onChange={(event) => updateSettings({ ...settings, indicators: event.target.checked ? [...settings.indicators, item.id] : settings.indicators.filter((id) => id !== item.id) })} />
              {item.label}
            </label>
          ))}
        </Menu>
        {compareOptions.length > 0 && (
          <Menu label={compareIds.length ? `Comparar (${compareIds.length})` : "Comparar"} icon="compare" open={openMenu === "compare"} onToggle={(open) => setOpenMenu(open ? "compare" : null)}>
            {compareOptions.filter((item) => item.id !== canonicalId).map((item) => (
              <label key={item.id} className={styles.menuItem}>
                <input type="checkbox" checked={compareIds.includes(item.id)} disabled={!compareIds.includes(item.id) && compareIds.length >= 3} onChange={(event) => setCompareIds(event.target.checked ? [...compareIds, item.id] : compareIds.filter((id) => id !== item.id))} />
                {item.label}
              </label>
            ))}
          </Menu>
        )}
        <span className={styles.spacer} />
        <button type="button" className={styles.iconButton} onClick={() => void screenshot()} aria-label="Baixar imagem do gráfico" title="Baixar imagem do gráfico"><Icon name="camera" /></button>
        <button type="button" className={styles.iconButton} aria-pressed={fullscreen} onClick={toggleFullscreen} aria-label="Tela cheia" title="Tela cheia"><Icon name="fullscreen" /></button>
      </div>

      <div className={styles.body}>
        <div className={styles.tools} role="toolbar" aria-orientation="vertical" aria-label="Ferramentas de desenho">
          <button type="button" className={styles.tool} aria-pressed={tool === null} onClick={() => chooseTool(null)} aria-label="Cursor" title="Cursor (Esc)"><Icon name="cursor" /></button>
          {TOOL_GROUPS.map((group) => {
            const activeInGroup = group.tools.find((item) => item.tool === tool);
            return (
              <button key={group.id} type="button" className={styles.tool} aria-expanded={openMenu === group.id} aria-pressed={Boolean(activeInGroup)} onClick={() => setOpenMenu(openMenu === group.id ? null : group.id)} aria-label={group.label} title={group.label}>
                <Icon name={(activeInGroup ?? group.tools[0]).tool as IconName} />
              </button>
            );
          })}
          <span className={styles.toolDivider} aria-hidden="true" />
          <button type="button" className={styles.tool} aria-pressed={magnet} onClick={() => setMagnet(!magnet)} aria-label="Ímã: prende o ponto à abertura, máxima, mínima ou fechamento" title="Ímã"><Icon name="magnet" /></button>
          <button type="button" className={styles.tool} aria-pressed={keepDrawing} onClick={() => setKeepDrawing(!keepDrawing)} aria-label="Continuar desenhando com a mesma ferramenta" title="Continuar desenhando"><Icon name="plus" /></button>
          <button type="button" className={styles.tool} aria-pressed={locked} onClick={() => setLocked(!locked)} aria-label="Travar desenhos" title="Travar desenhos"><Icon name="lock" /></button>
          <button type="button" className={styles.tool} aria-pressed={hidden} onClick={() => setHidden(!hidden)} aria-label="Ocultar desenhos" title="Ocultar desenhos"><Icon name="hide" /></button>
          <button type="button" className={styles.tool} disabled={undoStack.length === 0} onClick={undo} aria-label="Desfazer (Ctrl+Z)" title="Desfazer"><Icon name="undo" /></button>
          <button type="button" className={styles.tool} aria-pressed={showObjects} onClick={() => setShowObjects(!showObjects)} aria-label="Lista de desenhos" title="Lista de desenhos"><Icon name="layers" /></button>
          <button type="button" className={styles.tool} disabled={drawings.length === 0 || locked} onClick={() => { updateDrawings([]); setSelected(null); }} aria-label="Remover todos os desenhos" title="Remover desenhos"><Icon name="trash" /></button>
        </div>

        <div className={styles.stage}>
          {TOOL_GROUPS.filter((group) => group.id === openMenu).map((group) => (
            <div key={group.id} className={`${styles.flyout} ${styles.menu}`} role="group" aria-label={group.label}>
              <p>{group.label}</p>
              {group.tools.map((item) => (
                <button key={item.tool} type="button" className={styles.menuItem} aria-pressed={tool === item.tool} onClick={() => chooseTool(item.tool)}>
                  <Icon name={item.tool as IconName} /> {item.label}{item.shortcut && <kbd>{item.shortcut}</kbd>}
                </button>
              ))}
            </div>
          ))}
          {shown && (
            <div className={styles.legend} aria-hidden="true">
              <span className={styles.legendSymbol}>{symbol}</span>
              {hasOhlc(shown.bar) && <><span>A <b>{formatPrice(shown.bar.open)}</b></span><span>Máx <b>{formatPrice(shown.bar.high)}</b></span><span>Mín <b>{formatPrice(shown.bar.low)}</b></span></>}
              <span>F <b>{formatPrice(shown.bar.close)}</b></span>
              {shownChange !== null && shown.previous && <span className={shownChange > 0 ? "direction-up" : shownChange < 0 ? "direction-down" : "direction-flat"}>{shownChange > 0 ? "▲ +" : shownChange < 0 ? "▼ −" : "▬ "}{formatPrice(Math.abs(shownChange))} ({formatPrice(Math.abs((shownChange / shown.previous.close) * 100))}%)</span>}
              <span className={styles.legendDate}>{shown.time}</span>
            </div>
          )}
          <div ref={boxRef} className={styles.chart} role="figure" aria-label={`${symbol}, ${typeLabel.toLowerCase()}, ${baseBars.length} barras ${INTERVALS.find((item) => item.id === settings.interval)?.label.toLowerCase()}; último fechamento ${formatPrice(last.close)} ${currency} em ${last.time}. A tabela abaixo traz os mesmos dados.`} />
          {plotWidth > 0 && plotHeight > 0 && (
            <svg ref={overlayRef} xmlns="http://www.w3.org/2000/svg" className={styles.overlay} data-drawing={tool ? "on" : undefined} width={plotWidth} height={plotHeight} viewBox={`0 0 ${plotWidth} ${plotHeight}`}
              onPointerDown={onOverlayPointerDown} onPointerMove={onOverlayPointerMove} onPointerUp={onOverlayPointerUp} aria-hidden="true">
              {!hidden && drawings.map((item) => shapes(item))}
              {previewDrawing && shapes(previewDrawing, true)}
              {tool && pending.map((point, index) => { const screen = project(point); return screen ? <circle key={index} cx={screen.x} cy={screen.y} r={4} fill={colors.accent} /> : null; })}
            </svg>
          )}
          {textDraft && (() => {
            const at = project(textDraft.anchor);
            return at ? (
              <form className={styles.textDraft} style={{ left: at.x, top: at.y }} onSubmit={(event) => { event.preventDefault(); if (textDraft.value.trim()) commit("text", [textDraft.anchor], textDraft.value.trim()); setTextDraft(null); }}>
                <label className="sr-only" htmlFor="drawing-text">Texto da anotação</label>
                <input id="drawing-text" autoFocus value={textDraft.value} maxLength={80} onChange={(event) => setTextDraft({ ...textDraft, value: event.target.value })} onKeyDown={(event) => { if (event.key === "Escape") setTextDraft(null); }} placeholder="Escreva e tecle Enter" />
              </form>
            ) : null;
          })()}
        </div>

        {showObjects && (
          <aside className={styles.objects} aria-label="Desenhos deste ativo">
            <h3>Desenhos</h3>
            {drawings.length === 0 ? <p>Nenhum desenho. Escolha uma ferramenta à esquerda e clique no gráfico.</p> : (
              <ul>
                {drawings.map((item) => (
                  <li key={item.id} data-selected={item.id === selected || undefined}>
                    <button type="button" onClick={() => setSelected(item.id)}>{TOOL_SPECS[item.tool].label}{item.text ? `: ${item.text}` : ""}</button>
                    <button type="button" aria-label={`Remover ${TOOL_SPECS[item.tool].label}`} disabled={locked} onClick={() => removeDrawing(item.id)}><Icon name="close" width={16} height={16} /></button>
                  </li>
                ))}
              </ul>
            )}
          </aside>
        )}
      </div>

      <div className={styles.bottombar}>
        <div className={styles.segment} role="group" aria-label="Período visível">
          {RANGES.map((item) => <button key={item.id} type="button" aria-pressed={activeRange === item.id} onClick={() => setRange(item.id)}>{item.label}</button>)}
        </div>
        {series && <DataStateBadge dataLevel={series.data_level} freshness={series.freshness} />}
        <span className={styles.status}>{series ? `${series.provider} · ${series.dataset}` : ""}</span>
        <span className={styles.status}>Sem ajuste · {currency} · {series?.timezone ?? "UTC"}</span>
      </div>
      {tool && <p className={styles.hint} role="status">{TOOL_SPECS[tool].label}: {TOOL_SPECS[tool].anchors === 1 ? "clique no gráfico." : `clique ${TOOL_SPECS[tool].anchors} pontos no gráfico.`} Esc cancela.</p>}
      <ul className={styles.notes}>{[...notes, ...(series?.limitations ?? [])].map((note) => <li key={note}>{note}</li>)}</ul>
      <details className={styles.table}>
        <summary>Tabela de dados (alternativa acessível ao gráfico)</summary>
        {series && <AccessibleDataTable points={series.points} ohlc={ohlcOk} />}
      </details>
    </section>
  );
}
