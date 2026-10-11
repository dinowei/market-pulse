"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";

import { API_BASE } from "../lib/api-client";
import { PaletteToggle } from "./palette-toggle";
import { ThemeToggle } from "./theme-toggle";

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

export function isActiveRoute(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

// Nine points of the Particle Atlas mark; decorative, the brand text carries the name.
function BrandMark() {
  return (
    <svg className="brand-mark" viewBox="0 0 12 12" aria-hidden="true" focusable="false">
      {[2, 6, 10].flatMap((y, row) => [2, 6, 10].map((x, column) => <circle key={`${x}-${y}`} cx={x} cy={y} r={row === 1 && column === 1 ? 1.6 : 1} />))}
    </svg>
  );
}

// One header for every page (the dashboard passes its search). The current route is marked
// with aria-current, not only with color.
export function SiteHeader({ search, extraLinks }: { search?: ReactNode; extraLinks?: ReactNode }) {
  const pathname = usePathname() ?? "/";
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  async function logout() {
    try {
      const response = await fetch(`${API_BASE}/api/v1/auth/logout`, { method: "POST", credentials: "include" });
      if (!response.ok) throw new Error("Logout unavailable");
      router.push("/login");
    } catch {
      setError("Não foi possível encerrar a sessão. Tente novamente.");
    }
  }

  return (
    <>
      <a className="skip-link" href="#main-content">Pular para o conteúdo</a>
      <header className={search ? "topbar site-header" : "topbar site-header site-header-plain"}>
        <Link className="brand" href="/"><BrandMark /><span className="brand-name">MARKET PULSE</span> <span>BETA</span></Link>
        {search}
        <nav aria-label="Navegação principal">
          {SITE_NAV.map((item) => {
            const active = isActiveRoute(pathname, item.href);
            return <Link key={item.href} href={item.href} aria-current={active ? "page" : undefined} className={active ? "nav-active" : undefined}>{item.label}</Link>;
          })}
          {extraLinks}
          <Link href="/login">Login</Link>
          <button type="button" aria-label="Sair" onClick={() => void logout()}>Sair</button>
        </nav>
        <div className="display-toggles"><ThemeToggle /><PaletteToggle /></div>
      </header>
      {error && <p className="site-alert" role="alert">{error}</p>}
    </>
  );
}

const WITHOUT_CHROME = new Set(["/", "/login", "/register"]);

/** Header for every route except the dashboard (it renders its own with search) and auth. */
export function SiteChrome() {
  const pathname = usePathname() ?? "/";
  return WITHOUT_CHROME.has(pathname) ? null : <SiteHeader />;
}
