import "./globals.css";
import React from "react";

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

import { I18nProvider } from "@/components/common/I18nProvider";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-gdriveBg min-h-screen text-gdriveTextMain overflow-hidden select-none">
        <I18nProvider>
          {children}
        </I18nProvider>
      </body>
    </html>
  );
}
