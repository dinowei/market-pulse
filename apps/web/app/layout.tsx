import type { Metadata } from "next";
import { Archivo } from "next/font/google";
import Script from "next/script";
import "./globals.css";
import { AppShell } from "../src/components/site-header";
import { WebVitalsReporter } from "../src/components/web-vitals-reporter";
import { THEME_INIT_SCRIPT } from "../src/lib/theme";

// Self-hosted at build time by next/font: no request to Google at runtime. One variable
// family with the width axis: expanded headings, regular text and tabular figures (ADR-028).
const sans = Archivo({ subsets: ["latin"], axes: ["wdth"], variable: "--pa-font-sans", display: "swap" });

export const metadata: Metadata = {
  title: "Market Pulse",
  description: "Terminal financeiro informativo — inicialização do beta.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    // data-theme is set before hydration by the init script (ADR-016), so React must not
    // treat it as a mismatch.
    <html lang="pt-BR" className={sans.variable} suppressHydrationWarning>
      <body>
        <Script id="mp-theme-init" strategy="beforeInteractive">{THEME_INIT_SCRIPT}</Script>
        <WebVitalsReporter />
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
