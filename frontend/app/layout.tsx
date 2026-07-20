import "./globals.css";
import { Inter } from "next/font/google";
import Link from "next/link";
import React from "react";

const inter = Inter({ subsets: ["latin"], weight: ["300", "400", "500", "600", "700"] });

export const metadata = {
  title: "DocSearch AI",
  description: "AI-Powered Document Intelligence",
  viewport: "width=device-width, initial-scale=1",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} min-h-screen relative overflow-x-hidden`}>
        {/* Animated Background Gradient */}
        <div className="fixed inset-0 z-[-1]">
          <div className="absolute top-0 left-0 w-full h-full bg-[#0a0f1e]"></div>
          <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-primary/20 blur-[120px] mix-blend-screen pointer-events-none animate-pulse"></div>
          <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-secondary/20 blur-[120px] mix-blend-screen pointer-events-none animate-pulse"></div>
        </div>

        {/* Global Header */}
        <header className="sticky top-0 z-50 glass border-b-0 border-borderDark border-solid border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white font-bold text-lg">
                D
              </div>
              <span className="font-bold text-xl tracking-tight">DocSearch AI</span>
            </Link>

            <nav className="flex items-center gap-6">
              <Link href="/upload" className="text-sm font-medium text-textMuted hover:text-textMain transition-colors">
                Upload
              </Link>
              <Link href="/search" className="text-sm font-medium text-textMuted hover:text-textMain transition-colors">
                Search
              </Link>
              <div className="w-8 h-8 rounded-full bg-surface border border-borderDark flex items-center justify-center overflow-hidden">
                <svg className="w-4 h-4 text-textMuted" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M24 20.993V24H0v-2.996A14.977 14.977 0 0112.004 15c4.904 0 9.26 2.354 11.996 5.993zM16.002 8.999a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
              </div>
            </nav>
          </div>
        </header>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
      </body>
    </html>
  );
}
