import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Market Pulse",
  description: "Terminal financeiro informativo — inicialização do beta.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
