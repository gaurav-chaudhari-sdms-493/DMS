import type { Metadata } from "next";
import "./globals.css";
import { Noto_Sans_Devanagari } from "next/font/google";
import { I18nProvider } from "@/lib/i18n";
import { OnlineStatusProvider } from "@/hooks/useOnlineStatus";

const notoSansDevanagari = Noto_Sans_Devanagari({
  subsets: ["devanagari", "latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-noto-devanagari",
});

export const metadata: Metadata = {
  title: "DMS Ai",
  description: "DMS Ai verification system",
  icons: {
    icon: [
      { url: "/favicon.ico" },
      { url: "/icon.png", type: "image/png", sizes: "32x32" },
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
        <I18nProvider>
          <OnlineStatusProvider>{children}</OnlineStatusProvider>
        </I18nProvider>
      </body>
    </html>
  );
}
