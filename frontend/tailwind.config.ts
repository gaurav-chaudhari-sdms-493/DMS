import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        // T95 — CSS var set by next/font in app/layout.tsx; applied via
        // the `font-devanagari` class, toggled at runtime by locale.
        devanagari: ["var(--font-devanagari)", "system-ui", "sans-serif"],
      },
      colors: {
        // Navy + gold palette, restyled 2026-09-02 in the visual language
        // of maharashtra.gov.in (deep navy header/nav, warm gold accents,
        // clean white content areas) -- style only, not their actual
        // government emblem/logo, which was deliberately not used here.
        gdriveBg: "#f8f9fa",
        gdriveSurface: "#ffffff",
        gdriveSearchBg: "#eef1f7",
        gdrivePillActive: "#f3e3b0",
        gdrivePillText: "#0d2e5c",
        gdriveBlue: "#0d2e5c",
        gdriveBorder: "#e1e3e1",
        gdriveCardBg: "#f0f4f9",
        gdriveTextMain: "#1f1f1f",
        gdriveTextMuted: "#444746",
        background: "#f8f9fa",
        surface: "#ffffff",
        primary: "#0d2e5c",
        secondary: "#c9a227",
        success: "#146c2e",
        textMain: "#1f1f1f",
        textMuted: "#444746",
        borderDark: "#e1e3e1",
      },
      borderRadius: {
        "3xl": "24px",
        "4xl": "28px",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        fadeIn: "fadeIn 0.25s cubic-bezier(0.4, 0, 0.2, 1)",
        slideUp: "slideUp 0.25s cubic-bezier(0.4, 0, 0.2, 1)",
      },
    },
  },
  plugins: [],
};
export default config;
