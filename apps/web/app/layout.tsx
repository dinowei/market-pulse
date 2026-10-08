import type { Metadata } from "next";
import Script from "next/script";
import "./globals.css";
import { WebVitalsReporter } from "../src/components/web-vitals-reporter";
import { THEME_INIT_SCRIPT } from "../src/lib/theme";

export const metadata: Metadata = {
  title: "Market Pulse",
  description: "Terminal financeiro informativo — inicialização do beta.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    // data-theme is set before hydration by the init script (ADR-016), so React must not
    // treat it as a mismatch.
    <html lang="pt-BR" suppressHydrationWarning>
      <body>
        <Script id="mp-theme-init" strategy="beforeInteractive">{THEME_INIT_SCRIPT}</Script>
        <WebVitalsReporter />
        {children}
      </body>
    </html>
  );
}
