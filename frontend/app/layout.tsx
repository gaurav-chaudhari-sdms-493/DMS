import "./globals.css";
import React from "react";

export const metadata = {
  title: "Google Drive - DocSearch AI",
  description: "AI Powered Google Drive Clone",
  viewport: "width=device-width, initial-scale=1",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-gdriveBg min-h-screen text-gdriveTextMain overflow-hidden select-none">
        {children}
      </body>
    </html>
  );
}
