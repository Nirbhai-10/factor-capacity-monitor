import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        serif: ['"EB Garamond"', "Garamond", "Georgia", "serif"],
        body: ['"Source Serif 4"', "Source Serif Pro", "Georgia", "serif"],
        mono: ['"JetBrains Mono"', "IBM Plex Mono", "monospace"],
      },
      colors: {
        cream: "#fbfaf6",
        ivory: "#ffffff",
        ink: "#1a1a1a",
        muted: "#5a5a5a",
        rule: "#e6e3da",
        accent: "#1a3a5c",
        accentSoft: "#4d6b88",
        gold: "#a08c5d",
        safe: "#2d7a4f",
        caution: "#b07c2c",
        danger: "#a04040",
      },
      maxWidth: {
        prose: "70ch",
      },
    },
  },
  plugins: [],
};
export default config;
