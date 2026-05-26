/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Climate-tech palette: deep space backdrop + cyan/teal accents
        bhoomi: {
          bg: "#070b14",
          surface: "#0e1626",
          glass: "rgba(20,32,54,0.55)",
          border: "rgba(86,124,168,0.22)",
          cyan: "#38bdf8",
          teal: "#2dd4bf",
          amber: "#fbbf24",
          rose: "#fb7185",
        },
        risk: {
          low: "#34d399",
          moderate: "#fbbf24",
          high: "#fb923c",
          severe: "#f43f5e",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      backdropBlur: { xs: "2px" },
      boxShadow: {
        glow: "0 0 40px -8px rgba(56,189,248,0.35)",
        card: "0 8px 32px -12px rgba(0,0,0,0.6)",
      },
      keyframes: {
        shimmer: {
          "0%": { backgroundPosition: "-1000px 0" },
          "100%": { backgroundPosition: "1000px 0" },
        },
        float: {
          "0%,100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-6px)" },
        },
      },
      animation: {
        shimmer: "shimmer 2s infinite linear",
        float: "float 6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
