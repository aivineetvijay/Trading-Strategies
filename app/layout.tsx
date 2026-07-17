import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MACD Divergence Screener",
  description:
    "MACD Divergence + Support/Resistance stock screener, powered by Alpha Vantage.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="font-sans min-h-screen">{children}</body>
    </html>
  );
}
