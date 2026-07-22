import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        gdriveBg: "#f8f9fa",
        gdriveSurface: "#ffffff",
        gdriveSearchBg: "#edf2fc",
        gdrivePillActive: "#c2e7ff",
        gdrivePillText: "#001d35",
        gdriveBlue: "#0b57d0",
        gdriveBorder: "#e1e3e1",
        gdriveCardBg: "#f0f4f9",
        gdriveTextMain: "#1f1f1f",
        gdriveTextMuted: "#444746",
        background: "#f8f9fa",
        surface: "#ffffff",
        primary: "#0b57d0",
        secondary: "#00639b",
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
