import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        charcoal: {
          950: "#0b0d0c",
          900: "#111513",
          800: "#181d1a",
          700: "#222926",
        },
        emerald: {
          glow: "#34d399",
          deep: "#065f46",
        },
        violet: {
          glow: "#a78bfa",
          deep: "#4c1d95",
        },
        ink: {
          DEFAULT: "#e9ede9",
          muted: "#9aa59e",
          faint: "#5f6a63",
        },
      },
      fontFamily: {
        display: ["Fraunces", "Georgia", "Cambria", "serif"],
        sans: ["Manrope", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        glass: "0 1px 0 0 rgba(255,255,255,0.08) inset, 0 -1px 0 0 rgba(0,0,0,0.25) inset, 0 24px 60px -20px rgba(0,0,0,0.6)",
        lift: "0 40px 80px -24px rgba(0,0,0,0.7), 0 0 0 1px rgba(255,255,255,0.08)",
      },
      borderRadius: {
        tile: "1.5rem",
        pill: "999px",
      },
      transitionTimingFunction: {
        spring: "cubic-bezier(0.22, 1, 0.36, 1)",
      },
    },
  },
  plugins: [],
};
export default config;
