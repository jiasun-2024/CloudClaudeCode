import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#07131a",
        mist: "#ebf2f6",
        tide: "#54d3c2",
        amber: "#ffb146",
      },
      fontFamily: {
        sans: ["Space Grotesk", "Avenir Next", "Segoe UI", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        panel: "0 12px 40px rgba(4, 15, 24, 0.24)",
      },
    },
  },
  plugins: [],
} satisfies Config;
