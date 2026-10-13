"use client";

// App shell (ADR-028): sidebar navigation, a top bar with global search and a ticker of the
// benchmark values the API serves to this session, and the page. Login and sign-up render bare.
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, useSyncExternalStore, type ReactNode } from "react";

import type { components } from "../generated/api";
import { API_BASE, apiRequest, isAbort } from "../lib/api-client";
import { applyPalette, applyTheme, currentPalette, currentTheme, subscribePalette, subscribeTheme } from "../lib/theme";
import { Icon, type IconName } from "./icons";
import { InstrumentSearch } from "./instrument-search";

type BenchmarkItem = components["schemas"]["BenchmarkItem"];

export const SITE_NAV: readonly { href: string; label: string }[] = [
  { href: "/", label: "Dashboard" },
  { href: "/markets", label: "Mercados" },
  { href: "/compare", label: "Comparar" },
  { href: "/calendar", label: "Calendário" },
  { href: "/heatmap", label: "Heatmap" },
  { href: "/atlas", label: "Global Atlas" },
  { href: "/watchlists", label: "Watchlists" },
  { href: "/portfolios", label: "Carteiras" },
  { href: "/account", label: "Conta" },
];

const NAV_ICON: Record<string, IconName> = {
  "/": "dashboard", "/markets": "markets", "/compare": "compare", "/calendar": "calendar", "/heatmap": "heatmap",
  "/atlas": "globe", "/watchlists": "list", "/portfolios": "wallet", "/account": "user",
};
const PERSONAL = new Set(["/watchlists", "/portfolios", "/account"]);

export function isActiveRoute(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

function BrandMark() {
  return (
    <span className="brand-mark" aria-hidden="true">
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 13h4l2.5-6 4 11 3-8 1.5 3H22" /></svg>
    </span>
  );
}

function formatValue(value: string): string {
  const number = Number(value);
  return Number.isFinite(number) ? number.toLocaleString("pt-BR", { maximumFractionDigits: number >= 1000 ? 0 : 4 }) : value;
}

/** Benchmark values the API serves to this session; nothing is shown that it did not send. */
export function MarketTicker() {
  const [items, setItems] = useState<BenchmarkItem[] | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    apiRequest<{ items: BenchmarkItem[] }>("/api/v1/market-data/benchmarks", { signal: controller.signal })
      .then((data) => setItems(data.items))
      .catch((error: unknown) => { if (!isAbort(error)) setItems([]); });
    return () => controller.abort();
  }, []);
  if (!items) return <ul className="ticker ticker-note" aria-label="Referências de mercado"><li>Carregando referências…</li></ul>;
  const live = items.filter((item) => item.value != null && item.freshness !== "UNAVAILABLE");
  if (live.length === 0) {
    const needsSession = items.some((item) => item.unavailable_reason === "SESSION_REQUIRED");
    return <ul className="ticker ticker-note" aria-label="Referências de mercado"><li>{needsSession ? <Link href="/login">Entre para ver as cotações de referência</Link> : "Referências de mercado indisponíveis"}</li></ul>;
  }
  // The chips scroll sideways on narrow screens, so the list takes focus (WCAG 2.1.1).
  return (
    <ul className="ticker" aria-label="Referências de mercado" tabIndex={0}>
      {live.map((item) => {
        const change = item.change_percent == null ? null : Number(item.change_percent);
        const tone = change === null ? "" : change > 0 ? "direction-up" : change < 0 ? "direction-down" : "direction-flat";
        return (
          <li key={item.canonical_id}>
            <strong>{item.symbol}</strong>
            <span>{formatValue(item.value as string)}</span>
            {change !== null && <span className={tone}>{change > 0 ? "▲" : change < 0 ? "▼" : "▬"} {Math.abs(change).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}%</span>}
            {item.is_demo && <span>DEMO</span>}
          </li>
        );
      })}
    </ul>
  );
}

function DisplayButtons() {
  const theme = useSyncExternalStore(subscribeTheme, currentTheme, () => "dark" as const);
  const palette = useSyncExternalStore(subscribePalette, currentPalette, () => "default" as const);
  const next = theme === "dark" ? "light" : "dark";
  return (
    <>
      <button type="button" className="side-button" aria-label={`Mudar para tema ${next === "light" ? "claro" : "escuro"}`} onClick={() => applyTheme(next)}>
        <Icon name={next === "light" ? "sun" : "moon"} /><span>Tema {next === "light" ? "claro" : "escuro"}</span>
      </button>
      <button type="button" className="side-button" aria-pressed={palette === "cvd"} onClick={() => applyPalette(palette === "cvd" ? "default" : "cvd")}>
        <Icon name="eye" /><span>Paleta para daltonismo</span>
      </button>
    </>
  );
}

const WITHOUT_CHROME = new Set(["/login", "/register"]);

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname() ?? "/";
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  if (WITHOUT_CHROME.has(pathname)) return <>{children}</>;

  async function logout() {
    try {
      const response = await fetch(`${API_BASE}/api/v1/auth/logout`, { method: "POST", credentials: "include" });
      if (!response.ok) throw new Error("Logout unavailable");
      router.push("/login");
    } catch {
      setError("Não foi possível encerrar a sessão. Tente novamente.");
    }
  }

  const link = (item: (typeof SITE_NAV)[number]) => {
    const active = isActiveRoute(pathname, item.href);
    return (
      <Link key={item.href} href={item.href} className="side-link" aria-current={active ? "page" : undefined}>
        <Icon name={NAV_ICON[item.href]} />{item.label}
      </Link>
    );
  };

  return (
    <>
      <a className="skip-link" href="#main-content">Pular para o conteúdo</a>
      <div className="app-shell">
        <aside className="sidebar">
          <Link className="brand" href="/"><BrandMark /><span className="brand-name">Market Pulse</span></Link>
          <nav className="side-nav" aria-label="Navegação principal">
            <h2>Mercado</h2>
            {SITE_NAV.filter((item) => !PERSONAL.has(item.href)).map(link)}
            <h2>Sua área</h2>
            {SITE_NAV.filter((item) => PERSONAL.has(item.href)).map(link)}
          </nav>
          <div className="sidebar-foot">
            <DisplayButtons />
            <Link className="side-button" href="/login"><Icon name="login" /><span>Login</span></Link>
            <button type="button" className="side-button" aria-label="Sair" onClick={() => void logout()}><Icon name="logout" /><span>Sair</span></button>
          </div>
        </aside>
        <div className="app-body">
          <header className="app-topbar">
            <InstrumentSearch onSelect={(id) => router.push(`/assets?id=${encodeURIComponent(id)}`)} />
            <MarketTicker />
          </header>
          {error && <p className="site-alert" role="alert">{error}</p>}
          {children}
        </div>
      </div>
    </>
  );
}
