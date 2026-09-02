import "./globals.css";
import React from "react";
import { Noto_Sans_Devanagari } from "next/font/google";
import { I18nProvider } from "@/lib/i18n";

// T95 — loaded unconditionally (Next.js requires next/font calls to be
// static); applied via the `font-devanagari` class, toggled at runtime
// by I18nProvider based on the user's selected locale.
const notoSansDevanagari = Noto_Sans_Devanagari({
  subsets: ["devanagari"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-devanagari",
  display: "swap",
});

export const metadata = {
  title: "DMS - DocSearch AI",
  description: "AI Powered Document Management System (DMS)",
  viewport: "width=device-width, initial-scale=1",
  icons: {
    icon: [
      { url: "/stark-dms-app-logo.svg", type: "image/svg+xml" },
      { url: "/favicon.ico" },
      { url: "/stark-icon-32.png", sizes: "32x32", type: "image/png" },
      { url: "/stark-icon-16.png", sizes: "16x16", type: "image/png" },
    ],
    apple: [
      { url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" },
    ],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={notoSansDevanagari.variable}>
      <body className="bg-gdriveBg min-h-screen text-gdriveTextMain overflow-hidden select-none">
        <I18nProvider>{children}</I18nProvider>
      </body>
    </html>
  );
}
