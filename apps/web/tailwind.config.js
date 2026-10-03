/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        graphite: {
          950: "#070a0e",
          900: "#0b0f15",
          850: "#10161f",
          800: "#151d28",
          750: "#1b2533",
          700: "#222e3f",
          600: "#2c3b50",
          500: "#3d4f68",
        },
        terminal: {
          green: "#10b981",
          amber: "#f59e0b",
          red: "#ef4444",
          blue: "#38bdf8",
          purple: "#a855f7",
          cyan: "#06b6d4",
        },
      },
      fontFamily: {
        mono: [
          "JetBrains Mono",
          "Consolas",
          "SF Mono",
          "Fira Code",
          "monospace",
        ],
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};
